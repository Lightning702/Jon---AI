#pragma once

#include "../core/StringId.hpp"
#include "../math/DVec3.hpp"

#include <string>

namespace sf {

enum class EventKind : u32 {
    GameStateChanged = 0,
    ShipDamaged,
    ShipDestroyed,
    SystemEntered,
    PlanetLanded,
    PlanetLeft,
    HyperjumpStarted,
    HyperjumpFinished,
    HyperjumpDenied,
    VoidZoneChanged,
    TimeDilationChanged,
    StationDiscovered,
    ResourceCollected,
    ResearchUnlocked,
    MissionOffered,
    MissionAdvanced,
    MissionCompleted,
    JonSpoke,
    JonWarning,
    CoopPlayerJoined,
    CoopPlayerLeft,
    ScanCompleted,
    DockingGranted,
    HullStress,
    Count
};

struct Event {
    EventKind kind = EventKind::GameStateChanged;
    StringId subject;
    f64 numericValue = 0.0;
    f64 secondaryValue = 0.0;
    DVec3 location = DVec3::zero();
    std::string text;
};

const char* eventKindName(EventKind kind);

}
