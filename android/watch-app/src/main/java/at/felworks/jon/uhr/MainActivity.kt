package at.felworks.jon.uhr

import android.Manifest
import android.app.RemoteInput
import android.content.ActivityNotFoundException
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.speech.RecognizerIntent
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.MutableState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.wear.compose.foundation.lazy.ScalingLazyColumn
import androidx.wear.compose.foundation.lazy.rememberScalingLazyListState
import androidx.wear.compose.material.Chip
import androidx.wear.compose.material.ChipDefaults
import androidx.wear.compose.material.MaterialTheme
import androidx.wear.compose.material.Scaffold
import androidx.wear.compose.material.Text
import androidx.wear.compose.material.TimeText
import androidx.wear.input.RemoteInputIntentHelper
import kotlinx.coroutines.launch
import java.util.Locale

private val Gold = Color(0xFFE2BD4C)
private val GoldHell = Color(0xFFEEC657)
private val Gedaempft = Color(0xFF9A9AA6)

private enum class Phase { BEREIT, DENKT, ANTWORT, FEHLER, KOPPELT }

class MainActivity : ComponentActivity() {
    private val aktion = mutableStateOf<String?>(null)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        Stimme.starten(this)
        aktion.value = intent?.getStringExtra("aktion") ?: if (savedInstanceState == null) "start" else null
        setContent { JonUhr(aktion) }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        aktion.value = intent.getStringExtra("aktion") ?: "start"
    }
}

