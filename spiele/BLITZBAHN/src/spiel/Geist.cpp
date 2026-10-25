#include "Geist.hpp"

#include <cstdio>
#include <sstream>

namespace blitzbahn {

using namespace fw;

void Geist::leeren() { proben.clear(); }

void Geist::aufnehmen(const Lage& lage) {
    if (proben.size() < 60000) proben.push_back(lage);
}

Lage Geist::bei(float zeit) const {
    if (proben.empty()) return Lage();
    float stelle = zeit / GEIST_TAKT;
    if (stelle <= 0.0f) return proben.front();
    size_t a = static_cast<size_t>(stelle);
    if (a + 1 >= proben.size()) return proben.back();
    float t = stelle - static_cast<float>(a);
    const Lage& p = proben[a];
    const Lage& q = proben[a + 1];
    Lage l;
    l.ort = mische(p.ort, q.ort, t);
    l.vorne = normiert(mische(p.vorne, q.vorne, t));
    l.oben = normiert(mische(p.oben, q.oben, t));
    return l;
}

std::string Geist::speichern(int zeitMs) const {
    std::ostringstream aus;
    aus << "GEIST 1 " << zeitMs << " " << proben.size() << "\n";
    char zeile[200];
    for (const Lage& l : proben) {
        std::snprintf(zeile, sizeof(zeile), "%.2f %.2f %.2f %.3f %.3f %.3f %.3f %.3f %.3f\n", l.ort.x, l.ort.y, l.ort.z,
                      l.vorne.x, l.vorne.y, l.vorne.z, l.oben.x, l.oben.y, l.oben.z);
        aus << zeile;
    }
    return aus.str();
}

bool Geist::laden(const std::string& text, Geist& ziel, int& zeitMs) {
    std::istringstream ein(text);
    std::string kopf;
    int version = 0;
    size_t anzahl = 0;
    if (!(ein >> kopf >> version >> zeitMs >> anzahl) || kopf != "GEIST") return false;
    Geist neu;
    for (size_t i = 0; i < anzahl; ++i) {
        Lage l;
        if (!(ein >> l.ort.x >> l.ort.y >> l.ort.z >> l.vorne.x >> l.vorne.y >> l.vorne.z >> l.oben.x >> l.oben.y >>
              l.oben.z))
            break;
        neu.proben.push_back(l);
    }
    if (neu.proben.empty()) return false;
    ziel = neu;
    return true;
}

}
