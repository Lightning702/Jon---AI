package at.felworks.jon.device

import android.content.Context
import android.os.Build
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyPermanentlyInvalidatedException
import android.security.keystore.KeyProperties
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricManager.Authenticators.BIOMETRIC_STRONG
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity
import kotlinx.coroutines.suspendCancellableCoroutine
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import kotlin.coroutines.resume

object Fingerabdruck {
    private const val ALIAS = "jon-admin-fingerabdruck"

    private fun prefs(context: Context) = context.getSharedPreferences("jon-device", Context.MODE_PRIVATE)

    private fun speicher(): KeyStore = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }

    fun moeglich(context: Context): Boolean =
        runCatching { BiometricManager.from(context).canAuthenticate(BIOMETRIC_STRONG) == BiometricManager.BIOMETRIC_SUCCESS }.getOrDefault(false)

    fun an(context: Context): Boolean =
        prefs(context).getBoolean("fingerabdruck", false) && runCatching { speicher().containsAlias(ALIAS) }.getOrDefault(false)

    private fun erzeugen() {
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
        generator.init(
            KeyGenParameterSpec.Builder(ALIAS, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setUserAuthenticationRequired(true)
                .setInvalidatedByBiometricEnrollment(true)
                .apply { if (Build.VERSION.SDK_INT >= 30) setUserAuthenticationParameters(0, KeyProperties.AUTH_BIOMETRIC_STRONG) }
                .build()
        )
        generator.generateKey()
    }

    private fun chiffre(): Cipher? {
        val schluessel = runCatching { speicher().getKey(ALIAS, null) as? SecretKey }.getOrNull() ?: return null
        return try {
            Cipher.getInstance("AES/GCM/NoPadding").apply { init(Cipher.ENCRYPT_MODE, schluessel) }
        } catch (e: KeyPermanentlyInvalidatedException) {
            null
        }
    }

    fun ausschalten(context: Context) {
        runCatching { speicher().deleteEntry(ALIAS) }
        prefs(context).edit().putBoolean("fingerabdruck", false).commit()
    }

    private suspend fun fragen(activity: FragmentActivity, titel: String, text: String, chiffre: Cipher): Boolean =
        suspendCancellableCoroutine { weiter ->
            val prompt = BiometricPrompt(activity, ContextCompat.getMainExecutor(activity), object : BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                    val ok = runCatching { result.cryptoObject?.cipher?.doFinal(ByteArray(16)) != null }.getOrDefault(false)
                    if (weiter.isActive) weiter.resume(ok)
                }

                override fun onAuthenticationError(code: Int, meldung: CharSequence) {
                    if (weiter.isActive) weiter.resume(false)
                }
            })
            weiter.invokeOnCancellation { runCatching { prompt.cancelAuthentication() } }
            prompt.authenticate(
                BiometricPrompt.PromptInfo.Builder().setTitle(titel).setSubtitle(text)
                    .setNegativeButtonText("PIN verwenden").setAllowedAuthenticators(BIOMETRIC_STRONG).build(),
                BiometricPrompt.CryptoObject(chiffre)
            )
        }

    suspend fun einschalten(activity: FragmentActivity): Boolean {
        check(moeglich(activity)) { "Auf diesem Handy ist noch kein Fingerabdruck eingerichtet." }
        runCatching { speicher().deleteEntry(ALIAS) }
        erzeugen()
        val c = chiffre() ?: error("Der Schlüssel ließ sich nicht anlegen.")
        val ok = fragen(activity, "Fingerabdruck für Jon", "Leg deinen Finger auf, um ihn für die Verwaltung zu nutzen.", c)
        if (ok) prefs(activity).edit().putBoolean("fingerabdruck", true).commit() else ausschalten(activity)
        return ok
    }

    suspend fun entsperren(activity: FragmentActivity): Boolean {
        if (!an(activity)) return false
        val c = chiffre()
        if (c == null) {
            ausschalten(activity)
            error("Am Handy wurde ein neuer Fingerabdruck hinzugefügt. Bitte die PIN nehmen und den Fingerabdruck neu einschalten.")
        }
        return fragen(activity, "Verwaltung entsperren", "Mit deinem Fingerabdruck", c)
    }
}
