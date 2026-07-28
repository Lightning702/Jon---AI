#include "Collection.h"
#include "../core/Log.h"
#include "../core/Time.h"
#include "../core/FileSystem.h"
#include "../core/ImageWriter.h"

using namespace em;

namespace felworks {

namespace {

const Vec4 kInk(0.93f, 0.94f, 0.95f, 1.0f);
const Vec4 kFaint(0.55f, 0.57f, 0.60f, 1.0f);

Vec4 mixCol(const Vec3& a, float alpha) { return Vec4(a.x, a.y, a.z, alpha); }

}

bool Collection::init(Window* w, int forcedPreset, bool windowed) {
    window = w;
    forcedPresetValue = forcedPreset;
    rng.setSeed(0xFE10125ULL);

    QualitySettings quality;
    int preset = forcedPreset >= 0 ? forcedPreset : QualitySettings::detectPreset();
    quality.applyPreset(preset);
    if (!renderer.init(window->width(), window->height(), quality)) return false;
    if (!ui.init()) return false;
    audio.init();
    audio.setMasterVolume(0.85f);

    cards[0].title = "ECHO";
    cards[0].author = "BY FELWORKS";
    cards[0].genre = "PSYCHOLOGICAL HORROR";
    cards[0].tagline = "Ein Krankenhaus, das sich erinnert.";
    cards[0].accent = Vec3(0.62f, 0.86f, 0.80f);
    cards[0].deep = Vec3(0.020f, 0.032f, 0.038f);

    cards[1].title = "AETHERIA";
    cards[1].author = "BY FELWORKS";
    cards[1].genre = "FANTASY OPEN WORLD RPG";
    cards[1].tagline = "Eine Welt, die auf dich gewartet hat.";
    cards[1].accent = Vec3(0.98f, 0.80f, 0.42f);
    cards[1].deep = Vec3(0.045f, 0.038f, 0.022f);

    props.build();
    buildPreviewScene();
    captureCardShots();

    state = Shell::Boot;
    stateTime = 0.0f;
    fade = 1.0f;
    fadeTarget = 0.0f;
    return true;
}

void Collection::buildPreviewScene() {
    WorldConfig cfg;
    cfg.seed = 0x4D454E55ULL;
    echoPreview.generate(cfg, props);

    int best = -1;
    float bestLen = 0.0f;
    for (const auto& room : echoPreview.rooms()) {
        if (room.type != ROOM_CORRIDOR || room.floor != 1) continue;
        float len = std::max(room.rect.w, room.rect.d);
        if (len > bestLen) { bestLen = len; best = room.id; }
    }
    if (best >= 0) {
        const Room& room = echoPreview.rooms()[(size_t)best];
        bool alongX = room.rect.w > room.rect.d;
        Vec2 c = room.rect.center();
        if (alongX) {
            previewBase = Vec3(room.rect.x + 1.4f, room.floorY + 1.62f, c.y);
            previewDir = Vec3(1, 0, 0);
        } else {
            previewBase = Vec3(c.x, room.floorY + 1.62f, room.rect.z + 1.4f);
            previewDir = Vec3(0, 0, 1);
        }
        for (int lid : room.lights) {
            LightFixture& l = echoPreview.lights()[(size_t)lid];
            if (l.broken) continue;
            l.on = true;
            if (l.flickerAmount < 0.18f) l.flickerAmount = 0.22f;
        }
    }

    aetherPreview.generate(0xAE71EA1AULL);
    previewBuilt = true;
}

void Collection::shutdown() {
    for (int i = 0; i < 2; i++) {
        if (cardShot[i]) glDeleteTextures(1, &cardShot[i]);
        cardShot[i] = 0;
    }
    if (echoGame) { echoGame->shutdown(); echoGame.reset(); }
    if (aetheriaGame) { aetheriaGame->shutdown(); aetheriaGame.reset(); }
    aetherPreview.destroy();
    echoPreview.destroy();
    props.destroy();
    audio.shutdown();
    ui.shutdown();
    renderer.shutdown();
}

void Collection::updatePreviewCamera(float dt) {
    previewPhase += dt * 0.045f;

    if (blendToAetheria < 0.5f) {
        float drift = std::sin(previewPhase * TAU) * 0.5f + 0.5f;
        previewCam.position = previewBase + previewDir * (drift * 3.2f);
        previewCam.position.y = previewBase.y + std::sin(previewPhase * 3.0f) * 0.03f;
        Vec3 target = previewBase + previewDir * 26.0f;
        target.y = previewBase.y - 0.15f;
        Vec3 side = normalize(cross(previewDir, Vec3(0, 1, 0)));
        target += side * std::sin(previewPhase * 1.6f) * 1.2f;
        previewCam.forward = normalize(target - previewCam.position);
        previewCam.fovY = 1.02f;
        previewCam.nearPlane = 0.05f;
        previewCam.farPlane = 240.0f;
    } else {
        Vec3 anchor = aetherPreview.spawnPoint();
        float orbit = previewPhase * 0.55f;
        float radius = 26.0f + std::sin(previewPhase * 0.9f) * 6.0f;
        previewCam.position = anchor + Vec3(std::cos(orbit) * radius, 9.0f + std::sin(previewPhase * 1.3f) * 2.2f, std::sin(orbit) * radius);
        float ground = aetherPreview.groundHeight(previewCam.position.x, previewCam.position.z);
        previewCam.position.y = std::max(previewCam.position.y, ground + 4.0f);
        Vec3 target = anchor + Vec3(0, 3.0f, 0);
        previewCam.forward = normalize(target - previewCam.position);
        previewCam.fovY = 1.10f;
        previewCam.nearPlane = 0.08f;
        previewCam.farPlane = 900.0f;
    }
    previewCam.update(window->aspect());
}

void Collection::updateCardInput(float dt) {
    Input& in = window->input();

    Vec2 mouse = in.mousePos();
    float w = (float)window->width(), h = (float)window->height();
    float cardW = w * 0.30f;
    float cardH = h * 0.56f;
    float gap = w * 0.045f;
    float top = h * 0.24f;
    float leftX = w * 0.5f - cardW - gap * 0.5f;
    float rightX = w * 0.5f + gap * 0.5f;

    int hovered = -1;
    if (mouse.y >= top && mouse.y <= top + cardH) {
        if (mouse.x >= leftX && mouse.x <= leftX + cardW) hovered = 0;
        else if (mouse.x >= rightX && mouse.x <= rightX + cardW) hovered = 1;
    }
    if (hovered >= 0 && hovered != selected) {
        selected = hovered;
        audio.play2D(SFX_CLICK, 0.22f, 1.3f);
    }

    if (in.keyPressed(KEY_LEFT) || in.keyPressed(KEY_A)) { selected = 0; audio.play2D(SFX_CLICK, 0.25f, 1.2f); }
    if (in.keyPressed(KEY_RIGHT) || in.keyPressed(KEY_D)) { selected = 1; audio.play2D(SFX_CLICK, 0.25f, 1.2f); }

    for (int i = 0; i < 2; i++) {
        float target = i == selected ? 1.0f : 0.0f;
        cards[i].hover = lerpf(cards[i].hover, target, 1.0f - std::exp(-7.0f * dt));
    }
    blendToAetheria = lerpf(blendToAetheria, selected == 1 ? 1.0f : 0.0f, 1.0f - std::exp(-3.4f * dt));

    bool activate = in.keyPressed(KEY_ENTER) || in.keyPressed(KEY_SPACE) ||
                    (in.mousePressed(MOUSE_LEFT) && hovered == selected && hovered >= 0);

    if (activate) {
        audio.play2D(SFX_ELEVATOR_DING, 0.4f, 1.0f);
        fadeTarget = 1.0f;
        state = selected == 0 ? Shell::LaunchEcho : Shell::LaunchAetheria;
        stateTime = 0.0f;
    }

    if (in.keyPressed(KEY_ESCAPE)) quitRequested = true;
}

void Collection::enterEcho() {
    if (!echoGame) {
        echoGame = std::make_unique<Game>();
        if (!echoGame->initShared(window, &renderer, &ui, &audio, forcedPresetValue)) {
            LOG_ERROR("ECHO init failed");
            echoGame.reset();
            state = Shell::Cards;
            return;
        }
    }
    echoGame->enterFromCollection();
    state = Shell::InEcho;
    stateTime = 0.0f;
    fadeTarget = 0.0f;
}

void Collection::enterAetheria() {
    if (!aetheriaGame) {
        aetheriaGame = std::make_unique<aeth::AetheriaGame>();
        aetheriaGame->init(window, &renderer, &ui, &audio);
    }
    aetheriaGame->open(0xAE71EA1AULL);
    state = Shell::InAetheria;
    stateTime = 0.0f;
    fadeTarget = 0.0f;
}

void Collection::returnToShell() {
    window->setCursorLocked(false);
    state = Shell::Cards;
    stateTime = 0.0f;
    fade = 1.0f;
    fadeTarget = 0.0f;
    if (!audio.isPlaying(music)) {
        PlayParams mp;
        mp.spatial = false;
        mp.looping = true;
        mp.volume = 0.48f;
        mp.fadeIn = 2.5f;
        mp.reverbSend = 0.28f;
        music = audio.play(SFX_MUSIC_LOBBY, mp);
    }
}

void Collection::update(float dt) {
    stateTime += dt;
    globalTime += dt;
    fade = moveTowards(fade, fadeTarget, dt * 1.8f);

    Input& shellInput = window->input();
    if (shellInput.keyPressed(KEY_F11)) {
        if (shellInput.key(KEY_SHIFT)) window->moveToNextMonitor();
        else window->setFullscreen(!window->fullscreen());
        displayHintTimer = 2.6f;
    }
    if (displayHintTimer > 0.0f) displayHintTimer -= dt;

    switch (state) {
    case Shell::Boot:
        if (stateTime > 2.6f || window->input().anyKeyPressed()) {
            returnToShell();
        }
        break;

    case Shell::Cards:
        updateCardInput(dt);
        updatePreviewCamera(dt);
        if (!audio.isPlaying(music)) {
            PlayParams mp;
            mp.spatial = false;
            mp.looping = true;
            mp.volume = 0.48f;
            mp.fadeIn = 2.0f;
            music = audio.play(SFX_MUSIC_LOBBY, mp);
        }
        break;

    case Shell::LaunchEcho:
        updatePreviewCamera(dt);
        if (stateTime > 0.9f) {
            if (audio.isPlaying(music)) audio.stop(music, 0.8f);
            enterEcho();
        }
        break;

    case Shell::LaunchAetheria:
        updatePreviewCamera(dt);
        if (stateTime > 0.9f) {
            if (audio.isPlaying(music)) audio.stop(music, 0.8f);
            enterAetheria();
        }
        break;

    case Shell::InEcho:
        if (echoGame) {
            echoGame->tick(dt);
            if (echoGame->wantsCollection()) {
                echoGame->clearCollectionRequest();
                returnToShell();
            }
        }
        break;

    case Shell::InAetheria:
        if (aetheriaGame) {
            aetheriaGame->update(dt, globalTime);
            if (aetheriaGame->wantsExit()) {
                aetheriaGame->clearExit();
                aetheriaGame->stop();
                returnToShell();
            }
        }
        break;
    }
}

void Collection::drawParticles(float dt) {
    float w = (float)window->width(), h = (float)window->height();
    float intensity = blendToAetheria;

    if (intensity > 0.05f && particles.size() < 90) {
        Particle p;
        p.pos = Vec2(rng.range(-0.1f, 1.1f) * w, rng.range(-0.1f, 1.0f) * h);
        p.vel = Vec2(rng.range(-38.0f, -8.0f), rng.range(6.0f, 26.0f));
        p.size = rng.range(2.0f, 6.5f) * (h / 900.0f);
        p.life = rng.range(6.0f, 16.0f);
        p.spin = rng.range(-2.0f, 2.0f);
        particles.push_back(p);
    }

    for (auto it = particles.begin(); it != particles.end();) {
        it->life -= dt;
        it->pos += it->vel * dt;
        it->pos.x += std::sin(globalTime * 1.4f + it->spin * 3.0f) * 14.0f * dt;
        if (it->life <= 0.0f || it->pos.y > h + 20.0f || it->pos.x < -30.0f) {
            it = particles.erase(it);
        } else {
            float a = clampf(it->life / 2.0f, 0.0f, 1.0f) * intensity * 0.55f;
            Vec4 col = mixCol(cards[1].accent, a);
            ui.diamond(it->pos.x, it->pos.y, it->size, col);
            ++it;
        }
    }
}

void Collection::drawBoot() {
    float w = (float)window->width(), h = (float)window->height();
    float t = stateTime;
    float a = smoothstepf(0.2f, 1.0f, t) * (1.0f - smoothstepf(2.1f, 2.6f, t));

    ui.text("FELWORKS", w * 0.5f, h * 0.44f, h * 0.075f, Vec4(kInk.x, kInk.y, kInk.z, a), ALIGN_CENTER, h * 0.030f);
    ui.rect(w * 0.5f - h * 0.14f, h * 0.535f, h * 0.28f * clampf(t / 1.6f, 0.0f, 1.0f), 1.6f,
            Vec4(kFaint.x, kFaint.y, kFaint.z, a * 0.6f));
    ui.text("GAME COLLECTION", w * 0.5f, h * 0.565f, h * 0.020f, Vec4(kFaint.x, kFaint.y, kFaint.z, a * 0.8f), ALIGN_CENTER, h * 0.010f);
}

void Collection::drawCards() {
    float w = (float)window->width(), h = (float)window->height();

    Vec3 tint = lerp(cards[0].deep, cards[1].deep, blendToAetheria);
    ui.gradientRect(0, 0, w, h * 0.45f, Vec4(tint.x, tint.y, tint.z, 0.90f), Vec4(tint.x, tint.y, tint.z, 0.42f));
    ui.gradientRect(0, h * 0.45f, w, h * 0.55f, Vec4(tint.x, tint.y, tint.z, 0.42f), Vec4(tint.x, tint.y, tint.z, 0.94f));

    Vec3 accent = lerp(cards[0].accent, cards[1].accent, blendToAetheria);

    ui.text("FELWORKS", w * 0.5f, h * 0.085f, h * 0.030f, Vec4(kInk.x, kInk.y, kInk.z, 0.92f), ALIGN_CENTER, h * 0.016f);
    ui.rect(w * 0.5f - h * 0.085f, h * 0.128f, h * 0.17f, 1.4f, mixCol(accent, 0.45f));
    ui.text("GAME COLLECTION", w * 0.5f, h * 0.148f, h * 0.016f, Vec4(kFaint.x, kFaint.y, kFaint.z, 0.62f), ALIGN_CENTER, h * 0.009f);

    float cardW = w * 0.30f;
    float cardH = h * 0.56f;
    float gap = w * 0.045f;
    float top = h * 0.24f;

    for (int i = 0; i < 2; i++) {
        const CardVisual& c = cards[i];
        float lift = c.hover * h * 0.022f;
        float x = i == 0 ? (w * 0.5f - cardW - gap * 0.5f) : (w * 0.5f + gap * 0.5f);
        float y = top - lift;
        float ch = cardH + lift * 1.6f;

        float glow = 0.10f + c.hover * 0.30f;
        ui.rect(x - h * 0.006f, y - h * 0.006f, cardW + h * 0.012f, ch + h * 0.012f, mixCol(c.accent, glow * 0.28f));
        ui.gradientRect(x, y, cardW, ch,
                        Vec4(c.deep.x + 0.02f, c.deep.y + 0.02f, c.deep.z + 0.025f, 0.55f + c.hover * 0.22f),
                        Vec4(0.008f, 0.010f, 0.013f, 0.88f + c.hover * 0.08f));

        ui.rect(x, y, cardW, h * 0.004f + c.hover * h * 0.003f, mixCol(c.accent, 0.55f + c.hover * 0.45f));
        ui.rect(x, y + ch - h * 0.002f, cardW, h * 0.002f, mixCol(c.accent, 0.25f));

        float shotInset = cardW * 0.055f;
        float shotW = cardW - shotInset * 2.0f;
        float shotH = shotW / 1.90f;
        float shotY = y + ch * 0.042f;
        if (cardShot[i]) {
            float bright = 0.62f + c.hover * 0.38f;
            float crop = (1.0f - 1.55f / 1.90f) * 0.5f;
            ui.rect(x + shotInset - 2.0f, shotY - 2.0f, shotW + 4.0f, shotH + 4.0f, mixCol(c.accent, 0.10f + c.hover * 0.22f));
            ui.imageUV(x + shotInset, shotY, shotW, shotH, cardShot[i], Vec4(bright, bright, bright, 1.0f),
                       0.0f, 1.0f - crop, 1.0f, crop);
            ui.gradientRect(x + shotInset, shotY + shotH * 0.60f, shotW, shotH * 0.40f,
                            Vec4(0.008f, 0.010f, 0.013f, 0.0f), Vec4(0.008f, 0.010f, 0.013f, 0.80f));
        }

        float textTop = shotY + shotH;
        float titleSize = h * 0.046f + c.hover * h * 0.005f;
        ui.textShadow(c.title, x + cardW * 0.5f, textTop + ch * 0.045f, titleSize,
                      Vec4(kInk.x, kInk.y, kInk.z, 0.72f + c.hover * 0.28f), ALIGN_CENTER, titleSize * 0.13f);

        ui.text(c.author, x + cardW * 0.5f, textTop + ch * 0.128f, h * 0.016f,
                mixCol(c.accent, 0.55f + c.hover * 0.40f), ALIGN_CENTER, h * 0.008f);

        ui.rect(x + cardW * 0.28f, textTop + ch * 0.168f, cardW * 0.44f, 1.2f, mixCol(c.accent, 0.22f + c.hover * 0.3f));

        ui.text(c.genre, x + cardW * 0.5f, textTop + ch * 0.196f, h * 0.015f,
                Vec4(kFaint.x, kFaint.y, kFaint.z, 0.55f + c.hover * 0.35f), ALIGN_CENTER, h * 0.006f);

        if (c.hover > 0.15f) {
            auto lines = ui.font().wrap(c.tagline, h * 0.018f, cardW * 0.84f);
            float ly = textTop + ch * 0.250f;
            for (const auto& line : lines) {
                ui.text(line, x + cardW * 0.5f, ly, h * 0.018f,
                        Vec4(kInk.x, kInk.y, kInk.z, (c.hover - 0.15f) * 0.85f), ALIGN_CENTER);
                ly += h * 0.026f;
            }

            float pulse = 0.5f + 0.5f * std::sin(globalTime * 3.0f);
            float bw = cardW * 0.52f;
            float bx = x + cardW * 0.5f - bw * 0.5f;
            float bh = h * 0.046f;
            float by = y + ch - bh - h * 0.030f;
            ui.rect(bx, by, bw, bh, mixCol(c.accent, (0.10f + pulse * 0.08f) * c.hover));
            ui.rect(bx, by, bw, 1.4f, mixCol(c.accent, 0.6f * c.hover));
            ui.rect(bx, by + bh - 1.4f, bw, 1.4f, mixCol(c.accent, 0.6f * c.hover));
            ui.text("SPIELEN", x + cardW * 0.5f, by + bh * 0.5f - h * 0.010f, h * 0.020f,
                    Vec4(kInk.x, kInk.y, kInk.z, c.hover), ALIGN_CENTER, h * 0.008f);
        }
    }

    ui.text("MAUS ODER PFEILTASTEN   ENTER STARTEN   F11 VOLLBILD   ESC BEENDEN", w * 0.5f, h - h * 0.055f, h * 0.016f,
            Vec4(kFaint.x, kFaint.y, kFaint.z, 0.42f), ALIGN_CENTER, h * 0.005f);
    ui.text(ECHO_VERSION, w - h * 0.030f, h - h * 0.038f, h * 0.014f, Vec4(kFaint.x, kFaint.y, kFaint.z, 0.28f), ALIGN_RIGHT);
}

void Collection::renderPreviewScene(int index, float dt) {
    if (index == 0) {
        renderer.sky().enabled = false;
        AtmosphereParams& atmos = renderer.atmosphere();
        atmos.ambientTop = Vec3(0.190f, 0.212f, 0.248f);
        atmos.ambientBottom = Vec3(0.082f, 0.090f, 0.104f);
        atmos.fogDensity = 0.0105f;
        atmos.fogColor = Vec3(0.070f, 0.086f, 0.104f);
        atmos.decay = 0.5f;
        PostParams& post = renderer.post();
        post.exposure = 2.35f;
        post.saturation = 0.90f;
        post.vignette = 0.62f;
        post.grain = 0.038f;

        renderer.beginFrame(previewCam, globalTime, dt);
        echoPreview.update(dt, globalTime, previewCam.position);
        echoPreview.collectRender(renderer, previewCam, 40.0f);
        renderer.render();
    } else {
        aetherPreview.update(dt, globalTime, previewCam.position);
        aetherPreview.applySky(renderer);
        PostParams& post = renderer.post();
        post.exposure = 2.05f;
        post.saturation = 1.10f;
        post.vignette = 0.32f;
        post.grain = 0.010f;

        renderer.beginFrame(previewCam, globalTime, dt);
        aetherPreview.collectRender(renderer, previewCam, 170.0f);
        renderer.render();
    }
}

void Collection::captureCardShots() {
    int sw = window->width(), sh = window->height();
    if (sw < 64 || sh < 64) return;

    int capW = std::min(sw, 960);
    int capH = (int)(capW / 1.55f);
    if (capH > sh) {
        capH = sh;
        capW = std::min(sw, (int)(capH * 1.55f));
    }
    int ox = (sw - capW) / 2;
    int oy = (sh - capH) / 2;

    float savedBlend = blendToAetheria;
    float savedPhase = previewPhase;

    for (int i = 0; i < 2; i++) {
        blendToAetheria = i == 0 ? 0.0f : 1.0f;
        previewPhase = i == 0 ? 1.4f : 4.2f;
        updatePreviewCamera(0.0f);
        renderPreviewScene(i, 0.016f);

        if (cardShot[i]) glDeleteTextures(1, &cardShot[i]);
        glGenTextures(1, &cardShot[i]);
        glBindTexture(GL_TEXTURE_2D, cardShot[i]);
        glReadBuffer(GL_BACK);
        glCopyTexImage2D(GL_TEXTURE_2D, 0, GL_RGB8, ox, oy, capW, capH, 0);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
        glBindTexture(GL_TEXTURE_2D, 0);
    }

    blendToAetheria = savedBlend;
    previewPhase = savedPhase;
    shotsCaptured = true;
    LOG_INFO("Card previews captured %dx%d", capW, capH);
}

void Collection::render(float dt) {
    bool shellVisible = state == Shell::Boot || state == Shell::Cards ||
                        state == Shell::LaunchEcho || state == Shell::LaunchAetheria;

    if (state == Shell::InEcho && echoGame) {
        echoGame->renderFrame();
    } else if (state == Shell::InAetheria && aetheriaGame) {
        aetheriaGame->render(globalTime);
    } else if (shellVisible && previewBuilt) {
        renderPreviewScene(blendToAetheria < 0.5f ? 0 : 1, dt);
    } else {
        glBindFramebuffer(GL_FRAMEBUFFER, 0);
        glViewport(0, 0, window->width(), window->height());
        glClearColor(0.008f, 0.010f, 0.013f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
    }

    ui.begin(window->width(), window->height(), globalTime);

    if (state == Shell::Boot) drawBoot();
    else if (state == Shell::Cards || state == Shell::LaunchEcho || state == Shell::LaunchAetheria) {
        drawCards();
        drawParticles(dt);
    } else if (state == Shell::InEcho && echoGame) {
        echoGame->drawOverlay();
    } else if (state == Shell::InAetheria && aetheriaGame) {
        aetheriaGame->drawHud();
    }

    if (displayHintTimer > 0.0f) {
        float w = (float)window->width(), h = (float)window->height();
        float a = clampf(displayHintTimer / 0.7f, 0.0f, 1.0f);
        char buf[128];
        std::snprintf(buf, sizeof(buf), "%s   %dx%d", window->fullscreen() ? "VOLLBILD" : "FENSTER",
                      window->width(), window->height());
        ui.rect(w * 0.5f - h * 0.20f, h * 0.045f, h * 0.40f, h * 0.075f, Vec4(0.03f, 0.03f, 0.04f, 0.60f * a));
        ui.textShadow(buf, w * 0.5f, h * 0.062f, h * 0.026f, Vec4(kInk.x, kInk.y, kInk.z, a), ALIGN_CENTER, h * 0.008f);
        if (window->monitorCount() > 1) {
            ui.text("SHIFT+F11  NAECHSTER BILDSCHIRM", w * 0.5f, h * 0.096f, h * 0.016f,
                    Vec4(kFaint.x, kFaint.y, kFaint.z, a * 0.9f), ALIGN_CENTER, h * 0.005f);
        }
    }

    if (fade > 0.001f) ui.rect(0, 0, (float)window->width(), (float)window->height(), Vec4(0, 0, 0, fade));
    ui.end();
}

void Collection::run() {
    FrameTimer timer;
    int frameCount = 0;

    if (seedTest > 0) {
        for (int i = 0; i < seedTest; i++) {
            WorldConfig cfg;
            cfg.seed = hashCombine(0xEC4055EED5ULL, (u64)(i + 1) * 2654435761ULL);
            echoPreview.generate(cfg, props);
            Campaign probe;
            probe.init(&echoPreview, cfg.seed);
        }
        return;
    }

    if (testCard >= 0) {
        returnToShell();
        selected = clampi(testCard, 0, 1);
        cards[selected].hover = 1.0f;
        blendToAetheria = selected == 1 ? 1.0f : 0.0f;
        fade = 0.0f;
        fadeTarget = 0.0f;
    }

    if (testPlay >= 0) {
        fade = 0.0f;
        fadeTarget = 0.0f;
        if (testPlay == 1) {
            enterAetheria();
            if (aetheriaGame && (testAutoRun || testMapOpen)) {
                aetheriaGame->beginRun();
                if (testMapOpen) aetheriaGame->setMapOpen(true);
            }
        } else {
            enterEcho();
            if (echoGame && testAutoRun) echoGame->beginTestRun(20260727ULL);
        }
    }

    while (!window->shouldClose() && !quitRequested) {
        window->pollEvents();
        timer.tick();
        if (window->resized()) renderer.resize(window->width(), window->height());
        if (window->minimized()) continue;

        float dt = std::min(timer.dt, 0.05f);
        update(dt);
        if (window->resized()) renderer.resize(window->width(), window->height());
        if (window->minimized()) continue;
        render(dt);

        frameCount++;
        if (!shotPath.empty() && testFrames > 0 && frameCount == testFrames) {
            int sw = window->width(), sh = window->height();
            std::vector<unsigned char> pixels((size_t)sw * sh * 3);
            glPixelStorei(GL_PACK_ALIGNMENT, 1);
            glReadBuffer(GL_BACK);
            glReadPixels(0, 0, sw, sh, GL_RGB, GL_UNSIGNED_BYTE, pixels.data());
            writePNG(shotPath, sw, sh, 3, pixels.data(), true);
            LOG_INFO("Screenshot: %s (state %d)", shotPath.c_str(), (int)state);
        }

        window->swapBuffers();
        if (testFrames > 0 && frameCount >= testFrames) break;
    }
}

}
