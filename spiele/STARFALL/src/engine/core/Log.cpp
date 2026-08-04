#include "Log.hpp"

#include <atomic>
#include <chrono>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <ctime>
#include <mutex>
#include <thread>
#include <vector>

namespace sf {
namespace {

constexpr usize kMessageCapacity = 1024;
constexpr usize kRingCapacity = 4096;

struct LogRecord {
    LogLevel level = LogLevel::Info;
    char category[32] = {};
    char message[kMessageCapacity] = {};
    f64 timestampSeconds = 0.0;
};

struct LogState {
    std::mutex mutex;
    std::vector<LogRecord> ring;
    usize head = 0;
    usize tail = 0;
    std::atomic<bool> running{false};
    std::atomic<u32> minimumLevel{static_cast<u32>(LogLevel::Info)};
    std::atomic<u64> droppedRecords{0};
    std::thread writer;
    std::FILE* file = nullptr;
    bool structured = false;
    f64 startClock = 0.0;
};

LogState& state() {
    static LogState instance;
    return instance;
}

f64 monotonicSeconds() {
    return static_cast<f64>(std::clock()) / static_cast<f64>(CLOCKS_PER_SEC);
}

const char* levelName(LogLevel level) {
    switch (level) {
        case LogLevel::Trace: return "trace";
        case LogLevel::Debug: return "debug";
        case LogLevel::Info: return "info";
        case LogLevel::Warning: return "warn";
        case LogLevel::Error: return "error";
        case LogLevel::Fatal: return "fatal";
    }
    return "info";
}

void emit(LogState& s, const LogRecord& record) {
    char line[kMessageCapacity + 256];
    if (s.structured) {
        std::snprintf(line, sizeof(line), "{\"t\":%.3f,\"level\":\"%s\",\"category\":\"%s\",\"message\":\"%s\"}\n",
                      record.timestampSeconds, levelName(record.level), record.category, record.message);
    } else {
        std::snprintf(line, sizeof(line), "[%8.3f] %-5s %-12s %s\n", record.timestampSeconds,
                      levelName(record.level), record.category, record.message);
    }
    std::fputs(line, stdout);
    if (s.file) {
        std::fputs(line, s.file);
    }
}

void drain(LogState& s) {
    std::vector<LogRecord> batch;
    {
        std::unique_lock<std::mutex> lock(s.mutex);
        while (s.tail != s.head) {
            batch.push_back(s.ring[s.tail]);
            s.tail = (s.tail + 1) % kRingCapacity;
        }
    }
    for (const LogRecord& record : batch) {
        emit(s, record);
    }
    if (!batch.empty()) {
        std::fflush(stdout);
        if (s.file) std::fflush(s.file);
    }
}

void writerMain() {
    LogState& s = state();
    while (s.running.load(std::memory_order_acquire)) {
        drain(s);
        std::this_thread::sleep_for(std::chrono::milliseconds(8));
    }
    drain(s);
}

void push(LogLevel level, const char* category, const char* format, std::va_list args) {
    LogState& s = state();
    if (static_cast<u32>(level) < s.minimumLevel.load(std::memory_order_relaxed)) return;

    LogRecord record;
    record.level = level;
    record.timestampSeconds = monotonicSeconds() - s.startClock;
    std::snprintf(record.category, sizeof(record.category), "%s", category ? category : "core");
    std::vsnprintf(record.message, sizeof(record.message), format, args);
    for (char* c = record.message; *c; ++c) {
        if (*c == '"') *c = '\'';
        if (*c == '\n' || *c == '\r' || *c == '\t') *c = ' ';
    }

    if (!s.running.load(std::memory_order_acquire)) {
        emit(s, record);
        std::fflush(stdout);
        return;
    }

    std::unique_lock<std::mutex> lock(s.mutex);
    usize next = (s.head + 1) % kRingCapacity;
    if (next == s.tail) {
        s.droppedRecords.fetch_add(1, std::memory_order_relaxed);
        return;
    }
    s.ring[s.head] = record;
    s.head = next;
}

}

void logInit(const std::string& filePath, bool structuredOutput) {
    LogState& s = state();
    if (s.running.load(std::memory_order_acquire)) return;
    s.ring.resize(kRingCapacity);
    s.head = 0;
    s.tail = 0;
    s.structured = structuredOutput;
    s.startClock = monotonicSeconds();
    if (!filePath.empty()) {
        s.file = std::fopen(filePath.c_str(), "w");
    }
    s.running.store(true, std::memory_order_release);
    s.writer = std::thread(writerMain);
}

void logShutdown() {
    LogState& s = state();
    if (!s.running.exchange(false, std::memory_order_acq_rel)) {
        if (s.file) {
            std::fclose(s.file);
            s.file = nullptr;
        }
        return;
    }
    if (s.writer.joinable()) s.writer.join();
    drain(s);
    u64 dropped = s.droppedRecords.load(std::memory_order_relaxed);
    if (dropped > 0) {
        std::fprintf(stdout, "log dropped %llu records\n", static_cast<unsigned long long>(dropped));
    }
    if (s.file) {
        std::fflush(s.file);
        std::fclose(s.file);
        s.file = nullptr;
    }
    std::fflush(stdout);
}

void logSetMinimumLevel(LogLevel level) {
    state().minimumLevel.store(static_cast<u32>(level), std::memory_order_relaxed);
}

LogLevel logMinimumLevel() {
    return static_cast<LogLevel>(state().minimumLevel.load(std::memory_order_relaxed));
}

void logFlush() {
    drain(state());
}

void logWrite(LogLevel level, const char* category, const char* format, ...) {
    std::va_list args;
    va_start(args, format);
    push(level, category, format, args);
    va_end(args);
}

#define SF_LOG_FORWARD(functionName, levelValue)                    \
    void functionName(const char* category, const char* format, ...) { \
        std::va_list args;                                          \
        va_start(args, format);                                     \
        push(levelValue, category, format, args);                   \
        va_end(args);                                               \
    }

SF_LOG_FORWARD(logTrace, LogLevel::Trace)
SF_LOG_FORWARD(logDebug, LogLevel::Debug)
SF_LOG_FORWARD(logInfo, LogLevel::Info)
SF_LOG_FORWARD(logWarning, LogLevel::Warning)
SF_LOG_FORWARD(logError, LogLevel::Error)
SF_LOG_FORWARD(logFatal, LogLevel::Fatal)

#undef SF_LOG_FORWARD

}
