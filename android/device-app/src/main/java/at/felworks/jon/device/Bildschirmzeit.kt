package at.felworks.jon.device

import android.app.AlarmManager
import android.app.AppOpsManager
import android.app.PendingIntent
import android.app.admin.DevicePolicyManager
import android.app.usage.UsageEvents
import android.app.usage.UsageStatsManager
import android.content.BroadcastReceiver
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Process
import org.json.JSONArray
import org.json.JSONObject
import java.time.Instant
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.ZoneId

class RegelWaechter : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        runCatching { Bildschirmzeit.pruefen(context, true) }
    }
}

object Bildschirmzeit {
    private const val VORNE = 1
    private const val WEG = 2
    private const val GESTOPPT = 23
    private const val SITZUNG_MAX = 4 * 3_600_000L
    private const val ANFRAGE_MAX = 60 * 60_000L

    private fun prefs(context: Context) = context.getSharedPreferences("jon-bildschirmzeit", Context.MODE_PRIVATE)

    private fun ms(zeit: LocalDateTime): Long = zeit.atZone(ZoneId.systemDefault()).toInstant().toEpochMilli()

    private fun uhr(msWert: Long): String {
        val zeit = LocalDateTime.ofInstant(Instant.ofEpochMilli(msWert), ZoneId.systemDefault())
        return "%02d:%02d".format(zeit.hour, zeit.minute)
    }

    fun regeln(context: Context): Regeln {
        val roh = runCatching { JSONObject(prefs(context).getString("regeln", "{}") ?: "{}") }.getOrDefault(JSONObject())
        val bekannt = roh.optJSONObject("limits")?.keys()?.asSequence()?.toSet().orEmpty()
        return lesen(roh, Regeln(), GeraeteApps.ids(context).toSet() + bekannt)
    }

    private fun zahlen(liste: JSONArray?, erlaubt: (Int) -> Boolean): Set<Int>? = liste?.let { (0 until it.length()).map { i -> it.optInt(i, -1) }.filter(erlaubt).toSet() }

    private val kennung = Regex("^[A-Za-z][A-Za-z0-9_.]{1,120}$")

    private fun namen(liste: JSONArray?): Set<String>? = liste?.let { (0 until it.length()).map { i -> it.optString(i) }.filter { app -> kennung.matches(app) }.toSet() }

    fun lesen(json: JSONObject, alt: Regeln, apps: Set<String>): Regeln {
        val limits = alt.limits.toMutableMap()
        json.optJSONObject("limits")?.let { neu ->
            neu.keys().forEach { app -> if (kennung.matches(app) && (app in apps || app in limits)) limits[app] = neu.optInt(app, 0).coerceIn(0, 24 * 60) }
        }
        val jetztMs = System.currentTimeMillis()
        val ausnahmen = alt.ausnahmen.filterValues { it > jetztMs }.toMutableMap()
        json.optJSONObject("ausnahmen")?.let { neu ->
            neu.keys().forEach { app ->
                if (kennung.matches(app)) {
                    val bis = neu.optLong(app, 0L)
                    if (bis > jetztMs) ausnahmen[app] = bis else ausnahmen.remove(app)
                }
            }
        }
        val nacht = json.optJSONObject("nacht")?.let { n ->
            Nachtruhe(
                an = n.optBoolean("an", alt.nacht.an),
                von = Zeitregeln.zeitLesen(n.optString("von")) ?: alt.nacht.von,
                bis = Zeitregeln.zeitLesen(n.optString("bis")) ?: alt.nacht.bis,
                tage = zahlen(n.optJSONArray("tage")) { it in 1..7 } ?: alt.nacht.tage,
                apps = namen(n.optJSONArray("apps")) ?: alt.nacht.apps,
            )
        } ?: alt.nacht
        val pause = if (json.has("pause_bis")) json.optLong("pause_bis", 0L).coerceAtLeast(0L) else alt.pauseBis
        return Regeln(limits.filterValues { it > 0 }, nacht, pause, ausnahmen)
    }

