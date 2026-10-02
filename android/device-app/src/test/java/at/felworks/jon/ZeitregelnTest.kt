package at.felworks.jon

import at.felworks.jon.device.Nachtruhe
import at.felworks.jon.device.Regeln
import at.felworks.jon.device.Sperrgrund
import at.felworks.jon.device.Uhrbefehl
import at.felworks.jon.device.Zeitregeln
import org.junit.Assert.*
import org.junit.Test
import java.time.LocalDateTime
import java.time.LocalTime

class ZeitregelnTest {
    private val nacht = Nachtruhe(an = true, von = LocalTime.of(21, 0), bis = LocalTime.of(6, 30), tage = setOf(1, 2, 3, 4, 7))

    @Test fun nachtUeberMitternacht() {
        val sonntagAbend = LocalDateTime.of(2026, 9, 27, 22, 0)
        assertTrue(Zeitregeln.nachtAktiv(nacht, sonntagAbend))
        assertEquals(LocalDateTime.of(2026, 9, 28, 6, 30), Zeitregeln.nachtEnde(nacht, sonntagAbend))
        assertTrue(Zeitregeln.nachtAktiv(nacht, LocalDateTime.of(2026, 9, 28, 5, 59)))
        assertFalse(Zeitregeln.nachtAktiv(nacht, LocalDateTime.of(2026, 9, 28, 6, 30)))
        val freitagNacht = LocalDateTime.of(2026, 10, 2, 23, 0)
        assertFalse(Zeitregeln.nachtAktiv(nacht, freitagNacht))
        assertFalse(Zeitregeln.nachtAktiv(nacht, LocalDateTime.of(2026, 10, 3, 2, 0)))
        assertFalse(Zeitregeln.nachtAktiv(nacht.copy(an = false), sonntagAbend))
    }

    @Test fun naechsteGrenze() {
        val mittag = LocalDateTime.of(2026, 9, 28, 12, 0)
        assertEquals(LocalDateTime.of(2026, 9, 28, 21, 0), Zeitregeln.naechsteNachtgrenze(nacht, mittag))
        val nachts = LocalDateTime.of(2026, 9, 29, 1, 0)
        assertEquals(LocalDateTime.of(2026, 9, 29, 6, 30), Zeitregeln.naechsteNachtgrenze(nacht, nachts))
        val donnerstag = LocalDateTime.of(2026, 10, 1, 7, 0)
        assertEquals(LocalDateTime.of(2026, 10, 1, 21, 0), Zeitregeln.naechsteNachtgrenze(nacht, donnerstag))
        val freitagMorgen = LocalDateTime.of(2026, 10, 2, 7, 0)
        assertEquals(LocalDateTime.of(2026, 10, 4, 21, 0), Zeitregeln.naechsteNachtgrenze(nacht, freitagMorgen))
    }

    @Test fun tagesfensterOhneMitternacht() {
        val lernzeit = Nachtruhe(an = true, von = LocalTime.of(14, 0), bis = LocalTime.of(16, 0), tage = setOf(1), apps = setOf("tiktok"))
        assertTrue(Zeitregeln.nachtAktiv(lernzeit, LocalDateTime.of(2026, 9, 28, 15, 0)))
        assertFalse(Zeitregeln.nachtAktiv(lernzeit, LocalDateTime.of(2026, 9, 29, 15, 0)))
        val regeln = Regeln(nacht = lernzeit)
        assertEquals(Sperrgrund.NACHT, Zeitregeln.grund(regeln, "tiktok", 0, 0, LocalDateTime.of(2026, 9, 28, 15, 0)))
        assertNull(Zeitregeln.grund(regeln, "whatsapp", 0, 0, LocalDateTime.of(2026, 9, 28, 15, 0)))
    }

    @Test fun limitsUndPause() {
        val regeln = Regeln(limits = mapOf("tiktok" to 30))
        val jetzt = LocalDateTime.of(2026, 9, 28, 12, 0)
        assertNull(Zeitregeln.grund(regeln, "tiktok", 29 * 60_000L, 1000, jetzt))
        assertEquals(Sperrgrund.LIMIT, Zeitregeln.grund(regeln, "tiktok", 30 * 60_000L, 1000, jetzt))
        assertNull(Zeitregeln.grund(regeln, "amazon", 999 * 60_000L, 1000, jetzt))
        assertEquals(60_000L, Zeitregeln.restMs(regeln, "tiktok", 29 * 60_000L))
        assertNull(Zeitregeln.restMs(regeln, "whatsapp", 0))
        assertEquals(Sperrgrund.PAUSE, Zeitregeln.grund(regeln.copy(pauseBis = 5000), "amazon", 0, 1000, jetzt))
    }

