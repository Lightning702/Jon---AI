import json
import math
import os
import subprocess
import wave

import numpy as np

SR = 48000
HIER = os.path.dirname(os.path.abspath(__file__))
BAU = os.path.join(HIER, "bau")
os.makedirs(BAU, exist_ok=True)

SPRECHER = [
    (13.20, "Die meisten Assistenten reden."),
    (20.00, "Jon macht."),
    (25.90, "Er weiß, welcher Tag heute ist, und schaut nach, statt zu raten."),
    (51.40, "Am PC. Am Handy. Ohne Cloud, ohne Abo."),
    (76.30, "Und er kommt nicht allein."),
    (85.60, "Jon. Auf getjon Punkt info."),
]
UNTERTITEL = [
    "Die meisten Assistenten reden.",
    "Jon macht.",
    "Er weiß, welcher Tag heute ist — und schaut nach, statt zu raten.",
    "Am PC. Am Handy. Ohne Cloud, ohne Abo.",
    "Und er kommt nicht allein.",
    "Jon. Auf getjon.info.",
]

KLICK = [17.88, 19.00, 24.35, 33.65, 71.60]
GOLD = [21.40, 38.35, 47.00, 56.50, 62.70, 73.95]
BLIP = [1.55, 88.30]


def lies_wav(pfad):
    with wave.open(pfad, "rb") as w:
        n = w.getnframes()
        roh = w.readframes(n)
        breite = w.getsampwidth()
        kanaele = w.getnchannels()
        rate = w.getframerate()
    art = {1: np.int8, 2: np.int16, 4: np.int32}[breite]
    d = np.frombuffer(roh, dtype=art).astype(np.float64)
    d /= float(np.iinfo(art).max)
    if kanaele > 1:
        d = d.reshape(-1, kanaele).mean(axis=1)
    return d, rate


def schreib_wav(pfad, links, rechts):
    d = np.stack([links, rechts], axis=1)
    d = np.clip(d, -1.0, 1.0)
    roh = (d * 32767.0).astype(np.int16)
    with wave.open(pfad, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(roh.tobytes())


def sprecher_bauen():
    stimmen = []
    for i, (zeit, text) in enumerate(SPRECHER):
        roh = os.path.join(BAU, "vo%d-roh.wav" % i)
        fein = os.path.join(BAU, "vo%d.wav" % i)
        if not os.path.exists(roh):
            subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                 "-File", os.path.join(HIER, "stimme.ps1"),
                 "-Text", text, "-Ziel", roh],
                check=True, capture_output=True,
            )
        kette = (
            "asetrate=16000*0.93,aresample=48000,atempo=1/0.93,"
            "highpass=f=75,"
            "equalizer=f=150:t=q:w=1.0:g=2.6,"
            "equalizer=f=430:t=q:w=1.4:g=-1.6,"
            "equalizer=f=3100:t=q:w=1.6:g=-2.2,"
            "acompressor=threshold=0.1:ratio=3.2:attack=14:release=200:makeup=2,"
            "loudnorm=I=-17:TP=-2:LRA=8,"
            "aresample=48000"
        )
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", roh, "-af", kette, "-ac", "1", "-ar", "48000", fein],
            check=True,
        )
        d, r = lies_wav(fein)
        stimmen.append((zeit, d))
    return stimmen


def huell(n, an, ab, halten):
    e = np.ones(n)
    a = int(an * SR)
    b = int(ab * SR)
    if a > 0:
        e[:a] = np.linspace(0, 1, a) ** 1.6
    if b > 0:
        e[-b:] = np.linspace(1, 0, b) ** 1.6
    return e * halten


def falte(x, kern):
    n = len(x)
    m = len(kern)
    g = 1
    while g < n + m - 1:
        g <<= 1
    y = np.fft.irfft(np.fft.rfft(x, g) * np.fft.rfft(kern, g), g)
    versatz = (m - 1) // 2
    return y[versatz:versatz + n]


def tiefpass_schnell(x, fc):
    n = max(2, int(SR / (2 * math.pi * fc)))
    kern = np.exp(-np.arange(min(n * 4, 24000)) / n)
    kern /= kern.sum()
    return falte(x, kern)


def saege(f, t, unschaerfe=0.0):
    p = f * t + unschaerfe * np.sin(2 * math.pi * 0.07 * t)
    return 2.0 * (p - np.floor(p + 0.5))


