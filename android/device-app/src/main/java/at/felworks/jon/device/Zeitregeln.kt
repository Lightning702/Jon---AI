package at.felworks.jon.device

import java.time.LocalDateTime
import java.time.LocalTime

data class Nachtruhe(
    val an: Boolean = false,
    val von: LocalTime = LocalTime.of(21, 0),
    val bis: LocalTime = LocalTime.of(6, 30),
    val tage: Set<Int> = (1..7).toSet(),
    val apps: Set<String> = setOf("whatsapp", "tiktok", "amazon"),
)

data class Regeln(
    val limits: Map<String, Int> = emptyMap(),
    val nacht: Nachtruhe = Nachtruhe(),
    val pauseBis: Long = 0L,
    val ausnahmen: Map<String, Long> = emptyMap(),
)

enum class Sperrgrund { PAUSE, NACHT, LIMIT }

sealed class Uhrbefehl {
    data class Wecker(val stunde: Int, val minute: Int) : Uhrbefehl()
    data class Timer(val sekunden: Int) : Uhrbefehl()
    object Stopp : Uhrbefehl()
    object TimerAus : Uhrbefehl()
}

object Zeitregeln {
    fun nachtAktiv(n: Nachtruhe, jetzt: LocalDateTime): Boolean = nachtBeginn(n, jetzt) != null

    fun nachtBeginn(n: Nachtruhe, jetzt: LocalDateTime): LocalDateTime? {
        if (!n.an || n.von == n.bis) return null
        for (versatz in 0L..1L) {
            val tag = jetzt.toLocalDate().minusDays(versatz)
            if (tag.dayOfWeek.value !in n.tage) continue
            val beginn = LocalDateTime.of(tag, n.von)
            val ende = if (n.von < n.bis) LocalDateTime.of(tag, n.bis) else LocalDateTime.of(tag.plusDays(1), n.bis)
            if (!jetzt.isBefore(beginn) && jetzt.isBefore(ende)) return beginn
        }
        return null
    }

    fun nachtEnde(n: Nachtruhe, jetzt: LocalDateTime): LocalDateTime? {
        val beginn = nachtBeginn(n, jetzt) ?: return null
        return if (n.von < n.bis) LocalDateTime.of(beginn.toLocalDate(), n.bis) else LocalDateTime.of(beginn.toLocalDate().plusDays(1), n.bis)
    }

    fun naechsteNachtgrenze(n: Nachtruhe, jetzt: LocalDateTime): LocalDateTime? {
        if (!n.an || n.von == n.bis || n.tage.isEmpty()) return null
        var beste: LocalDateTime? = null
        for (versatz in -1L..8L) {
            val tag = jetzt.toLocalDate().plusDays(versatz)
            if (tag.dayOfWeek.value !in n.tage) continue
            val beginn = LocalDateTime.of(tag, n.von)
            val ende = if (n.von < n.bis) LocalDateTime.of(tag, n.bis) else LocalDateTime.of(tag.plusDays(1), n.bis)
            for (kandidat in listOf(beginn, ende)) {
                if (kandidat.isAfter(jetzt) && (beste == null || kandidat.isBefore(beste))) beste = kandidat
            }
        }
        return beste
    }

    fun ausnahme(r: Regeln, app: String, jetztMs: Long): Boolean = (r.ausnahmen[app] ?: 0L) > jetztMs

    fun grund(r: Regeln, app: String, genutztMs: Long, jetztMs: Long, jetzt: LocalDateTime): Sperrgrund? {
        if (ausnahme(r, app, jetztMs)) return null
        if (r.pauseBis > jetztMs) return Sperrgrund.PAUSE
        if (app in r.nacht.apps && nachtAktiv(r.nacht, jetzt)) return Sperrgrund.NACHT
        val limit = r.limits[app] ?: 0
        if (limit > 0 && genutztMs >= limit * 60_000L) return Sperrgrund.LIMIT
        return null
    }

    fun restMs(r: Regeln, app: String, genutztMs: Long, jetztMs: Long = System.currentTimeMillis()): Long? {
        val bis = r.ausnahmen[app] ?: 0L
        if (bis > jetztMs) return bis - jetztMs
        val limit = r.limits[app] ?: 0
        return if (limit > 0) (limit * 60_000L - genutztMs).coerceAtLeast(0) else null
    }

