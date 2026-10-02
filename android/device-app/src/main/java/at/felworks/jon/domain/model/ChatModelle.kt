package at.felworks.jon.domain.model

enum class Rolle { NUTZER, JON, SYSTEM }

enum class BlockArt { TEXT, CODE, LISTE, ZITAT, UEBERSCHRIFT }

data class ChatBlock(
    val art: BlockArt,
    val text: String,
    val sprache: String = "",
)

data class Anhang(
    val name: String,
    val art: String,
    val quelle: String,
)

data class WerkzeugLauf(
    val name: String,
    val beschriftung: String,
    val status: String,
    val fortschritt: Float? = null,
    val braucht: Boolean = false,
    val id: String = "",
)

data class ChatNachricht(
    val id: String,
    val rolle: Rolle,
    val text: String,
    val zeit: Long,
    val laeuft: Boolean = false,
    val fehler: String? = null,
    val anhaenge: List<Anhang> = emptyList(),
    val werkzeuge: List<WerkzeugLauf> = emptyList(),
    val vorschlaege: List<String> = emptyList(),
)

data class Unterhaltung(
    val id: String,
    val titel: String,
    val zeit: Long,
)

data class Schnellaktion(
    val schluessel: String,
    val titel: String,
    val zeile: String,
    val auftrag: String,
)