def pad_akkord(t, grund, dauer_maske):
    verhaeltnis = [1.0, 1.5, 2.0, 3.0]
    aus = np.zeros_like(t)
    for k, v in enumerate(verhaeltnis):
        for d in (-0.06, 0.0, 0.07):
            aus += saege((grund * v) + d, t) * (0.5 ** (k * 0.9))
    aus /= 9.0
    return tiefpass_schnell(aus, 760) * dauer_maske


def glocke(f, dauer, laut=1.0):
    n = int(dauer * SR)
    t = np.arange(n) / SR
    teil = [(1.0, 1.0), (2.0, 0.42), (2.98, 0.22), (4.1, 0.1)]
    x = np.zeros(n)
    for v, a in teil:
        x += a * np.sin(2 * math.pi * f * v * t) * np.exp(-t * (2.4 + v * 0.9))
    ein = np.clip(t / 0.006, 0, 1)
    return x * ein * laut * 0.25


def klick():
    n = int(0.07 * SR)
    t = np.arange(n) / SR
    rausch = np.random.default_rng(7).normal(0, 1, n) * np.exp(-t * 130)
    ton = np.sin(2 * math.pi * 880 * t) * np.exp(-t * 46)
    return tiefpass_schnell(rausch * 0.5 + ton * 0.6, 2600) * 0.16


def blip():
    n = int(0.26 * SR)
    t = np.arange(n) / SR
    a = np.sin(2 * math.pi * 784 * t) * np.exp(-np.maximum(t - 0.0, 0) * 22) * (t < 0.11)
    b = np.sin(2 * math.pi * 1175 * t) * np.exp(-np.maximum(t - 0.1, 0) * 20) * (t >= 0.1)
    x = (a + b) * 0.3
    x += np.sin(2 * math.pi * 1568 * t) * np.exp(-t * 30) * 0.06
    return x


def musik(gesamt, kurz=False):
    n = int(gesamt * SR)
    t = np.arange(n) / SR
    links = np.zeros(n)
    rechts = np.zeros(n)

    start = 0.0 if kurz else 8.0
    voll = 1.2 if kurz else 13.0
    duenn = gesamt - 3.6 if kurz else 80.0
    schluss = gesamt - 0.6

    grund = np.clip((t - start) / 2.6, 0, 1)
    koerper = np.clip((t - voll) / 3.0, 0, 1)
    abbau = 1.0 - np.clip((t - duenn) / (schluss - duenn), 0, 1) * 0.72
    ende = 1.0 - np.clip((t - schluss) / 0.6, 0, 1)
    maske = grund * abbau * ende

    sub = np.sin(2 * math.pi * 55 * t + 0.6 * np.sin(2 * math.pi * 0.07 * t))
    sub += 0.3 * np.sin(2 * math.pi * 110 * t)
    puls = 0.72 + 0.28 * (0.5 + 0.5 * np.sin(2 * math.pi * (70 / 60.0) * t - 1.4))
    sub *= puls * maske * (0.34 + 0.2 * koerper)

    folge = [55.0, 43.65, 49.0, 65.41]
    takt = 6.857
    pad = np.zeros(n)
    for i in range(int(gesamt / takt) + 2):
        a = i * takt
        b = a + takt
        i0 = int(max(0, a) * SR)
        i1 = int(min(gesamt, b + 0.9) * SR)
        if i1 <= i0:
            continue
        lokal = t[i0:i1] - a
        form = np.clip(lokal / 1.3, 0, 1) * np.clip((takt + 0.9 - lokal) / 1.1, 0, 1)
        pad[i0:i1] += pad_akkord(t[i0:i1], folge[i % len(folge)] * 2, form)
    pad *= maske * (0.1 + 0.2 * koerper)

    luft = np.random.default_rng(3).normal(0, 1, n)
    luft = tiefpass_schnell(luft, 5200) - tiefpass_schnell(luft, 900)
    luft *= maske * 0.012 * (0.5 + 0.5 * koerper)

    schlag = np.zeros(n)
    schritt = 60.0 / 70.0 * 4
    i = 0
    while True:
        z = start + 0.4 + i * schritt
        if z > schluss:
            break
        p = int(z * SR)
        m = int(0.5 * SR)
        if p + m < n:
            lokal = np.arange(m) / SR
            f = 74 * np.exp(-lokal * 9) + 44
            schlag[p:p + m] += np.sin(2 * math.pi * np.cumsum(f) / SR) * np.exp(-lokal * 7.5) * 0.4
        i += 1
    schlag *= maske

    glocken = []
    if kurz:
        glocken = [(0.1, 880.0, 0.5), (4.0, 659.3, 0.42), (8.0, 880.0, 0.42), (12.0, 987.8, 0.42), (16.05, 1046.5, 0.7)]
    else:
        glocken = [
            (13.05, 880.0, 0.42), (23.0, 659.3, 0.3), (32.0, 784.0, 0.3), (41.0, 880.0, 0.3),
            (51.0, 659.3, 0.34), (60.0, 784.0, 0.3), (69.0, 880.0, 0.3), (76.0, 987.8, 0.38),
            (84.1, 1046.5, 0.62), (86.9, 784.0, 0.34),
        ]
    ton = sub + pad + luft + schlag
    for z, f, a in glocken:
        g = glocke(f, 3.4, a)
        p = int(z * SR)
        m = min(len(g), n - p)
        if m > 0:
            ton[p:p + m] += g[:m]

    breite = 0.14 * np.sin(2 * math.pi * 0.031 * t) + 0.06 * np.sin(2 * math.pi * 0.017 * t + 1.1)
    links += ton * (1.0 - breite)
    rechts += ton * (1.0 + breite)
    return links * 0.5, rechts * 0.5


