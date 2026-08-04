#pragma once

#include "../../engine/platform/Input.hpp"
#include "../../engine/ui/UIRenderer.hpp"
#include "../space/HyperdriveSystem.hpp"
#include "../universe/GalaxyGenerator.hpp"

#include <string>
#include <vector>

namespace sf {

enum class MapFilter : u32 {
    Habitable = 0, Resources, Unexplored, Faction, TradePrice, Missions, Friends, Danger, OwnBases, Count
};

struct MapMarker {
    SystemCoord coordinate;
    std::string label;
    Vec3 color = Vec3(1.0f, 1.0f, 1.0f);
    f32 magnitude = 1.0f;
    bool visited = false;
    bool habitable = false;
    bool hasStation = false;
    bool isVoidHeart = false;
    bool friendPresent = false;
    f32 dangerRating = 0.0f;
};

class GalaxyMapState {
public:
    void initialize(const GalaxyProfile& galaxy, const SystemCoord& playerSystem);
    void setMarkers(std::vector<MapMarker> value) { markers = std::move(value); }
    void update(f64 stepSeconds, const Input& input, u32 surfaceWidth, u32 surfaceHeight);
    void draw(UIRenderer& ui, const HyperRoute& route, const std::string& denialText) const;

    f64 zoomLevel() const { return zoom; }
    u32 zoomStage() const;
    const SystemCoord& selection() const { return selectedSystem; }
    bool hasSelection() const { return selectionValid; }
    bool consumeJumpRequest();
    bool consumeRouteRequest();
    bool filterActive(MapFilter filter) const { return filters[static_cast<usize>(filter)]; }
    void toggleFilter(MapFilter filter);
    const std::string& searchText() const { return search; }

    static const char* zoomStageName(u32 stage);
    static const char* filterName(MapFilter filter);

private:
    Vec2 project(const DVec3& positionLightYears, u32 surfaceWidth, u32 surfaceHeight) const;
    bool markerPassesFilters(const MapMarker& marker) const;

    GalaxyProfile profile;
    std::vector<MapMarker> markers;
    SystemCoord playerLocation;
    SystemCoord selectedSystem;
    DVec3 focus = DVec3::zero();
    f64 zoom = 900.0;
    f64 yaw = 0.6;
    f64 pitch = 0.42;
    f64 pulse = 0.0;
    u32 viewportWidth = 1600;
    u32 viewportHeight = 900;
    bool selectionValid = false;
    bool jumpRequested = false;
    bool routeRequested = false;
    bool filters[static_cast<usize>(MapFilter::Count)] = {};
    std::string search;
};

}
