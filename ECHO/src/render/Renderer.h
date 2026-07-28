#pragma once

#include "Shader.h"
#include "Mesh.h"
#include "Texture.h"
#include "Framebuffer.h"
#include "Material.h"

namespace echo {

static const int kMaxLights = 48;
static const int kMaxShadows = 16;
static const int kShadowTiles = 4;
static const int kSSAOKernel = 24;
static const int kBloomMips = 6;

struct RenderLight {
    em::Vec3 position = em::Vec3(0, 0, 0);
    em::Vec3 direction = em::Vec3(0, -1, 0);
    em::Vec3 color = em::Vec3(1, 1, 1);
    float intensity = 1.0f;
    float range = 8.0f;
    float innerAngle = 0.4f;
    float outerAngle = 0.7f;
    bool spot = false;
    bool castShadows = false;
    float volumetric = 1.0f;
    float priority = 0.0f;
    int shadowSlot = -1;
};

struct DrawCall {
    const Mesh* mesh = nullptr;
    int subIndex = 0;
    em::Mat4 transform;
    int material = -1;
    em::Vec4 tint = em::Vec4(1, 1, 1, 1);
    bool castShadow = true;
    bool transparent = false;
    em::AABB bounds;
    float sortKey = 0.0f;
};

struct CameraData {
    em::Mat4 view, proj, viewProj, invViewProj, invProj, invView;
    em::Vec3 position;
    em::Vec3 forward = em::Vec3(0, 0, -1);
    float nearPlane = 0.05f;
    float farPlane = 220.0f;
    float fovY = 1.221f;
    em::Frustum frustum;

    void update(float aspect);
};

struct SkyParams {
    bool enabled = false;
    em::Vec3 sunDirection = em::normalize(em::Vec3(0.35f, -0.62f, 0.28f));
    em::Vec3 sunColor = em::Vec3(1.0f, 0.94f, 0.82f);
    float sunIntensity = 2.6f;
    em::Vec3 zenith = em::Vec3(0.085f, 0.155f, 0.310f);
    em::Vec3 horizon = em::Vec3(0.520f, 0.600f, 0.700f);
    em::Vec3 ground = em::Vec3(0.075f, 0.082f, 0.075f);
    float sunDisc = 1.0f;
    float starAmount = 0.0f;
    float cloudAmount = 0.35f;
    float aerialDensity = 0.0018f;
    float aerialHeight = 0.006f;
};

struct TerrainParams {
    float waterLevel = 8.5f;
    float maxHeight = 92.0f;
    float snowLine = 0.62f;
};

struct AtmosphereParams {
    em::Vec3 ambientTop = em::Vec3(0.190f, 0.212f, 0.248f);
    em::Vec3 ambientBottom = em::Vec3(0.082f, 0.090f, 0.104f);
    float ambientIntensity = 1.0f;
    em::Vec3 fogColor = em::Vec3(0.070f, 0.086f, 0.104f);
    float fogDensity = 0.0105f;
    float fogHeightFalloff = 0.09f;
    float fogBase = -1.0f;
    float scattering = 0.55f;
    float dust = 0.22f;
    float globalWetness = 0.0f;
    float decay = 0.6f;
    em::Vec4 warp = em::Vec4(0, 0, 0.1f, 0.0f);
};

struct PostParams {
    float exposure = 2.35f;
    float bloomStrength = 0.048f;
    float bloomThreshold = 1.15f;
    float vignette = 0.62f;
    float grain = 0.038f;
    float chromatic = 0.0010f;
    float saturation = 0.90f;
    float contrast = 1.045f;
    em::Vec3 lift = em::Vec3(0.010f, 0.014f, 0.020f);
    em::Vec3 gamma = em::Vec3(1.02f, 1.00f, 0.97f);
    em::Vec3 gain = em::Vec3(0.96f, 1.00f, 1.06f);
    float sanity = 1.0f;
    float distortion = 0.0f;
    float pulse = 0.0f;
    float flashWhite = 0.0f;
    float fade = 1.0f;
    float scanline = 0.0f;
    float ssrStrength = 0.85f;
    float fogStrength = 1.0f;
};

struct QualitySettings {
    bool ssao = true;
    bool ssr = true;
    bool volumetric = true;
    bool bloom = true;
    bool fxaa = true;
    bool shadows = true;
    int shadowTileSize = 1024;
    int volumetricSteps = 40;
    int ssrSteps = 32;
    int maxShadowLights = 12;
    int maxVolumetricLights = 6;
    int ssaoSamples = 24;
    float renderScale = 1.0f;
    int maxRenderPixels = 0;
    int preset = 2;

