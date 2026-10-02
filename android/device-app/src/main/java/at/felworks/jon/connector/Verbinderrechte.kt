package at.felworks.jon.connector

import android.content.Context
import android.content.pm.PackageManager
import androidx.core.content.ContextCompat

object Verbinderrechte {
    fun erteilt(context: Context, recht: String): Boolean = ContextCompat.checkSelfPermission(context, recht) == PackageManager.PERMISSION_GRANTED
}
