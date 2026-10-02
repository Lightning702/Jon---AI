package at.felworks.jon.device

import android.app.Activity
import android.app.ActivityManager
import android.app.KeyguardManager
import android.app.admin.DeviceAdminReceiver
import android.app.admin.DevicePolicyManager
import android.content.BroadcastReceiver
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import android.content.pm.ResolveInfo
import android.os.Build
import android.os.UserManager
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import at.felworks.jon.MainActivity
import at.felworks.jon.connector.Verbinderrechte

class JonAdmin : DeviceAdminReceiver()

class JonStart : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        runCatching { Uhren.allePlanen(context) }
        runCatching { Bildschirmzeit.pruefen(context) }
        runCatching { Schritte.planen(context) }
        if (intent.action in setOf(Intent.ACTION_BOOT_COMPLETED, Intent.ACTION_MY_PACKAGE_REPLACED)) runCatching { JonHintergrund.starten(context) }
        val modus = GeraeteModus(context)
        val nachUpdate = intent.action == Intent.ACTION_MY_PACKAGE_REPLACED && Aktualisierung.neustartFaellig(context)
        val klemmt = modus.reparaturNoetig()
        if (klemmt) modus.freischalten()
        if (klemmt || nachUpdate || (modus.aktiv && modus.eigentuemer && intent.action in setOf(Intent.ACTION_BOOT_COMPLETED, Intent.ACTION_MY_PACKAGE_REPLACED))) {
            runCatching { context.startActivity(Intent(context, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)) }
        }
    }
}

class GeraeteModus(private val context: Context) {
    private val dpm = context.getSystemService(DevicePolicyManager::class.java)
    private val admin = ComponentName(context, JonAdmin::class.java)
    private val prefs = context.getSharedPreferences("jon-device", Context.MODE_PRIVATE)
    private val startseite = ComponentName(context.packageName, "at.felworks.jon.JonHome")
    private val regeln = listOf(UserManager.DISALLOW_SAFE_BOOT, UserManager.DISALLOW_CREATE_WINDOWS, UserManager.DISALLOW_ADD_USER)
    private val helfer = listOf(
        "com.google.android.permissioncontroller", "com.android.permissioncontroller",
        "com.google.android.documentsui", "com.android.documentsui",
        "com.google.android.photopicker", "com.google.android.providers.media.module", "com.android.providers.media.module"
    )
    val schutz = AdminSchutz(context)
    val eigentuemer: Boolean get() = dpm.isDeviceOwnerApp(context.packageName)
    val aktiv: Boolean get() = prefs.getBoolean("kiosk", false)
    val gesperrt: Boolean get() = context.getSystemService(ActivityManager::class.java).lockTaskModeState == ActivityManager.LOCK_TASK_MODE_LOCKED
    val abgeschottet: Boolean get() = (aktiv && eigentuemer) || gesperrt
    var wakeWord: Boolean
        get() = prefs.getBoolean("wake", false)
        set(wert) { prefs.edit().putBoolean("wake", wert).apply() }
    var unterbrechen: Boolean
        get() = prefs.getBoolean("barge", true)
        set(wert) { prefs.edit().putBoolean("barge", wert).apply() }

    private fun installiert(paket: String) = runCatching { context.packageManager.getPackageInfo(paket, 0); true }.getOrDefault(false)

    private fun kioskPakete(): Array<String> {
        val apps = GeraeteApps.liste(context).map { it.paket }.filter(::installiert)
        val waehler = runCatching { SosHilfe.waehlerPaket(context) }.getOrNull()
        return (listOf(context.packageName) + apps + helfer.filter(::installiert) + listOfNotNull(waehler)).distinct().toTypedArray()
    }

    fun reparaturNoetig(): Boolean = eigentuemer && !aktiv && gesperrt

    fun freischalten() {
        if (eigentuemer) runCatching { dpm.setLockTaskPackages(admin, arrayOf(context.packageName)) }
    }

    private fun aufraeumen() {
        if (eigentuemer) {
            regeln.forEach { runCatching { dpm.clearUserRestriction(admin, it) } }
            runCatching { dpm.setStatusBarDisabled(admin, false) }
            runCatching { dpm.setKeyguardDisabled(admin, false) }
            runCatching { dpm.setAlwaysOnVpnPackage(admin, null, false) }
            runCatching { dpm.setLockTaskPackages(admin, arrayOf(context.packageName)) }
        }
        runCatching { startZurueckgeben() }
    }

