package at.felworks.jon.security

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import at.felworks.jon.data.remote.Krypto
import at.felworks.jon.data.remote.Zugang
import org.json.JSONArray
import org.json.JSONObject
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

private const val SPEICHER = "jon-tresor"
private const val ALIAS = "jon-geraeteschluessel"
private const val FELD_ZUGANG = "zugang"
private const val FELD_ZUGAENGE = "zugaenge"
private const val FELD_AKTIV = "aktiv"

class Tresor(context: Context) {

    private val ablage = context.getSharedPreferences(SPEICHER, Context.MODE_PRIVATE)

    private fun schluessel(): SecretKey {
        val laden = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        val vorhanden = laden.getKey(ALIAS, null) as? SecretKey
        if (vorhanden != null) return vorhanden
        val erzeuger = KeyGenerator.getInstance(
            KeyProperties.KEY_ALGORITHM_AES,
            "AndroidKeyStore",
        )
        erzeuger.init(
            KeyGenParameterSpec.Builder(
                ALIAS,
                KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT,
            )
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .build(),
        )
        return erzeuger.generateKey()
    }

    private fun sichern(klartext: String): String {
        val chiffre = Cipher.getInstance("AES/GCM/NoPadding")
        chiffre.init(Cipher.ENCRYPT_MODE, schluessel())
        val daten = chiffre.doFinal(klartext.toByteArray(Charsets.UTF_8))
        val zusammen = chiffre.iv + daten
        return Base64.encodeToString(zusammen, Base64.NO_WRAP)
    }

    private fun oeffnen(gesichert: String): String? = runCatching {
        val roh = Base64.decode(gesichert, Base64.NO_WRAP)
        val chiffre = Cipher.getInstance("AES/GCM/NoPadding")
        chiffre.init(
            Cipher.DECRYPT_MODE,
            schluessel(),
            GCMParameterSpec(128, roh.copyOfRange(0, 12)),
        )
        String(chiffre.doFinal(roh.copyOfRange(12, roh.size)), Charsets.UTF_8)
    }.getOrNull()

    private fun alsJson(zugang: Zugang): JSONObject = JSONObject()
        .put("geraet", zugang.geraet)
        .put("schluessel", Krypto.b64(zugang.schluessel))
        .put("token", zugang.token)
        .put("pcId", zugang.pcId)
        .put("pcName", zugang.pcName)
        .put("adresse", zugang.adresse)
        .put("adressen", JSONArray(zugang.adressen))
        .put("broker", zugang.broker)
        .put("brokerPort", zugang.brokerPort)
        .put("nurDirekt", zugang.nurDirekt)

    private fun ausJson(daten: JSONObject): Zugang = Zugang(
        geraet = daten.getString("geraet"),
        schluessel = Krypto.unb64(daten.getString("schluessel")),
        token = daten.getString("token"),
        pcId = daten.getString("pcId"),
        pcName = daten.getString("pcName"),
        adresse = daten.getString("adresse"),
        adressen = daten.optJSONArray("adressen")?.let { liste ->
            (0 until liste.length()).map { liste.optString(it) }
        } ?: emptyList(),
        broker = daten.getString("broker"),
        brokerPort = daten.getInt("brokerPort"),
        nurDirekt = daten.optBoolean("nurDirekt", false),
    )

    private fun alterZugang(): Zugang? {
        val gesichert = ablage.getString(FELD_ZUGANG, null) ?: return null
        val roh = oeffnen(gesichert) ?: return null
        return runCatching { ausJson(JSONObject(roh)) }.getOrNull()
    }

    private fun speichern(liste: List<Zugang>, aktiv: String?) {
        val daten = JSONArray().apply { liste.forEach { put(alsJson(it)) } }
        ablage.edit()
            .putString(FELD_ZUGAENGE, sichern(daten.toString()))
            .putString(FELD_AKTIV, aktiv)
            .remove(FELD_ZUGANG)
            .commit()
    }

    @Synchronized
    fun zugaenge(): List<Zugang> {
        val gesichert = ablage.getString(FELD_ZUGAENGE, null)
        if (gesichert == null) {
            val alt = alterZugang() ?: return emptyList()
            speichern(listOf(alt), alt.pcId)
            return listOf(alt)
        }
        val roh = oeffnen(gesichert) ?: return emptyList()
        return runCatching {
            val liste = JSONArray(roh)
            (0 until liste.length()).mapNotNull { runCatching { ausJson(liste.getJSONObject(it)) }.getOrNull() }
        }.getOrDefault(emptyList())
    }

    @Synchronized
    fun aktiverZugang(): Zugang? {
        val liste = zugaenge()
        val aktiv = ablage.getString(FELD_AKTIV, null)
        return liste.firstOrNull { it.pcId == aktiv } ?: liste.firstOrNull()
    }

    @Synchronized
    fun zugangHinzufuegen(zugang: Zugang) {
        speichern(zugaenge().filter { it.pcId != zugang.pcId } + zugang, zugang.pcId)
    }

    @Synchronized
    fun aktivSetzen(pcId: String) {
        check(zugaenge().any { it.pcId == pcId }) { "Diesen Jon kennt das Handy nicht." }
        ablage.edit().putString(FELD_AKTIV, pcId).commit()
    }

    @Synchronized
    fun zugangEntfernen(pcId: String): Zugang? {
        val liste = zugaenge().filter { it.pcId != pcId }
        val bisher = ablage.getString(FELD_AKTIV, null)
        val aktiv = liste.firstOrNull { it.pcId == bisher } ?: liste.firstOrNull()
        speichern(liste, aktiv?.pcId)
        return aktiv
    }

    fun leeren() {
        ablage.edit().remove(FELD_ZUGANG).remove(FELD_ZUGAENGE).remove(FELD_AKTIV).commit()
    }

    fun geheimnisSpeichern(name: String, wert: String) {
        ablage.edit().putString("geheim-$name", sichern(wert)).commit()
    }

    fun geheimnisLesen(name: String): String? =
        ablage.getString("geheim-$name", null)?.let { oeffnen(it) }

    fun geheimnisVorhanden(name: String): Boolean = ablage.contains("geheim-$name")

    fun geheimnisLoeschen(name: String) {
        ablage.edit().remove("geheim-$name").commit()
    }

    fun vernichten() {
        ablage.edit().clear().commit()
        runCatching { KeyStore.getInstance("AndroidKeyStore").apply { load(null) }.deleteEntry(ALIAS) }
    }
}
