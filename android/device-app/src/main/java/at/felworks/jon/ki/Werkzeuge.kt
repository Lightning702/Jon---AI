package at.felworks.jon.ki

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.os.BatteryManager
import at.felworks.jon.device.Bildschirmzeit
import at.felworks.jon.device.GeraeteApps
import at.felworks.jon.device.Uhren
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONArray
import org.json.JSONObject
import java.net.InetAddress
import java.net.URLDecoder
import java.net.URLEncoder
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter
import java.util.Locale
import java.util.concurrent.TimeUnit

data class WerkzeugDef(val name: String, val beschreibung: String, val parameter: JSONObject, val arbeit: Boolean = false, val kurz: (JSONObject) -> String)

private fun objekt(vararg felder: Pair<String, JSONObject>, pflicht: List<String> = emptyList()): JSONObject =
    JSONObject().put("type", "object").put("properties", JSONObject().apply { felder.forEach { (n, s) -> put(n, s) } }).put("required", JSONArray(pflicht))

private fun text(beschreibung: String) = JSONObject().put("type", "string").put("description", beschreibung)
private fun zahl(beschreibung: String) = JSONObject().put("type", "number").put("description", beschreibung)
private fun ganz(beschreibung: String) = JSONObject().put("type", "integer").put("description", beschreibung)
private fun auswahl(beschreibung: String, vararg werte: String) = JSONObject().put("type", "string").put("description", beschreibung).put("enum", JSONArray(werte.toList()))

object Werkzeuge {
    private val netz = OkHttpClient.Builder().connectTimeout(12, TimeUnit.SECONDS).readTimeout(20, TimeUnit.SECONDS).followRedirects(true).build()
    private const val BROWSER = "Mozilla/5.0 (Linux; Android 15; Jon) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Mobile Safari/537.36"

