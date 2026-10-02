package at.felworks.jon.device

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.graphics.drawable.Icon
import android.os.Build
import android.service.quicksettings.Tile
import android.service.quicksettings.TileService
import android.widget.RemoteViews
import at.felworks.jon.MainActivity
import at.felworks.jon.R

class JonWidget : AppWidgetProvider() {
    override fun onUpdate(context: Context, manager: AppWidgetManager, ids: IntArray) {
        val ansicht = ansicht(context)
        ids.forEach { manager.updateAppWidget(it, ansicht) }
    }

    companion object {
        private fun absicht(context: Context, sprechen: Boolean, code: Int): PendingIntent =
            PendingIntent.getActivity(context, code, Intent(context, MainActivity::class.java).putExtra("sprechen", sprechen).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP),
                PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)

        private fun info(context: Context): String {
            val teile = mutableListOf<String>()
            runCatching { Schritte.heute(context) }.getOrNull()?.takeIf { it > 0 }?.let { teile += "👣 ${"%,d".format(it).replace(',', '.')}" }
            runCatching { Uhren.naechsterText(context) }.getOrNull()?.takeIf { it.isNotBlank() }?.let { teile += "⏰ $it" }
            return teile.joinToString(" · ").ifBlank { "Tippe, um mit Jon zu schreiben" }
        }

        fun ansicht(context: Context): RemoteViews = RemoteViews(context.packageName, R.layout.jon_widget).apply {
            setTextViewText(R.id.widget_info, info(context))
            setOnClickPendingIntent(R.id.widget_flaeche, absicht(context, false, 4950))
            setOnClickPendingIntent(R.id.widget_sprechen, absicht(context, true, 4951))
        }

        fun aktualisieren(context: Context) {
            val manager = AppWidgetManager.getInstance(context) ?: return
            val ids = manager.getAppWidgetIds(ComponentName(context, JonWidget::class.java))
            if (ids.isNotEmpty()) manager.updateAppWidget(ids, ansicht(context))
        }
    }
}

class SprechenKachel : TileService() {
    override fun onStartListening() {
        super.onStartListening()
        qsTile?.apply {
            state = Tile.STATE_INACTIVE
            label = "Mit Jon sprechen"
            icon = Icon.createWithResource(this@SprechenKachel, R.drawable.ic_mikro)
            updateTile()
        }
    }

    override fun onClick() {
        super.onClick()
        val intent = Intent(this, MainActivity::class.java).putExtra("sprechen", true).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
        if (Build.VERSION.SDK_INT >= 34) startActivityAndCollapse(PendingIntent.getActivity(this, 4960, intent, PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT))
        else @Suppress("DEPRECATION") startActivityAndCollapse(intent)
    }
}
