#pragma once

#include "JonContextBuilder.hpp"

namespace sf {

enum class JonUrgency : u32 {
    Ambient = 0,
    Notice,
    Caution,
    Warning,
    Critical
};

struct JonUtterance {
    std::string text;
    JonUrgency urgency = JonUrgency::Ambient;
    f64 lifetimeSeconds = 7.0;
    bool fromBridge = false;
};

struct JonMissionOffer {
    std::string title;
    std::string description;
    std::string objective;
    f64 rewardCredits = 0.0;
    u32 difficulty = 1;
};

class JonOfflineBrain {
public:
    void reset(u64 seed);

    std::vector<JonUtterance> evaluateThreats(const JonWorldContext& context, f64 stepSeconds);
    JonUtterance analysePlanet(const JonWorldContext& context) const;
    JonUtterance explainDiscovery(const std::string& subject, const JonWorldContext& context) const;
    JonUtterance respondToMessage(const std::string& message, const JonWorldContext& context) const;
    JonMissionOffer generateMission(const JonWorldContext& context, u64 salt) const;
    std::string recommendLandingSite(const JonWorldContext& context) const;
    std::string navigationAdvice(const JonWorldContext& context) const;

    void rememberDiscovery(const std::string& name);
    const std::vector<std::string>& discoveries() const { return rememberedDiscoveries; }
    u32 conversationCount() const { return exchanges; }

private:
    bool shouldRepeat(const std::string& key, f64 minimumIntervalSeconds);
    void advanceCooldowns(f64 stepSeconds);

    std::vector<std::string> rememberedDiscoveries;
    std::vector<std::pair<std::string, f64>> cooldowns;
    u64 randomSeed = 1;
    mutable u32 exchanges = 0;
};

}
