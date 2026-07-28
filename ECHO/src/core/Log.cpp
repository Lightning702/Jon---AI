#include "Log.h"

#include <cstdio>
#include <cstdarg>
#include <ctime>
#include <mutex>

namespace echo {

static FILE* g_file = nullptr;
static std::mutex g_mutex;

void logInit(const char* file) {
    std::lock_guard<std::mutex> lock(g_mutex);
    if (g_file) return;
    fopen_s(&g_file, file, "w");
    if (g_file) {
        std::time_t t = std::time(nullptr);
        char buf[64];
        std::tm tmv;
        localtime_s(&tmv, &t);
        std::strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M:%S", &tmv);
        std::fprintf(g_file, "ECHO %s log started %s\n", ECHO_VERSION, buf);
        std::fflush(g_file);
    }
}

void logShutdown() {
    std::lock_guard<std::mutex> lock(g_mutex);
    if (g_file) { std::fclose(g_file); g_file = nullptr; }
}

void logWrite(LogLevel lv, const char* fmt, ...) {
    static const char* tags[] = { "TRACE", "INFO ", "WARN ", "ERROR" };
    char buf[4096];
    va_list args;
    va_start(args, fmt);
    vsnprintf(buf, sizeof(buf), fmt, args);
    va_end(args);

    std::lock_guard<std::mutex> lock(g_mutex);
    std::printf("[%s] %s\n", tags[(int)lv], buf);
    if (g_file) {
        std::fprintf(g_file, "[%s] %s\n", tags[(int)lv], buf);
        std::fflush(g_file);
    }
}

}
