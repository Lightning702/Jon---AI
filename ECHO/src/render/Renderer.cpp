#include "Renderer.h"
#include "../core/Log.h"
#include "../core/Random.h"
#include "../core/Time.h"

#include <cstdio>
#include <cctype>

using namespace em;

namespace echo {

void CameraData::update(float aspect) {
    forward = normalize(forward);
    view = Mat4::lookAt(position, position + forward, Vec3(0, 1, 0));
    proj = Mat4::perspective(fovY, aspect, nearPlane, farPlane);
    viewProj = proj * view;
    invViewProj = viewProj.inverted();
    invProj = proj.inverted();
    invView = view.inverted();
    frustum.fromMatrix(viewProj);
}

void QualitySettings::applyPreset(int p) {
    preset = clampi(p, 0, 3);
    switch (preset) {
    case 0:
        ssao = true; ssr = false; volumetric = true; bloom = true; fxaa = true; shadows = true;
        shadowTileSize = 512; volumetricSteps = 16; ssrSteps = 10; renderScale = 0.62f;
        maxShadowLights = 4; maxVolumetricLights = 3; ssaoSamples = 10;
        maxRenderPixels = 540000;
        break;
    case 1:
        ssao = true; ssr = false; volumetric = true; bloom = true; fxaa = true; shadows = true;
        shadowTileSize = 640; volumetricSteps = 22; ssrSteps = 14; renderScale = 0.80f;
        maxShadowLights = 5; maxVolumetricLights = 3; ssaoSamples = 12;
        maxRenderPixels = 1400000;
        break;
    case 2:
        ssao = true; ssr = true; volumetric = true; bloom = true; fxaa = true; shadows = true;
        shadowTileSize = 1024; volumetricSteps = 32; ssrSteps = 26; renderScale = 1.0f;
        maxShadowLights = 10; maxVolumetricLights = 5; ssaoSamples = 20;
        maxRenderPixels = 2500000;
        break;
    default:
        ssao = true; ssr = true; volumetric = true; bloom = true; fxaa = true; shadows = true;
        shadowTileSize = 1536; volumetricSteps = 56; ssrSteps = 44; renderScale = 1.0f;
        maxShadowLights = 16; maxVolumetricLights = 8; ssaoSamples = 24;
        maxRenderPixels = 0;
        break;
    }
}

int QualitySettings::detectPreset() {
    std::string r = glRendererString();
    std::string v = glVendorString();
    for (auto& c : r) c = (char)std::tolower((unsigned char)c);
    for (auto& c : v) c = (char)std::tolower((unsigned char)c);

    bool intel = v.find("intel") != std::string::npos;
    bool software = r.find("llvmpipe") != std::string::npos || r.find("softwar") != std::string::npos || r.find("gdi") != std::string::npos;
    if (software) return 0;

    if (intel) {
        if (r.find("arc") != std::string::npos) return 2;
        if (r.find("iris xe") != std::string::npos) return 1;
        return 0;
    }

    bool nvidia = v.find("nvidia") != std::string::npos;
    bool amd = v.find("amd") != std::string::npos || v.find("ati") != std::string::npos;
    if (nvidia) {
        if (r.find("rtx 40") != std::string::npos || r.find("rtx 50") != std::string::npos || r.find("rtx 30") != std::string::npos) return 3;
        if (r.find("rtx") != std::string::npos || r.find("gtx 16") != std::string::npos || r.find("gtx 10") != std::string::npos) return 2;
        return 1;
    }
    if (amd) {
        if (r.find("rx 7") != std::string::npos || r.find("rx 6") != std::string::npos) return 3;
        if (r.find("rx ") != std::string::npos) return 2;
        return 1;
    }
    return 1;
}

static std::string shaderDefines() {
    char buf[512];
    std::snprintf(buf, sizeof(buf),
                  "#define MAX_LIGHTS %d\n#define MAX_SHADOWS %d\n#define SHADOW_TILES %d\n#define SSAO_KERNEL %d\n#define MAT_COUNT %d\n",
                  kMaxLights, kMaxShadows, kShadowTiles, kSSAOKernel, (int)MAT_COUNT);
    return std::string(buf);
}

bool Renderer::loadShaders() {
    std::string def = shaderDefines();
    bool ok = true;
    ok &= shGBuffer.loadFromFiles("shaders/gbuffer.vert", "shaders/gbuffer.frag", def);
    ok &= shShadow.loadFromFiles("shaders/shadow.vert", "shaders/shadow.frag", def);
    ok &= shLighting.loadFromFiles("shaders/fullscreen.vert", "shaders/lighting.frag", def);
    ok &= shSSAO.loadFromFiles("shaders/fullscreen.vert", "shaders/ssao.frag", def);
    ok &= shBlur.loadFromFiles("shaders/fullscreen.vert", "shaders/blur.frag", def);
    ok &= shSSR.loadFromFiles("shaders/fullscreen.vert", "shaders/ssr.frag", def);
    ok &= shVolumetric.loadFromFiles("shaders/fullscreen.vert", "shaders/volumetric.frag", def);
    ok &= shComposite.loadFromFiles("shaders/fullscreen.vert", "shaders/composite.frag", def);
    ok &= shBloomPre.loadFromFiles("shaders/fullscreen.vert", "shaders/bloom_prefilter.frag", def);
    ok &= shBloomDown.loadFromFiles("shaders/fullscreen.vert", "shaders/bloom_down.frag", def);
    ok &= shBloomUp.loadFromFiles("shaders/fullscreen.vert", "shaders/bloom_up.frag", def);
    ok &= shPost.loadFromFiles("shaders/fullscreen.vert", "shaders/post.frag", def);
    ok &= shFXAA.loadFromFiles("shaders/fullscreen.vert", "shaders/fxaa.frag", def);
    ok &= shForward.loadFromFiles("shaders/forward.vert", "shaders/forward.frag", def);
    ok &= shTerrain.loadFromFiles("shaders/terrain.vert", "shaders/terrain.frag", def);
    return ok;
}

bool Renderer::reloadShaders() {
    bool ok = loadShaders();
    LOG_INFO("Shader reload %s", ok ? "ok" : "failed");
    return ok;
}

void Renderer::buildSSAOKernel() {
    Rng rng(0x5EED0A0);
    for (int i = 0; i < kSSAOKernel; i++) {
        Vec3 s(rng.range(-1.0f, 1.0f), rng.range(-1.0f, 1.0f), rng.range(0.08f, 1.0f));
        s = normalize(s);
        float scale = (float)i / kSSAOKernel;
        scale = lerpf(0.15f, 1.0f, scale * scale);
        s *= scale * rng.range(0.35f, 1.0f);
        ssaoKernel[i * 3 + 0] = s.x;
        ssaoKernel[i * 3 + 1] = s.y;
        ssaoKernel[i * 3 + 2] = s.z;
    }
}

bool Renderer::init(int width, int height, const QualitySettings& q) {
    quality_ = q;
    screenW = std::max(width, 1);
    screenH = std::max(height, 1);

    glGenVertexArrays(1, &emptyVAO);

    if (!loadShaders()) {
        LOG_ERROR("Renderer shader compilation failed");
        return false;
    }

    matLib.generate(512);
    buildSSAOKernel();

    shadowAtlasSize = quality_.shadowTileSize * kShadowTiles;
    AttachmentDesc sd;
    sd.internalFormat = GL_DEPTH_COMPONENT32F;
    sd.format = GL_DEPTH_COMPONENT;
    sd.type = GL_FLOAT;
    sd.filter = GL_LINEAR;
    sd.wrap = GL_CLAMP_TO_BORDER;
    shadowFB.createDepthOnly(shadowAtlasSize, shadowAtlasSize, sd);

    createTargets();

    u8 white[4] = { 255, 255, 255, 255 };
    glGenTextures(1, &whiteTex);
    glBindTexture(GL_TEXTURE_2D, whiteTex);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, 1, 1, 0, GL_RGBA, GL_UNSIGNED_BYTE, white);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glBindTexture(GL_TEXTURE_2D, 0);

