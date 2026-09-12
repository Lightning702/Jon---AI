from __future__ import annotations

from app.core.fehler import leise

P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"
P14_NS = "http://schemas.microsoft.com/office/powerpoint/2010/main"
P159_NS = "http://schemas.microsoft.com/office/powerpoint/2015/09/main"

EINFACH = {
    "fade": "<p:fade/>",
    "cut": "<p:cut/>",
    "dissolve": "<p:dissolve/>",
    "wipe": '<p:wipe dir="d"/>',
    "wipe_rechts": '<p:wipe dir="r"/>',
    "push": '<p:push dir="u"/>',
    "push_links": '<p:push dir="l"/>',
    "cover": '<p:cover dir="d"/>',
    "pull": '<p:pull dir="d"/>',
    "split": '<p:split orient="horz" dir="out"/>',
    "wheel": '<p:wheel spokes="4"/>',
    "random": "<p:random/>",
    "blinds": '<p:blinds dir="horz"/>',
    "checker": '<p:checker dir="horz"/>',
    "comb": '<p:comb dir="horz"/>',
    "zoom": '<p:zoom dir="in"/>',
    "newsflash": "<p:newsflash/>",
}

MODERN = {
    "morph": '<p159:morph option="byObject"/>',
    "glitter": '<p14:glitter dir="l" pattern="hexagon"/>',
    "ripple": '<p14:ripple/>',
    "honeycomb": "<p14:honeycomb/>",
    "vortex": '<p14:vortex dir="l"/>',
    "shred": '<p14:shred pattern="strip" dir="in"/>',
    "flash": "<p14:flash/>",
    "switch": '<p14:switch dir="r"/>',
    "flip": '<p14:flip dir="l"/>',
    "gallery": '<p14:gallery dir="l"/>',
    "reveal": '<p14:reveal dir="l" thruBlk="0"/>',
    "wind": '<p14:wind dir="l"/>',
    "prestige": "<p14:prestige/>",
    "fracture": "<p14:fracture/>",
}

GESCHWINDIGKEIT = {"langsam": "slow", "mittel": "med", "schnell": "fast"}

EINGANG = {
    "fade": (10, "fade", 500),
    "wipe": (22, "wipe(up)", 500),
    "wipe_links": (22, "wipe(left)", 500),
    "blind": (3, "blinds(horizontal)", 500),
    "box": (4, "box(in)", 500),
    "circle": (6, "circle(in)", 500),
    "dissolve": (9, "dissolveIn", 500),
    "plus": (13, "plus(in)", 500),
    "split": (17, "barn(inVertical)", 500),
    "wedge": (21, "wedge", 500),
    "zoom": (23, "zoom(in)", 500),
    "random": (1, "randomBar(horizontal)", 500),
}

FOLGE_UEBERGAENGE = (
    "fade",
    "push",
    "wipe",
    "fade",
    "cover",
    "fade",
    "split",
    "push_links",
)


def _element(xml: str):
    import re

    from pptx.oxml import parse_xml

    kopf = (
        f'xmlns:p="{P_NS}" xmlns:a="{A_NS}" xmlns:mc="{MC_NS}" '
        f'xmlns:p14="{P14_NS}" xmlns:p159="{P159_NS}"'
    )
    return parse_xml(re.sub(r"^<([a-zA-Z0-9:]+)", rf"<\1 {kopf}", xml.strip(), count=1))


def _entfernen(slide, kurzname: str) -> None:
    wurzel = slide._element
    for kind in list(wurzel):
        if kind.tag == f"{{{P_NS}}}{kurzname}":
            wurzel.remove(kind)


def uebergang(slide, art: str = "fade", tempo: str = "mittel") -> bool:
    name = str(art or "fade").strip().lower()
    speed = GESCHWINDIGKEIT.get(str(tempo).strip().lower(), "med")
    if name in ("keiner", "kein", "none", ""):
        _entfernen(slide, "transition")
        return True
    if name in EINFACH:
        roh = f'<p:transition spd="{speed}">{EINFACH[name]}</p:transition>'
    elif name in MODERN:
        inner = MODERN[name]
        marke = "p159" if name == "morph" else "p14"
        roh = (
            f'<p:transition spd="{speed}">'
            f"<mc:AlternateContent>"
            f'<mc:Choice Requires="{marke}">{inner}</mc:Choice>'
            f"<mc:Fallback><p:fade/></mc:Fallback>"
            f"</mc:AlternateContent>"
            f"</p:transition>"
        )
    else:
        return False
    try:
        _entfernen(slide, "transition")
        wurzel = slide._element
        neu = _element(roh)
        timing = wurzel.find(f"{{{P_NS}}}timing")
        if timing is not None:
            timing.addprevious(neu)
        else:
            wurzel.append(neu)
        return True
    except Exception as fehler:
        leise(fehler, "services/pptx_effekte")
        return False


