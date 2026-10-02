package at.felworks.jon.device

import android.app.AlarmManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import at.felworks.jon.MainActivity
import at.felworks.jon.data.remote.Krypto
import org.json.JSONArray
import org.json.JSONObject
import java.time.Instant
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.ZoneId

class UhrenEmpfaenger : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val id = intent.getStringExtra("id") ?: return
        val ereignis = Uhren.ausgeloest(context, id) ?: return
        KlingelDienst.starten(context, ereignis.optString("art"), ereignis.optString("titel"))
    }
}

object Uhren {
    private val wochentage = listOf("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")

    private fun prefs(context: Context) = context.getSharedPreferences("jon-uhren", Context.MODE_PRIVATE)

    private fun liste(context: Context, name: String): MutableList<JSONObject> {
        val roh = runCatching { JSONArray(prefs(context).getString(name, "[]")) }.getOrDefault(JSONArray())
        return MutableList(roh.length()) { roh.getJSONObject(it) }
    }

    private fun speichern(context: Context, name: String, liste: List<JSONObject>) {
        prefs(context).edit().putString(name, JSONArray().apply { liste.forEach { put(it) } }.toString()).commit()
    }

    private fun tage(json: JSONObject): Set<Int> {
        val roh = json.optJSONArray("tage") ?: return emptySet()
        return (0 until roh.length()).map { roh.optInt(it) }.filter { it in 1..7 }.toSet()
    }

    private fun zeitpunkt(wecker: JSONObject, jetzt: LocalDateTime = LocalDateTime.now()): Long =
        Zeitregeln.naechsterWecker(wecker.optInt("stunde"), wecker.optInt("minute"), tage(wecker), jetzt).atZone(ZoneId.systemDefault()).toInstant().toEpochMilli()

    fun wannText(ms: Long): String {
        val zeit = LocalDateTime.ofInstant(Instant.ofEpochMilli(ms), ZoneId.systemDefault())
        val heute = LocalDate.now()
        val uhr = "%02d:%02d".format(zeit.hour, zeit.minute)
        return when (zeit.toLocalDate()) {
            heute -> "heute $uhr"
            heute.plusDays(1) -> "morgen $uhr"
            else -> "${wochentage[zeit.dayOfWeek.value - 1]} $uhr"
        }
    }

    fun stand(context: Context): JSONObject {
        val jetzt = System.currentTimeMillis()
        val wecker = JSONArray()
        liste(context, "wecker").sortedWith(compareBy({ it.optInt("stunde") }, { it.optInt("minute") })).forEach { w ->
            val kopie = JSONObject(w.toString())
            if (w.optBoolean("an", true)) {
                val wann = zeitpunkt(w)
                kopie.put("naechster", wann).put("naechsterText", wannText(wann))
            }
            wecker.put(kopie)
        }
        val timer = JSONArray()
        liste(context, "timer").filter { it.optLong("ende") > jetzt - 60_000 }.sortedBy { it.optLong("ende") }.forEach { t ->
            timer.put(JSONObject(t.toString()).put("rest", (t.optLong("ende") - jetzt).coerceAtLeast(0)))
        }
        return JSONObject().put("wecker", wecker).put("timer", timer).put("jetzt", jetzt)
            .put("klingelt", KlingelDienst.aktuell ?: JSONObject.NULL).put("naechster", naechsterText(context) ?: JSONObject.NULL)
    }

    fun naechsterText(context: Context): String? {
        val naechster = liste(context, "wecker").filter { it.optBoolean("an", true) }.minOfOrNull { zeitpunkt(it) } ?: return null
        return wannText(naechster)
    }

    fun weckerSetzen(context: Context, daten: JSONObject): JSONObject {
        val stunde = daten.optInt("stunde", -1)
        val minute = daten.optInt("minute", -1)
        require(stunde in 0..23 && minute in 0..59) { "Ungültige Uhrzeit." }
        val alle = liste(context, "wecker")
        val id = daten.optString("id").takeIf { it.isNotBlank() && it.length <= 40 } ?: "w-${Krypto.kennung(8)}"
        val vorhanden = alle.indexOfFirst { it.optString("id") == id }
        check(vorhanden >= 0 || alle.size < 20) { "Mehr als 20 Wecker gehen nicht." }
        val eintrag = JSONObject().put("id", id).put("stunde", stunde).put("minute", minute)
            .put("tage", JSONArray(tage(daten).sorted())).put("an", daten.optBoolean("an", true))
            .put("name", daten.optString("name").trim().take(40))
        if (vorhanden >= 0) alle[vorhanden] = eintrag else alle += eintrag
        speichern(context, "wecker", alle)
        allePlanen(context)
        return stand(context).put("gestellt", wannText(zeitpunkt(eintrag)))
    }

    fun weckerLoeschen(context: Context, id: String): JSONObject {
        speichern(context, "wecker", liste(context, "wecker").filter { it.optString("id") != id })
        allePlanen(context)
        return stand(context)
    }

