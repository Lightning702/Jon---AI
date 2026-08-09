#pragma once

#include <string>

namespace fw {

void protokollDatei(const std::string& pfad);
void notiz(const char* format, ...);
void warnung(const char* format, ...);
void protokollSchliessen();

}