    fun zeitText(t: LocalTime): String = "%02d:%02d".format(t.hour, t.minute)

    fun zeitLesen(text: String): LocalTime? {
        val treffer = Regex("^(\\d{1,2}):(\\d{2})$").matchEntire(text.trim()) ?: return null
        val stunde = treffer.groupValues[1].toInt()
        val minute = treffer.groupValues[2].toInt()
        return if (stunde in 0..23 && minute in 0..59) LocalTime.of(stunde, minute) else null
    }

    fun naechsterWecker(stunde: Int, minute: Int, tage: Set<Int>, jetzt: LocalDateTime): LocalDateTime {
        val zeit = LocalTime.of(stunde, minute)
        for (versatz in 0L..7L) {
            val tag = jetzt.toLocalDate().plusDays(versatz)
            val kandidat = LocalDateTime.of(tag, zeit)
            if (!kandidat.isAfter(jetzt)) continue
            if (tage.isEmpty() || tag.dayOfWeek.value in tage) return kandidat
        }
        return LocalDateTime.of(jetzt.toLocalDate().plusDays(8), zeit)
    }

    private val zahlwoerter = mapOf(
        "ein" to 1, "eine" to 1, "einen" to 1, "eins" to 1, "einer" to 1, "zwei" to 2, "drei" to 3, "vier" to 4, "fünf" to 5,
        "sechs" to 6, "sieben" to 7, "acht" to 8, "neun" to 9, "zehn" to 10, "elf" to 11, "zwölf" to 12, "dreizehn" to 13,
        "vierzehn" to 14, "fünfzehn" to 15, "sechzehn" to 16, "siebzehn" to 17, "achtzehn" to 18, "neunzehn" to 19,
        "zwanzig" to 20, "dreißig" to 30, "vierzig" to 40, "fünfzig" to 50, "sechzig" to 60, "neunzig" to 90
    )
    private val zehner = mapOf("zwanzig" to 20, "dreißig" to 30, "vierzig" to 40, "fünfzig" to 50)

    private fun zahl(wort: String): Int? {
        wort.toIntOrNull()?.let { return it }
        zahlwoerter[wort]?.let { return it }
        val teile = Regex("^(ein|zwei|drei|vier|fünf|sechs|sieben|acht|neun)und(zwanzig|dreißig|vierzig|fünfzig)$").matchEntire(wort) ?: return null
        return (zahlwoerter[teile.groupValues[1]] ?: return null) + (zehner[teile.groupValues[2]] ?: return null)
    }

    private fun normalisieren(text: String): String = text.lowercase()
        .replace(Regex("[,!?]"), " ").trim().replace(Regex("\\.$"), "")
        .replace(Regex("(\\d)\\.(\\d{2})"), "$1:$2")
        .replace(Regex("\\s+"), " ").trim()

    private fun uhrzeit(text: String): Pair<Int, Int>? {
        Regex("(?:^| )halb (\\S+)").find(text)?.let { m ->
            val h = zahl(m.groupValues[1]) ?: return null
            if (h in 1..24) return ((h - 1 + 24) % 24) to 30
        }
        Regex("(?:^| )viertel nach (\\S+)").find(text)?.let { m -> val h = zahl(m.groupValues[1]) ?: return null; if (h in 0..23) return h to 15 }
        Regex("(?:^| )viertel vor (\\S+)").find(text)?.let { m -> val h = zahl(m.groupValues[1]) ?: return null; if (h in 1..24) return ((h - 1 + 24) % 24) to 45 }
        Regex("(\\d{1,2}):(\\d{2})").find(text)?.let { m ->
            val h = m.groupValues[1].toInt(); val mi = m.groupValues[2].toInt()
            return if (h in 0..23 && mi in 0..59) h to mi else null
        }
        Regex("(?:um|auf|für|für morgen|morgen um|morgen) (\\S+) uhr(?: (\\S+))?").find(text)?.let { m ->
            val h = zahl(m.groupValues[1]) ?: return null
            val mi = m.groupValues[2].takeIf { it.isNotBlank() }?.let(::zahl) ?: 0
            return if (h in 0..23 && mi in 0..59) h to mi else null
        }
        Regex("(?:^| )(\\S+) uhr(?: (\\S+))?").find(text)?.let { m ->
            val h = zahl(m.groupValues[1]) ?: return null
            val mi = m.groupValues[2].takeIf { it.isNotBlank() }?.let(::zahl) ?: 0
            return if (h in 0..23 && mi in 0..59) h to mi else null
        }
        Regex("(?:um|auf|für) (\\S+)$").find(text)?.let { m ->
            val h = zahl(m.groupValues[1]) ?: return null
            return if (h in 0..23) h to 0 else null
        }
        return null
    }

