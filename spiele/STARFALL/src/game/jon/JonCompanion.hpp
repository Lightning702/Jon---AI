#pragma once

#include "JonOfflineBrain.hpp"

#include <atomic>
#include <memory>
#include <mutex>
#include <thread>

namespace sf {

struct JonBridgeSettings {
    std::string host = "127.0.0.1";
    u16 port = 8756;
    std::string path = "/api/chat";
    u32 timeoutMilliseconds = 4000;
    bool enabled = true;
};

class JonCompanion {
public:
    JonCompanion() = default;
    ~JonCompanion();

    void initialize(u64 seed, const JonBridgeSettings& settings);
    void shutdown();

    void update(const JonWorldContext& context, f64 stepSeconds);
    void ask(const std::string& message, const JonWorldContext& context);
    void announceDiscovery(const std::string& subject, const JonWorldContext& context);
    void requestMission(const JonWorldContext& context);
    void say(const JonUtterance& utterance);

    const std::vector<JonUtterance>& activeMessages() const { return visible; }
    const JonMissionOffer& latestMissionOffer() const { return lastOffer; }
    bool bridgeOnline() const { return bridgeReachable.load(std::memory_order_relaxed); }
    bool bridgeBusy() const { return requestActive.load(std::memory_order_relaxed); }
    JonOfflineBrain& brain() { return offlineBrain; }
    f32 hologramPulse() const { return pulse; }

    static std::string extractStreamedAnswer(const std::string& responseBody);

private:
    void launchBridgeRequest(const std::string& message, const JonWorldContext& context);
    void collectBridgeResult();

    JonOfflineBrain offlineBrain;
    JonContextBuilder contextBuilder;
    JonBridgeSettings bridge;
    JonMissionOffer lastOffer;

    std::vector<JonUtterance> visible;
    std::mutex resultMutex;
    std::string pendingAnswer;
    std::atomic<bool> answerReady{false};
    std::atomic<bool> requestActive{false};
    std::atomic<bool> bridgeReachable{false};
    std::thread worker;
    f32 pulse = 0.0f;
    f64 elapsed = 0.0;
};

}
