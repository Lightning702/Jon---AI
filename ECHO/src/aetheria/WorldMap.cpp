#include "WorldMap.h"

using namespace em;
using namespace echo;

namespace aeth {

namespace {

const int kMapRes = 384;

const Vec3 kBiomeInk[BIOME_COUNT] = {
    Vec3(0.55f, 0.66f, 0.36f),
    Vec3(0.26f, 0.44f, 0.26f),
    Vec3(0.72f, 0.57f, 0.24f),
    Vec3(0.52f, 0.49f, 0.42f),
    Vec3(0.90f, 0.92f, 0.95f),
    Vec3(0.36f, 0.44f, 0.32f),
    Vec3(0.80f, 0.74f, 0.52f)
};

const Vec4 kParchment(0.16f, 0.14f, 0.11f, 0.94f);
const Vec4 kFrame(0.72f, 0.58f, 0.32f, 0.85f);
const Vec4 kInk(0.95f, 0.93f, 0.86f, 1.0f);
const Vec4 kGold(0.99f, 0.83f, 0.46f, 1.0f);

}

void WorldMap::build(const Terrain& terrain) {
    worldSize = terrain.worldSize();
    float water = terrain.waterLevel();
    float step = worldSize / (float)kMapRes;

    Image img;
    img.allocate(kMapRes, kMapRes, 3);

    Vec3 lightDir = normalize(Vec3(-0.62f, 0.72f, -0.32f));

    for (int y = 0; y < kMapRes; y++) {
        for (int x = 0; x < kMapRes; x++) {
            float wx = (x + 0.5f) * step;
            float wz = (y + 0.5f) * step;
            float h = terrain.heightAt(wx, wz);
            int biome = terrain.biomeAt(wx, wz);

            Vec3 c = kBiomeInk[biome < 0 || biome >= BIOME_COUNT ? 0 : biome];

            if (h < water) {
                float depth = clampf((water - h) / 12.0f, 0.0f, 1.0f);
                c = lerp(Vec3(0.34f, 0.55f, 0.62f), Vec3(0.10f, 0.20f, 0.34f), depth);
            } else {
                Vec3 n = terrain.normalAt(wx, wz);
                float lambert = clampf(dot(n, lightDir), 0.0f, 1.0f);
                float shade = 0.62f + lambert * 0.62f;
                c = c * shade;

                float band = h / std::max(terrain.config().maxHeight, 1.0f);
                float contour = std::fabs(fractf(band * 14.0f) - 0.5f);
                if (contour > 0.455f) c = c * 0.82f;

                if (h < water + 0.9f) c = lerp(c, Vec3(0.80f, 0.74f, 0.52f), 0.55f);
            }

            float grain = 0.94f + hash21(Vec2((float)x * 0.37f, (float)y * 0.53f)) * 0.12f;
            c = c * grain;
            c = lerp(c, Vec3(0.58f, 0.48f, 0.32f), 0.10f);
            img.set(x, y, c);
        }
    }

    mapTexture = makeTexture2D(img, false, false, GL_CLAMP_TO_EDGE);
}

void WorldMap::destroy() {
    mapTexture.reset();
}

void WorldMap::drawMarker(UIRenderer& ui, const MapMarker& m, float sx, float sy, float scale, bool labels) const {
    switch (m.shape) {
    case MARK_VILLAGE:
        ui.rect(sx - scale, sy - scale, scale * 2.0f, scale * 2.0f, Vec4(0.05f, 0.04f, 0.03f, 0.75f));
        ui.rect(sx - scale * 0.68f, sy - scale * 0.68f, scale * 1.36f, scale * 1.36f, m.color);
        break;
    case MARK_LANDMARK:
        ui.diamond(sx, sy, scale * 1.25f, Vec4(0.05f, 0.04f, 0.03f, 0.75f));
        ui.diamond(sx, sy, scale * 0.85f, m.color);
        break;
    case MARK_QUEST:
        ui.circle(sx, sy, scale * 1.30f, 14, Vec4(0.05f, 0.04f, 0.03f, 0.70f));
        ui.circle(sx, sy, scale * 0.90f, 14, m.color);
        break;
    default:
        ui.circle(sx, sy, scale * 0.8f, 12, m.color);
        break;
    }
    if (labels && !m.label.empty()) {
        ui.textShadow(m.label, sx, sy + scale * 2.6f, scale * 2.0f, Vec4(m.color.x, m.color.y, m.color.z, 0.92f),
                      ALIGN_CENTER, scale * 0.3f);
    }
}

void WorldMap::drawMinimap(UIRenderer& ui, float cx, float cy, float size,
                           const Vec2& player, float yaw, float rangeMeters,
                           const std::vector<MapMarker>& markers) const {
    float half = size * 0.5f;
    float x0 = cx - half, y0 = cy - half;

    ui.rect(x0 - 3.0f, y0 - 3.0f, size + 6.0f, size + 6.0f, Vec4(0.06f, 0.05f, 0.04f, 0.72f));

    if (ready()) {
        float u = player.x / worldSize;
        float v = player.y / worldSize;
        float r = (rangeMeters * 0.5f) / worldSize;
        ui.imageUV(x0, y0, size, size, mapTexture->id(), Vec4(1, 1, 1, 0.95f), u - r, v - r, u + r, v + r);
    }

    float pxPerMeter = size / rangeMeters;
    for (const MapMarker& m : markers) {
        if (!m.known || !m.onMinimap) continue;
        float sx = cx + (m.world.x - player.x) * pxPerMeter;
        float sy = cy + (m.world.y - player.y) * pxPerMeter;
        float pad = size * 0.045f;
        if (sx < x0 + pad || sx > x0 + size - pad || sy < y0 + pad || sy > y0 + size - pad) {
            Vec2 dir(sx - cx, sy - cy);
            float len = length(dir);
            if (len < 0.001f) continue;
            dir /= len;
            float edge = half - pad;
            float k = std::min(std::fabs(edge / (std::fabs(dir.x) < 1e-4f ? 1e-4f : dir.x)),
                               std::fabs(edge / (std::fabs(dir.y) < 1e-4f ? 1e-4f : dir.y)));
            if (m.shape != MARK_QUEST) continue;
            sx = cx + dir.x * k;
            sy = cy + dir.y * k;
            ui.diamond(sx, sy, size * 0.028f, m.color);
            continue;
        }
        drawMarker(ui, m, sx, sy, size * 0.026f, false);
    }

    ui.arrow(cx, cy, size * 0.048f, yaw, kGold);

    ui.rectOutline(x0, y0, size, size, 1.6f, kFrame);
    ui.text("N", cx, y0 - size * 0.075f, size * 0.10f, Vec4(kGold.x, kGold.y, kGold.z, 0.8f), ALIGN_CENTER);
    ui.text("TAB", cx, y0 + size + size * 0.045f, size * 0.085f, Vec4(kInk.x, kInk.y, kInk.z, 0.45f), ALIGN_CENTER);
}

void WorldMap::drawFull(UIRenderer& ui, float screenW, float screenH,
                        const Vec2& player, float yaw,
                        const std::vector<MapMarker>& markers,
                        const std::vector<std::string>& lines,
                        const std::string& title) const {
    ui.rect(0, 0, screenW, screenH, Vec4(0.02f, 0.02f, 0.03f, 0.86f));

    float size = std::min(screenW * 0.60f, screenH * 0.78f);
    float x0 = screenW * 0.32f - size * 0.5f;
    float y0 = screenH * 0.52f - size * 0.5f;
    if (x0 < screenH * 0.04f) x0 = screenH * 0.04f;

    ui.rect(x0 - 10.0f, y0 - 10.0f, size + 20.0f, size + 20.0f, kParchment);
    if (ready()) ui.image(x0, y0, size, size, mapTexture->id(), Vec4(1, 1, 1, 1));
    ui.rectOutline(x0 - 10.0f, y0 - 10.0f, size + 20.0f, size + 20.0f, 2.0f, kFrame);

    float pxPerMeter = size / worldSize;
    for (const MapMarker& m : markers) {
        if (!m.known) continue;
        float sx = x0 + m.world.x * pxPerMeter;
        float sy = y0 + m.world.y * pxPerMeter;
        drawMarker(ui, m, sx, sy, size * 0.011f, true);
    }

    float px = x0 + player.x * pxPerMeter;
    float py = y0 + player.y * pxPerMeter;
    ui.circle(px, py, size * 0.019f, 16, Vec4(0.05f, 0.04f, 0.03f, 0.8f));
    ui.arrow(px, py, size * 0.016f, yaw, kGold);

    ui.textShadow(title, x0 + size * 0.5f, y0 - screenH * 0.068f, screenH * 0.034f, kGold, ALIGN_CENTER, screenH * 0.006f);
    ui.text("N", x0 + size * 0.5f, y0 + screenH * 0.012f, screenH * 0.020f,
            Vec4(kInk.x, kInk.y, kInk.z, 0.55f), ALIGN_CENTER, screenH * 0.006f);

    float panelX = x0 + size + screenH * 0.06f;
    float panelW = screenW - panelX - screenH * 0.05f;
    if (panelW > screenH * 0.20f) {
        ui.rect(panelX - screenH * 0.02f, y0 - 10.0f, panelW + screenH * 0.02f, size + 20.0f,
                Vec4(0.05f, 0.05f, 0.06f, 0.70f));
        ui.rectOutline(panelX - screenH * 0.02f, y0 - 10.0f, panelW + screenH * 0.02f, size + 20.0f, 1.5f,
                       Vec4(kFrame.x, kFrame.y, kFrame.z, 0.45f));
        float ly = y0 + screenH * 0.03f;
        for (const std::string& line : lines) {
            if (ly > y0 + size - screenH * 0.01f) break;
            if (line.empty()) { ly += screenH * 0.014f; continue; }
            bool heading = line[0] == '#';
            float sizeText = heading ? screenH * 0.024f : screenH * 0.019f;
            Vec4 col = heading ? kGold : Vec4(kInk.x, kInk.y, kInk.z, 0.82f);
            std::string text = heading ? line.substr(1) : line;
            float limit = panelW - screenH * 0.012f;
            if (ui.font().measure(text, sizeText, 0.0f) > limit) {
                while (text.size() > 3 && ui.font().measure(text + "...", sizeText, 0.0f) > limit) text.pop_back();
                text += "...";
            }
            ui.text(text, panelX, ly, sizeText, col, ALIGN_LEFT);
            ly += sizeText * 1.55f;
        }
    }

    ui.text("TAB  KARTE SCHLIESSEN", screenW * 0.5f, screenH - screenH * 0.045f, screenH * 0.018f,
            Vec4(kInk.x, kInk.y, kInk.z, 0.45f), ALIGN_CENTER, screenH * 0.005f);
}

}