    @Test fun weckerZeitpunkte() {
        val jetzt = LocalDateTime.of(2026, 9, 28, 7, 0)
        assertEquals(LocalDateTime.of(2026, 9, 29, 6, 30), Zeitregeln.naechsterWecker(6, 30, emptySet(), jetzt))
        assertEquals(LocalDateTime.of(2026, 9, 28, 7, 30), Zeitregeln.naechsterWecker(7, 30, emptySet(), jetzt))
        assertEquals(LocalDateTime.of(2026, 10, 3, 9, 0), Zeitregeln.naechsterWecker(9, 0, setOf(6), jetzt))
    }

    @Test fun zeitLesen() {
        assertEquals(LocalTime.of(6, 5), Zeitregeln.zeitLesen("06:05"))
        assertNull(Zeitregeln.zeitLesen("25:00"))
        assertNull(Zeitregeln.zeitLesen("abc"))
    }

    @Test fun sprachbefehleWecker() {
        assertEquals(Uhrbefehl.Wecker(6, 30), Zeitregeln.uhrbefehl("Weck mich um 6:30 Uhr."))
        assertEquals(Uhrbefehl.Wecker(7, 0), Zeitregeln.uhrbefehl("Stell einen Wecker auf 7 Uhr"))
        assertEquals(Uhrbefehl.Wecker(6, 30), Zeitregeln.uhrbefehl("weck mich um halb sieben"))
        assertEquals(Uhrbefehl.Wecker(6, 30), Zeitregeln.uhrbefehl("Wecker für 6 Uhr dreißig"))
        assertEquals(Uhrbefehl.Wecker(7, 0), Zeitregeln.uhrbefehl("weck mich um sieben"))
        assertEquals(Uhrbefehl.Wecker(8, 45), Zeitregeln.uhrbefehl("stelle einen wecker für viertel vor neun"))
        assertEquals(Uhrbefehl.Timer(20 * 60), Zeitregeln.uhrbefehl("weck mich in 20 Minuten"))
    }

    @Test fun sprachbefehleTimer() {
        assertEquals(Uhrbefehl.Timer(600), Zeitregeln.uhrbefehl("Timer 10 Minuten"))
        assertEquals(Uhrbefehl.Timer(300), Zeitregeln.uhrbefehl("Stell einen Timer auf fünf Minuten"))
        assertEquals(Uhrbefehl.Timer(1800), Zeitregeln.uhrbefehl("Timer für eine halbe Stunde"))
        assertEquals(Uhrbefehl.Timer(5400), Zeitregeln.uhrbefehl("timer 1 stunde 30 minuten"))
        assertEquals(Uhrbefehl.Timer(90), Zeitregeln.uhrbefehl("Starte einen Timer für 90 Sekunden"))
        assertEquals(Uhrbefehl.Timer(1500), Zeitregeln.uhrbefehl("fünfundzwanzig Minuten Timer"))
        assertEquals(Uhrbefehl.TimerAus, Zeitregeln.uhrbefehl("Timer abbrechen"))
        assertEquals(Uhrbefehl.Stopp, Zeitregeln.uhrbefehl("Wecker aus"))
    }

    @Test fun keineFalschenTreffer() {
        assertNull(Zeitregeln.uhrbefehl("Erkläre mir, wie ein Timer funktioniert"))
        assertNull(Zeitregeln.uhrbefehl("Was ist ein Wecker?"))
        assertNull(Zeitregeln.uhrbefehl("Timer"))
        assertNull(Zeitregeln.uhrbefehl("Stell einen Wecker"))
        assertNull(Zeitregeln.uhrbefehl("Wie spät ist es um 7 Uhr in New York"))
    }

    @Test fun dauerText() {
        assertEquals("10 Minuten", Zeitregeln.dauerText(600))
        assertEquals("1 Stunde 30 Minuten", Zeitregeln.dauerText(5400))
        assertEquals("1 Minute 30 Sekunden", Zeitregeln.dauerText(90))
    }

    @Test fun ausnahmeHebtSperreAuf() {
        val jetzt = LocalDateTime.of(2026, 9, 28, 15, 0)
        val regeln = Regeln(limits = mapOf("tiktok" to 30), pauseBis = 50_000L, ausnahmen = mapOf("tiktok" to 10_000L))
        assertNull(Zeitregeln.grund(regeln, "tiktok", 60 * 60_000L, 5_000L, jetzt))
        assertEquals(Sperrgrund.PAUSE, Zeitregeln.grund(regeln, "tiktok", 60 * 60_000L, 20_000L, jetzt))
        assertEquals(Sperrgrund.LIMIT, Zeitregeln.grund(regeln.copy(pauseBis = 0L), "tiktok", 60 * 60_000L, 20_000L, jetzt))
        assertEquals(5_000L, Zeitregeln.restMs(regeln, "tiktok", 0, 5_000L))
        assertEquals(Sperrgrund.PAUSE, Zeitregeln.grund(regeln, "com.google.android.youtube", 0, 5_000L, jetzt))
    }
}
