#pragma once

namespace fw {

enum class Klang { Glocke, Schritt, Platsch, Hammer, Ernte, Freude };

class Ton {
public:
    ~Ton();

    bool starten();
    void stoppen();

    void ereignis(Klang klang, float staerke = 1.0f);
    void stimmung(float wind, float wellen);
    void lautstaerke(float wert);
    bool laeuft() const { return aktiv; }

private:
    struct Stimme {
        bool frei = true;
        Klang art = Klang::Glocke;
        float phase = 0.0f;
        float frequenz = 440.0f;
        float alter = 0.0f;
        float dauer = 0.4f;
        float staerke = 1.0f;
    };

    void mischen(short* ziel, int anzahl);
    static unsigned long __stdcall faden(void* nutzer);

    void* geraet = nullptr;
    void* wecker = nullptr;
    void* fadenGriff = nullptr;
    bool aktiv = false;
    bool beenden = false;
    float meister = 0.5f;
    float windStaerke = 0.25f;
    float wellenStaerke = 0.3f;
    float wellenPhase = 0.0f;
    float windPhase = 0.0f;
    float rauschZustand = 0.0f;
    Stimme stimmen[12];
};

}
