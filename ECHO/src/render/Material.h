#pragma once

#include "Texture.h"

namespace echo {

enum MaterialId {
    MAT_TILE_WALL = 0,
    MAT_TILE_WALL_GREEN,
    MAT_TILE_WALL_WHITE,
    MAT_PLASTER,
    MAT_PAINT_WALL,
    MAT_CONCRETE_WALL,
    MAT_FLOOR_CHECKER,
    MAT_FLOOR_LINO,
    MAT_CONCRETE_FLOOR,
    MAT_TILE_FLOOR_SMALL,
    MAT_CEILING_TILE,
    MAT_CEILING_CONCRETE,
    MAT_METAL_PAINTED,
    MAT_METAL_RUST,
    MAT_STEEL,
    MAT_VENT_GRATE,
    MAT_WOOD_DOOR,
    MAT_WOOD_OLD,
    MAT_DOOR_GREEN,
    MAT_DOOR_METAL,
    MAT_FABRIC,
    MAT_MATTRESS,
    MAT_CURTAIN,
    MAT_RUBBER,
    MAT_PLASTIC_WHITE,
    MAT_GLASS,
    MAT_PAPER,
    MAT_MORGUE_STEEL,
    MAT_SERVER_RACK,
    MAT_LIGHT_PANEL,
    MAT_SKIN,
    MAT_HAIR,
    MAT_CLOTH_WHITE,
    MAT_CLOTH_SCRUB,
    MAT_COUNT
};

struct MaterialDef {
    int layer = 0;
    em::Vec2 uvScale = em::Vec2(1, 1);
    em::Vec3 tint = em::Vec3(1, 1, 1);
    float roughnessScale = 1.0f;
    float metallicScale = 1.0f;
    float normalStrength = 1.0f;
    em::Vec3 emissive = em::Vec3(0, 0, 0);
    float emissiveStrength = 0.0f;
    float wetness = 0.0f;
    float alpha = 1.0f;
    bool transparent = false;
    bool doubleSided = false;
};

class MaterialLibrary {
public:
    void generate(int resolution);
    void destroy();

    const MaterialDef& def(int id) const { return defs[id < 0 || id >= MAT_COUNT ? 0 : id]; }
    MaterialDef& mutableDef(int id) { return defs[id < 0 || id >= MAT_COUNT ? 0 : id]; }

    GLuint albedoArray() const { return albedo ? albedo->id() : 0; }
    GLuint normalArray() const { return normal ? normal->id() : 0; }
    GLuint ormArray() const { return orm ? orm->id() : 0; }
    GLuint noiseTexture() const { return noise ? noise->id() : 0; }
    GLuint blueNoiseTexture() const { return blueNoise ? blueNoise->id() : 0; }

    void bind(int albedoUnit, int normalUnit, int ormUnit) const;
    void uploadUniforms(class Shader& shader) const;

private:
    Ref<Texture> albedo, normal, orm, noise, blueNoise;
    MaterialDef defs[MAT_COUNT];
    int res = 512;
};

}
