package at.felworks.jon.uhr

import android.util.Base64
import org.json.JSONObject
import java.security.SecureRandom
import javax.crypto.Cipher
import javax.crypto.Mac
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec

object Krypto {
    private const val SALZ = "jon-handy-v1"
    private const val ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
    private val ERSATZ = mapOf('I' to '1', 'L' to '1', 'O' to '0', 'U' to 'V')
    private val zufall = SecureRandom()

    fun b64(roh: ByteArray): String = Base64.encodeToString(roh, Base64.URL_SAFE or Base64.NO_PADDING or Base64.NO_WRAP)

    fun unb64(text: String): ByteArray = Base64.decode(text.replace('+', '-').replace('/', '_').trimEnd('='), Base64.URL_SAFE or Base64.NO_PADDING or Base64.NO_WRAP)

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

    fun codeSaeubern(roh: String): String = buildString {
        roh.uppercase().forEach { zeichen ->
            val ersetzt = ERSATZ[zeichen] ?: zeichen
            if (ersetzt in ALPHABET) append(ersetzt)
        }
    }

    fun codeSchluessel(code: String): ByteArray = ableiten(codeSaeubern(code).toByteArray(), "pairing")

    fun codeThema(code: String): String = ableiten(codeSaeubern(code).toByteArray(), "topic").copyOfRange(0, 8).joinToString("") { "%02x".format(it) }

    fun umschlag(anfrage: JSONObject, art: String, id: String, schluessel: ByteArray): JSONObject {
        val nonce = ByteArray(12).also { zufall.nextBytes(it) }
        val chiffre = Cipher.getInstance("AES/GCM/NoPadding")
        chiffre.init(Cipher.ENCRYPT_MODE, SecretKeySpec(schluessel, "AES"), GCMParameterSpec(128, nonce))
        chiffre.updateAAD("$art:$id".toByteArray())
        val daten = chiffre.doFinal(anfrage.toString().toByteArray(Charsets.UTF_8))
        return JSONObject().put("v", 2).put("k", art).put("i", id).put("n", b64(nonce)).put("c", b64(daten))
    }

    fun oeffnen(schluessel: ByteArray, art: String, id: String, umschlag: JSONObject): JSONObject {
        val chiffre = Cipher.getInstance("AES/GCM/NoPadding")
        chiffre.init(Cipher.DECRYPT_MODE, SecretKeySpec(schluessel, "AES"), GCMParameterSpec(128, unb64(umschlag.getString("n"))))
        chiffre.updateAAD("$art:$id".toByteArray())
        return JSONObject(String(chiffre.doFinal(unb64(umschlag.getString("c"))), Charsets.UTF_8))
    }

    fun kennung(laenge: Int = 8): String = ByteArray(laenge).also { zufall.nextBytes(it) }.joinToString("") { "%02x".format(it) }
}