    void applyPreset(int p);
    static int detectPreset();
};

struct RenderStats {
    int drawCalls = 0;
    int shadowDraws = 0;
    int lights = 0;
    int shadowedLights = 0;
    int culled = 0;
    int triangles = 0;
};

class Renderer {
public:
    bool init(int width, int height, const QualitySettings& quality);
    void shutdown();
    void resize(int width, int height);
    void setQuality(const QualitySettings& q);
    const QualitySettings& quality() const { return quality_; }

    void beginFrame(const CameraData& cam, float time, float dt);
    void submit(const DrawCall& dc);
    void submitLight(const RenderLight& l);
    void render();

    MaterialLibrary& materials() { return matLib; }
    const MaterialLibrary& materials() const { return matLib; }
    AtmosphereParams& atmosphere() { return atmos; }
    SkyParams& sky() { return skyParams; }
    TerrainParams& terrainParams() { return terrainCfg; }
    void submitTerrain(const DrawCall& dc);
    PostParams& post() { return postParams; }
    const RenderStats& stats() const { return stats_; }
    bool reloadShaders();
    void setDebugView(int v) { debugView = v; }
    int debugViewMode() const { return debugView; }

    int width() const { return screenW; }
    int height() const { return screenH; }
    int renderWidth() const { return renderW; }
    int renderHeight() const { return renderH; }
    GLuint sceneDepthTexture() const { return gbuffer.depthTex(); }
    const CameraData& camera() const { return cam_; }

private:
    void createTargets();
    void destroyTargets();
    bool loadShaders();
    void drawFullscreen();
    void shadowPass();
    void geometryPass();
    void ssaoPass();
    void lightingPass();
    void forwardPass();
    void ssrPass();
    void volumetricPass();
    void compositePass();
    void bloomPass();
    void postPass();
    void uploadLights(Shader& sh);
    void uploadVolumetricLights(Shader& sh);
    void buildSSAOKernel();
    void assignShadowSlots();

    QualitySettings quality_;
    AtmosphereParams atmos;
    SkyParams skyParams;
    TerrainParams terrainCfg;
    PostParams postParams;
    RenderStats stats_;
    MaterialLibrary matLib;
    CameraData cam_;

    Shader shGBuffer, shShadow, shLighting, shSSAO, shBlur, shSSR;
    Shader shVolumetric, shComposite, shBloomPre, shBloomDown, shBloomUp;
    Shader shPost, shFXAA, shForward, shTerrain;

    Framebuffer gbuffer, hdrA, hdrB, ssaoFB, ssaoBlurFB, ssrFB, fogFB, fogBlurFB, ldrFB, shadowFB;
    Framebuffer bloomFB[kBloomMips];

    GLuint emptyVAO = 0;
    GLuint whiteTex = 0;

    std::vector<DrawCall> opaque, transparent, shadowCasters, terrainDraws;
    std::vector<RenderLight> lights;
    std::vector<int> shadowLights;
    em::Mat4 shadowMatrices[kMaxShadows];

    float ssaoKernel[kSSAOKernel * 3];
    float time_ = 0.0f, dt_ = 0.0f;
    u64 frameIndex = 0;
    int screenW = 0, screenH = 0;
    int renderW = 0, renderH = 0;
    int halfW = 0, halfH = 0;
    int shadowAtlasSize = 4096;
    int debugView = 0;
    bool initialized = false;
};

}