    glEnable(GL_DEPTH_TEST);
    glEnable(GL_CULL_FACE);
    glCullFace(GL_BACK);
    glFrontFace(GL_CCW);
    glDepthFunc(GL_LEQUAL);
    glEnable(GL_TEXTURE_CUBE_MAP_SEAMLESS);

    initialized = true;
    LOG_INFO("Renderer initialized %dx%d (render %dx%d, shadow atlas %d)", screenW, screenH, renderW, renderH, shadowAtlasSize);
    return true;
}

void Renderer::createTargets() {
    float scale = quality_.renderScale;
    if (quality_.maxRenderPixels > 0) {
        float pixels = (float)screenW * (float)screenH * scale * scale;
        if (pixels > (float)quality_.maxRenderPixels) {
            scale *= std::sqrt((float)quality_.maxRenderPixels / pixels);
        }
    }
    scale = clampf(scale, 0.35f, 1.0f);

    renderW = std::max(1, (int)(screenW * scale));
    renderH = std::max(1, (int)(screenH * scale));
    halfW = std::max(1, renderW / 2);
    halfH = std::max(1, renderH / 2);

    AttachmentDesc albedoD;
    albedoD.internalFormat = GL_RGBA8;
    albedoD.format = GL_RGBA;
    albedoD.type = GL_UNSIGNED_BYTE;
    albedoD.filter = GL_NEAREST;

    AttachmentDesc normalD;
    normalD.internalFormat = GL_RGB10_A2;
    normalD.format = GL_RGBA;
    normalD.type = GL_UNSIGNED_INT_2_10_10_10_REV;
    normalD.filter = GL_NEAREST;

    AttachmentDesc matD = albedoD;

    AttachmentDesc depthD;
    depthD.internalFormat = GL_DEPTH_COMPONENT32F;
    depthD.format = GL_DEPTH_COMPONENT;
    depthD.type = GL_FLOAT;
    depthD.filter = GL_NEAREST;

    gbuffer.create(renderW, renderH, { albedoD, normalD, matD }, &depthD);

    AttachmentDesc hdrD;
    hdrD.internalFormat = GL_RGBA16F;
    hdrD.format = GL_RGBA;
    hdrD.type = GL_HALF_FLOAT;
    hdrD.filter = GL_LINEAR;
    hdrD.mipmaps = true;

    hdrA.create(renderW, renderH, { hdrD }, &depthD);

    AttachmentDesc hdrNoMip = hdrD;
    hdrNoMip.mipmaps = false;
    hdrB.create(renderW, renderH, { hdrNoMip }, nullptr);

    AttachmentDesc aoD;
    aoD.internalFormat = GL_R8;
    aoD.format = GL_RED;
    aoD.type = GL_UNSIGNED_BYTE;
    aoD.filter = GL_LINEAR;
    ssaoFB.create(halfW, halfH, { aoD }, nullptr);
    ssaoBlurFB.create(halfW, halfH, { aoD }, nullptr);

    ssrFB.create(halfW, halfH, { hdrNoMip }, nullptr);
    fogFB.create(halfW, halfH, { hdrNoMip }, nullptr);
    fogBlurFB.create(halfW, halfH, { hdrNoMip }, nullptr);

    AttachmentDesc ldrD;
    ldrD.internalFormat = GL_RGBA8;
    ldrD.format = GL_RGBA;
    ldrD.type = GL_UNSIGNED_BYTE;
    ldrD.filter = GL_LINEAR;
    ldrFB.create(renderW, renderH, { ldrD }, nullptr);

    int bw = halfW, bh = halfH;
    for (int i = 0; i < kBloomMips; i++) {
        bloomFB[i].create(std::max(bw, 1), std::max(bh, 1), { hdrNoMip }, nullptr);
        bw /= 2;
        bh /= 2;
    }
}

