#pragma once

#include "Types.hpp"

#include <string>

namespace sf {

enum class LogLevel : u32 {
    Trace = 0,
    Debug = 1,
    Info = 2,
    Warning = 3,
    Error = 4,
    Fatal = 5
};

void logInit(const std::string& filePath, bool structuredOutput);
void logShutdown();
void logSetMinimumLevel(LogLevel level);
LogLevel logMinimumLevel();
void logWrite(LogLevel level, const char* category, const char* format, ...);
void logFlush();

void logTrace(const char* category, const char* format, ...);
void logDebug(const char* category, const char* format, ...);
void logInfo(const char* category, const char* format, ...);
void logWarning(const char* category, const char* format, ...);
void logError(const char* category, const char* format, ...);
void logFatal(const char* category, const char* format, ...);

}
