#include "Protokoll.hpp"

#include <cstdarg>
#include <cstdio>
#include <ctime>
#include <mutex>

namespace fw {
namespace {

std::mutex schloss;
FILE* datei = nullptr;

void schreibe(const char* stufe, const char* format, va_list argumente) {
    char text[2048];
    vsnprintf(text, sizeof(text), format, argumente);
    std::time_t jetzt = std::time(nullptr);
    std::tm zeit{};
    localtime_s(&zeit, &jetzt);
    char stempel[32];
    std::strftime(stempel, sizeof(stempel), "%H:%M:%S", &zeit);
    std::lock_guard<std::mutex> sperre(schloss);
    std::printf("[%s] %s %s\n", stempel, stufe, text);
    std::fflush(stdout);
    if (datei) {
        std::fprintf(datei, "[%s] %s %s\n", stempel, stufe, text);
        std::fflush(datei);
    }
}

}

void protokollDatei(const std::string& pfad) {
    std::lock_guard<std::mutex> sperre(schloss);
    if (datei) std::fclose(datei);
    fopen_s(&datei, pfad.c_str(), "w");
}

void notiz(const char* format, ...) {
    va_list argumente;
    va_start(argumente, format);
    schreibe("info", format, argumente);
    va_end(argumente);
}

void warnung(const char* format, ...) {
    va_list argumente;
    va_start(argumente, format);
    schreibe("warn", format, argumente);
    va_end(argumente);
}

void protokollSchliessen() {
    std::lock_guard<std::mutex> sperre(schloss);
    if (datei) {
        std::fclose(datei);
        datei = nullptr;
    }
}

}