    private val alle: List<WerkzeugDef> = listOf(
        WerkzeugDef("wecker_stellen", "Stellt einen Wecker auf diesem Handy. tage sind Wochentage 1=Montag bis 7=Sonntag, leer für einmalig.",
            objekt("stunde" to ganz("0 bis 23"), "minute" to ganz("0 bis 59"), "tage" to JSONObject().put("type", "array").put("items", JSONObject().put("type", "integer")), "name" to text("Optionaler Name"), pflicht = listOf("stunde", "minute"))) { "Stellt einen Wecker für %02d:%02d".format(it.optInt("stunde"), it.optInt("minute")) },
        WerkzeugDef("timer_starten", "Startet einen Timer auf diesem Handy. Gib minuten oder sekunden an.",
            objekt("minuten" to zahl("Dauer in Minuten"), "sekunden" to ganz("Dauer in Sekunden"), "name" to text("Wofür, z.B. Nudeln"))) { "Startet einen Timer" },
        WerkzeugDef("uhren_anzeigen", "Zeigt alle Wecker und laufenden Timer auf diesem Handy.", objekt()) { "Schaut nach Weckern und Timern" },
        WerkzeugDef("app_oeffnen", "Öffnet eine freigegebene App auf diesem Handy. Keine anderen Apps.",
            objekt("app" to text("Name der App, genau wie in der Liste"), pflicht = listOf("app"))) { "Öffnet ${it.optString("app")}" },
        WerkzeugDef("musik_steuern", "Steuert Amazon Music: play, pause, next, previous oder status.",
            objekt("aktion" to auswahl("Aktion", "play", "pause", "next", "previous", "status"), pflicht = listOf("aktion"))) { "Steuert die Musik" },
        WerkzeugDef("wetter", "Aktuelles Wetter und Vorhersage für einen Ort.",
            objekt("ort" to text("Stadt oder Ort"), "tage" to ganz("1 bis 7 Tage Vorhersage"), pflicht = listOf("ort"))) { "Schaut das Wetter in ${it.optString("ort")} nach" },
        WerkzeugDef("web_suche", "Sucht im Internet und liefert Titel, Link und Ausschnitt der besten Treffer. Für aktuelle Informationen.",
            objekt("anfrage" to text("Suchbegriffe"), pflicht = listOf("anfrage"))) { "Sucht im Web: ${it.optString("anfrage").take(60)}" },
        WerkzeugDef("webseite_lesen", "Liest den Text einer Webseite (http oder https), zum Beispiel einen Treffer aus der Websuche.",
            objekt("url" to text("Adresse der Seite"), pflicht = listOf("url"))) { "Liest ${it.optString("url").take(60)}" },
        WerkzeugDef("fitness_training_eintragen", "Trägt ein Training ins Fitness-Tagebuch ein. Kraftübungen als text wie 'Bankdrücken 3x10 60kg, 20 Liegestütze', Ausdauer mit dauer_min und distanz_km.",
            objekt("art" to auswahl("Art", "gym", "laufen", "rad", "schwimmen", "yoga", "wandern", "sonstiges"), "titel" to text("Kurzer Name"), "text" to text("Übungen als Freitext"),
                "dauer_min" to ganz("Dauer in Minuten"), "distanz_km" to zahl("Strecke in km"), "datum" to text("heute, gestern oder TT.MM.JJJJ"), pflicht = listOf("art"))) { "Trägt ein Training ein" },
        WerkzeugDef("fitness_uebersicht", "Schritte heute und der letzten Tage, Trainings dieser Woche, Rekorde und Ziele.", objekt()) { "Schaut in dein Fitness-Tagebuch" },
        WerkzeugDef("bildschirmzeit", "Zeigt, wie lange die freigegebenen Apps heute genutzt wurden, die Limits, Schlafenszeit und Pause. Nur lesen.", objekt()) { "Schaut auf die Bildschirmzeit" },
        WerkzeugDef("merken", "Merkt sich eine wichtige Information über den Nutzer dauerhaft, zum Beispiel Vorlieben, Namen oder Termine.",
            objekt("fakt" to text("Die Information in einem Satz"), pflicht = listOf("fakt"))) { "Merkt sich etwas" },
        WerkzeugDef("handy_status", "Akku, Ladezustand, Internetverbindung, Datum und Uhrzeit dieses Handys.", objekt()) { "Schaut auf den Handy-Status" },
        WerkzeugDef("bild_erstellen", "Erstellt ein Bild aus einer Beschreibung und speichert es in der Galerie.",
            objekt("beschreibung" to text("Was auf dem Bild zu sehen sein soll, ausführlich"), pflicht = listOf("beschreibung"))) { "Malt ein Bild" },
        WerkzeugDef("datei_schreiben", "Schreibt eine Datei in Jons Arbeitsordner auf dem Handy, zum Beispiel websites/meine-seite/index.html, notizen/plan.md oder code/rechner.py. Vorhandene Dateien werden ersetzt.",
            objekt("pfad" to text("Relativer Pfad im Arbeitsordner"), "inhalt" to text("Vollständiger Inhalt"), pflicht = listOf("pfad", "inhalt")), arbeit = true) { "Schreibt ${it.optString("pfad")}" },
        WerkzeugDef("podcast_erstellen", "Nimmt einen Podcast oder ein Hörstück mit zwei Stimmen auf (a = erste, b = zweite Stimme) und speichert ihn als WAV im Arbeitsordner. Schreib zuerst ein lebendiges Skript.",
            objekt("titel" to text("Titel"), "teile" to JSONObject().put("type", "array").put("items", objekt("sprecher" to auswahl("a oder b", "a", "b"), "text" to text("Was gesagt wird"))),
                "skript" to text("Alternativ Zeilen wie 'A: ...' und 'B: ...'"), pflicht = listOf("titel")), arbeit = true) { "Nimmt einen Podcast auf" },
        WerkzeugDef("datei_lesen", "Liest eine Datei aus Jons Arbeitsordner.", objekt("pfad" to text("Relativer Pfad"), pflicht = listOf("pfad")), arbeit = true) { "Liest ${it.optString("pfad")}" },
        WerkzeugDef("dateien_auflisten", "Listet Dateien und Ordner in Jons Arbeitsordner.", objekt("ordner" to text("Relativer Ordner, leer für alles")), arbeit = true) { "Schaut in den Arbeitsordner" },
    )

    fun liste(context: Context, arbeit: Boolean, bilder: Boolean): List<WerkzeugDef> {
        val apps = GeraeteApps.liste(context).joinToString { it.name }
        return alle.filter { (arbeit || !it.arbeit) && (bilder || it.name != "bild_erstellen") }
            .map { if (it.name == "app_oeffnen") it.copy(beschreibung = "Öffnet eine freigegebene App auf diesem Handy: $apps. Keine anderen Apps.") else it }
    }

