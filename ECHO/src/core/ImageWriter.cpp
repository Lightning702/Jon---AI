#include "ImageWriter.h"

#include <cstdio>

namespace echo {

namespace {

u32 crcTable[256];
bool crcReady = false;

void initCrc() {
    for (u32 n = 0; n < 256; n++) {
        u32 c = n;
        for (int k = 0; k < 8; k++) c = (c & 1) ? (0xEDB88320u ^ (c >> 1)) : (c >> 1);
        crcTable[n] = c;
    }
    crcReady = true;
}

u32 crc32(const u8* data, size_t len, u32 crc = 0xFFFFFFFFu) {
    if (!crcReady) initCrc();
    for (size_t i = 0; i < len; i++) crc = crcTable[(crc ^ data[i]) & 0xFF] ^ (crc >> 8);
    return crc;
}

void push32(std::vector<u8>& v, u32 value) {
    v.push_back((u8)(value >> 24));
    v.push_back((u8)(value >> 16));
    v.push_back((u8)(value >> 8));
    v.push_back((u8)value);
}

void writeChunk(std::vector<u8>& out, const char* type, const std::vector<u8>& data) {
    push32(out, (u32)data.size());
    size_t start = out.size();
    out.insert(out.end(), type, type + 4);
    out.insert(out.end(), data.begin(), data.end());
    u32 crc = crc32(out.data() + start, out.size() - start) ^ 0xFFFFFFFFu;
    push32(out, crc);
}

}

bool writePNG(const std::string& path, int width, int height, int channels, const u8* pixels, bool flipY) {
    if (width <= 0 || height <= 0 || !pixels) return false;
    if (channels != 3 && channels != 4) return false;

    std::vector<u8> raw;
    raw.reserve((size_t)height * (width * channels + 1));
    for (int y = 0; y < height; y++) {
        int srcY = flipY ? (height - 1 - y) : y;
        raw.push_back(0);
        const u8* row = pixels + (size_t)srcY * width * channels;
        raw.insert(raw.end(), row, row + (size_t)width * channels);
    }

    std::vector<u8> z;
    z.push_back(0x78);
    z.push_back(0x01);

    const size_t maxBlock = 65535;
    size_t pos = 0;
    while (pos < raw.size()) {
        size_t n = std::min(maxBlock, raw.size() - pos);
        bool last = (pos + n) >= raw.size();
        z.push_back(last ? 1 : 0);
        z.push_back((u8)(n & 0xFF));
        z.push_back((u8)((n >> 8) & 0xFF));
        z.push_back((u8)(~n & 0xFF));
        z.push_back((u8)((~n >> 8) & 0xFF));
        z.insert(z.end(), raw.begin() + pos, raw.begin() + pos + n);
        pos += n;
    }

    u32 a = 1, b = 0;
    for (size_t i = 0; i < raw.size(); i++) {
        a = (a + raw[i]) % 65521;
        b = (b + a) % 65521;
    }
    push32(z, (b << 16) | a);

    std::vector<u8> png = { 0x89, 'P', 'N', 'G', 0x0D, 0x0A, 0x1A, 0x0A };

    std::vector<u8> ihdr;
    push32(ihdr, (u32)width);
    push32(ihdr, (u32)height);
    ihdr.push_back(8);
    ihdr.push_back(channels == 4 ? 6 : 2);
    ihdr.push_back(0);
    ihdr.push_back(0);
    ihdr.push_back(0);
    writeChunk(png, "IHDR", ihdr);
    writeChunk(png, "IDAT", z);
    writeChunk(png, "IEND", {});

    FILE* f = nullptr;
    fopen_s(&f, path.c_str(), "wb");
    if (!f) return false;
    std::fwrite(png.data(), 1, png.size(), f);
    std::fclose(f);
    return true;
}

}
