package at.felworks.jon

import android.app.Application
import at.felworks.jon.core.AppBehaelter

class JonApplication : Application() {
    val behaelter by lazy { AppBehaelter(this) }
    override fun onCreate() {
        super.onCreate()
        behaelter
        at.felworks.jon.ki.Vorladen.beobachten(this)
        Thread { runCatching { at.felworks.jon.ki.Katalog.einmalAufraeumen(this) } }.start()
    }
}
