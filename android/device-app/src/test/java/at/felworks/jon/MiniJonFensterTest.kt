package at.felworks.jon

import at.felworks.jon.device.MiniJonFenster
import org.junit.Assert.assertEquals
import org.junit.Test

class MiniJonFensterTest {
    @Test fun kioskWechselUndRueckkehr() {
        assertEquals(MiniJonFenster.OVERLAY, MiniJonFenster.waehlen(false, true, true))
        assertEquals(MiniJonFenster.APP, MiniJonFenster.waehlen(true, true, true))
        assertEquals(MiniJonFenster.WARTEN, MiniJonFenster.waehlen(true, false, true))
        assertEquals(MiniJonFenster.APP, MiniJonFenster.waehlen(true, true, true))
        assertEquals(MiniJonFenster.OVERLAY, MiniJonFenster.waehlen(false, false, true))
    }

    @Test fun keineFremdenFensterOhneFreigabe() {
        assertEquals(MiniJonFenster.WARTEN, MiniJonFenster.waehlen(false, true, false))
        assertEquals(MiniJonFenster.WARTEN, MiniJonFenster.waehlen(false, false, false))
    }
}
