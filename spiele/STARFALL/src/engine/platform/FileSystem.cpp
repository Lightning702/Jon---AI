#include "FileSystem.hpp"

#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>

#include <cstdio>

namespace sf {

bool FileSystem::exists(const std::string& path) {
    return GetFileAttributesA(path.c_str()) != INVALID_FILE_ATTRIBUTES;
}

bool FileSystem::isDirectory(const std::string& path) {
    const DWORD attributes = GetFileAttributesA(path.c_str());
    return attributes != INVALID_FILE_ATTRIBUTES && (attributes & FILE_ATTRIBUTE_DIRECTORY) != 0;
}

bool FileSystem::createDirectories(const std::string& path) {
    if (path.empty()) return false;
    std::string current;
    for (usize index = 0; index <= path.size(); ++index) {
        if (index == path.size() || path[index] == '/' || path[index] == '\\') {
            if (current.size() > 2) CreateDirectoryA(current.c_str(), nullptr);
            if (index == path.size()) break;
        }
        current.push_back(path[index]);
    }
    return isDirectory(path);
}

bool FileSystem::removeFile(const std::string& path) {
    return DeleteFileA(path.c_str()) != 0;
}

bool FileSystem::renameFile(const std::string& from, const std::string& to) {
    return MoveFileExA(from.c_str(), to.c_str(), MOVEFILE_REPLACE_EXISTING) != 0;
}

u64 FileSystem::fileSize(const std::string& path) {
    WIN32_FILE_ATTRIBUTE_DATA data;
    if (!GetFileAttributesExA(path.c_str(), GetFileExInfoStandard, &data)) return 0;
    return (static_cast<u64>(data.nFileSizeHigh) << 32) | data.nFileSizeLow;
}

u64 FileSystem::modifiedTime(const std::string& path) {
    WIN32_FILE_ATTRIBUTE_DATA data;
    if (!GetFileAttributesExA(path.c_str(), GetFileExInfoStandard, &data)) return 0;
    return (static_cast<u64>(data.ftLastWriteTime.dwHighDateTime) << 32) | data.ftLastWriteTime.dwLowDateTime;
}

Result<std::vector<u8>> FileSystem::readBinary(const std::string& path) {
    std::FILE* file = std::fopen(path.c_str(), "rb");
    if (!file) return resultError<std::vector<u8>>(StatusCode::NotFound, "Datei fehlt: " + path);
    std::fseek(file, 0, SEEK_END);
    const long size = std::ftell(file);
    std::fseek(file, 0, SEEK_SET);
    std::vector<u8> data(size > 0 ? static_cast<usize>(size) : 0);
    if (!data.empty()) {
        const usize read = std::fread(data.data(), 1, data.size(), file);
        data.resize(read);
    }
    std::fclose(file);
    return resultOk(std::move(data));
}

Result<std::string> FileSystem::readText(const std::string& path) {
    Result<std::vector<u8>> binary = readBinary(path);
    if (!binary) return Result<std::string>(binary.status());
    return resultOk(std::string(binary.value().begin(), binary.value().end()));
}

Status FileSystem::writeBinary(const std::string& path, const void* data, usize size) {
    std::FILE* file = std::fopen(path.c_str(), "wb");
    if (!file) return statusError(StatusCode::IoFailure, "Datei nicht schreibbar: " + path);
    if (size > 0) std::fwrite(data, 1, size, file);
    std::fclose(file);
    return statusOk();
}

Status FileSystem::writeText(const std::string& path, const std::string& text) {
    return writeBinary(path, text.data(), text.size());
}

Status FileSystem::writeAtomic(const std::string& path, const void* data, usize size) {
    const std::string temporary = path + ".tmp";
    const Status written = writeBinary(temporary, data, size);
    if (!written.ok()) return written;
    if (!renameFile(temporary, path)) {
        removeFile(temporary);
        return statusError(StatusCode::IoFailure, "Umbenennen fehlgeschlagen: " + path);
    }
    return statusOk();
}

std::vector<std::string> FileSystem::listFiles(const std::string& directory, const std::string& extensionFilter) {
    std::vector<std::string> results;
    const std::string pattern = directory + "\\*";
    WIN32_FIND_DATAA found;
    HANDLE handle = FindFirstFileA(pattern.c_str(), &found);
    if (handle == INVALID_HANDLE_VALUE) return results;
    do {
        if ((found.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) != 0) continue;
        const std::string name = found.cFileName;
        if (!extensionFilter.empty() && extension(name) != extensionFilter) continue;
        results.push_back(joinPath(directory, name));
    } while (FindNextFileA(handle, &found));
    FindClose(handle);
    return results;
}

std::string FileSystem::executableDirectory() {
    char buffer[MAX_PATH];
    const DWORD length = GetModuleFileNameA(nullptr, buffer, MAX_PATH);
    std::string full(buffer, length);
    const usize separator = full.find_last_of("\\/");
    return separator == std::string::npos ? std::string(".") : full.substr(0, separator);
}

std::string FileSystem::joinPath(const std::string& first, const std::string& second) {
    if (first.empty()) return second;
    if (second.empty()) return first;
    const char last = first[first.size() - 1];
    if (last == '/' || last == '\\') return first + second;
    return first + "\\" + second;
}

std::string FileSystem::fileName(const std::string& path) {
    const usize separator = path.find_last_of("\\/");
    return separator == std::string::npos ? path : path.substr(separator + 1);
}

std::string FileSystem::fileStem(const std::string& path) {
    const std::string name = fileName(path);
    const usize dot = name.find_last_of('.');
    return dot == std::string::npos ? name : name.substr(0, dot);
}

std::string FileSystem::extension(const std::string& path) {
    const std::string name = fileName(path);
    const usize dot = name.find_last_of('.');
    return dot == std::string::npos ? std::string() : name.substr(dot);
}

}