void Renderer::destroyTargets() {
    gbuffer.destroy();
    hdrA.destroy();
    hdrB.destroy();
    ssaoFB.destroy();
    ssaoBlurFB.destroy();
    ssrFB.destroy();
    fogFB.destroy();
    fogBlurFB.destroy();
    ldrFB.destroy();
    for (int i = 0; i < kBloomMips; i++) bloomFB[i].destroy();
}

void Renderer::shutdown() {
    destroyTargets();
    shadowFB.destroy();
    matLib.destroy();
    if (emptyVAO) { glDeleteVertexArrays(1, &emptyVAO); emptyVAO = 0; }
    if (whiteTex) { glDeleteTextures(1, &whiteTex); whiteTex = 0; }
    initialized = false;
}

void Renderer::resize(int width, int height) {
    if (width <= 0 || height <= 0) return;
    if (width == screenW && height == screenH) return;
    screenW = width;
    screenH = height;
    destroyTargets();
    createTargets();
}

void Renderer::setQuality(const QualitySettings& q) {
    bool shadowChanged = q.shadowTileSize != quality_.shadowTileSize;
    bool scaleChanged = q.renderScale != quality_.renderScale || q.maxRenderPixels != quality_.maxRenderPixels;
    quality_ = q;
    if (shadowChanged) {
        shadowAtlasSize = quality_.shadowTileSize * kShadowTiles;
        AttachmentDesc sd;
        sd.internalFormat = GL_DEPTH_COMPONENT32F;
        sd.format = GL_DEPTH_COMPONENT;
        sd.type = GL_FLOAT;
        sd.filter = GL_LINEAR;
        sd.wrap = GL_CLAMP_TO_BORDER;
        shadowFB.destroy();
        shadowFB.createDepthOnly(shadowAtlasSize, shadowAtlasSize, sd);
    }
    if (scaleChanged) {
        destroyTargets();
        createTargets();
    }
}

void Renderer::beginFrame(const CameraData& cam, float time, float dt) {
    cam_ = cam;
    time_ = time;
    dt_ = dt;
    opaque.clear();
    terrainDraws.clear();
    transparent.clear();
    shadowCasters.clear();
    lights.clear();
    shadowLights.clear();
    stats_ = RenderStats();
    frameIndex++;
}

void Renderer::submit(const DrawCall& dc) {
    if (!dc.mesh || !dc.mesh->valid()) return;
    if (dc.bounds.valid() && !cam_.frustum.testAABB(dc.bounds)) {
        stats_.culled++;
        if (dc.castShadow) shadowCasters.push_back(dc);
        return;
    }
    if (dc.transparent) {
        DrawCall t = dc;
        t.sortKey = -distanceSq(dc.bounds.valid() ? dc.bounds.center() : dc.transform.origin(), cam_.position);
        transparent.push_back(t);
    } else {
        opaque.push_back(dc);
    }
    if (dc.castShadow) shadowCasters.push_back(dc);
}

void Renderer::submitTerrain(const DrawCall& dc) {
    if (!dc.mesh || !dc.mesh->valid()) return;
    if (dc.bounds.valid() && !cam_.frustum.testAABB(dc.bounds)) {
        stats_.culled++;
        return;
    }
    terrainDraws.push_back(dc);
}

void Renderer::submitLight(const RenderLight& l) {
    if (l.intensity <= 0.0001f) return;
    if (!cam_.frustum.testSphere(l.position, l.range)) {
        float d = distance(l.position, cam_.position);
        if (d > l.range * 1.5f) return;
    }
    if ((int)lights.size() >= kMaxLights) return;
    lights.push_back(l);
}

void Renderer::assignShadowSlots() {
    struct Cand { int index; float score; };
    std::vector<Cand> cands;
    for (int i = 0; i < (int)lights.size(); i++) {
        lights[(size_t)i].shadowSlot = -1;
        if (!lights[(size_t)i].castShadows || !lights[(size_t)i].spot) continue;
        float d = distance(lights[(size_t)i].position, cam_.position);
        float score = lights[(size_t)i].intensity * lights[(size_t)i].range / (1.0f + d * d * 0.05f) + lights[(size_t)i].priority;
        cands.push_back({ i, score });
    }
    std::sort(cands.begin(), cands.end(), [](const Cand& a, const Cand& b) { return a.score > b.score; });

    int limit = clampi(quality_.maxShadowLights, 0, kMaxShadows);
    int slot = 0;
    for (const auto& c : cands) {
        if (slot >= limit) break;
        lights[(size_t)c.index].shadowSlot = slot;
        shadowLights.push_back(c.index);

        const RenderLight& l = lights[(size_t)c.index];
        Vec3 up = std::fabs(l.direction.y) > 0.95f ? Vec3(0, 0, 1) : Vec3(0, 1, 0);
        float fov = clampf(l.outerAngle * 2.0f + 0.16f, 0.25f, 2.05f);
        Mat4 lv = Mat4::lookAt(l.position, l.position + l.direction, up);
        Mat4 lp = Mat4::perspective(fov, 1.0f, 0.08f, std::max(l.range, 0.5f));
        shadowMatrices[slot] = lp * lv;
        slot++;
    }
    stats_.shadowedLights = slot;
}

