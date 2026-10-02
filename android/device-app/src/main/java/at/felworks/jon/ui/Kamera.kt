package at.felworks.jon.ui

import android.graphics.Bitmap
import android.util.Size
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageCapture
import androidx.camera.core.ImageCaptureException
import androidx.camera.core.ImageProxy
import androidx.camera.core.Preview
import androidx.camera.core.resolutionselector.ResolutionSelector
import androidx.camera.core.resolutionselector.ResolutionStrategy
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import at.felworks.jon.MainActivity
import at.felworks.jon.device.Fotos
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.util.concurrent.Executors

@Composable
private fun Knopf(text: String, hell: Boolean = false, modifier: Modifier = Modifier, aktiv: Boolean = true, klick: () -> Unit) {
    Box(
        modifier.height(54.dp).clip(RoundedCornerShape(28.dp)).background(if (hell) Color.White else Color(0xFF2F2F2F))
            .alpha(if (aktiv) 1f else .5f).clickable(enabled = aktiv, onClick = klick),
        contentAlignment = Alignment.Center
    ) { Text(text, color = if (hell) Color.Black else Color.White, fontSize = 17.sp, fontWeight = FontWeight.SemiBold) }
}

@Composable
private fun Rund(text: String, klick: () -> Unit) {
    Box(Modifier.size(48.dp).clip(CircleShape).background(Color(0x66000000)).clickable(onClick = klick), contentAlignment = Alignment.Center) {
        Text(text, color = Color.White, fontSize = 20.sp)
    }
}

@Composable
private fun LiveKamera(activity: MainActivity, vorne: Boolean, aufnahme: ImageCapture, fehler: (String) -> Unit) {
    val vorschau = remember { PreviewView(activity).apply { scaleType = PreviewView.ScaleType.FILL_CENTER } }
    AndroidView(factory = { vorschau }, modifier = Modifier.fillMaxSize())
    DisposableEffect(vorne) {
        val zukunft = ProcessCameraProvider.getInstance(activity)
        var anbieter: ProcessCameraProvider? = null
        var zu = false
        zukunft.addListener({
            if (!zu) runCatching {
                val kamera = zukunft.get()
                anbieter = kamera
                val bild = Preview.Builder().build().also { it.setSurfaceProvider(vorschau.surfaceProvider) }
                kamera.unbindAll()
                kamera.bindToLifecycle(activity, if (vorne) CameraSelector.DEFAULT_FRONT_CAMERA else CameraSelector.DEFAULT_BACK_CAMERA, bild, aufnahme)
            }.onFailure { fehler(it.message ?: "Die Kamera ist gerade nicht verfügbar.") }
        }, ContextCompat.getMainExecutor(activity))
        onDispose {
            zu = true
            anbieter?.unbindAll()
        }
    }
}

