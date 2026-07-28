#pragma once

#include <cstdint>
#include <cstddef>
#include <cstring>
#include <string>
#include <vector>
#include <unordered_map>
#include <memory>
#include <algorithm>

typedef int8_t   i8;
typedef int16_t  i16;
typedef int32_t  i32;
typedef int64_t  i64;
typedef uint8_t  u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef uint64_t u64;
typedef float    f32;
typedef double   f64;

#define ECHO_TITLE "ECHO"
#define ECHO_STUDIO "FelWorks"
#define ECHO_VERSION "1.0.0"

template <typename T> using Ref = std::shared_ptr<T>;
template <typename T> using Scope = std::unique_ptr<T>;
