package at.felworks.jon.uhr

import android.app.PendingIntent
import android.content.Intent
import android.graphics.drawable.Icon
import androidx.wear.watchface.complications.data.ComplicationData
import androidx.wear.watchface.complications.data.ComplicationType
import androidx.wear.watchface.complications.data.MonochromaticImage
import androidx.wear.watchface.complications.data.MonochromaticImageComplicationData
import androidx.wear.watchface.complications.data.PlainComplicationText
import androidx.wear.watchface.complications.data.ShortTextComplicationData
import androidx.wear.watchface.complications.data.SmallImage
import androidx.wear.watchface.complications.data.SmallImageComplicationData
import androidx.wear.watchface.complications.data.SmallImageType
import androidx.wear.watchface.complications.datasource.ComplicationRequest
import androidx.wear.watchface.complications.datasource.SuspendingComplicationDataSourceService

class JonKomplikation : SuspendingComplicationDataSourceService() {
    private fun tippen(): PendingIntent = PendingIntent.getActivity(
        this,
        7400,
        Intent(this, MainActivity::class.java).putExtra("aktion", "sprechen").addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP),
        PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
    )

    private fun daten(typ: ComplicationType, aktion: PendingIntent?): ComplicationData? {
        val beschreibung = PlainComplicationText.Builder("Mit Jon sprechen").build()
        val bild = MonochromaticImage.Builder(Icon.createWithResource(this, R.drawable.jon_icon_mono)).build()
        return when (typ) {
            ComplicationType.SHORT_TEXT -> ShortTextComplicationData.Builder(PlainComplicationText.Builder("Jon").build(), beschreibung)
                .setMonochromaticImage(bild)
                .setTapAction(aktion)
                .build()
            ComplicationType.MONOCHROMATIC_IMAGE -> MonochromaticImageComplicationData.Builder(bild, beschreibung)
                .setTapAction(aktion)
                .build()
            ComplicationType.SMALL_IMAGE -> SmallImageComplicationData.Builder(
                SmallImage.Builder(Icon.createWithResource(this, R.mipmap.ic_launcher), SmallImageType.ICON).build(),
                beschreibung,
            ).setTapAction(aktion).build()
            else -> null
        }
    }

    override fun getPreviewData(type: ComplicationType): ComplicationData? = daten(type, null)

    override suspend fun onComplicationRequest(request: ComplicationRequest): ComplicationData? = daten(request.complicationType, tippen())
}
