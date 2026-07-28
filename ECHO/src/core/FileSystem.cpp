#include "FileSystem.h"
#include "Log.h"

#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#include <cstdio>

namespace echo {
namespace fs {

static std::string g_root;

static bool dirHas(const std::string& base, const char* probe) {
    DWORD a = GetFileAttributesA((base + "\\" + probe).c_str());
    return a != INVALID_FILE_ATTRIBUTES;
}

void init() {
    char buf[MAX_PATH];
    GetModuleFileNameA(nullptr, buf, MAX_PATH);
    std::string exe(buf);
    size_t slash = exe.find_last_of("\\/");
    std::string dir = slash == std::string::npos ? "." : exe.substr(0, slash);

    std::string candidate = dir;
    for (int i = 0; i < 4; i++) {
        if (dirHas(candidate, "shaders")) { g_root = candidate; return; }
        size_t s = candidate.find_last_of("\\/");
        if (s == std::string::npos) break;
        candidate = candidate.substr(0, s);
    }

    GetCurrentDirectoryA(MAX_PATH, buf);
    candidate = buf;
    for (int i = 0; i < 4; i++) {
        if (dirHas(candidate, "shaders")) { g_root = candidate; return; }
        size_t s = candidate.find_last_of("\\/");
        if (s == std::string::npos) break;
        candidate = candidate.substr(0, s);
    }
    g_root = dir;
}

const std::string& rootDir() { return g_root; }

std::string resolve(const std::string& relative) {
    if (relative.size() > 1 && (relative[1] == ':' || relative[0] == '\\' || relative[0] == '/')) return relative;
    return g_root + "\\" + relative;
}

bool exists(const std::string& path) {
    return GetFileAttributesA(resolve(path).c_str()) != INVALID_FILE_ATTRIBUTES;
}

bool readText(const std::string& path, std::string& out) {
    FILE* f = nullptr;
    fopen_s(&f, resolve(path).c_str(), "rb");
    if (!f) return false;
    std::fseek(f, 0, SEEK_END);
    long n = std::ftell(f);
    std::fseek(f, 0, SEEK_SET);
    out.resize((size_t)(n > 0 ? n : 0));
    if (n > 0) {
        size_t got = std::fread(out.data(), 1, (size_t)n, f);
        out.resize(got);
    }
    std::fclose(f);
    return true;
}

bool writeText(const std::string& path, const std::string& data) {
    FILE* f = nullptr;
    fopen_s(&f, resolve(path).c_str(), "wb");
    if (!f) return false;
    std::fwrite(data.data(), 1, data.size(), f);
    std::fclose(f);
    return true;
}

bool readBinary(const std::string& path, std::vector<u8>& out) {
    FILE* f = nullptr;
    fopen_s(&f, resolve(path).c_str(), "rb");
    if (!f) return false;
    std::fseek(f, 0, SEEK_END);
    long n = std::ftell(f);
    std::fseek(f, 0, SEEK_SET);
    out.resize((size_t)(n > 0 ? n : 0));
    if (n > 0) {
        size_t got = std::fread(out.data(), 1, (size_t)n, f);
        out.resize(got);
    }
    std::fclose(f);
    return true;
}

bool writeBinary(const std::string& path, const void* data, size_t size) {
    FILE* f = nullptr;
    fopen_s(&f, resolve(path).c_str(), "wb");
    if (!f) return false;
    std::fwrite(data, 1, size, f);
    std::fclose(f);
    return true;
}

bool makeDir(const std::string& path) {
    std::string p = resolve(path);
    return CreateDirectoryA(p.c_str(), nullptr) != 0 || GetLastError() == ERROR_ALREADY_EXISTS;
}

bool removeFile(const std::string& path) {
    return DeleteFileA(resolve(path).c_str()) != 0;
}

std::vector<std::string> listFiles(const std::string& dir, const std::string& ext) {
    std::vector<std::string> result;
    std::string pattern = resolve(dir) + "\\*" + ext;
    WIN32_FIND_DATAA fd;
    HANDLE h = FindFirstFileA(pattern.c_str(), &fd);
    if (h == INVALID_HANDLE_VALUE) return result;
    do {
        if (!(fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)) result.push_back(fd.cFileName);
    } while (FindNextFileA(h, &fd));
    FindClose(h);
    return result;
}

std::string parentPath(const std::string& path) {
    size_t s = path.find_last_of("\\/");
    return s == std::string::npos ? std::string(".") : path.substr(0, s);
}

}
}