void Renderer::uploadLights(Shader& sh) {
    float pos[kMaxLights * 4];
    float col[kMaxLights * 4];
    float dir[kMaxLights * 4];
    float ext[kMaxLights * 4];
    int n = (int)lights.size();
    for (int i = 0; i < n; i++) {
        const RenderLight& l = lights[(size_t)i];
        pos[i * 4 + 0] = l.position.x;
        pos[i * 4 + 1] = l.position.y;
        pos[i * 4 + 2] = l.position.z;
        pos[i * 4 + 3] = l.range;
        Vec3 c = l.color * l.intensity;
        col[i * 4 + 0] = c.x;
        col[i * 4 + 1] = c.y;
        col[i * 4 + 2] = c.z;
        col[i * 4 + 3] = l.spot ? 1.0f : 0.0f;
        Vec3 d = normalize(l.direction);
        dir[i * 4 + 0] = d.x;
        dir[i * 4 + 1] = d.y;
        dir[i * 4 + 2] = d.z;
        dir[i * 4 + 3] = std::cos(l.outerAngle);
        ext[i * 4 + 0] = std::cos(l.innerAngle);
        ext[i * 4 + 1] = (float)l.shadowSlot;
        ext[i * 4 + 2] = l.volumetric;
        ext[i * 4 + 3] = 0.0f;
    }
    sh.setInt("uLightCount", n);
    if (n > 0) {
        sh.setVec4Array("uLightPosRange", pos, n);
        sh.setVec4Array("uLightColor", col, n);
        sh.setVec4Array("uLightDir", dir, n);
        sh.setVec4Array("uLightExtra", ext, n);
    }
    stats_.lights = n;
}

void Renderer::uploadVolumetricLights(Shader& sh) {
    struct Cand { int index; float score; };
    std::vector<Cand> cands;
    cands.reserve(lights.size());
    for (int i = 0; i < (int)lights.size(); i++) {
        const RenderLight& l = lights[(size_t)i];
        if (l.volumetric <= 0.005f) continue;
        float d = distance(l.position, cam_.position);
        cands.push_back({ i, l.intensity * l.volumetric * l.range / (1.0f + d * d * 0.03f) + l.priority });
    }
    std::sort(cands.begin(), cands.end(), [](const Cand& a, const Cand& b) { return a.score > b.score; });

    int limit = clampi(quality_.maxVolumetricLights, 0, kMaxLights);
    int n = std::min((int)cands.size(), limit);

    float pos[kMaxLights * 4];
    float col[kMaxLights * 4];
    float dir[kMaxLights * 4];
    float ext[kMaxLights * 4];

    for (int i = 0; i < n; i++) {
        const RenderLight& l = lights[(size_t)cands[(size_t)i].index];
        pos[i * 4 + 0] = l.position.x;
        pos[i * 4 + 1] = l.position.y;
        pos[i * 4 + 2] = l.position.z;
        pos[i * 4 + 3] = l.range;
        Vec3 c = l.color * l.intensity;
        col[i * 4 + 0] = c.x;
        col[i * 4 + 1] = c.y;
        col[i * 4 + 2] = c.z;
        col[i * 4 + 3] = l.spot ? 1.0f : 0.0f;
        Vec3 d = normalize(l.direction);
        dir[i * 4 + 0] = d.x;
        dir[i * 4 + 1] = d.y;
        dir[i * 4 + 2] = d.z;
        dir[i * 4 + 3] = std::cos(l.outerAngle);
        ext[i * 4 + 0] = std::cos(l.innerAngle);
        ext[i * 4 + 1] = (float)l.shadowSlot;
        ext[i * 4 + 2] = l.volumetric;
        ext[i * 4 + 3] = 0.0f;
    }

    sh.setInt("uLightCount", n);
    if (n > 0) {
        sh.setVec4Array("uLightPosRange", pos, n);
        sh.setVec4Array("uLightColor", col, n);
        sh.setVec4Array("uLightDir", dir, n);
        sh.setVec4Array("uLightExtra", ext, n);
    }
}

void Renderer::drawFullscreen() {
    glBindVertexArray(emptyVAO);
    glDrawArrays(GL_TRIANGLES, 0, 3);
}

void Renderer::shadowPass() {
    if (!quality_.shadows || shadowLights.empty()) {
        shadowFB.bind();
        glViewport(0, 0, shadowAtlasSize, shadowAtlasSize);
        glClearDepth(1.0);
        glDepthMask(GL_TRUE);
        glClear(GL_DEPTH_BUFFER_BIT);
        return;
    }

    shadowFB.bind();
    glViewport(0, 0, shadowAtlasSize, shadowAtlasSize);
    glDepthMask(GL_TRUE);
    glClearDepth(1.0);
    glClear(GL_DEPTH_BUFFER_BIT);

    glEnable(GL_DEPTH_TEST);
    glEnable(GL_CULL_FACE);
    glCullFace(GL_FRONT);
    glEnable(GL_POLYGON_OFFSET_FILL);
    glPolygonOffset(1.8f, 3.0f);

    shShadow.bind();
    int tile = quality_.shadowTileSize;

    for (size_t si = 0; si < shadowLights.size(); si++) {
        const RenderLight& l = lights[(size_t)shadowLights[si]];
        int slot = l.shadowSlot;
        if (slot < 0) continue;
        int tx = (slot % kShadowTiles) * tile;
        int ty = (slot / kShadowTiles) * tile;
        glViewport(tx, ty, tile, tile);

        Frustum lf;
        lf.fromMatrix(shadowMatrices[slot]);
        shShadow.setMat4("uLightViewProj", shadowMatrices[slot]);

        for (const DrawCall& dc : shadowCasters) {
            if (dc.transparent) continue;
            if (dc.bounds.valid() && !lf.testAABB(dc.bounds)) continue;
            shShadow.setMat4("uModel", dc.transform);
            dc.mesh->bind();
            dc.mesh->drawSub(dc.subIndex);
            stats_.shadowDraws++;
        }
    }

    glDisable(GL_POLYGON_OFFSET_FILL);
    glCullFace(GL_BACK);
}

