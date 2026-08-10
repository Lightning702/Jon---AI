#include "Leitung.hpp"
#include "Protokoll.hpp"

#include <winsock2.h>
#include <ws2tcpip.h>

namespace fw {

namespace {
const size_t kMaxFrame = 4u * 1024u * 1024u;
std::atomic<int> gWinsockUsers{ 0 };

bool winsockAcquire() {
    if (gWinsockUsers.fetch_add(1) == 0) {
        WSADATA data;
        if (WSAStartup(MAKEWORD(2, 2), &data) != 0) {
            gWinsockUsers.fetch_sub(1);
            return false;
        }
    }
    return true;
}

void winsockRelease() {
    if (gWinsockUsers.fetch_sub(1) == 1) WSACleanup();
}
}

Leitung::~Leitung() {
    disconnect();
}

void Leitung::setError(const std::string& text) {
    std::lock_guard<std::mutex> guard(errLock);
    errorText = text;
}

bool Leitung::connect(const std::string& host, int port) {
    disconnect();
    if (host.empty() || port <= 0 || port > 65535) {
        setError("Adresse unvollstaendig");
        status.store(LEITUNG_FEHLER);
        return false;
    }
    setError(std::string());
    stopFlag.store(false);
    status.store(LEITUNG_SUCHT);
    sentBytes.store(0);
    recvBytes.store(0);
    {
        std::lock_guard<std::mutex> guard(inLock);
        incoming.clear();
    }
    {
        std::lock_guard<std::mutex> guard(outLock);
        outgoing.clear();
    }
    worker = std::thread(&Leitung::threadMain, this, host, port);
    return true;
}

void Leitung::disconnect() {
    stopFlag.store(true);
    if (worker.joinable()) worker.join();
    status.store(LEITUNG_AUS);
    std::lock_guard<std::mutex> guard(outLock);
    outgoing.clear();
}

void Leitung::send(const js::Value& message) {
    std::string text = message.dump();
    if (text.size() > kMaxFrame) return;
    std::lock_guard<std::mutex> guard(outLock);
    if (outgoing.size() > 512) outgoing.erase(outgoing.begin(), outgoing.begin() + 256);
    outgoing.push_back(text);
}

bool Leitung::poll(js::Value& out) {
    std::string line;
    {
        std::lock_guard<std::mutex> guard(inLock);
        if (incoming.empty()) return false;
        line = incoming.front();
        incoming.erase(incoming.begin());
    }
    bool ok = false;
    out = js::parse(line, &ok);
    return ok && out.isObject();
}

int Leitung::pendingIn() const {
    std::lock_guard<std::mutex> guard(inLock);
    return (int)incoming.size();
}

void Leitung::update() {
    if (status.load() == LEITUNG_FEHLER && worker.joinable()) worker.join();
}

void Leitung::pushIncoming(const std::string& line) {
    std::lock_guard<std::mutex> guard(inLock);
    if (incoming.size() > 2048) incoming.erase(incoming.begin(), incoming.begin() + 1024);
    incoming.push_back(line);
}

void Leitung::threadMain(std::string host, int port) {
    if (!winsockAcquire()) {
        setError("Netzwerk nicht verfuegbar");
        status.store(LEITUNG_FEHLER);
        return;
    }

    char portText[16];
    std::snprintf(portText, sizeof(portText), "%d", port);

    addrinfo hints;
    std::memset(&hints, 0, sizeof(hints));
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_protocol = IPPROTO_TCP;

    addrinfo* result = nullptr;
    if (getaddrinfo(host.c_str(), portText, &hints, &result) != 0 || result == nullptr) {
        setError("Server nicht gefunden: " + host);
        status.store(LEITUNG_FEHLER);
        winsockRelease();
        return;
    }

    status.store(LEITUNG_VERBINDET);
    SOCKET sock = INVALID_SOCKET;
    bool refused = false;
    for (addrinfo* it = result; it != nullptr; it = it->ai_next) {
        sock = socket(it->ai_family, it->ai_socktype, it->ai_protocol);
        if (sock == INVALID_SOCKET) continue;

        u_long nonBlocking = 1;
        ioctlsocket(sock, FIONBIO, &nonBlocking);
        ::connect(sock, it->ai_addr, (int)it->ai_addrlen);

        fd_set writeSet, errorSet;
        FD_ZERO(&writeSet);
        FD_ZERO(&errorSet);
        FD_SET(sock, &writeSet);
        FD_SET(sock, &errorSet);
        timeval timeout;
        timeout.tv_sec = 5;
        timeout.tv_usec = 0;
        int ready = select(0, nullptr, &writeSet, &errorSet, &timeout);
        bool ok = false;
        if (ready > 0 && FD_ISSET(sock, &writeSet)) {
            int soError = 0;
            int len = (int)sizeof(soError);
            if (getsockopt(sock, SOL_SOCKET, SO_ERROR, (char*)&soError, &len) == 0 && soError == 0) {
                ok = true;
            }
        }
        if (ok) break;
        if (ready > 0) refused = true;
        closesocket(sock);
        sock = INVALID_SOCKET;
        if (stopFlag.load()) break;
    }
    freeaddrinfo(result);

    if (sock == INVALID_SOCKET) {
        char portInfo[24];
        std::snprintf(portInfo, sizeof(portInfo), ":%d", port);
        setError(refused
                     ? "Kein Jon-Server auf " + host + portInfo
                     : "Keine Antwort von " + host + portInfo);
        status.store(LEITUNG_FEHLER);
        winsockRelease();
        return;
    }

    BOOL noDelay = TRUE;
    setsockopt(sock, IPPROTO_TCP, TCP_NODELAY, (const char*)&noDelay, sizeof(noDelay));
    status.store(LEITUNG_OFFEN);
    notiz("Coop: verbunden mit %s:%d", host.c_str(), port);

    std::string buffer;
    std::string pending;
    bool broken = false;

    while (!stopFlag.load() && !broken) {
        std::vector<std::string> batch;
        {
            std::lock_guard<std::mutex> guard(outLock);
            batch.swap(outgoing);
        }
        for (size_t i = 0; i < batch.size(); i++) {
            unsigned int size = (unsigned int)batch[i].size();
            unsigned char header[4];
            header[0] = (unsigned char)((size >> 24) & 0xFF);
            header[1] = (unsigned char)((size >> 16) & 0xFF);
            header[2] = (unsigned char)((size >> 8) & 0xFF);
            header[3] = (unsigned char)(size & 0xFF);
            pending.append((const char*)header, 4);
            pending.append(batch[i]);
        }

        while (!pending.empty()) {
            int written = ::send(sock, pending.data(), (int)std::min<size_t>(pending.size(), 32768), 0);
            if (written > 0) {
                pending.erase(0, (size_t)written);
                sentBytes.fetch_add((unsigned long long)written);
                continue;
            }
            if (written == SOCKET_ERROR && WSAGetLastError() == WSAEWOULDBLOCK) break;
            broken = true;
            break;
        }
        if (broken) break;

        fd_set readSet;
        FD_ZERO(&readSet);
        FD_SET(sock, &readSet);
        timeval timeout;
        timeout.tv_sec = 0;
        timeout.tv_usec = pending.empty() ? 12000 : 2000;
        int ready = select(0, &readSet, nullptr, nullptr, &timeout);
        if (ready < 0) break;
        if (ready == 0) continue;

        char chunk[8192];
        int got = recv(sock, chunk, (int)sizeof(chunk), 0);
        if (got == 0) break;
        if (got == SOCKET_ERROR) {
            if (WSAGetLastError() == WSAEWOULDBLOCK) continue;
            break;
        }
        recvBytes.fetch_add((unsigned long long)got);
        buffer.append(chunk, (size_t)got);

        while (buffer.size() >= 4) {
            unsigned int size = ((unsigned int)(unsigned char)buffer[0] << 24) | ((unsigned int)(unsigned char)buffer[1] << 16) |
                       ((unsigned int)(unsigned char)buffer[2] << 8) | (unsigned int)(unsigned char)buffer[3];
            if (size == 0 || size > kMaxFrame) {
                broken = true;
                break;
            }
            if (buffer.size() < 4 + (size_t)size) break;
            pushIncoming(buffer.substr(4, (size_t)size));
            buffer.erase(0, 4 + (size_t)size);
        }
    }

    closesocket(sock);
    winsockRelease();
    if (!stopFlag.load()) {
        setError("Verbindung unterbrochen");
        status.store(LEITUNG_FEHLER);
    } else {
        status.store(LEITUNG_AUS);
    }
    notiz("Coop: Verbindung beendet");
}

}
