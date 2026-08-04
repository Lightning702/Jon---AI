#include "JonCompanion.hpp"

#include "../../engine/core/Log.hpp"
#include "../../engine/math/Scalar.hpp"
#include "../../engine/net/Socket.hpp"

namespace sf {
namespace {

constexpr usize kMaximumVisibleMessages = 4;

}

JonCompanion::~JonCompanion() {
    shutdown();
}

void JonCompanion::initialize(u64 seed, const JonBridgeSettings& settings) {
    offlineBrain.reset(seed);
    bridge = settings;
    visible.clear();
    elapsed = 0.0;
    logInfo("jon", "Begleiter bereit, Bruecke %s", bridge.enabled ? "aktiv" : "deaktiviert");
}

void JonCompanion::shutdown() {
    if (worker.joinable()) worker.join();
    visible.clear();
}

std::string JonCompanion::extractStreamedAnswer(const std::string& responseBody) {
    std::string answer;
    usize cursor = 0;
    while (cursor < responseBody.size()) {
        const usize lineEnd = responseBody.find('\n', cursor);
        const std::string line = responseBody.substr(cursor, lineEnd == std::string::npos ? std::string::npos
                                                                                         : lineEnd - cursor);
        cursor = lineEnd == std::string::npos ? responseBody.size() : lineEnd + 1;
        if (line.compare(0, 6, "data: ") != 0) continue;
        const JsonValue event = JsonValue::parse(line.substr(6));
        if (event["type"].text() != "content") continue;
        answer += event["delta"].text();
    }
    if (answer.empty()) {
        const JsonValue direct = JsonValue::parse(responseBody);
        answer = direct["content"].text(direct["answer"].text());
    }
    return answer;
}

void JonCompanion::launchBridgeRequest(const std::string& message, const JonWorldContext& context) {
    if (!bridge.enabled) return;
    if (requestActive.exchange(true, std::memory_order_acq_rel)) return;
    if (worker.joinable()) worker.join();

    const std::string payload = contextBuilder.buildRequestPayload(context, message).serialize();
    const JonBridgeSettings settings = bridge;

    worker = std::thread([this, payload, settings]() {
        const HttpClient::Response response =
            HttpClient::post(settings.host, settings.port, settings.path, "application/json", payload,
                             settings.timeoutMilliseconds);
        std::string answer;
        if (response.ok()) answer = extractStreamedAnswer(response.body);

        bridgeReachable.store(response.statusCode > 0, std::memory_order_relaxed);
        if (!answer.empty()) {
            std::lock_guard<std::mutex> lock(resultMutex);
            pendingAnswer = answer.size() > 480 ? answer.substr(0, 480) : answer;
            answerReady.store(true, std::memory_order_release);
        }
        requestActive.store(false, std::memory_order_release);
    });
}

void JonCompanion::collectBridgeResult() {
    if (!answerReady.load(std::memory_order_acquire)) return;
    std::string answer;
    {
        std::lock_guard<std::mutex> lock(resultMutex);
        answer.swap(pendingAnswer);
    }
    answerReady.store(false, std::memory_order_release);
    if (answer.empty()) return;

    JonUtterance utterance;
    utterance.text = answer;
    utterance.urgency = JonUrgency::Notice;
    utterance.lifetimeSeconds = 14.0;
    utterance.fromBridge = true;
    say(utterance);
}

void JonCompanion::say(const JonUtterance& utterance) {
    visible.push_back(utterance);
    while (visible.size() > kMaximumVisibleMessages) visible.erase(visible.begin());
    pulse = 1.0f;
}

void JonCompanion::update(const JonWorldContext& context, f64 stepSeconds) {
    elapsed += stepSeconds;
    pulse = static_cast<f32>(exponentialApproach(static_cast<f64>(pulse), 0.22, 1.6, stepSeconds));

    for (usize index = visible.size(); index > 0; --index) {
        JonUtterance& utterance = visible[index - 1];
        utterance.lifetimeSeconds -= stepSeconds;
        if (utterance.lifetimeSeconds <= 0.0) {
            visible.erase(visible.begin() + static_cast<isize>(index - 1));
        }
    }

    for (const JonUtterance& threat : offlineBrain.evaluateThreats(context, stepSeconds)) {
        say(threat);
    }
    collectBridgeResult();
}

void JonCompanion::ask(const std::string& message, const JonWorldContext& context) {
    say(offlineBrain.respondToMessage(message, context));
    launchBridgeRequest(message, context);
}

void JonCompanion::announceDiscovery(const std::string& subject, const JonWorldContext& context) {
    offlineBrain.rememberDiscovery(subject);
    say(offlineBrain.explainDiscovery(subject, context));
}

void JonCompanion::requestMission(const JonWorldContext& context) {
    lastOffer = offlineBrain.generateMission(context, static_cast<u64>(elapsed * 1000.0));
    JonUtterance utterance;
    utterance.text = lastOffer.title + ": " + lastOffer.description + " Ziel: " + lastOffer.objective;
    utterance.urgency = JonUrgency::Notice;
    utterance.lifetimeSeconds = 16.0;
    say(utterance);
}

}
