package at.felworks.jon.device

import android.content.Context
import android.os.SystemClock
import android.util.Base64
import at.felworks.jon.security.Tresor
import java.security.MessageDigest
import java.security.SecureRandom
import javax.crypto.SecretKeyFactory
import javax.crypto.spec.PBEKeySpec
import org.json.JSONObject

class AdminSchutz(context: Context) {
    private val tresor = Tresor(context)
    private val prefs = context.getSharedPreferences("jon-device", Context.MODE_PRIVATE)
    val eingerichtet: Boolean get() = tresor.geheimnisVorhanden("admin")
    val bestaetigt: Boolean get() = prefs.getBoolean("recovery-bestaetigt", false)
    val frei: Boolean get() = SystemClock.elapsedRealtime() < offenBis

    fun einrichten(pin: String): String {
        require(!eingerichtet || frei) { "Zuerst Verwaltung entsperren." }
        require(pin.matches(Regex("[0-9]{6,12}"))) { "Die PIN braucht 6 bis 12 Ziffern." }
        val zufall = SecureRandom()
        val salt = ByteArray(24).also(zufall::nextBytes)
        val code = ByteArray(18).also(zufall::nextBytes).joinToString("") { "%02x".format(it) }
        tresor.geheimnisSpeichern("admin", JSONObject()
            .put("salt", Base64.encodeToString(salt, Base64.NO_WRAP))
            .put("pin", ableiten(pin, salt))
            .put("recovery", ableiten(code, salt)).toString())
        prefs.edit().putBoolean("recovery-bestaetigt", false).putInt("versuche", 0).putLong("sperre", 0).commit()
        offenBis = SystemClock.elapsedRealtime() + 300_000
        return code.chunked(6).joinToString("-")
    }

    fun recoveryBestaetigen() {
        check(frei)
        prefs.edit().putBoolean("recovery-bestaetigt", true).commit()
    }

    fun pruefen(eingabe: String, recovery: Boolean = false): Boolean {
        check(System.currentTimeMillis() >= prefs.getLong("sperre", 0)) { "Bitte eine Minute warten." }
        val daten = JSONObject(tresor.geheimnisLesen("admin") ?: return false)
        val salt = Base64.decode(daten.getString("salt"), Base64.NO_WRAP)
        val text = if (recovery) eingabe.replace("-", "").trim().lowercase() else eingabe
        val feld = if (recovery) "recovery" else "pin"
        val ok = MessageDigest.isEqual(ableiten(text, salt).toByteArray(), daten.optString(feld).toByteArray())
        if (ok) {
            offenBis = SystemClock.elapsedRealtime() + 300_000
            prefs.edit().putInt("versuche", 0).putLong("sperre", 0).commit()
            if (recovery) {
                daten.remove("recovery")
                tresor.geheimnisSpeichern("admin", daten.toString())
                prefs.edit().putBoolean("recovery-bestaetigt", false).commit()
            }
        } else {
            val versuche = prefs.getInt("versuche", 0) + 1
            prefs.edit().putInt("versuche", versuche)
                .putLong("sperre", if (versuche >= 5) System.currentTimeMillis() + 60_000 else 0).commit()
        }
        return ok
    }

    fun sperren() { offenBis = 0 }

    fun fingerFrei() {
        offenBis = SystemClock.elapsedRealtime() + 300_000
        prefs.edit().putInt("versuche", 0).putLong("sperre", 0).commit()
    }

    private fun ableiten(wert: String, salt: ByteArray): String {
        val spec = PBEKeySpec(wert.toCharArray(), salt, 210_000, 256)
        return try {
            Base64.encodeToString(SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256").generateSecret(spec).encoded, Base64.NO_WRAP)
        } finally { spec.clearPassword() }
    }

    companion object {
        private val _frist = kotlinx.coroutines.flow.MutableStateFlow(0L)
        val frist: kotlinx.coroutines.flow.StateFlow<Long> = _frist
        private var offenBis: Long
            get() = _frist.value
            set(wert) { _frist.value = wert }
    }
}