    fun timerStarten(context: Context, sekunden: Int, name: String = "", art: String = "timer"): JSONObject {
        require(sekunden in 1..86_400) { "Ein Timer darf 1 Sekunde bis 24 Stunden laufen." }
        val jetzt = System.currentTimeMillis()
        val alle = liste(context, "timer").filter { it.optLong("ende") > jetzt }.toMutableList()
        check(alle.size < 10) { "Mehr als 10 Timer gehen nicht." }
        alle += JSONObject().put("id", "t-${Krypto.kennung(8)}").put("ende", jetzt + sekunden * 1000L).put("dauer", sekunden)
            .put("name", name.trim().take(40)).put("art", art)
        speichern(context, "timer", alle)
        allePlanen(context)
        return stand(context)
    }

    fun timerAbbrechen(context: Context, id: String? = null): JSONObject {
        speichern(context, "timer", if (id.isNullOrBlank()) emptyList() else liste(context, "timer").filter { it.optString("id") != id })
        allePlanen(context)
        return stand(context)
    }

    fun schlummern(context: Context, titel: String, minuten: Int = 5) {
        timerStarten(context, minuten * 60, titel.ifBlank { "Wecker" }, "schlummer")
    }

    private fun ausloesen(context: Context, id: String, erzeugen: Boolean): PendingIntent? {
        val intent = Intent(context, UhrenEmpfaenger::class.java).setAction("at.felworks.jon.uhr.$id").putExtra("id", id)
        val flags = PendingIntent.FLAG_IMMUTABLE or if (erzeugen) PendingIntent.FLAG_UPDATE_CURRENT else PendingIntent.FLAG_NO_CREATE
        return PendingIntent.getBroadcast(context, id.hashCode(), intent, flags)
    }

    private fun planen(context: Context, id: String, zeit: Long) {
        val am = context.getSystemService(AlarmManager::class.java)
        val ausloeser = ausloesen(context, id, true) ?: return
        val zeigen = PendingIntent.getActivity(context, 4720, Intent(context, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        if (Build.VERSION.SDK_INT < 31 || am.canScheduleExactAlarms()) am.setAlarmClock(AlarmManager.AlarmClockInfo(zeit, zeigen), ausloeser)
        else am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, zeit, ausloeser)
    }

    @Synchronized
    fun allePlanen(context: Context) {
        val am = context.getSystemService(AlarmManager::class.java)
        val p = prefs(context)
        p.getStringSet("geplant", emptySet()).orEmpty().forEach { id -> ausloesen(context, id, false)?.let { am.cancel(it); it.cancel() } }
        val jetzt = System.currentTimeMillis()
        val geplant = mutableSetOf<String>()
        liste(context, "wecker").filter { it.optBoolean("an", true) }.forEach { w ->
            val id = w.optString("id")
            planen(context, id, zeitpunkt(w))
            geplant += id
        }
        val timer = liste(context, "timer")
        val gueltig = timer.filter { it.optLong("ende") > jetzt - 5 * 60_000 }
        if (gueltig.size != timer.size) speichern(context, "timer", gueltig)
        gueltig.forEach { t ->
            val id = t.optString("id")
            planen(context, id, t.optLong("ende").coerceAtLeast(jetzt + 1000))
            geplant += id
        }
        p.edit().putStringSet("geplant", geplant).commit()
        runCatching { JonWidget.aktualisieren(context) }
    }

    @Synchronized
    fun ausgeloest(context: Context, id: String): JSONObject? {
        val wecker = liste(context, "wecker")
        val w = wecker.firstOrNull { it.optString("id") == id }
        if (w != null) {
            if (tage(w).isEmpty()) {
                w.put("an", false)
                speichern(context, "wecker", wecker)
            }
            allePlanen(context)
            val uhr = "%02d:%02d".format(w.optInt("stunde"), w.optInt("minute"))
            return JSONObject().put("art", "wecker").put("titel", w.optString("name").ifBlank { "Wecker $uhr" })
        }
        val timer = liste(context, "timer")
        val t = timer.firstOrNull { it.optString("id") == id } ?: return null
        speichern(context, "timer", timer.filter { it.optString("id") != id })
        allePlanen(context)
        val art = if (t.optString("art") == "schlummer") "wecker" else "timer"
        val titel = t.optString("name").ifBlank { "Timer · ${Zeitregeln.dauerText(t.optInt("dauer"))}" }
        return JSONObject().put("art", art).put("titel", titel)
    }

    fun sprachbefehl(context: Context, befehl: Uhrbefehl): String = when (befehl) {
        is Uhrbefehl.Wecker -> {
            val r = weckerSetzen(context, JSONObject().put("stunde", befehl.stunde).put("minute", befehl.minute))
            "Dein Wecker ist gestellt: ${r.optString("gestellt")} Uhr."
        }
        is Uhrbefehl.Timer -> {
            timerStarten(context, befehl.sekunden)
            "Der Timer läuft: ${Zeitregeln.dauerText(befehl.sekunden)}."
        }
        Uhrbefehl.Stopp -> if (KlingelDienst.aktuell != null) { KlingelDienst.stoppen(); "Ist aus." } else "Gerade klingelt nichts."
        Uhrbefehl.TimerAus -> { timerAbbrechen(context); "Alle Timer sind abgebrochen." }
    }
}