    fun reparieren(activity: Activity): Boolean {
        if (!reparaturNoetig()) return false
        freischalten()
        runCatching { activity.stopLockTask() }
        aufraeumen()
        vollbild(activity)
        return true
    }

    fun neustarten() {
        check(eigentuemer) { "Jon ist kein Geräteverwalter." }
        dpm.reboot(admin)
    }

    fun appsUebernehmen() {
        if (!aktiv || !eigentuemer) return
        runCatching { dpm.setLockTaskPackages(admin, kioskPakete()) }
    }

    private fun startFilter() = IntentFilter(Intent.ACTION_MAIN).apply {
        addCategory(Intent.CATEGORY_HOME)
        addCategory(Intent.CATEGORY_DEFAULT)
    }

    private fun startIntent() = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_HOME)

    private fun startseiteSchalten(an: Boolean) {
        val zustand = if (an) PackageManager.COMPONENT_ENABLED_STATE_ENABLED else PackageManager.COMPONENT_ENABLED_STATE_DISABLED
        if (context.packageManager.getComponentEnabledSetting(startseite) == zustand) return
        val flags = if (Build.VERSION.SDK_INT >= 33) PackageManager.DONT_KILL_APP or PackageManager.SYNCHRONOUS else PackageManager.DONT_KILL_APP
        context.packageManager.setComponentEnabledSetting(startseite, zustand, flags)
    }

    private fun aktuellerStart(): ComponentName? {
        val info = context.packageManager.resolveActivity(startIntent(), PackageManager.MATCH_DEFAULT_ONLY)?.activityInfo ?: return null
        return ComponentName(info.packageName, info.name)
    }

    private fun bisherigenStartMerken() {
        val start = aktuellerStart() ?: return
        if (start.packageName == context.packageName || start.packageName == "android") return
        prefs.edit().putString("bisheriger-start", start.flattenToString()).apply()
    }

    fun bisherigerStart(): ComponentName? {
        val kandidaten = context.packageManager.queryIntentActivities(startIntent(), PackageManager.MATCH_DEFAULT_ONLY)
            .filter { it.activityInfo.packageName != context.packageName && it.priority >= 0 }
        val gemerkt = prefs.getString("bisheriger-start", null)?.let(ComponentName::unflattenFromString)
        if (gemerkt != null && kandidaten.any { it.activityInfo.packageName == gemerkt.packageName && it.activityInfo.name == gemerkt.className }) return gemerkt
        val beste = kandidaten.sortedWith(
            compareByDescending<ResolveInfo> { it.activityInfo.applicationInfo.flags and ApplicationInfo.FLAG_SYSTEM != 0 }.thenByDescending { it.priority }
        ).firstOrNull() ?: return null
        return ComponentName(beste.activityInfo.packageName, beste.activityInfo.name)
    }

    private fun startUebernehmen() {
        startseiteSchalten(true)
        if (aktuellerStart() == startseite) return
        runCatching { dpm.clearPackagePersistentPreferredActivities(admin, context.packageName) }
        dpm.addPersistentPreferredActivity(admin, startFilter(), startseite)
    }

    fun startZurueckgeben() {
        if (!eigentuemer) {
            runCatching { startseiteSchalten(false) }
            return
        }
        runCatching { dpm.clearPackagePersistentPreferredActivities(admin, context.packageName) }
        runCatching { startseiteSchalten(false) }
        val ziel = bisherigerStart() ?: return
        runCatching {
            dpm.addPersistentPreferredActivity(admin, startFilter(), ziel)
            dpm.clearPackagePersistentPreferredActivities(admin, ziel.packageName)
        }
    }

    fun einschalten(activity: Activity, verbunden: Boolean) {
        check(schutz.eingerichtet && schutz.bestaetigt) { "Richte zuerst Admin-PIN und Recovery-Code ein." }
        check(schutz.frei) { "Admin-PIN erforderlich." }
        check(verbunden) { "Verbinde das Gerät zuerst mit deinem Pi." }
        check(eigentuemer) { "Der Gerätemodus (Device Owner) ist noch nicht eingerichtet." }
        check(Build.VERSION.SDK_INT >= 28) { "Der Kiosk braucht Android 9 oder neuer." }
        check(Verbinderrechte.erteilt(context, android.Manifest.permission.RECORD_AUDIO)) { "Mikrofon zuerst erlauben." }
        val altePakete = dpm.getLockTaskPackages(admin)
        val alteFunktionen = dpm.getLockTaskFeatures(admin)
        val alteRegeln = dpm.getUserRestrictions(admin)
        try {
            bisherigenStartMerken()
            dpm.setLockTaskPackages(admin, kioskPakete())
            var funktionen = DevicePolicyManager.LOCK_TASK_FEATURE_HOME or DevicePolicyManager.LOCK_TASK_FEATURE_GLOBAL_ACTIONS or DevicePolicyManager.LOCK_TASK_FEATURE_SYSTEM_INFO
            if (Build.VERSION.SDK_INT >= 30) funktionen = funktionen or DevicePolicyManager.LOCK_TASK_FEATURE_BLOCK_ACTIVITY_START_IN_TASK
            dpm.setLockTaskFeatures(admin, funktionen)
            startUebernehmen()
            regeln.forEach { dpm.addUserRestriction(admin, it) }
            runCatching { dpm.setStatusBarDisabled(admin, true) }
            if (!context.getSystemService(KeyguardManager::class.java).isKeyguardSecure) runCatching { dpm.setKeyguardDisabled(admin, true) }
            if (GeraeteApps.installiert(context, "vpn")) runCatching { dpm.setAlwaysOnVpnPackage(admin, GeraeteApps.pakete.getValue("vpn"), false) }
            prefs.edit().putBoolean("kiosk", true).commit()
            anwenden(activity)
            schutz.sperren()
        } catch (e: Exception) {
            prefs.edit().putBoolean("kiosk", false).commit()
            runCatching { activity.stopLockTask() }
            runCatching { dpm.setLockTaskPackages(admin, altePakete) }
            runCatching { dpm.setLockTaskFeatures(admin, alteFunktionen) }
            runCatching { startZurueckgeben() }
            regeln.forEach { regel -> if (!alteRegeln.getBoolean(regel)) runCatching { dpm.clearUserRestriction(admin, regel) } }
            runCatching { dpm.setStatusBarDisabled(admin, false) }
            runCatching { dpm.setKeyguardDisabled(admin, false) }
            vollbild(activity)
            throw e
        }
    }

    fun anwenden(activity: Activity) {
        MiniJonDienst.attach(activity)
        if (reparieren(activity)) return
        vollbild(activity)
        if (!aktiv && !gesperrt && aktuellerStart()?.packageName == context.packageName) runCatching { startZurueckgeben() }
        if (!aktiv || !eigentuemer) return
        runCatching { startUebernehmen() }
        if (context.getSystemService(KeyguardManager::class.java).isDeviceLocked) return
        if (dpm.isLockTaskPermitted(context.packageName) && !gesperrt) runCatching { activity.startLockTask() }
    }

    fun vollbild(activity: Activity) {
        val abgeschottet = abgeschottet
        WindowCompat.getInsetsController(activity.window, activity.window.decorView).apply {
            systemBarsBehavior = WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
            if (abgeschottet) hide(WindowInsetsCompat.Type.systemBars())
            else {
                hide(WindowInsetsCompat.Type.statusBars())
                show(WindowInsetsCompat.Type.navigationBars())
            }
        }
    }

    suspend fun verlassen(activity: Activity) {
        check(schutz.frei) { "Admin-PIN erforderlich." }
        prefs.edit().putBoolean("kiosk", false).commit()
        runCatching { activity.stopLockTask() }
        repeat(20) { if (gesperrt) kotlinx.coroutines.delay(100) }
        aufraeumen()
        vollbild(activity)
        MiniJonDienst.attach(activity)
    }

    suspend fun entfernen(activity: Activity) {
        check(schutz.frei) { "Admin-PIN erforderlich." }
        check(eigentuemer) { "Jon ist kein Geräteverwalter." }
        if (aktiv || gesperrt) verlassen(activity)
        runCatching { Bildschirmzeit.allesFreigeben(context) }
        runCatching { startZurueckgeben() }
        dpm.clearDeviceOwnerApp(context.packageName)
    }
}
