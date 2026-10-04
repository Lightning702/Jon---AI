package at.felworks.jon.ki

import android.content.Context
import com.google.ai.edge.litertlm.Backend
import com.google.ai.edge.litertlm.Content
import com.google.ai.edge.litertlm.Contents
import com.google.ai.edge.litertlm.Conversation
import com.google.ai.edge.litertlm.ConversationConfig
import com.google.ai.edge.litertlm.Engine
import com.google.ai.edge.litertlm.EngineConfig
import com.google.ai.edge.litertlm.Message
import com.google.ai.edge.litertlm.OpenApiTool
import com.google.ai.edge.litertlm.SamplerConfig
import com.google.ai.edge.litertlm.ToolProvider
import com.google.ai.edge.litertlm.tool
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.channels.ProducerScope
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.channelFlow
import kotlinx.coroutines.flow.flowOn
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import org.json.JSONObject

object LokaleKi {
    private val sperre = Mutex()
    private var engine: Engine? = null
    @Volatile var geladen: String? = null
        private set
    @Volatile private var gespraech: Conversation? = null
    @Volatile private var geladenMitBild = false
    private val _zustand = MutableStateFlow(JSONObject().put("phase", "aus"))
    val zustand: StateFlow<JSONObject> = _zustand

    private fun melden(phase: String, m: KiModell? = null, backend: String = "", fehler: String = "") {
        _zustand.value = JSONObject().put("phase", phase).put("modell", m?.name ?: geladen ?: JSONObject.NULL)
            .put("titel", m?.titel ?: "").put("backend", backend).put("fehler", fehler)
    }

    private suspend fun laden(context: Context, m: KiModell): Engine = sperre.withLock {
        engine?.let { if (geladen == m.name) return@withLock it }
        runCatching { engine?.close() }
        engine = null
        geladen = null
        val datei = Katalog.datei(context, m)
        check(Katalog.vorhanden(context, m)) { "${m.titel} ist noch nicht heruntergeladen." }
        melden("laedt", m)
        val versuche = if (m.gpu) listOf("GPU", "CPU") else listOf("CPU")
        var letzter: Throwable? = null
        for (art in versuche) {
            val backend = if (art == "GPU") Backend.GPU() else Backend.CPU()
            val sehen = when {
                !m.bild -> null
                art == "GPU" -> Backend.GPU()
                else -> null
            }
            try {
                val neu = Engine(EngineConfig(modelPath = datei.absolutePath, backend = backend, visionBackend = sehen, maxNumTokens = m.maxTokens, maxNumImages = if (sehen != null) 8 else null, cacheDir = context.cacheDir.absolutePath))
                neu.initialize()
                engine = neu
                geladen = m.name
                geladenMitBild = sehen != null
                melden("bereit", m, art)
                return@withLock neu
            } catch (t: Throwable) {
                letzter = t
            }
        }
        melden("fehler", m, fehler = letzter?.message ?: "unbekannt")
        throw IllegalStateException("${m.titel} startet auf diesem Handy nicht: ${letzter?.message ?: "unbekannter Fehler"}")
    }

    suspend fun vorladen(context: Context, name: String) {
        val m = Katalog.modell(context, name) ?: return
        runCatching { laden(context, m) }
    }

    fun entladen() {
        runCatching { gespraech?.cancelProcess() }
        runCatching { engine?.close() }
        engine = null
        geladen = null
        melden("aus")
    }

    fun stoppen() {
        runCatching { gespraech?.cancelProcess() }
    }

