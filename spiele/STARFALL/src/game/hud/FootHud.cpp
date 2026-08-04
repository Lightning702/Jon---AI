#include "FootHud.hpp"

#include "../../engine/math/Scalar.hpp"

#include <cstdio>

namespace sf {
namespace {

Vec4 barColor(const UIStyle& style, f64 fraction) {
    if (fraction < 0.20) return style.danger;
    if (fraction < 0.45) return style.warning;
    return style.accent;
}

std::string trimToWidth(UIRenderer& ui, const std::string& text, f32 scale, f32 availableWidth) {
    if (ui.textWidth(text, scale) <= availableWidth) return text;
    const usize maximum = static_cast<usize>(availableWidth / (6.0f * scale));
    if (maximum <= 3) return std::string();
    return text.substr(0, maximum - 3) + "...";
}

}

void FootHud::draw(UIRenderer& ui, const PlayerCharacter& player, const FootHudFrame& frame, const BaseGrid& base,
                   const TradeMarket* market, const DiscoveryCatalog& catalog,
                   const std::vector<const Recipe*>& recipes,
                   const std::vector<const BuildPartDefinition*>& parts) {
    pulse += 0.016f;

    drawVitals(ui, player, frame);
    drawEnvironment(ui, frame);
    drawToolBar(ui, player, frame);
    drawCrosshair(ui, player, frame);

    switch (frame.panel) {
        case FootPanel::Inventory: drawInventoryPanel(ui, player.inventory(), frame); break;
        case FootPanel::Crafting: drawCraftingPanel(ui, player.inventory(), recipes, frame); break;
        case FootPanel::Build: drawBuildPanel(ui, player.inventory(), parts, base, frame); break;
        case FootPanel::Trade: drawTradePanel(ui, player.inventory(), market, frame); break;
        case FootPanel::Catalog: drawCatalogPanel(ui, catalog, frame); break;
        default: break;
    }

    const UIStyle& style = ui.style();
    if (!frame.statusMessage.empty()) {
        const f32 width = ui.textWidth(frame.statusMessage, 1.6f) + 40.0f;
        const f32 x = static_cast<f32>(ui.surfaceWidth()) * 0.5f - width * 0.5f;
        const f32 y = static_cast<f32>(ui.surfaceHeight()) * 0.70f;
        ui.drawHologramPanel(x, y, width, 44.0f, style, 0.5f + 0.5f * std::sin(pulse * 4.0f));
        ui.drawText(frame.statusMessage, static_cast<f32>(ui.surfaceWidth()) * 0.5f, y + 17.0f, 1.6f, style.accent,
                    TextAlign::Center);
    }

    char corner[128];
    std::snprintf(corner, sizeof(corner), "%.0f fps  %s", frame.framesPerSecond, frame.qualityPreset.c_str());
    ui.drawText(corner, static_cast<f32>(ui.surfaceWidth()) - 24.0f, 24.0f, 1.3f, style.textDim, TextAlign::Right);

    char credits[96];
    std::snprintf(credits, sizeof(credits), "%.0f EINHEITEN", frame.credits);
    ui.drawText(credits, static_cast<f32>(ui.surfaceWidth()) - 24.0f, 44.0f, 1.5f, style.voidGold, TextAlign::Right);
}

void FootHud::drawVitals(UIRenderer& ui, const PlayerCharacter& player, const FootHudFrame& frame) {
    const UIStyle& style = ui.style();
    const SurvivalStats& survival = player.survival();
    const f32 panelX = 24.0f;
    const f32 panelHeight = 176.0f;
    const f32 panelY = static_cast<f32>(ui.surfaceHeight()) - panelHeight - 24.0f;
    const f32 panelWidth = 292.0f;

    ui.drawHologramPanel(panelX, panelY, panelWidth, panelHeight, style, 0.5f + 0.5f * std::sin(pulse * 1.5f));

    struct Row {
        const char* label;
        f64 value;
    };
    const Row rows[] = {{"GESUNDHEIT", survival.health()},
                        {"LEBENSERHALT", survival.lifeSupport()},
                        {"SCHUTZ", survival.hazardProtection()},
                        {"SAUERSTOFF", survival.oxygenReserve()},
                        {"AUSDAUER", survival.stamina()},
                        {"JETPACK", survival.jetpackFuel()}};

    f32 rowY = panelY + 14.0f;
    for (const Row& row : rows) {
        ui.drawText(row.label, panelX + 14.0f, rowY, 1.3f, style.textDim);
        ui.drawProgressBar(panelX + 128.0f, rowY - 2.0f, panelWidth - 146.0f, 11.0f,
                           static_cast<f32>(clampValue(row.value, 0.0, 1.0)), barColor(style, row.value),
                           style.accentDim);
        rowY += 20.0f;
    }

    if (survival.activeHazard() != HazardKind::None) {
        char line[128];
        std::snprintf(line, sizeof(line), "%s  %.0f%%", SurvivalStats::hazardName(survival.activeHazard()),
                      survival.hazardSeverity() * 100.0);
        ui.drawText(line, panelX + 14.0f, rowY + 4.0f, 1.4f, style.warning);
    }
    if (!survival.lastWarning().empty()) {
        ui.drawText(survival.lastWarning(), panelX + 14.0f, rowY + 24.0f, 1.4f, style.danger);
    }
    if (frame.inShelter) {
        ui.drawText("UNTERSTAND", panelX + 14.0f, rowY + 24.0f, 1.4f, style.accent);
    }
}

void FootHud::drawEnvironment(UIRenderer& ui, const FootHudFrame& frame) {
    const UIStyle& style = ui.style();
    const f32 panelWidth = 300.0f;
    const f32 panelX = static_cast<f32>(ui.surfaceWidth()) - panelWidth - 24.0f;
    const f32 panelY = static_cast<f32>(ui.surfaceHeight()) - 158.0f - 24.0f;

    ui.drawHologramPanel(panelX, panelY, panelWidth, 158.0f, style, 0.5f + 0.5f * std::sin(pulse * 1.1f));

    char line[160];
    f32 rowY = panelY + 14.0f;
    ui.drawText(trimToWidth(ui, frame.planetName, 1.7f, panelWidth - 28.0f), panelX + 14.0f, rowY, 1.7f, style.text);
    rowY += 24.0f;
    ui.drawText(frame.biomeName, panelX + 14.0f, rowY, 1.4f, style.accent);
    rowY += 20.0f;

    std::snprintf(line, sizeof(line), "TEMPERATUR %.0f K  /  %.0f C", frame.temperatureKelvin,
                  frame.temperatureKelvin - 273.15);
    ui.drawText(line, panelX + 14.0f, rowY, 1.3f, style.textDim);
    rowY += 18.0f;

    std::snprintf(line, sizeof(line), "HOEHE %.0f m", frame.altitudeMeters);
    ui.drawText(line, panelX + 14.0f, rowY, 1.3f, style.textDim);
    rowY += 18.0f;

    const f64 hours = frame.localTimeFraction * 24.0;
    std::snprintf(line, sizeof(line), "ORTSZEIT %02.0f:%02.0f", std::floor(hours), (hours - std::floor(hours)) * 60.0);
    ui.drawText(line, panelX + 14.0f, rowY, 1.3f, style.textDim);
    rowY += 18.0f;

    if (!frame.weatherLine.empty()) {
        ui.drawText(frame.weatherLine, panelX + 14.0f, rowY, 1.3f, style.warning);
        rowY += 18.0f;
    }

    std::snprintf(line, sizeof(line), "SCHIFF %.0f m", frame.shipDistanceMeters);
    ui.drawText(line, panelX + 14.0f, rowY, 1.3f, style.accentDim);
}

void FootHud::drawToolBar(UIRenderer& ui, const PlayerCharacter& player, const FootHudFrame& frame) {
    const UIStyle& style = ui.style();
    const f32 centerX = static_cast<f32>(ui.surfaceWidth()) * 0.5f;
    const f32 barY = static_cast<f32>(ui.surfaceHeight()) - 54.0f;

    ui.drawText(frame.toolLabel, centerX, barY, 1.6f, style.accent, TextAlign::Center);
    ui.drawProgressBar(centerX - 90.0f, barY + 22.0f, 180.0f, 8.0f,
                       clampValue(player.beamCharge() / 1.4f, 0.0f, 1.0f),
                       player.beamCharge() > 1.1f ? style.danger : style.accentDim, style.accentDim);

    if (!frame.buildMessage.empty()) {
        ui.drawText(frame.buildMessage, centerX, barY - 24.0f, 1.4f,
                    frame.buildMessage[0] == 'P' ? style.accent : style.warning, TextAlign::Center);
    }
}

void FootHud::drawCrosshair(UIRenderer& ui, const PlayerCharacter& player, const FootHudFrame& frame) {
    const UIStyle& style = ui.style();
    const f32 centerX = static_cast<f32>(ui.surfaceWidth()) * 0.5f;
    const f32 centerY = static_cast<f32>(ui.surfaceHeight()) * 0.5f;

    Vec4 color = style.accent;
    color.w = 0.7f;
    ui.drawRect(centerX - 1.0f, centerY - 1.0f, 2.0f, 2.0f, color);
    ui.drawCircleOutline(centerX, centerY, 12.0f, 1.4f, 28, Vec4(color.x, color.y, color.z, 0.28f));

    if (frame.scanning) {
        ui.drawCircleOutline(centerX, centerY, 20.0f + static_cast<f32>(frame.scanProgress) * 26.0f, 2.0f, 48,
                             style.accent);
        ui.drawText("SCAN", centerX, centerY + 56.0f, 1.4f, style.accent, TextAlign::Center);
    }

    if (!frame.interactionPrompt.empty()) {
        ui.drawText(frame.interactionPrompt, centerX, centerY + 34.0f, 1.5f, style.text, TextAlign::Center);
    }
    (void)player;
}

void FootHud::drawInventoryPanel(UIRenderer& ui, const Inventory& inventory, const FootHudFrame& frame) {
    const UIStyle& style = ui.style();
    const f32 width = clampValue(static_cast<f32>(ui.surfaceWidth()) * 0.52f, 520.0f, 840.0f);
    const f32 height = clampValue(static_cast<f32>(ui.surfaceHeight()) * 0.62f, 380.0f, 620.0f);
    const f32 x = static_cast<f32>(ui.surfaceWidth()) * 0.5f - width * 0.5f;
    const f32 y = static_cast<f32>(ui.surfaceHeight()) * 0.5f - height * 0.5f;

    ui.drawRect(0.0f, 0.0f, static_cast<f32>(ui.surfaceWidth()), static_cast<f32>(ui.surfaceHeight()),
                Vec4(0.0f, 0.0f, 0.0f, 0.55f));
    ui.drawHologramPanel(x, y, width, height, style, 0.5f + 0.5f * std::sin(pulse * 1.4f));
    ui.drawText(inventory.label(), x + 18.0f, y + 16.0f, 2.0f, style.accent);

    char header[160];
    std::snprintf(header, sizeof(header), "%u/%u SLOTS  %.0f kg  WERT %.0f",
                  inventory.slotCount() - inventory.freeSlots(), inventory.slotCount(),
                  inventory.totalMassKilograms(), inventory.totalValue());
    ui.drawText(header, x + width - 18.0f, y + 20.0f, 1.3f, style.textDim, TextAlign::Right);

    const u32 columns = 6;
    const f32 cellWidth = (width - 36.0f) / static_cast<f32>(columns);
    const f32 cellHeight = 46.0f;
    f32 cellY = y + 50.0f;

    for (u32 index = 0; index < inventory.slotCount(); ++index) {
        const u32 column = index % columns;
        if (column == 0 && index > 0) cellY += cellHeight + 4.0f;
        if (cellY + cellHeight > y + height - 12.0f) break;

        const f32 cellX = x + 18.0f + static_cast<f32>(column) * cellWidth;
        const ItemStack& stack = inventory.slot(index);

        Vec4 background = Vec4(0.06f, 0.10f, 0.13f, 0.72f);
        ui.drawRect(cellX, cellY, cellWidth - 6.0f, cellHeight, background);
        ui.drawRectOutline(cellX, cellY, cellWidth - 6.0f, cellHeight, 1.0f, style.accentDim);

        if (stack.empty()) continue;
        const ItemDefinition& definition = ItemDatabase::instance().definition(stack.id);
        ui.drawRect(cellX + 4.0f, cellY + 4.0f, 6.0f, cellHeight - 8.0f,
                    Vec4(definition.tint.x, definition.tint.y, definition.tint.z, 1.0f));
        ui.drawText(trimToWidth(ui, definition.name, 1.2f, cellWidth - 26.0f), cellX + 16.0f, cellY + 8.0f, 1.2f,
                    style.text);
        char amount[32];
        std::snprintf(amount, sizeof(amount), "%u", stack.count);
        ui.drawText(amount, cellX + cellWidth - 12.0f, cellY + 26.0f, 1.4f, style.accent, TextAlign::Right);
    }

    ui.drawText("TAB SCHLIESSEN   1-6 VERBRAUCHEN", x + 18.0f, y + height - 22.0f, 1.2f, style.textDim);
    (void)frame;
}

void FootHud::drawCraftingPanel(UIRenderer& ui, const Inventory& inventory, const std::vector<const Recipe*>& recipes,
                                const FootHudFrame& frame) {
    const UIStyle& style = ui.style();
    const f32 width = clampValue(static_cast<f32>(ui.surfaceWidth()) * 0.46f, 460.0f, 720.0f);
    const f32 height = clampValue(static_cast<f32>(ui.surfaceHeight()) * 0.60f, 360.0f, 580.0f);
    const f32 x = static_cast<f32>(ui.surfaceWidth()) * 0.5f - width * 0.5f;
    const f32 y = static_cast<f32>(ui.surfaceHeight()) * 0.5f - height * 0.5f;

    ui.drawRect(0.0f, 0.0f, static_cast<f32>(ui.surfaceWidth()), static_cast<f32>(ui.surfaceHeight()),
                Vec4(0.0f, 0.0f, 0.0f, 0.55f));
    ui.drawHologramPanel(x, y, width, height, style, 0.5f + 0.5f * std::sin(pulse * 1.4f));
    ui.drawText("HERSTELLUNG", x + 18.0f, y + 16.0f, 2.0f, style.accent);

    if (recipes.empty()) {
        ui.drawText("KEIN REZEPT MIT DEM AKTUELLEN MATERIAL", x + 18.0f, y + 60.0f, 1.4f, style.textDim);
        return;
    }

    f32 rowY = y + 52.0f;
    const u32 visible = 12;
    const u32 start = frame.selectedRecipeIndex >= visible ? frame.selectedRecipeIndex - visible + 1 : 0;
    for (u32 index = start; index < recipes.size() && index < start + visible; ++index) {
        const Recipe& recipe = *recipes[index];
        const bool selected = index == frame.selectedRecipeIndex;
        if (selected) {
            Vec4 highlight = style.accent;
            highlight.w = 0.16f;
            ui.drawRect(x + 12.0f, rowY - 4.0f, width - 24.0f, 30.0f, highlight);
        }
        const ItemDefinition& output = ItemDatabase::instance().definition(recipe.output);
        char line[200];
        std::snprintf(line, sizeof(line), "%s x%u", output.name.c_str(), recipe.outputAmount);
        ui.drawText(line, x + 20.0f, rowY, 1.4f, selected ? style.accent : style.text);

        std::string cost;
        for (const RecipeIngredient& ingredient : recipe.inputs) {
            const ItemDefinition& definition = ItemDatabase::instance().definition(ingredient.id);
            char part[80];
            std::snprintf(part, sizeof(part), "%s %u/%u  ", definition.shortName.c_str(),
                          inventory.count(ingredient.id), ingredient.amount);
            cost += part;
        }
        ui.drawText(trimToWidth(ui, cost, 1.1f, width - 44.0f), x + 20.0f, rowY + 15.0f, 1.1f,
                    canCraft(recipe, inventory, 5) ? style.textDim : style.danger);
        rowY += 32.0f;
    }

    ui.drawText("PFEILE WAEHLEN   ENTER HERSTELLEN   X SCHLIESSEN", x + 18.0f, y + height - 22.0f, 1.2f,
                style.textDim);
}

void FootHud::drawBuildPanel(UIRenderer& ui, const Inventory& inventory,
                             const std::vector<const BuildPartDefinition*>& parts, const BaseGrid& base,
                             const FootHudFrame& frame) {
    const UIStyle& style = ui.style();
    const f32 width = 380.0f;
    const f32 height = clampValue(static_cast<f32>(ui.surfaceHeight()) * 0.58f, 340.0f, 560.0f);
    const f32 x = 24.0f;
    const f32 y = static_cast<f32>(ui.surfaceHeight()) * 0.5f - height * 0.5f;

    ui.drawHologramPanel(x, y, width, height, style, 0.5f + 0.5f * std::sin(pulse * 1.4f));
    ui.drawText("BAUMODUS", x + 18.0f, y + 16.0f, 1.9f, style.accent);

    const BasePowerReport report = base.powerReport();
    char header[160];
    std::snprintf(header, sizeof(header), "%s  %u TEILE  ENERGIE %+.1f", base.name().c_str(),
                  static_cast<u32>(base.parts().size()), report.balance);
    ui.drawText(header, x + 18.0f, y + 40.0f, 1.2f, report.stable ? style.textDim : style.warning);

    f32 rowY = y + 64.0f;
    const u32 visible = 13;
    const u32 start = frame.selectedPartIndex >= visible ? frame.selectedPartIndex - visible + 1 : 0;
    for (u32 index = start; index < parts.size() && index < start + visible; ++index) {
        const BuildPartDefinition& definition = *parts[index];
        const bool selected = index == frame.selectedPartIndex;
        if (selected) {
            Vec4 highlight = style.accent;
            highlight.w = 0.16f;
            ui.drawRect(x + 12.0f, rowY - 4.0f, width - 24.0f, 30.0f, highlight);
        }
        ui.drawText(trimToWidth(ui, definition.name, 1.4f, width - 44.0f), x + 20.0f, rowY, 1.4f,
                    selected ? style.accent : style.text);

        std::string cost;
        bool affordable = true;
        for (const RecipeIngredient& ingredient : definition.cost) {
            const ItemDefinition& item = ItemDatabase::instance().definition(ingredient.id);
            char part[80];
            std::snprintf(part, sizeof(part), "%s %u/%u  ", item.shortName.c_str(), inventory.count(ingredient.id),
                          ingredient.amount);
            cost += part;
            if (inventory.count(ingredient.id) < ingredient.amount) affordable = false;
        }
        ui.drawText(trimToWidth(ui, cost, 1.1f, width - 44.0f), x + 20.0f, rowY + 15.0f, 1.1f,
                    affordable ? style.textDim : style.danger);
        rowY += 32.0f;
    }

    ui.drawText("PFEILE WAEHLEN   LMB SETZEN   RMB ABBAUEN   B SCHLIESSEN", x + 18.0f, y + height - 22.0f, 1.1f,
                style.textDim);
}

void FootHud::drawTradePanel(UIRenderer& ui, const Inventory& inventory, const TradeMarket* market,
                             const FootHudFrame& frame) {
    if (!market) return;
    const UIStyle& style = ui.style();
    const f32 width = clampValue(static_cast<f32>(ui.surfaceWidth()) * 0.52f, 540.0f, 820.0f);
    const f32 height = clampValue(static_cast<f32>(ui.surfaceHeight()) * 0.62f, 380.0f, 600.0f);
    const f32 x = static_cast<f32>(ui.surfaceWidth()) * 0.5f - width * 0.5f;
    const f32 y = static_cast<f32>(ui.surfaceHeight()) * 0.5f - height * 0.5f;

    ui.drawRect(0.0f, 0.0f, static_cast<f32>(ui.surfaceWidth()), static_cast<f32>(ui.surfaceHeight()),
                Vec4(0.0f, 0.0f, 0.0f, 0.55f));
    ui.drawHologramPanel(x, y, width, height, style, 0.5f + 0.5f * std::sin(pulse * 1.3f));

    char header[200];
    std::snprintf(header, sizeof(header), "%s  [%s]", market->name().c_str(),
                  TradeMarket::specialisationName(market->specialisation()));
    ui.drawText(header, x + 18.0f, y + 16.0f, 1.8f, style.accent);
    std::snprintf(header, sizeof(header), "GUTHABEN %.0f", frame.credits);
    ui.drawText(header, x + width - 18.0f, y + 20.0f, 1.4f, style.voidGold, TextAlign::Right);

    f32 rowY = y + 54.0f;
    const u32 visible = 13;
    const std::vector<MarketEntry>& offers = market->entries();
    const u32 start = frame.selectedTradeIndex >= visible ? frame.selectedTradeIndex - visible + 1 : 0;

    for (u32 index = start; index < offers.size() && index < start + visible; ++index) {
        const MarketEntry& entry = offers[index];
        const bool selected = index == frame.selectedTradeIndex;
        if (selected) {
            Vec4 highlight = style.accent;
            highlight.w = 0.16f;
            ui.drawRect(x + 12.0f, rowY - 4.0f, width - 24.0f, 26.0f, highlight);
        }
        const ItemDefinition& definition = ItemDatabase::instance().definition(entry.id);
        ui.drawText(trimToWidth(ui, definition.name, 1.3f, width * 0.42f), x + 20.0f, rowY, 1.3f,
                    selected ? style.accent : style.text);

        char values[160];
        std::snprintf(values, sizeof(values), "KAUF %.0f   VERKAUF %.0f   LAGER %.0f   DU %u", entry.buyPrice(),
                      entry.sellPrice(), entry.stock, inventory.count(entry.id));
        ui.drawText(values, x + width - 20.0f, rowY, 1.15f, style.textDim, TextAlign::Right);
        rowY += 28.0f;
    }

    ui.drawText("PFEILE WAEHLEN   ENTER KAUFEN   RUECKTASTE VERKAUFEN   T SCHLIESSEN", x + 18.0f,
                y + height - 22.0f, 1.15f, style.textDim);
}

void FootHud::drawCatalogPanel(UIRenderer& ui, const DiscoveryCatalog& catalog, const FootHudFrame& frame) {
    const UIStyle& style = ui.style();
    const f32 width = clampValue(static_cast<f32>(ui.surfaceWidth()) * 0.50f, 520.0f, 800.0f);
    const f32 height = clampValue(static_cast<f32>(ui.surfaceHeight()) * 0.60f, 360.0f, 580.0f);
    const f32 x = static_cast<f32>(ui.surfaceWidth()) * 0.5f - width * 0.5f;
    const f32 y = static_cast<f32>(ui.surfaceHeight()) * 0.5f - height * 0.5f;

    ui.drawRect(0.0f, 0.0f, static_cast<f32>(ui.surfaceWidth()), static_cast<f32>(ui.surfaceHeight()),
                Vec4(0.0f, 0.0f, 0.0f, 0.55f));
    ui.drawHologramPanel(x, y, width, height, style, 0.5f + 0.5f * std::sin(pulse * 1.2f));
    ui.drawText("ENTDECKUNGEN", x + 18.0f, y + 16.0f, 1.9f, style.accent);

    char header[200];
    std::snprintf(header, sizeof(header), "%u ARTEN  %u WELTEN  %u SYSTEME  OFFEN %.0f",
                  catalog.speciesCatalogued(), catalog.planetsMapped(), catalog.systemsVisited(),
                  catalog.pendingRewardValue());
    ui.drawText(header, x + 18.0f, y + 42.0f, 1.2f, style.textDim);

    f32 rowY = y + 66.0f;
    const std::vector<DiscoveryEntry>& records = catalog.entries();
    const usize visible = 13;
    const usize start = records.size() > visible ? records.size() - visible : 0;
    for (usize index = start; index < records.size(); ++index) {
        const DiscoveryEntry& entry = records[index];
        char line[220];
        std::snprintf(line, sizeof(line), "[%s] %s", DiscoveryCatalog::kindName(entry.kind),
                      entry.displayName().c_str());
        ui.drawText(trimToWidth(ui, line, 1.3f, width * 0.62f), x + 20.0f, rowY, 1.3f,
                    entry.uploaded ? style.textDim : style.text);
        std::snprintf(line, sizeof(line), "%s  %.0f", entry.uploaded ? "GEMELDET" : "OFFEN", entry.rewardCredits);
        ui.drawText(line, x + width - 20.0f, rowY, 1.15f, entry.uploaded ? style.accentDim : style.voidGold,
                    TextAlign::Right);
        rowY += 26.0f;
    }

    ui.drawText("U ALLES MELDEN   K SCHLIESSEN", x + 18.0f, y + height - 22.0f, 1.2f, style.textDim);
    (void)frame;
}

}