    private fun json(r: Regeln, apps: List<String>): JSONObject = JSONObject()
        .put("limits", JSONObject().apply { (apps + r.limits.keys).distinct().forEach { put(it, r.limits[it] ?: 0) } })
        .put("nacht", JSONObject().put("an", r.nacht.an).put("von", Zeitregeln.zeitText(r.nacht.von)).put("bis", Zeitregeln.zeitText(r.nacht.bis))
            .put("tage", JSONArray(r.nacht.tage.sorted())).put("apps", JSONArray(r.nacht.apps.sorted())))
        .put("pause_bis", r.pauseBis)
        .put("ausnahmen", JSONObject().apply { r.ausnahmen.forEach { (app, bis) -> put(app, bis) } })

    private fun speichern(context: Context, r: Regeln) {
        prefs(context).edit().putString("regeln", json(r, GeraeteApps.ids(context)).toString()).commit()
    }

    fun zugriff(context: Context): Boolean = runCatching {
        val ops = context.getSystemService(AppOpsManager::class.java)
        val modus = if (Build.VERSION.SDK_INT >= 29) ops.unsafeCheckOpNoThrow(AppOpsManager.OPSTR_GET_USAGE_STATS, Process.myUid(), context.packageName)
        else @Suppress("DEPRECATION") ops.checkOpNoThrow(AppOpsManager.OPSTR_GET_USAGE_STATS, Process.myUid(), context.packageName)
        if (modus == AppOpsManager.MODE_DEFAULT) context.checkSelfPermission(android.Manifest.permission.PACKAGE_USAGE_STATS) == PackageManager.PERMISSION_GRANTED
        else modus == AppOpsManager.MODE_ALLOWED
    }.getOrDefault(false)

    private fun tagesbeginn(): Long = ms(LocalDate.now().atStartOfDay())

    private fun tagWechsel(context: Context) {
        val heute = LocalDate.now().toString()
        val p = prefs(context)
        if (p.getString("tag", "") == heute) return
        p.edit().apply {
            p.all.keys.filter { it.startsWith("ms-") }.forEach { remove(it) }
            putString("tag", heute)
            val laufApp = p.getString("lauf-app", null)
            if (laufApp != null) putLong("lauf-seit", maxOf(p.getLong("lauf-seit", 0L), tagesbeginn()))
        }.commit()
    }

    private fun ereignisse(context: Context, von: Long, bis: Long): Pair<Map<String, Long>, String?> {
        val usm = context.getSystemService(UsageStatsManager::class.java)
        val pakete = GeraeteApps.liste(context).associate { it.paket to it.id }
        val summe = mutableMapOf<String, Long>()
        val offen = mutableMapOf<String, Long>()
        val liste = usm.queryEvents(von - 3 * 3_600_000L, bis) ?: return emptyMap<String, Long>() to null
        val e = UsageEvents.Event()
        while (liste.hasNextEvent()) {
            liste.getNextEvent(e)
            val app = pakete[e.packageName] ?: continue
            when (e.eventType) {
                VORNE -> offen.putIfAbsent(app, e.timeStamp)
                WEG, GESTOPPT -> offen.remove(app)?.let { start -> summe.merge(app, (e.timeStamp - maxOf(start, von)).coerceAtLeast(0L), Long::plus) }
            }
        }
        offen.forEach { (app, start) -> summe.merge(app, (bis - maxOf(start, von)).coerceAtLeast(0L), Long::plus) }
        return summe to offen.maxByOrNull { it.value }?.key
    }

    fun genutzt(context: Context): Map<String, Long> {
        tagWechsel(context)
        val jetzt = System.currentTimeMillis()
        if (zugriff(context)) {
            val (summe, _) = runCatching { ereignisse(context, tagesbeginn(), jetzt) }.getOrDefault(emptyMap<String, Long>() to null)
            return GeraeteApps.ids(context).associateWith { summe[it] ?: 0L }
        }
        val p = prefs(context)
        val laufApp = p.getString("lauf-app", null)
        val seit = p.getLong("lauf-seit", jetzt)
        return GeraeteApps.ids(context).associateWith { app ->
            p.getLong("ms-$app", 0L) + if (app == laufApp) (jetzt - seit).coerceIn(0L, SITZUNG_MAX) else 0L
        }
    }

    fun vordergrund(context: Context): String? {
        if (zugriff(context)) {
            val jetzt = System.currentTimeMillis()
            return runCatching { ereignisse(context, jetzt - 2 * 3_600_000L, jetzt).second }.getOrNull()
        }
        return prefs(context).getString("lauf-app", null)
    }

