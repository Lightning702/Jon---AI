package at.felworks.jon.pairing

import org.json.JSONObject

data class QrNutzlast(
    val pcName: String,
    val code: String,
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

    companion object {
        fun lesen(roh: String): QrNutzlast? = runCatching {
            val daten = JSONObject(roh.trim())
            if (daten.optString("t") != "jon-pair") return null
            val code = Kopplungscode.saeubern(daten.optString("c"))
            if (code.length != CODE_LAENGE) return null
            val liste = daten.optJSONArray("us")
            QrNutzlast(
                pcName = daten.optString("n", "Jon PC"),
                code = code,
                adresse = daten.optString("u").trimEnd('/'),
                adressen = (0 until (liste?.length() ?: 0))
                    .map { liste!!.optString(it).trimEnd('/') },
                broker = daten.optString("b", STANDARD_BROKER),
                brokerPort = daten.optInt("p", STANDARD_PORT),
                nurDirekt = daten.optBoolean("direct_only", false),
            )
        }.getOrNull()

        fun ausCode(code: String): QrNutzlast? {
            val sauber = Kopplungscode.saeubern(code)
            if (sauber.length != CODE_LAENGE) return null
            return QrNutzlast(
                pcName = "Jon PC",
                code = sauber,
                adresse = "",
                broker = STANDARD_BROKER,
                brokerPort = STANDARD_PORT,
            )
        }
    }
}
