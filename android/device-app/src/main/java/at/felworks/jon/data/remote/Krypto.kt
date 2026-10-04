package at.felworks.jon.data.remote

import android.util.Base64
import org.json.JSONObject
import java.security.SecureRandom
import javax.crypto.Cipher
import javax.crypto.Mac
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec

object Krypto {

    private const val SALZ = "jon-handy-v1"
    private const val NONCE_LAENGE = 12
    private const val MARKE_BITS = 128
    private val zufall = SecureRandom()

    fun b64(roh: ByteArray): String =
        Base64.encodeToString(roh, Base64.URL_SAFE or Base64.NO_PADDING or Base64.NO_WRAP)

    fun unb64(text: String): ByteArray =
        Base64.decode(text, Base64.URL_SAFE or Base64.NO_PADDING or Base64.NO_WRAP)

    fun ableiten(geheimnis: ByteArray, zweck: String): ByteArray {
        val mac = Mac.getInstance("HmacSHA256")
        mac.init(SecretKeySpec(SALZ.toByteArray(), "HmacSHA256"))
        val wurzel = mac.doFinal(geheimnis)
        val ausgabe = Mac.getInstance("HmacSHA256")
        ausgabe.init(SecretKeySpec(wurzel, "HmacSHA256"))
        ausgabe.update(zweck.toByteArray())
        ausgabe.update(1.toByte())
        return ausgabe.doFinal().copyOf(32)
    }

    fun verschluesseln(schluessel: ByteArray, zusatz: String, klartext: JSONObject): JSONObject {
        val nonce = ByteArray(NONCE_LAENGE).also { zufall.nextBytes(it) }
        val chiffre = Cipher.getInstance("AES/GCM/NoPadding")
        chiffre.init(
            Cipher.ENCRYPT_MODE,
            SecretKeySpec(schluessel, "AES"),
            GCMParameterSpec(MARKE_BITS, nonce),
        )
        chiffre.updateAAD(zusatz.toByteArray())
        val daten = chiffre.doFinal(klartext.toString().toByteArray(Charsets.UTF_8))
        return JSONObject().put("n", b64(nonce)).put("c", b64(daten))
    }

    fun entschluesseln(schluessel: ByteArray, zusatz: String, umschlag: JSONObject): JSONObject {
        val nonce = unb64(umschlag.getString("n"))
        val daten = unb64(umschlag.getString("c"))
        val chiffre = Cipher.getInstance("AES/GCM/NoPadding")
        chiffre.init(
            Cipher.DECRYPT_MODE,
            SecretKeySpec(schluessel, "AES"),
            GCMParameterSpec(MARKE_BITS, nonce),
        )
        chiffre.updateAAD(zusatz.toByteArray())
        return JSONObject(String(chiffre.doFinal(daten), Charsets.UTF_8))
    }

    fun kennung(laenge: Int = 8): String {
        val roh = ByteArray(laenge).also { zufall.nextBytes(it) }
        return roh.joinToString("") { "%02x".format(it) }
    }
}
