package at.felworks.jon.pairing

import at.felworks.jon.data.remote.Krypto

const val CODE_LAENGE = 12
const val STANDARD_BROKER = ""
const val STANDARD_PORT = 0

private val ERSATZ = mapOf('I' to '1', 'L' to '1', 'O' to '0', 'U' to 'V')
private const val ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

object Kopplungscode {

    fun saeubern(roh: String): String = buildString {
        roh.uppercase().forEach { zeichen ->
            if (zeichen == '-' || zeichen == ' ' || zeichen == '_') return@forEach
            val ersetzt = ERSATZ[zeichen] ?: zeichen
            if (ersetzt in ALPHABET) append(ersetzt)
        }
    }

    fun gruppiert(code: String): String =
        code.chunked(4).joinToString("-")

    fun vollstaendig(code: String): Boolean = saeubern(code).length == CODE_LAENGE

    fun schluessel(code: String): ByteArray =
        Krypto.ableiten(saeubern(code).toByteArray(Charsets.UTF_8), "pairing")

    fun thema(code: String): String =
        Krypto.ableiten(saeubern(code).toByteArray(Charsets.UTF_8), "topic")
            .copyOfRange(0, 8)
            .joinToString("") { "%02x".format(it) }
}
