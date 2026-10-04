package at.felworks.jon.data.remote

import kotlinx.coroutines.flow.Flow
import org.json.JSONObject

data class Zugang(
    val geraet: String,
    val schluessel: ByteArray,
    val token: String,
    val pcId: String,
    val pcName: String,
    val adresse: String,
    val adressen: List<String> = emptyList(),
    val broker: String,
    val brokerPort: Int,
    val nurDirekt: Boolean = false,
) {
    val alleAdressen: List<String>
        get() = (listOf(adresse) + adressen)
            .filter { it.isNotBlank() && !it.contains("127.0.0.1") && !it.contains("localhost") }
            .distinct()

    val umschlagArt: String get() = "dev"
    val umschlagId: String get() = geraet

    override fun equals(other: Any?): Boolean = other is Zugang && other.geraet == geraet
    override fun hashCode(): Int = geraet.hashCode()
}

data class Kopplungsschluessel(
    val pcId: String,
    val pcName: String,
    val schluessel: ByteArray,
    val adresse: String,
    val broker: String,
    val brokerPort: Int,
) {
    override fun equals(other: Any?): Boolean = other is Kopplungsschluessel && other.pcId == pcId
    override fun hashCode(): Int = pcId.hashCode()
}

class JonFehler(val grund: String, val schwer: Boolean = false) : Exception(grund)

interface JonTransport {
    val name: String
    suspend fun erreichbar(): Boolean
    suspend fun senden(
        anfrage: JSONObject,
        art: String,
        id: String,
        schluessel: ByteArray,
        wartezeit: Long = 60_000,
    ): JSONObject
    suspend fun werfen(anfrage: JSONObject, art: String, id: String, schluessel: ByteArray)
    fun strom(anfrage: JSONObject, art: String, id: String, schluessel: ByteArray): Flow<JSONObject>
    fun schliessen()
}
