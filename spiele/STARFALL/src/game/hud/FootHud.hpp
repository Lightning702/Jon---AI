#pragma once

#include "../../engine/ui/UIRenderer.hpp"
#include "../alien/TradeMarket.hpp"
#include "../base/BaseGrid.hpp"
#include "../player/PlayerCharacter.hpp"
#include "../quest/DiscoveryCatalog.hpp"

#include <string>
#include <vector>

namespace sf {

enum class FootPanel : u32 {
    None = 0,
    Inventory,
    Crafting,
    Build,
    Trade,
    Catalog,
    Count
};

struct FootHudFrame {
    std::string planetName;
    std::string biomeName;
    std::string weatherLine;
    std::string interactionPrompt;
    std::string toolLabel;
    std::string statusMessage;
    std::string buildMessage;
    f64 credits = 0.0;
    f64 temperatureKelvin = 288.0;
    f64 altitudeMeters = 0.0;
    f64 localTimeFraction = 0.5;
    f64 shipDistanceMeters = 0.0;
    f64 scanProgress = 0.0;
    f64 framesPerSecond = 0.0;
    std::string qualityPreset;
    u32 selectedPartIndex = 0;
    u32 selectedRecipeIndex = 0;
    u32 selectedTradeIndex = 0;
    bool scanning = false;
    bool inShelter = false;
    FootPanel panel = FootPanel::None;
};

class FootHud {
public:
    void draw(UIRenderer& ui, const PlayerCharacter& player, const FootHudFrame& frame,
              const BaseGrid& base, const TradeMarket* market, const DiscoveryCatalog& catalog,
              const std::vector<const Recipe*>& recipes, const std::vector<const BuildPartDefinition*>& parts);

private:
    void drawVitals(UIRenderer& ui, const PlayerCharacter& player, const FootHudFrame& frame);
    void drawEnvironment(UIRenderer& ui, const FootHudFrame& frame);
    void drawToolBar(UIRenderer& ui, const PlayerCharacter& player, const FootHudFrame& frame);
    void drawCrosshair(UIRenderer& ui, const PlayerCharacter& player, const FootHudFrame& frame);
    void drawInventoryPanel(UIRenderer& ui, const Inventory& inventory, const FootHudFrame& frame);
    void drawCraftingPanel(UIRenderer& ui, const Inventory& inventory, const std::vector<const Recipe*>& recipes,
                           const FootHudFrame& frame);
    void drawBuildPanel(UIRenderer& ui, const Inventory& inventory,
                        const std::vector<const BuildPartDefinition*>& parts, const BaseGrid& base,
                        const FootHudFrame& frame);
    void drawTradePanel(UIRenderer& ui, const Inventory& inventory, const TradeMarket* market,
                        const FootHudFrame& frame);
    void drawCatalogPanel(UIRenderer& ui, const DiscoveryCatalog& catalog, const FootHudFrame& frame);

    f32 pulse = 0.0f;
};

}
