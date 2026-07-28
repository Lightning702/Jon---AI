#pragma once

#include "Common.h"

namespace echo {

enum class LogLevel { Trace, Info, Warn, Error };

void logInit(const char* file);
void logShutdown();
void logWrite(LogLevel lv, const char* fmt, ...);

#define LOG_TRACE(...) ::echo::logWrite(::echo::LogLevel::Trace, __VA_ARGS__)
#define LOG_INFO(...)  ::echo::logWrite(::echo::LogLevel::Info,  __VA_ARGS__)
#define LOG_WARN(...)  ::echo::logWrite(::echo::LogLevel::Warn,  __VA_ARGS__)
#define LOG_ERROR(...) ::echo::logWrite(::echo::LogLevel::Error, __VA_ARGS__)

}
