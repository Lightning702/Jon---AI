#pragma once

#include "Terrain.h"
#include "../ui/UIRenderer.h"

namespace aeth {

enum MarkerShape {
    MARK_VILLAGE = 0,
    MARK_LANDMARK,
    MARK_QUEST,
    MARK_PLAYER,
    MARK_SHAPE_COUNT
};

struct MapMarker {
    em::Vec2 world;
    em::Vec4 color = em::Vec4(1, 1, 1, 1);
    std::string label;
    int shape = MARK_VILLAGE;
    bool known = true;
    bool onMinimap = true;
};

class WorldMap {
public:
    void build(const Terrain& terrain);
    void destroy();
    bool ready() const { return mapTexture && mapTexture->valid(); }

    void drawMinimap(echo::UIRenderer& ui, float cx, float cy, float size,
                     const em::Vec2& player, float yaw, float rangeMeters,
                     const std::vector<MapMarker>& markers) const;

    void drawFull(echo::UIRenderer& ui, float screenW, float screenH,
                  const em::Vec2& player, float yaw,
                  const std::vector<MapMarker>& markers,
                  const std::vector<std::string>& lines,
                  const std::string& title) const;

private:
    void drawMarker(echo::UIRenderer& ui, const MapMarker& m, float sx, float sy, float scale, bool labels) const;

    Ref<echo::Texture> mapTexture;
    float worldSize = 512.0f;
};

}
