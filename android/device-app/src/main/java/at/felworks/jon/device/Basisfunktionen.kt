package at.felworks.jon.device

import android.app.admin.DevicePolicyManager
import android.bluetooth.BluetoothManager
import android.content.ComponentName
import android.content.Context
import android.media.AudioManager
import android.net.wifi.WifiConfiguration
import android.net.wifi.WifiManager
import android.provider.Settings

class Basisfunktionen(private val context: Context) {
    private val wifi = context.applicationContext.getSystemService(WifiManager::class.java)
    private val audio = context.getSystemService(AudioManager::class.java)
    private val dpm = context.getSystemService(DevicePolicyManager::class.java)
    val wlan: Boolean get() = wifi.isWifiEnabled
    val bluetooth: Boolean get() = context.getSystemService(BluetoothManager::class.java).adapter?.isEnabled == true
    val lautstaerke: Int get() = audio.getStreamVolume(AudioManager.STREAM_MUSIC)
    val maximal: Int get() = audio.getStreamMaxVolume(AudioManager.STREAM_MUSIC)
    val helligkeit: Int get() = Settings.System.getInt(context.contentResolver, Settings.System.SCREEN_BRIGHTNESS, 128)

    private fun verwaltet() { check(dpm.isDeviceOwnerApp(context.packageName)) { "Diese Funktion braucht den eingerichteten Gerätemodus." } }
    fun wlanSetzen(wert: Boolean) { verwaltet(); check(wifi.setWifiEnabled(wert)) { "WLAN konnte nicht geändert werden." } }
    fun bluetoothSetzen(wert: Boolean) {
        verwaltet()
        val adapter = context.getSystemService(BluetoothManager::class.java).adapter ?: error("Bluetooth fehlt.")
        check(if (wert) adapter.enable() else adapter.disable()) { "Bluetooth konnte nicht geändert werden." }
    }
    fun netze(): List<String> = wifi.scanResults.map { it.SSID }.filter { it.isNotBlank() }.distinct().sorted()
    fun suchen() { check(wifi.startScan()) { "Android begrenzt WLAN-Suchen. Die letzte Liste bleibt verfügbar." } }
    fun verbinden(ssid: String, passwort: String, art: String) {
        verwaltet()
        require(ssid.isNotBlank() && ssid.toByteArray().size <= 32) { "SSID ist ungültig." }
        require(art == "offen" || passwort.length in 8..63) { "Das WLAN-Passwort braucht 8 bis 63 Zeichen." }
        fun zitat(s: String) = "\"" + s.replace("\\", "\\\\").replace("\"", "\\\"") + "\""
        val config = WifiConfiguration().apply {
            SSID = zitat(ssid)
            hiddenSSID = true
            when (art) {
                "offen" -> allowedKeyManagement.set(WifiConfiguration.KeyMgmt.NONE)
                "wpa3" -> {
                    check(android.os.Build.VERSION.SDK_INT >= 29 && wifi.isWpa3SaeSupported) { "WPA3 wird nicht unterstützt." }
                    allowedKeyManagement.set(WifiConfiguration.KeyMgmt.SAE)
                    preSharedKey = zitat(passwort)
                }
                else -> { allowedKeyManagement.set(WifiConfiguration.KeyMgmt.WPA_PSK); preSharedKey = zitat(passwort) }
            }
        }
        val id = wifi.addNetwork(config)
        check(id >= 0 && wifi.enableNetwork(id, true)) { "Android hat die WLAN-Konfiguration abgelehnt." }
    }
    fun lautstaerkeSetzen(wert: Int) { audio.setStreamVolume(AudioManager.STREAM_MUSIC, wert.coerceIn(0, maximal), 0) }
    fun helligkeitSetzen(wert: Int) {
        verwaltet()
        val admin = ComponentName(context, JonAdmin::class.java)
        dpm.setSystemSetting(admin, Settings.System.SCREEN_BRIGHTNESS_MODE, Settings.System.SCREEN_BRIGHTNESS_MODE_MANUAL.toString())
        dpm.setSystemSetting(admin, Settings.System.SCREEN_BRIGHTNESS, wert.coerceIn(10, 255).toString())
    }
}
