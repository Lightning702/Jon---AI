package at.felworks.jon.domain.repository

sealed interface ChatStueck {
    data class Text(val teil: String) : ChatStueck
    data class Fehler(val text: String) : ChatStueck
    data class Werkzeug(val zeile: String, val freigabe: String? = null) : ChatStueck
    data object Ende : ChatStueck
}