    private fun dauer(text: String): Int? {
        var sekunden = 0
        var gefunden = false
        if (Regex("(?:^| )(eine |einer )?halben? stunde").containsMatchIn(text)) { sekunden += 1800; gefunden = true }
        if (Regex("(?:^| )(eine )?viertelstunde").containsMatchIn(text)) { sekunden += 900; gefunden = true }
        for (m in Regex("(\\S+) ?(stunden|stunde|std|minuten|minute|min|sekunden|sekunde|sek)(?= |$)").findAll(text)) {
            val n = zahl(m.groupValues[1]) ?: continue
            sekunden += n * when {
                m.groupValues[2].startsWith("st") -> 3600
                m.groupValues[2].startsWith("m") -> 60
                else -> 1
            }
            gefunden = true
        }
        return if (gefunden && sekunden in 1..86_400) sekunden else null
    }

    fun uhrbefehl(roh: String): Uhrbefehl? {
        val text = normalisieren(roh)
        if (text.isBlank() || text.length > 90) return null
        if (Regex("^(bitte )?(wecker|alarm|klingeln) (aus|stopp|stop|beenden)( bitte)?$").matches(text) || Regex("^(stopp|stop|sei still|ruhe)$").matches(text)) return Uhrbefehl.Stopp
        if (Regex("^(bitte )?(den |alle )?timer (aus|abbrechen|stoppen|stopp|löschen|beenden)( bitte)?$").matches(text) || Regex("^(bitte )?(brich|lösche|stopp|stoppe) (den |alle )?timer( ab)?$").matches(text)) return Uhrbefehl.TimerAus
        val weckWunsch = Regex("^(bitte )?(weck|wecke) mich").containsMatchIn(text) ||
            Regex("^(bitte )?((stell|stelle|setz|setze|mach|mache)( mir| bitte)* (einen |den |nen )?)?wecker( (auf|für|um|morgen))").containsMatchIn(text)
        if (weckWunsch) {
            if (Regex("(^| )in (\\S+) ?(minuten|minute|stunden|stunde)").containsMatchIn(text)) return dauer(text)?.let { Uhrbefehl.Timer(it) }
            val (h, mi) = uhrzeit(text) ?: return null
            return Uhrbefehl.Wecker(h, mi)
        }
        val timerWunsch = Regex("^(bitte )?((stell|stelle|setz|setze|starte|starten|mach|mache)( mir| bitte)* (einen |den |nen )?)?timer( |$)").containsMatchIn(text) ||
            Regex("^(\\S+ )+(minuten|minute|sekunden|stunden|stunde)[ -]?timer$").containsMatchIn(text)
        if (timerWunsch) return dauer(text)?.let { Uhrbefehl.Timer(it) }
        return null
    }

    fun dauerText(sekunden: Int): String {
        val h = sekunden / 3600
        val m = (sekunden % 3600) / 60
        val s = sekunden % 60
        val teile = mutableListOf<String>()
        if (h > 0) teile += if (h == 1) "1 Stunde" else "$h Stunden"
        if (m > 0) teile += if (m == 1) "1 Minute" else "$m Minuten"
        if (s > 0 && h == 0) teile += if (s == 1) "1 Sekunde" else "$s Sekunden"
        return teile.joinToString(" ").ifBlank { "0 Sekunden" }
    }
}
