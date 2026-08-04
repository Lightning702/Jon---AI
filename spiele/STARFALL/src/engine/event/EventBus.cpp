#include "EventBus.hpp"

namespace sf {
namespace {

constexpr usize kHistoryLimit = 96;

}

const char* eventKindName(EventKind kind) {
    switch (kind) {
        case EventKind::GameStateChanged: return "spielzustand";
        case EventKind::ShipDamaged: return "schiff_beschaedigt";
        case EventKind::ShipDestroyed: return "schiff_zerstoert";
        case EventKind::SystemEntered: return "system_betreten";
        case EventKind::PlanetLanded: return "gelandet";
        case EventKind::PlanetLeft: return "gestartet";
        case EventKind::HyperjumpStarted: return "sprung_start";
        case EventKind::HyperjumpFinished: return "sprung_ende";
        case EventKind::HyperjumpDenied: return "sprung_verweigert";
        case EventKind::VoidZoneChanged: return "void_zone";
        case EventKind::TimeDilationChanged: return "zeitdilatation";
        case EventKind::StationDiscovered: return "station_entdeckt";
        case EventKind::ResourceCollected: return "ressource";
        case EventKind::ResearchUnlocked: return "forschung";
        case EventKind::MissionOffered: return "mission_angeboten";
        case EventKind::MissionAdvanced: return "mission_fortschritt";
        case EventKind::MissionCompleted: return "mission_erfuellt";
        case EventKind::JonSpoke: return "jon_spricht";
        case EventKind::JonWarning: return "jon_warnung";
        case EventKind::CoopPlayerJoined: return "koop_beitritt";
        case EventKind::CoopPlayerLeft: return "koop_austritt";
        case EventKind::ScanCompleted: return "scan_fertig";
        case EventKind::DockingGranted: return "andocken_frei";
        case EventKind::HullStress: return "rumpfbelastung";
        case EventKind::Count: return "unbekannt";
    }
    return "unbekannt";
}

EventBus& EventBus::instance() {
    static EventBus bus;
    return bus;
}

u32 EventBus::subscribe(EventKind kind, EventListener listener) {
    std::lock_guard<std::mutex> lock(mutex);
    Subscription entry;
    entry.id = nextId++;
    entry.kind = kind;
    entry.everything = false;
    entry.listener = std::move(listener);
    subscriptions.push_back(std::move(entry));
    return subscriptions.back().id;
}

u32 EventBus::subscribeAll(EventListener listener) {
    std::lock_guard<std::mutex> lock(mutex);
    Subscription entry;
    entry.id = nextId++;
    entry.everything = true;
    entry.listener = std::move(listener);
    subscriptions.push_back(std::move(entry));
    return subscriptions.back().id;
}

void EventBus::unsubscribe(u32 subscriptionId) {
    std::lock_guard<std::mutex> lock(mutex);
    for (usize index = 0; index < subscriptions.size(); ++index) {
        if (subscriptions[index].id != subscriptionId) continue;
        subscriptions.erase(subscriptions.begin() + static_cast<isize>(index));
        return;
    }
}

void EventBus::publish(const Event& event) {
    std::lock_guard<std::mutex> lock(mutex);
    queue.push_back(event);
}

void EventBus::publishImmediate(const Event& event) {
    std::vector<EventListener> targets;
    {
        std::lock_guard<std::mutex> lock(mutex);
        for (const Subscription& entry : subscriptions) {
            if (entry.everything || entry.kind == event.kind) targets.push_back(entry.listener);
        }
        history.push_back(event);
        if (history.size() > kHistoryLimit) history.erase(history.begin());
    }
    for (const EventListener& listener : targets) listener(event);
}

void EventBus::dispatchQueued() {
    std::vector<Event> pending;
    {
        std::lock_guard<std::mutex> lock(mutex);
        pending.swap(queue);
    }
    for (const Event& event : pending) publishImmediate(event);
}

void EventBus::clear() {
    std::lock_guard<std::mutex> lock(mutex);
    queue.clear();
    history.clear();
}

usize EventBus::queuedCount() const {
    std::lock_guard<std::mutex> lock(mutex);
    return queue.size();
}

}
