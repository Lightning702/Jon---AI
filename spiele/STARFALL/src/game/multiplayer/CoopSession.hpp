#pragma once

#include "../../engine/math/DVec3.hpp"
#include "../../engine/math/Quat.hpp"
#include "../../engine/net/Json.hpp"
#include "../../engine/net/Socket.hpp"
#include "../universe/CoordinateSpace.hpp"

#include <atomic>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

namespace sf {

enum class CoopPhase : u32 {
    Offline = 0,
    Connecting,
    Lobby,
    Loading,
    Playing,
    Lost,
    Failed
};

struct CoopSample {
    f64 stamp = 0.0;
    DVec3 position = DVec3::zero();
    DVec3 velocity = DVec3::zero();
    Quat orientation = Quat::identity();
};

struct CoopMember {
    std::string id;
    std::string name;
    bool host = false;
    bool ready = false;
    bool online = true;
    i32 slot = 0;
    f32 ping = 0.0f;
};

struct CoopRemotePlayer {
    std::string id;
    std::string name;
    i32 slot = 0;
    bool present = false;
    SystemCoord system;
    DVec3 renderPosition = DVec3::zero();
    Quat renderOrientation = Quat::identity();
    std::vector<CoopSample> buffer;
};

struct CoopLocalState {
    DVec3 position = DVec3::zero();
    DVec3 velocity = DVec3::zero();
    Quat orientation = Quat::identity();
    SystemCoord system;
    f64 timeDilation = 1.0;
    f64 hullIntegrity = 1.0;
};

class CoopSession {
public:
    ~CoopSession();

    void configure(const std::string& host, u16 port, const std::string& playerName);
    void hostGame(u64 universeSeed);
    void joinGame(const std::string& invitationCode);
    void leave();

    void setReady(bool value);
    void requestStart();
    void sendChat(const std::string& text);
    void pushLocalState(const CoopLocalState& state);
    void update(f64 stepSeconds);

    CoopPhase phase() const { return currentPhase; }
    bool playing() const { return currentPhase == CoopPhase::Playing; }
    bool inSession() const;
    const std::string& lobbyCode() const { return code; }
    const std::string& statusText() const { return status; }
    const std::string& errorText() const { return lastError; }
    u64 universeSeed() const { return seed; }
    f32 ping() const { return localPing; }
    const std::vector<CoopMember>& members() const { return roster; }
    const std::vector<CoopRemotePlayer>& remotes() const { return others; }
    bool consumeChatLine(std::string& line);

private:
    void connectionThread(std::string host, u16 port);
    void queueOutgoing(const JsonValue& message);
    void handleMessage(const JsonValue& message);
    void applySnapshot(const JsonValue& message);
    void applyRoster(const JsonValue& lobby);
    void sendHandshake();
    CoopRemotePlayer* findRemote(const std::string& id);

    TcpSocket socket;
    std::thread worker;
    std::atomic<bool> stopRequested{false};
    std::atomic<bool> connected{false};

    std::mutex incomingMutex;
    std::mutex outgoingMutex;
    std::vector<std::string> incoming;
    std::vector<std::string> outgoing;

    std::vector<CoopMember> roster;
    std::vector<CoopRemotePlayer> others;
    std::vector<std::string> chatLines;
    usize chatCursor = 0;

    CoopPhase currentPhase = CoopPhase::Offline;
    CoopLocalState local;
    std::string serverHost = "127.0.0.1";
    u16 serverPort = 8759;
    std::string playerId;
    std::string playerLabel = "Pilot";
    std::string code;
    std::string status;
    std::string lastError;
    u64 seed = 0;
    f64 clock = 0.0;
    f64 sendTimer = 0.0;
    f32 localPing = 0.0f;
    bool wantHost = false;
    bool handshakeSent = false;
};

}
