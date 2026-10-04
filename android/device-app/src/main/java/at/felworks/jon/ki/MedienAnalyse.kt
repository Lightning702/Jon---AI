package at.felworks.jon.ki

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Color
import android.graphics.pdf.PdfRenderer
import android.media.MediaCodec
import android.media.MediaExtractor
import android.media.MediaFormat
import android.media.MediaMetadataRetriever
import android.net.Uri
import android.os.Build
import android.os.ParcelFileDescriptor
import android.provider.OpenableColumns
import at.felworks.jon.core.AppBehaelter
import at.felworks.jon.data.remote.Krypto
import at.felworks.jon.device.Fotos
import at.felworks.jon.device.VoskModell
import at.felworks.jon.domain.model.Draht
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.sync.Semaphore
import kotlinx.coroutines.sync.withPermit
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.RandomAccessFile
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.concurrent.atomic.AtomicInteger
import kotlin.math.sqrt

object MedienAnalyse {
    private const val RATE = 16000
    private const val ANHANG_ZEICHEN = 28_000
    private const val STILLE = 90.0
    private val textEndungen = setOf("txt", "md", "csv", "json", "html", "htm", "css", "js", "py", "xml", "yml", "yaml", "log", "kt", "java", "ts", "tsx", "srt", "vtt", "ini")
    private val audioEndungen = setOf("mp3", "m4a", "aac", "wav", "ogg", "opus", "flac", "amr", "3gp", "weba", "mka")

    fun art(mime: String, name: String): String {
        val endung = name.substringAfterLast('.', "").lowercase()
        return when {
            mime.startsWith("image/") -> "bild"
            mime.startsWith("video/") -> "video"
            mime.startsWith("audio/") || endung in audioEndungen -> "audio"
            mime == "application/pdf" || endung == "pdf" -> "pdf"
            mime.startsWith("text/") || endung in textEndungen -> "text"
            else -> "datei"
        }
    }

    private fun sauber(name: String): String = name.replace(Regex("[\\\\/:*?\"<>|\\x00-\\x1f]"), "_").trim().take(120).ifBlank { "Datei" }

