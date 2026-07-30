#pragma once

#include "Json.h"
#include <atomic>
#include <mutex>
#include <thread>

namespace echo {

enum NetState {
    NET_OFFLINE = 0,
    NET_RESOLVING,
    NET_CONNECTING,
    NET_ONLINE,
    NET_FAILED
};

class NetClient {
public:
    ~NetClient();

    bool connect(const std::string& host, int port);
    void disconnect();
    void update();

    int state() const { return status.load(); }
    bool online() const { return status.load() == NET_ONLINE; }
    const std::string& lastError() const { return errorText; }

    void send(const js::Value& message);
    bool poll(js::Value& out);

    int pendingIn() const;
    u64 bytesSent() const { return sentBytes.load(); }
    u64 bytesReceived() const { return recvBytes.load(); }

private:
    void threadMain(std::string host, int port);
    void pushIncoming(const std::string& line);
    void setError(const std::string& text);

    std::thread worker;
    std::atomic<int> status{ NET_OFFLINE };
    std::atomic<bool> stopFlag{ false };
    std::atomic<u64> sentBytes{ 0 };
    std::atomic<u64> recvBytes{ 0 };

    mutable std::mutex inLock;
    mutable std::mutex outLock;
    std::vector<std::string> incoming;
    std::vector<std::string> outgoing;

    std::string errorText;
    mutable std::mutex errLock;
};

}