    fun openAi(defs: List<WerkzeugDef>): JSONArray = JSONArray().apply {
        defs.forEach { def -> put(JSONObject().put("type", "function").put("function", JSONObject().put("name", def.name).put("description", def.beschreibung).put("parameters", def.parameter))) }
    }

    fun laeuft(def: WerkzeugDef, args: JSONObject): JSONObject =
        JSONObject().put("type", "tool").put("name", def.name).put("status", "running").put("args", args).put("summary", runCatching { def.kurz(args) }.getOrDefault(def.name))

    fun fertig(name: String, ergebnis: JSONObject): JSONObject {
        val ereignis = JSONObject().put("type", "tool").put("name", name).put("status", "done").put("ok", !ergebnis.has("fehler"))
        ergebnis.optJSONObject("karte")?.let { ereignis.put("card", it) }
        return ereignis
    }

    fun kurz(name: String, args: JSONObject): String = alle.firstOrNull { it.name == name }?.let { runCatching { it.kurz(args) }.getOrNull() } ?: name

    suspend fun ausfuehren(context: Context, name: String, args: JSONObject): JSONObject = try {
        when (name) {
            "wecker_stellen" -> {
                val tage = args.optJSONArray("tage")?.let { a -> JSONArray((0 until a.length()).map { a.optInt(it) }.filter { it in 1..7 }) } ?: JSONArray()
                val stand = Uhren.weckerSetzen(context, JSONObject().put("stunde", args.optInt("stunde", -1)).put("minute", args.optInt("minute", 0)).put("tage", tage).put("name", args.optString("name")))
                JSONObject().put("ok", true).put("klingelt", stand.optString("gestellt"))
            }
            "timer_starten" -> {
                val sekunden = if (args.has("sekunden")) args.optInt("sekunden") else (args.optDouble("minuten", 0.0) * 60).toInt()
                Uhren.timerStarten(context, sekunden, args.optString("name"))
                JSONObject().put("ok", true).put("dauer", at.felworks.jon.device.Zeitregeln.dauerText(sekunden))
            }
            "uhren_anzeigen" -> Uhren.stand(context)
            "app_oeffnen" -> withContext(Dispatchers.Main) { GeraeteApps.oeffnen(context, args.optString("app")) }
            "musik_steuern" -> withContext(Dispatchers.Main) { GeraeteApps.musik(context, args.optString("aktion", "status")) }
            "wetter" -> wetter(args.optString("ort"), args.optInt("tage", 3).coerceIn(1, 7))
            "web_suche" -> suche(args.optString("anfrage"), at.felworks.jon.device.KinderModus.alter(context) > 0)
            "webseite_lesen" -> {
                check(at.felworks.jon.device.KinderModus.alter(context) == 0 || at.felworks.jon.device.KinderModus.kindgerecht(args.optString("url"))) { "Diese Seite ist im Kindermodus gesperrt." }
                lesen(args.optString("url"))
            }
            "fitness_training_eintragen" -> FitnessLokal.eintragen(context, args)
            "fitness_uebersicht" -> FitnessLokal.uebersicht(context)
            "bildschirmzeit" -> Bildschirmzeit.stand(context)
            "merken" -> Gedaechtnis.merken(context, args.optString("fakt"))
            "handy_status" -> status(context)
            "bild_erstellen" -> {
                check(at.felworks.jon.device.KinderModus.alter(context) == 0 || at.felworks.jon.device.KinderModus.kindgerecht(args.optString("beschreibung"))) { "Dieses Bild geht im Kindermodus nicht." }
                Solo.bildErstellen(context, args.optString("beschreibung"))
            }
            "podcast_erstellen" -> Podcast.erstellen(context, args)
            "datei_schreiben" -> Arbeitsraum.schreiben(context, args.optString("pfad"), args.optString("inhalt"))
            "datei_lesen" -> Arbeitsraum.lesen(context, args.optString("pfad"))
            "dateien_auflisten" -> Arbeitsraum.liste(context, args.optString("ordner"))
            else -> JSONObject().put("fehler", "Dieses Werkzeug gibt es nicht.")
        }
    } catch (e: Exception) {
        JSONObject().put("fehler", e.message ?: "Das hat nicht funktioniert.")
    }

