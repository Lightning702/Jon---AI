package at.felworks.jon

import android.content.Context
import android.content.ContextWrapper
import android.content.SharedPreferences
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import at.felworks.jon.device.AdminSchutz
import at.felworks.jon.device.GeraeteModus
import at.felworks.jon.device.SprachDienst
import at.felworks.jon.device.SprachPhase
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class SprachPraxisTest {
    @Test fun pinRecoveryUndFehlversuche() {
        val original = InstrumentationRegistry.getInstrumentation().targetContext
        val context = object : ContextWrapper(original) {
            override fun getSharedPreferences(name: String, mode: Int): SharedPreferences = original.getSharedPreferences("pruefung-$name", mode)
        }
        fun leeren() {
            listOf("jon-device", "jon-tresor").forEach { context.getSharedPreferences(it, Context.MODE_PRIVATE).edit().clear().commit() }
        }
        leeren()
        val admin = AdminSchutz(context)
        try {
            val code = admin.einrichten("384729")
            assertFalse(admin.bestaetigt)
            admin.recoveryBestaetigen()
            admin.sperren()
            assertTrue(admin.eingerichtet)
            assertFalse(admin.frei)
            assertFalse(admin.pruefen("000000"))
            assertTrue(admin.pruefen("384729"))
            admin.sperren()
            assertTrue(admin.pruefen(code, true))
            assertFalse(admin.bestaetigt)
            admin.sperren()
            assertFalse(admin.pruefen(code, true))
            repeat(4) { assertFalse(admin.pruefen("000000")) }
            assertTrue(runCatching { admin.pruefen("384729") }.isFailure)
            assertFalse(context.getSharedPreferences("jon-tresor", Context.MODE_PRIVATE).all.toString().contains("384729"))
        } finally { admin.sperren(); leeren() }
    }

    @Test fun mikrofonStartetNurAufKnopfdruck() {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val context = instrumentation.targetContext
        instrumentation.uiAutomation.executeShellCommand("pm grant ${context.packageName} android.permission.RECORD_AUDIO").close()
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            try {
                Thread.sleep(1500)
                assertFalse(SprachDienst.zustand.value.offen)
                scenario.onActivity { SprachDienst.starten(it, true, true) }
                val stand = runBlocking {
                    withTimeout(30_000) {
                        SprachDienst.zustand.first { (it.offen && it.phase == SprachPhase.LISTENING) || it.phase == SprachPhase.ERROR }
                    }
                }
                assertEquals(stand.fehler, SprachPhase.LISTENING, stand.phase)
                scenario.onActivity { SprachDienst.schliessen(it) }
                val ende = runBlocking { withTimeout(10_000) { SprachDienst.zustand.first { !it.offen } } }
                assertFalse(ende.offen)
            } finally {
                SprachDienst.stoppen(context)
            }
        }
    }
}
