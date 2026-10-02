package at.felworks.jon.device

import android.content.ContentUris
import android.content.ContentValues
import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import android.util.Base64
import android.util.Size
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.File
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter

object Fotos {
    private const val ORDNER = "Pictures/Jon"

    fun drehen(bild: Bitmap, grad: Int, spiegeln: Boolean = false): Bitmap {
        if (grad % 360 == 0 && !spiegeln) return bild
        val matrix = Matrix().apply {
            postRotate(grad.toFloat())
            if (spiegeln) postScale(-1f, 1f)
        }
        return Bitmap.createBitmap(bild, 0, 0, bild.width, bild.height, matrix, true)
    }

    fun verkleinern(bild: Bitmap, kante: Int): Bitmap {
        val groesste = maxOf(bild.width, bild.height)
        if (groesste <= kante) return bild
        val faktor = kante.toFloat() / groesste
        return Bitmap.createScaledBitmap(bild, (bild.width * faktor).toInt().coerceAtLeast(1), (bild.height * faktor).toInt().coerceAtLeast(1), true)
    }

    fun jpeg(bild: Bitmap, qualitaet: Int = 88): ByteArray = ByteArrayOutputStream().use { aus ->
        bild.compress(Bitmap.CompressFormat.JPEG, qualitaet, aus)
        aus.toByteArray()
    }

    fun base64(daten: ByteArray): String = Base64.encodeToString(daten, Base64.NO_WRAP)

    fun speichern(context: Context, bild: Bitmap): JSONObject {
        val name = "Jon-Foto-${LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd-HHmmss"))}.jpg"
        val daten = jpeg(bild, 92)
        if (Build.VERSION.SDK_INT >= 29) {
            val resolver = context.contentResolver
            val werte = ContentValues().apply {
                put(MediaStore.Images.Media.DISPLAY_NAME, name)
                put(MediaStore.Images.Media.MIME_TYPE, "image/jpeg")
                put(MediaStore.Images.Media.RELATIVE_PATH, ORDNER)
                put(MediaStore.Images.Media.IS_PENDING, 1)
            }
            val uri = resolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, werte) ?: error("Foto konnte nicht gespeichert werden.")
            try {
                resolver.openOutputStream(uri)?.use { it.write(daten) } ?: error("Foto konnte nicht gespeichert werden.")
                werte.clear()
                werte.put(MediaStore.Images.Media.IS_PENDING, 0)
                resolver.update(uri, werte, null, null)
            } catch (e: Exception) {
                resolver.delete(uri, null, null)
                throw e
            }
            return JSONObject().put("name", name).put("id", ContentUris.parseId(uri))
        }
        val ordner = File(context.getExternalFilesDir(Environment.DIRECTORY_PICTURES), "Jon").apply { mkdirs() }
        File(ordner, name).writeBytes(daten)
        return JSONObject().put("name", name).put("id", -1)
    }

    private fun uri(id: Long): Uri = ContentUris.withAppendedId(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, id)

    fun liste(context: Context, grenze: Int = 48): JSONArray {
        val ergebnis = JSONArray()
        if (Build.VERSION.SDK_INT < 29) return ergebnis
        val spalten = arrayOf(MediaStore.Images.Media._ID, MediaStore.Images.Media.DISPLAY_NAME, MediaStore.Images.Media.DATE_ADDED)
        context.contentResolver.query(
            MediaStore.Images.Media.EXTERNAL_CONTENT_URI, spalten,
            "${MediaStore.Images.Media.RELATIVE_PATH} LIKE ?", arrayOf("$ORDNER%"),
            "${MediaStore.Images.Media.DATE_ADDED} DESC"
        )?.use { zeiger ->
            while (zeiger.moveToNext() && ergebnis.length() < grenze) {
                val id = zeiger.getLong(0)
                val vorschau = runCatching { context.contentResolver.loadThumbnail(uri(id), Size(260, 260), null) }.getOrNull() ?: continue
                ergebnis.put(JSONObject().put("id", id).put("name", zeiger.getString(1)).put("zeit", zeiger.getLong(2) * 1000)
                    .put("vorschau", base64(jpeg(vorschau, 72))))
            }
        }
        return ergebnis
    }

    fun laden(context: Context, id: Long): JSONObject {
        val daten = context.contentResolver.openInputStream(uri(id))?.use { it.readBytes() } ?: error("Foto nicht gefunden.")
        val bild = BitmapFactory.decodeByteArray(daten, 0, daten.size) ?: error("Foto nicht lesbar.")
        return JSONObject().put("id", id).put("mime", "image/jpeg").put("data", base64(jpeg(verkleinern(bild, 1800), 86)))
    }

    fun loeschen(context: Context, id: Long): Boolean = runCatching { context.contentResolver.delete(uri(id), null, null) > 0 }.getOrDefault(false)
}
