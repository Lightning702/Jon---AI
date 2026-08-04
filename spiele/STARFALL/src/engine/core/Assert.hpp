#pragma once

#include "Log.hpp"

#include <cstdlib>

namespace sf {

inline void reportAssertion(const char* expression, const char* file, int line, const char* message) {
    logFatal("assert", "%s (%s:%d) %s", expression, file, line, message ? message : "");
    logShutdown();
    std::abort();
}

}

#define SF_ASSERT(expression)                                                        \
    do {                                                                             \
        if (!(expression)) ::sf::reportAssertion(#expression, __FILE__, __LINE__, ""); \
    } while (false)

#define SF_ASSERT_MSG(expression, message)                                                \
    do {                                                                                  \
        if (!(expression)) ::sf::reportAssertion(#expression, __FILE__, __LINE__, message); \
    } while (false)

#ifdef NDEBUG
#define SF_DEBUG_ASSERT(expression) ((void)0)
#else
#define SF_DEBUG_ASSERT(expression) SF_ASSERT(expression)
#endif
