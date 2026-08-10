#pragma once

#include "Json.hpp"
#include <atomic>
#include <mutex>
#include <thread>

namespace fw {

enum LeitungStand {
    LEITUNG_AUS = 0,
    LEITUNG_SUCHT,
    LEITUNG_VERBINDET,
    LEITUNG_OFFEN,
    LEITUNG_FEHLER
};

class Leitung {
public:
    ~Leitung();

    bool connect(const std::string& host, int port);
    void disconnect();
    void update();

    int state() const { return status.load(); }
    bool online() const { return status.load() == LEITUNG_OFFEN; }
    const std::string& lastError() const { return errorText; }

    void send(const js::Value& message);
    bool poll(js::Value& out);

    int pendingIn() const;
    unsigned long long bytesSent() const { return sentBytes.load(); }
    unsigned long long bytesReceived() const { return recvBytes.load(); }

private:
    void threadMain(std::string host, int port);
    void pushIncoming(const std::string& line);
    void setError(const std::string& text);

    std::thread worker;
    std::atomic<int> status{ LEITUNG_AUS };
    std::atomic<bool> stopFlag{ false };
    std::atomic<unsigned long long> sentBytes{ 0 };
    std::atomic<unsigned long long> recvBytes{ 0 };

    mutable std::mutex inLock;
    mutable std::mutex outLock;
    std::vector<std::string> incoming;
    std::vector<std::string> outgoing;

    std::string errorText;
    mutable std::mutex errLock;
};

}
