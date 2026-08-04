#include "Socket.hpp"

#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <winsock2.h>
#include <ws2tcpip.h>

#include <atomic>
#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace sf {
namespace {

std::atomic<i32> socketUsers{0};

}

bool TcpSocket::platformStartup() {
    if (socketUsers.fetch_add(1) > 0) return true;
    WSADATA data;
    return WSAStartup(MAKEWORD(2, 2), &data) == 0;
}

void TcpSocket::platformShutdown() {
    if (socketUsers.fetch_sub(1) > 1) return;
    WSACleanup();
}

TcpSocket::~TcpSocket() {
    disconnect();
}

Status TcpSocket::connectTo(const std::string& host, u16 port, u32 timeoutMilliseconds) {
    disconnect();
    if (!platformStartup()) {
        return statusError(StatusCode::NetworkFailure, "Winsock konnte nicht gestartet werden");
    }

    char portText[16];
    std::snprintf(portText, sizeof(portText), "%u", static_cast<unsigned>(port));

    addrinfo hints = {};
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_protocol = IPPROTO_TCP;

    addrinfo* results = nullptr;
    if (getaddrinfo(host.c_str(), portText, &hints, &results) != 0 || results == nullptr) {
        platformShutdown();
        return statusError(StatusCode::NetworkFailure, "Adresse nicht aufloesbar: " + host);
    }

    SOCKET target = INVALID_SOCKET;
    for (addrinfo* candidate = results; candidate != nullptr; candidate = candidate->ai_next) {
        target = socket(candidate->ai_family, candidate->ai_socktype, candidate->ai_protocol);
        if (target == INVALID_SOCKET) continue;

        u_long nonBlocking = 1;
        ioctlsocket(target, FIONBIO, &nonBlocking);
        connect(target, candidate->ai_addr, static_cast<int>(candidate->ai_addrlen));

        fd_set writeSet;
        FD_ZERO(&writeSet);
        FD_SET(target, &writeSet);
        timeval waitTime;
        waitTime.tv_sec = static_cast<long>(timeoutMilliseconds / 1000);
        waitTime.tv_usec = static_cast<long>((timeoutMilliseconds % 1000) * 1000);

        const int ready = select(0, nullptr, &writeSet, nullptr, &waitTime);
        u_long blocking = 0;
        ioctlsocket(target, FIONBIO, &blocking);

        if (ready > 0) break;
        closesocket(target);
        target = INVALID_SOCKET;
    }
    freeaddrinfo(results);

    if (target == INVALID_SOCKET) {
        platformShutdown();
        return statusError(StatusCode::NetworkFailure, "Verbindung fehlgeschlagen: " + host);
    }

    int noDelay = 1;
    setsockopt(target, IPPROTO_TCP, TCP_NODELAY, reinterpret_cast<const char*>(&noDelay), sizeof(noDelay));

    handle = static_cast<u64>(target);
    return statusOk();
}

void TcpSocket::disconnect() {
    if (handle == kInvalidSocket) return;
    closesocket(static_cast<SOCKET>(handle));
    handle = kInvalidSocket;
    platformShutdown();
}

i32 TcpSocket::sendAll(const void* data, usize size) {
    if (handle == kInvalidSocket) return -1;
    const char* cursor = static_cast<const char*>(data);
    usize remaining = size;
    while (remaining > 0) {
        const int written = send(static_cast<SOCKET>(handle), cursor, static_cast<int>(remaining), 0);
        if (written <= 0) return -1;
        cursor += written;
        remaining -= static_cast<usize>(written);
        sentBytes += static_cast<u64>(written);
    }
    return static_cast<i32>(size);
}

i32 TcpSocket::receiveSome(void* buffer, usize size, u32 timeoutMilliseconds) {
    if (handle == kInvalidSocket) return -1;
    fd_set readSet;
    FD_ZERO(&readSet);
    FD_SET(static_cast<SOCKET>(handle), &readSet);
    timeval waitTime;
    waitTime.tv_sec = static_cast<long>(timeoutMilliseconds / 1000);
    waitTime.tv_usec = static_cast<long>((timeoutMilliseconds % 1000) * 1000);

    const int ready = select(0, &readSet, nullptr, nullptr, &waitTime);
    if (ready <= 0) return 0;

    const int received = recv(static_cast<SOCKET>(handle), static_cast<char*>(buffer), static_cast<int>(size), 0);
    if (received <= 0) return -1;
    receivedBytes += static_cast<u64>(received);
    return received;
}

bool TcpSocket::sendLine(const std::string& line) {
    const std::string payload = line + "\n";
    return sendAll(payload.data(), payload.size()) > 0;
}

HttpClient::Response HttpClient::post(const std::string& host, u16 port, const std::string& path,
                                      const std::string& contentType, const std::string& body,
                                      u32 timeoutMilliseconds) {
    Response response;
    TcpSocket connection;
    if (!connection.connectTo(host, port, timeoutMilliseconds).ok()) return response;

    char header[1024];
    std::snprintf(header, sizeof(header),
                  "POST %s HTTP/1.1\r\nHost: %s:%u\r\nContent-Type: %s\r\nContent-Length: %llu\r\n"
                  "Accept: text/event-stream, application/json\r\nConnection: close\r\n\r\n",
                  path.c_str(), host.c_str(), static_cast<unsigned>(port), contentType.c_str(),
                  static_cast<unsigned long long>(body.size()));

    if (connection.sendAll(header, std::strlen(header)) < 0) return response;
    if (!body.empty() && connection.sendAll(body.data(), body.size()) < 0) return response;

    std::string raw;
    char buffer[4096];
    while (true) {
        const i32 received = connection.receiveSome(buffer, sizeof(buffer), timeoutMilliseconds);
        if (received < 0) break;
        if (received == 0) break;
        raw.append(buffer, static_cast<usize>(received));
        if (raw.size() > 1 << 20) break;
    }
    connection.disconnect();

    if (raw.size() < 12) return response;
    response.statusCode = std::atoi(raw.c_str() + 9);
    const usize separator = raw.find("\r\n\r\n");
    if (separator != std::string::npos) response.body = raw.substr(separator + 4);
    return response;
}

HttpClient::Response HttpClient::get(const std::string& host, u16 port, const std::string& path,
                                     u32 timeoutMilliseconds) {
    Response response;
    TcpSocket connection;
    if (!connection.connectTo(host, port, timeoutMilliseconds).ok()) return response;

    char header[768];
    std::snprintf(header, sizeof(header), "GET %s HTTP/1.1\r\nHost: %s:%u\r\nConnection: close\r\n\r\n", path.c_str(),
                  host.c_str(), static_cast<unsigned>(port));
    if (connection.sendAll(header, std::strlen(header)) < 0) return response;

    std::string raw;
    char buffer[4096];
    while (true) {
        const i32 received = connection.receiveSome(buffer, sizeof(buffer), timeoutMilliseconds);
        if (received <= 0) break;
        raw.append(buffer, static_cast<usize>(received));
        if (raw.size() > 1 << 20) break;
    }
    connection.disconnect();

    if (raw.size() < 12) return response;
    response.statusCode = std::atoi(raw.c_str() + 9);
    const usize separator = raw.find("\r\n\r\n");
    if (separator != std::string::npos) response.body = raw.substr(separator + 4);
    return response;
}

}
