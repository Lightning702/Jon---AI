package at.felworks.jon.ki

import android.content.ContentValues
import android.content.Context
import android.os.Build
import android.provider.MediaStore
import android.util.Base64
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.File
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

object Arbeitsraum {
    val textEndungen = setOf("html", "htm", "css", "js", "mjs", "json", "md", "txt", "csv", "py", "kt", "java", "ts", "tsx", "jsx", "xml", "svg", "yml", "yaml", "sh", "sql", "ini", "toml")

    fun wurzel(context: Context): File = File(context.filesDir, "arbeit").apply { mkdirs() }

    fun datei(context: Context, pfad: String): File {
        val sauber = pfad.trim().replace('\\', '/').trimStart('/').removePrefix("arbeit/")
        require(sauber.isNotEmpty() && !sauber.split('/').any { it == ".." || it.startsWith(".") && it.length > 1 && it != ".well-known" }) { "Ungültiger Pfad." }
        val ziel = File(wurzel(context), sauber).canonicalFile
        require(ziel.path.startsWith(wurzel(context).canonicalPath)) { "Der Pfad liegt außerhalb des Arbeitsordners." }
        return ziel
    }

    fun relativ(context: Context, datei: File): String = datei.canonicalPath.removePrefix(wurzel(context).canonicalPath).trimStart('/', '\\').replace('\\', '/')

    fun schreiben(context: Context, pfad: String, inhalt: String): JSONObject {
        require(inhalt.length <= 2_000_000) { "Die Datei ist zu groß." }
        val ziel = datei(context, pfad)
        ziel.parentFile?.mkdirs()
        ziel.writeText(inhalt)
        val rel = relativ(context, ziel)
        return JSONObject().put("ok", true).put("pfad", rel).put("bytes", ziel.length())
            .put("karte", JSONObject().put("kind", "handy-datei").put("data", JSONObject().put("dateien", JSONArray().put(eintrag(context, ziel)))))
    }

    fun lesen(context: Context, pfad: String): JSONObject {
        val ziel = datei(context, pfad)
        check(ziel.isFile) { "Die Datei $pfad gibt es nicht." }
        check(ziel.length() <= 2_000_000) { "Die Datei ist zu groß zum Lesen." }
        return JSONObject().put("pfad", relativ(context, ziel)).put("inhalt", ziel.readText().take(60_000))
    }

    fun eintrag(context: Context, datei: File): JSONObject = JSONObject().put("name", datei.name).put("pfad", relativ(context, datei))
        .put("ordner", datei.isDirectory).put("groesse", if (datei.isFile) datei.length() else 0).put("zeit", datei.lastModified())
        .put("endung", datei.extension.lowercase())

    fun liste(context: Context, ordner: String): JSONObject {
        val basis = if (ordner.isBlank()) wurzel(context) else datei(context, ordner)
        check(basis.isDirectory) { "Diesen Ordner gibt es nicht." }
        val eintraege = JSONArray()
        basis.walkTopDown().maxDepth(4).filter { it != basis }.take(400).forEach { eintraege.put(eintrag(context, it)) }
        return JSONObject().put("ordner", if (basis == wurzel(context)) "" else relativ(context, basis)).put("eintraege", eintraege)
    }

    fun inhaltBase64(context: Context, pfad: String): JSONObject {
        val ziel = datei(context, pfad)
        check(ziel.isFile && ziel.length() <= 8_000_000) { "Datei nicht verfügbar." }
        return JSONObject().put("name", ziel.name).put("data", Base64.encodeToString(ziel.readBytes(), Base64.NO_WRAP))
            .put("mime", mime(ziel.name))
    }

    fun mime(name: String): String = when (name.substringAfterLast('.', "").lowercase()) {
        "html", "htm" -> "text/html"; "css" -> "text/css"; "js", "mjs" -> "text/javascript"; "json" -> "application/json"
        "svg" -> "image/svg+xml"; "png" -> "image/png"; "jpg", "jpeg" -> "image/jpeg"; "gif" -> "image/gif"; "webp" -> "image/webp"
        "woff2" -> "font/woff2"; "woff" -> "font/woff"; "ttf" -> "font/ttf"; "mp3" -> "audio/mpeg"; "wav" -> "audio/wav"; "mp4" -> "video/mp4"
        "md" -> "text/markdown"; "txt" -> "text/plain"; "csv" -> "text/csv"; "py" -> "text/x-python"; "pdf" -> "application/pdf"; "zip" -> "application/zip"
        else -> "application/octet-stream"
    }

    fun exportieren(context: Context, pfad: String): JSONObject {
        val ziel = datei(context, pfad)
        check(ziel.exists()) { "Nicht gefunden." }
        val (name, daten, typ) = if (ziel.isDirectory) {
            val puffer = ByteArrayOutputStream()
            ZipOutputStream(puffer).use { zip ->
                ziel.walkTopDown().filter { it.isFile }.take(2000).forEach { datei ->
                    zip.putNextEntry(ZipEntry(ziel.name + "/" + datei.relativeTo(ziel).path.replace('\\', '/')))
                    datei.inputStream().use { it.copyTo(zip) }
                    zip.closeEntry()
                }
            }
            Triple(ziel.name + ".zip", puffer.toByteArray(), "application/zip")
        } else Triple(ziel.name, ziel.readBytes(), mime(ziel.name))
        check(daten.size <= 64_000_000) { "Zu groß zum Speichern." }
        if (Build.VERSION.SDK_INT >= 29) {
            val werte = ContentValues().apply {
                put(MediaStore.Downloads.DISPLAY_NAME, name)
                put(MediaStore.Downloads.MIME_TYPE, typ)
                put(MediaStore.Downloads.RELATIVE_PATH, "Download/Jon")
                put(MediaStore.Downloads.IS_PENDING, 1)
            }
            val resolver = context.contentResolver
            val uri = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, werte) ?: error("Speichern fehlgeschlagen.")
            resolver.openOutputStream(uri)?.use { it.write(daten) } ?: error("Speichern fehlgeschlagen.")
            werte.clear()
            werte.put(MediaStore.Downloads.IS_PENDING, 0)
            resolver.update(uri, werte, null, null)
        } else File(context.getExternalFilesDir(null), name).writeBytes(daten)
        return JSONObject().put("saved", name)
    }

    fun loeschen(context: Context, pfad: String): Boolean {
        val ziel = datei(context, pfad)
        return if (ziel.isDirectory) ziel.deleteRecursively() else ziel.delete()
    }
}
