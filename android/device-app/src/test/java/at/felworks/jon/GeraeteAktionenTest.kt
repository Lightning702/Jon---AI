package at.felworks.jon

import at.felworks.jon.device.GeraeteApps
import at.felworks.jon.device.JonApp
import org.junit.Assert.*
import org.junit.Test

class GeraeteAktionenTest {
    @Test fun nurExpliziteStartbefehle() {
        assertEquals("tiktok" to "oeffnen", GeraeteApps.sprachAktion("Öffne TikTok"))
        assertEquals("whatsapp" to "oeffnen", GeraeteApps.sprachAktion("Starte WhatsApp"))
        assertEquals("amazon" to "pause", GeraeteApps.sprachAktion("Musik pausieren"))
        assertNull(GeraeteApps.sprachAktion("Erkläre mir, wie ich TikTok öffne"))
        assertNull(GeraeteApps.sprachAktion("Öffne die Einstellungen"))
        assertNull(GeraeteApps.sprachAktion("Schreibe Mama auf WhatsApp"))
    }

    @Test fun freieAppAuswahl() {
        val apps = listOf(JonApp("com.google.android.youtube", "com.google.android.youtube", "YouTube"), JonApp("whatsapp", "com.whatsapp", "WhatsApp"))
        assertEquals("com.google.android.youtube" to "oeffnen", GeraeteApps.sprachAktion("Öffne YouTube", apps))
        assertEquals("com.google.android.youtube" to "oeffnen", GeraeteApps.sprachAktion("bitte starte die YouTube App", apps))
        assertNull(GeraeteApps.sprachAktion("Öffne TikTok", apps))
        assertNull(GeraeteApps.sprachAktion("Öffne die Einstellungen", apps))
        assertEquals("whatsapp", GeraeteApps.finden(apps, "Whats App")?.id)
        assertEquals("com.google.android.youtube", GeraeteApps.finden(apps, "com.google.android.youtube")?.id)
        assertNull(GeraeteApps.finden(apps, "Netflix"))
    }
}
