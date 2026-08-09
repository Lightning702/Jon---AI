#include "Ton.hpp"

#include <windows.h>

#include <mmsystem.h>

#include <cmath>
#include <cstring>

#include "Mathe.hpp"
#include "Protokoll.hpp"
#include "Zufall.hpp"

namespace fw {
namespace {

constexpr int RATE = 22050;
constexpr int BLOCK = 1024;
constexpr int BLOECKE = 4;

WAVEHDR koepfe[BLOECKE] = {};
short daten[BLOECKE][BLOCK] = {};
Zufall wuerfel(0xC0FFEEull);

float grundton(Klang klang) {
    switch (klang) {
        case Klang::Glocke: return 784.0f;
        case Klang::Schritt: return 150.0f;
        case Klang::Platsch: return 320.0f;
        case Klang::Hammer: return 210.0f;
        case Klang::Ernte: return 520.0f;
        case Klang::Freude: return 660.0f;
    }
    return 440.0f;
}

float dauerVon(Klang klang) {
    switch (klang) {
        case Klang::Glocke: return 1.6f;
        case Klang::Schritt: return 0.12f;
        case Klang::Platsch: return 0.35f;
        case Klang::Hammer: return 0.28f;
        case Klang::Ernte: return 0.5f;
        case Klang::Freude: return 1.1f;
    }
    return 0.4f;
}

}

Ton::~Ton() { stoppen(); }

bool Ton::starten() {
    if (aktiv) return true;
    WAVEFORMATEX format = {};
    format.wFormatTag = WAVE_FORMAT_PCM;
    format.nChannels = 1;
    format.nSamplesPerSec = RATE;
    format.wBitsPerSample = 16;
    format.nBlockAlign = 2;
    format.nAvgBytesPerSec = RATE * 2;

    wecker = CreateEventA(nullptr, FALSE, FALSE, nullptr);
    HWAVEOUT ausgang = nullptr;
    MMRESULT ergebnis = waveOutOpen(&ausgang, WAVE_MAPPER, &format,
                                    reinterpret_cast<DWORD_PTR>(wecker), 0, CALLBACK_EVENT);
    if (ergebnis != MMSYSERR_NOERROR) {
        warnung("Kein Tonausgang gefunden, es bleibt still");
        CloseHandle(static_cast<HANDLE>(wecker));
        wecker = nullptr;
        return false;
    }
    geraet = ausgang;
    for (int i = 0; i < BLOECKE; ++i) {
        std::memset(&koepfe[i], 0, sizeof(WAVEHDR));
        std::memset(daten[i], 0, sizeof(daten[i]));
        koepfe[i].lpData = reinterpret_cast<LPSTR>(daten[i]);
        koepfe[i].dwBufferLength = BLOCK * sizeof(short);
        waveOutPrepareHeader(ausgang, &koepfe[i], sizeof(WAVEHDR));
        koepfe[i].dwFlags |= WHDR_DONE;
    }
    aktiv = true;
    beenden = false;
    fadenGriff = CreateThread(nullptr, 0, faden, this, 0, nullptr);
    return true;
}

void Ton::stoppen() {
    if (!aktiv) return;
    beenden = true;
    if (wecker) SetEvent(static_cast<HANDLE>(wecker));
    if (fadenGriff) {
        WaitForSingleObject(static_cast<HANDLE>(fadenGriff), 800);
        CloseHandle(static_cast<HANDLE>(fadenGriff));
        fadenGriff = nullptr;
    }
    HWAVEOUT ausgang = static_cast<HWAVEOUT>(geraet);
    if (ausgang) {
        waveOutReset(ausgang);
        for (int i = 0; i < BLOECKE; ++i) waveOutUnprepareHeader(ausgang, &koepfe[i], sizeof(WAVEHDR));
        waveOutClose(ausgang);
    }
    geraet = nullptr;
    if (wecker) {
        CloseHandle(static_cast<HANDLE>(wecker));
        wecker = nullptr;
    }
    aktiv = false;
}

void Ton::lautstaerke(float wert) { meister = klemme(wert, 0.0f, 1.0f); }

void Ton::stimmung(float wind, float wellen) {
    windStaerke = klemme(wind, 0.0f, 1.0f);
    wellenStaerke = klemme(wellen, 0.0f, 1.0f);
}

void Ton::ereignis(Klang klang, float staerke) {
    for (Stimme& stimme : stimmen) {
        if (!stimme.frei) continue;
        stimme.frei = false;
        stimme.art = klang;
        stimme.phase = 0.0f;
        stimme.alter = 0.0f;
        stimme.dauer = dauerVon(klang);
        stimme.frequenz = grundton(klang) * wuerfel.bereich(0.96f, 1.05f);
        stimme.staerke = klemme(staerke, 0.0f, 1.5f);
        return;
    }
}

void Ton::mischen(short* ziel, int anzahl) {
    const float schritt = 1.0f / RATE;
    for (int i = 0; i < anzahl; ++i) {
        wellenPhase += schritt * 0.13f;
        windPhase += schritt * 0.07f;
        if (wellenPhase > 1.0f) wellenPhase -= 1.0f;
        if (windPhase > 1.0f) windPhase -= 1.0f;
        float rauschen = wuerfel.einheit() * 2.0f - 1.0f;
        rauschZustand = rauschZustand * 0.94f + rauschen * 0.06f;
        float brandung = rauschZustand * (0.45f + 0.55f * std::sin(wellenPhase * TAU)) * wellenStaerke;
        float wind = rauschZustand * (0.35f + 0.3f * std::sin(windPhase * TAU * 0.6f)) * windStaerke * 0.6f;
        float summe = brandung * 0.5f + wind * 0.4f;

        for (Stimme& stimme : stimmen) {
            if (stimme.frei) continue;
            float t = stimme.alter / stimme.dauer;
            if (t >= 1.0f) {
                stimme.frei = true;
                continue;
            }
            float huelle = std::exp(-3.2f * t) * (1.0f - t);
            float wert = 0.0f;
            switch (stimme.art) {
                case Klang::Glocke:
                case Klang::Freude:
                    wert = std::sin(stimme.phase * TAU) * 0.6f +
                           std::sin(stimme.phase * TAU * 2.01f) * 0.25f +
                           std::sin(stimme.phase * TAU * 3.02f) * 0.12f;
                    break;
                case Klang::Ernte:
                    wert = std::sin(stimme.phase * TAU) * 0.5f +
                           std::sin(stimme.phase * TAU * 1.5f) * 0.3f;
                    break;
                case Klang::Schritt:
                case Klang::Hammer:
                    wert = (wuerfel.einheit() * 2.0f - 1.0f) * 0.5f +
                           std::sin(stimme.phase * TAU) * 0.5f;
                    break;
                case Klang::Platsch:
                    wert = (wuerfel.einheit() * 2.0f - 1.0f) * (1.0f - t);
                    break;
            }
            summe += wert * huelle * stimme.staerke * 0.35f;
            stimme.phase += stimme.frequenz * schritt;
            if (stimme.phase > 1.0f) stimme.phase -= std::floor(stimme.phase);
            stimme.alter += schritt;
        }

        float endwert = klemme(summe * meister, -1.0f, 1.0f);
        ziel[i] = static_cast<short>(endwert * 30000.0f);
    }
}

unsigned long __stdcall Ton::faden(void* nutzer) {
    Ton* ton = static_cast<Ton*>(nutzer);
    HWAVEOUT ausgang = static_cast<HWAVEOUT>(ton->geraet);
    while (!ton->beenden) {
        bool gearbeitet = false;
        for (int i = 0; i < BLOECKE; ++i) {
            if (!(koepfe[i].dwFlags & WHDR_DONE)) continue;
            ton->mischen(daten[i], BLOCK);
            koepfe[i].dwFlags &= ~WHDR_DONE;
            koepfe[i].dwBufferLength = BLOCK * sizeof(short);
            waveOutWrite(ausgang, &koepfe[i], sizeof(WAVEHDR));
            gearbeitet = true;
        }
        if (!gearbeitet) WaitForSingleObject(static_cast<HANDLE>(ton->wecker), 20);
    }
    return 0;
}

}