void Renderer::geometryPass() {
    gbuffer.bindWithViewport();
    glDepthMask(GL_TRUE);
    glEnable(GL_DEPTH_TEST);
    glDisable(GL_BLEND);
    glClearColor(0.0f, 0.0f, 0.0f, 0.0f);
    glClearDepth(1.0);
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

    std::sort(opaque.begin(), opaque.end(), [](const DrawCall& a, const DrawCall& b) {
        return a.material < b.material;
    });

    shGBuffer.bind();
    shGBuffer.setMat4("uViewProj", cam_.viewProj);
    shGBuffer.setVec3("uCameraPos", cam_.position);
    shGBuffer.setFloat("uTime", time_);
    shGBuffer.setFloat("uGlobalWetness", atmos.globalWetness);
    shGBuffer.setFloat("uDecay", atmos.decay);
    shGBuffer.setVec4("uWarp", atmos.warp);
    matLib.uploadUniforms(shGBuffer);
    shGBuffer.setTexture("uAlbedoArray", 0, matLib.albedoArray(), GL_TEXTURE_2D_ARRAY);
    shGBuffer.setTexture("uNormalArray", 1, matLib.normalArray(), GL_TEXTURE_2D_ARRAY);
    shGBuffer.setTexture("uORMArray", 2, matLib.ormArray(), GL_TEXTURE_2D_ARRAY);
    shGBuffer.setTexture("uDetailNoise", 3, matLib.noiseTexture());

    int lastMat = -999;
    const Mesh* lastMesh = nullptr;
    for (const DrawCall& dc : opaque) {
        int mat = dc.material >= 0 ? dc.material : dc.mesh->subMeshes()[(size_t)dc.subIndex].material;
        if (mat != lastMat) {
            shGBuffer.setInt("uMaterial", mat);
            lastMat = mat;
        }
        shGBuffer.setVec4("uTintOverride", dc.tint);
        shGBuffer.setMat4("uModel", dc.transform);
        shGBuffer.setMat3("uNormalMat", dc.transform.normalMatrix());
        if (dc.mesh != lastMesh) {
            dc.mesh->bind();
            lastMesh = dc.mesh;
        }
        dc.mesh->drawSub(dc.subIndex);
        stats_.drawCalls++;
        stats_.triangles += (int)(dc.mesh->subMeshes()[(size_t)dc.subIndex].indexCount / 3);
    }

    if (!terrainDraws.empty()) {
        shTerrain.bind();
        shTerrain.setMat4("uViewProj", cam_.viewProj);
        shTerrain.setFloat("uTime", time_);
        shTerrain.setFloat("uWaterLevel", terrainCfg.waterLevel);
        shTerrain.setFloat("uMaxHeight", terrainCfg.maxHeight);
        shTerrain.setFloat("uSnowLine", terrainCfg.snowLine);
        shTerrain.setTexture("uDetailNoise", 0, matLib.noiseTexture());

        const Mesh* lastTerrain = nullptr;
        for (const DrawCall& dc : terrainDraws) {
            if (dc.mesh != lastTerrain) {
                dc.mesh->bind();
                lastTerrain = dc.mesh;
            }
            dc.mesh->drawSub(dc.subIndex);
            stats_.drawCalls++;
            stats_.triangles += (int)(dc.mesh->subMeshes()[(size_t)dc.subIndex].indexCount / 3);
        }
    }
}

void Renderer::ssaoPass() {
    if (!quality_.ssao) {
        ssaoBlurFB.bindWithViewport();
        glClearColor(1, 1, 1, 1);
        glClear(GL_COLOR_BUFFER_BIT);
        return;
    }

    glDisable(GL_DEPTH_TEST);
    glDepthMask(GL_FALSE);

    ssaoFB.bindWithViewport();
    shSSAO.bind();
    shSSAO.setMat4("uProj", cam_.proj);
    shSSAO.setMat4("uInvProj", cam_.invProj);
    shSSAO.setMat4("uView", cam_.view);
    shSSAO.setVec2("uResolution", Vec2((float)halfW, (float)halfH));
    shSSAO.setVec3Array("uKernel", ssaoKernel, kSSAOKernel);
    shSSAO.setInt("uKernelCount", clampi(quality_.ssaoSamples, 4, kSSAOKernel));
    shSSAO.setFloat("uRadius", 0.55f);
    shSSAO.setFloat("uIntensity", 1.15f);
    shSSAO.setFloat("uBias", 0.022f);
    shSSAO.setFloat("uFrameIndex", (float)(frameIndex % 64));
    shSSAO.setTexture("uDepthTex", 0, gbuffer.depthTex());
    shSSAO.setTexture("uNormalTex", 1, gbuffer.colorTex(1));
    shSSAO.setTexture("uBlueNoise", 2, matLib.blueNoiseTexture());
    drawFullscreen();

    shBlur.bind();
    shBlur.setFloat("uNear", cam_.nearPlane);
    shBlur.setFloat("uFar", cam_.farPlane);
    shBlur.setFloat("uDepthSigma", 6.0f);
    shBlur.setVec2("uTexelSize", Vec2(1.0f / halfW, 1.0f / halfH));

    ssaoBlurFB.bindWithViewport();
    shBlur.setVec2("uDirection", Vec2(1, 0));
    shBlur.setTexture("uSource", 0, ssaoFB.colorTex(0));
    shBlur.setTexture("uDepthTex", 1, gbuffer.depthTex());
    drawFullscreen();

    ssaoFB.bindWithViewport();
    shBlur.setVec2("uDirection", Vec2(0, 1));
    shBlur.setTexture("uSource", 0, ssaoBlurFB.colorTex(0));
    shBlur.setTexture("uDepthTex", 1, gbuffer.depthTex());
    drawFullscreen();

    ssaoBlurFB.bindWithViewport();
    shBlur.setVec2("uDirection", Vec2(1, 0));
    shBlur.setTexture("uSource", 0, ssaoFB.colorTex(0));
    shBlur.setTexture("uDepthTex", 1, gbuffer.depthTex());
    drawFullscreen();
}