    private fun werkzeugListe(context: Context, arbeit: Boolean, ausgabe: ProducerScope<JSONObject>): List<ToolProvider> =
        Werkzeuge.liste(context, arbeit, false).map { def ->
            tool(object : OpenApiTool {
                override fun getToolDescriptionJsonString(): String =
                    JSONObject().put("name", def.name).put("description", def.beschreibung).put("parameters", def.parameter).toString()

                override fun execute(paramsJsonString: String): String {
                    val args = runCatching { JSONObject(paramsJsonString) }.getOrDefault(JSONObject())
                    ausgabe.trySend(Werkzeuge.laeuft(def, args))
                    val ergebnis = runBlocking { Werkzeuge.ausfuehren(context, def.name, args) }
                    ausgabe.trySend(Werkzeuge.fertig(def.name, ergebnis))
                    return ergebnis.toString()
                }
            })
        }

    fun antworten(
        context: Context,
        name: String,
        system: String,
        verlauf: List<Pair<String, String>>,
        text: String,
        bilder: List<ByteArray>,
        arbeit: Boolean,
    ): Flow<JSONObject> = channelFlow {
        val m = Katalog.modell(context, name) ?: error("Dieses Offline-Modell kennt Jon nicht.")
        send(JSONObject().put("type", "meta").put("provider", "handy").put("model", m.name))
        val aktiv = laden(context, m)
        val budget = ((m.maxTokens - 640).coerceAtLeast(400) * 3 - system.length).coerceAtLeast(1200)
        val frage = MedienAnalyse.kuerzen(text, budget * 3 / 5)
        var frei = budget - frage.length
        val bisher = ArrayDeque<Message>()
        for ((rolle, inhalt) in verlauf.takeLast(16).asReversed()) {
            if (frei < 240) break
            val stueck = MedienAnalyse.kuerzen(inhalt, minOf(frei, 2400))
            frei -= stueck.length
            bisher.addFirst(if (rolle == "user") Message.user(stueck) else Message.model(stueck))
        }
        val konfiguration = ConversationConfig(
            systemInstruction = Contents.of(system),
            initialMessages = bisher.toList(),
            tools = if (m.werkzeuge) werkzeugListe(context, arbeit, this) else emptyList(),
            samplerConfig = SamplerConfig(m.topK, m.topP, m.temperatur),
        )
        val neu = sperre.withLock { aktiv.createConversation(konfiguration) }
        gespraech = neu
        melden("antwortet", m)
        var denkt = false
        try {
            val teile = mutableListOf<Content>()
            if (m.bild && geladenMitBild) bilder.take(8).forEach { teile += Content.ImageBytes(it) }
            else if (bilder.isNotEmpty()) send(JSONObject().put("type", "content").put("delta", "(Dieses Offline-Modell kann keine Bilder ansehen. Ich antworte nur auf deinen Text.)\n\n"))
            teile += Content.Text(frage)
            neu.sendMessageAsync(Contents.of(teile)).collect { nachricht ->
                nachricht.channels["thought"]?.takeIf { it.isNotEmpty() }?.let { send(JSONObject().put("type", "reasoning").put("delta", it)) }
                var stueck = nachricht.toString()
                while (stueck.isNotEmpty()) {
                    if (denkt) {
                        val ende = stueck.indexOf("</think>")
                        if (ende < 0) {
                            send(JSONObject().put("type", "reasoning").put("delta", stueck))
                            stueck = ""
                        } else {
                            if (ende > 0) send(JSONObject().put("type", "reasoning").put("delta", stueck.substring(0, ende)))
                            stueck = stueck.substring(ende + 8)
                            denkt = false
                        }
                    } else {
                        val anfang = stueck.indexOf("<think>")
                        if (anfang < 0) {
                            send(JSONObject().put("type", "content").put("delta", stueck))
                            stueck = ""
                        } else {
                            if (anfang > 0) send(JSONObject().put("type", "content").put("delta", stueck.substring(0, anfang)))
                            stueck = stueck.substring(anfang + 7)
                            denkt = true
                        }
                    }
                }
            }
        } finally {
            gespraech = null
            runCatching { neu.close() }
            if (geladen != null) melden("bereit", m)
        }
    }.flowOn(Dispatchers.IO)
}