class _Zaehler:
    def __init__(self, start: int = 2) -> None:
        self.wert = start

    def naechste(self) -> int:
        self.wert += 1
        return self.wert


def _effekt_block(
    zaehler: _Zaehler,
    form_id: int,
    preset: int,
    filter_: str,
    dauer: int,
    knoten: str,
    verzoegerung: int,
    absatz: int | None,
) -> str:
    a, b, c, d, e = (zaehler.naechste() for _ in range(5))
    ziel = f'<p:spTgt spid="{form_id}"/>'
    if absatz is not None:
        ziel = (
            f'<p:spTgt spid="{form_id}"><p:txEl>'
            f'<p:pRg st="{absatz}" end="{absatz}"/>'
            f"</p:txEl></p:spTgt>"
        )
    return (
        f'<p:par><p:cTn id="{a}" fill="hold">'
        f'<p:stCondLst><p:cond delay="{verzoegerung}"/></p:stCondLst>'
        f"<p:childTnLst>"
        f'<p:par><p:cTn id="{b}" fill="hold">'
        f'<p:stCondLst><p:cond delay="0"/></p:stCondLst>'
        f"<p:childTnLst>"
        f'<p:par><p:cTn id="{c}" presetID="{preset}" presetClass="entr" '
        f'presetSubtype="0" fill="hold" grpId="0" nodeType="{knoten}">'
        f'<p:stCondLst><p:cond delay="0"/></p:stCondLst>'
        f"<p:childTnLst>"
        f"<p:set><p:cBhvr>"
        f'<p:cTn id="{d}" dur="1" fill="hold">'
        f'<p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>'
        f"<p:tgtEl>{ziel}</p:tgtEl>"
        f"<p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst>"
        f"</p:cBhvr><p:to><p:strVal val=\"visible\"/></p:to></p:set>"
        f'<p:animEffect transition="in" filter="{filter_}">'
        f'<p:cBhvr><p:cTn id="{e}" dur="{dauer}"/>'
        f"<p:tgtEl>{ziel}</p:tgtEl></p:cBhvr></p:animEffect>"
        f"</p:childTnLst></p:cTn></p:par>"
        f"</p:childTnLst></p:cTn></p:par>"
        f"</p:childTnLst></p:cTn></p:par>"
    )


def animieren(slide, auftraege: list[dict]) -> int:
    gefiltert = [a for a in auftraege if a.get("form") is not None]
    if not gefiltert:
        return 0
    zaehler = _Zaehler()
    bloecke: list[str] = []
    bauteile: list[str] = []
    for stelle, auftrag in enumerate(gefiltert):
        form = auftrag["form"]
        preset, filter_, standard = EINGANG.get(
            str(auftrag.get("effekt", "fade")).lower(), EINGANG["fade"]
        )
        dauer = int(auftrag.get("dauer", standard) or standard)
        verzoegerung = int(auftrag.get("verzoegerung", 0) or 0)
        knoten = "clickEffect" if stelle == 0 else str(
            auftrag.get("start", "afterEffect")
        )
        absatz = auftrag.get("absatz")
        try:
            form_id = int(form.shape_id)
        except Exception as fehler:
            leise(fehler, "services/pptx_effekte")
            continue
        bloecke.append(
            _effekt_block(
                zaehler,
                form_id,
                preset,
                filter_,
                dauer,
                knoten,
                verzoegerung,
                absatz if isinstance(absatz, int) else None,
            )
        )
        if auftrag.get("absatzweise"):
            bauteile.append(f'<p:bldP spid="{form_id}" grpId="0" build="p"/>')
    if not bloecke:
        return 0
    aufbau = f"<p:bldLst>{''.join(bauteile)}</p:bldLst>" if bauteile else ""
    roh = (
        "<p:timing><p:tnLst>"
        '<p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot">'
        "<p:childTnLst>"
        '<p:seq concurrent="1" nextAc="seek">'
        '<p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>'
        + "".join(bloecke)
        + "</p:childTnLst></p:cTn>"
        '<p:prevCondLst><p:cond evt="onPrev" delay="0">'
        "<p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>"
        '<p:nextCondLst><p:cond evt="onNext" delay="0">'
        "<p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst>"
        "</p:seq>"
        "</p:childTnLst></p:cTn></p:par>"
        "</p:tnLst>" + aufbau + "</p:timing>"
    )
    try:
        _entfernen(slide, "timing")
        slide._element.append(_element(roh))
        return len(bloecke)
    except Exception as fehler:
        leise(fehler, "services/pptx_effekte")
        return 0


def uebergang_fuer(nummer: int, layout: str, wunsch: str = "") -> str:
    if wunsch:
        return wunsch
    if layout == "title":
        return "fade"
    if layout in ("quote", "stat", "closing"):
        return "fade"
    return FOLGE_UEBERGAENGE[nummer % len(FOLGE_UEBERGAENGE)]