@Composable
private fun JonUhr(aktion: MutableState<String?>) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var zugang by remember { mutableStateOf(Tresor(context).zugang()) }
    var phase by remember { mutableStateOf(Phase.BEREIT) }
    var frage by remember { mutableStateOf("") }
    var antwort by remember { mutableStateOf("") }
    var meldung by remember { mutableStateOf("") }
    var vorlesen by remember { mutableStateOf(Stimme.an(context)) }
    var gespraech by remember { mutableStateOf("") }
    val verlauf = remember { mutableStateListOf<Pair<String, String>>() }
    val liste = rememberScalingLazyListState()

    DisposableEffect(Unit) {
        val weg = Zustand.beobachten {
            zugang = Tresor(context).zugang()
            if (zugang != null && phase == Phase.KOPPELT) phase = Phase.BEREIT
        }
        onDispose { weg() }
    }

    val benachrichtigung = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { }

    fun fragen(text: String) {
        frage = text
        antwort = ""
        meldung = ""
        phase = Phase.DENKT
        scope.launch {
            runCatching { Jon.fragen(context, text, verlauf.toList(), gespraech) }
                .onSuccess { ergebnis ->
                    antwort = ergebnis.optString("antwort")
                    gespraech = ergebnis.optString("gespraech", gespraech)
                    verlauf += "user" to text
                    verlauf += "assistant" to antwort
                    phase = Phase.ANTWORT
                    Aufgaben.vibrieren(context, longArrayOf(0, 50))
                    if (vorlesen) Stimme.sprechen(antwort)
                }
                .onFailure {
                    meldung = it.message ?: "Jon ist gerade nicht erreichbar."
                    phase = Phase.FEHLER
                }
        }
    }

    val eingabe = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { ergebnis ->
        val daten = ergebnis.data
        val text = daten?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)?.firstOrNull()
            ?: daten?.let { RemoteInput.getResultsFromIntent(it)?.getCharSequence("frage")?.toString() }
        if (!text.isNullOrBlank()) fragen(text.trim())
    }

    fun koppeln(weg: suspend () -> String) {
        phase = Phase.KOPPELT
        meldung = "Verbinde mit Jon …"
        scope.launch {
            runCatching { weg() }
                .onSuccess { name ->
                    zugang = Tresor(context).zugang()
                    meldung = "Verbunden mit $name"
                    phase = Phase.BEREIT
                    Aufgaben.vibrieren(context, longArrayOf(0, 80, 80, 80))
                    if (Build.VERSION.SDK_INT >= 33 && context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                        benachrichtigung.launch(Manifest.permission.POST_NOTIFICATIONS)
                    }
                }
                .onFailure {
                    meldung = it.message ?: "Die Kopplung hat nicht geklappt."
                    phase = Phase.FEHLER
                }
        }
    }

    val codeEingabe = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { ergebnis ->
        val code = ergebnis.data?.let { RemoteInput.getResultsFromIntent(it)?.getCharSequence("code")?.toString() }
        if (!code.isNullOrBlank()) koppeln { Jon.koppeln(context, code, emptyList(), "") }
    }

    fun texteingabe(schluessel: String, beschriftung: String): Intent {
        val intent = RemoteInputIntentHelper.createActionRemoteInputIntent()
        RemoteInputIntentHelper.putRemoteInputsExtra(intent, listOf(RemoteInput.Builder(schluessel).setLabel(beschriftung).build()))
        return intent
    }

    fun tippen() {
        runCatching { eingabe.launch(texteingabe("frage", "Frag Jon")) }.onFailure { meldung = "Auf dieser Uhr gibt es keine Texteingabe." }
    }

    fun hoeren() {
        Stimme.stopp()
        meldung = ""
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            .putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            .putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault().toLanguageTag())
            .putExtra(RecognizerIntent.EXTRA_PROMPT, "Frag Jon")
        try {
            eingabe.launch(intent)
        } catch (_: ActivityNotFoundException) {
            tippen()
        }
    }

    fun klingeln() {
        meldung = "Suche dein Handy …"
        scope.launch {
            meldung = runCatching { Jon.handyKlingeln(context) }.getOrElse { it.message ?: "Das Handy hat nicht reagiert." }
        }
    }

    LaunchedEffect(aktion.value) {
        val wunsch = aktion.value ?: return@LaunchedEffect
        aktion.value = null
        when (wunsch) {
            "start", "sprechen" -> if (zugang != null) hoeren()
            "klingeln" -> klingeln()
            "stopp" -> Aufgaben.stoppen(context)
        }
    }

    MaterialTheme {
        Scaffold(timeText = { TimeText() }) {
            ScalingLazyColumn(
                modifier = Modifier.fillMaxSize().background(Color.Black),
                state = liste,
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                if (zugang == null) {
                    item { JonGesicht(groesse = 64.dp, denkt = phase == Phase.KOPPELT) }
                    item {
                        Text(
                            "Verbinde deine Uhr mit Jon",
                            textAlign = TextAlign.Center,
                            fontWeight = FontWeight.SemiBold,
                            modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
                        )
                    }
                    item {
                        Chip(
                            label = { Text("Über das Handy koppeln") },
                            onClick = { koppeln { Jon.ueberHandyKoppeln(context) } },
                            colors = ChipDefaults.primaryChipColors(backgroundColor = Gold, contentColor = Color.Black),
                            modifier = Modifier.fillMaxWidth(),
                        )
                    }
                    item {
                        Chip(
                            label = { Text("Code eingeben") },
                            onClick = { runCatching { codeEingabe.launch(texteingabe("code", "Kopplungscode")) } },
                            colors = ChipDefaults.secondaryChipColors(),
                            modifier = Modifier.fillMaxWidth(),
                        )
                    }
                    if (meldung.isNotBlank()) item { Hinweis(meldung, phase == Phase.FEHLER) }
                } else {
                    item { JonGesicht(groesse = 92.dp, denkt = phase == Phase.DENKT, onClick = { hoeren() }) }
                    item {
                        Text(
                            when (phase) {
                                Phase.DENKT -> "Jon denkt …"
                                Phase.ANTWORT -> "Jon"
                                Phase.FEHLER -> "Das hat nicht geklappt"
                                else -> "Tippen und sprechen"
                            },
                            color = if (phase == Phase.ANTWORT) Gold else Color.White,
                            fontWeight = FontWeight.SemiBold,
                            textAlign = TextAlign.Center,
                            modifier = Modifier.padding(top = 4.dp),
                        )
                    }
                    if (frage.isNotBlank() && (phase == Phase.DENKT || phase == Phase.ANTWORT)) {
                        item {
                            Text("„$frage“", color = Gedaempft, fontSize = 12.sp, textAlign = TextAlign.Center, modifier = Modifier.padding(horizontal = 14.dp, vertical = 4.dp))
                        }
                    }
                    if (phase == Phase.ANTWORT && antwort.isNotBlank()) {
                        item {
                            Text(Stimme.sauber(antwort), fontSize = 14.sp, textAlign = TextAlign.Start, modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp))
                        }
                    }
                    if (meldung.isNotBlank()) item { Hinweis(meldung, phase == Phase.FEHLER) }
                    if (phase == Phase.ANTWORT || phase == Phase.FEHLER) {
                        item {
                            Chip(
                                label = { Text(if (phase == Phase.ANTWORT) "Weiter fragen" else "Nochmal versuchen") },
                                onClick = { hoeren() },
                                colors = ChipDefaults.primaryChipColors(backgroundColor = Gold, contentColor = Color.Black),
                                modifier = Modifier.fillMaxWidth(),
                            )
                        }
                    }
                    item { Chip(label = { Text("Handy klingeln lassen") }, onClick = { klingeln() }, colors = ChipDefaults.secondaryChipColors(), modifier = Modifier.fillMaxWidth()) }
                    item { Chip(label = { Text("Frage tippen") }, onClick = { tippen() }, colors = ChipDefaults.secondaryChipColors(), modifier = Modifier.fillMaxWidth()) }
                    item {
                        Chip(
                            label = { Text(if (vorlesen) "Vorlesen: an" else "Vorlesen: aus") },
                            onClick = { vorlesen = !vorlesen; Stimme.setzen(context, vorlesen) },
                            colors = ChipDefaults.secondaryChipColors(),
                            modifier = Modifier.fillMaxWidth(),
                        )
                    }
                    if (verlauf.isNotEmpty()) {
                        item {
                            Chip(
                                label = { Text("Neues Gespräch") },
                                onClick = { verlauf.clear(); gespraech = ""; frage = ""; antwort = ""; meldung = ""; phase = Phase.BEREIT; Stimme.stopp() },
                                colors = ChipDefaults.secondaryChipColors(),
                                modifier = Modifier.fillMaxWidth(),
                            )
                        }
                    }
                    item {
                        Text("Verbunden mit ${zugang?.pcName?.ifBlank { "Jon" } ?: "Jon"}", color = Gedaempft, fontSize = 11.sp, textAlign = TextAlign.Center, modifier = Modifier.padding(top = 6.dp, bottom = 18.dp))
                    }
                }
            }
        }
    }
}