    suspend fun kopieren(context: Context, uri: Uri): Triple<File, String, String> = withContext(Dispatchers.IO) {
        val resolver = context.contentResolver
        var name = "Datei"
        var groesse = -1L
        resolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME, OpenableColumns.SIZE), null, null, null)?.use { z ->
            if (z.moveToFirst()) {
                name = z.getString(0) ?: name
                groesse = if (z.isNull(1)) -1L else z.getLong(1)
            }
        }
        check(groesse <= 500_000_000L) { "Die Datei ist größer als 500 MB." }
        val mime = resolver.getType(uri) ?: "application/octet-stream"
        val ordner = File(context.cacheDir, "hochladen").apply { mkdirs() }
        ordner.listFiles()?.filter { System.currentTimeMillis() - it.lastModified() > 3_600_000 }?.forEach { it.delete() }
        val ziel = File(ordner, "${System.currentTimeMillis()}-${sauber(name)}")
        resolver.openInputStream(uri)?.use { eingabe -> ziel.outputStream().use { eingabe.copyTo(it) } } ?: error("Die Datei lässt sich nicht öffnen.")
        check(ziel.length() <= 500_000_000L) { "Die Datei ist größer als 500 MB." }
        Triple(ziel, sauber(name), mime)
    }

    fun bildJpeg(datei: File, kante: Int = 1600): ByteArray {
        val grenzen = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeFile(datei.absolutePath, grenzen)
        var stufe = 1
        while (maxOf(grenzen.outWidth, grenzen.outHeight) / (stufe * 2) >= kante) stufe *= 2
        val bild = BitmapFactory.decodeFile(datei.absolutePath, BitmapFactory.Options().apply { inSampleSize = stufe }) ?: error("Das Bild lässt sich nicht lesen.")
        val grad = runCatching {
            when (android.media.ExifInterface(datei.absolutePath).getAttributeInt(android.media.ExifInterface.TAG_ORIENTATION, 1)) {
                6 -> 90; 3 -> 180; 8 -> 270; else -> 0
            }
        }.getOrDefault(0)
        return Fotos.jpeg(Fotos.verkleinern(Fotos.drehen(bild, grad), kante), 84)
    }

    fun videoBilder(context: Context, datei: File, anzahl: Int = 6): Pair<List<ByteArray>, Double> {
        val leser = MediaMetadataRetriever()
        try {
            leser.setDataSource(datei.absolutePath)
            val dauer = leser.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)?.toLongOrNull() ?: 0L
            val bilder = (1..anzahl).mapNotNull { i ->
                val zeit = dauer * 1000L * i / (anzahl + 1)
                val bild = if (Build.VERSION.SDK_INT >= 27) leser.getScaledFrameAtTime(zeit, MediaMetadataRetriever.OPTION_CLOSEST_SYNC, 768, 768)
                else leser.getFrameAtTime(zeit, MediaMetadataRetriever.OPTION_CLOSEST_SYNC)
                bild?.let { Fotos.jpeg(Fotos.verkleinern(it, 768), 78) }
            }
            return bilder to dauer / 1000.0
        } finally { runCatching { leser.release() } }
    }

    fun pdfBilder(datei: File, seiten: Int = 4): Pair<List<ByteArray>, Int> {
        ParcelFileDescriptor.open(datei, ParcelFileDescriptor.MODE_READ_ONLY).use { fd ->
            PdfRenderer(fd).use { pdf ->
                val bilder = (0 until minOf(seiten, pdf.pageCount)).map { i ->
                    pdf.openPage(i).use { seite ->
                        val faktor = 1400f / maxOf(seite.width, seite.height)
                        val bild = Bitmap.createBitmap((seite.width * faktor).toInt().coerceAtLeast(1), (seite.height * faktor).toInt().coerceAtLeast(1), Bitmap.Config.ARGB_8888)
                        bild.eraseColor(Color.WHITE)
                        seite.render(bild, null, null, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
                        Fotos.jpeg(bild, 82)
                    }
                }
                return bilder to pdf.pageCount
            }
        }
    }

    fun kuerzen(text: String, grenze: Int): String {
        if (text.length <= grenze) return text
        val marke = "\n\n[… Mitte gekürzt, ${text.length - grenze} Zeichen ausgelassen …]\n\n"
        val rest = (grenze - marke.length).coerceAtLeast(400)
        return text.take(rest * 2 / 3) + marke + text.takeLast(rest - rest * 2 / 3)
    }

    fun pcm(datei: File, ziel: File, maxSekunden: Int = 3600): Long {
        val extraktor = MediaExtractor()
        extraktor.setDataSource(datei.absolutePath)
        val spur = (0 until extraktor.trackCount).firstOrNull { extraktor.getTrackFormat(it).getString(MediaFormat.KEY_MIME)?.startsWith("audio/") == true }
            ?: run { extraktor.release(); error("In dieser Datei gibt es keine Tonspur.") }
        extraktor.selectTrack(spur)
        val format = extraktor.getTrackFormat(spur)
        val dekoder = MediaCodec.createDecoderByType(format.getString(MediaFormat.KEY_MIME)!!)
        val aus = ziel.outputStream().buffered(1 shl 16)
        var geschrieben = 0L
        val grenze = RATE.toLong() * 2 * maxSekunden
        try {
            dekoder.configure(format, null, null, 0)
            dekoder.start()
            val info = MediaCodec.BufferInfo()
            var eingabeFertig = false
            var rate = format.getInteger(MediaFormat.KEY_SAMPLE_RATE)
            var kanaele = format.getInteger(MediaFormat.KEY_CHANNEL_COUNT)
            var position = 0.0
            while (geschrieben < grenze) {
                if (!eingabeFertig) {
                    val index = dekoder.dequeueInputBuffer(10_000)
                    if (index >= 0) {
                        val puffer = dekoder.getInputBuffer(index)!!
                        val n = extraktor.readSampleData(puffer, 0)
                        if (n < 0) {
                            dekoder.queueInputBuffer(index, 0, 0, 0, MediaCodec.BUFFER_FLAG_END_OF_STREAM)
                            eingabeFertig = true
                        } else {
                            dekoder.queueInputBuffer(index, 0, n, extraktor.sampleTime, 0)
                            extraktor.advance()
                        }
                    }
                }
                val ausIndex = dekoder.dequeueOutputBuffer(info, 10_000)
                when {
                    ausIndex == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED -> {
                        rate = dekoder.outputFormat.getInteger(MediaFormat.KEY_SAMPLE_RATE)
                        kanaele = dekoder.outputFormat.getInteger(MediaFormat.KEY_CHANNEL_COUNT)
                    }
                    ausIndex >= 0 -> {
                        val puffer = dekoder.getOutputBuffer(ausIndex)!!
                        puffer.position(info.offset)
                        puffer.limit(info.offset + info.size)
                        val proben = puffer.order(ByteOrder.LITTLE_ENDIAN).asShortBuffer()
                        val anzahl = proben.remaining() / kanaele.coerceAtLeast(1)
                        val mono = ShortArray(anzahl) { i ->
                            var summe = 0
                            for (k in 0 until kanaele) summe += proben.get(i * kanaele + k)
                            (summe / kanaele.coerceAtLeast(1)).toShort()
                        }
                        val schritt = rate.toDouble() / RATE
                        val bytes = ByteBuffer.allocate((anzahl / schritt + 2).toInt() * 2).order(ByteOrder.LITTLE_ENDIAN)
                        while (position < anzahl) {
                            bytes.putShort(mono[position.toInt().coerceAtMost(anzahl - 1)])
                            position += schritt
                        }
                        position -= anzahl
                        aus.write(bytes.array(), 0, bytes.position())
                        geschrieben += bytes.position()
                        dekoder.releaseOutputBuffer(ausIndex, false)
                        if (info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM != 0) break
                    }
                }
            }
        } finally {
            runCatching { aus.close() }
            runCatching { dekoder.stop() }
            runCatching { dekoder.release() }
            runCatching { extraktor.release() }
        }
        return geschrieben
    }

    private fun lesen(datei: File, start: Long, laenge: Int): ByteArray = RandomAccessFile(datei, "r").use { r ->
        val n = minOf(laenge.toLong(), (r.length() - start).coerceAtLeast(0)).toInt()
        ByteArray(n).also { r.seek(start); r.readFully(it) }
    }

    private fun still(pcm: ByteArray): Boolean {
        val proben = ByteBuffer.wrap(pcm).order(ByteOrder.LITTLE_ENDIAN).asShortBuffer()
        var summe = 0.0
        var anzahl = 0
        var i = 0
        while (i < proben.limit()) {
            val wert = proben.get(i).toDouble()
            summe += wert * wert
            anzahl++
            i += 4
        }
        return anzahl == 0 || sqrt(summe / anzahl) < STILLE
    }

    fun wav(pcm: ByteArray, rate: Int = RATE): ByteArray = ByteBuffer.allocate(44 + pcm.size).order(ByteOrder.LITTLE_ENDIAN)
        .put("RIFF".toByteArray()).putInt(36 + pcm.size).put("WAVEfmt ".toByteArray())
        .putInt(16).putShort(1).putShort(1).putInt(rate).putInt(rate * 2).putShort(2).putShort(16)
        .put("data".toByteArray()).putInt(pcm.size).put(pcm).array()

    suspend fun transkript(context: Context, behaelter: AppBehaelter, weg: Weg, pcm: File, melden: (String) -> Unit): String {
        val groesse = pcm.length()
        if (groesse < RATE) return ""
        if (weg == Weg.SOLO) {
            val laenge = RATE * 2 * 600
            val anzahl = ((groesse + laenge - 1) / laenge).toInt()
            val texte = mutableListOf<String>()
            for (i in 0 until anzahl) {
                melden("Wandle Sprache in Text um … ${i + 1}/$anzahl")
                val stueck = withContext(Dispatchers.IO) { lesen(pcm, i.toLong() * laenge, laenge) }
                texte += Solo.transkribieren(context, wav(stueck)) ?: break
            }
            if (texte.size == anzahl) return texte.joinToString(" ")
        }
        if (weg == Weg.PI && behaelter.gekoppelt.value && behaelter.verbindung.lage.value.draht != Draht.AUS) {
            val laenge = RATE * 2 * 28
            val anzahl = ((groesse + laenge - 1) / laenge).toInt()
            val fertig = AtomicInteger(0)
            val gleichzeitig = Semaphore(2)
            melden("Jon hört zu … 0 %")
            val texte = runCatching {
                coroutineScope {
                    (0 until anzahl).map { i ->
                        async {
                            gleichzeitig.withPermit {
                                val stueck = withContext(Dispatchers.IO) { lesen(pcm, i.toLong() * laenge, laenge) }
                                val text = if (still(stueck)) "" else behaelter.verbindung.geraeteOperation(JSONObject().put("op", "audio-stt").put("audio", Krypto.b64(wav(stueck))), 90_000).optString("text").trim()
                                melden("Jon hört zu … ${fertig.incrementAndGet() * 100 / anzahl} %")
                                text
                            }
                        }
                    }.awaitAll()
                }
            }
            texte.getOrNull()?.let { liste -> return liste.filter { it.isNotBlank() }.joinToString(" ") }
            texte.exceptionOrNull()?.let { if (it is kotlinx.coroutines.CancellationException) throw it }
        }
        if (!at.felworks.jon.device.VoskModell.vorhanden(context)) {
            at.felworks.jon.device.VoskModell.anstossen(context)
            error("Für die Offline-Abschrift lädt Jon gerade das Sprachmodell (45 MB). Versuch es gleich nochmal.")
        }
        melden("Wandle Sprache offline in Text um …")
        return withContext(Dispatchers.Default) { VoskModell.transkribieren(context, pcm) { anteil -> melden("Offline-Transkript … ${(anteil * 100).toInt()} %") } }
    }

    suspend fun piHochladen(behaelter: AppBehaelter, datei: File, name: String, mime: String, melden: (String) -> Unit): String {
        val start = behaelter.verbindung.geraeteOperation(JSONObject().put("op", "datei-start").put("name", name).put("groesse", datei.length()).put("art", mime), 30_000)
        val kennung = start.getString("id")
        val teil = start.optInt("teilgroesse", 262_144).coerceIn(32_768, 262_144)
        var nummer = 0
        var gesendet = 0L
        datei.inputStream().buffered().use { eingabe ->
            val puffer = ByteArray(teil)
            while (true) {
                var n = 0
                while (n < teil) {
                    val gelesen = eingabe.read(puffer, n, teil - n)
                    if (gelesen < 0) break
                    n += gelesen
                }
                if (n <= 0) break
                behaelter.verbindung.geraeteOperation(JSONObject().put("op", "datei-teil").put("id", kennung).put("nr", nummer).put("daten", Krypto.b64(puffer.copyOf(n))), 60_000)
                nummer++
                gesendet += n
                melden("Lade auf den Pi … ${gesendet * 100 / datei.length().coerceAtLeast(1)} %")
                if (n < teil) break
            }
        }
        val ende = behaelter.verbindung.geraeteOperation(JSONObject().put("op", "datei-ende").put("id", kennung).put("teile", nummer), 180_000)
        return ende.getString("pfad")
    }

    private suspend fun piBeschreiben(behaelter: AppBehaelter, jpeg: ByteArray, name: String): String = runCatching {
        behaelter.verbindung.objekt("POST", "/api/attachments/extract", JSONObject().put("name", name).put("mime", "image/jpeg").put("data", android.util.Base64.encodeToString(jpeg, android.util.Base64.NO_WRAP)))
            .let { it.optString("content").ifBlank { it.optString("text") } }
    }.getOrDefault("")

    suspend fun verarbeiten(context: Context, behaelter: AppBehaelter, uri: Uri, ziel: String, weg: Weg, melden: (String) -> Unit): JSONObject {
        melden("Datei wird geöffnet …")
        val (datei, name, mime) = kopieren(context, uri)
        return auswerten(context, behaelter, datei, name, mime, ziel, weg, melden)
    }

    suspend fun auswerten(context: Context, behaelter: AppBehaelter, datei: File, name: String, mime: String, ziel: String, weg: Weg, melden: (String) -> Unit): JSONObject {
        try {
            val art = art(mime, name)
            val ergebnis = JSONObject().put("name", name).put("mime", mime).put("groesse", datei.length()).put("art", art)
            val verbunden = behaelter.gekoppelt.value && behaelter.verbindung.lage.value.draht != Draht.AUS
            if (ziel == "pi") {
                check(verbunden) { "Der Pi ist gerade nicht erreichbar. Wähle „Auf dem Handy behalten“." }
                ergebnis.put("pfad_pi", piHochladen(behaelter, datei, name, mime, melden))
            } else {
                val lokal = Arbeitsraum.datei(context, "uploads/$name").let { z -> if (z.exists()) Arbeitsraum.datei(context, "uploads/${System.currentTimeMillis()}-$name") else z }
                lokal.parentFile?.mkdirs()
                datei.copyTo(lokal, overwrite = true)
                ergebnis.put("pfad_handy", Arbeitsraum.relativ(context, lokal))
            }
            val bilder = JSONArray()
            val teile = mutableListOf<String>()
            when (art) {
                "bild" -> {
                    melden("Schaue mir das Bild an …")
                    val jpeg = withContext(Dispatchers.Default) { bildJpeg(datei) }
                    ergebnis.put("vorschau", Fotos.base64(jpeg))
                    if (weg == Weg.PI) piBeschreiben(behaelter, jpeg, name).takeIf { it.isNotBlank() }?.let { teile += "Beschreibung des Bildes:\n$it" }
                    else bilder.put(Fotos.base64(jpeg))
                }
                "video" -> {
                    melden("Schaue mir das Video an …")
                    val (szenen, dauer) = withContext(Dispatchers.Default) { videoBilder(context, datei) }
                    ergebnis.put("dauer", dauer)
                    szenen.firstOrNull()?.let { ergebnis.put("vorschau", Fotos.base64(it)) }
                    teile += "Video, Länge ${dauer.toInt() / 60}:${"%02d".format(dauer.toInt() % 60)} Minuten."
                    if (weg == Weg.PI) {
                        val beschreibungen = szenen.filterIndexed { i, _ -> i % 2 == 0 }.mapIndexedNotNull { i, bild ->
                            melden("Beschreibe Szene ${i + 1} …")
                            piBeschreiben(behaelter, bild, "szene-${i + 1}.jpg").takeIf { it.isNotBlank() }?.let { "Szene ${i + 1}: $it" }
                        }
                        if (beschreibungen.isNotEmpty()) teile += "Was im Video zu sehen ist:\n" + beschreibungen.joinToString("\n")
                    } else szenen.forEach { bilder.put(Fotos.base64(it)) }
                    val ton = File(datei.parentFile, datei.name + ".pcm")
                    try {
                        if (runCatching { withContext(Dispatchers.Default) { pcm(datei, ton, 3600) } }.isSuccess) {
                            val text = transkript(context, behaelter, weg, ton, melden)
                            if (text.isNotBlank()) {
                                ergebnis.put("transkript", text)
                                teile += "Gesprochener Text im Video:\n$text"
                            }
                        }
                    } finally { ton.delete() }
                }
                "audio" -> {
                    melden("Höre mir die Aufnahme an …")
                    val ton = File(datei.parentFile, datei.name + ".pcm")
                    try {
                        val laenge = withContext(Dispatchers.Default) { pcm(datei, ton, 3600) }
                        ergebnis.put("dauer", laenge / (RATE * 2.0))
                        val text = transkript(context, behaelter, weg, ton, melden)
                        ergebnis.put("transkript", text)
                        teile += if (text.isNotBlank()) "Transkript:\n$text" else "In der Aufnahme wurde keine Sprache erkannt."
                    } finally { ton.delete() }
                }
                "pdf" -> {
                    val (seiten, anzahl) = withContext(Dispatchers.Default) { pdfBilder(datei) }
                    ergebnis.put("seiten", anzahl)
                    seiten.firstOrNull()?.let { ergebnis.put("vorschau", Fotos.base64(it)) }
                    if (weg != Weg.PI) seiten.forEach { bilder.put(Fotos.base64(it)) }
                    teile += "PDF mit $anzahl Seiten." + if (weg != Weg.PI && anzahl > seiten.size) " Du siehst die ersten ${seiten.size} Seiten als Bilder." else ""
                }
                "text" -> {
                    val inhalt = datei.readText().take(60_000)
                    teile += "Inhalt:\n$inhalt"
                }
            }
            val anhang = buildString {
                append("Datei: ").append(name)
                ergebnis.optString("pfad_pi").takeIf { it.isNotBlank() }?.let { append("\nPfad auf dem Pi: ").append(it) }
                ergebnis.optString("pfad_handy").takeIf { it.isNotBlank() }?.let { append("\nPfad auf dem Handy: ").append(it) }
                teile.forEach { append("\n").append(it) }
            }
            return ergebnis.put("anhang", kuerzen(anhang, ANHANG_ZEICHEN)).put("bilder", bilder)
        } finally {
            datei.delete()
        }
    }
}