void Renderer::lightingPass() {
    hdrA.bindWithViewport();
    glDisable(GL_DEPTH_TEST);
    glDepthMask(GL_FALSE);
    glDisable(GL_BLEND);
    glClearColor(0, 0, 0, 1);
    glClear(GL_COLOR_BUFFER_BIT);

    shLighting.bind();
    shLighting.setMat4("uInvViewProj", cam_.invViewProj);
    shLighting.setVec3("uCameraPos", cam_.position);
    shLighting.setVec2("uResolution", Vec2((float)renderW, (float)renderH));
    shLighting.setFloat("uTime", time_);
    shLighting.setFloat("uNear", cam_.nearPlane);
    shLighting.setFloat("uFar", cam_.farPlane);
    shLighting.setVec3("uAmbientTop", atmos.ambientTop);
    shLighting.setVec3("uAmbientBottom", atmos.ambientBottom);
    shLighting.setFloat("uAmbientIntensity", atmos.ambientIntensity);
    shLighting.setFloat("uShadowTexel", 1.0f / (float)quality_.shadowTileSize);
    shLighting.setFloat("uSanity", postParams.sanity);
    shLighting.setInt("uSkyEnabled", skyParams.enabled ? 1 : 0);
    shLighting.setVec3("uSunDir", normalize(skyParams.sunDirection));
    shLighting.setVec3("uSunColor", skyParams.sunColor);
    shLighting.setFloat("uSunIntensity", skyParams.enabled ? skyParams.sunIntensity : 0.0f);
    shLighting.setVec3("uSkyZenith", skyParams.zenith);
    shLighting.setVec3("uSkyHorizon", skyParams.horizon);
    shLighting.setVec3("uSkyGround", skyParams.ground);
    shLighting.setFloat("uSunDisc", skyParams.sunDisc);
    shLighting.setFloat("uStars", skyParams.starAmount);
    shLighting.setFloat("uClouds", skyParams.cloudAmount);
    shLighting.setFloat("uAerialDensity", skyParams.aerialDensity);
    shLighting.setFloat("uAerialHeight", skyParams.aerialHeight);
    uploadLights(shLighting);
    for (int i = 0; i < stats_.shadowedLights; i++) {
        char name[32];
        std::snprintf(name, sizeof(name), "uShadowMatrix[%d]", i);
        shLighting.setMat4(name, shadowMatrices[i]);
    }
    shLighting.setTexture("uAlbedoAO", 0, gbuffer.colorTex(0));
    shLighting.setTexture("uNormalTex", 1, gbuffer.colorTex(1));
    shLighting.setTexture("uMaterialTex", 2, gbuffer.colorTex(2));
    shLighting.setTexture("uDepthTex", 3, gbuffer.depthTex());
    shLighting.setTexture("uSSAOTex", 4, quality_.ssao ? ssaoBlurFB.colorTex(0) : whiteTex);
    shLighting.setTexture("uShadowAtlas", 5, shadowFB.depthTex());
    drawFullscreen();
}

void Renderer::forwardPass() {
    if (transparent.empty()) return;

    std::sort(transparent.begin(), transparent.end(), [](const DrawCall& a, const DrawCall& b) {
        return a.sortKey < b.sortKey;
    });

    glBindFramebuffer(GL_READ_FRAMEBUFFER, gbuffer.id());
    glBindFramebuffer(GL_DRAW_FRAMEBUFFER, hdrA.id());
    glBlitFramebuffer(0, 0, renderW, renderH, 0, 0, renderW, renderH, GL_DEPTH_BUFFER_BIT, GL_NEAREST);

    hdrA.bindWithViewport();
    glEnable(GL_DEPTH_TEST);
    glDepthMask(GL_FALSE);
    glEnable(GL_BLEND);
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    glDisable(GL_CULL_FACE);

    shForward.bind();
    shForward.setMat4("uViewProj", cam_.viewProj);
    shForward.setVec3("uCameraPos", cam_.position);
    shForward.setFloat("uTime", time_);
    shForward.setVec3("uAmbientTop", atmos.ambientTop);
    shForward.setVec3("uAmbientBottom", atmos.ambientBottom);
    shForward.setFloat("uAmbientIntensity", atmos.ambientIntensity);
    matLib.uploadUniforms(shForward);
    uploadLights(shForward);
    shForward.setTexture("uAlbedoArray", 0, matLib.albedoArray(), GL_TEXTURE_2D_ARRAY);
    shForward.setTexture("uORMArray", 1, matLib.ormArray(), GL_TEXTURE_2D_ARRAY);

    for (const DrawCall& dc : transparent) {
        int mat = dc.material >= 0 ? dc.material : dc.mesh->subMeshes()[(size_t)dc.subIndex].material;
        shForward.setInt("uMaterial", mat);
        shForward.setFloat("uAlpha", dc.tint.w);
        shForward.setMat4("uModel", dc.transform);
        shForward.setMat3("uNormalMat", dc.transform.normalMatrix());
        dc.mesh->bind();
        dc.mesh->drawSub(dc.subIndex);
        stats_.drawCalls++;
    }

    glEnable(GL_CULL_FACE);
    glDisable(GL_BLEND);
    glDepthMask(GL_TRUE);
}

