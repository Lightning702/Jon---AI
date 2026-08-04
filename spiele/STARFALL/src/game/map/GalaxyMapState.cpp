#include "GalaxyMapState.hpp"

#include "../../engine/math/Scalar.hpp"
#include "../../engine/ui/Localization.hpp"

#include <cstdio>

namespace sf {

void GalaxyMapState::initialize(const GalaxyProfile& galaxy, const SystemCoord& playerSystem) {
    profile = galaxy;
    playerLocation = playerSystem;
    selectedSystem = playerSystem;
    selectionValid = true;
    focus = DVec3(static_cast<f64>(playerSystem.x), static_cast<f64>(playerSystem.y),
                  static_cast<f64>(playerSystem.z));
    zoom = 900.0;
    for (bool& value : filters) value = false;
}

u32 GalaxyMapState::zoomStage() const {
    if (zoom > 240000.0) return 1;
    if (zoom > 26000.0) return 2;
    if (zoom > 2400.0) return 3;
    if (zoom > 220.0) return 4;
    if (zoom > 12.0) return 5;
    return 6;
}

const char* GalaxyMapState::zoomStageName(u32 stage) {
    switch (stage) {
        case 1: return "GALAXIENHAUFEN";
        case 2: return "GALAXIE";
        case 3: return "SEKTOR";
        case 4: return "STERNENNACHBARSCHAFT";
        case 5: return "STERNSYSTEM";
        default: return "KOERPERDETAIL";
    }
}

const char* GalaxyMapState::filterName(MapFilter filter) {
    switch (filter) {
        case MapFilter::Habitable: return "BEWOHNBAR";
        case MapFilter::Resources: return "RESSOURCEN";
        case MapFilter::Unexplored: return "UNERFORSCHT";
        case MapFilter::Faction: return "FRAKTION";
        case MapFilter::TradePrice: return "HANDELSPREIS";
        case MapFilter::Missions: return "MISSIONSZIELE";
        case MapFilter::Friends: return "FREUNDE";
        case MapFilter::Danger: return "GEFAHRENSTUFE";
        case MapFilter::OwnBases: return "EIGENE BASEN";
        default: return "";
    }
}

void GalaxyMapState::toggleFilter(MapFilter filter) {
    bool& value = filters[static_cast<usize>(filter)];
    value = !value;
}

Vec2 GalaxyMapState::project(const DVec3& positionLightYears, u32 surfaceWidth, u32 surfaceHeight) const {
    const DVec3 relative = positionLightYears - focus;
    const f64 cosineYaw = std::cos(yaw);
    const f64 sineYaw = std::sin(yaw);
    const f64 cosinePitch = std::cos(pitch);
    const f64 sinePitch = std::sin(pitch);

    const f64 rotatedX = relative.x * cosineYaw - relative.z * sineYaw;
    const f64 rotatedZ = relative.x * sineYaw + relative.z * cosineYaw;
    const f64 rotatedY = relative.y * cosinePitch - rotatedZ * sinePitch;
    const f64 depth = relative.y * sinePitch + rotatedZ * cosinePitch;

    const f64 scale = static_cast<f64>(minValue(surfaceWidth, surfaceHeight)) * 0.42 / maxValue(zoom, 1.0e-3);
    const f64 perspective = 1.0 / (1.0 + maxValue(depth, -zoom * 0.9) / maxValue(zoom * 2.4, 1.0));

    return Vec2(static_cast<f32>(static_cast<f64>(surfaceWidth) * 0.5 + rotatedX * scale * perspective),
                static_cast<f32>(static_cast<f64>(surfaceHeight) * 0.5 - rotatedY * scale * perspective));
}

bool GalaxyMapState::markerPassesFilters(const MapMarker& marker) const {
    bool anyActive = false;
    for (bool value : filters) anyActive = anyActive || value;
    if (!anyActive) return true;

    if (filters[static_cast<usize>(MapFilter::Habitable)] && marker.habitable) return true;
    if (filters[static_cast<usize>(MapFilter::Unexplored)] && !marker.visited) return true;
    if (filters[static_cast<usize>(MapFilter::TradePrice)] && marker.hasStation) return true;
    if (filters[static_cast<usize>(MapFilter::Friends)] && marker.friendPresent) return true;
    if (filters[static_cast<usize>(MapFilter::Danger)] && marker.dangerRating > 0.4f) return true;
    if (filters[static_cast<usize>(MapFilter::Missions)] && marker.hasStation) return true;
    if (filters[static_cast<usize>(MapFilter::Resources)] && marker.magnitude > 1.1f) return true;
    return false;
}

void GalaxyMapState::update(f64 stepSeconds, const Input& input, u32 surfaceWidth, u32 surfaceHeight) {
    pulse += stepSeconds;
    viewportWidth = surfaceWidth;
    viewportHeight = surfaceHeight;

    const f32 wheel = input.wheelDelta();
    if (std::fabs(wheel) > 0.0f) {
        zoom *= std::pow(0.82, static_cast<f64>(wheel));
        zoom = clampValue(zoom, 0.6, 900000.0);
    }

    if (input.mouseDown(MouseButton::Left)) {
        const Vec2 delta = input.mouseDelta();
        yaw += static_cast<f64>(delta.x) * 0.005;
        pitch = clampValue(pitch + static_cast<f64>(delta.y) * 0.005, -1.45, 1.45);
    }
    if (input.mouseDown(MouseButton::Middle)) {
        const Vec2 delta = input.mouseDelta();
        const f64 scale = zoom * 0.0016;
        focus.x -= static_cast<f64>(delta.x) * scale;
        focus.z += static_cast<f64>(delta.y) * scale;
    }

    if (input.keyPressed(Key::Space)) {
        focus = DVec3(static_cast<f64>(playerLocation.x), static_cast<f64>(playerLocation.y),
                      static_cast<f64>(playerLocation.z));
        selectedSystem = playerLocation;
        selectionValid = true;
    }
    if (input.keyPressed(Key::R)) routeRequested = true;
    if (input.keyPressed(Key::F)) toggleFilter(MapFilter::Habitable);

    if (input.mousePressed(MouseButton::Left) || input.mousePressed(MouseButton::Right)) {
        const Vec2 cursor = input.mousePosition();
        f32 bestDistance = 26.0f;
        for (const MapMarker& marker : markers) {
            if (!markerPassesFilters(marker)) continue;
            const DVec3 position(static_cast<f64>(marker.coordinate.x), static_cast<f64>(marker.coordinate.y),
                                 static_cast<f64>(marker.coordinate.z));
            const Vec2 screen = project(position, surfaceWidth, surfaceHeight);
            const f32 distance = length(screen - cursor);
            if (distance >= bestDistance) continue;
            bestDistance = distance;
            selectedSystem = marker.coordinate;
            selectionValid = true;
        }
        if (input.mousePressed(MouseButton::Right) && selectionValid) jumpRequested = true;
    }
}

bool GalaxyMapState::consumeJumpRequest() {
    const bool value = jumpRequested;
    jumpRequested = false;
    return value;
}

bool GalaxyMapState::consumeRouteRequest() {
    const bool value = routeRequested;
    routeRequested = false;
    return value;
}

void GalaxyMapState::draw(UIRenderer& ui, const HyperRoute& route, const std::string& denialText) const {
    const UIStyle& style = ui.style();
    const f32 width = static_cast<f32>(ui.surfaceWidth());
    const f32 height = static_cast<f32>(ui.surfaceHeight());
    const f32 glow = 0.5f + 0.5f * std::sin(static_cast<f32>(pulse) * 2.0f);

    ui.drawRect(0.0f, 0.0f, width, height, Vec4(0.008f, 0.016f, 0.024f, 0.86f));

    for (const MapMarker& marker : markers) {
        if (!markerPassesFilters(marker)) continue;
        const DVec3 position(static_cast<f64>(marker.coordinate.x), static_cast<f64>(marker.coordinate.y),
                             static_cast<f64>(marker.coordinate.z));
        const Vec2 screen = project(position, ui.surfaceWidth(), ui.surfaceHeight());
        if (screen.x < -40.0f || screen.y < -40.0f || screen.x > width + 40.0f || screen.y > height + 40.0f) continue;

        const f32 size = clampValue(marker.magnitude * 3.4f, 1.6f, 12.0f);
        Vec4 color(marker.color.x, marker.color.y, marker.color.z, marker.visited ? 1.0f : 0.55f);
        if (marker.isVoidHeart) {
            ui.drawCircleOutline(screen.x, screen.y, 22.0f + glow * 6.0f, 2.0f, 64, style.voidGold);
            ui.drawRect(screen.x - 5.0f, screen.y - 5.0f, 10.0f, 10.0f, Vec4(0.0f, 0.0f, 0.0f, 1.0f));
            ui.drawCircleOutline(screen.x, screen.y, 9.0f, 2.0f, 32, style.voidGold);
        } else {
            ui.drawRect(screen.x - size * 0.5f, screen.y - size * 0.5f, size, size, color);
        }
        if (marker.friendPresent) {
            ui.drawCircleOutline(screen.x, screen.y, 12.0f, 1.4f, 24, style.accent);
        }
        if (marker.coordinate == selectedSystem) {
            ui.drawCircleOutline(screen.x, screen.y, 16.0f + glow * 3.0f, 1.8f, 48, style.accent);
            ui.drawText(marker.label, screen.x + 20.0f, screen.y - 6.0f, 1.4f, style.text);
        }
    }

    if (!route.legs.empty()) {
        DVec3 previous(static_cast<f64>(playerLocation.x), static_cast<f64>(playerLocation.y),
                       static_cast<f64>(playerLocation.z));
        for (const RouteLeg& leg : route.legs) {
            const DVec3 next(static_cast<f64>(leg.target.x), static_cast<f64>(leg.target.y),
                             static_cast<f64>(leg.target.z));
            const Vec2 from = project(previous, ui.surfaceWidth(), ui.surfaceHeight());
            const Vec2 to = project(next, ui.surfaceWidth(), ui.surfaceHeight());
            ui.drawLine(from.x, from.y, to.x, to.y, 1.6f, Vec4(style.accent.x, style.accent.y, style.accent.z, 0.7f));
            previous = next;
        }
    }

    const f32 headerHeight = 74.0f;
    ui.drawHologramPanel(24.0f, 24.0f, 430.0f, headerHeight, style, glow);
    ui.drawText(translate("map.title"), 40.0f, 40.0f, 2.0f, style.accent);
    char line[192];
    std::snprintf(line, sizeof(line), "%s  %s  ZOOM %u  %.1f Lj", profile.name.c_str(),
                  GalaxyGenerator::galaxyTypeName(profile.type), zoomStage(), zoom);
    ui.drawText(line, 40.0f, 66.0f, 1.4f, style.textDim);

    const f32 infoWidth = 400.0f;
    const f32 infoHeight = 214.0f;
    const f32 infoX = width - infoWidth - 24.0f;
    const f32 infoY = 24.0f;
    ui.drawHologramPanel(infoX, infoY, infoWidth, infoHeight, style, glow);

    if (selectionValid) {
        std::snprintf(line, sizeof(line), "ZIEL  %lld / %lld / %lld", static_cast<long long>(selectedSystem.x),
                      static_cast<long long>(selectedSystem.y), static_cast<long long>(selectedSystem.z));
        ui.drawText(line, infoX + 14.0f, infoY + 16.0f, 1.5f, style.text);

        const f64 distance = HyperdriveSystem::distanceLightYears(playerLocation, selectedSystem);
        std::snprintf(line, sizeof(line), "DISTANZ %.2f Lj", distance);
        ui.drawText(line, infoX + 14.0f, infoY + 40.0f, 1.4f, style.text);

        if (route.reachable && !route.legs.empty()) {
            std::snprintf(line, sizeof(line), "SPRUENGE %u  TREIBSTOFF %.1f", static_cast<u32>(route.legs.size()),
                          route.totalFuelCost);
            ui.drawText(line, infoX + 14.0f, infoY + 62.0f, 1.4f, style.text);
            std::snprintf(line, sizeof(line), "DAUER %.0f s  GEFAHR %.2f", route.estimatedSeconds, route.averageHazard);
            ui.drawText(line, infoX + 14.0f, infoY + 84.0f, 1.4f, style.textDim);
            ui.drawText(translate("map.jump"), infoX + 14.0f, infoY + 112.0f, 1.7f, style.accent);
            ui.drawText("RECHTSKLICK", infoX + 14.0f, infoY + 136.0f, 1.3f, style.textDim);
        } else if (!denialText.empty()) {
            ui.drawText(denialText, infoX + 14.0f, infoY + 62.0f, 1.3f, style.danger);
        }
    }

    ui.drawText("M KARTE  F FILTER  R ROUTE  LEERTASTE ZURUECK  LINKSZIEHEN ROTIEREN  MAUSRAD ZOOM", 24.0f,
                height - 34.0f, 1.3f, style.textDim);
}

}