    private fun meldung(context: Context, grund: Sperrgrund, app: String, r: Regeln): String {
        val name = GeraeteApps.name(context, app)
        return when (grund) {
            Sperrgrund.PAUSE -> "Gerade ist Pause bis ${uhr(r.pauseBis)} Uhr. $name geht danach wieder."
            Sperrgrund.NACHT -> "Schlafenszeit bis ${Zeitregeln.zeitText(r.nacht.bis)} Uhr. $name ist bis dahin gesperrt."
            Sperrgrund.LIMIT -> "Deine Zeit für $name ist für heute aufgebraucht (${r.limits[app]} Minuten)."
        }
    }

    fun darf(context: Context, app: String): String? {
        val r = regeln(context)
        val grund = Zeitregeln.grund(r, app, genutzt(context)[app] ?: 0L, System.currentTimeMillis(), LocalDateTime.now()) ?: return null
        return meldung(context, grund, app, r)
    }

    fun pruefeStart(context: Context, app: String) {
        darf(context, app)?.let { throw IllegalStateException(it) }
    }

    fun gestartet(context: Context, app: String) {
        tagWechsel(context)
        sitzungBeenden(context)
        prefs(context).edit().putString("lauf-app", app).putLong("lauf-seit", System.currentTimeMillis()).commit()
        runCatching { pruefen(context) }
    }

    private fun sitzungBeenden(context: Context) {
        val p = prefs(context)
        val app = p.getString("lauf-app", null) ?: return
        val dauer = (System.currentTimeMillis() - p.getLong("lauf-seit", System.currentTimeMillis())).coerceIn(0L, SITZUNG_MAX)
        p.edit().putLong("ms-$app", p.getLong("ms-$app", 0L) + dauer).remove("lauf-app").remove("lauf-seit").commit()
    }

    fun zurueck(context: Context) {
        tagWechsel(context)
        sitzungBeenden(context)
        runCatching { pruefen(context) }
    }

    private fun sperren(context: Context, apps: Set<String>) {
        val dpm = context.getSystemService(DevicePolicyManager::class.java)
        if (!dpm.isDeviceOwnerApp(context.packageName)) return
        val admin = ComponentName(context, JonAdmin::class.java)
        val p = prefs(context)
        val vorher = p.getStringSet("gesperrt", emptySet()).orEmpty()
        val jetzt = apps.filter { GeraeteApps.installiert(context, it) }.mapNotNull { GeraeteApps.paket(context, it) }.toSet()
        if (jetzt == vorher) return
        val frei = vorher - jetzt
        if (jetzt.isNotEmpty()) runCatching { dpm.setPackagesSuspended(admin, jetzt.toTypedArray(), true) }
        if (frei.isNotEmpty()) runCatching { dpm.setPackagesSuspended(admin, frei.toTypedArray(), false) }
        p.edit().putStringSet("gesperrt", jetzt).commit()
    }

    fun allesFreigeben(context: Context) {
        val dpm = context.getSystemService(DevicePolicyManager::class.java)
        val p = prefs(context)
        val vorher = p.getStringSet("gesperrt", emptySet()).orEmpty()
        if (vorher.isNotEmpty() && dpm.isDeviceOwnerApp(context.packageName)) {
            runCatching { dpm.setPackagesSuspended(ComponentName(context, JonAdmin::class.java), vorher.toTypedArray(), false) }
        }
        p.edit().putStringSet("gesperrt", emptySet()).commit()
    }

    private fun waechter(context: Context): PendingIntent =
        PendingIntent.getBroadcast(context, 4730, Intent(context, RegelWaechter::class.java).setAction("at.felworks.jon.regeln"), PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)

