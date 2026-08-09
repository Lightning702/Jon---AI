#include "Werkzeug.hpp"

#include <cstdio>
#include <fstream>
#include <sstream>

#include "GL.hpp"
#include "Protokoll.hpp"

namespace fw {
namespace {

double taktFrequenz() {
    LARGE_INTEGER takt;
    QueryPerformanceFrequency(&takt);
    return static_cast<double>(takt.QuadPart);
}

}

double jetzt() {
    static const double frequenz = taktFrequenz();
    LARGE_INTEGER zaehler;
    QueryPerformanceCounter(&zaehler);
    return static_cast<double>(zaehler.QuadPart) / frequenz;
}

void schlafen(int millisekunden) { Sleep(static_cast<DWORD>(millisekunden)); }

std::string ordnerNeben(const std::string& unterordner) {
    char pfad[MAX_PATH] = {};
    GetModuleFileNameA(nullptr, pfad, MAX_PATH);
    std::string voll(pfad);
    size_t schnitt = voll.find_last_of("\\/");
    std::string basis = schnitt == std::string::npos ? "." : voll.substr(0, schnitt);
    schnitt = basis.find_last_of("\\/");
    if (schnitt != std::string::npos) {
        std::string eltern = basis.substr(schnitt + 1);
        if (eltern == "bin" || eltern == "Bin") basis = basis.substr(0, schnitt);
    }
    if (unterordner.empty()) return basis;
    return basis + "\\" + unterordner;
}

bool ordnerAnlegen(const std::string& pfad) {
    if (CreateDirectoryA(pfad.c_str(), nullptr)) return true;
    return GetLastError() == ERROR_ALREADY_EXISTS;
}

std::string leseText(const std::string& pfad) {
    std::ifstream datei(pfad, std::ios::binary);
    if (!datei) return "";
    std::ostringstream strom;
    strom << datei.rdbuf();
    return strom.str();
}

bool schreibeText(const std::string& pfad, const std::string& inhalt) {
    std::ofstream datei(pfad, std::ios::binary | std::ios::trunc);
    if (!datei) return false;
    datei << inhalt;
    return true;
}

bool bildSchreiben(const std::string& pfad, int breite, int hoehe, const std::vector<unsigned char>& rgb) {
    if (breite <= 0 || hoehe <= 0) return false;
    const int zeile = breite * 3;
    const int fuellung = (4 - (zeile % 4)) % 4;
    const int datenGroesse = (zeile + fuellung) * hoehe;
    const int kopfGroesse = 54;
    std::vector<unsigned char> kopf(kopfGroesse, 0);
    kopf[0] = 'B';
    kopf[1] = 'M';
    const int gesamt = kopfGroesse + datenGroesse;
    kopf[2] = static_cast<unsigned char>(gesamt & 0xFF);
    kopf[3] = static_cast<unsigned char>((gesamt >> 8) & 0xFF);
    kopf[4] = static_cast<unsigned char>((gesamt >> 16) & 0xFF);
    kopf[5] = static_cast<unsigned char>((gesamt >> 24) & 0xFF);
    kopf[10] = static_cast<unsigned char>(kopfGroesse);
    kopf[14] = 40;
    kopf[18] = static_cast<unsigned char>(breite & 0xFF);
    kopf[19] = static_cast<unsigned char>((breite >> 8) & 0xFF);
    kopf[20] = static_cast<unsigned char>((breite >> 16) & 0xFF);
    kopf[21] = static_cast<unsigned char>((breite >> 24) & 0xFF);
    kopf[22] = static_cast<unsigned char>(hoehe & 0xFF);
    kopf[23] = static_cast<unsigned char>((hoehe >> 8) & 0xFF);
    kopf[24] = static_cast<unsigned char>((hoehe >> 16) & 0xFF);
    kopf[25] = static_cast<unsigned char>((hoehe >> 24) & 0xFF);
    kopf[26] = 1;
    kopf[28] = 24;
    std::ofstream datei(pfad, std::ios::binary | std::ios::trunc);
    if (!datei) return false;
    datei.write(reinterpret_cast<const char*>(kopf.data()), kopfGroesse);
    std::vector<unsigned char> puffer(zeile + fuellung, 0);
    for (int y = 0; y < hoehe; ++y) {
        const unsigned char* quelle = rgb.data() + static_cast<size_t>(y) * zeile;
        for (int x = 0; x < breite; ++x) {
            puffer[x * 3 + 0] = quelle[x * 3 + 2];
            puffer[x * 3 + 1] = quelle[x * 3 + 1];
            puffer[x * 3 + 2] = quelle[x * 3 + 0];
        }
        datei.write(reinterpret_cast<const char*>(puffer.data()), zeile + fuellung);
    }
    return true;
}

bool bildschirmfoto(const std::string& pfad, int breite, int hoehe) {
    if (breite <= 0 || hoehe <= 0) return false;
    std::vector<unsigned char> bild(static_cast<size_t>(breite) * hoehe * 3);
    glPixelStorei(GL_PACK_ALIGNMENT, 1);
    glReadPixels(0, 0, breite, hoehe, GL_RGB, GL_UNSIGNED_BYTE, bild.data());
    if (!bildSchreiben(pfad, breite, hoehe, bild)) {
        warnung("Bild %s liess sich nicht schreiben", pfad.c_str());
        return false;
    }
    notiz("Bild gespeichert: %s", pfad.c_str());
    return true;
}

std::vector<std::string> zerlegen(const std::string& text, char trenner) {
    std::vector<std::string> teile;
    std::string aktuell;
    for (char c : text) {
        if (c == trenner) {
            teile.push_back(aktuell);
            aktuell.clear();
        } else {
            aktuell.push_back(c);
        }
    }
    teile.push_back(aktuell);
    return teile;
}

std::string putzen(const std::string& text) {
    size_t anfang = text.find_first_not_of(" \t\r\n");
    if (anfang == std::string::npos) return "";
    size_t ende = text.find_last_not_of(" \t\r\n");
    return text.substr(anfang, ende - anfang + 1);
}

}
