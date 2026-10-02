package at.felworks.jon.ui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.scaleIn
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
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import at.felworks.jon.MainActivity
import at.felworks.jon.core.AppBehaelter

@Composable
fun GeraeteApp(activity: MainActivity, behaelter: AppBehaelter) {
    val bruecke = remember { JonWebBruecke(activity, behaelter).also { activity.bruecke = it } }
    DisposableEffect(Unit) { onDispose { if (activity.bruecke === bruecke) activity.bruecke = null; bruecke.schliessen() } }
    val dichte = LocalDensity.current
    val oben = WindowInsets.statusBars.union(WindowInsets.displayCutout).getTop(dichte)
    val unten = WindowInsets.navigationBars.union(WindowInsets.displayCutout).exclude(WindowInsets.ime).getBottom(dichte)
    LaunchedEffect(oben, unten, dichte.density) { bruecke.einsaetze(oben / dichte.density, unten / dichte.density) }
    val qr by activity.qrWunsch.collectAsState()
    val kamera by activity.kameraWunsch.collectAsState()
    val site by activity.siteWunsch.collectAsState()
    Box(Modifier.fillMaxSize().background(Color.Black)) {
        JonWeb(activity, behaelter, bruecke)
        AnimatedVisibility(visible = qr != null, enter = fadeIn(tween(220)) + scaleIn(initialScale = .96f), exit = fadeOut(tween(180))) {
            QrAnsicht(activity, oben / dichte.density, { qr?.complete(it) }) { qr?.complete(null) }
        }
        AnimatedVisibility(visible = kamera != null, enter = fadeIn(tween(200)) + scaleIn(initialScale = .97f), exit = fadeOut(tween(160))) {
            val wunsch = kamera
            if (wunsch != null) {
                androidx.activity.compose.BackHandler { wunsch.ergebnis.complete(null) }
                KameraAnsicht(activity, oben / dichte.density, unten / dichte.density, wunsch.ziel) { wunsch.ergebnis.complete(it) }
            }
        }
        AnimatedVisibility(visible = site != null, enter = fadeIn(tween(200)) + scaleIn(initialScale = .97f), exit = fadeOut(tween(160))) {
            val wunsch = site
            if (wunsch != null) SiteAnsicht(activity, behaelter, wunsch, oben / dichte.density) { wunsch.fertig.complete(Unit) }
        }
    }
}

@Composable
private fun QrAnsicht(activity: MainActivity, oben: Float, erkannt: (String) -> Unit, schliessen: () -> Unit) {
    val puls = rememberInfiniteTransition(label = "qr")
    val leuchten by puls.animateFloat(.35f, 1f, infiniteRepeatable(tween(1100), RepeatMode.Reverse), label = "rahmen")
    Column(
        Modifier.fillMaxSize().background(Brush.verticalGradient(listOf(Color(0xFF050814), Color.Black))).padding(top = (oben + 40).dp, start = 24.dp, end = 24.dp, bottom = 32.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text("QR-Code scannen", color = Color.White, fontSize = 24.sp, fontWeight = FontWeight.SemiBold)
        Spacer(Modifier.height(10.dp))
        Text("Öffne in Jon am PC oder Pi „Jon-Gerät einrichten“ und halte die Kamera auf den Code.", color = Color(0xFFA3A3A3), fontSize = 15.sp, textAlign = TextAlign.Center)
        Spacer(Modifier.height(36.dp))
        Box(
            Modifier.fillMaxWidth().aspectRatio(1f).clip(RoundedCornerShape(34.dp))
                .border(3.dp, Brush.linearGradient(listOf(Color(0xFF5EE7FF).copy(alpha = leuchten), Color(0xFF3B6CFF), Color(0xFFA35CFF).copy(alpha = leuchten))), RoundedCornerShape(34.dp))
        ) { QrKamera(activity, erkannt) }
        Spacer(Modifier.weight(1f))
        Box(
            Modifier.fillMaxWidth().height(56.dp).clip(RoundedCornerShape(30.dp)).background(Color(0xFF2F2F2F)).clickable(onClick = schliessen),
            contentAlignment = Alignment.Center
        ) { Text("Abbrechen", color = Color.White, fontSize = 17.sp, fontWeight = FontWeight.SemiBold) }
        Spacer(Modifier.height(8.dp))
        Box(Modifier.size(6.dp).clip(CircleShape).background(Color(0xFF3B6CF6)))
    }
}
