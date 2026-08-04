#pragma once

#include "../core/Types.hpp"

namespace sf {

constexpr u32 kGlyphFirst = 32;
constexpr u32 kGlyphCount = 96;
constexpr u32 kGlyphColumns = 5;
constexpr u32 kGlyphRows = 7;

const u8* glyphColumns(u32 codepoint);
bool glyphExists(u32 codepoint);
u32 mapExtendedCharacter(u32 codepoint);

}
