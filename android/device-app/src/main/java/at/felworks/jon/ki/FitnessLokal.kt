package at.felworks.jon.ki

import android.content.Context
import at.felworks.jon.data.remote.Krypto
import at.felworks.jon.device.Schritte
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.time.LocalDate
import java.time.format.DateTimeFormatter

object FitnessLokal {
    val arten = listOf("gym", "laufen", "rad", "schwimmen", "yoga", "wandern", "sonstiges")
    private val artNamen = mapOf("gym" to "Gym", "laufen" to "Laufen", "rad" to "Radfahren", "schwimmen" to "Schwimmen", "yoga" to "Yoga", "wandern" to "Wandern", "sonstiges" to "Training")
    private const val ZAHL = "\\d+(?:[.,]\\d+)?"
    private val saetzeMuster = Regex("(\\d+)\\s*[x×*]\\s*(\\d+)(?:\\s*(?:mit|à|a|@|je)?\\s*($ZAHL)\\s*(?:kg|kilo))?", RegexOption.IGNORE_CASE)
    private val gewichtMuster = Regex("($ZAHL)\\s*(?:kg|kilo)", RegexOption.IGNORE_CASE)
    private val wdhMuster = Regex("(\\d+)\\s*(?:wdh|wiederholungen|mal|stück)?", RegexOption.IGNORE_CASE)
    private val trenner = Regex("\\s*(?:[;\\n]|(?<!\\d),|,(?!\\d)|\\bund\\b|\\bdann\\b)\\s*", RegexOption.IGNORE_CASE)

    private fun datei(context: Context) = File(context.filesDir, "fitness.json")

    @Synchronized
    private fun laden(context: Context): JSONObject = runCatching { JSONObject(datei(context).readText()) }.getOrDefault(JSONObject())
        .apply { if (!has("trainings")) put("trainings", JSONArray()); if (!has("ziele")) put("ziele", JSONObject()) }

    @Synchronized
    private fun speichern(context: Context, daten: JSONObject) {
        val ziel = datei(context)
        val temp = File(ziel.parentFile, ziel.name + ".neu")
        temp.writeText(daten.toString())
        temp.renameTo(ziel)
    }

    private fun zahl(text: String) = text.replace(",", ".").toDouble()

    fun uebungenLesen(text: String): JSONArray {
        val uebungen = JSONArray()
        for (roh in text.split(trenner)) {
            val teil = roh.trim(' ', '.', ':', '-')
            if (teil.isEmpty()) continue
            val saetze = JSONArray()
            var rest = teil
            val treffer = saetzeMuster.find(teil)
            if (treffer != null) {
                val anzahl = treffer.groupValues[1].toInt().coerceIn(1, 20)
                val wdh = treffer.groupValues[2].toInt().coerceIn(1, 500)
                val gewicht = treffer.groupValues[3].ifBlank { gewichtMuster.find(teil)?.groupValues?.get(1).orEmpty() }.let { if (it.isBlank()) 0.0 else zahl(it) }
                repeat(anzahl) { saetze.put(JSONObject().put("wdh", wdh).put("gewicht", gewicht)) }
                rest = gewichtMuster.replace(saetzeMuster.replace(teil, " "), " ")
            } else {
                val gewicht = gewichtMuster.find(teil)?.groupValues?.get(1)?.let(::zahl) ?: 0.0
                val ohne = gewichtMuster.replace(teil, " ")
                val wdh = wdhMuster.find(ohne)
                if (wdh != null) {
                    saetze.put(JSONObject().put("wdh", wdh.groupValues[1].toInt().coerceIn(1, 500)).put("gewicht", gewicht))
                    rest = ohne.replaceFirst(wdhMuster, " ")
                } else rest = ohne
            }
            val name = rest.replace(Regex("\\b(?:mit|à|je|sätze|satz|wdh|wiederholungen|mal|kg|kilo)\\b", RegexOption.IGNORE_CASE), " ")
                .replace(Regex("[^\\p{L}\\p{N}\\- ]"), " ").replace(Regex("\\s+"), " ").trim(' ', '-')
            if (name.isEmpty()) continue
            uebungen.put(JSONObject().put("name", name.take(60).replaceFirstChar { it.uppercase() }).put("saetze", saetze))
        }
        return uebungen
    }