void Renderer::ssrPass() {
    if (!quality_.ssr) {
        ssrFB.bindWithViewport();
        glClearColor(0, 0, 0, 0);
        glClear(GL_COLOR_BUFFER_BIT);
        return;
    }

    hdrA.generateColorMips(0);

    ssrFB.bindWithViewport();
    glDisable(GL_DEPTH_TEST);
    glDepthMask(GL_FALSE);
    glClearColor(0, 0, 0, 0);
    glClear(GL_COLOR_BUFFER_BIT);

    shSSR.bind();
    shSSR.setMat4("uProj", cam_.proj);
    shSSR.setMat4("uInvProj", cam_.invProj);
    shSSR.setMat4("uView", cam_.view);
    shSSR.setMat4("uInvView", cam_.invView);
    shSSR.setVec2("uResolution", Vec2((float)halfW, (float)halfH));
    shSSR.setFloat("uFrameIndex", (float)(frameIndex % 64));
    shSSR.setFloat("uMaxDistance", 14.0f);
    shSSR.setFloat("uIntensity", 1.0f);
    shSSR.setInt("uSteps", quality_.ssrSteps);
    shSSR.setInt("uRefineSteps", 5);
    shSSR.setTexture("uColorTex", 0, hdrA.colorTex(0));
    shSSR.setTexture("uDepthTex", 1, gbuffer.depthTex());
    shSSR.setTexture("uNormalTex", 2, gbuffer.colorTex(1));
    shSSR.setTexture("uMaterialTex", 3, gbuffer.colorTex(2));
    shSSR.setTexture("uBlueNoise", 4, matLib.blueNoiseTexture());
    drawFullscreen();
}

void Renderer::volumetricPass() {
    fogFB.bindWithViewport();
    glDisable(GL_DEPTH_TEST);
    glDepthMask(GL_FALSE);

    if (!quality_.volumetric) {
        glClearColor(0, 0, 0, 1);
        glClear(GL_COLOR_BUFFER_BIT);
        return;
    }

    shVolumetric.bind();
    shVolumetric.setMat4("uInvViewProj", cam_.invViewProj);
    shVolumetric.setVec3("uCameraPos", cam_.position);
    shVolumetric.setVec2("uResolution", Vec2((float)halfW, (float)halfH));
    shVolumetric.setFloat("uTime", time_);
    shVolumetric.setFloat("uFrameIndex", (float)(frameIndex % 64));
    shVolumetric.setFloat("uFogDensity", atmos.fogDensity);
    shVolumetric.setFloat("uFogHeightFalloff", atmos.fogHeightFalloff);
    shVolumetric.setFloat("uFogBase", atmos.fogBase);
    shVolumetric.setVec3("uFogColor", atmos.fogColor);
    shVolumetric.setFloat("uScattering", atmos.scattering);
    shVolumetric.setInt("uSteps", quality_.volumetricSteps);
    shVolumetric.setFloat("uMaxDistance", 60.0f);
    shVolumetric.setFloat("uDustAmount", atmos.dust);
    uploadVolumetricLights(shVolumetric);
    for (int i = 0; i < stats_.shadowedLights; i++) {
        char name[32];
        std::snprintf(name, sizeof(name), "uShadowMatrix[%d]", i);
        shVolumetric.setMat4(name, shadowMatrices[i]);
    }
    shVolumetric.setTexture("uDepthTex", 0, gbuffer.depthTex());
    shVolumetric.setTexture("uShadowAtlas", 1, shadowFB.depthTex());
    shVolumetric.setTexture("uBlueNoise", 2, matLib.blueNoiseTexture());
    drawFullscreen();

    shBlur.bind();
    shBlur.setFloat("uNear", cam_.nearPlane);
    shBlur.setFloat("uFar", cam_.farPlane);
    shBlur.setFloat("uDepthSigma", 1.2f);
    shBlur.setVec2("uTexelSize", Vec2(1.0f / halfW, 1.0f / halfH));

    fogBlurFB.bindWithViewport();
    shBlur.setVec2("uDirection", Vec2(1, 0));
    shBlur.setTexture("uSource", 0, fogFB.colorTex(0));
    shBlur.setTexture("uDepthTex", 1, gbuffer.depthTex());
    drawFullscreen();

    fogFB.bindWithViewport();
    shBlur.setVec2("uDirection", Vec2(0, 1));
    shBlur.setTexture("uSource", 0, fogBlurFB.colorTex(0));
    shBlur.setTexture("uDepthTex", 1, gbuffer.depthTex());
    drawFullscreen();
}

void Renderer::compositePass() {
    hdrB.bindWithViewport();
    glDisable(GL_DEPTH_TEST);
    glDepthMask(GL_FALSE);

    shComposite.bind();
    shComposite.setMat4("uInvViewProj", cam_.invViewProj);
    shComposite.setVec3("uCameraPos", cam_.position);
    shComposite.setFloat("uSSRStrength", quality_.ssr ? postParams.ssrStrength : 0.0f);
    shComposite.setFloat("uFogStrength", quality_.volumetric ? postParams.fogStrength : 0.0f);
    shComposite.setTexture("uSceneTex", 0, hdrA.colorTex(0));
    shComposite.setTexture("uSSRTex", 1, ssrFB.colorTex(0));
    shComposite.setTexture("uFogTex", 2, fogFB.colorTex(0));
    shComposite.setTexture("uNormalTex", 3, gbuffer.colorTex(1));
    shComposite.setTexture("uMaterialTex", 4, gbuffer.colorTex(2));
    shComposite.setTexture("uAlbedoAO", 5, gbuffer.colorTex(0));
    shComposite.setTexture("uDepthTex", 6, gbuffer.depthTex());
    drawFullscreen();
}

