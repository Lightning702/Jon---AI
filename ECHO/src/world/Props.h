#pragma once

#include "../render/Mesh.h"
#include "../render/Material.h"

namespace echo {

enum PropType {
    PROP_BED = 0,
    PROP_GURNEY,
    PROP_CRIB,
    PROP_WHEELCHAIR,
    PROP_IV_STAND,
    PROP_MONITOR_CART,
    PROP_DEFIBRILLATOR,
    PROP_CABINET,
    PROP_FILE_CABINET,
    PROP_LOCKER,
    PROP_SHELF,
    PROP_DESK,
    PROP_TABLE,
    PROP_CHAIR,
    PROP_STOOL,
    PROP_BENCH,
    PROP_TROLLEY,
    PROP_BIN,
    PROP_SINK,
    PROP_TOILET,
    PROP_MIRROR,
    PROP_RADIATOR,
    PROP_PIPES,
    PROP_DUCT,
    PROP_CEILING_LAMP,
    PROP_WALL_LAMP,
    PROP_OR_LAMP,
    PROP_OR_TABLE,
    PROP_XRAY_MACHINE,
    PROP_MORGUE_WALL,
    PROP_SERVER_RACK,
    PROP_VENDING,
    PROP_CURTAIN,
    PROP_WINDOW,
    PROP_VENT_COVER,
    PROP_EXIT_SIGN,
    PROP_LIGHT_SWITCH,
    PROP_KEYPAD,
    PROP_PAPER_PILE,
    PROP_BOX,
    PROP_DEBRIS,
    PROP_DEAD_PLANT,
    PROP_TV,
    PROP_CLOCK,
    PROP_NOTICE_BOARD,
    PROP_STRETCHER,
    PROP_SPEAKER,
    PROP_KEYRING,
    PROP_BATTERY,
    PROP_CORPSE,
    PROP_COUNT
};

struct PropMesh {
    Mesh mesh;
    em::AABB bounds;
    em::Vec3 colliderHalf = em::Vec3(0.3f, 0.3f, 0.3f);
    em::Vec3 colliderOffset = em::Vec3(0, 0, 0);
    bool solid = true;
    bool hasTransparent = false;
    int transparentSub = -1;
};

class PropLibrary {
public:
    void build();
    void destroy();
    const PropMesh& get(int type) const { return props[type < 0 || type >= PROP_COUNT ? 0 : type]; }
    PropMesh& mutableGet(int type) { return props[type < 0 || type >= PROP_COUNT ? 0 : type]; }

private:
    PropMesh props[PROP_COUNT];
};

}
