package at.felworks.jon.ki

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder

object Podcast {
    private const val ZIELRATE = 24000

    private class Pcm(val rate: Int, val kanaele: Int, val daten: ByteArray)

    private fun lesen(datei: File): Pcm? {
        val roh = datei.readBytes()
        if (roh.size < 44 || String(roh, 0, 4) != "RIFF" || String(roh, 8, 4) != "WAVE") return null
        val puffer = ByteBuffer.wrap(roh).order(ByteOrder.LITTLE_ENDIAN)
        var pos = 12
        var rate = 22050
        var kanaele = 1
        var bits = 16
        while (pos + 8 <= roh.size) {
            val id = String(roh, pos, 4)
            val laenge = puffer.getInt(pos + 4)
            if (id == "fmt ") {
                kanaele = puffer.getShort(pos + 10).toInt()
                rate = puffer.getInt(pos + 12)
                bits = puffer.getShort(pos + 22).toInt()
            }
            if (id == "data") {
                if (bits != 16) return null
                val ende = minOf(roh.size, pos + 8 + laenge.coerceAtLeast(0))
                return Pcm(rate, kanaele, roh.copyOfRange(pos + 8, ende))
            }
            pos += 8 + laenge + (laenge and 1)
        }
        return null
    }

    private fun angleichen(pcm: Pcm): ByteArray {
        val proben = ByteBuffer.wrap(pcm.daten).order(ByteOrder.LITTLE_ENDIAN).asShortBuffer()
        val anzahl = proben.remaining() / pcm.kanaele.coerceAtLeast(1)
        val schritt = pcm.rate.toDouble() / ZIELRATE
        val ziel = ByteBuffer.allocate(((anzahl / schritt) + 2).toInt() * 2).order(ByteOrder.LITTLE_ENDIAN)
        var position = 0.0
        while (position < anzahl) {
            val i = position.toInt()
            var summe = 0
            for (k in 0 until pcm.kanaele) summe += proben.get(i * pcm.kanaele + k)
            ziel.putShort((summe / pcm.kanaele.coerceAtLeast(1)).toShort())
            position += schritt
        }
        return ziel.array().copyOf(ziel.position())
    }

    fun teile(args: JSONObject): List<Pair<Int, String>> {
        val ergebnis = mutableListOf<Pair<Int, String>>()
        args.optJSONArray("teile")?.let { liste ->
            for (i in 0 until liste.length()) {
                val t = liste.optJSONObject(i) ?: continue
                val text = t.optString("text").trim()
                if (text.isNotEmpty()) ergebnis += (if (t.optString("sprecher").lowercase() in setOf("b", "gast", "2")) 1 else 0) to text
            }
        }
        if (ergebnis.isEmpty()) args.optString("skript").lines().forEach { zeile ->
            val m = Regex("^\\s*(A|B|Jon|Gast)\\s*:\\s*(.+)$", RegexOption.IGNORE_CASE).find(zeile)
            when {
                m != null -> ergebnis += (if (m.groupValues[1].lowercase() in setOf("b", "gast")) 1 else 0) to m.groupValues[2].trim()
                zeile.isNotBlank() && ergebnis.isNotEmpty() -> ergebnis[ergebnis.lastIndex] = ergebnis.last().first to ergebnis.last().second + " " + zeile.trim()
                zeile.isNotBlank() -> ergebnis += 0 to zeile.trim()
            }
        }
        return ergebnis.take(80)
    }

    suspend fun erstellen(context: Context, args: JSONObject): JSONObject = withContext(Dispatchers.IO) {
        val teile = teile(args)
        require(teile.isNotEmpty()) { "Für den Podcast fehlt das Skript." }
        val titel = args.optString("titel").trim().ifBlank { "Podcast" }.take(60)
        val gesamt = ByteArrayOutputStream()
        val pause = ByteArray(ZIELRATE * 2 * 35 / 100)
        for ((sprecher, text) in teile) {
            val datei = LokaleStimme.datei(context, text, sprecher) ?: error("Die Handy-Stimme ist nicht bereit. Installiere unter Android eine deutsche Sprachausgabe.")
            try {
                val pcm = lesen(datei) ?: error("Die Sprachausgabe lieferte ein unbekanntes Format.")
                gesamt.write(angleichen(pcm))
                gesamt.write(pause)
            } finally { datei.delete() }
        }
        val daten = gesamt.toByteArray()
        val wav = ByteBuffer.allocate(44 + daten.size).order(ByteOrder.LITTLE_ENDIAN)
            .put("RIFF".toByteArray()).putInt(36 + daten.size).put("WAVEfmt ".toByteArray())
            .putInt(16).putShort(1).putShort(1).putInt(ZIELRATE).putInt(ZIELRATE * 2).putShort(2).putShort(16)
            .put("data".toByteArray()).putInt(daten.size).put(daten).array()
        val name = titel.replace(Regex("[^\\p{L}\\p{N}\\- ]"), "").trim().replace(' ', '-').ifBlank { "Podcast" }
        val ziel = Arbeitsraum.datei(context, "podcasts/$name-${System.currentTimeMillis() / 1000}.wav")
        ziel.parentFile?.mkdirs()
        ziel.writeBytes(wav)
        JSONObject().put("ok", true).put("pfad", Arbeitsraum.relativ(context, ziel)).put("sekunden", daten.size / (ZIELRATE * 2)).put("teile", teile.size)
            .put("karte", JSONObject().put("kind", "handy-datei").put("data", JSONObject().put("dateien", JSONArray().put(Arbeitsraum.eintrag(context, ziel)))))
    }
}
