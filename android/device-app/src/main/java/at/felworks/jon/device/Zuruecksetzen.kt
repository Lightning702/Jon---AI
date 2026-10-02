package at.felworks.jon.device

import android.app.Activity
import android.content.ContentUris
import android.content.Context
import android.content.Intent
import android.os.Build
import android.provider.MediaStore
import android.webkit.CookieManager
import android.webkit.WebStorage
import at.felworks.jon.core.AppBehaelter
import at.felworks.jon.security.Tresor
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File

object Zuruecksetzen {
    suspend fun allesLoeschen(activity: Activity, behaelter: AppBehaelter, medien: Boolean) {
        val modus = GeraeteModus(activity)
        withContext(Dispatchers.Main) {
            if (modus.aktiv || modus.gesperrt) modus.verlassen(activity)
            runCatching { modus.startZurueckgeben() }
            runCatching { SprachDienst.stoppen(activity) }
            runCatching { KlingelDienst.stoppen() }
        }
        runCatching { Bildschirmzeit.allesFreigeben(activity) }
        runCatching { behaelter.ueberallAbmelden() }
        if (medien) runCatching { medienLoeschen(activity) }
        withContext(Dispatchers.Main) {
            runCatching { WebStorage.getInstance().deleteAllData() }
            runCatching { CookieManager.getInstance().removeAllCookies(null) }
        }
        runCatching { Tresor(activity).vernichten() }
        dateienLoeschen(activity)
        withContext(Dispatchers.Main) { neustarten(activity) }
    }

    private fun dateienLoeschen(context: Context) {
        val basis = context.dataDir
        listOf(context.filesDir, context.cacheDir, context.noBackupFilesDir, File(basis, "databases"), File(basis, "app_webview"))
            .forEach { runCatching { it.deleteRecursively() } }
        context.getExternalFilesDirs(null).filterNotNull().forEach { runCatching { it.deleteRecursively() } }
        context.externalCacheDirs.filterNotNull().forEach { runCatching { it.deleteRecursively() } }
        File(basis, "shared_prefs").listFiles()?.forEach { runCatching { it.delete() } }
    }

    private fun medienLoeschen(context: Context) {
        if (Build.VERSION.SDK_INT < 29) return
        val resolver = context.contentResolver
        val ziele = listOf(
            MediaStore.Images.Media.EXTERNAL_CONTENT_URI to "Pictures/Jon%",
            MediaStore.Downloads.EXTERNAL_CONTENT_URI to "Download/Jon%",
            MediaStore.Video.Media.EXTERNAL_CONTENT_URI to "Movies/Jon%",
            MediaStore.Audio.Media.EXTERNAL_CONTENT_URI to "Music/Jon%",
        )
        for ((uri, pfad) in ziele) {
            runCatching {
                resolver.query(uri, arrayOf(MediaStore.MediaColumns._ID), "${MediaStore.MediaColumns.RELATIVE_PATH} LIKE ?", arrayOf(pfad), null)?.use { zeiger ->
                    val spalte = zeiger.getColumnIndexOrThrow(MediaStore.MediaColumns._ID)
                    while (zeiger.moveToNext()) runCatching { resolver.delete(ContentUris.withAppendedId(uri, zeiger.getLong(spalte)), null, null) }
                }
            }
        }
    }

    fun neustarten(activity: Activity) {
        val ziel = activity.packageManager.getLaunchIntentForPackage(activity.packageName)?.component
        if (ziel != null) activity.startActivity(Intent.makeRestartActivityTask(ziel))
        activity.finishAffinity()
        Runtime.getRuntime().exit(0)
    }
}