@Composable
private fun Hinweis(text: String, fehler: Boolean) {
    Text(
        text,
        color = if (fehler) Color(0xFFFF8A80) else Gedaempft,
        fontSize = 12.sp,
        textAlign = TextAlign.Center,
        modifier = Modifier.padding(horizontal = 14.dp, vertical = 6.dp),
    )
}

@Composable
private fun JonGesicht(groesse: Dp, denkt: Boolean, onClick: (() -> Unit)? = null) {
    val puls = rememberInfiniteTransition(label = "puls")
    val wert by puls.animateFloat(
        initialValue = 0f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(1100, easing = FastOutSlowInEasing), RepeatMode.Reverse),
        label = "wert",
    )
    val skala = if (denkt) 1f + wert * 0.07f else 1f
    val tippbar = if (onClick != null) Modifier.clip(CircleShape).clickable(onClick = onClick) else Modifier
    Canvas(modifier = Modifier.size(groesse).graphicsLayer { scaleX = skala; scaleY = skala }.then(tippbar)) {
        val r = size.minDimension / 2
        if (denkt) drawCircle(Gold.copy(alpha = 0.35f * (1f - wert)), r, style = Stroke(width = r * 0.06f))
        drawCircle(Color(0xFF0B0B0E), r * 0.86f)
        drawCircle(Gold, r * 0.86f, style = Stroke(width = r * 0.11f))
        val augeY = center.y - r * 0.12f
        drawCircle(GoldHell, r * 0.13f, Offset(center.x - r * 0.26f, augeY))
        drawCircle(GoldHell, r * 0.13f, Offset(center.x + r * 0.26f, augeY))
        drawCircle(Color.White, r * 0.04f, Offset(center.x - r * 0.215f, augeY - r * 0.045f))
        drawCircle(Color.White, r * 0.04f, Offset(center.x + r * 0.305f, augeY - r * 0.045f))
        val mund = Path().apply {
            moveTo(center.x - r * 0.3f, center.y + r * 0.2f)
            quadraticTo(center.x, center.y + (if (denkt) 0.42f else 0.5f) * r, center.x + r * 0.3f, center.y + r * 0.2f)
        }
        drawPath(mund, Gold, style = Stroke(width = r * 0.11f, cap = StrokeCap.Round))
    }
}
