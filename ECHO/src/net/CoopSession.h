#pragma once

#include "NetClient.h"
#include "../core/Math.h"
#include "../world/Human.h"

namespace echo {

enum CoopPhase {
    COOP_OFF = 0,
    COOP_CONNECTING,
    COOP_LOBBY,
    COOP_LOADING,
    COOP_PLAYING,
    COOP_LOST,
    COOP_ERROR
};

enum CoopAnim {
    CANIM_IDLE = 0,
    CANIM_WALK,
    CANIM_RUN,
    CANIM_CROUCH,
    CANIM_SNEAK,
    CANIM_JUMP,
    CANIM_FALL,
    CANIM_INTERACT,
    CANIM_ATTACK,
    CANIM_COUNT
};

const u32 CFLAG_GROUND = 1u << 0;
const u32 CFLAG_SPRINT = 1u << 1;
const u32 CFLAG_CROUCH = 1u << 2;
const u32 CFLAG_LIGHT = 1u << 3;
const u32 CFLAG_INTERACT = 1u << 4;
const u32 CFLAG_ATTACK = 1u << 5;

struct CoopSample {
    double stamp = 0.0;
    em::Vec3 position;
    em::Vec3 velocity;
    float yaw = 0.0f;
    float pitch = 0.0f;
    int anim = CANIM_IDLE;
    u32 flags = 0;
};

struct CoopMember {
    std::string id;
    std::string name;
    std::string model;
    bool host = false;
    bool ready = false;
    bool online = true;
    bool loaded = false;
    int slot = 0;
    float ping = 0.0f;
    float loss = 0.0f;
};

struct RemotePlayer {
    std::string id;
    std::string name;
    std::string model;
    int slot = 0;
    float ping = 0.0f;
    bool online = true;
    bool present = false;
    int anim = CANIM_IDLE;
    u32 flags = 0;
    float emoteTimer = 0.0f;
    float interactFlash = 0.0f;
    em::Vec3 renderPos;
    float renderYaw = 0.0f;
    float renderPitch = 0.0f;
    std::vector<CoopSample> buffer;
    HumanInstance body;
    bool configured = false;
};

struct CoopLocalState {
    em::Vec3 position;
    em::Vec3 velocity;
    float yaw = 0.0f;
    float pitch = 0.0f;
    int anim = CANIM_IDLE;
    u32 flags = 0;
    int health = 100;
};

class CoopSession {
public:
    void init(const std::string& game, HumanRig* rig);
    void shutdown();

    void hostGame(const std::string& name, u64 seed, const em::Vec3& spawn);
    void joinGame(const std::string& invite, const std::string& name);
    void leave();
    void setServer(const std::string& host, int port);

    void setReady(bool value);
    void requestStart();
    void closeLobby();
    void reportLoaded();
    void sendChat(const std::string& text);

    void pushLocal(const CoopLocalState& state);
    void sendInteract(const std::string& kind, const std::string& id, double value, const em::Vec3& at);
    void sendCheckpoint(const js::Value& data);
    void sendEffect(const std::string& kind, const js::Value& data);

    void update(float dt);
    void updateRemotes(float dt, float time, const em::Vec3& listener);
    void submitRemotes(Renderer& renderer);

    int phase() const { return currentPhase; }
    bool inSession() const { return currentPhase == COOP_LOBBY || currentPhase == COOP_LOADING || currentPhase == COOP_PLAYING; }
    bool playing() const { return currentPhase == COOP_PLAYING; }
    bool isHost() const;
    const std::string& code() const { return lobbyCode; }
    const std::string& invite() const { return inviteText; }
    const std::string& errorText() const { return lastError; }
    const std::string& statusText() const { return statusLine; }
    const std::string& serverHost() const { return host; }
    int serverPort() const { return port; }
    u64 worldSeed() const { return seed; }
    em::Vec3 spawnPoint() const { return spawn; }
    bool spawnReady() const { return hasSpawn; }
    bool consumeSpawnSignal();
    bool consumeChat(std::string& line);
    float ping() const { return localPing; }
    float loss() const { return localLoss; }
    int playerCount() const { return (int)roster.size(); }
    const std::vector<CoopMember>& members() const { return roster; }
    const std::vector<RemotePlayer>& remotes() const { return others; }
    const std::string& localId() const { return playerId; }

    bool worldFlag(const std::string& key, bool fallback = false) const;
    double worldValue(const std::string& key, double fallback = 0.0) const;
    bool hasWorldValue(const std::string& key) const;
    const js::Value& savedState() const { return saveBlob; }
    bool consumeWorldEvent(std::string& kind, std::string& key, double& value);

private:
    void handle(const js::Value& msg);
    void applySnapshot(const js::Value& msg);
    void applyPlayerPatch(const std::string& id, const js::Value& patch, double stamp);
    void applyRoster(const js::Value& lobby);
    void applyWorld(const js::Value& world);
    void applyEvent(const js::Value& event);
    RemotePlayer* findRemote(const std::string& id);
    void dropRemote(const std::string& id);
    void sendHandshake();
    void beginConnect();
    bool applyRedirect();
    void attemptReconnect(float dt);
    double netNow() const;
    static em::Vec3 readVec(const js::Value& v);

    NetClient client;
    HumanRig* rig = nullptr;
    std::string gameId = "echo";
    std::string host = "127.0.0.1";
    int port = 8759;
    std::string homeHost = "127.0.0.1";
    int homePort = 8759;
    std::string playerName = "Spieler";
    std::string playerModel = "default";
    std::string playerId;
    std::string token;
    std::string lobbyCode;
    std::string inviteText;
    std::string serverInvite;
    std::string lastError;
    std::string statusLine;
    std::string pendingCode;

    std::vector<CoopMember> roster;
    std::vector<RemotePlayer> others;
    std::unordered_map<std::string, double> worldState;
    std::unordered_map<std::string, std::string> worldText;
    std::vector<std::string> chatLines;
    std::vector<std::string> eventKinds;
    std::vector<std::string> eventKeys;
    std::vector<double> eventValues;
    js::Value saveBlob;

    std::string redirectHost;
    int redirectPort = 0;
    bool hasRedirect = false;
    int redirectHops = 0;

    int currentPhase = COOP_OFF;
    int intent = 0;
    u64 seed = 0;
    em::Vec3 spawn;
    bool hasSpawn = false;
    bool spawnSignal = false;
    bool wantHost = false;
    double timeOffset = 0.0;
    double clock = 0.0;
    float sendTimer = 0.0f;
    float reconnectTimer = 0.0f;
    int reconnectTries = 0;
    float localPing = 0.0f;
    float localLoss = 0.0f;
    int lastSnapshot = 0;
    int eventCursor = 0;
    CoopLocalState local;
    CoopLocalState lastSent;
    bool handshakeSent = false;
    bool forceSend = false;
};

}