    private fun status(context: Context): JSONObject {
        val akku = context.getSystemService(BatteryManager::class.java)
        val netz = context.getSystemService(ConnectivityManager::class.java)
        val faehig = netz.getNetworkCapabilities(netz.activeNetwork)
        val art = when {
            faehig == null -> "offline"
            faehig.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) -> "WLAN"
            faehig.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) -> "Mobilfunk"
            else -> "verbunden"
        }
        return JSONObject().put("akku", akku.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)).put("laedt", akku.isCharging)
            .put("netz", art).put("jetzt", LocalDateTime.now().format(DateTimeFormatter.ofPattern("EEEE, d. MMMM yyyy, HH:mm", Locale.GERMAN)))
    }

    private suspend fun holen(url: String, grenze: Int = 1_500_000): Pair<String, String> = withContext(Dispatchers.IO) {
        netz.newCall(Request.Builder().url(url).header("User-Agent", BROWSER).header("Accept-Language", "de-DE,de;q=0.9").build()).execute().use { antwort ->
            check(antwort.isSuccessful) { "Die Seite antwortet mit Fehler ${antwort.code}." }
            val quelle = antwort.body.source()
            quelle.request(grenze.toLong())
            val daten = quelle.buffer.readByteArray(minOf(grenze.toLong(), quelle.buffer.size))
            String(daten, Charsets.UTF_8) to (antwort.header("Content-Type") ?: "")
        }
    }

    private val wetterCodes = mapOf(
        0 to "klar", 1 to "überwiegend klar", 2 to "teils bewölkt", 3 to "bedeckt", 45 to "Nebel", 48 to "Reifnebel",
        51 to "leichter Nieselregen", 53 to "Nieselregen", 55 to "starker Nieselregen", 61 to "leichter Regen", 63 to "Regen", 65 to "starker Regen",
        66 to "gefrierender Regen", 67 to "starker gefrierender Regen", 71 to "leichter Schneefall", 73 to "Schneefall", 75 to "starker Schneefall",
        77 to "Schneegriesel", 80 to "leichte Regenschauer", 81 to "Regenschauer", 82 to "heftige Regenschauer", 85 to "Schneeschauer",
        86 to "starke Schneeschauer", 95 to "Gewitter", 96 to "Gewitter mit Hagel", 99 to "schweres Gewitter mit Hagel"
    )

    private suspend fun wetter(ort: String, tage: Int): JSONObject {
        require(ort.isNotBlank()) { "Für welchen Ort?" }
        val treffer = JSONObject(holen("https://geocoding-api.open-meteo.com/v1/search?count=1&language=de&format=json&name=${URLEncoder.encode(ort.trim(), "UTF-8")}").first)
            .optJSONArray("results")?.optJSONObject(0) ?: error("Den Ort $ort finde ich nicht.")
        val breite = treffer.getDouble("latitude")
        val laenge = treffer.getDouble("longitude")
        val daten = JSONObject(holen("https://api.open-meteo.com/v1/forecast?latitude=$breite&longitude=$laenge&current=temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=auto&forecast_days=$tage").first)
        val jetzt = daten.getJSONObject("current")
        val taeglich = daten.getJSONObject("daily")
        val vorhersage = JSONArray()
        for (i in 0 until taeglich.getJSONArray("time").length()) {
            vorhersage.put(JSONObject().put("datum", taeglich.getJSONArray("time").getString(i))
                .put("wetter", wetterCodes[taeglich.getJSONArray("weather_code").optInt(i)] ?: "wechselhaft")
                .put("max", taeglich.getJSONArray("temperature_2m_max").optDouble(i)).put("min", taeglich.getJSONArray("temperature_2m_min").optDouble(i))
                .put("regen_prozent", taeglich.getJSONArray("precipitation_probability_max").optInt(i)))
        }
        return JSONObject().put("ort", "${treffer.optString("name")}, ${treffer.optString("country")}")
            .put("jetzt", JSONObject().put("temperatur", jetzt.optDouble("temperature_2m")).put("gefuehlt", jetzt.optDouble("apparent_temperature"))
                .put("wetter", wetterCodes[jetzt.optInt("weather_code")] ?: "wechselhaft").put("wind_kmh", jetzt.optDouble("wind_speed_10m")).put("feuchte", jetzt.optInt("relative_humidity_2m")))
            .put("vorhersage", vorhersage)
    }

    private fun ohneTags(html: String): String = html
        .replace(Regex("(?is)<(script|style|noscript|svg|head)[^>]*>.*?</\\1>"), " ")
        .replace(Regex("(?i)<br\\s*/?>|</p>|</div>|</li>|</h[1-6]>"), "\n")
        .replace(Regex("<[^>]+>"), " ")
        .replace("&nbsp;", " ").replace("&amp;", "&").replace("&quot;", "\"").replace("&#39;", "'").replace("&lt;", "<").replace("&gt;", ">")
        .replace(Regex("[ \\t\\x0B\\f\\r]+"), " ")
        .replace(Regex("\\n\\s*\\n+"), "\n\n")
        .trim()

    private suspend fun suche(anfrage: String, kinder: Boolean = false): JSONObject {
        require(anfrage.isNotBlank()) { "Wonach soll ich suchen?" }
        check(!kinder || at.felworks.jon.device.KinderModus.kindgerecht(anfrage)) { "Danach sucht Jon im Kindermodus nicht." }
        val treffer = JSONArray()
        runCatching {
            val html = holen("https://html.duckduckgo.com/html/?kl=de-de${if (kinder) "&kp=1" else ""}&q=${URLEncoder.encode(anfrage, "UTF-8")}").first
            val links = Regex("(?is)<a[^>]+class=\"result__a\"[^>]+href=\"([^\"]+)\"[^>]*>(.*?)</a>").findAll(html).toList()
            val ausschnitte = Regex("(?is)<a[^>]+class=\"result__snippet\"[^>]*>(.*?)</a>").findAll(html).map { ohneTags(it.groupValues[1]) }.toList()
            links.take(6).forEachIndexed { i, m ->
                var ziel = m.groupValues[1].replace("&amp;", "&")
                Regex("uddg=([^&]+)").find(ziel)?.let { ziel = URLDecoder.decode(it.groupValues[1], "UTF-8") }
                if (ziel.startsWith("//")) ziel = "https:$ziel"
                treffer.put(JSONObject().put("titel", ohneTags(m.groupValues[2])).put("url", ziel).put("ausschnitt", ausschnitte.getOrNull(i).orEmpty()))
            }
        }
        if (treffer.length() == 0) {
            val wiki = JSONObject(holen("https://de.wikipedia.org/w/api.php?action=query&list=search&format=json&utf8=1&srlimit=5&srsearch=${URLEncoder.encode(anfrage, "UTF-8")}").first)
            val liste = wiki.optJSONObject("query")?.optJSONArray("search") ?: JSONArray()
            for (i in 0 until liste.length()) {
                val e = liste.getJSONObject(i)
                treffer.put(JSONObject().put("titel", e.optString("title")).put("url", "https://de.wikipedia.org/wiki/${URLEncoder.encode(e.optString("title").replace(' ', '_'), "UTF-8")}")
                    .put("ausschnitt", ohneTags(e.optString("snippet"))))
            }
        }
        val gefiltert = if (!kinder) treffer else JSONArray().apply {
            for (i in 0 until treffer.length()) treffer.optJSONObject(i)?.let { t ->
                if (at.felworks.jon.device.KinderModus.kindgerecht(t.optString("titel") + " " + t.optString("url") + " " + t.optString("ausschnitt"))) put(t)
            }
        }
        check(gefiltert.length() > 0) { "Keine Treffer gefunden." }
        return JSONObject().put("anfrage", anfrage).put("treffer", gefiltert)
    }

    private suspend fun lesen(adresse: String): JSONObject {
        val url = adresse.trim().toHttpUrlOrNull() ?: error("Das ist keine gültige Adresse.")
        require(url.scheme == "https" || url.scheme == "http") { "Nur Webseiten mit http oder https." }
        val privat = withContext(Dispatchers.IO) { runCatching { InetAddress.getAllByName(url.host).any { it.isLoopbackAddress || it.isSiteLocalAddress || it.isLinkLocalAddress || it.isAnyLocalAddress } }.getOrDefault(true) }
        check(!privat) { "Seiten im Heimnetz liest Jon so nicht." }
        val (inhalt, typ) = holen(url.toString())
        val titel = Regex("(?is)<title[^>]*>(.*?)</title>").find(inhalt)?.groupValues?.get(1)?.let(::ohneTags).orEmpty()
        val text = if (typ.contains("html", true) || inhalt.trimStart().startsWith("<")) ohneTags(inhalt) else inhalt
        return JSONObject().put("url", url.toString()).put("titel", titel).put("text", text.take(8000)).put("gekuerzt", text.length > 8000)
    }
}