void Renderer::bloomPass() {
    if (!quality_.bloom) {
        bloomFB[0].bindWithViewport();
        glClearColor(0, 0, 0, 1);
        glClear(GL_COLOR_BUFFER_BIT);
        return;
    }

    glDisable(GL_DEPTH_TEST);
    glDepthMask(GL_FALSE);

    bloomFB[0].bindWithViewport();
    shBloomPre.bind();
    shBloomPre.setVec2("uTexelSize", Vec2(1.0f / renderW, 1.0f / renderH));
    shBloomPre.setFloat("uThreshold", postParams.bloomThreshold);
    shBloomPre.setFloat("uSoftKnee", 0.6f);
    shBloomPre.setFloat("uClamp", 24.0f);
    shBloomPre.setTexture("uSource", 0, hdrB.colorTex(0));
    drawFullscreen();

    shBloomDown.bind();
    for (int i = 1; i < kBloomMips; i++) {
        bloomFB[i].bindWithViewport();
        shBloomDown.setVec2("uTexelSize", Vec2(1.0f / bloomFB[i - 1].width(), 1.0f / bloomFB[i - 1].height()));
        shBloomDown.setTexture("uSource", 0, bloomFB[i - 1].colorTex(0));
        drawFullscreen();
    }

    shBloomUp.bind();
    shBloomUp.setFloat("uRadius", 1.35f);
    glEnable(GL_BLEND);
    glBlendFunc(GL_ONE, GL_ONE);
    glBlendEquation(GL_FUNC_ADD);
    for (int i = kBloomMips - 2; i >= 0; i--) {
        bloomFB[i].bindWithViewport();
        shBloomUp.setVec2("uTexelSize", Vec2(1.0f / bloomFB[i + 1].width(), 1.0f / bloomFB[i + 1].height()));
        shBloomUp.setTexture("uSource", 0, bloomFB[i + 1].colorTex(0));
        drawFullscreen();
    }
    glDisable(GL_BLEND);
}

void Renderer::postPass() {
    glDisable(GL_DEPTH_TEST);
    glDepthMask(GL_FALSE);
    glDisable(GL_BLEND);

    if (quality_.fxaa) {
        ldrFB.bindWithViewport();
    } else {
        Framebuffer::unbind(screenW, screenH);
    }

    shPost.bind();
    shPost.setVec2("uResolution", Vec2((float)renderW, (float)renderH));
    shPost.setFloat("uTime", time_);
    shPost.setFloat("uExposure", postParams.exposure);
    shPost.setFloat("uBloomStrength", quality_.bloom ? postParams.bloomStrength : 0.0f);
    shPost.setFloat("uVignette", postParams.vignette);
    shPost.setFloat("uGrain", postParams.grain);
    shPost.setFloat("uChromatic", postParams.chromatic);
    shPost.setFloat("uSaturation", postParams.saturation);
    shPost.setFloat("uContrast", postParams.contrast);
    shPost.setVec3("uLift", postParams.lift);
    shPost.setVec3("uGamma", postParams.gamma);
    shPost.setVec3("uGain", postParams.gain);
    shPost.setFloat("uSanity", postParams.sanity);
    shPost.setFloat("uDistortion", postParams.distortion);
    shPost.setFloat("uPulse", postParams.pulse);
    shPost.setFloat("uFlashWhite", postParams.flashWhite);
    shPost.setFloat("uFade", postParams.fade);
    shPost.setFloat("uScanline", postParams.scanline);

    GLuint sceneSource = hdrB.colorTex(0);
    if (debugView == 1) sceneSource = gbuffer.colorTex(0);
    else if (debugView == 2) sceneSource = gbuffer.colorTex(1);
    else if (debugView == 3) sceneSource = gbuffer.colorTex(2);
    else if (debugView == 4) sceneSource = ssaoBlurFB.colorTex(0);
    else if (debugView == 5) sceneSource = hdrA.colorTex(0);
    else if (debugView == 6) sceneSource = fogFB.colorTex(0);
    else if (debugView == 7) sceneSource = ssrFB.colorTex(0);
    if (debugView > 0) {
        shPost.setFloat("uExposure", 1.0f);
        shPost.setFloat("uVignette", 0.0f);
        shPost.setFloat("uGrain", 0.0f);
        shPost.setFloat("uChromatic", 0.0f);
        shPost.setFloat("uBloomStrength", 0.0f);
        shPost.setFloat("uSaturation", 1.0f);
        shPost.setFloat("uContrast", 1.0f);
        shPost.setVec3("uLift", Vec3(0));
        shPost.setVec3("uGamma", Vec3(1));
        shPost.setVec3("uGain", Vec3(1));
    }
    shPost.setTexture("uSceneTex", 0, sceneSource);
    shPost.setTexture("uBloomTex", 1, bloomFB[0].colorTex(0));
    shPost.setTexture("uDepthTex", 2, gbuffer.depthTex());
    shPost.setTexture("uBlueNoise", 3, matLib.blueNoiseTexture());
    drawFullscreen();

    if (quality_.fxaa) {
        Framebuffer::unbind(screenW, screenH);
        shFXAA.bind();
        shFXAA.setVec2("uTexelSize", Vec2(1.0f / renderW, 1.0f / renderH));
        shFXAA.setTexture("uSource", 0, ldrFB.colorTex(0));
        drawFullscreen();
    }
}

void Renderer::render() {
    if (!initialized) return;

    assignShadowSlots();
    shadowPass();
    geometryPass();
    ssaoPass();
    lightingPass();
    forwardPass();
    ssrPass();
    volumetricPass();
    compositePass();
    bloomPass();
    postPass();

    glEnable(GL_DEPTH_TEST);
    glDepthMask(GL_TRUE);
}

}
