#pragma once

#include <string>
#include <vector>

namespace fw {

double jetzt();
void schlafen(int millisekunden);

std::string ordnerNeben(const std::string& unterordner);
bool ordnerAnlegen(const std::string& pfad);

std::string leseText(const std::string& pfad);
bool schreibeText(const std::string& pfad, const std::string& inhalt);

bool bildSchreiben(const std::string& pfad, int breite, int hoehe, const std::vector<unsigned char>& rgb);
bool bildschirmfoto(const std::string& pfad, int breite, int hoehe);

std::vector<std::string> zerlegen(const std::string& text, char trenner);
std::string putzen(const std::string& text);

}
