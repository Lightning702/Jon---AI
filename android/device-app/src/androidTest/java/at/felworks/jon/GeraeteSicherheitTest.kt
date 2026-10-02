package at.felworks.jon

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import at.felworks.jon.device.AdminSchutz
import at.felworks.jon.device.GeraeteApps
import at.felworks.jon.pairing.QrNutzlast
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class GeraeteSicherheitTest {
    @Test fun festePaketlisteUndKeineFremdenIntents() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        assertEquals("com.whatsapp", GeraeteApps.pakete["whatsapp"])
        assertTrue(runCatching { GeraeteApps.oeffnen(context, "com.android.settings") }.isFailure)
    }

    @Test fun doppelteAuftraegeUeberlebenNeueInstanz() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val id = "pruefung-${java.util.UUID.randomUUID()}"
        at.felworks.jon.device.AuftragsSpeicher(context).use { assertTrue(it.vormerken(id)) }
        at.felworks.jon.device.AuftragsSpeicher(context).use { assertFalse(it.vormerken(id)) }
    }

    @Test fun vpnProfilBleibtDirekt() {
        val payload = QrNutzlast.lesen("""{"t":"jon-pair","c":"123456789ABC","u":"http://100.100.20.30:8756","direct_only":true}""")
        assertNotNull(payload)
        assertTrue(payload!!.nurDirekt)
    }
}
