package at.felworks.jon.ui

import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import at.felworks.jon.MainActivity
import com.google.zxing.BarcodeFormat
import com.google.zxing.BinaryBitmap
import com.google.zxing.DecodeHintType
import com.google.zxing.MultiFormatReader
import com.google.zxing.PlanarYUVLuminanceSource
import com.google.zxing.common.HybridBinarizer
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

@Composable
fun QrKamera(activity: MainActivity, erkannt: (String) -> Unit) {
    val preview = remember { PreviewView(activity).apply { scaleType = PreviewView.ScaleType.FILL_CENTER } }
    val rueckruf by rememberUpdatedState(erkannt)
    AndroidView(factory = { preview }, modifier = Modifier.fillMaxSize())
    DisposableEffect(activity) {
        val executor = Executors.newSingleThreadExecutor()
        val erledigt = AtomicBoolean(false)
        val geschlossen = AtomicBoolean(false)
        val zukunft = ProcessCameraProvider.getInstance(activity)
        var provider: ProcessCameraProvider? = null
        zukunft.addListener({
            if (!geschlossen.get()) {
                runCatching {
                    val kamera = zukunft.get()
                    provider = kamera
                    val bild = Preview.Builder().build().also { it.setSurfaceProvider(preview.surfaceProvider) }
                    val analyse = ImageAnalysis.Builder().setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST).build()
                    val leser = MultiFormatReader().apply { setHints(mapOf(DecodeHintType.POSSIBLE_FORMATS to listOf(BarcodeFormat.QR_CODE))) }
                    analyse.setAnalyzer(executor) { frame ->
                        try {
                            if (!erledigt.get()) {
                                val ebene = frame.planes[0]
                                val daten = ByteArray(frame.width * frame.height)
                                for (y in 0 until frame.height) for (x in 0 until frame.width) daten[y * frame.width + x] = ebene.buffer.get(y * ebene.rowStride + x * ebene.pixelStride)
                                val quelle = PlanarYUVLuminanceSource(daten, frame.width, frame.height, 0, 0, frame.width, frame.height, false)
                                val text = leser.decodeWithState(BinaryBitmap(HybridBinarizer(quelle))).text
                                if (erledigt.compareAndSet(false, true)) activity.runOnUiThread { rueckruf(text) }
                            }
                        } catch (_: Exception) {
                        } finally {
                            leser.reset()
                            frame.close()
                        }
                    }
                    kamera.unbindAll()
                    kamera.bindToLifecycle(activity, CameraSelector.DEFAULT_BACK_CAMERA, bild, analyse)
                }.onFailure { activity.runOnUiThread { rueckruf("") } }
            }
        }, ContextCompat.getMainExecutor(activity))
        onDispose {
            geschlossen.set(true)
            provider?.unbindAll()
            executor.shutdown()
        }
    }
}
