#pragma once

#include "EventTypes.hpp"

#include <functional>
#include <mutex>
#include <vector>

namespace sf {

using EventListener = std::function<void(const Event&)>;

class EventBus {
public:
    static EventBus& instance();

    u32 subscribe(EventKind kind, EventListener listener);
    u32 subscribeAll(EventListener listener);
    void unsubscribe(u32 subscriptionId);

    void publish(const Event& event);
    void publishImmediate(const Event& event);
    void dispatchQueued();
    void clear();

    usize queuedCount() const;
    const std::vector<Event>& recentHistory() const { return history; }

private:
    struct Subscription {
        u32 id = 0;
        EventKind kind = EventKind::Count;
        bool everything = false;
        EventListener listener;
    };

    mutable std::mutex mutex;
    std::vector<Subscription> subscriptions;
    std::vector<Event> queue;
    std::vector<Event> history;
    u32 nextId = 1;
};

}