@Composable
fun KameraAnsicht(activity: MainActivity, oben: Float, unten: Float, ziel: String, fertig: (JSONObject?) -> Unit) {
    val scope = rememberCoroutineScope()
    val arbeiter = remember { Executors.newSingleThreadExecutor() }
    DisposableEffect(Unit) { onDispose { arbeiter.shutdown() } }
    var vorne by remember { mutableStateOf(false) }
    var blitz by remember { mutableStateOf(false) }
    var foto by remember { mutableStateOf<Bitmap?>(null) }
    var arbeitet by remember { mutableStateOf(false) }
    var fehler by remember { mutableStateOf("") }
    var gespeichert by remember { mutableIntStateOf(0) }
    var aufblitzen by remember { mutableStateOf(false) }
    val helligkeit by animateFloatAsState(if (aufblitzen) .85f else 0f, tween(if (aufblitzen) 60 else 260), label = "blitz")
    val aufnahme = remember {
        ImageCapture.Builder().setCaptureMode(ImageCapture.CAPTURE_MODE_MINIMIZE_LATENCY)
            .setResolutionSelector(ResolutionSelector.Builder().setResolutionStrategy(ResolutionStrategy(Size(2560, 1920), ResolutionStrategy.FALLBACK_RULE_CLOSEST_LOWER_THEN_HIGHER)).build())
            .build()
    }
    LaunchedEffect(blitz) { aufnahme.flashMode = if (blitz) ImageCapture.FLASH_MODE_ON else ImageCapture.FLASH_MODE_OFF }

    fun sichern(bild: Bitmap, senden: Boolean) {
        arbeitet = true
        scope.launch {
            try {
                val ergebnis = withContext(Dispatchers.IO) {
                    val info = Fotos.speichern(activity, bild)
                    if (senden) info.put("data", Fotos.base64(Fotos.jpeg(Fotos.verkleinern(bild, 1600), 82))).put("mime", "image/jpeg")
                    info
                }
                if (senden) fertig(ergebnis.put("gesendet", true)) else {
                    gespeichert++
                    foto = null
                }
            } catch (e: Exception) {
                fehler = e.message ?: "Foto konnte nicht gespeichert werden."
            } finally { arbeitet = false }
        }
    }

    fun ausloesen() {
        if (arbeitet) return
        arbeitet = true
        fehler = ""
        aufblitzen = true
        scope.launch { delay(90); aufblitzen = false }
        aufnahme.takePicture(arbeiter, object : ImageCapture.OnImageCapturedCallback() {
            override fun onCaptureSuccess(image: ImageProxy) {
                val grad = image.imageInfo.rotationDegrees
                val bild = runCatching { Fotos.drehen(image.toBitmap(), grad) }.getOrNull()
                image.close()
                activity.runOnUiThread {
                    arbeitet = false
                    if (bild == null) { fehler = "Das Foto ist nicht gelungen."; return@runOnUiThread }
                    if (ziel == "chat") foto = bild else sichern(bild, false)
                }
            }

            override fun onError(exception: ImageCaptureException) {
                activity.runOnUiThread {
                    arbeitet = false
                    fehler = exception.message ?: "Das Foto ist nicht gelungen."
                }
            }
        })
    }

    Box(Modifier.fillMaxSize().background(Color.Black)) {
        val aktuell = foto
        if (aktuell == null) {
            LiveKamera(activity, vorne, aufnahme) { fehler = it }
            Box(Modifier.fillMaxSize().background(Color.White.copy(alpha = helligkeit)))
            Row(Modifier.fillMaxWidth().padding(top = (oben + 14).dp, start = 16.dp, end = 16.dp), verticalAlignment = Alignment.CenterVertically) {
                Rund("✕") { fertig(JSONObject().put("gespeichert", gespeichert)) }
                Spacer(Modifier.weight(1f))
                if (gespeichert > 0) Text(if (gespeichert == 1) "1 Foto gespeichert" else "$gespeichert Fotos gespeichert", color = Color.White, fontSize = 15.sp,
                    modifier = Modifier.clip(RoundedCornerShape(20.dp)).background(Color(0x66000000)).padding(horizontal = 14.dp, vertical = 8.dp))
                Spacer(Modifier.weight(1f))
                Rund(if (blitz) "⚡" else "ϟ") { blitz = !blitz }
            }
            Column(Modifier.align(Alignment.BottomCenter).fillMaxWidth().padding(bottom = (unten + 28).dp), horizontalAlignment = Alignment.CenterHorizontally) {
                if (fehler.isNotBlank()) Text(fehler, color = Color(0xFFFF8A8F), fontSize = 14.sp, modifier = Modifier.padding(bottom = 14.dp, start = 24.dp, end = 24.dp))
                Row(Modifier.fillMaxWidth().padding(horizontal = 36.dp), verticalAlignment = Alignment.CenterVertically) {
                    Spacer(Modifier.size(48.dp))
                    Spacer(Modifier.weight(1f))
                    Box(
                        Modifier.size(78.dp).clip(CircleShape).border(4.dp, Color.White, CircleShape).padding(8.dp).clip(CircleShape)
                            .background(if (arbeitet) Color(0xFFBDBDBD) else Color.White).clickable(enabled = !arbeitet) { ausloesen() }
                    )
                    Spacer(Modifier.weight(1f))
                    Rund("⟲") { vorne = !vorne }
                }
                Text(if (ziel == "chat") "Foto für Jon" else "Fotos landen in deiner Galerie unter „Jon“", color = Color(0xFFBDBDBD), fontSize = 13.sp, modifier = Modifier.padding(top = 14.dp))
            }
        } else {
            Image(aktuell.asImageBitmap(), contentDescription = "Aufgenommenes Foto", contentScale = ContentScale.Fit, modifier = Modifier.fillMaxSize())
            Column(Modifier.align(Alignment.BottomCenter).fillMaxWidth().background(Color(0xAA000000)).padding(start = 20.dp, end = 20.dp, top = 18.dp, bottom = (unten + 22).dp)) {
                if (fehler.isNotBlank()) Text(fehler, color = Color(0xFFFF8A8F), fontSize = 14.sp, modifier = Modifier.padding(bottom = 12.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Knopf("Nochmal", modifier = Modifier.weight(1f), aktiv = !arbeitet) { foto = null }
                    Knopf(if (arbeitet) "Wird gesendet …" else "An Jon senden", hell = true, modifier = Modifier.weight(1.4f), aktiv = !arbeitet) { sichern(aktuell, true) }
                }
            }
        }
    }
}
