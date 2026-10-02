package at.felworks.jon.domain.model

enum class Draht { AUS, LOKAL }
data class Verbindungslage(val draht: Draht = Draht.AUS, val pcName: String = "", val meldung: String = "", val adresse: String = "")