    private fun planen(context: Context, r: Regeln, genutzt: Map<String, Long>, jetzt: LocalDateTime, jetztMs: Long, vorne: String?) {
        val kandidaten = mutableListOf<Long>()
        if (r.pauseBis > jetztMs) kandidaten += r.pauseBis + 1000
        Zeitregeln.naechsteNachtgrenze(r.nacht, jetzt)?.let { kandidaten += ms(it) + 1000 }
        if (r.limits.isNotEmpty() || prefs(context).getStringSet("gesperrt", emptySet()).orEmpty().isNotEmpty()) kandidaten += ms(LocalDate.now().plusDays(1).atStartOfDay()) + 5000
        if (vorne != null) Zeitregeln.restMs(r, vorne, genutzt[vorne] ?: 0L, jetztMs)?.let { rest -> if (rest > 0) kandidaten += jetztMs + rest.coerceIn(5_000L, 5 * 60_000L) }
        r.ausnahmen.values.filter { it > jetztMs }.minOrNull()?.let { kandidaten += it + 1000 }
        val am = context.getSystemService(AlarmManager::class.java)
        val ziel = kandidaten.filter { it > jetztMs }.minOrNull()
        if (ziel == null) { am.cancel(waechter(context)); return }
        if (Build.VERSION.SDK_INT < 31 || am.canScheduleExactAlarms()) am.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, ziel, waechter(context))
        else am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, ziel, waechter(context))
    }

    @Synchronized
    fun pruefen(context: Context, holen: Boolean = false): JSONObject {
        val r = regeln(context)
        val jetztMs = System.currentTimeMillis()
        val jetzt = LocalDateTime.now()
        if (r.pauseBis in 1 until jetztMs) speichern(context, r.copy(pauseBis = 0L))
        val genutzt = genutzt(context)
        val gruende = GeraeteApps.ids(context).associateWith { Zeitregeln.grund(r, it, genutzt[it] ?: 0L, jetztMs, jetzt) }
        val gesperrt = gruende.filterValues { it != null }.keys
        sperren(context, gesperrt)
        val vorne = vordergrund(context)
        if (holen) {
            val beginn = Zeitregeln.nachtBeginn(r.nacht, jetzt)
            val p = prefs(context)
            if (beginn != null && p.getString("nacht-gezeigt", "") != beginn.toString()) {
                p.edit().putString("nacht-gezeigt", beginn.toString()).commit()
                Anzeige.zeigen(JSONObject().put("art", "nacht").put("id", "regel").put("bis", Zeitregeln.zeitText(r.nacht.bis))
                    .put("apps", JSONArray(GeraeteApps.ids(context).filter { it in r.nacht.apps }.map { GeraeteApps.name(context, it) })))
                Anzeige.jonHolen(context, false)
            } else if (vorne != null && vorne in gesperrt) {
                val grund = gruende[vorne]!!
                Anzeige.zeigen(JSONObject().put("art", "regel").put("id", "regel").put("grund", grund.name.lowercase()).put("app", vorne)
                    .put("name", GeraeteApps.name(context, vorne)).put("text", meldung(context, grund, vorne, r)).put("anfragbar", true))
                Anzeige.jonHolen(context, false)
            }
        }
        planen(context, r, genutzt, jetzt, jetztMs, vorne)
        return stand(context, r, genutzt, gruende)
    }

    private fun stand(context: Context, r: Regeln, genutzt: Map<String, Long>, gruende: Map<String, Sperrgrund?>): JSONObject {
        val jetzt = LocalDateTime.now()
        val minuten = JSONObject()
        val rest = JSONObject()
        val sperre = JSONObject()
        val apps = GeraeteApps.liste(context)
        val liste = JSONArray()
        apps.forEach { a ->
            val app = a.id
            minuten.put(app, ((genutzt[app] ?: 0L) / 60_000L).toInt())
            Zeitregeln.restMs(r, app, genutzt[app] ?: 0L)?.let { rest.put(app, ((it + 59_999L) / 60_000L).toInt()) }
            gruende[app]?.let { sperre.put(app, it.name.lowercase()) }
            liste.put(JSONObject().put("id", app).put("name", a.name).put("paket", a.paket))
        }
        val dpm = context.getSystemService(DevicePolicyManager::class.java)
        val jetztMs = System.currentTimeMillis()
        val freiBis = JSONObject().apply { r.ausnahmen.forEach { (app, bis) -> if (bis > jetztMs) put(app, uhr(bis)) } }
        return json(r, apps.map { it.id }).put("apps", liste).put("genutzt", minuten).put("rest", rest).put("gesperrt", sperre).put("frei_bis", freiBis)
            .put("nacht_aktiv", Zeitregeln.nachtAktiv(r.nacht, jetzt))
            .put("nacht_ende", Zeitregeln.nachtEnde(r.nacht, jetzt)?.let { Zeitregeln.zeitText(it.toLocalTime()) } ?: JSONObject.NULL)
            .put("pause_aktiv", r.pauseBis > System.currentTimeMillis())
            .put("pause_ende", if (r.pauseBis > System.currentTimeMillis()) uhr(r.pauseBis) else JSONObject.NULL)
            .put("zugriff", zugriff(context)).put("verwaltet", dpm.isDeviceOwnerApp(context.packageName))
            .put("tag", LocalDate.now().toString()).put("anfrage", anfrage(context) ?: JSONObject.NULL)
    }

    fun anfrage(context: Context): JSONObject? {
        val roh = prefs(context).getString("anfrage", null) ?: return null
        val a = runCatching { JSONObject(roh) }.getOrNull()
        if (a == null || System.currentTimeMillis() - a.optLong("seit") > ANFRAGE_MAX) {
            prefs(context).edit().remove("anfrage").apply()
            return null
        }
        return a
    }

    fun anfrageMerken(context: Context, app: String, minuten: Int, kennung: String): JSONObject {
        val a = JSONObject().put("app", app).put("name", GeraeteApps.name(context, app)).put("minuten", minuten)
            .put("id", kennung).put("seit", System.currentTimeMillis())
        prefs(context).edit().putString("anfrage", a.toString()).commit()
        return a
    }

    fun antwort(context: Context, daten: JSONObject): JSONObject {
        val app = daten.optString("app")
        val erlaubt = daten.optBoolean("erlaubt")
        val minuten = daten.optInt("minuten", 0).coerceIn(0, 240)
        val name = daten.optString("name").take(60).ifBlank { GeraeteApps.name(context, app) }
        prefs(context).edit().remove("anfrage").commit()
        runCatching { pruefen(context) }
        val text = if (erlaubt) "Du hast $minuten Minuten mehr $name. Viel Spaß!" else "Diesmal gibt es keine Extra-Zeit für $name."
        val hinweis = if (erlaubt) Sprache.t(context, text, "You got $minuten more minutes of $name. Have fun!") else Sprache.t(context, text, "No extra time for $name this time.")
        if (erlaubt) Anzeige.entfernen("regel")
        Anzeige.zeigen(JSONObject().put("art", "zeitantwort").put("id", "zeitantwort").put("app", app).put("name", name)
            .put("erlaubt", erlaubt).put("minuten", minuten).put("text", text).put("seit", System.currentTimeMillis()))
        if (!Sichtbarkeit.vorne) Benachrichtigung.familie(context, if (erlaubt) Sprache.t(context, "Extra-Zeit bekommen", "Extra time granted") else Sprache.t(context, "Keine Extra-Zeit", "No extra time"), hinweis, "zeit")
        return JSONObject().put("angezeigt", true)
    }

    fun stand(context: Context): JSONObject = pruefen(context)

    fun setzen(context: Context, daten: JSONObject): JSONObject {
        val alt = regeln(context)
        var neu = lesen(daten, alt, GeraeteApps.ids(context).toSet())
        if (daten.has("pause_minuten")) {
            val minuten = daten.optInt("pause_minuten", 0).coerceIn(0, 24 * 60)
            neu = neu.copy(pauseBis = if (minuten == 0) 0L else System.currentTimeMillis() + minuten * 60_000L)
        }
        speichern(context, neu)
        return pruefen(context, true)
    }

    fun ausnahmeGeben(context: Context, app: String, minuten: Int): JSONObject {
        require(minuten in 1..240) { "Zwischen 1 und 240 Minuten." }
        val r = regeln(context)
        val jetztMs = System.currentTimeMillis()
        speichern(context, r.copy(ausnahmen = r.ausnahmen.filterValues { it > jetztMs } + (app to jetztMs + minuten * 60_000L)))
        return pruefen(context)
    }

    fun fokus(context: Context, minuten: Int): JSONObject {
        require(minuten in 5..240) { "Fokuszeit geht von 5 bis 240 Minuten." }
        val r = regeln(context)
        val ende = System.currentTimeMillis() + minuten * 60_000L
        speichern(context, r.copy(pauseBis = maxOf(r.pauseBis, ende)))
        return pruefen(context, true)
    }
}
