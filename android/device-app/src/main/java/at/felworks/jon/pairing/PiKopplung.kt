package at.felworks.jon.pairing

import android.os.Build
import at.felworks.jon.data.remote.DirektTransport
import at.felworks.jon.data.remote.Krypto
import at.felworks.jon.data.remote.Zugang
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.delay
import kotlinx.coroutines.withTimeout
import org.json.JSONObject
import java.net.URI

object PiKopplung {
    fun adressePruefen(text: String): String {
        val uri = URI(if (text.contains("://")) text.trim().trimEnd('/') else "http://${text.trim().trimEnd('/')}:8756")
        require(uri.scheme in setOf("http", "https") && uri.host != null && uri.userInfo == null && uri.query == null && uri.fragment == null && uri.path.isNullOrEmpty()) { "Nur die LAN- oder Tailscale-Adresse des Pi eingeben." }
        val host = uri.host.lowercase()
        val teile = host.split('.').mapNotNull { it.toIntOrNull() }
        val ip = teile.size == 4 && teile.all { it in 0..255 } && (teile[0] == 10 || teile[0] == 192 && teile[1] == 168 || teile[0] == 172 && teile[1] in 16..31 || teile[0] == 100 && teile[1] in 64..127)
        require(ip || host.endsWith(".ts.net") || host.startsWith("[fd7a:115c:a1e0:")) { "Eine private LAN- oder Tailscale-Adresse verwenden." }
        return uri.toString()
    }

    suspend fun verbinden(qr: QrNutzlast, status: (String) -> Unit): Zugang = withTimeout(180_000) {
        require(qr.nurDirekt) { "Im Desktop-Assistenten „Jon-Gerät einrichten“ einen VPN-Code erzeugen." }
        val key = Kopplungscode.schluessel(qr.code)
        val id = Kopplungscode.thema(qr.code)
        var verbindung: DirektTransport? = null
        for (adresse in qr.alleAdressen.take(6)) {
            val weg = DirektTransport(adressePruefen(adresse))
            status("Pi suchen …")
            try {
                val hallo = weg.senden(JSONObject().put("op", "hello").put("rid", Krypto.kennung(12)), "pair", id, key, 6000)
                if (hallo.optBoolean("ok")) { verbindung = weg; break }
            } catch (e: CancellationException) { weg.schliessen(); throw e }
            catch (_: Exception) { }
            weg.schliessen()
        }
        val weg = verbindung ?: error("Pi oder Code nicht erreichbar. Tailscale und den aktuellen Kopplungscode prüfen.")
        try {
            suspend fun ruf(op: String): JSONObject {
                val r = weg.senden(JSONObject().put("op", op).put("rid", Krypto.kennung(12)).put("name", "${Build.MANUFACTURER} ${Build.MODEL}").put("plattform", "Android ${Build.VERSION.RELEASE} · Jon Gerät"), "pair", id, key, 10_000)
                check(r.optBoolean("ok")) { r.optString("fehler", "Kopplung abgelehnt.") }
                return r
            }
            ruf("pair")
            status("Bitte dieses Handy in der Jon-Geräteverwaltung auf deinem PC oder Pi bestätigen.")
            while (true) {
                delay(1500)
                val r = ruf("pair-status")
                if (r.has("schluessel")) {
                    val pc = r.getJSONObject("pc")
                    val liste = r.optJSONArray("adressen")
                    val adressen = (qr.alleAdressen + (0 until (liste?.length() ?: 0)).map { liste!!.getString(it) }).distinct().map(::adressePruefen)
                    return@withTimeout Zugang(r.getString("geraet"), Krypto.unb64(r.getString("schluessel")), r.getString("token"), pc.getString("id"), pc.getString("name"), adressen.first(), adressen, "", 0, true)
                }
            }
            error("Kopplung beendet")
        } finally { weg.schliessen() }
    }
}
