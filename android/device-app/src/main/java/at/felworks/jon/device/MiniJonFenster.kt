package at.felworks.jon.device

enum class MiniJonFenster {
    APP, OVERLAY, WARTEN;

    companion object {
        fun waehlen(kiosk: Boolean, appSichtbar: Boolean, erlaubt: Boolean): MiniJonFenster = when {
            kiosk && appSichtbar -> APP
            kiosk || !erlaubt -> WARTEN
            else -> OVERLAY
        }
    }
}
