#pragma once

#include "Common.h"

namespace echo {
namespace fs {

void init();
const std::string& rootDir();
std::string resolve(const std::string& relative);
bool exists(const std::string& path);
bool readText(const std::string& path, std::string& out);
bool writeText(const std::string& path, const std::string& data);
bool readBinary(const std::string& path, std::vector<u8>& out);
bool writeBinary(const std::string& path, const void* data, size_t size);
bool makeDir(const std::string& path);
bool removeFile(const std::string& path);
std::vector<std::string> listFiles(const std::string& dir, const std::string& ext);
std::string parentPath(const std::string& path);

}
}