def bau_lang():
    gesamt = 90.0
    n = int(gesamt * SR)
    stimmen = sprecher_bauen()

    ml, mr = musik(gesamt)

    stimme = np.zeros(n)
    for z, d in stimmen:
        p = int(z * SR)
        m = min(len(d), n - p)
        if m > 0:
            stimme[p:p + m] += d[:m]

    anwesend = (np.abs(stimme) > 0.004).astype(float)
    fenster = int(0.3 * SR)
    summe = np.concatenate([[0.0], np.cumsum(anwesend)])
    links_i = np.clip(np.arange(n) - fenster, 0, n)
    rechts_i = np.clip(np.arange(n) + fenster, 0, n)
    glatt = (summe[rechts_i] - summe[links_i]) / (rechts_i - links_i + 1)
    duck = 1.0 - 0.45 * np.clip(glatt * 3.0, 0, 1)

    effekt = np.zeros(n)
    k = klick()
    b = blip()
    for z in KLICK:
        p = int(z * SR)
        m = min(len(k), n - p)
        effekt[p:p + m] += k[:m]
    for z in GOLD:
        g = glocke(1318.5, 1.6, 0.42) + glocke(1975.5, 1.6, 0.2)
        p = int(z * SR)
        m = min(len(g), n - p)
        effekt[p:p + m] += g[:m] * 0.55
    for z in BLIP:
        p = int(z * SR)
        m = min(len(b), n - p)
        effekt[p:p + m] += b[:m]

    links = ml * duck + stimme * 0.92 + effekt
    rechts = mr * duck + stimme * 0.92 + effekt
    schreib_wav(os.path.join(BAU, "ton-lang-roh.wav"), links, rechts)

    zeilen = []
    for i, (z, d) in enumerate(stimmen):
        zeilen.append([round(z, 2), round(len(d) / SR, 2), UNTERTITEL[i]])
    with open(os.path.join(HIER, "js", "vo.js"), "w", encoding="utf-8") as f:
        f.write("window.VO = " + json.dumps(zeilen, ensure_ascii=False) + ";\n")
    print(json.dumps(zeilen, ensure_ascii=False, indent=1))


def bau_kurz():
    gesamt = 20.0
    n = int(gesamt * SR)
    ml, mr = musik(gesamt, kurz=True)
    effekt = np.zeros(n)
    k = klick()
    for z in (4.0, 8.0, 12.0, 16.0):
        p = int(z * SR)
        m = min(len(k), n - p)
        effekt[p:p + m] += k[:m] * 0.8
    b = blip()
    p = int(0.35 * SR)
    effekt[p:p + len(b)] += b
    schreib_wav(os.path.join(BAU, "ton-kurz-roh.wav"), ml + effekt, mr + effekt)


def meistern(quelle, ziel, ziel_lufs):
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", quelle,
         "-af", "loudnorm=I=%d:TP=-1.5:LRA=11,alimiter=limit=0.94,aresample=48000" % ziel_lufs,
         "-ar", "48000", "-ac", "2", ziel],
        check=True,
    )
    print("fertig:", ziel)


if __name__ == "__main__":
    bau_lang()
    bau_kurz()
    meistern(os.path.join(BAU, "ton-lang-roh.wav"), os.path.join(BAU, "ton-lang.wav"), -15)
    meistern(os.path.join(BAU, "ton-kurz-roh.wav"), os.path.join(BAU, "ton-kurz.wav"), -14)
