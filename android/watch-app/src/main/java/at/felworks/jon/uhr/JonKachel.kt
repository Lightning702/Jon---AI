package at.felworks.jon.uhr

import androidx.wear.protolayout.ActionBuilders
import androidx.wear.protolayout.ColorBuilders.argb
import androidx.wear.protolayout.DimensionBuilders.dp
import androidx.wear.protolayout.DimensionBuilders.sp
import androidx.wear.protolayout.LayoutElementBuilders
import androidx.wear.protolayout.ModifiersBuilders
import androidx.wear.protolayout.ResourceBuilders
import androidx.wear.protolayout.TimelineBuilders
import androidx.wear.tiles.RequestBuilders
import androidx.wear.tiles.TileBuilders
import androidx.wear.tiles.TileService
import com.google.common.util.concurrent.Futures
import com.google.common.util.concurrent.ListenableFuture

class JonKachel : TileService() {
    private val version = "2"

    private fun oeffnen(aktion: String): ModifiersBuilders.Clickable =
        ModifiersBuilders.Clickable.Builder()
            .setId(aktion)
            .setOnClick(
                ActionBuilders.LaunchAction.Builder()
                    .setAndroidActivity(
                        ActionBuilders.AndroidActivity.Builder()
                            .setPackageName(packageName)
                            .setClassName(MainActivity::class.java.name)
                            .addKeyToExtraMapping("aktion", ActionBuilders.AndroidStringExtra.Builder().setValue(aktion).build())
                            .build(),
                    )
                    .build(),
            )
            .build()

    private fun text(inhalt: String, groesse: Float, farbe: Int, fett: Boolean = false): LayoutElementBuilders.Text =
        LayoutElementBuilders.Text.Builder()
            .setText(inhalt)
            .setFontStyle(
                LayoutElementBuilders.FontStyle.Builder()
                    .setSize(sp(groesse))
                    .setColor(argb(farbe))
                    .setWeight(if (fett) LayoutElementBuilders.FONT_WEIGHT_BOLD else LayoutElementBuilders.FONT_WEIGHT_NORMAL)
                    .build(),
            )
            .build()

    private fun knopf(): LayoutElementBuilders.LayoutElement =
        LayoutElementBuilders.Box.Builder()
            .setWidth(dp(104f))
            .setHeight(dp(104f))
            .setModifiers(
                ModifiersBuilders.Modifiers.Builder()
                    .setClickable(oeffnen("sprechen"))
                    .setBackground(
                        ModifiersBuilders.Background.Builder()
                            .setColor(argb(0xFF0B0B0E.toInt()))
                            .setCorner(ModifiersBuilders.Corner.Builder().setRadius(dp(52f)).build())
                            .build(),
                    )
                    .setBorder(ModifiersBuilders.Border.Builder().setWidth(dp(5f)).setColor(argb(0xFFE2BD4C.toInt())).build())
                    .build(),
            )
            .addContent(
                LayoutElementBuilders.Column.Builder()
                    .addContent(text("Jon", 26f, 0xFFE2BD4C.toInt(), true))
                    .addContent(text("sprechen", 12f, 0xFFFFFFFF.toInt()))
                    .build(),
            )
            .build()

    private fun klingelChip(): LayoutElementBuilders.LayoutElement =
        LayoutElementBuilders.Box.Builder()
            .setWidth(dp(132f))
            .setHeight(dp(34f))
            .setModifiers(
                ModifiersBuilders.Modifiers.Builder()
                    .setClickable(oeffnen("klingeln"))
                    .setBackground(
                        ModifiersBuilders.Background.Builder()
                            .setColor(argb(0xFF2A2A30.toInt()))
                            .setCorner(ModifiersBuilders.Corner.Builder().setRadius(dp(17f)).build())
                            .build(),
                    )
                    .build(),
            )
            .addContent(text("Handy klingeln", 13f, 0xFFFFFFFF.toInt()))
            .build()

    override fun onTileRequest(requestParams: RequestBuilders.TileRequest): ListenableFuture<TileBuilders.Tile> {
        val inhalt = LayoutElementBuilders.Column.Builder()
            .setHorizontalAlignment(LayoutElementBuilders.HORIZONTAL_ALIGN_CENTER)
            .addContent(knopf())
            .addContent(LayoutElementBuilders.Spacer.Builder().setHeight(dp(10f)).build())
            .addContent(klingelChip())
            .build()
        val wurzel = LayoutElementBuilders.Box.Builder()
            .setWidth(androidx.wear.protolayout.DimensionBuilders.expand())
            .setHeight(androidx.wear.protolayout.DimensionBuilders.expand())
            .addContent(inhalt)
            .build()
        val kachel = TileBuilders.Tile.Builder()
            .setResourcesVersion(version)
            .setTileTimeline(TimelineBuilders.Timeline.fromLayoutElement(wurzel))
            .build()
        return Futures.immediateFuture(kachel)
    }

    override fun onTileResourcesRequest(requestParams: RequestBuilders.ResourcesRequest): ListenableFuture<ResourceBuilders.Resources> =
        Futures.immediateFuture(ResourceBuilders.Resources.Builder().setVersion(version).build())
}
