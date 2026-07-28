#pragma once

#include "WorldTypes.h"
#include "../physics/PhysicsWorld.h"
#include "../render/Renderer.h"

namespace echo {

struct WorldConfig {
    u64 seed = 1337;
    int floors = 4;
    float floorWidth = 92.0f;
    float floorDepth = 66.0f;
    float cellSize = 0.5f;
    float wallThickness = 0.14f;
    float ceilingHeight = 3.10f;
};

struct DoorSoundEvent {
    em::Vec3 position;
    int kind = 0;
    float volume = 1.0f;
};

class World {
public:
    void generate(const WorldConfig& cfg, PropLibrary& props);
    void destroy();

    void update(float dt, float time, const em::Vec3& listener);
    void collectRender(Renderer& renderer, const CameraData& cam, float maxDistance);

    PhysicsWorld& physics() { return phys; }
    const PhysicsWorld& physics() const { return phys; }

    std::vector<Room>& rooms() { return roomList; }
    const std::vector<Room>& rooms() const { return roomList; }
    std::vector<Door>& doors() { return doorList; }
    const std::vector<Door>& doors() const { return doorList; }
    std::vector<LightFixture>& lights() { return lightList; }
    const std::vector<LightFixture>& lights() const { return lightList; }
    std::vector<PropInstance>& props() { return propList; }
    const std::vector<PropInstance>& props() const { return propList; }
    std::vector<Interactable>& interactables() { return interactList; }
    const std::vector<Interactable>& interactables() const { return interactList; }
    const std::vector<FloorPlan>& floors() const { return floorList; }
    const std::vector<ElevatorCab>& cabs() const { return cabList; }
    std::vector<ElevatorCab>& cabs() { return cabList; }
    int cabContaining(const em::Vec3& p) const;
    int cabOnFloor(int shaft, int floor) const;
    int shaftCount() const { return 2; }

    int roomAt(const em::Vec3& position) const;
    int floorAt(float y) const;
    em::Vec3 spawnPoint() const { return spawn; }
    float spawnYaw() const { return spawnFacing; }
    em::Vec3 randomPointInRoom(int room, em::Rng& rng) const;
    em::Vec3 roomCenter(int room) const;

    void setDoorOpen(int doorId, bool open);
    void toggleDoor(int doorId);
    bool doorBlocked(int doorId, const em::Vec3& actorPos, float radius) const;
    void setLightOn(int lightId, bool on, bool immediate = false);
    void breakLight(int lightId, bool immediate = false);
    void setRoomLights(int room, bool on, bool immediate = false);
    void setObserver(const em::Vec3& eye, const em::Vec3& forward);
    bool lightObserved(int lightId) const;

    void moveProp(int propId, const em::Vec3& newPos, float newYaw);
    void restoreProp(int propId);
    void hideProp(int propId, bool hidden);

    void extendCorridor(int room, float amount);
    void sealDoor(int doorId, bool sealed);
    void refreshCollider(int propId);

    bool consumeSound(DoorSoundEvent& out);
    void queueSound(const em::Vec3& pos, int kind, float volume);

    float ambientOcclusionAt(const em::Vec3& p) const;
    float lightLevelAt(const em::Vec3& p) const;
    bool insideVisibleRoom(const em::Vec3& p, const em::Vec3& viewPos) const;

    int findNearestInteractable(const em::Vec3& origin, const em::Vec3& dir, float maxDist, float maxAngle) const;
    bool interactableVisible(const em::Vec3& origin, const Interactable& it) const;
    int doorInFront(const em::Vec3& origin, const em::Vec3& dir, float maxDist) const;
    int findRoomOfType(int type, int floor) const;
    std::vector<int> roomsOfType(int type) const;
    int doorBetween(int roomA, int roomB) const;
    bool canLockDoor(int doorId) const;
    bool roomHasOpenExit(int roomId) const;
    int startRoom() const { return startRoomId; }
    bool hasStartVent() const { return ventBuilt; }
    em::Vec3 ventKeyPosition() const { return ventKeyPos; }
    em::Vec3 ventEntrance() const { return ventEntrancePos; }

    const std::vector<int>& visibleRooms() const { return visibleList; }
    int totalTriangles() const { return triangleCount; }

private:
    struct DoorSpot {
        int a = -1, b = -1;
        bool vertical = false;
        int fixed = 0, start = 0, end = 0;
        float length = 0.0f;
    };

    void buildLayout(em::Rng& rng);
    void buildFloorLayout(int floorIndex, em::Rng& rng);
    int createDoorAt(const DoorSpot& spot, em::Rng& rng, bool guaranteed);
    void connectFloor(int floorIndex, std::vector<DoorSpot>& spots, em::Rng& rng);
    void pickStartRoom();
    void buildStartVent(int roomId, MeshBuilder& mb);
    void chooseSpawn();
    void rasterizeRooms(int floorIndex);
    void buildWalls(int floorIndex, em::Rng& rng);
    void buildSectorMesh(int roomId, PropLibrary& props, em::Rng& rng);
    void populateRoom(int roomId, PropLibrary& props, em::Rng& rng);
    void resolveProps(int roomId, PropLibrary& props, em::Rng& rng);
    void placeLights(int roomId, em::Rng& rng);
    void createColliders(PropLibrary& props);
    void createDoorInteractables();
    void assignMaterials(Room& room, em::Rng& rng);
    void computeVisibility(const CameraData& cam, float maxDistance);
    void buildPortals();

    int cellIndex(int floorIndex, int cx, int cz) const;
    int cellRoom(int floorIndex, int cx, int cz) const;
    void setCellRoom(int floorIndex, int cx, int cz, int room);

    WorldConfig config;
    PhysicsWorld phys;
    std::vector<Room> roomList;
    std::vector<Door> doorList;
    std::vector<LightFixture> lightList;
    std::vector<PropInstance> propList;
    std::vector<Interactable> interactList;
    std::vector<FloorPlan> floorList;
    std::vector<ElevatorCab> cabList;
    std::vector<Sector> sectors;
    std::vector<std::vector<int>> grids;
    std::vector<DoorSoundEvent> soundQueue;
    std::vector<int> visibleList;
    PropLibrary* propLib = nullptr;
    Ref<Mesh> doorLeaf;
    void buildDoorLeaf();

    int gridW = 0, gridH = 0;
    em::Vec3 observerEye;
    em::Vec3 observerDir = em::Vec3(0, 0, -1);
    em::Vec3 spawn = em::Vec3(0, 0, 0);
    float spawnFacing = 0.0f;
    int startRoomId = -1;
    bool ventBuilt = false;
    em::Vec3 ventKeyPos;
    em::Vec3 ventEntrancePos;
    em::AABB ventInterior;
    int triangleCount = 0;
    float worldTime = 0.0f;
};

}