    fun datumLesen(wert: String): String {
        val text = wert.trim().lowercase()
        val heute = LocalDate.now()
        return when {
            text.isEmpty() || text == "heute" -> heute.toString()
            text == "gestern" -> heute.minusDays(1).toString()
            text == "vorgestern" -> heute.minusDays(2).toString()
            else -> listOf("yyyy-MM-dd", "d.M.yyyy", "d.M.yy").firstNotNullOfOrNull { runCatching { LocalDate.parse(text, DateTimeFormatter.ofPattern(it)).toString() }.getOrNull() }
                ?: Regex("(\\d{1,2})\\.(\\d{1,2})\\.?").matchEntire(text)?.let { runCatching { LocalDate.of(heute.year, it.groupValues[2].toInt(), it.groupValues[1].toInt()).toString() }.getOrNull() }
                ?: error("Das Datum verstehe ich nicht. Nimm heute, gestern oder TT.MM.JJJJ.")
        }
    }

    private fun volumen(training: JSONObject): Double {
        var summe = 0.0
        val uebungen = training.optJSONArray("uebungen") ?: return 0.0
        for (i in 0 until uebungen.length()) {
            val saetze = uebungen.getJSONObject(i).optJSONArray("saetze") ?: continue
            for (j in 0 until saetze.length()) saetze.getJSONObject(j).let { summe += it.optInt("wdh") * it.optDouble("gewicht") }
        }
        return Math.round(summe * 10) / 10.0
    }

    fun eintragen(context: Context, args: JSONObject): JSONObject {
        val art = args.optString("art", "gym").lowercase().takeIf { it in arten } ?: "sonstiges"
        val uebungen = args.optJSONArray("uebungen")?.takeIf { it.length() > 0 } ?: uebungenLesen(args.optString("text"))
        val dauer = args.optDouble("dauer_min", 0.0).toInt().coerceIn(0, 24 * 60)
        val distanz = args.optString("distanz_km").replace(",", ".").toDoubleOrNull()?.coerceIn(0.0, 1000.0) ?: 0.0
        require(uebungen.length() > 0 || dauer > 0 || distanz > 0) { "Sag mir, was du gemacht hast: Übungen, Dauer oder Strecke." }
        val training = JSONObject().put("id", "h" + Krypto.kennung(8)).put("datum", datumLesen(args.optString("datum")))
            .put("zeit", System.currentTimeMillis() / 1000.0).put("art", art)
            .put("titel", args.optString("titel").trim().take(80).ifBlank { artNamen.getValue(art) })
            .put("dauer_min", dauer).put("distanz_km", distanz).put("uebungen", uebungen).put("notiz", args.optString("notiz").take(300))
        val daten = laden(context)
        val liste = daten.getJSONArray("trainings")
        liste.put(training)
        while (liste.length() > 2000) liste.remove(0)
        daten.put("ausstehend", (daten.optJSONArray("ausstehend") ?: JSONArray()).put(training.getString("id")))
        speichern(context, daten)
        return JSONObject(training.toString()).put("volumen", volumen(training))
    }

    fun loeschen(context: Context, id: String): Boolean {
        val daten = laden(context)
        val alt = daten.getJSONArray("trainings")
        val neu = JSONArray()
        var weg = false
        for (i in 0 until alt.length()) alt.getJSONObject(i).let { if (it.optString("id") == id) weg = true else neu.put(it) }
        if (weg) {
            daten.put("trainings", neu)
            daten.put("geloescht", (daten.optJSONArray("geloescht") ?: JSONArray()).put(id))
            speichern(context, daten)
        }
        return weg
    }

    fun zieleSetzen(context: Context, schritte: Int?, wochen: Int?): JSONObject {
        val daten = laden(context)
        val ziele = daten.getJSONObject("ziele")
        schritte?.let { ziele.put("schritte", it.coerceIn(500, 100_000)); Schritte.zielSetzen(context, it) }
        wochen?.let { ziele.put("trainings_pro_woche", it.coerceIn(1, 21)) }
        speichern(context, daten)
        return ziele
    }

