#pragma once

#include "../core/Result.hpp"

#include <string>
#include <vector>

namespace sf {

class FileSystem {
public:
    static bool exists(const std::string& path);
    static bool isDirectory(const std::string& path);
    static bool createDirectories(const std::string& path);
    static bool removeFile(const std::string& path);
    static bool renameFile(const std::string& from, const std::string& to);
    static u64 fileSize(const std::string& path);
    static u64 modifiedTime(const std::string& path);

    static Result<std::vector<u8>> readBinary(const std::string& path);
    static Result<std::string> readText(const std::string& path);
    static Status writeBinary(const std::string& path, const void* data, usize size);
    static Status writeText(const std::string& path, const std::string& text);
    static Status writeAtomic(const std::string& path, const void* data, usize size);

    static std::vector<std::string> listFiles(const std::string& directory, const std::string& extension);

    static std::string executableDirectory();
    static std::string joinPath(const std::string& first, const std::string& second);
    static std::string fileName(const std::string& path);
    static std::string fileStem(const std::string& path);
    static std::string extension(const std::string& path);
};

}
