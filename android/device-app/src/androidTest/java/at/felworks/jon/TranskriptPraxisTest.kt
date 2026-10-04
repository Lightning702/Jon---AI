package at.felworks.jon

import android.os.Bundle
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import at.felworks.jon.domain.model.Draht
import at.felworks.jon.ki.MedienAnalyse
import at.felworks.jon.ki.Weg
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

@RunWith(AndroidJUnit4::class)
class TranskriptPraxisTest {
    @Test fun langeAufnahmeLandetAlsDateiUndWirdZuegigTranskribiert() {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val context = instrumentation.targetContext
        val quelle = File(context.getExternalFilesDir(null), "jon-praxis-aufnahme.wav")
        val ton = File(context.cacheDir, "praxis-aufnahme.pcm")
        assumeTrue(quelle.length() > 100_000)
        ActivityScenario.launch(MainActivity::class.java)
        try {
            val behaelter = (context.applicationContext as JonApplication).behaelter
            val bis = System.currentTimeMillis() + 30_000
            while (behaelter.verbindung.lage.value.draht == Draht.AUS && System.currentTimeMillis() < bis) Thread.sleep(300)
            val laenge = MedienAnalyse.pcm(quelle, ton)
            assertEquals(laenge, ton.length())
            val start = System.currentTimeMillis()
            val meldungen = mutableListOf<String>()
            val text = runBlocking { MedienAnalyse.transkript(context, behaelter, Weg.PI, ton) { synchronized(meldungen) { meldungen += it } } }
            val dauer = System.currentTimeMillis() - start
            val sekunden = laenge / 32_000
            instrumentation.sendStatus(0, Bundle().apply { putString("bericht", "$sekunden s Audio in $dauer ms, ${text.length} Zeichen, Weg ${behaelter.verbindung.lage.value.draht}, letzte Meldung ${meldungen.lastOrNull()}, Anfang: ${text.take(160)}") })
            assertTrue(text, text.contains("Brot", ignoreCase = true))
            assertTrue("$dauer ms für $sekunden s", dauer < sekunden * 1000)
            val kurz = MedienAnalyse.kuerzen("a".repeat(50_000), 28_000)
            assertTrue(kurz.length <= 28_000 && kurz.contains("gekürzt"))
        } finally {
            ton.delete()
        }
    }
}
