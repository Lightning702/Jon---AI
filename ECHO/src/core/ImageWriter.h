#pragma once

#include "Common.h"

namespace echo {

bool writePNG(const std::string& path, int width, int height, int channels, const u8* pixels, bool flipY);

}