    fun uebersicht(context: Context): JSONObject {
        val daten = laden(context)
        val trainings = daten.getJSONArray("trainings")
        val ziele = daten.getJSONObject("ziele")
        val heute = LocalDate.now()
        val wochenbeginn = heute.minusDays((heute.dayOfWeek.value - 1).toLong()).toString()
        val schritte = Schritte.tage(context, 7)
        val verlauf = JSONArray()
        schritte.keys().asSequence().sorted().forEach { verlauf.put(JSONObject().put("datum", it).put("schritte", schritte.optInt(it))) }
        val woche = (0 until trainings.length()).map { trainings.getJSONObject(it) }.filter { it.optString("datum") >= wochenbeginn }
        val letzte = JSONArray()
        (0 until trainings.length()).map { trainings.getJSONObject(it) }.sortedByDescending { it.optString("datum") + "%015.3f".format(it.optDouble("zeit")) }.take(15)
            .forEach { letzte.put(JSONObject(it.toString()).put("volumen", volumen(it)).put("art_name", artNamen[it.optString("art")] ?: "Training")) }
        val rekorde = mutableMapOf<String, JSONObject>()
        for (i in 0 until trainings.length()) {
            val t = trainings.getJSONObject(i)
            val uebungen = t.optJSONArray("uebungen") ?: continue
            for (j in 0 until uebungen.length()) {
                val u = uebungen.getJSONObject(j)
                val saetze = u.optJSONArray("saetze") ?: continue
                for (k in 0 until saetze.length()) {
                    val s = saetze.getJSONObject(k)
                    val schluessel = u.optString("name").lowercase()
                    val bisher = rekorde[schluessel]
                    if (s.optDouble("gewicht") > 0 && (bisher == null || s.optDouble("gewicht") > bisher.optDouble("gewicht")))
                        rekorde[schluessel] = JSONObject().put("name", u.optString("name")).put("gewicht", s.optDouble("gewicht")).put("wdh", s.optInt("wdh")).put("datum", t.optString("datum"))
                }
            }
        }
        val tageMit = (0 until trainings.length()).map { trainings.getJSONObject(it).optString("datum") }.toSet()
        var serie = 0
        var tag = if (heute.toString() in tageMit) heute else heute.minusDays(1)
        while (tag.toString() in tageMit) { serie++; tag = tag.minusDays(1) }
        val ziel = ziele.optInt("schritte", Schritte.stand(context).optInt("ziel", 8000))
        val heuteSchritte = Schritte.heute(context)
        return JSONObject()
            .put("heute", JSONObject().put("datum", heute.toString()).put("schritte", heuteSchritte).put("ziel", ziel).put("fortschritt", (heuteSchritte.toDouble() / ziel).coerceAtMost(1.0)))
            .put("verlauf", verlauf)
            .put("woche", JSONObject().put("trainings", woche.size).put("ziel", ziele.optInt("trainings_pro_woche", 3))
                .put("minuten", woche.sumOf { it.optInt("dauer_min") }).put("volumen", woche.sumOf { volumen(it) }))
            .put("serie", serie).put("trainings", letzte)
            .put("rekorde", JSONArray(rekorde.values.sortedByDescending { it.optDouble("gewicht") }.take(12)))
            .put("ziele", JSONObject().put("schritte", ziel).put("trainings_pro_woche", ziele.optInt("trainings_pro_woche", 3)))
            .put("schritte_erlaubt", Schritte.erlaubt(context)).put("schritte_verfuegbar", Schritte.verfuegbar(context))
    }

    fun ausstehend(context: Context): JSONObject {
        val daten = laden(context)
        val ids = daten.optJSONArray("ausstehend")?.let { a -> (0 until a.length()).map { a.optString(it) }.toSet() }.orEmpty()
        val trainings = daten.getJSONArray("trainings")
        val neu = JSONArray()
        for (i in 0 until trainings.length()) trainings.getJSONObject(i).let { if (it.optString("id") in ids) neu.put(it) }
        return JSONObject().put("trainings", neu).put("geloescht", daten.optJSONArray("geloescht") ?: JSONArray())
    }

    fun abgeglichen(context: Context, fremde: JSONArray) {
        val daten = laden(context)
        val trainings = daten.getJSONArray("trainings")
        val bekannt = (0 until trainings.length()).map { trainings.getJSONObject(it).optString("id") }.toMutableSet()
        val geloescht = daten.optJSONArray("geloescht")?.let { a -> (0 until a.length()).map { a.optString(it) }.toSet() }.orEmpty()
        for (i in 0 until fremde.length()) {
            val t = fremde.optJSONObject(i) ?: continue
            val id = t.optString("id")
            if (id.isBlank() || id in bekannt || id in geloescht) continue
            trainings.put(t)
            bekannt += id
        }
        daten.put("ausstehend", JSONArray())
        daten.put("geloescht", JSONArray())
        speichern(context, daten)
    }
}
