#pragma once

#include "../core/Result.hpp"

#include <string>

namespace sf {

class TcpSocket {
public:
    TcpSocket() = default;
    ~TcpSocket();

    TcpSocket(const TcpSocket&) = delete;
    TcpSocket& operator=(const TcpSocket&) = delete;

    Status connectTo(const std::string& host, u16 port, u32 timeoutMilliseconds);
    void disconnect();
    bool connected() const { return handle != kInvalidSocket; }

    i32 sendAll(const void* data, usize size);
    i32 receiveSome(void* buffer, usize size, u32 timeoutMilliseconds);
    bool sendLine(const std::string& line);

    u64 bytesSent() const { return sentBytes; }
    u64 bytesReceived() const { return receivedBytes; }

    static bool platformStartup();
    static void platformShutdown();

private:
    static constexpr u64 kInvalidSocket = static_cast<u64>(-1);
    u64 handle = kInvalidSocket;
    u64 sentBytes = 0;
    u64 receivedBytes = 0;
};

class HttpClient {
public:
    struct Response {
        i32 statusCode = 0;
        std::string body;
        bool ok() const { return statusCode >= 200 && statusCode < 300; }
    };

    static Response post(const std::string& host, u16 port, const std::string& path, const std::string& contentType,
                         const std::string& body, u32 timeoutMilliseconds);
    static Response get(const std::string& host, u16 port, const std::string& path, u32 timeoutMilliseconds);
};

}
