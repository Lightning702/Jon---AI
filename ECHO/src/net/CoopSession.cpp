#include "CoopSession.h"
#include "../core/Log.h"
#include "../core/Time.h"

using namespace em;

namespace echo {

namespace {
const double kInterpDelay = 0.110;
const double kExtrapolateMax = 0.280;
const float kSendRate = 20.0f;
const int kIntentHost = 1;
const int kIntentJoin = 2;
const int kIntentResume = 3;

const char* kAnimNames[CANIM_COUNT] = {
    "idle", "walk", "run", "crouch", "sneak", "jump", "fall", "interact", "attack"
};

int animFromName(const std::string& name) {
    for (int i = 0; i < CANIM_COUNT; i++) {
        if (name == kAnimNames[i]) return i;
    }
    return CANIM_IDLE;
}

std::string trim(const std::string& text) {
    size_t a = 0, b = text.size();
    while (a < b && (text[a] == ' ' || text[a] == '\t' || text[a] == '\n' || text[a] == '\r')) a++;
    while (b > a && (text[b - 1] == ' ' || text[b - 1] == '\t' || text[b - 1] == '\n' || text[b - 1] == '\r')) b--;
    return text.substr(a, b - a);
}

std::string upper(const std::string& text) {
    std::string out = text;
    for (size_t i = 0; i < out.size(); i++) {
        if (out[i] >= 'a' && out[i] <= 'z') out[i] = (char)(out[i] - 32);
    }
    return out;
}
}

void CoopSession::init(const std::string& game, HumanRig* humanRig) {
    gameId = game;
    rig = humanRig;
    currentPhase = COOP_OFF;
    statusLine = "Nicht verbunden";
}

void CoopSession::shutdown() {
    client.disconnect();
    others.clear();
    roster.clear();
    worldState.clear();
    worldText.clear();
    currentPhase = COOP_OFF;
}

void CoopSession::setServer(const std::string& newHost, int newPort) {
    if (!newHost.empty()) {
        host = newHost;
        homeHost = newHost;
    }
    if (newPort > 0 && newPort < 65536) {
        port = newPort;
        homePort = newPort;
    }
}

double CoopSession::netNow() const {
    return clock + timeOffset;
}

Vec3 CoopSession::readVec(const js::Value& v) {
    return Vec3(v.get("x").asFloat(0.0f), v.get("y").asFloat(0.0f), v.get("z").asFloat(0.0f));
}

bool CoopSession::isHost() const {
    for (size_t i = 0; i < roster.size(); i++) {
        if (roster[i].id == playerId) return roster[i].host;
    }
    return wantHost;
}

void CoopSession::beginConnect() {
    handshakeSent = false;
    client.disconnect();
    client.connect(host, port);
}

bool CoopSession::applyRedirect() {
    if (!hasRedirect) return false;
    hasRedirect = false;
    host = redirectHost;
    port = redirectPort > 0 ? redirectPort : port;
    token.clear();
    playerId.clear();
    lastError.clear();
    roster.clear();
    others.clear();
    intent = kIntentJoin;
    wantHost = false;
    reconnectTries = 0;
    reconnectTimer = 0.0f;
    currentPhase = COOP_CONNECTING;
    statusLine = "Verbinde mit " + host + " ...";
    beginConnect();
    return true;
}

void CoopSession::hostGame(const std::string& name, u64 worldSeedValue, const Vec3& spawnPoint) {
    playerName = name.empty() ? std::string("Gastgeber") : name;
    playerModel = "host";
    seed = worldSeedValue;
    spawn = spawnPoint;
    wantHost = true;
    intent = kIntentHost;
    host = homeHost;
    port = homePort;
    token.clear();
    playerId.clear();
    lastError.clear();
    lobbyCode.clear();
    inviteText.clear();
    serverInvite.clear();
    hasRedirect = false;
    redirectHops = 0;
    roster.clear();
    others.clear();
    reconnectTries = 0;
    reconnectTimer = 0.0f;
    currentPhase = COOP_CONNECTING;
    statusLine = "Lobby wird erstellt ...";
    beginConnect();
}

void CoopSession::joinGame(const std::string& inviteCode, const std::string& name) {
    std::string text = trim(inviteCode);
    std::string codePart = text;
    host = homeHost;
    port = homePort;
    size_t at = text.find('@');
    if (at != std::string::npos) {
        codePart = text.substr(0, at);
        std::string address = trim(text.substr(at + 1));
        size_t colon = address.rfind(':');
        if (colon != std::string::npos) {
            std::string portText = address.substr(colon + 1);
            int parsed = std::atoi(portText.c_str());
            if (parsed > 0 && parsed < 65536) {
                port = parsed;
                address = address.substr(0, colon);
            }
        }
        if (!address.empty()) host = address;
    }

    std::string clean;
    for (size_t i = 0; i < codePart.size(); i++) {
        char c = codePart[i];
        if ((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9')) clean.push_back(c);
    }
    pendingCode = upper(clean);
    if (pendingCode.size() < 6) {
        lastError = "Code besteht aus 6 Zeichen";
        currentPhase = COOP_ERROR;
        return;
    }

    playerName = name.empty() ? std::string("Spieler 2") : name;
    playerModel = "guest";
    wantHost = false;
    intent = kIntentJoin;
    token.clear();
    playerId.clear();
    lastError.clear();
    lobbyCode.clear();
    inviteText.clear();
    serverInvite.clear();
    hasRedirect = false;
    redirectHops = 0;
    roster.clear();
    others.clear();
    reconnectTries = 0;
    reconnectTimer = 0.0f;
    currentPhase = COOP_CONNECTING;
    statusLine = "Suche Lobby " + pendingCode + " ...";
    beginConnect();
}

void CoopSession::leave() {
    if (client.online()) {
        js::Value msg = js::Value::object();
        msg.set("t", "leave");
        client.send(msg);
    }
    client.disconnect();
    others.clear();
    roster.clear();
    worldState.clear();
    worldText.clear();
    chatLines.clear();
    lobbyCode.clear();
    inviteText.clear();
    serverInvite.clear();
    hasRedirect = false;
    redirectHops = 0;
    host = homeHost;
    port = homePort;
    token.clear();
    playerId.clear();
    hasSpawn = false;
    spawnSignal = false;
    intent = 0;
    reconnectTries = 0;
    reconnectTimer = 0.0f;
    handshakeSent = false;
    forceSend = false;
    eventCursor = 0;
    lastSnapshot = 0;
    currentPhase = COOP_OFF;
    statusLine = "Nicht verbunden";
}

void CoopSession::sendHandshake() {
    handshakeSent = true;
    js::Value msg = js::Value::object();
    msg.set("name", playerName);
    msg.set("model", playerModel);
    msg.set("game", gameId);
    if (intent == kIntentResume && !token.empty()) {
        msg.set("t", "hello");
        msg.set("token", token);
    } else if (intent == kIntentHost) {
        msg.set("t", "create");
        msg.set("seed", (double)(seed & 0x7FFFFFFFULL));
        msg.set("max_players", 4);
        js::Value point = js::Value::object();
        point.set("x", spawn.x);
        point.set("y", spawn.y);
        point.set("z", spawn.z);
        msg.set("spawn", point);
    } else {
        msg.set("t", "join");
        msg.set("code", pendingCode);
    }
    client.send(msg);
}

void CoopSession::setReady(bool value) {
    js::Value msg = js::Value::object();
    msg.set("t", "ready");
    msg.set("value", value);
    client.send(msg);
}

void CoopSession::requestStart() {
    js::Value msg = js::Value::object();
    msg.set("t", "start");
    client.send(msg);
}

void CoopSession::closeLobby() {
    js::Value msg = js::Value::object();
    msg.set("t", "close");
    client.send(msg);
}

void CoopSession::reportLoaded() {
    js::Value msg = js::Value::object();
    msg.set("t", "scene");
    msg.set("phase", "ready");
    msg.set("scene", "world");
    client.send(msg);
}

void CoopSession::sendChat(const std::string& text) {
    if (text.empty()) return;
    js::Value msg = js::Value::object();
    msg.set("t", "chat");
    msg.set("text", text.substr(0, 240));
    client.send(msg);
}

void CoopSession::pushLocal(const CoopLocalState& state) {
    local = state;
}

void CoopSession::sendInteract(const std::string& kind, const std::string& id, double value, const Vec3& at) {
    if (!playing()) return;
    js::Value msg = js::Value::object();
    msg.set("t", "act");
    msg.set("kind", kind);
    msg.set("id", id);
    msg.set("value", value);
    msg.set("x", at.x);
    msg.set("y", at.y);
    msg.set("z", at.z);
    client.send(msg);
}

void CoopSession::sendCheckpoint(const js::Value& data) {
    if (!playing()) return;
    js::Value msg = js::Value::object();
    msg.set("t", "act");
    msg.set("kind", "checkpoint");
    msg.set("data", data);
    client.send(msg);
}

void CoopSession::sendEffect(const std::string& kind, const js::Value& data) {
    if (!playing()) return;
    js::Value msg = js::Value::object();
    msg.set("t", "fx");
    msg.set("kind", kind);
    msg.set("data", data);
    client.send(msg);
}

bool CoopSession::consumeSpawnSignal() {
    if (!spawnSignal) return false;
    spawnSignal = false;
    return true;
}

bool CoopSession::consumeChat(std::string& line) {
    if (chatLines.empty()) return false;
    line = chatLines.front();
    chatLines.erase(chatLines.begin());
    return true;
}

bool CoopSession::consumeWorldEvent(std::string& kind, std::string& key, double& value) {
    if (eventKinds.empty()) return false;
    kind = eventKinds.front();
    key = eventKeys.front();
    value = eventValues.front();
    eventKinds.erase(eventKinds.begin());
    eventKeys.erase(eventKeys.begin());
    eventValues.erase(eventValues.begin());
    return true;
}

bool CoopSession::worldFlag(const std::string& key, bool fallback) const {
    std::unordered_map<std::string, double>::const_iterator it = worldState.find(key);
    if (it == worldState.end()) return fallback;
    return it->second != 0.0;
}

double CoopSession::worldValue(const std::string& key, double fallback) const {
    std::unordered_map<std::string, double>::const_iterator it = worldState.find(key);
    if (it == worldState.end()) return fallback;
    return it->second;
}

bool CoopSession::hasWorldValue(const std::string& key) const {
    return worldState.find(key) != worldState.end();
}

RemotePlayer* CoopSession::findRemote(const std::string& id) {
    for (size_t i = 0; i < others.size(); i++) {
        if (others[i].id == id) return &others[i];
    }
    return nullptr;
}

void CoopSession::dropRemote(const std::string& id) {
    for (size_t i = 0; i < others.size(); i++) {
        if (others[i].id != id) continue;
        others.erase(others.begin() + (long)i);
        return;
    }
}

void CoopSession::applyRoster(const js::Value& lobby) {
    if (!lobby.isObject()) return;
    if (lobby.has("code")) {
        lobbyCode = lobby.get("code").asString();
        inviteText = serverInvite.empty() ? lobbyCode + "@" + host + ":" + std::to_string(port)
                                          : serverInvite;
    }
    if (lobby.has("seed")) seed = (u64)lobby.get("seed").asNumber(0.0);

    const js::Value& players = lobby.get("players");
    roster.clear();
    for (size_t i = 0; i < players.size(); i++) {
        const js::Value& entry = players.at(i);
        CoopMember member;
        member.id = entry.get("id").asString();
        member.name = entry.get("name").asString("Spieler");
        member.model = entry.get("model").asString("default");
        member.host = entry.get("host").asBool(false);
        member.ready = entry.get("ready").asBool(false);
        member.online = entry.get("online").asBool(true);
        member.loaded = entry.get("loaded").asBool(false);
        member.slot = entry.get("slot").asInt(0);
        member.ping = entry.get("ping").asFloat(0.0f);
        member.loss = entry.get("loss").asFloat(0.0f);
        roster.push_back(member);
        if (member.id == playerId) {
            localPing = member.ping;
            localLoss = member.loss;
        }
    }

    for (size_t i = 0; i < others.size(); i++) others[i].present = false;
    for (size_t i = 0; i < roster.size(); i++) {
        if (roster[i].id == playerId) continue;
        RemotePlayer* remote = findRemote(roster[i].id);
        if (remote == nullptr) {
            RemotePlayer fresh;
            fresh.id = roster[i].id;
            others.push_back(fresh);
            remote = &others.back();
        }
        remote->name = roster[i].name;
        remote->model = roster[i].model;
        remote->slot = roster[i].slot;
        remote->ping = roster[i].ping;
        remote->online = roster[i].online;
        remote->present = true;
        if (!remote->configured) {
            int type = remote->slot % HUMAN_TYPE_COUNT;
            remote->body.configure(type, 0x51E0u + (u64)(remote->slot + 1) * 7919ULL);
            remote->body.active = true;
            remote->body.setPose(POSE_STAND_STILL, 0.2f);
            remote->configured = true;
        }
    }
    for (size_t i = others.size(); i > 0; i--) {
        if (!others[i - 1].present) others.erase(others.begin() + (long)(i - 1));
    }
}

void CoopSession::applyPlayerPatch(const std::string& id, const js::Value& patch, double stamp) {
    if (id == playerId) {
        if (patch.has("ping")) localPing = patch.get("ping").asFloat(localPing);
        return;
    }
    RemotePlayer* remote = findRemote(id);
    if (remote == nullptr) {
        RemotePlayer fresh;
        fresh.id = id;
        fresh.name = patch.get("name").asString("Spieler");
        others.push_back(fresh);
        remote = &others.back();
        remote->slot = (int)others.size();
        remote->body.configure(remote->slot % HUMAN_TYPE_COUNT, 0x51E0u + (u64)(remote->slot + 1) * 7919ULL);
        remote->body.active = true;
        remote->configured = true;
        remote->present = true;
    }
    if (patch.has("name")) remote->name = patch.get("name").asString(remote->name);
    if (patch.has("ping")) remote->ping = patch.get("ping").asFloat(remote->ping);
    if (patch.has("online")) remote->online = patch.get("online").asBool(true);

    CoopSample sample;
    if (!remote->buffer.empty()) sample = remote->buffer.back();
    sample.stamp = stamp;
    if (patch.has("x")) sample.position.x = patch.get("x").asFloat(sample.position.x);
    if (patch.has("y")) sample.position.y = patch.get("y").asFloat(sample.position.y);
    if (patch.has("z")) sample.position.z = patch.get("z").asFloat(sample.position.z);
    if (patch.has("vx")) sample.velocity.x = patch.get("vx").asFloat(0.0f);
    if (patch.has("vy")) sample.velocity.y = patch.get("vy").asFloat(0.0f);
    if (patch.has("vz")) sample.velocity.z = patch.get("vz").asFloat(0.0f);
    if (patch.has("yaw")) sample.yaw = patch.get("yaw").asFloat(sample.yaw);
    if (patch.has("pitch")) sample.pitch = patch.get("pitch").asFloat(sample.pitch);
    if (patch.has("anim")) sample.anim = animFromName(patch.get("anim").asString("idle"));
    if (patch.has("flags")) sample.flags = (u32)patch.get("flags").asInt(0);

    if (remote->buffer.empty()) {
        remote->renderPos = sample.position;
        remote->renderYaw = sample.yaw;
    }
    remote->buffer.push_back(sample);
    if (remote->buffer.size() > 32) remote->buffer.erase(remote->buffer.begin());
}

void CoopSession::applyWorld(const js::Value& world) {
    if (!world.isObject()) return;
    const std::map<std::string, js::Value>& fields = world.members();
    for (std::map<std::string, js::Value>::const_iterator it = fields.begin(); it != fields.end(); ++it) {
        if (it->second.isString()) {
            worldText[it->first] = it->second.asString();
            worldState[it->first] = 1.0;
        } else if (it->second.isObject() || it->second.isArray()) {
            worldState[it->first] = 1.0;
        } else {
            worldState[it->first] = it->second.asNumber(0.0);
        }
    }
}

void CoopSession::applyEvent(const js::Value& event) {
    std::string kind = event.get("kind").asString();
    if (kind == "interact") {
        eventKinds.push_back(event.get("act").asString("interact"));
        eventKeys.push_back(event.get("key").asString());
        eventValues.push_back(event.get("value").asNumber(1.0));
        std::string by = event.get("by").asString();
        RemotePlayer* remote = findRemote(by);
        if (remote != nullptr) remote->interactFlash = 0.45f;
        return;
    }
    if (kind == "save") {
        eventKinds.push_back("save");
        eventKeys.push_back(event.get("by").asString());
        eventValues.push_back(1.0);
        return;
    }
    if (kind == "strike") {
        eventKinds.push_back("strike");
        eventKeys.push_back(event.get("target").asString());
        eventValues.push_back(event.get("hp").asNumber(0.0));
        return;
    }
    if (kind == "teleport") {
        RemotePlayer* remote = findRemote(event.get("id").asString());
        if (remote != nullptr) {
            remote->buffer.clear();
            remote->renderPos = Vec3(event.get("x").asFloat(0.0f), event.get("y").asFloat(0.0f),
                                     event.get("z").asFloat(0.0f));
        }
        return;
    }
    if (kind == "left") {
        dropRemote(event.get("id").asString());
        return;
    }
    if (kind == "presence") {
        RemotePlayer* remote = findRemote(event.get("id").asString());
        if (remote != nullptr) remote->online = event.get("online").asBool(true);
        return;
    }
}

void CoopSession::applySnapshot(const js::Value& msg) {
    if (msg.has("time")) {
        double serverTime = msg.get("time").asNumber(0.0) / 1000.0;
        double offset = serverTime - clock;
        timeOffset = timeOffset == 0.0 ? offset : timeOffset * 0.9 + offset * 0.1;
    }
    lastSnapshot = msg.get("id").asInt(0);
    double stamp = netNow();

    if (msg.get("base").asInt(0) == 0) {
        for (size_t i = 0; i < others.size(); i++) others[i].present = false;
    }

    const js::Value& players = msg.get("players");
    if (players.isObject()) {
        const std::map<std::string, js::Value>& fields = players.members();
        for (std::map<std::string, js::Value>::const_iterator it = fields.begin(); it != fields.end(); ++it) {
            applyPlayerPatch(it->first, it->second, stamp);
            RemotePlayer* remote = findRemote(it->first);
            if (remote != nullptr) remote->present = true;
        }
    }

    if (msg.has("world")) applyWorld(msg.get("world"));
    const js::Value& unset = msg.get("unset");
    for (size_t i = 0; i < unset.size(); i++) {
        worldState.erase(unset.at(i).asString());
        worldText.erase(unset.at(i).asString());
    }

    const js::Value& gone = msg.get("gone");
    for (size_t i = 0; i < gone.size(); i++) dropRemote(gone.at(i).asString());

    const js::Value& events = msg.get("ev");
    for (size_t i = 0; i < events.size(); i++) {
        const js::Value& event = events.at(i);
        int eid = event.get("eid").asInt(0);
        if (eid <= eventCursor) continue;
        eventCursor = eid;
        applyEvent(event);
    }

    js::Value ack = js::Value::object();
    ack.set("t", "ack");
    ack.set("snap", lastSnapshot);
    ack.set("ev", eventCursor);
    client.send(ack);
}

void CoopSession::handle(const js::Value& msg) {
    std::string type = msg.get("t").asString();

    if (type == "redirect") {
        if (redirectHops >= 3) {
            lastError = "Gastgeber nicht erreichbar";
            currentPhase = COOP_ERROR;
            return;
        }
        std::string target = msg.get("host").asString();
        int targetPort = msg.get("tcp_port").asInt(0);
        if (target.empty()) {
            lastError = "Gastgeber nicht erreichbar";
            currentPhase = COOP_ERROR;
            return;
        }
        std::string newCode = msg.get("code").asString(pendingCode);
        if (!newCode.empty()) pendingCode = upper(newCode);
        redirectHops++;
        redirectHost = target;
        redirectPort = targetPort > 0 ? targetPort : port;
        hasRedirect = true;
        statusLine = "Gastgeber gefunden — verbinde ...";
        return;
    }

    if (type == "welcome") {
        playerId = msg.get("player_id").asString();
        token = msg.get("token").asString(token);
        serverInvite = msg.get("invite_tcp").asString(serverInvite);
        redirectHops = 0;
        applyRoster(msg.get("lobby"));
        if (msg.has("spawn")) {
            spawn = readVec(msg.get("spawn"));
            hasSpawn = true;
        }
        if (msg.has("save")) saveBlob = msg.get("save");
        const js::Value& state = msg.get("state");
        if (state.isObject()) {
            worldState.clear();
            worldText.clear();
            applyWorld(state.get("world"));
        }
        std::string lobbyPhase = msg.get("lobby").get("phase").asString("lobby");
        reconnectTries = 0;
        if (lobbyPhase == "playing" || lobbyPhase == "paused") {
            currentPhase = COOP_LOADING;
            statusLine = "Sitzung wird wiederhergestellt ...";
        } else {
            currentPhase = COOP_LOBBY;
            statusLine = wantHost ? "Warte auf Mitspieler" : "In der Lobby";
        }
        intent = kIntentResume;
        return;
    }
    if (type == "lobby") {
        applyRoster(msg.get("lobby"));
        if (currentPhase == COOP_CONNECTING) currentPhase = COOP_LOBBY;
        return;
    }
    if (type == "start") {
        seed = (u64)msg.get("seed").asNumber((double)seed);
        const js::Value& spawns = msg.get("spawns");
        if (spawns.has(playerId)) {
            spawn = readVec(spawns.get(playerId));
            hasSpawn = true;
        }
        if (msg.has("save")) saveBlob = msg.get("save");
        applyRoster(msg.get("lobby"));
        currentPhase = COOP_LOADING;
        statusLine = "Welt wird geladen ...";
        return;
    }
    if (type == "sync") {
        int loaded = (int)msg.get("loaded").size();
        int total = msg.get("total").asInt(1);
        char buf[64];
        std::snprintf(buf, sizeof(buf), "Warte auf Mitspieler (%d/%d)", loaded, total);
        statusLine = buf;
        return;
    }
    if (type == "spawn") {
        const js::Value& spawns = msg.get("spawns");
        if (spawns.has(playerId)) {
            spawn = readVec(spawns.get(playerId));
            hasSpawn = true;
        }
        const js::Value& state = msg.get("state");
        if (state.isObject()) applyWorld(state.get("world"));
        currentPhase = COOP_PLAYING;
        statusLine = "Koop laeuft";
        spawnSignal = true;
        forceSend = true;
        return;
    }
    if (type == "snap") {
        applySnapshot(msg);
        return;
    }
    if (type == "ping") {
        js::Value pong = js::Value::object();
        pong.set("t", "pong");
        pong.set("s", msg.get("s").asInt(0));
        client.send(pong);
        return;
    }
    if (type == "chat") {
        chatLines.push_back(msg.get("name").asString("Spieler") + ": " + msg.get("text").asString());
        return;
    }
    if (type == "fx") {
        eventKinds.push_back("fx:" + msg.get("kind").asString());
        eventKeys.push_back(msg.get("by").asString());
        eventValues.push_back(msg.get("data").get("value").asNumber(1.0));
        return;
    }
    if (type == "correct") {
        eventKinds.push_back("correct");
        eventKeys.push_back(std::string());
        eventValues.push_back(1.0);
        spawn = Vec3(msg.get("x").asFloat(spawn.x), msg.get("y").asFloat(spawn.y), msg.get("z").asFloat(spawn.z));
        hasSpawn = true;
        return;
    }
    if (type == "kick" || type == "bye") {
        lastError = msg.get("reason").asString("Verbindung beendet");
        client.disconnect();
        currentPhase = COOP_ERROR;
        statusLine = lastError;
        return;
    }
    if (type == "error") {
        lastError = msg.get("msg").asString("Fehler");
        statusLine = lastError;
        if (currentPhase == COOP_CONNECTING) currentPhase = COOP_ERROR;
        return;
    }
    if (type == "reject") {
        eventKinds.push_back("reject");
        eventKeys.push_back(msg.get("kind").asString());
        eventValues.push_back(0.0);
        return;
    }
}

void CoopSession::attemptReconnect(float dt) {
    if (token.empty() || intent == 0) {
        currentPhase = COOP_ERROR;
        return;
    }
    reconnectTimer -= dt;
    if (reconnectTimer > 0.0f) return;
    reconnectTries++;
    reconnectTimer = std::min(8.0f, 1.2f * (float)reconnectTries);
    intent = kIntentResume;
    statusLine = "Verbindung wird wiederhergestellt ...";
    beginConnect();
}

void CoopSession::update(float dt) {
    clock += (double)dt;
    client.update();

    int netStatus = client.state();
    if (currentPhase == COOP_OFF || currentPhase == COOP_ERROR) {
        js::Value drop;
        while (client.poll(drop)) {}
        return;
    }

    if (netStatus == NET_FAILED) {
        js::Value pending;
        int drained = 0;
        while (client.poll(pending) && drained++ < 128) handle(pending);
        if (applyRedirect()) return;
        if (currentPhase == COOP_CONNECTING && token.empty()) {
            lastError = client.lastError();
            statusLine = lastError.empty() ? "Jon-Server nicht erreichbar" : lastError;
            currentPhase = COOP_ERROR;
            return;
        }
        currentPhase = COOP_LOST;
        attemptReconnect(dt);
        return;
    }

    if (currentPhase == COOP_LOST) {
        if (netStatus == NET_ONLINE) {
            sendHandshake();
            currentPhase = COOP_CONNECTING;
        } else if (netStatus == NET_OFFLINE) {
            attemptReconnect(dt);
        }
        return;
    }

    if (netStatus != NET_ONLINE) return;
    if (!handshakeSent) sendHandshake();

    js::Value msg;
    int guard = 0;
    while (client.poll(msg) && guard++ < 256) handle(msg);

    if (applyRedirect()) return;

    if (currentPhase != COOP_PLAYING) return;

    sendTimer += dt;
    if (sendTimer < 1.0f / kSendRate) return;
    sendTimer = 0.0f;

    bool changed = forceSend;
    forceSend = false;
    if (distanceSq(local.position, lastSent.position) > 0.000004f) changed = true;
    if (std::fabs(wrapAngle(local.yaw - lastSent.yaw)) > 0.004f) changed = true;
    if (std::fabs(local.pitch - lastSent.pitch) > 0.004f) changed = true;
    if (local.anim != lastSent.anim || local.flags != lastSent.flags) changed = true;
    if (local.health != lastSent.health) changed = true;
    if (!changed) return;

    lastSent = local;
    js::Value packet = js::Value::object();
    packet.set("t", "input");
    packet.set("x", local.position.x);
    packet.set("y", local.position.y);
    packet.set("z", local.position.z);
    packet.set("vx", local.velocity.x);
    packet.set("vy", local.velocity.y);
    packet.set("vz", local.velocity.z);
    packet.set("yaw", local.yaw);
    packet.set("pitch", local.pitch);
    packet.set("anim", std::string(kAnimNames[clampi(local.anim, 0, CANIM_COUNT - 1)]));
    packet.set("flags", (int)local.flags);
    packet.set("hp", local.health);
    client.send(packet);
}

void CoopSession::updateRemotes(float dt, float time, const Vec3& listener) {
    double target = netNow() - kInterpDelay;

    for (size_t i = 0; i < others.size(); i++) {
        RemotePlayer& remote = others[i];
        if (remote.interactFlash > 0.0f) remote.interactFlash -= dt;

        Vec3 wanted = remote.renderPos;
        float wantYaw = remote.renderYaw;
        float wantPitch = remote.renderPitch;

        if (!remote.buffer.empty()) {
            const std::vector<CoopSample>& buf = remote.buffer;
            if (buf.size() == 1 || target <= buf.front().stamp) {
                wanted = buf.front().position;
                wantYaw = buf.front().yaw;
                wantPitch = buf.front().pitch;
                remote.anim = buf.front().anim;
                remote.flags = buf.front().flags;
            } else if (target >= buf.back().stamp) {
                double ahead = std::min(kExtrapolateMax, target - buf.back().stamp);
                wanted = buf.back().position + buf.back().velocity * (float)ahead;
                wantYaw = buf.back().yaw;
                wantPitch = buf.back().pitch;
                remote.anim = buf.back().anim;
                remote.flags = buf.back().flags;
            } else {
                for (size_t k = buf.size() - 1; k > 0; k--) {
                    const CoopSample& a = buf[k - 1];
                    const CoopSample& b = buf[k];
                    if (a.stamp > target || target > b.stamp) continue;
                    double span = b.stamp - a.stamp;
                    float f = span > 1e-6 ? (float)((target - a.stamp) / span) : 1.0f;
                    wanted = a.position + (b.position - a.position) * f;
                    wantYaw = a.yaw + wrapAngle(b.yaw - a.yaw) * f;
                    wantPitch = lerpf(a.pitch, b.pitch, f);
                    remote.anim = f > 0.5f ? b.anim : a.anim;
                    remote.flags = f > 0.5f ? b.flags : a.flags;
                    break;
                }
            }
            while (remote.buffer.size() > 4 && remote.buffer[1].stamp < target - 0.6) {
                remote.buffer.erase(remote.buffer.begin());
            }
        }

        float blend = std::min(1.0f, dt * 16.0f);
        if (distanceSq(remote.renderPos, wanted) > 36.0f) remote.renderPos = wanted;
        else remote.renderPos = remote.renderPos + (wanted - remote.renderPos) * blend;
        remote.renderYaw += wrapAngle(wantYaw - remote.renderYaw) * blend;
        remote.renderPitch += (wantPitch - remote.renderPitch) * blend;

        int pose = POSE_STAND_STILL;
        switch (remote.anim) {
        case CANIM_WALK: pose = POSE_SLOW_WALK; break;
        case CANIM_RUN: pose = POSE_SLOW_WALK; break;
        case CANIM_CROUCH:
        case CANIM_SNEAK: pose = POSE_LEAN; break;
        case CANIM_JUMP:
        case CANIM_FALL: pose = POSE_LOOK_UP; break;
        case CANIM_INTERACT: pose = POSE_LEAN; break;
        case CANIM_ATTACK: pose = POSE_LEAN; break;
        default: pose = (remote.flags & CFLAG_CROUCH) ? POSE_SIT : POSE_IDLE; break;
        }
        remote.body.walkSpeed = remote.anim == CANIM_RUN ? 1.55f : 0.85f;
        remote.body.setPose(pose, 0.28f);
        remote.body.position = remote.renderPos;
        remote.body.yaw = remote.renderYaw;
        remote.body.visibility = remote.online ? 1.0f : 0.35f;
        remote.body.active = true;
        remote.body.update(dt, time, listener, true);
    }
}

void CoopSession::submitRemotes(Renderer& renderer) {
    if (rig == nullptr) return;
    for (size_t i = 0; i < others.size(); i++) {
        others[i].body.submit(renderer, *rig);
    }
}

}
