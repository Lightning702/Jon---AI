from __future__ import annotations

BAUWERKE = r'''
import bmesh
from mathutils import Euler, Matrix


def _jon_matrix(mitte, groesse=(1.0, 1.0, 1.0), drehung=(0.0, 0.0, 0.0)):
    return Matrix.Translation(Vector(mitte)) @ Euler(drehung).to_matrix().to_4x4() @ Matrix.Diagonal((groesse[0], groesse[1], groesse[2], 1.0))


def _jon_grad(winkel):
    return tuple(math.radians(w) for w in winkel)


def _jon_kanten(netz, winkel=40.0):
    if hasattr(netz, "set_sharp_from_angle"):
        try:
            netz.set_sharp_from_angle(angle=math.radians(winkel))
            return
        except Exception:
            pass
    if hasattr(netz, "use_auto_smooth"):
        netz.use_auto_smooth = True
        netz.auto_smooth_angle = math.radians(winkel)


def _jon_fase(objekt, breite, segmente=2):
    fase = objekt.modifiers.new("Fase", "BEVEL")
    fase.width = breite
    fase.segments = segmente
    fase.limit_method = "ANGLE"
    fase.angle_limit = math.radians(35.0)
    try:
        fase.harden_normals = True
    except Exception:
        pass
    return fase


class JonBau:
    def __init__(self, name):
        self.name = name
        self.punkte = []
        self.flaechen = []
        self.materialien = []

    def _index(self, material):
        if material not in self.materialien:
            self.materialien.append(material)
        return self.materialien.index(material)

    def _uebernehmen(self, klein, material, glatt):
        index = self._index(material)
        versatz = len(self.punkte)
        klein.verts.index_update()
        self.punkte.extend(tuple(punkt.co) for punkt in klein.verts)
        for flaeche in klein.faces:
            self.flaechen.append((tuple(versatz + punkt.index for punkt in flaeche.verts), index, glatt))
        klein.free()
        return self

    def quader(self, mitte, groesse, material, drehung=(0.0, 0.0, 0.0), glatt=False):
        klein = bmesh.new()
        bmesh.ops.create_cube(klein, size=1.0, matrix=_jon_matrix(mitte, groesse, _jon_grad(drehung)))
        return self._uebernehmen(klein, material, glatt)

    def zylinder(self, mitte, radius, hoehe, material, oben=None, segmente=32, drehung=(0.0, 0.0, 0.0)):
        klein = bmesh.new()
        bmesh.ops.create_cone(klein, cap_ends=True, cap_tris=False, segments=segmente, radius1=radius, radius2=radius if oben is None else oben, depth=hoehe, matrix=_jon_matrix(mitte, (1.0, 1.0, 1.0), _jon_grad(drehung)))
        return self._uebernehmen(klein, material, True)

    def kugel(self, mitte, radius, material, streckung=(1.0, 1.0, 1.0), drehung=(0.0, 0.0, 0.0), feinheit=3):
        klein = bmesh.new()
        bmesh.ops.create_icosphere(klein, subdivisions=feinheit, radius=radius, matrix=_jon_matrix(mitte, streckung, _jon_grad(drehung)))
        return self._uebernehmen(klein, material, True)

    def flaeche(self, punkte, material, glatt=False):
        index = self._index(material)
        versatz = len(self.punkte)
        self.punkte.extend(tuple(float(w) for w in punkt) for punkt in punkte)
        self.flaechen.append((tuple(range(versatz, versatz + len(punkte))), index, glatt))
        return self

    def _schliessen(self, unten, oben, material, glatt=False):
        klein = bmesh.new()
        ringe = ([klein.verts.new(p) for p in unten], [klein.verts.new(p) for p in oben])
        neu = [klein.faces.new(list(reversed(ringe[0]))), klein.faces.new(ringe[1])]
        anzahl = len(ringe[0])
        for i in range(anzahl):
            j = (i + 1) % anzahl
            neu.append(klein.faces.new((ringe[0][i], ringe[0][j], ringe[1][j], ringe[1][i])))
        bmesh.ops.recalc_face_normals(klein, faces=neu)
        return self._uebernehmen(klein, material, glatt)

    def platte(self, umriss, unten, dicke, material, winkel=0.0, versatz=(0.0, 0.0)):
        c, s = math.cos(math.radians(winkel)), math.sin(math.radians(winkel))
        gedreht = [(versatz[0] + x * c - y * s, versatz[1] + x * s + y * c) for x, y in umriss]
        return self._schliessen([(x, y, unten) for x, y in gedreht], [(x, y, unten + dicke) for x, y in gedreht], material)

    def prisma(self, profil, achse, von, bis, material):
        if achse == "x":
            return self._schliessen([(von, a, b) for a, b in profil], [(bis, a, b) for a, b in profil], material)
        return self._schliessen([(a, von, b) for a, b in profil], [(a, bis, b) for a, b in profil], material)

    def fertig(self, ort=(0.0, 0.0, 0.0), drehung=0.0, fase=0.0, eltern=None, leuchtet=False):
        netz = bpy.data.meshes.new(self.name)
        netz.from_pydata(self.punkte, [], [f[0] for f in self.flaechen])
        netz.polygons.foreach_set("material_index", [f[1] for f in self.flaechen])
        netz.polygons.foreach_set("use_smooth", [f[2] for f in self.flaechen])
        netz.update()
        self.punkte, self.flaechen = [], []
        for material in self.materialien:
            netz.materials.append(material)
        objekt = bpy.data.objects.new(self.name, netz)
        bpy.context.collection.objects.link(objekt)
        objekt.location = Vector(ort)
        objekt.rotation_euler = (0.0, 0.0, math.radians(drehung))
        if eltern is not None:
            objekt.parent = eltern
        _jon_kanten(netz)
        if fase > 0:
            _jon_fase(objekt, fase)
        if leuchtet:
            objekt["jon_selbstleuchtend"] = True
        return objekt


def _jon_leer(name, ort=(0.0, 0.0, 0.0), drehung=0.0, eltern=None):
    leer = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(leer)
    leer.location = Vector(ort)
    leer.rotation_euler = (0.0, 0.0, math.radians(drehung))
    if eltern is not None:
        leer.parent = eltern
    return leer


def _jon_ort(ort):
    werte = list(ort) + [0.0, 0.0, 0.0]
    return (float(werte[0]), float(werte[1]), float(werte[2]))


def _jon_zeit():
    return str(bpy.context.scene.get("jon_zeit", "tag"))


def _jon_dunkel():
    return _jon_zeit() in ("abend", "nacht")


def _jon_lager(name, erzeuger):
    vorhanden = bpy.data.materials.get(name)
    if vorhanden is not None and vorhanden.get("jon_lager"):
        return vorhanden
    material = erzeuger()
    material.name = name
    material["jon_lager"] = True
    return material


def _jon_knoten(name):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    baum = material.node_tree
    return material, baum, baum.nodes.get("Principled BSDF")


def _jon_koordinaten(baum, art="Object", skala=(1.0, 1.0, 1.0)):
    koordinaten = baum.nodes.new("ShaderNodeTexCoord")
    if tuple(skala) == (1.0, 1.0, 1.0):
        return koordinaten.outputs[art]
    abbildung = baum.nodes.new("ShaderNodeMapping")
    abbildung.inputs["Scale"].default_value = skala
    baum.links.new(koordinaten.outputs[art], abbildung.inputs["Vector"])
    return abbildung.outputs["Vector"]


def _jon_rampe(baum, eingang, farben):
    rampe = baum.nodes.new("ShaderNodeValToRGB")
    stufen = rampe.color_ramp.elements
    stufen[0].position, stufen[0].color = farben[0][0], _jon_farbe(farben[0][1])
    stufen[1].position, stufen[1].color = farben[-1][0], _jon_farbe(farben[-1][1])
    for lage, farbe in farben[1:-1]:
        stufe = stufen.new(lage)
        stufe.color = _jon_farbe(farbe)
    baum.links.new(eingang, rampe.inputs["Fac"])
    return rampe.outputs["Color"]


def _jon_relief(baum, bsdf, hoehe, staerke, abstand=0.1):
    relief = baum.nodes.new("ShaderNodeBump")
    relief.inputs["Strength"].default_value = staerke
    if "Distance" in relief.inputs:
        relief.inputs["Distance"].default_value = abstand
    baum.links.new(hoehe, relief.inputs["Height"])
    baum.links.new(relief.outputs["Normal"], bsdf.inputs["Normal"])
    return relief


def _jon_heller(farbe, faktor):
    return tuple(max(0.0, min(1.0, c * faktor)) for c in farbe[:3])


def _jon_rauschen(baum, vektor, skala, detail=6.0):
    rauschen = baum.nodes.new("ShaderNodeTexNoise")
    rauschen.inputs["Scale"].default_value = skala
    rauschen.inputs["Detail"].default_value = detail
    baum.links.new(vektor, rauschen.inputs["Vector"])
    return rauschen.outputs["Fac"]


def _jon_setzen(bsdf, name, wert, *ersatz):
    eingang = _jon_eingang(bsdf, name, *ersatz)
    if eingang is not None:
        try:
            eingang.default_value = wert
        except Exception:
            pass
    return eingang


def jon_putz(name="Putz", farbe=(0.86, 0.82, 0.74), rau=0.88, relief=0.12):
    material, baum, bsdf = _jon_knoten(name)
    vektor = _jon_koordinaten(baum)
    grob = _jon_rauschen(baum, vektor, 0.35, 3.0)
    baum.links.new(_jon_rampe(baum, grob, ((0.35, _jon_heller(farbe, 0.96)), (0.65, _jon_heller(farbe, 1.03)))), bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = rau
    _jon_relief(baum, bsdf, _jon_rauschen(baum, vektor, 38.0, 4.0), relief, 0.02)
    return material


def jon_holz(name="Holz", farbe=(0.42, 0.25, 0.12), rau=0.45, dielen=False, laenge=1.4, breite=0.19):
    material, baum, bsdf = _jon_knoten(name)
    vektor = _jon_koordinaten(baum)
    welle = baum.nodes.new("ShaderNodeTexWave")
    welle.wave_type = "BANDS"
    if hasattr(welle, "bands_direction"):
        welle.bands_direction = "Y"
    welle.inputs["Scale"].default_value = 4.0
    welle.inputs["Distortion"].default_value = 7.0
    welle.inputs["Detail"].default_value = 3.0
    dehnen = baum.nodes.new("ShaderNodeMapping")
    dehnen.inputs["Scale"].default_value = (0.25, 2.5, 1.0)
    baum.links.new(vektor, dehnen.inputs["Vector"])
    baum.links.new(dehnen.outputs["Vector"], welle.inputs["Vector"])
    maserung = _jon_rampe(baum, welle.outputs["Fac"], ((0.0, _jon_heller(farbe, 0.8)), (0.5, farbe), (1.0, _jon_heller(farbe, 1.12))))
    hoehe = welle.outputs["Fac"]
    if dielen:
        ziegel = baum.nodes.new("ShaderNodeTexBrick")
        ziegel.offset = 0.37
        ziegel.inputs["Scale"].default_value = 1.0
        ziegel.inputs["Brick Width"].default_value = laenge
        ziegel.inputs["Row Height"].default_value = breite
        ziegel.inputs["Mortar Size"].default_value = 0.003
        ziegel.inputs["Color1"].default_value = (1.0, 1.0, 1.0, 1.0)
        ziegel.inputs["Color2"].default_value = (0.72, 0.72, 0.72, 1.0)
        ziegel.inputs["Mortar"].default_value = (0.15, 0.15, 0.15, 1.0)
        baum.links.new(vektor, ziegel.inputs["Vector"])
        anteil, a, b, ergebnis = _jon_mischen(baum, "MULTIPLY")
        anteil.default_value = 1.0
        baum.links.new(maserung, a)
        baum.links.new(ziegel.outputs["Color"], b)
        maserung = ergebnis
        hoehe = ziegel.outputs["Fac"]
    baum.links.new(maserung, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = rau
    _jon_relief(baum, bsdf, hoehe, 0.25 if dielen else 0.08, 0.01)
    return material


def jon_stoff(name="Stoff", farbe=(0.3, 0.38, 0.5), rau=0.95):
    material, baum, bsdf = _jon_knoten(name)
    vektor = _jon_koordinaten(baum)
    baum.links.new(_jon_rampe(baum, _jon_rauschen(baum, vektor, 2.0), ((0.3, _jon_heller(farbe, 0.9)), (0.7, _jon_heller(farbe, 1.08)))), bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = rau
    _jon_setzen(bsdf, "Sheen Weight", 0.6, "Sheen")
    _jon_setzen(bsdf, "Specular IOR Level", 0.3, "Specular")
    _jon_relief(baum, bsdf, _jon_rauschen(baum, vektor, 260.0, 2.0), 0.25, 0.005)
    return material


def jon_glas(name="Glas", farbe=(0.85, 0.93, 1.0), deckkraft=0.12, rau=0.02, glanz=1.0):
    material, baum, bsdf = _jon_knoten(name)
    bsdf.inputs["Base Color"].default_value = _jon_farbe(farbe)
    bsdf.inputs["Roughness"].default_value = rau
    _jon_setzen(bsdf, "Specular IOR Level", glanz, "Specular")
    bsdf.inputs["Alpha"].default_value = deckkraft
    _jon_durchsichtig(material)
    return material


def jon_fensterglas(name="Fensterglas", leuchten=0.0):
    material, baum, bsdf = _jon_knoten(name)
    bsdf.inputs["Base Color"].default_value = (0.02, 0.035, 0.05, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.04
    _jon_setzen(bsdf, "Specular IOR Level", 1.0, "Specular")
    if leuchten > 0:
        _jon_setzen(bsdf, "Emission Color", (1.0, 0.68, 0.36, 1.0), "Emission")
        _jon_setzen(bsdf, "Emission Strength", leuchten)
    return material


def jon_metall(name="Metall", farbe=(0.8, 0.8, 0.82), rau=0.28):
    return jon_material(name, farbe, metall=1.0, rau=rau)


def jon_ziegel(name="Ziegel", farbe=(0.5, 0.2, 0.13), fuge=(0.62, 0.6, 0.56), breite=0.25, hoehe=0.075):
    material, baum, bsdf = _jon_knoten(name)
    ziegel = baum.nodes.new("ShaderNodeTexBrick")
    ziegel.inputs["Scale"].default_value = 1.0
    ziegel.inputs["Brick Width"].default_value = breite
    ziegel.inputs["Row Height"].default_value = hoehe
    ziegel.inputs["Mortar Size"].default_value = 0.008
    ziegel.inputs["Color1"].default_value = _jon_farbe(farbe)
    ziegel.inputs["Color2"].default_value = _jon_farbe(_jon_heller(farbe, 0.72))
    ziegel.inputs["Mortar"].default_value = _jon_farbe(fuge)
    teile = baum.nodes.new("ShaderNodeSeparateXYZ")
    vektor = baum.nodes.new("ShaderNodeCombineXYZ")
    summe = baum.nodes.new("ShaderNodeMath")
    summe.operation = "ADD"
    baum.links.new(_jon_koordinaten(baum), teile.inputs["Vector"])
    baum.links.new(teile.outputs["X"], summe.inputs[0])
    baum.links.new(teile.outputs["Y"], summe.inputs[1])
    baum.links.new(summe.outputs["Value"], vektor.inputs["X"])
    baum.links.new(teile.outputs["Z"], vektor.inputs["Y"])
    baum.links.new(vektor.outputs["Vector"], ziegel.inputs["Vector"])
    baum.links.new(ziegel.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.9
    _jon_relief(baum, bsdf, ziegel.outputs["Fac"], 0.35, 0.01)
    return material


def jon_dachziegel(name="Dachziegel", farbe=(0.42, 0.13, 0.08), neigung=35.0):
    material, baum, bsdf = _jon_knoten(name)
    ziegel = baum.nodes.new("ShaderNodeTexBrick")
    ziegel.inputs["Scale"].default_value = 1.0
    ziegel.inputs["Brick Width"].default_value = 0.3
    ziegel.inputs["Row Height"].default_value = 0.34
    ziegel.inputs["Mortar Size"].default_value = 0.012
    ziegel.inputs["Mortar Smooth"].default_value = 0.6
    ziegel.inputs["Color1"].default_value = _jon_farbe(farbe)
    ziegel.inputs["Color2"].default_value = _jon_farbe(_jon_heller(farbe, 0.75))
    ziegel.inputs["Mortar"].default_value = _jon_farbe(_jon_heller(farbe, 0.35))
    teile = baum.nodes.new("ShaderNodeSeparateXYZ")
    vektor = baum.nodes.new("ShaderNodeCombineXYZ")
    hang = baum.nodes.new("ShaderNodeMath")
    hang.operation = "MULTIPLY"
    hang.inputs[1].default_value = 1.0 / max(0.2, math.sin(math.radians(neigung)))
    baum.links.new(_jon_koordinaten(baum), teile.inputs["Vector"])
    baum.links.new(teile.outputs["Z"], hang.inputs[0])
    baum.links.new(teile.outputs["X"], vektor.inputs["X"])
    baum.links.new(hang.outputs["Value"], vektor.inputs["Y"])
    baum.links.new(vektor.outputs["Vector"], ziegel.inputs["Vector"])
    baum.links.new(ziegel.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.62
    _jon_relief(baum, bsdf, ziegel.outputs["Fac"], 0.6, 0.03)
    return material


JON_TAGESZEITEN = {
    "tag": {"zenit": (0.13, 0.3, 0.78), "horizont": (0.6, 0.74, 0.93), "boden": (0.26, 0.25, 0.23), "licht": (1.0, 0.95, 0.88), "staerke": 4.2, "hoehe": 46.0, "richtung": -122.0, "welt": 1.0, "winkel": 2.5, "halo": 0.6},
    "morgen": {"zenit": (0.28, 0.4, 0.72), "horizont": (1.0, 0.74, 0.52), "boden": (0.22, 0.2, 0.19), "licht": (1.0, 0.78, 0.55), "staerke": 3.4, "hoehe": 15.0, "richtung": -135.0, "welt": 0.9, "winkel": 3.0, "halo": 1.5},
    "abend": {"zenit": (0.06, 0.08, 0.24), "horizont": (1.0, 0.4, 0.13), "boden": (0.08, 0.06, 0.06), "licht": (1.0, 0.5, 0.22), "staerke": 3.3, "hoehe": 7.0, "richtung": -140.0, "welt": 0.85, "winkel": 3.0, "halo": 3.0},
    "nacht": {"zenit": (0.0025, 0.004, 0.016), "horizont": (0.014, 0.022, 0.055), "boden": (0.004, 0.004, 0.006), "licht": (0.55, 0.66, 1.0), "staerke": 0.35, "hoehe": 38.0, "richtung": -60.0, "welt": 1.0, "winkel": 1.0, "halo": 0.0},
    "bewoelkt": {"zenit": (0.4, 0.44, 0.5), "horizont": (0.64, 0.67, 0.7), "boden": (0.22, 0.22, 0.22), "licht": (0.92, 0.94, 1.0), "staerke": 1.4, "hoehe": 55.0, "richtung": -120.0, "welt": 1.0, "winkel": 25.0, "halo": 0.0},
}

JON_ZEITWOERTER = {"mittag": "tag", "tag": "tag", "sonnig": "tag", "sonnenaufgang": "morgen", "morgen": "morgen", "morgens": "morgen", "daemmerung": "abend", "sonnenuntergang": "abend", "abend": "abend", "abends": "abend", "nacht": "nacht", "nachts": "nacht", "mond": "nacht", "bewoelkt": "bewoelkt", "wolkig": "bewoelkt", "grau": "bewoelkt", "regen": "bewoelkt"}


def jon_himmel(zeit="tag", sonnenhoehe=None, sonnenrichtung=None, staerke=1.0):
    schluessel = JON_ZEITWOERTER.get(str(zeit).lower().replace("ö", "oe").replace("ä", "ae").strip(), "tag")
    werte = JON_TAGESZEITEN[schluessel]
    szene = bpy.context.scene
    szene["jon_zeit"] = schluessel
    hoehe = math.radians(werte["hoehe"] if sonnenhoehe is None else float(sonnenhoehe))
    richtung = math.radians(werte["richtung"] if sonnenrichtung is None else float(sonnenrichtung))
    zur_sonne = Vector((math.cos(hoehe) * math.cos(richtung), math.cos(hoehe) * math.sin(richtung), math.sin(hoehe)))
    welt = szene.world or bpy.data.worlds.new("JonWelt")
    szene.world = welt
    welt.use_nodes = True
    baum = welt.node_tree
    baum.nodes.clear()
    ausgabe = baum.nodes.new("ShaderNodeOutputWorld")
    koordinaten = baum.nodes.new("ShaderNodeTexCoord")
    teile = baum.nodes.new("ShaderNodeSeparateXYZ")
    baum.links.new(koordinaten.outputs["Generated"], teile.inputs["Vector"])
    hoch = baum.nodes.new("ShaderNodeMapRange")
    hoch.inputs["From Min"].default_value = -1.0
    hoch.inputs["From Max"].default_value = 1.0
    baum.links.new(teile.outputs["Z"], hoch.inputs["Value"])
    mitte = tuple(werte["horizont"][i] * 0.55 + werte["zenit"][i] * 0.45 for i in range(3))
    farbe = _jon_rampe(baum, hoch.outputs["Result"], ((0.0, _jon_heller(werte["boden"], 0.6)), (0.42, _jon_heller(werte["horizont"], 0.7)), (0.5, werte["horizont"]), (0.56, mitte), (0.78, werte["zenit"]), (1.0, _jon_heller(werte["zenit"], 0.85))))
    if werte["halo"] > 0:
        punkt = baum.nodes.new("ShaderNodeVectorMath")
        punkt.operation = "DOT_PRODUCT"
        punkt.inputs[1].default_value = zur_sonne
        baum.links.new(koordinaten.outputs["Generated"], punkt.inputs[0])
        schein = baum.nodes.new("ShaderNodeMapRange")
        schein.interpolation_type = "SMOOTHSTEP"
        schein.inputs["From Min"].default_value = 0.88
        schein.inputs["From Max"].default_value = 1.0
        schein.inputs["To Max"].default_value = werte["halo"]
        scheibe = baum.nodes.new("ShaderNodeMapRange")
        scheibe.inputs["From Min"].default_value = 0.99955
        scheibe.inputs["From Max"].default_value = 0.9998
        scheibe.inputs["To Max"].default_value = 60.0
        summe = baum.nodes.new("ShaderNodeMath")
        summe.operation = "ADD"
        baum.links.new(punkt.outputs["Value"], schein.inputs["Value"])
        baum.links.new(punkt.outputs["Value"], scheibe.inputs["Value"])
        baum.links.new(schein.outputs["Result"], summe.inputs[0])
        baum.links.new(scheibe.outputs["Result"], summe.inputs[1])
        anteil, a, b, ergebnis = _jon_mischen(baum, "ADD")
        baum.links.new(summe.outputs["Value"], anteil)
        baum.links.new(farbe, a)
        b.default_value = _jon_farbe(werte["licht"])
        farbe = ergebnis
    grund = baum.nodes.new("ShaderNodeBackground")
    grund.inputs["Strength"].default_value = werte["welt"] * float(staerke)
    baum.links.new(farbe, grund.inputs["Color"])
    summe = grund.outputs["Background"]
    if schluessel == "nacht":
        oben = baum.nodes.new("ShaderNodeMath")
        oben.operation = "GREATER_THAN"
        oben.inputs[1].default_value = 0.02
        baum.links.new(teile.outputs["Z"], oben.inputs[0])
        for skala, schwelle, glanz in ((240.0, 0.08, 5.0), (80.0, 0.03, 12.0)):
            zellen = baum.nodes.new("ShaderNodeTexVoronoi")
            zellen.inputs["Scale"].default_value = skala
            baum.links.new(koordinaten.outputs["Generated"], zellen.inputs["Vector"])
            punkte = _jon_rampe(baum, zellen.outputs["Distance"], ((0.0, (1.0, 1.0, 1.0)), (schwelle, (0.0, 0.0, 0.0))))
            anteil, a, b, ergebnis = _jon_mischen(baum, "MULTIPLY")
            anteil.default_value = 1.0
            baum.links.new(punkte, a)
            baum.links.new(oben.outputs["Value"], b)
            sterne = baum.nodes.new("ShaderNodeBackground")
            sterne.inputs["Strength"].default_value = glanz
            baum.links.new(ergebnis, sterne.inputs["Color"])
            plus = baum.nodes.new("ShaderNodeAddShader")
            baum.links.new(summe, plus.inputs[0])
            baum.links.new(sterne.outputs["Background"], plus.inputs[1])
            summe = plus.outputs["Shader"]
    baum.links.new(summe, ausgabe.inputs["Surface"])
    for altes in [o for o in szene.objects if o.get("jon_himmelslicht")]:
        bpy.data.objects.remove(altes, do_unlink=True)
    daten = bpy.data.lights.new("Sonnenlicht" if schluessel != "nacht" else "Mondlicht", type="SUN")
    daten.energy = werte["staerke"] * float(staerke)
    daten.color = werte["licht"]
    daten.angle = math.radians(werte["winkel"])
    licht = bpy.data.objects.new(daten.name, daten)
    licht["jon_himmelslicht"] = True
    szene.collection.objects.link(licht)
    licht.rotation_euler = (-zur_sonne).to_track_quat("-Z", "Y").to_euler()
    return licht


JON_BOEDEN = {
    "gras": ((0.1, 0.24, 0.045), 0.95, 0.35, 0.5),
    "wiese": ((0.12, 0.26, 0.05), 0.95, 0.4, 0.5),
    "asphalt": ((0.05, 0.05, 0.055), 0.82, 0.3, 0.25),
    "strasse": ((0.05, 0.05, 0.055), 0.82, 0.3, 0.25),
    "beton": ((0.42, 0.42, 0.4), 0.85, 0.06, 0.15),
    "sand": ((0.72, 0.58, 0.38), 0.92, 0.18, 0.4),
    "wueste": ((0.75, 0.55, 0.32), 0.92, 0.2, 0.5),
    "erde": ((0.18, 0.11, 0.06), 0.95, 0.3, 0.45),
    "schnee": ((0.9, 0.92, 0.96), 0.55, 0.06, 0.25),
    "wasser": ((0.015, 0.06, 0.09), 0.04, 0.3, 0.15),
    "stein": ((0.36, 0.35, 0.33), 0.85, 0.25, 0.4),
}


def jon_boden(art="gras", groesse=8000.0, farbe=None, ort=(0.0, 0.0, 0.0), name="Boden"):
    art = str(art).lower().replace("ü", "ue").replace("ß", "ss")
    if art in ("holz", "parkett", "dielen", "laminat"):
        material = jon_holz(f"{name}Holz", farbe or (0.45, 0.28, 0.14), 0.4, dielen=True)
    elif art in ("fliesen", "kacheln"):
        material = jon_fliesen(f"{name}Fliesen", farbe or (0.82, 0.8, 0.76))
    elif art in ("pflaster", "kopfsteinpflaster", "platten"):
        material = jon_ziegel(f"{name}Pflaster", farbe or (0.42, 0.4, 0.37), (0.2, 0.19, 0.18), 0.4, 0.2)
    else:
        grund, rau, wechsel, relief = JON_BOEDEN.get(art, JON_BOEDEN["gras"])
        grund = tuple(farbe) if farbe else grund
        material, baum, bsdf = _jon_knoten(f"{name}{art.title()}")
        vektor = _jon_koordinaten(baum)
        grob = _jon_rauschen(baum, vektor, 0.08, 4.0)
        fein = _jon_rauschen(baum, vektor, 3.0, 8.0)
        anteil, a, b, ergebnis = _jon_mischen(baum, "MULTIPLY")
        anteil.default_value = 0.6
        baum.links.new(_jon_rampe(baum, grob, ((0.3, _jon_heller(grund, 1.0 - wechsel)), (0.7, _jon_heller(grund, 1.0 + wechsel)))), a)
        baum.links.new(_jon_rampe(baum, fein, ((0.3, (0.75, 0.75, 0.75)), (0.7, (1.0, 1.0, 1.0)))), b)
        baum.links.new(ergebnis, bsdf.inputs["Base Color"])
        bsdf.inputs["Roughness"].default_value = rau
        _jon_relief(baum, bsdf, _jon_rauschen(baum, vektor, 2.5 if art == "wasser" else 40.0, 6.0), relief, 0.05)
    bau = JonBau(name)
    if art not in ("holz", "parkett", "dielen", "laminat", "fliesen", "kacheln"):
        groesse = max(float(groesse), 8000.0)
    bau.quader((0.0, 0.0, -0.01), (groesse, groesse, 0.02), material)
    boden = bau.fertig(_jon_ort(ort))
    boden["jon_hintergrund"] = True
    return boden


def jon_fliesen(name="Fliesen", farbe=(0.82, 0.8, 0.76), groesse=0.6, fuge=(0.45, 0.44, 0.42)):
    material, baum, bsdf = _jon_knoten(name)
    ziegel = baum.nodes.new("ShaderNodeTexBrick")
    ziegel.offset = 0.0
    ziegel.inputs["Scale"].default_value = 1.0
    ziegel.inputs["Brick Width"].default_value = groesse
    ziegel.inputs["Row Height"].default_value = groesse
    ziegel.inputs["Mortar Size"].default_value = 0.004
    ziegel.inputs["Color1"].default_value = _jon_farbe(farbe)
    ziegel.inputs["Color2"].default_value = _jon_farbe(_jon_heller(farbe, 0.94))
    ziegel.inputs["Mortar"].default_value = _jon_farbe(fuge)
    baum.links.new(_jon_koordinaten(baum), ziegel.inputs["Vector"])
    baum.links.new(ziegel.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.18
    _jon_relief(baum, bsdf, ziegel.outputs["Fac"], 0.3, 0.004)
    return material


def jon_haus(breite=9.0, tiefe=7.0, stockwerke=1, stockhoehe=2.8, dach="sattel", wandfarbe=(0.88, 0.82, 0.7), dachfarbe=(0.42, 0.13, 0.08), rahmenfarbe=(0.95, 0.95, 0.93), tuerfarbe=(0.32, 0.18, 0.09), ort=(0.0, 0.0, 0.0), drehung=0.0, kamin=True, fensterlaeden=False, ladenfarbe=(0.18, 0.3, 0.2), name="Haus"):
    b, t = float(breite), float(tiefe)
    sockel = 0.3
    geschosse = max(1, int(stockwerke))
    h = sockel + geschosse * stockhoehe
    sattel = not str(dach).lower().startswith(("flach", "pult", "modern"))
    dachhoehe = t * 0.42 if sattel else 0.0
    dunkel = _jon_dunkel()
    zufall = random.Random(int(abs(ort[0] * 31.7 + ort[1] * 17.3)) + 5)
    haus = _jon_leer(name, _jon_ort(ort), drehung)
    wand = jon_putz(f"{name}Wand", wandfarbe)
    rahmen = jon_material(f"{name}Rahmen", rahmenfarbe, rau=0.35)
    stein = jon_material(f"{name}Stein", (0.62, 0.6, 0.57), rau=0.7)
    sockelstein = jon_material(f"{name}Sockel", (0.3, 0.29, 0.28), rau=0.85)
    glas = jon_fensterglas(f"{name}Glas")
    glas_hell = jon_fensterglas(f"{name}GlasHell", 4.0) if dunkel else glas
    holz = jon_holz(f"{name}Tuer", tuerfarbe, 0.5)
    metall = jon_metall(f"{name}Metall", (0.75, 0.72, 0.65), 0.3)
    laden = jon_material(f"{name}Laden", ladenfarbe, rau=0.6)
    koerper = JonBau(f"{name}Koerper")
    profil = [(-t / 2, sockel), (t / 2, sockel), (t / 2, h)] + ([(0.0, h + dachhoehe)] if sattel else []) + [(-t / 2, h)]
    koerper.prisma(profil, "x", -b / 2, b / 2, wand)
    koerper_objekt = koerper.fertig(eltern=haus)
    unterbau = JonBau(f"{name}Sockel")
    unterbau.quader((0.0, 0.0, sockel / 2), (b + 0.08, t + 0.08, sockel), sockelstein)
    unterbau.fertig(eltern=haus, fase=0.015)
    seiten = {
        "vorne": (Vector((0.0, -t / 2, 0.0)), Vector((1.0, 0.0, 0.0)), Vector((0.0, -1.0, 0.0)), 0.0),
        "hinten": (Vector((0.0, t / 2, 0.0)), Vector((-1.0, 0.0, 0.0)), Vector((0.0, 1.0, 0.0)), 0.0),
        "links": (Vector((-b / 2, 0.0, 0.0)), Vector((0.0, -1.0, 0.0)), Vector((-1.0, 0.0, 0.0)), 90.0),
        "rechts": (Vector((b / 2, 0.0, 0.0)), Vector((0.0, 1.0, 0.0)), Vector((1.0, 0.0, 0.0)), 90.0),
    }

    def stelle(seite, u, z, tiefe_aussen):
        basis, achse, normale, _ = seiten[seite]
        return basis + achse * u + Vector((0.0, 0.0, z)) + normale * tiefe_aussen

    oeffnungen = []
    vorne = max(2, int(b / 2.3))
    tuerplatz = vorne // 2
    for geschoss in range(geschosse):
        unten = sockel + geschoss * stockhoehe + 0.85
        for seite, laenge, anzahl in (("vorne", b, vorne), ("hinten", b, vorne), ("links", t, max(1, int(t / 2.8))), ("rechts", t, max(1, int(t / 2.8)))):
            fensterbreite = min(1.25, laenge / anzahl * 0.5)
            for nummer in range(anzahl):
                u = -laenge / 2 + laenge * (nummer + 0.5) / anzahl
                if geschoss == 0 and seite == "vorne" and nummer == tuerplatz:
                    oeffnungen.append(("tuer", seite, u, sockel, 1.1, 2.2))
                else:
                    oeffnungen.append(("fenster", seite, u, unten, fensterbreite, min(1.35, stockhoehe * 0.48)))
    if sattel and dachhoehe > 1.7:
        for seite in ("links", "rechts"):
            oeffnungen.append(("fenster", seite, 0.0, h + dachhoehe * 0.18, 0.8, min(1.0, dachhoehe * 0.4)))
    schnitt = JonBau(f"{name}Aussparungen")
    teile = JonBau(f"{name}Fenster")
    scheiben = JonBau(f"{name}Scheiben")
    tueren = JonBau(f"{name}Haustuer")
    for art, seite, u, unten, w, hh in oeffnungen:
        drehwinkel = (0.0, 0.0, seiten[seite][3])
        mitte_z = unten + hh / 2
        schnitt.quader(stelle(seite, u, mitte_z, 0.0), (w, 0.6, hh), wand, drehwinkel)
        r = 0.07
        teile.quader(stelle(seite, u, unten + hh - r / 2, -0.12), (w, 0.08, r), rahmen, drehwinkel)
        teile.quader(stelle(seite, u - w / 2 + r / 2, mitte_z, -0.12), (r, 0.08, hh), rahmen, drehwinkel)
        teile.quader(stelle(seite, u + w / 2 - r / 2, mitte_z, -0.12), (r, 0.08, hh), rahmen, drehwinkel)
        if art == "tuer":
            tueren.quader(stelle(seite, u, unten + (hh - r) / 2, -0.1), (w - 2 * r, 0.06, hh - r), holz, drehwinkel)
            for feld in (0.28, 0.68):
                tueren.quader(stelle(seite, u, unten + hh * feld, -0.065), (w * 0.62, 0.02, hh * 0.3), holz, drehwinkel)
            tueren.zylinder(stelle(seite, u + w * 0.32, unten + 1.05, -0.04), 0.03, 0.08, metall, drehung=(90.0, 0.0, seiten[seite][3]), segmente=16)
            tueren.quader(stelle(seite, u, sockel / 2, 0.24), (w + 0.7, 0.48, sockel), stein, drehwinkel)
            tueren.quader(stelle(seite, u, unten + hh + 0.32, 0.45), (w + 0.8, 0.9, 0.08), rahmen, drehwinkel)
            if dunkel:
                tueren.quader(stelle(seite, u + w / 2 + 0.35, unten + 1.9, 0.06), (0.14, 0.12, 0.22), jon_leuchtmaterial(f"{name}Laterne", (1.0, 0.75, 0.45), 12.0), drehwinkel)
                daten = bpy.data.lights.new(f"{name}Eingangslicht", type="POINT")
                daten.energy = 60.0
                daten.color = (1.0, 0.75, 0.45)
                lampe = bpy.data.objects.new(daten.name, daten)
                bpy.context.collection.objects.link(lampe)
                lampe.parent = haus
                lampe.location = stelle(seite, u + w / 2 + 0.35, unten + 1.85, 0.3)
            continue
        teile.quader(stelle(seite, u, unten + r / 2, -0.12), (w, 0.08, r), rahmen, drehwinkel)
        teile.quader(stelle(seite, u, mitte_z, -0.12), (0.045, 0.05, hh - 2 * r), rahmen, drehwinkel)
        teile.quader(stelle(seite, u, unten + hh * 0.64, -0.12), (w - 2 * r, 0.05, 0.045), rahmen, drehwinkel)
        teile.quader(stelle(seite, u, unten - 0.03, 0.05), (w + 0.14, 0.28, 0.05), stein, drehwinkel)
        scheiben.quader(stelle(seite, u, mitte_z, -0.15), (w - r, 0.02, hh - r), glas_hell if dunkel and zufall.random() < 0.7 else glas, drehwinkel)
        if fensterlaeden:
            for seitlich in (-1.0, 1.0):
                teile.quader(stelle(seite, u + seitlich * (w / 2 + 0.3), mitte_z, 0.03), (0.52, 0.04, hh + 0.05), laden, drehwinkel)
    schnitt_objekt = schnitt.fertig(eltern=haus)
    schnitt_objekt.hide_render = True
    schnitt_objekt.display_type = "WIRE"
    schnitt_objekt["jon_hintergrund"] = True
    loch = koerper_objekt.modifiers.new("Oeffnungen", "BOOLEAN")
    loch.operation = "DIFFERENCE"
    loch.object = schnitt_objekt
    teile.fertig(eltern=haus, fase=0.008)
    scheiben.fertig(eltern=haus, leuchtet=dunkel)
    tueren.fertig(eltern=haus, fase=0.01)
    dachbau = JonBau(f"{name}Dach")
    if sattel:
        ueber, giebel, dicke = 0.5, 0.4, 0.2
        winkel = math.atan2(dachhoehe, t / 2)
        ziegel = jon_dachziegel(f"{name}Dachziegel", dachfarbe, math.degrees(winkel))
        dunkler = jon_material(f"{name}First", _jon_heller(dachfarbe, 0.7), rau=0.6)
        rinne = jon_metall(f"{name}Rinne", (0.55, 0.56, 0.58), 0.35)
        brett = jon_material(f"{name}Brett", rahmenfarbe, rau=0.5)
        for vorzeichen in (-1.0, 1.0):
            traufe = Vector((0.0, vorzeichen * (t / 2 + ueber), h - ueber * math.tan(winkel)))
            first = Vector((0.0, 0.0, h + dachhoehe))
            normale = Vector((0.0, vorzeichen * math.sin(winkel), math.cos(winkel)))
            laenge = (first - traufe).length + 0.12
            mitte = (traufe + first) / 2 + normale * dicke / 2 + (first - traufe).normalized() * 0.06
            dachbau.quader(mitte, (b + 2 * giebel, laenge, dicke), ziegel, (-vorzeichen * math.degrees(winkel), 0.0, 0.0))
            dachbau.quader(traufe + normale * 0.02 + Vector((0.0, vorzeichen * 0.02, -0.08)), (b + 2 * giebel, 0.05, 0.24), brett)
            dachbau.zylinder(traufe + Vector((0.0, vorzeichen * 0.1, -0.12)), 0.075, b + 2 * giebel, rinne, drehung=(0.0, 90.0, 0.0), segmente=16)
        dachbau.zylinder((0.0, 0.0, h + dachhoehe + dicke * 0.95), 0.14, b + 2 * giebel + 0.02, dunkler, drehung=(0.0, 90.0, 0.0), segmente=20)
        if kamin:
            backstein = jon_ziegel(f"{name}Kamin", (0.42, 0.18, 0.12))
            oben = h + dachhoehe + 0.75
            dachbau.quader((b * 0.24, t * 0.2, (h + oben) / 2), (0.62, 0.62, oben - h), backstein)
            dachbau.quader((b * 0.24, t * 0.2, oben + 0.05), (0.78, 0.78, 0.1), stein)
    else:
        kies = jon_boden_material(f"{name}Flachdach", (0.32, 0.31, 0.3))
        dachbau.quader((0.0, 0.0, h + 0.12), (b + 0.3, t + 0.3, 0.24), kies)
        for x, y, sb, st in ((0.0, -(t + 0.3) / 2, b + 0.3, 0.2), (0.0, (t + 0.3) / 2, b + 0.3, 0.2), (-(b + 0.3) / 2, 0.0, 0.2, t + 0.3), ((b + 0.3) / 2, 0.0, 0.2, t + 0.3)):
            dachbau.quader((x, y, h + 0.4), (sb, st, 0.56), rahmen)
    dachbau.fertig(eltern=haus, fase=0.015)
    return haus


def jon_boden_material(name, farbe, rau=0.9):
    material, baum, bsdf = _jon_knoten(name)
    vektor = _jon_koordinaten(baum)
    baum.links.new(_jon_rampe(baum, _jon_rauschen(baum, vektor, 30.0, 4.0), ((0.3, _jon_heller(farbe, 0.75)), (0.7, _jon_heller(farbe, 1.2)))), bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = rau
    _jon_relief(baum, bsdf, _jon_rauschen(baum, vektor, 60.0, 4.0), 0.4, 0.02)
    return material


def _jon_laubmaterial(name, farbe):
    material, baum, bsdf = _jon_knoten(name)
    vektor = _jon_koordinaten(baum)
    baum.links.new(_jon_rampe(baum, _jon_rauschen(baum, vektor, 1.6, 4.0), ((0.25, _jon_heller(farbe, 0.6)), (0.5, farbe), (0.75, _jon_heller(farbe, 1.45)))), bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.75
    _jon_setzen(bsdf, "Subsurface Weight", 0.15, "Subsurface")
    _jon_relief(baum, bsdf, _jon_rauschen(baum, vektor, 18.0, 3.0), 0.8, 0.08)
    return material


def _jon_wuchs(objekt, staerke, groesse):
    try:
        muster = bpy.data.textures.new(f"{objekt.name}Wuchs", "CLOUDS")
        muster.noise_scale = groesse
        verformen = objekt.modifiers.new("Wuchs", "DISPLACE")
        verformen.texture = muster
        verformen.strength = staerke
        verformen.mid_level = 0.5
    except Exception:
        pass


def _jon_baeume(punkte, name="Baeume", art="laub", farbe=None, eltern=None, samen=1):
    zufall = random.Random(samen)
    nadel = str(art).lower().startswith(("nadel", "tanne", "fichte", "kiefer"))
    farbe = farbe or ((0.05, 0.17, 0.07) if nadel else (0.13, 0.3, 0.06))
    rinde = jon_material(f"{name}Rinde", (0.22, 0.15, 0.1), rau=0.9)
    laub = _jon_laubmaterial(f"{name}Laub", farbe)
    staemme = JonBau(f"{name}Staemme")
    kronen = JonBau(f"{name}Kronen")
    groesste = 1.0
    for ort, hoehe in punkte:
        x, y, z = _jon_ort(ort)
        hoehe = float(hoehe) * (0.85 + zufall.random() * 0.3)
        groesste = max(groesste, hoehe)
        if nadel:
            staemme.zylinder((x, y, z + hoehe * 0.15), hoehe * 0.035, hoehe * 0.3, rinde, oben=hoehe * 0.025, segmente=12)
            for stufe in range(4):
                anteil = stufe / 4.0
                radius = hoehe * (0.27 - anteil * 0.17)
                staemme.zylinder((x, y, z + hoehe * (0.32 + anteil * 0.5)), radius, hoehe * 0.36, laub, oben=radius * 0.15, segmente=18)
        else:
            staemme.zylinder((x, y, z + hoehe * 0.3), hoehe * 0.045, hoehe * 0.6, rinde, oben=hoehe * 0.03, segmente=12)
            for _ in range(6):
                winkel = zufall.random() * math.tau
                weite = hoehe * 0.12 * zufall.random()
                radius = hoehe * (0.17 + zufall.random() * 0.08)
                kronen.kugel((x + math.cos(winkel) * weite, y + math.sin(winkel) * weite, z + hoehe * (0.62 + zufall.random() * 0.15)), radius, laub, (1.0, 1.0, 0.85))
    staemme.fertig(eltern=eltern)
    if not nadel:
        krone = kronen.fertig(eltern=eltern)
        _jon_wuchs(krone, groesste * 0.09, groesste * 0.07)
        return krone
    return None


def jon_baum(ort=(0.0, 0.0, 0.0), hoehe=6.0, art="laub", farbe=None, samen=0, name="Baum"):
    leer = _jon_leer(name, (0.0, 0.0, 0.0))
    _jon_baeume([(ort, hoehe)], name, art, farbe, leer, samen or int(abs(ort[0] * 13 + ort[1] * 7)) + 1)
    return leer


def jon_wald(anzahl=30, flaeche=(40.0, 40.0), mitte=(0.0, 0.0, 0.0), hoehe=7.0, art="gemischt", frei=None, samen=3):
    zufall = random.Random(samen)
    laub, nadel = [], []
    frei = frei or []
    versuche = 0
    while len(laub) + len(nadel) < anzahl and versuche < anzahl * 20:
        versuche += 1
        x = mitte[0] + (zufall.random() - 0.5) * flaeche[0]
        y = mitte[1] + (zufall.random() - 0.5) * flaeche[1]
        if any(math.hypot(x - fx, y - fy) < fr for fx, fy, fr in frei):
            continue
        ziel = nadel if (art == "nadel" or (art == "gemischt" and zufall.random() < 0.4)) else laub
        ziel.append(((x, y, mitte[2]), hoehe))
    leer = _jon_leer("Wald")
    if laub:
        _jon_baeume(laub, "WaldLaub", "laub", None, leer, samen)
    if nadel:
        _jon_baeume(nadel, "WaldNadel", "nadel", None, leer, samen + 1)
    return leer


def jon_fassade(name="Fassade", wandfarbe=(0.62, 0.6, 0.58), glasfarbe=(0.03, 0.05, 0.07), stockwerk=3.4, achse=2.6, fensteranteil=0.55, leuchten=None):
    leuchten = _jon_dunkel() if leuchten is None else leuchten
    material, baum, bsdf = _jon_knoten(name)
    koordinaten = baum.nodes.new("ShaderNodeTexCoord")
    teile = baum.nodes.new("ShaderNodeSeparateXYZ")
    baum.links.new(koordinaten.outputs["Object"], teile.inputs["Vector"])

    def rechnen(art, a, b=None):
        knoten = baum.nodes.new("ShaderNodeMath")
        knoten.operation = art
        for stelle, wert in ((0, a), (1, b)):
            if wert is None:
                continue
            if isinstance(wert, (int, float)):
                knoten.inputs[stelle].default_value = float(wert)
            else:
                baum.links.new(wert, knoten.inputs[stelle])
        return knoten.outputs["Value"]

    u = rechnen("ADD", teile.outputs["X"], teile.outputs["Y"])
    spalte = rechnen("DIVIDE", u, achse)
    zeile = rechnen("DIVIDE", teile.outputs["Z"], stockwerk)
    in_spalte = rechnen("LESS_THAN", rechnen("ABSOLUTE", rechnen("SUBTRACT", rechnen("FRACT", spalte), 0.5)), fensteranteil / 2)
    in_zeile = rechnen("LESS_THAN", rechnen("ABSOLUTE", rechnen("SUBTRACT", rechnen("FRACT", zeile), 0.55)), 0.28)
    geometrie = baum.nodes.new("ShaderNodeNewGeometry")
    normale = baum.nodes.new("ShaderNodeSeparateXYZ")
    baum.links.new(geometrie.outputs["Normal"], normale.inputs["Vector"])
    seitlich = rechnen("LESS_THAN", rechnen("ABSOLUTE", normale.outputs["Z"]), 0.5)
    fenster = rechnen("MULTIPLY", rechnen("MULTIPLY", in_spalte, in_zeile), seitlich)
    vektor = _jon_koordinaten(baum)
    wand = _jon_rampe(baum, _jon_rauschen(baum, vektor, 0.6, 3.0), ((0.3, _jon_heller(wandfarbe, 0.88)), (0.7, _jon_heller(wandfarbe, 1.08))))
    anteil, a, b, farbe = _jon_mischen(baum, "MIX")
    baum.links.new(fenster, anteil)
    baum.links.new(wand, a)
    b.default_value = _jon_farbe(glasfarbe)
    baum.links.new(farbe, bsdf.inputs["Base Color"])
    rau = baum.nodes.new("ShaderNodeMath")
    rau.operation = "MULTIPLY_ADD"
    baum.links.new(fenster, rau.inputs[0])
    rau.inputs[1].default_value = -0.78
    rau.inputs[2].default_value = 0.85
    baum.links.new(rau.outputs["Value"], bsdf.inputs["Roughness"])
    _jon_setzen(bsdf, "Specular IOR Level", 0.8, "Specular")
    if leuchten:
        info = baum.nodes.new("ShaderNodeObjectInfo")
        zelle = baum.nodes.new("ShaderNodeCombineXYZ")
        baum.links.new(rechnen("FLOOR", spalte), zelle.inputs["X"])
        baum.links.new(rechnen("FLOOR", zeile), zelle.inputs["Y"])
        baum.links.new(rechnen("MULTIPLY", info.outputs["Random"], 97.0), zelle.inputs["Z"])
        weiss = baum.nodes.new("ShaderNodeTexWhiteNoise")
        baum.links.new(zelle.outputs["Vector"], weiss.inputs["Vector"])
        an = rechnen("GREATER_THAN", weiss.outputs["Value"], 0.45)
        _jon_setzen(bsdf, "Emission Color", (1.0, 0.7, 0.4, 1.0), "Emission")
        staerke = _jon_eingang(bsdf, "Emission Strength")
        if staerke is not None:
            baum.links.new(rechnen("MULTIPLY", rechnen("MULTIPLY", fenster, an), 2.4), staerke)
    return material


def jon_auto(ort=(0.0, 0.0, 0.0), drehung=0.0, farbe=(0.55, 0.04, 0.04), name="Auto", eltern=None):
    dunkel = _jon_dunkel()
    lack = jon_material(f"{name}Lack", farbe, metall=0.6, rau=0.22)
    _jon_setzen(lack.node_tree.nodes.get("Principled BSDF"), "Coat Weight", 1.0, "Clearcoat")
    scheibe = _jon_lager("JonAutoScheibe", lambda: jon_material("JonAutoScheibe", (0.015, 0.02, 0.025), rau=0.05))
    reifen = _jon_lager("JonAutoReifen", lambda: jon_material("JonAutoReifen", (0.02, 0.02, 0.02), rau=0.8))
    felge = _jon_lager("JonAutoFelge", lambda: jon_metall("JonAutoFelge", (0.7, 0.7, 0.72), 0.25))
    kunststoff = _jon_lager("JonAutoKunststoff", lambda: jon_material("JonAutoKunststoff", (0.04, 0.04, 0.045), rau=0.6))
    vorne_licht = _jon_lager("JonAutoScheinwerfer" + ("Nacht" if dunkel else ""), lambda: jon_material("JonAutoScheinwerfer", (0.9, 0.9, 0.88), rau=0.1, leuchten=12.0 if dunkel else 0.0, leuchtfarbe=(1.0, 0.95, 0.85)))
    hinten_licht = _jon_lager("JonAutoRuecklicht" + ("Nacht" if dunkel else ""), lambda: jon_material("JonAutoRuecklicht", (0.5, 0.02, 0.02), rau=0.2, leuchten=6.0 if dunkel else 1.5, leuchtfarbe=(1.0, 0.05, 0.03)))
    bau = JonBau(name)
    schild = _jon_lager("JonAutoSchild", lambda: jon_material("JonAutoSchild", (0.85, 0.85, 0.82), rau=0.4))
    bau.prisma([(-2.12, 0.3), (2.12, 0.3), (2.2, 0.6), (2.08, 0.8), (0.95, 0.92), (-1.55, 0.95), (-2.1, 0.88), (-2.2, 0.62)], "y", -0.9, 0.9, lack)
    bau.prisma([(-1.52, 0.9), (0.92, 0.9), (0.22, 1.4), (-1.18, 1.42)], "y", -0.8, 0.8, scheibe)
    bau.prisma([(-1.25, 1.39), (0.27, 1.37), (0.22, 1.44), (-1.2, 1.46)], "y", -0.81, 0.81, lack)
    for x in (-1.35, 1.35):
        bau.zylinder((x, 0.0, 0.36), 0.43, 1.81, kunststoff, drehung=(90.0, 0.0, 0.0), segmente=32)
        for y in (-0.8, 0.8):
            bau.zylinder((x, y, 0.34), 0.34, 0.25, reifen, drehung=(90.0, 0.0, 0.0), segmente=32)
            bau.zylinder((x, y * 1.03, 0.34), 0.22, 0.25, felge, drehung=(90.0, 0.0, 0.0), segmente=20)
    for y in (-0.62, 0.62):
        bau.quader((2.15, y, 0.68), (0.08, 0.36, 0.11), vorne_licht)
        bau.quader((-2.17, y, 0.74), (0.06, 0.34, 0.1), hinten_licht)
    bau.quader((2.19, 0.0, 0.52), (0.04, 0.8, 0.16), kunststoff)
    for x in (-2.22, 2.22):
        bau.quader((x, 0.0, 0.36), (0.1, 1.84, 0.16), kunststoff)
        bau.quader((x * 1.01, 0.0, 0.48), (0.02, 0.5, 0.11), schild)
    for y in (-0.94, 0.94):
        bau.quader((0.78, y, 1.0), (0.12, 0.12, 0.08), lack)
    return bau.fertig(_jon_ort(ort), drehung, fase=0.04, eltern=eltern)


def jon_laterne(ort=(0.0, 0.0, 0.0), drehung=0.0, hoehe=5.5, name="Laterne", eltern=None, licht=None):
    licht = _jon_dunkel() if licht is None else licht
    pfahl = _jon_lager("JonLaternenpfahl", lambda: jon_metall("JonLaternenpfahl", (0.12, 0.13, 0.14), 0.45))
    kopf = _jon_lager("JonLaternenkopf" + ("An" if licht else ""), lambda: jon_material("JonLaternenkopf", (0.9, 0.9, 0.85), rau=0.3, leuchten=25.0 if licht else 0.0, leuchtfarbe=(1.0, 0.78, 0.5)))
    bau = JonBau(name)
    bau.zylinder((0.0, 0.0, hoehe / 2), 0.07, hoehe, pfahl, oben=0.05, segmente=12)
    bau.quader((0.0, -0.55, hoehe), (0.08, 1.1, 0.08), pfahl)
    bau.quader((0.0, -1.05, hoehe - 0.08), (0.3, 0.5, 0.12), pfahl)
    bau.quader((0.0, -1.05, hoehe - 0.15), (0.24, 0.42, 0.03), kopf)
    objekt = bau.fertig(_jon_ort(ort), drehung, eltern=eltern)
    if licht:
        daten = bpy.data.lights.new(f"{name}Licht", type="SPOT")
        daten.energy = 900.0
        daten.color = (1.0, 0.78, 0.5)
        daten.spot_size = math.radians(110.0)
        daten.spot_blend = 0.6
        if hasattr(daten, "use_shadow"):
            daten.use_shadow = False
        strahler = bpy.data.objects.new(daten.name, daten)
        bpy.context.collection.objects.link(strahler)
        strahler.parent = objekt
        strahler.location = (0.0, -1.05, hoehe - 0.25)
    return objekt


JON_FASSADEN = (
    ((0.62, 0.6, 0.57), (0.03, 0.05, 0.07)),
    ((0.42, 0.2, 0.14), (0.04, 0.05, 0.06)),
    ((0.78, 0.72, 0.6), (0.04, 0.06, 0.08)),
    ((0.2, 0.26, 0.32), (0.05, 0.09, 0.13)),
    ((0.85, 0.85, 0.83), (0.03, 0.05, 0.08)),
    ((0.5, 0.45, 0.4), (0.03, 0.04, 0.05)),
)


def jon_stadt(bloecke=4, blockgroesse=26.0, strasse=9.0, hoehe=(9.0, 60.0), samen=4, baeume=True, laternen=True, autos=True, kamera=True, blick="schraeg"):
    zufall = random.Random(samen)
    n = max(1, int(bloecke))
    raster = blockgroesse + strasse
    ausdehnung = n * blockgroesse + (n + 1) * strasse
    stadt = _jon_leer("Stadt")
    fassaden = [jon_fassade(f"Fassade{i}", w, g) for i, (w, g) in enumerate(JON_FASSADEN)]
    erdgeschoss = jon_fensterglas("Ladenglas", 0.5 if _jon_dunkel() else 0.0)
    dach = jon_boden_material("Stadtdach", (0.22, 0.22, 0.23))
    technik = jon_material("Dachtechnik", (0.55, 0.56, 0.57), metall=0.5, rau=0.4)
    gehweg = jon_boden_material("Gehweg", (0.5, 0.49, 0.47), 0.8)
    farbe = jon_material("Markierung", (0.85, 0.85, 0.82), rau=0.6)
    asphalt = JonBau("Strassen")
    asphalt_material = jon_boden_material("Asphalt", (0.055, 0.055, 0.06), 0.85)
    asphalt.quader((0.0, 0.0, -0.05), (ausdehnung + 30.0, ausdehnung + 30.0, 0.1), asphalt_material)
    asphalt.fertig(eltern=stadt)["jon_hintergrund"] = True
    jon_boden("beton", farbe=(0.15, 0.15, 0.145), ort=(0.0, 0.0, -0.12), name="Umland").parent = stadt
    zentren = [-ausdehnung / 2 + strasse + blockgroesse / 2 + i * raster for i in range(n)]
    strassen = [-ausdehnung / 2 + strasse / 2 + i * raster for i in range(n + 1)]
    gebaeude = []
    baumpunkte = []
    for bx in zentren:
        for by in zentren:
            platte = JonBau("Gehweg")
            platte.quader((0.0, 0.0, 0.08), (blockgroesse, blockgroesse, 0.16), gehweg)
            platte.fertig((bx, by, 0.0), eltern=stadt, fase=0.04)
            innen = blockgroesse - 5.0
            teilung = zufall.choice((1, 2, 2, 3))
            stueck = innen / teilung
            for i in range(teilung):
                for j in range(teilung):
                    if teilung > 1 and zufall.random() < 0.12:
                        continue
                    breite = stueck - zufall.uniform(1.0, 2.5)
                    tiefe = stueck - zufall.uniform(1.0, 2.5)
                    x = bx - innen / 2 + stueck * (i + 0.5)
                    y = by - innen / 2 + stueck * (j + 0.5)
                    naehe = max(0.0, 1.0 - math.hypot(x, y) / (ausdehnung * 0.62))
                    gipfel = hoehe[0] + (hoehe[1] - hoehe[0]) * (naehe ** 1.6) * zufall.uniform(0.45, 1.0) / max(1.0, teilung * 0.8)
                    gipfel = max(hoehe[0], round(gipfel / 3.4) * 3.4 + 0.6)
                    fassade = zufall.choice(fassaden)
                    bau = JonBau(f"Gebaeude{len(gebaeude) + 1}")
                    bau.quader((0.0, 0.0, 2.0), (breite + 0.12, tiefe + 0.12, 4.0), erdgeschoss)
                    bau.quader((0.0, 0.0, 4.0 + (gipfel - 4.0) / 2), (breite, tiefe, gipfel - 4.0), fassade)
                    oben = gipfel
                    if gipfel > 28 and zufall.random() < 0.55:
                        aufsatz = gipfel * zufall.uniform(0.18, 0.35)
                        bau.quader((0.0, 0.0, gipfel + aufsatz / 2), (breite * 0.68, tiefe * 0.68, aufsatz), fassade)
                        bau.quader((0.0, 0.0, gipfel + 0.15), (breite + 0.2, tiefe + 0.2, 0.3), dach)
                        oben = gipfel + aufsatz
                        breite, tiefe = breite * 0.68, tiefe * 0.68
                    bau.quader((0.0, 0.0, oben + 0.2), (breite + 0.25, tiefe + 0.25, 0.4), dach)
                    for _ in range(zufall.randint(1, 3)):
                        gw, gt, gh = zufall.uniform(1.2, 3.0), zufall.uniform(1.2, 3.0), zufall.uniform(0.8, 2.4)
                        bau.quader((zufall.uniform(-breite / 3, breite / 3), zufall.uniform(-tiefe / 3, tiefe / 3), oben + 0.4 + gh / 2), (gw, gt, gh), technik)
                    gebaeude.append(bau.fertig((x, y, 0.16), eltern=stadt))
            if baeume:
                for seite in range(4):
                    for k in range(1, 4):
                        anteil = -0.5 + k / 4
                        rand = blockgroesse / 2 - 1.1
                        punkt = ((bx + anteil * blockgroesse, by - rand), (bx + rand, by + anteil * blockgroesse), (bx - anteil * blockgroesse, by + rand), (bx - rand, by - anteil * blockgroesse))[seite]
                        baumpunkte.append(((punkt[0], punkt[1], 0.16), 5.5))
    if baumpunkte:
        _jon_baeume(baumpunkte, "Stadtbaeume", "laub", None, stadt, samen)
    linien = JonBau("Markierungen")
    for lage in strassen:
        schritt = -ausdehnung / 2
        while schritt < ausdehnung / 2:
            if all(abs(schritt + 1.25 - s) > strasse / 2 + 1.5 for s in strassen):
                linien.quader((schritt + 1.25, lage, 0.006), (2.5, 0.16, 0.012), farbe)
                linien.quader((lage, schritt + 1.25, 0.006), (0.16, 2.5, 0.012), farbe)
            schritt += 5.5
        for quer in strassen:
            for richtung in (-1.0, 1.0):
                for streifen in range(int((strasse - 1.2) / 0.9)):
                    versatz = -strasse / 2 + 0.8 + streifen * 0.9
                    linien.quader((quer + richtung * (strasse / 2 + 1.6), lage + versatz, 0.006), (2.4, 0.45, 0.012), farbe)
                    linien.quader((lage + versatz, quer + richtung * (strasse / 2 + 1.6), 0.006), (0.45, 2.4, 0.012), farbe)
    linien.fertig(eltern=stadt)
    if laternen:
        for bx in zentren:
            for by in zentren:
                for ex, ey, winkel in ((-1, -1, 45.0), (1, 1, -135.0)):
                    jon_laterne((bx + ex * (blockgroesse / 2 - 0.6), by + ey * (blockgroesse / 2 - 0.6), 0.16), winkel + 180.0, eltern=stadt)
    if autos:
        lacke = ((0.6, 0.03, 0.03), (0.02, 0.1, 0.35), (0.8, 0.8, 0.8), (0.03, 0.03, 0.035), (0.9, 0.55, 0.05), (0.15, 0.3, 0.2), (0.45, 0.46, 0.5))
        for nummer in range(n * 4):
            lage = zufall.choice(strassen)
            spur = zufall.choice((-1.0, 1.0))
            entlang = zufall.choice(zentren) + zufall.uniform(-blockgroesse / 3, blockgroesse / 3)
            if zufall.random() < 0.5:
                jon_auto((entlang, lage + spur * strasse / 4, 0.0), 0.0 if spur < 0 else 180.0, zufall.choice(lacke), f"Auto{nummer + 1}", stadt)
            else:
                jon_auto((lage - spur * strasse / 4, entlang, 0.0), 90.0 if spur < 0 else -90.0, zufall.choice(lacke), f"Auto{nummer + 1}", stadt)
    if kamera:
        if str(blick).lower().startswith("strass"):
            szene = bpy.context.scene
            kam = szene.camera or bpy.data.objects.new("JonKamera", bpy.data.cameras.new("JonKamera"))
            if kam.name not in szene.collection.objects and kam.users_collection == ():
                szene.collection.objects.link(kam)
            szene.camera = kam
            kam.data.lens = 22.0
            x = strassen[len(strassen) // 2] - strasse * 0.25
            kam.location = (x, -ausdehnung / 2 - 4.0, 1.7)
            ziel = Vector((x + 2.0, ausdehnung / 2, 9.0))
            kam.rotation_euler = (ziel - Vector(kam.location)).to_track_quat("-Z", "Y").to_euler()
            kam.data.clip_end = ausdehnung * 4
            jon_kamera_fest()
        else:
            jon_kamera(richtung=(0.75, -1.0, 0.5), brennweite=28.0, objekte=gebaeude, rand=0.82)
            jon_kamera_fest()
    return stadt


def jon_studio(farbe=(0.8, 0.8, 0.82), licht=True, objekte=None):
    bpy.context.view_layer.update()
    motiv = jon_motiv(objekte)
    if motiv:
        punkte = _jon_ecken(motiv)
        kleinste = Vector((min(p.x for p in punkte), min(p.y for p in punkte), min(p.z for p in punkte)))
        groesste = Vector((max(p.x for p in punkte), max(p.y for p in punkte), max(p.z for p in punkte)))
    else:
        kleinste, groesste = Vector((-1.0, -1.0, 0.0)), Vector((1.0, 1.0, 2.0))
    mitte = (kleinste + groesste) / 2
    radius = max((groesste - kleinste).length / 2, 0.2)
    boden = kleinste.z
    weite, rueck, kehle, hoch = radius * 30, radius * 3.5, radius * 1.5, radius * 14
    profil = [(-radius * 30, 0.0), (rueck - kehle, 0.0)]
    for schritt in range(1, 12):
        winkel = schritt / 12 * math.pi / 2
        profil.append((rueck - kehle + math.sin(winkel) * kehle, kehle - math.cos(winkel) * kehle))
    profil += [(rueck, kehle), (rueck, hoch)]
    bau = JonBau("Studio")
    material = jon_material("Studiohintergrund", farbe, rau=0.75)
    for i in range(len(profil) - 1):
        bau.flaeche(((-weite, profil[i][0], profil[i][1]), (weite, profil[i][0], profil[i][1]), (weite, profil[i + 1][0], profil[i + 1][1]), (-weite, profil[i + 1][0], profil[i + 1][1])), material, True)
    studio = bau.fertig((mitte.x, mitte.y, boden))
    studio["jon_hintergrund"] = True
    szene = bpy.context.scene
    szene["jon_studio"] = True
    welt = szene.world or bpy.data.worlds.new("JonWelt")
    szene.world = welt
    welt.use_nodes = True
    grund = welt.node_tree.nodes.get("Background")
    if grund is not None:
        grund.inputs["Color"].default_value = _jon_farbe(_jon_heller(farbe, 0.45))
        grund.inputs["Strength"].default_value = 1.0
    if licht:
        abstand = radius * 4
        for name, lage, staerke, groesse in (("Hauptlicht", (-0.8, -1.0, 0.9), 28.0, 1.2), ("Fuelllicht", (1.0, -0.7, 0.35), 10.0, 2.0), ("Kantenlicht", (0.5, 1.0, 0.9), 22.0, 0.8)):
            daten = bpy.data.lights.new(name, type="AREA")
            daten.energy = staerke * abstand * abstand
            daten.size = radius * groesse * 2
            lampe = bpy.data.objects.new(name, daten)
            szene.collection.objects.link(lampe)
            lampe.location = mitte + Vector(lage).normalized() * abstand
            lampe.rotation_euler = (mitte - lampe.location).to_track_quat("-Z", "Y").to_euler()
    return studio


def jon_raum(breite=6.0, tiefe=5.0, hoehe=2.7, wandfarbe=(0.9, 0.88, 0.84), boden="holz", bodenfarbe=None, fenster="hinten", fensterbreite=2.2, decke=True, licht=True, kamera=True, name="Raum"):
    b, t, h = float(breite), float(tiefe), float(hoehe)
    d = 0.15
    if "jon_zeit" not in bpy.context.scene:
        jon_himmel("tag")
    raum = _jon_leer(name)
    bpy.context.scene["jon_raum"] = {"name": raum.name, "b": b, "t": t, "h": h}
    wand = jon_putz(f"{name}Wand", wandfarbe, relief=0.05)
    leiste = jon_material(f"{name}Leiste", (0.93, 0.93, 0.91), rau=0.4)
    art = str(boden).lower()
    if art in ("fliesen", "kacheln"):
        belag = jon_fliesen(f"{name}Boden", bodenfarbe or (0.82, 0.8, 0.76))
    elif art in ("teppich", "teppichboden"):
        belag = jon_stoff(f"{name}Boden", bodenfarbe or (0.45, 0.42, 0.38))
    elif art in ("beton", "stein"):
        belag = jon_boden_material(f"{name}Boden", bodenfarbe or (0.5, 0.5, 0.48), 0.6)
    else:
        belag = jon_holz(f"{name}Boden", bodenfarbe or (0.5, 0.32, 0.17), 0.35, dielen=True)
    flaechen = JonBau(f"{name}Boden")
    flaechen.quader((0.0, d / 2, -0.05), (b + 2 * d, t + d, 0.1), belag)
    flaechen.fertig(eltern=raum)
    if not any(o.get("jon_hintergrund") and o.name.startswith(("Boden", "Umland")) for o in bpy.context.scene.objects):
        jon_boden("gras", ort=(0.0, 0.0, -0.12), name="Umland")
    waende = {}
    for seite, mitte, groesse in (("hinten", (0.0, t / 2 + d / 2, h / 2), (b + 2 * d, d, h)), ("links", (-b / 2 - d / 2, 0.0, h / 2), (d, t, h)), ("rechts", (b / 2 + d / 2, 0.0, h / 2), (d, t, h))):
        bau = JonBau(f"{name}Wand{seite.title()}")
        bau.quader(mitte, groesse, wand)
        waende[seite] = bau.fertig(eltern=raum)
    if decke:
        bau = JonBau(f"{name}Decke")
        bau.quader((0.0, d / 2, h + 0.06), (b + 2 * d, t + d, 0.12), jon_putz(f"{name}Deckenputz", (0.95, 0.95, 0.94), relief=0.03))
        bau.fertig(eltern=raum)
    leisten = JonBau(f"{name}Leisten")
    leisten.quader((0.0, t / 2 - 0.01, 0.04), (b, 0.02, 0.08), leiste)
    leisten.quader((-b / 2 + 0.01, 0.0, 0.04), (0.02, t, 0.08), leiste)
    leisten.quader((b / 2 - 0.01, 0.0, 0.04), (0.02, t, 0.08), leiste)
    leisten.fertig(eltern=raum)
    if fenster:
        seite = str(fenster).lower()
        fb, fh, unten = float(fensterbreite), min(1.6, h * 0.58), min(0.9, h * 0.33)
        if seite.startswith("l"):
            mitte, drehwinkel, wand_objekt = Vector((-b / 2 - d / 2, 0.0, unten + fh / 2)), (0.0, 0.0, 90.0), waende["links"]
        elif seite.startswith("r"):
            mitte, drehwinkel, wand_objekt = Vector((b / 2 + d / 2, 0.0, unten + fh / 2)), (0.0, 0.0, 90.0), waende["rechts"]
        else:
            mitte, drehwinkel, wand_objekt = Vector((0.0, t / 2 + d / 2, unten + fh / 2)), (0.0, 0.0, 0.0), waende["hinten"]
        schnitt = JonBau(f"{name}Fensteroeffnung")
        schnitt.quader(mitte, (fb, 1.0, fh), wand, drehwinkel)
        schnitt_objekt = schnitt.fertig(eltern=raum)
        schnitt_objekt.hide_render = True
        schnitt_objekt.display_type = "WIRE"
        schnitt_objekt["jon_hintergrund"] = True
        loch = wand_objekt.modifiers.new("Fenster", "BOOLEAN")
        loch.operation = "DIFFERENCE"
        loch.object = schnitt_objekt
        rahmen = jon_material(f"{name}Fensterrahmen", (0.95, 0.95, 0.94), rau=0.35)
        scheibe = jon_glas(f"{name}Fensterglas", deckkraft=0.06)
        teile = JonBau(f"{name}Fenster")
        quer = Vector((1.0, 0.0, 0.0)) if drehwinkel[2] == 0.0 else Vector((0.0, 1.0, 0.0))
        r = 0.06
        for z in (unten + r / 2, unten + fh - r / 2, unten + fh * 0.62):
            teile.quader(Vector((mitte.x, mitte.y, z)), (fb, 0.08, r if z != unten + fh * 0.62 else 0.04), rahmen, drehwinkel)
        for versatz in (-fb / 2 + r / 2, fb / 2 - r / 2, 0.0):
            teile.quader(mitte + quer * versatz, (r if versatz else 0.04, 0.08, fh), rahmen, drehwinkel)
        teile.quader(mitte, (fb - r, 0.01, fh - r), scheibe, drehwinkel)
        innen = Vector((0.0, -1.0, 0.0)) if drehwinkel[2] == 0.0 else Vector((1.0 if seite.startswith("l") else -1.0, 0.0, 0.0))
        teile.quader(Vector((mitte.x, mitte.y, unten - 0.025)) + innen * 0.1, (fb + 0.2, 0.3, 0.04), rahmen, drehwinkel)
        teile.fertig(eltern=raum, fase=0.006)
    if licht:
        daten = bpy.data.lights.new(f"{name}Deckenlicht", type="AREA")
        daten.shape = "RECTANGLE"
        daten.size = b * 0.5
        daten.size_y = t * 0.5
        daten.energy = 9.0 * b * t
        daten.color = (1.0, 0.93, 0.85)
        lampe = bpy.data.objects.new(daten.name, daten)
        bpy.context.collection.objects.link(lampe)
        lampe.parent = raum
        lampe.location = (0.0, 0.0, h - 0.05)
    if kamera:
        szene = bpy.context.scene
        kam = szene.camera
        if kam is None:
            kam = bpy.data.objects.new("JonKamera", bpy.data.cameras.new("JonKamera"))
            szene.collection.objects.link(kam)
            szene.camera = kam
        kam.data.lens = 20.0
        kam.location = (b * 0.2, -t / 2 + 0.15, min(1.65, h * 0.6))
        ziel = Vector((-b * 0.04, t * 0.12, h * 0.36))
        kam.rotation_euler = (ziel - Vector(kam.location)).to_track_quat("-Z", "Y").to_euler()
        kam.data.clip_start = 0.05
        jon_kamera_fest()
    return raum


def _jon_wand(objekt, art="moebel"):
    objekt["jon_wand"] = art
    return objekt


def _jon_moebel_pruefen():
    szene = bpy.context.scene
    raum = szene.get("jon_raum")
    huelle = bpy.data.objects.get(str(raum.get("name", ""))) if raum else None
    if huelle is None:
        return 0
    bpy.context.view_layer.update()
    b, t = float(raum["b"]), float(raum["t"])
    zurueck = huelle.matrix_world.inverted()
    waende = ((Vector((0.0, 1.0, 0.0)), 0.0), (Vector((-1.0, 0.0, 0.0)), 90.0), (Vector((1.0, 0.0, 0.0)), -90.0))
    korrigiert = 0
    for objekt in list(szene.objects):
        art = objekt.get("jon_wand")
        if not art:
            continue
        lokal = zurueck @ objekt.matrix_world
        ort = lokal.translation
        abstaende = (t / 2 - ort.y, ort.x + b / 2, b / 2 - ort.x)
        stelle = min(range(3), key=lambda i: abstaende[i])
        if abstaende[stelle] > (1.0 if art == "bild" else 1.3):
            continue
        aussen, winkel = waende[stelle]
        vorne = lokal.to_3x3() @ Vector((0.0, -1.0, 0.0))
        vorne.z = 0.0
        if vorne.length < 1e-6:
            continue
        vorne.normalize()
        if art == "bild":
            ziel = Vector((ort.x, t / 2 - 0.025, ort.z)) if stelle == 0 else Vector((-b / 2 + 0.025 if stelle == 1 else b / 2 - 0.025, ort.y, ort.z))
            neu = huelle.matrix_world @ ziel
            if (neu - objekt.matrix_world.translation).length > 1e-4 or vorne.dot(aussen) > -0.7:
                objekt.location = neu if objekt.parent is None else objekt.parent.matrix_world.inverted() @ neu
                objekt.rotation_euler = (0.0, 0.0, math.radians(winkel) + huelle.matrix_world.to_euler().z)
                korrigiert += 1
        elif vorne.dot(aussen) > 0.3:
            objekt.rotation_euler = (objekt.rotation_euler.x, objekt.rotation_euler.y, math.radians(winkel) + huelle.matrix_world.to_euler().z)
            korrigiert += 1
    return korrigiert


def _jon_moebel_ort(ort):
    x, y, z = _jon_ort(ort)
    return (x, y, z)


def jon_sofa(ort=(0.0, 1.6, 0.0), drehung=0.0, farbe=(0.24, 0.34, 0.46), breite=2.2, sitze=3, kissenfarbe=(0.85, 0.62, 0.3), name="Sofa"):
    stoff = jon_stoff(f"{name}Stoff", farbe)
    kissen = jon_stoff(f"{name}Kissen", kissenfarbe)
    fuss = jon_holz(f"{name}Fuss", (0.18, 0.11, 0.06), 0.5)
    b = float(breite)
    plaetze = max(1, int(sitze))
    bau = JonBau(name)
    bau.quader((0.0, 0.05, 0.27), (b, 0.92, 0.3), stoff)
    bau.quader((0.0, 0.42, 0.62), (b, 0.18, 0.7), stoff)
    for seite in (-1.0, 1.0):
        bau.quader((seite * (b / 2 - 0.1), 0.05, 0.43), (0.2, 0.92, 0.62), stoff)
    sitz = (b - 0.4) / plaetze
    for i in range(plaetze):
        x = -b / 2 + 0.2 + sitz * (i + 0.5)
        bau.quader((x, -0.06, 0.51), (sitz - 0.02, 0.7, 0.18), stoff)
        bau.quader((x, 0.26, 0.76), (sitz - 0.02, 0.2, 0.46), stoff, (-12.0, 0.0, 0.0))
    for seite in (-1.0, 1.0):
        bau.quader((seite * (b / 2 - 0.42), 0.12, 0.78), (0.42, 0.14, 0.42), kissen, (-14.0, 0.0, seite * 12.0))
        for y in (-0.32, 0.4):
            bau.zylinder((seite * (b / 2 - 0.12), y, 0.06), 0.025, 0.12, fuss, oben=0.018, segmente=12)
    return _jon_wand(bau.fertig(_jon_moebel_ort(ort), drehung, fase=0.045), "moebel")


def jon_sessel(ort=(0.0, 0.0, 0.0), drehung=0.0, farbe=(0.55, 0.25, 0.18), name="Sessel"):
    return jon_sofa(ort, drehung, farbe, breite=1.0, sitze=1, kissenfarbe=_jon_heller(farbe, 1.3), name=name)


def jon_tisch(ort=(0.0, 0.0, 0.0), drehung=0.0, breite=1.6, tiefe=0.9, hoehe=0.75, farbe=(0.45, 0.27, 0.13), name="Tisch"):
    holz = jon_holz(f"{name}Holz", farbe, 0.4)
    bau = JonBau(name)
    b, t, h = float(breite), float(tiefe), float(hoehe)
    bau.quader((0.0, 0.0, h - 0.02), (b, t, 0.04), holz)
    for x in (-1.0, 1.0):
        bau.quader((x * (b / 2 - 0.1), 0.0, h - 0.1), (0.03, t - 0.2, 0.1), holz)
        for y in (-1.0, 1.0):
            bau.quader((x * (b / 2 - 0.08), y * (t / 2 - 0.08), (h - 0.04) / 2), (0.06, 0.06, h - 0.04), holz)
    for y in (-1.0, 1.0):
        bau.quader((0.0, y * (t / 2 - 0.1), h - 0.1), (b - 0.2, 0.03, 0.1), holz)
    return bau.fertig(_jon_moebel_ort(ort), drehung, fase=0.006)


def jon_couchtisch(ort=(0.0, 0.0, 0.0), drehung=0.0, breite=1.1, tiefe=0.6, farbe=(0.38, 0.23, 0.11), name="Couchtisch"):
    return jon_tisch(ort, drehung, breite, tiefe, 0.42, farbe, name)


def jon_stuhl(ort=(0.0, 0.0, 0.0), drehung=0.0, farbe=(0.42, 0.26, 0.13), polster=None, name="Stuhl"):
    holz = jon_holz(f"{name}Holz", farbe, 0.45)
    sitz = jon_stoff(f"{name}Polster", polster) if polster else holz
    bau = JonBau(name)
    bau.quader((0.0, 0.0, 0.45), (0.44, 0.44, 0.04), sitz)
    for x in (-0.19, 0.19):
        for y in (-0.19, 0.19):
            hoehe = 0.92 if y > 0 else 0.43
            bau.quader((x, y, hoehe / 2), (0.035, 0.035, hoehe), holz)
    bau.quader((0.0, 0.19, 0.78), (0.42, 0.025, 0.2), holz)
    bau.quader((0.0, 0.19, 0.58), (0.42, 0.02, 0.04), holz)
    return bau.fertig(_jon_moebel_ort(ort), drehung, fase=0.006)


def jon_lampe(ort=(0.0, 0.0, 0.0), art="steh", farbe=(1.0, 0.82, 0.58), staerke=None, schirmfarbe=(0.93, 0.88, 0.78), name="Lampe"):
    metall = jon_metall(f"{name}Metall", (0.12, 0.12, 0.12), 0.35)
    schirm = jon_material(f"{name}Schirm", schirmfarbe, rau=0.8, leuchten=2.0, leuchtfarbe=farbe)
    bau = JonBau(name)
    art = str(art).lower()
    if not art.startswith(("decke", "haenge", "pendel")) and _jon_ort(ort)[2] > 1.6:
        art = "decke"
    if art.startswith("decke") or art.startswith("haenge") or art.startswith("pendel"):
        hoehe = _jon_ort(ort)[2] or 2.2
        bau.zylinder((0.0, 0.0, -0.4), 0.006, 0.8, metall, segmente=8)
        bau.zylinder((0.0, 0.0, -0.95), 0.3, 0.3, schirm, oben=0.08, segmente=32)
        bau.zylinder((0.0, 0.0, -0.01), 0.06, 0.02, metall, segmente=16)
        licht_z, basis = -1.05, (ort[0], ort[1], hoehe)
        energie = 120.0
    elif art.startswith("tisch"):
        bau.zylinder((0.0, 0.0, 0.01), 0.09, 0.02, metall, segmente=24)
        bau.zylinder((0.0, 0.0, 0.2), 0.012, 0.38, metall, segmente=8)
        bau.zylinder((0.0, 0.0, 0.42), 0.16, 0.2, schirm, oben=0.1, segmente=32)
        licht_z, basis = 0.38, _jon_moebel_ort(ort)
        energie = 25.0
    else:
        bau.zylinder((0.0, 0.0, 0.015), 0.16, 0.03, metall, segmente=32)
        bau.zylinder((0.0, 0.0, 0.8), 0.015, 1.55, metall, segmente=10)
        bau.zylinder((0.0, 0.0, 1.55), 0.25, 0.32, schirm, oben=0.16, segmente=32)
        licht_z, basis = 1.5, _jon_moebel_ort(ort)
        energie = 60.0
    objekt = bau.fertig(basis)
    daten = bpy.data.lights.new(f"{name}Licht", type="POINT")
    daten.energy = float(staerke) if staerke else energie
    daten.color = farbe
    daten.shadow_soft_size = 0.08
    licht = bpy.data.objects.new(daten.name, daten)
    bpy.context.collection.objects.link(licht)
    licht.parent = objekt
    licht.location = (0.0, 0.0, licht_z)
    return objekt


def jon_teppich(ort=(0.0, 0.0, 0.0), groesse=(2.4, 1.7), farbe=(0.55, 0.22, 0.18), randfarbe=(0.88, 0.8, 0.66), drehung=0.0, name="Teppich"):
    material, baum, bsdf = _jon_knoten(name)
    koordinaten = baum.nodes.new("ShaderNodeTexCoord")
    teile = baum.nodes.new("ShaderNodeSeparateXYZ")
    baum.links.new(koordinaten.outputs["Generated"], teile.inputs["Vector"])
    rand = []
    for achse in ("X", "Y"):
        abstand = baum.nodes.new("ShaderNodeMath")
        abstand.operation = "PINGPONG"
        abstand.inputs[1].default_value = 0.5
        baum.links.new(teile.outputs[achse], abstand.inputs[0])
        rand.append(abstand.outputs["Value"])
    kleiner = baum.nodes.new("ShaderNodeMath")
    kleiner.operation = "MINIMUM"
    baum.links.new(rand[0], kleiner.inputs[0])
    baum.links.new(rand[1], kleiner.inputs[1])
    muster = _jon_rampe(baum, kleiner.outputs["Value"], ((0.0, randfarbe), (0.06, randfarbe), (0.061, farbe), (0.1, farbe), (0.101, randfarbe), (0.115, randfarbe), (0.116, farbe), (1.0, _jon_heller(farbe, 0.85))))
    baum.links.new(muster, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.95
    _jon_setzen(bsdf, "Sheen Weight", 0.8, "Sheen")
    _jon_relief(baum, bsdf, _jon_rauschen(baum, koordinaten.outputs["Object"], 400.0, 2.0), 0.35, 0.004)
    bau = JonBau(name)
    bau.quader((0.0, 0.0, 0.006), (groesse[0], groesse[1], 0.012), material)
    return bau.fertig(_jon_moebel_ort(ort), drehung)


def jon_regal(ort=(0.0, 0.0, 0.0), drehung=0.0, breite=1.2, hoehe=1.9, tiefe=0.34, farbe=(0.85, 0.82, 0.76), buecher=True, samen=5, name="Regal"):
    zufall = random.Random(samen)
    holz = jon_holz(f"{name}Holz", farbe, 0.5) if sum(farbe) < 2.0 else jon_material(f"{name}Holz", farbe, rau=0.5)
    farben = [jon_material(f"{name}Buch{i}", f, rau=0.6) for i, f in enumerate(((0.5, 0.08, 0.06), (0.06, 0.18, 0.4), (0.12, 0.3, 0.16), (0.8, 0.62, 0.3), (0.12, 0.12, 0.13), (0.82, 0.8, 0.74)))]
    b, h, t = float(breite), float(hoehe), float(tiefe)
    bau = JonBau(name)
    for seite in (-1.0, 1.0):
        bau.quader((seite * (b / 2 - 0.0125), 0.0, h / 2), (0.025, t, h), holz)
    bau.quader((0.0, t / 2 - 0.005, h / 2), (b, 0.01, h), holz)
    boeden = max(3, int(h / 0.36))
    for i in range(boeden + 1):
        z = 0.06 + (h - 0.08) * i / boeden
        bau.quader((0.0, 0.0, z), (b - 0.05, t, 0.025), holz)
        if buecher and i < boeden:
            x = -b / 2 + 0.05
            platz = (h - 0.08) / boeden - 0.04
            while x < b / 2 - 0.12:
                if zufall.random() < 0.12:
                    x += zufall.uniform(0.06, 0.18)
                    continue
                dicke = zufall.uniform(0.022, 0.05)
                buchhoehe = min(platz, zufall.uniform(0.18, 0.29))
                bau.quader((x + dicke / 2, -0.01, z + 0.0125 + buchhoehe / 2), (dicke, t * zufall.uniform(0.7, 0.9), buchhoehe), zufall.choice(farben))
                x += dicke + 0.003
    return _jon_wand(bau.fertig(_jon_moebel_ort(ort), drehung, fase=0.003), "moebel")


def jon_pflanze(ort=(0.0, 0.0, 0.0), groesse=1.0, topffarbe=(0.72, 0.38, 0.24), farbe=(0.1, 0.3, 0.08), samen=2, name="Pflanze"):
    zufall = random.Random(samen)
    g = float(groesse)
    topf = jon_material(f"{name}Topf", topffarbe, rau=0.7)
    erde = jon_material(f"{name}Erde", (0.08, 0.05, 0.03), rau=1.0)
    blatt = _jon_laubmaterial(f"{name}Blatt", farbe)
    bau = JonBau(name)
    bau.zylinder((0.0, 0.0, 0.16 * g), 0.18 * g, 0.32 * g, topf, oben=0.21 * g, segmente=28)
    bau.zylinder((0.0, 0.0, 0.31 * g), 0.19 * g, 0.02 * g, erde, segmente=28)
    for nummer in range(16):
        winkel = nummer * 137.5
        neigung = zufall.uniform(25.0, 65.0)
        laenge = zufall.uniform(0.28, 0.45) * g
        richtung = Vector((math.cos(math.radians(winkel)) * math.sin(math.radians(neigung)), math.sin(math.radians(winkel)) * math.sin(math.radians(neigung)), math.cos(math.radians(neigung))))
        mitte = Vector((0.0, 0.0, 0.34 * g)) + richtung * laenge * 0.9
        bau.kugel(mitte, 1.0, blatt, (0.07 * g, laenge, 0.012 * g), (-(90.0 - neigung), 0.0, winkel - 90.0), feinheit=2)
        bau.zylinder(Vector((0.0, 0.0, 0.34 * g)) + richtung * laenge * 0.3, 0.006 * g, laenge * 0.6, blatt, segmente=6, drehung=(math.degrees(math.acos(max(-1.0, min(1.0, richtung.z)))), 0.0, winkel + 90.0))
    return bau.fertig(_jon_moebel_ort(ort))


def jon_bett(ort=(0.0, 1.0, 0.0), drehung=0.0, breite=1.6, laenge=2.0, farbe=(0.42, 0.52, 0.66), holzfarbe=(0.4, 0.26, 0.14), name="Bett"):
    holz = jon_holz(f"{name}Holz", holzfarbe, 0.45)
    decke = jon_stoff(f"{name}Decke", farbe)
    laken = jon_stoff(f"{name}Laken", (0.95, 0.95, 0.94))
    b, l = float(breite), float(laenge)
    bau = JonBau(name)
    bau.quader((0.0, 0.0, 0.2), (b + 0.08, l + 0.08, 0.24), holz)
    for x in (-1.0, 1.0):
        for y in (-1.0, 1.0):
            bau.quader((x * (b / 2 - 0.02), y * (l / 2 - 0.02), 0.05), (0.07, 0.07, 0.1), holz)
    bau.quader((0.0, l / 2 + 0.03, 0.55), (b + 0.12, 0.06, 1.0), holz)
    bau.quader((0.0, 0.0, 0.42), (b, l, 0.22), laken)
    bau.quader((0.0, -l * 0.14, 0.55), (b + 0.06, l * 0.7, 0.1), decke)
    for x in (-b / 4, b / 4) if b > 1.2 else (0.0,):
        bau.quader((x, l / 2 - 0.3, 0.6), (min(0.68, b / 2 - 0.06), 0.42, 0.14), laken, (-10.0, 0.0, 0.0))
    return _jon_wand(bau.fertig(_jon_moebel_ort(ort), drehung, fase=0.04), "moebel")


def jon_schrank(ort=(0.0, 0.0, 0.0), drehung=0.0, breite=1.2, hoehe=2.0, tiefe=0.6, farbe=(0.9, 0.89, 0.86), tueren=2, name="Schrank"):
    korpus = jon_material(f"{name}Korpus", farbe, rau=0.45)
    griff = jon_metall(f"{name}Griff", (0.7, 0.7, 0.7), 0.3)
    b, h, t = float(breite), float(hoehe), float(tiefe)
    bau = JonBau(name)
    bau.quader((0.0, 0.0, h / 2 + 0.04), (b, t, h - 0.08), korpus)
    bau.quader((0.0, 0.02, 0.02), (b - 0.04, t - 0.04, 0.04), griff)
    anzahl = max(1, int(tueren))
    for i in range(anzahl):
        x = -b / 2 + b * (i + 0.5) / anzahl
        bau.quader((x, -t / 2 - 0.01, h / 2 + 0.04), (b / anzahl - 0.006, 0.02, h - 0.1), korpus)
        seite = 1.0 if i % 2 == 0 else -1.0
        bau.quader((x + seite * (b / anzahl / 2 - 0.06), -t / 2 - 0.035, h * 0.52), (0.015, 0.02, 0.3), griff)
    return _jon_wand(bau.fertig(_jon_moebel_ort(ort), drehung, fase=0.004), "moebel")


def jon_fernseher(ort=(0.0, 0.0, 0.0), drehung=0.0, zoll=55, an=True, name="Fernseher"):
    breite = float(zoll) * 0.0254 * 0.87
    hoehe = breite * 9 / 16
    rahmen = jon_material(f"{name}Rahmen", (0.02, 0.02, 0.022), rau=0.3)
    bild = jon_bildschirm(f"{name}Bild", an)
    korpus = jon_material(f"{name}Board", (0.16, 0.16, 0.17), rau=0.5)
    bau = JonBau(name)
    bau.quader((0.0, 0.0, 0.22), (breite + 0.4, 0.42, 0.44), korpus)
    bau.quader((0.0, 0.0, 0.47), (0.3, 0.2, 0.02), rahmen)
    bau.quader((0.0, 0.0, 0.52), (0.05, 0.05, 0.1), rahmen)
    unten = 0.56
    bau.quader((0.0, 0.0, unten + hoehe / 2), (breite + 0.02, 0.04, hoehe + 0.02), rahmen)
    bau.quader((0.0, -0.021, unten + hoehe / 2), (breite - 0.01, 0.002, hoehe - 0.01), bild)
    return _jon_wand(bau.fertig(_jon_moebel_ort(ort), drehung, fase=0.004, leuchtet=bool(an)), "moebel")


def jon_bildschirm(name="Bildschirm", an=True):
    material, baum, bsdf = _jon_knoten(name)
    bsdf.inputs["Base Color"].default_value = (0.005, 0.005, 0.006, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.08
    if an:
        koordinaten = baum.nodes.new("ShaderNodeTexCoord")
        verlauf = baum.nodes.new("ShaderNodeTexGradient")
        verlauf.gradient_type = "DIAGONAL"
        baum.links.new(koordinaten.outputs["Generated"], verlauf.inputs["Vector"])
        farbe = _jon_rampe(baum, verlauf.outputs["Fac"], ((0.0, (0.05, 0.15, 0.6)), (0.5, (0.45, 0.2, 0.7)), (1.0, (1.0, 0.5, 0.25))))
        eingang = _jon_eingang(bsdf, "Emission Color", "Emission")
        baum.links.new(farbe, eingang)
        _jon_setzen(bsdf, "Emission Strength", 2.5)
    return material


def jon_bild(ort=(0.0, 2.4, 1.5), drehung=0.0, breite=0.9, hoehe=0.65, farben=((0.9, 0.55, 0.2), (0.15, 0.25, 0.5)), rahmenfarbe=(0.08, 0.07, 0.06), name="Bild"):
    material, baum, bsdf = _jon_knoten(f"{name}Leinwand")
    koordinaten = baum.nodes.new("ShaderNodeTexCoord")
    farbe = _jon_rampe(baum, _jon_rauschen(baum, koordinaten.outputs["Generated"], 2.2, 3.0), ((0.25, farben[0]), (0.5, (0.92, 0.88, 0.8)), (0.75, farben[-1])))
    baum.links.new(farbe, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.7
    rahmen = jon_material(f"{name}Rahmen", rahmenfarbe, rau=0.4)
    bau = JonBau(name)
    b, h = float(breite), float(hoehe)
    for x, z, sb, sh in ((0.0, h / 2, b + 0.08, 0.04), (0.0, -h / 2, b + 0.08, 0.04), (-b / 2, 0.0, 0.04, h), (b / 2, 0.0, 0.04, h)):
        bau.quader((x, 0.0, z), (sb, 0.04, sh), rahmen)
    bau.quader((0.0, 0.005, 0.0), (b, 0.01, h), material)
    return _jon_wand(bau.fertig(_jon_moebel_ort(ort), drehung, fase=0.004), "bild")


def jon_kueche(ort=(0.0, 2.2, 0.0), drehung=0.0, breite=3.0, farbe=(0.92, 0.92, 0.9), platte=(0.2, 0.2, 0.21), name="Kueche"):
    front = jon_material(f"{name}Front", farbe, rau=0.35)
    arbeit = jon_material(f"{name}Arbeitsplatte", platte, rau=0.25)
    stahl = jon_metall(f"{name}Stahl", (0.8, 0.8, 0.8), 0.2)
    feld = jon_material(f"{name}Kochfeld", (0.01, 0.01, 0.012), rau=0.05)
    sockel = jon_material(f"{name}Sockel", (0.1, 0.1, 0.1), rau=0.6)
    b = float(breite)
    bau = JonBau(name)
    bau.quader((0.0, 0.0, 0.05), (b, 0.52, 0.1), sockel)
    bau.quader((0.0, 0.0, 0.48), (b, 0.58, 0.76), front)
    bau.quader((0.0, -0.01, 0.885), (b + 0.02, 0.62, 0.04), arbeit)
    anzahl = max(2, int(b / 0.6))
    for i in range(anzahl):
        x = -b / 2 + b * (i + 0.5) / anzahl
        bau.quader((x, -0.3, 0.48), (b / anzahl - 0.006, 0.02, 0.74), front)
        bau.quader((x, -0.32, 0.78), (min(0.3, b / anzahl * 0.6), 0.02, 0.015), stahl)
        bau.quader((x, 0.12, 1.85), (b / anzahl - 0.006, 0.36, 0.72), front)
    bau.quader((-b * 0.22, -0.02, 0.9), (0.55, 0.42, 0.012), stahl)
    bau.quader((b * 0.22, -0.02, 0.908), (0.58, 0.5, 0.006), feld)
    bau.zylinder((-b * 0.22, 0.17, 1.05), 0.012, 0.3, stahl, segmente=10)
    bau.quader((-b * 0.22, 0.09, 1.19), (0.02, 0.18, 0.02), stahl)
    return _jon_wand(bau.fertig(_jon_moebel_ort(ort), drehung, fase=0.004), "moebel")


JON_ROEMISCH = ("XII", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI")


def jon_uhr(durchmesser=0.6, uhrzeit=(10, 10, 32), ziffern="roemisch", stil="wand", gehaeusefarbe=(0.78, 0.6, 0.3), zifferblattfarbe=(0.95, 0.92, 0.85), zeigerfarbe=(0.04, 0.04, 0.05), ort=(0.0, 0.0, 1.6), drehung=0.0, kamera=True, umgebung=True, name="Uhr"):
    r = float(durchmesser) / 2
    stunde, minute, sekunde = (list(uhrzeit) + [0, 0, 0])[:3]
    uhr = _jon_leer(name, _jon_ort(ort), drehung)
    uhr.rotation_euler = (math.radians(90.0), 0.0, math.radians(drehung))
    gehaeuse = jon_metall(f"{name}Gehaeuse", gehaeusefarbe, 0.22)
    blatt_material, baum, bsdf = _jon_knoten(f"{name}Zifferblatt")
    koordinaten = baum.nodes.new("ShaderNodeTexCoord")
    abstand = baum.nodes.new("ShaderNodeVectorMath")
    abstand.operation = "LENGTH"
    baum.links.new(koordinaten.outputs["Object"], abstand.inputs[0])
    teilen = baum.nodes.new("ShaderNodeMath")
    teilen.operation = "DIVIDE"
    teilen.inputs[1].default_value = r
    baum.links.new(abstand.outputs["Value"], teilen.inputs[0])
    baum.links.new(_jon_rampe(baum, teilen.outputs["Value"], ((0.0, _jon_heller(zifferblattfarbe, 1.04)), (0.75, zifferblattfarbe), (1.0, _jon_heller(zifferblattfarbe, 0.82)))), bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.45
    zeiger = jon_metall(f"{name}Zeiger", zeigerfarbe, 0.3) if sum(zeigerfarbe) > 0.6 else jon_material(f"{name}Zeiger", zeigerfarbe, rau=0.5)
    rot = jon_material(f"{name}Sekunde", (0.7, 0.05, 0.04), rau=0.35)
    glas = jon_glas(f"{name}Glas", deckkraft=0.03, glanz=0.45)
    bau = JonBau(f"{name}Koerper")
    tiefe = r * 0.16
    bau.zylinder((0.0, 0.0, -tiefe / 2), r * 1.06, tiefe, gehaeuse, segmente=96)
    bau.zylinder((0.0, 0.0, 0.002), r, 0.004, blatt_material, segmente=96)
    for teil in range(60):
        winkel = math.radians(teil * 6.0)
        gross = teil % 5 == 0
        laenge = r * (0.1 if gross else 0.045)
        weite = r * (0.028 if gross else 0.009)
        mitte = r * 0.9 - laenge / 2
        bau.quader((math.sin(winkel) * mitte, math.cos(winkel) * mitte, 0.0045), (weite, laenge, 0.0015), zeiger, (0.0, 0.0, -teil * 6.0))

    def zeigerform(laenge, weite, schwanz, z, winkel, material):
        umriss = [(-weite / 2, -schwanz), (weite / 2, -schwanz), (weite * 0.38, laenge * 0.78), (0.0, laenge), (-weite * 0.38, laenge * 0.78)]
        bau.platte(umriss, z, r * 0.008, material, -winkel)

    stundenwinkel = ((stunde % 12) + minute / 60.0 + sekunde / 3600.0) * 30.0
    minutenwinkel = (minute + sekunde / 60.0) * 6.0
    zeigerform(r * 0.5, r * 0.06, r * 0.1, 0.008, stundenwinkel, zeiger)
    zeigerform(r * 0.78, r * 0.042, r * 0.12, 0.008 + r * 0.012, minutenwinkel, zeiger)
    zeigerform(r * 0.86, r * 0.012, r * 0.22, 0.008 + r * 0.026, sekunde * 6.0, rot)
    bau.zylinder((0.0, 0.0, 0.01 + r * 0.03), r * 0.035, r * 0.02, zeiger, segmente=24)
    bau.zylinder((0.0, 0.0, 0.012 + r * 0.045), r * 0.96, 0.003, glas, segmente=96)
    bau.fertig(eltern=uhr)
    ring = r * 0.08
    bpy.ops.mesh.primitive_torus_add(major_radius=r * 1.02, minor_radius=ring, major_segments=96, minor_segments=24, location=(0.0, 0.0, 0.0))
    luenette = bpy.context.active_object
    luenette.name = f"{name}Luenette"
    luenette.scale = (1.0, 1.0, 0.7)
    luenette.location = (0.0, 0.0, ring * 0.35)
    luenette.data.materials.append(gehaeuse)
    _jon_glatt(luenette)
    luenette.parent = uhr
    if str(ziffern).lower() not in ("striche", "keine", "none", ""):
        roemisch = str(ziffern).lower().startswith("r")
        for nummer in range(12):
            winkel = math.radians(nummer * 30.0)
            kurve = bpy.data.curves.new(f"{name}Ziffer{nummer}", type="FONT")
            kurve.body = JON_ROEMISCH[nummer] if roemisch else str(nummer or 12)
            kurve.align_x = "CENTER"
            kurve.align_y = "CENTER"
            kurve.size = r * (0.15 if roemisch else 0.19)
            kurve.extrude = 0.0006
            text = bpy.data.objects.new(kurve.name, kurve)
            bpy.context.collection.objects.link(text)
            text.data.materials.append(zeiger)
            text.parent = uhr
            text.location = (math.sin(winkel) * r * 0.7, math.cos(winkel) * r * 0.7, 0.005)
            if roemisch:
                text.rotation_euler = (0.0, 0.0, -winkel)
    if str(stil).lower().startswith(("wecker", "tisch")):
        fuesse = JonBau(f"{name}Fuesse")
        for seite in (-1.0, 1.0):
            fuesse.zylinder((seite * r * 0.62, -r * 1.02, -tiefe / 2), r * 0.09, tiefe * 0.8, gehaeuse, drehung=(0.0, 0.0, 0.0), segmente=20)
            fuesse.kugel((seite * r * 0.55, r * 1.1, -tiefe * 0.4), r * 0.3, gehaeuse, (1.0, 1.0, 0.85), feinheit=3)
        fuesse.zylinder((0.0, r * 1.1, -tiefe * 0.4), r * 0.035, r * 0.6, gehaeuse, drehung=(0.0, 90.0, 0.0), segmente=12)
        fuesse.fertig(eltern=uhr)
    eigene = set(_jon_flach([uhr]))
    szene = bpy.context.scene
    allein = not any(o.type in _JON_GEOMETRIE and o not in eigene for o in szene.objects) and "jon_zeit" not in szene and not szene.get("jon_studio")
    if umgebung and allein:
        rahmen = _jon_leer(f"{name}Umgebung", _jon_ort(ort), drehung)
        welt = JonBau(f"{name}Wand")
        putz = jon_putz(f"{name}Wandputz", (0.8, 0.76, 0.7), relief=0.05)
        if str(stil).lower().startswith(("wecker", "tisch")):
            welt.quader((0.0, r * 2.0, -r * 1.11 - 0.02), (r * 18, r * 10, 0.04), jon_holz(f"{name}Tisch", (0.36, 0.22, 0.11), 0.35))
            welt.quader((0.0, r * 7.0 + 0.05, r * 5.0), (r * 40, 0.1, r * 16), putz)
        else:
            welt.quader((0.0, tiefe + 0.051, 0.0), (r * 40, 0.1, r * 26), putz)
        welt.fertig(eltern=rahmen)["jon_hintergrund"] = True
        abstand = r * 9.0
        daten = bpy.data.lights.new(f"{name}Licht", type="AREA")
        daten.energy = 26.0 * abstand * abstand
        daten.size = r * 5.0
        daten.color = (1.0, 0.95, 0.88)
        lampe = bpy.data.objects.new(daten.name, daten)
        szene.collection.objects.link(lampe)
        lampe.parent = rahmen
        lampe.location = Vector((-0.45, -0.8, 0.4)).normalized() * abstand
        lampe.rotation_euler = (-lampe.location).to_track_quat("-Z", "Y").to_euler()
        welt_daten = szene.world or bpy.data.worlds.new("JonWelt")
        szene.world = welt_daten
        welt_daten.use_nodes = True
        grund = welt_daten.node_tree.nodes.get("Background")
        if grund is not None:
            grund.inputs["Color"].default_value = (0.32, 0.31, 0.3, 1.0)
            grund.inputs["Strength"].default_value = 1.0
    if kamera:
        bpy.context.view_layer.update()
        vorne = uhr.matrix_world.to_3x3() @ Vector((0.0, 0.0, 1.0))
        rechts = uhr.matrix_world.to_3x3() @ Vector((1.0, 0.0, 0.0))
        jon_kamera(richtung=vorne + rechts * 0.32 + Vector((0.0, 0.0, 0.12)), brennweite=85.0, objekte=[uhr], rand=1.12)
    return uhr
'''
