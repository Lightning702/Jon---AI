#pragma once

#include <cstddef>
#include <cstdint>

namespace sf {

using i8 = std::int8_t;
using i16 = std::int16_t;
using i32 = std::int32_t;
using i64 = std::int64_t;
using u8 = std::uint8_t;
using u16 = std::uint16_t;
using u32 = std::uint32_t;
using u64 = std::uint64_t;
using f32 = float;
using f64 = double;
using usize = std::size_t;
using isize = std::ptrdiff_t;

constexpr u32 kInvalidIndex32 = 0xFFFFFFFFu;
constexpr u64 kInvalidIndex64 = 0xFFFFFFFFFFFFFFFFull;

constexpr f64 kSpeedOfLight = 299792458.0;
constexpr f64 kGravitationalConstant = 6.67430e-11;
constexpr f64 kSolarMass = 1.98847e30;
constexpr f64 kAstronomicalUnit = 1.495978707e11;
constexpr f64 kLightYear = 9.4607304725808e15;
constexpr f64 kStefanBoltzmann = 5.670374419e-8;
constexpr f64 kEarthRadius = 6371000.0;
constexpr f64 kEarthMass = 5.9722e24;

template <typename T>
constexpr T alignUp(T value, T alignment) {
    return (value + alignment - T(1)) & ~(alignment - T(1));
}

template <typename T>
constexpr bool isPowerOfTwo(T value) {
    return value != T(0) && (value & (value - T(1))) == T(0);
}

}
