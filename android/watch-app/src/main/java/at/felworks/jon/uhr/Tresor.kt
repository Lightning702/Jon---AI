package at.felworks.jon.uhr

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import org.json.JSONArray
import org.json.JSONObject
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

data class Zugang(
    val geraet: String,
    val schluessel: ByteArray,
    val pcId: String,
    val pcName: String,
    val adressen: List<String>,
    val besitzer: String,
) {
    override fun equals(other: Any?): Boolean = other is Zugang && other.geraet == geraet
    override fun hashCode(): Int = geraet.hashCode()
}

class Tresor(context: Context) {
    private val ablage = context.applicationContext.getSharedPreferences("jon-uhr-tresor", Context.MODE_PRIVATE)

    private fun schluessel(): SecretKey {
        val speicher = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (speicher.getKey("jon-uhr", null) as? SecretKey)?.let { return it }
        val erzeuger = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
        erzeuger.init(
            KeyGenParameterSpec.Builder("jon-uhr", KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .build(),
        )
        return erzeuger.generateKey()
    }

    fun zugang(): Zugang? {
        val gesichert = ablage.getString("zugang", null) ?: return null
        return runCatching {
            val roh = Base64.decode(gesichert, Base64.NO_WRAP)
            val chiffre = Cipher.getInstance("AES/GCM/NoPadding")
            chiffre.init(Cipher.DECRYPT_MODE, schluessel(), GCMParameterSpec(128, roh.copyOfRange(0, 12)))
            val daten = JSONObject(String(chiffre.doFinal(roh.copyOfRange(12, roh.size)), Charsets.UTF_8))
            val liste = daten.optJSONArray("adressen") ?: JSONArray()
            Zugang(
                daten.getString("geraet"),
                Krypto.unb64(daten.getString("schluessel")),
                daten.optString("pcId"),
                daten.optString("pcName"),
                (0 until liste.length()).map { liste.getString(it) },
                daten.optString("besitzer"),
            )
        }.getOrNull()
    }

    fun speichern(zugang: Zugang) {
        val daten = JSONObject()
            .put("geraet", zugang.geraet)
            .put("schluessel", Krypto.b64(zugang.schluessel))
            .put("pcId", zugang.pcId)
            .put("pcName", zugang.pcName)
            .put("adressen", JSONArray(zugang.adressen))
            .put("besitzer", zugang.besitzer)
        val chiffre = Cipher.getInstance("AES/GCM/NoPadding")
        chiffre.init(Cipher.ENCRYPT_MODE, schluessel())
        val verschluesselt = chiffre.iv + chiffre.doFinal(daten.toString().toByteArray(Charsets.UTF_8))
        ablage.edit().putString("zugang", Base64.encodeToString(verschluesselt, Base64.NO_WRAP)).apply()
    }

    fun loeschen() {
        ablage.edit().remove("zugang").apply()
    }
}
