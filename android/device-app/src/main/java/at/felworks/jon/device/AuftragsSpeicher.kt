package at.felworks.jon.device

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper

class AuftragsSpeicher(private val context: Context) : SQLiteOpenHelper(context, "jon-auftraege.db", null, 1) {
    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL("CREATE TABLE erledigt (id TEXT PRIMARY KEY NOT NULL, zeit INTEGER NOT NULL)")
    }

    override fun onUpgrade(db: SQLiteDatabase, alt: Int, neu: Int) = Unit

    fun vormerken(id: String): Boolean {
        require(id.isNotBlank() && id.length <= 128)
        if (context.getSharedPreferences("jon-auftraege", Context.MODE_PRIVATE).contains(id)) return false
        val werte = ContentValues().apply {
            put("id", id)
            put("zeit", System.currentTimeMillis())
        }
        return writableDatabase.insertWithOnConflict("erledigt", null, werte, SQLiteDatabase.CONFLICT_IGNORE) != -1L
    }
}
