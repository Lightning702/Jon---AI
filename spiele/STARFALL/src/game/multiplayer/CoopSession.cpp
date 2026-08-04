#include "CoopSession.hpp"

#include "../../engine/core/Log.hpp"
#include "../../engine/core/Time.hpp"
#include "../../engine/math/Random.hpp"
#include "../../engine/math/Scalar.hpp"

namespace sf {
namespace {

constexpr f64 kSendInterval = 1.0 / 20.0;
constexpr f64 kInterpolationDelay = 0.1;

JsonValue vectorToJson(const DVec3& value) {
    JsonValue array = JsonValue::makeArray();
    array.push(JsonValue(value.x));
    array.push(JsonValue(value.y));
    array.push(JsonValue(value.z));
    return array;
}

DVec3 vectorFromJson(const JsonValue& value) {
    if (value.size() < 3) return DVec3::zero();
    return DVec3(value.at(0).number(), value.at(1).number(), value.at(2).number());
}

Quat quaternionFromJson(const JsonValue& value) {
    if (value.size() < 4) return Quat::identity();
    return normalize(Quat(static_cast<f32>(value.at(0).number()), static_cast<f32>(value.at(1).number()),
                          static_cast<f32>(value.at(2).number()), static_cast<f32>(value.at(3).number())));
}

JsonValue quaternionToJson(const Quat& value) {
    JsonValue array = JsonValue::makeArray();
    array.push(JsonValue(static_cast<f64>(value.x)));
    array.push(JsonValue(static_cast<f64>(value.y)));
    array.push(JsonValue(static_cast<f64>(value.z)));
    array.push(JsonValue(static_cast<f64>(value.w)));
    return array;
}

SystemCoord systemFromJson(const JsonValue& value) {
    SystemCoord coordinate;
    if (value.size() >= 3) {
        coordinate.x = value.at(0).integer();
        coordinate.y = value.at(1).integer();
        coordinate.z = value.at(2).integer();
    }
    return coordinate;
}

JsonValue systemToJson(const SystemCoord& value) {
    JsonValue array = JsonValue::makeArray();
    array.push(JsonValue(static_cast<f64>(value.x)));
    array.push(JsonValue(static_cast<f64>(value.y)));
    array.push(JsonValue(static_cast<f64>(value.z)));
    return array;
}

}

CoopSession::~CoopSession() {
    leave();
}

void CoopSession::configure(const std::string& host, u16 port, const std::string& playerName) {
    serverHost = host;
    serverPort = port;
    playerLabel = playerName.empty() ? std::string("Pilot") : playerName;
    Random random(hashCombine(wallClockUnixSeconds(), static_cast<u64>(port)));
    char buffer[32];
    std::snprintf(buffer, sizeof(buffer), "sf%08x", random.nextUnsigned32());
    playerId = buffer;
}

void CoopSession::hostGame(u64 universeSeed) {
    leave();
    wantHost = true;
    seed = universeSeed;
    code.clear();
    lastError.clear();
    status = "Verbinde mit dem Jon-Koop-Server";
    currentPhase = CoopPhase::Connecting;
    stopRequested.store(false, std::memory_order_release);
    worker = std::thread(&CoopSession::connectionThread, this, serverHost, serverPort);
}

void CoopSession::joinGame(const std::string& invitationCode) {
    leave();
    wantHost = false;
    code = invitationCode;
    lastError.clear();
    status = "Trete Sitzung bei";
    currentPhase = CoopPhase::Connecting;
    stopRequested.store(false, std::memory_order_release);
    worker = std::thread(&CoopSession::connectionThread, this, serverHost, serverPort);
}

void CoopSession::leave() {
    stopRequested.store(true, std::memory_order_release);
    if (worker.joinable()) worker.join();
    socket.disconnect();
    connected.store(false, std::memory_order_release);
    currentPhase = CoopPhase::Offline;
    roster.clear();
    others.clear();
    handshakeSent = false;
    {
        std::lock_guard<std::mutex> lock(incomingMutex);
        incoming.clear();
    }
    {
        std::lock_guard<std::mutex> lock(outgoingMutex);
        outgoing.clear();
    }
}

bool CoopSession::inSession() const {
    return currentPhase == CoopPhase::Lobby || currentPhase == CoopPhase::Loading ||
           currentPhase == CoopPhase::Playing;
}

void CoopSession::connectionThread(std::string host, u16 port) {
    TcpSocket connection;
    const Status opened = connection.connectTo(host, port, 3000);
    if (!opened.ok()) {
        lastError = opened.detail;
        status = "Koop-Server nicht erreichbar";
        currentPhase = CoopPhase::Failed;
        return;
    }
    connected.store(true, std::memory_order_release);

    std::string receiveBuffer;
    char chunk[4096];
    while (!stopRequested.load(std::memory_order_acquire)) {
        {
            std::vector<std::string> pending;
            {
                std::lock_guard<std::mutex> lock(outgoingMutex);
                pending.swap(outgoing);
            }
            for (const std::string& line : pending) {
                if (!connection.sendLine(line)) {
                    stopRequested.store(true, std::memory_order_release);
                    break;
                }
            }
        }

        const i32 received = connection.receiveSome(chunk, sizeof(chunk), 40);
        if (received < 0) break;
        if (received > 0) {
            receiveBuffer.append(chunk, static_cast<usize>(received));
            usize newline = receiveBuffer.find('\n');
            while (newline != std::string::npos) {
                std::string line = receiveBuffer.substr(0, newline);
                receiveBuffer.erase(0, newline + 1);
                if (!line.empty()) {
                    std::lock_guard<std::mutex> lock(incomingMutex);
                    incoming.push_back(line);
                }
                newline = receiveBuffer.find('\n');
            }
        }
    }

    connection.disconnect();
    connected.store(false, std::memory_order_release);
    if (currentPhase != CoopPhase::Offline && currentPhase != CoopPhase::Failed) {
        currentPhase = CoopPhase::Lost;
        status = "Verbindung verloren";
    }
}

void CoopSession::queueOutgoing(const JsonValue& message) {
    std::lock_guard<std::mutex> lock(outgoingMutex);
    outgoing.push_back(message.serialize());
}

void CoopSession::sendHandshake() {
    JsonValue message = JsonValue::makeObject();
    message.set("type", std::string(wantHost ? "host" : "join"));
    message.set("game", std::string("starfall"));
    message.set("player", playerId);
    message.set("name", playerLabel);
    if (wantHost) {
        message.set("seed", static_cast<f64>(seed));
    } else {
        message.set("code", code);
    }
    queueOutgoing(message);
    handshakeSent = true;
}

void CoopSession::setReady(bool value) {
    JsonValue message = JsonValue::makeObject();
    message.set("type", std::string("ready"));
    message.set("player", playerId);
    message.set("ready", value);
    queueOutgoing(message);
}

void CoopSession::requestStart() {
    JsonValue message = JsonValue::makeObject();
    message.set("type", std::string("start"));
    message.set("player", playerId);
    queueOutgoing(message);
}

void CoopSession::sendChat(const std::string& text) {
    if (text.empty()) return;
    JsonValue message = JsonValue::makeObject();
    message.set("type", std::string("chat"));
    message.set("player", playerId);
    message.set("text", text);
    queueOutgoing(message);
}

void CoopSession::pushLocalState(const CoopLocalState& state) {
    local = state;
}

CoopRemotePlayer* CoopSession::findRemote(const std::string& id) {
    for (CoopRemotePlayer& remote : others) {
        if (remote.id == id) return &remote;
    }
    others.push_back(CoopRemotePlayer());
    others.back().id = id;
    return &others.back();
}

void CoopSession::applyRoster(const JsonValue& lobby) {
    roster.clear();
    const JsonValue& players = lobby["players"];
    for (usize index = 0; index < players.size(); ++index) {
        const JsonValue& entry = players.at(index);
        CoopMember member;
        member.id = entry["id"].text();
        member.name = entry["name"].text("Pilot");
        member.host = entry["host"].boolean();
        member.ready = entry["ready"].boolean();
        member.online = entry["online"].boolean(true);
        member.slot = static_cast<i32>(entry["slot"].integer());
        member.ping = static_cast<f32>(entry["ping"].number());
        roster.push_back(member);
        if (member.id == playerId) localPing = member.ping;
    }
    if (lobby.has("code")) code = lobby["code"].text();
    if (lobby.has("seed")) seed = static_cast<u64>(lobby["seed"].number());
}

void CoopSession::applySnapshot(const JsonValue& message) {
    const JsonValue& players = message["players"];
    const f64 stamp = message["time"].number(clock);
    for (usize index = 0; index < players.size(); ++index) {
        const JsonValue& entry = players.at(index);
        const std::string id = entry["id"].text();
        if (id.empty() || id == playerId) continue;
        CoopRemotePlayer* remote = findRemote(id);
        remote->name = entry["name"].text(remote->name);
        remote->slot = static_cast<i32>(entry["slot"].integer(remote->slot));
        remote->present = true;
        remote->system = systemFromJson(entry["system"]);

        CoopSample sample;
        sample.stamp = stamp;
        sample.position = vectorFromJson(entry["position"]);
        sample.velocity = vectorFromJson(entry["velocity"]);
        sample.orientation = quaternionFromJson(entry["orientation"]);
        remote->buffer.push_back(sample);
        while (remote->buffer.size() > 32) remote->buffer.erase(remote->buffer.begin());
    }
}

void CoopSession::handleMessage(const JsonValue& message) {
    const std::string kind = message["type"].text();
    if (kind == "lobby") {
        applyRoster(message);
        if (currentPhase == CoopPhase::Connecting) currentPhase = CoopPhase::Lobby;
        status = "Lobby " + code;
    } else if (kind == "start") {
        currentPhase = CoopPhase::Playing;
        status = "Sitzung laeuft";
        if (message.has("seed")) seed = static_cast<u64>(message["seed"].number());
    } else if (kind == "snapshot") {
        applySnapshot(message);
        if (currentPhase == CoopPhase::Lobby || currentPhase == CoopPhase::Loading) {
            currentPhase = CoopPhase::Playing;
        }
    } else if (kind == "chat") {
        chatLines.push_back(message["name"].text("Pilot") + ": " + message["text"].text());
        while (chatLines.size() > 64) {
            chatLines.erase(chatLines.begin());
            if (chatCursor > 0) --chatCursor;
        }
    } else if (kind == "leave") {
        const std::string id = message["player"].text();
        for (usize index = 0; index < others.size(); ++index) {
            if (others[index].id != id) continue;
            others.erase(others.begin() + static_cast<isize>(index));
            break;
        }
    } else if (kind == "error") {
        lastError = message["message"].text("Unbekannter Serverfehler");
        status = lastError;
        currentPhase = CoopPhase::Failed;
    }
}

void CoopSession::update(f64 stepSeconds) {
    clock += stepSeconds;

    if (connected.load(std::memory_order_acquire) && !handshakeSent) {
        sendHandshake();
    }

    std::vector<std::string> pending;
    {
        std::lock_guard<std::mutex> lock(incomingMutex);
        pending.swap(incoming);
    }
    for (const std::string& line : pending) {
        handleMessage(JsonValue::parse(line));
    }

    if (currentPhase == CoopPhase::Playing) {
        sendTimer += stepSeconds;
        if (sendTimer >= kSendInterval) {
            sendTimer = 0.0;
            JsonValue message = JsonValue::makeObject();
            message.set("type", std::string("state"));
            message.set("player", playerId);
            message.set("time", clock);
            message.set("position", vectorToJson(local.position));
            message.set("velocity", vectorToJson(local.velocity));
            message.set("orientation", quaternionToJson(local.orientation));
            message.set("system", systemToJson(local.system));
            message.set("dilation", local.timeDilation);
            message.set("hull", local.hullIntegrity);
            queueOutgoing(message);
        }
    }

    const f64 renderTime = clock - kInterpolationDelay;
    for (CoopRemotePlayer& remote : others) {
        if (remote.buffer.empty()) continue;
        if (remote.buffer.size() == 1) {
            remote.renderPosition = remote.buffer.back().position;
            remote.renderOrientation = remote.buffer.back().orientation;
            continue;
        }
        for (usize index = remote.buffer.size() - 1; index > 0; --index) {
            const CoopSample& newer = remote.buffer[index];
            const CoopSample& older = remote.buffer[index - 1];
            if (older.stamp > renderTime || newer.stamp < renderTime) continue;
            const f64 span = maxValue(newer.stamp - older.stamp, 1.0e-4);
            const f64 alpha = clampValue((renderTime - older.stamp) / span, 0.0, 1.0);
            remote.renderPosition = lerp(older.position, newer.position, alpha);
            remote.renderOrientation = slerp(older.orientation, newer.orientation, static_cast<f32>(alpha));
            break;
        }
    }
}

bool CoopSession::consumeChatLine(std::string& line) {
    if (chatCursor >= chatLines.size()) return false;
    line = chatLines[chatCursor++];
    return true;
}

}
