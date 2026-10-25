from __future__ import annotations

BAUSTEINE = r'''
import math
import random

from mathutils import Vector

_JON_GEOMETRIE = ("MESH", "CURVE", "SURFACE", "META", "FONT", "VOLUME", "POINTCLOUD", "CURVES")


def _jon_eingang(knoten, *namen):
    for name in namen:
        if name in knoten.inputs:
            return knoten.inputs[name]
    return None


def _jon_mischen(baum, art="MULTIPLY"):
    try:
        knoten = baum.nodes.new("ShaderNodeMix")
        knoten.data_type = "RGBA"
        knoten.blend_type = art
        return knoten.inputs[0], knoten.inputs[6], knoten.inputs[7], knoten.outputs[2]
    except Exception:
        knoten = baum.nodes.new("ShaderNodeMixRGB")
        knoten.blend_type = art
        return knoten.inputs[0], knoten.inputs[1], knoten.inputs[2], knoten.outputs[0]


def _jon_farbe(farbe, alpha=1.0):
    return (float(farbe[0]), float(farbe[1]), float(farbe[2]), alpha)


def _jon_glatt(objekt):
    if objekt.type == "MESH":
        for flaeche in objekt.data.polygons:
            flaeche.use_smooth = True


def _jon_durchsichtig(material, gemischt=True):
    if hasattr(material, "use_transparent_shadow"):
        material.use_transparent_shadow = True
    if hasattr(material, "surface_render_method"):
        try:
            material.surface_render_method = "BLENDED" if gemischt else "DITHERED"
        except Exception:
            pass
    if hasattr(material, "blend_method"):
        try:
            material.blend_method = "BLEND" if gemischt else "HASHED"
        except Exception:
            pass


def _jon_neu(objekt, name, leuchtet=False):
    objekt.name = name
    if leuchtet:
        objekt["jon_selbstleuchtend"] = True
    return objekt


def jon_material(name, farbe=(0.8, 0.8, 0.8), metall=0.0, rau=0.5, leuchten=0.0, leuchtfarbe=None, glanz=None):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = _jon_farbe(farbe)
    bsdf.inputs["Metallic"].default_value = metall
    bsdf.inputs["Roughness"].default_value = rau
    if glanz is not None:
        eingang = _jon_eingang(bsdf, "Specular IOR Level", "Specular")
        if eingang is not None:
            eingang.default_value = glanz
    if leuchten > 0:
        _jon_eingang(bsdf, "Emission Color", "Emission").default_value = _jon_farbe(leuchtfarbe or farbe)
        _jon_eingang(bsdf, "Emission Strength").default_value = leuchten
    return material


def jon_leuchtmaterial(name, farbe=(1.0, 0.8, 0.5), staerke=5.0):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    baum = material.node_tree
    baum.nodes.clear()
    ausgabe = baum.nodes.new("ShaderNodeOutputMaterial")
    licht = baum.nodes.new("ShaderNodeEmission")
    licht.inputs["Color"].default_value = _jon_farbe(farbe)
    licht.inputs["Strength"].default_value = staerke
    baum.links.new(licht.outputs["Emission"], ausgabe.inputs["Surface"])
    return material


def jon_sternenhimmel(dichte=1.0, helligkeit=1.0, grund=(0.0, 0.0, 0.003)):
    szene = bpy.context.scene
    welt = szene.world or bpy.data.worlds.new("JonWelt")
    szene.world = welt
    szene["jon_weltraum"] = True
    welt.use_nodes = True
    baum = welt.node_tree
    baum.nodes.clear()
    ausgabe = baum.nodes.new("ShaderNodeOutputWorld")
    hintergrund = baum.nodes.new("ShaderNodeBackground")
    hintergrund.inputs["Color"].default_value = _jon_farbe(grund)
    hintergrund.inputs["Strength"].default_value = 1.0
    koordinaten = baum.nodes.new("ShaderNodeTexCoord")
    summe = hintergrund.outputs["Background"]
    for skala, schwelle, staerke in ((260.0 * dichte, 0.09, 6.0), (90.0 * dichte, 0.035, 14.0)):
        zellen = baum.nodes.new("ShaderNodeTexVoronoi")
        zellen.inputs["Scale"].default_value = skala
        rampe = baum.nodes.new("ShaderNodeValToRGB")
        rampe.color_ramp.elements[0].position = 0.0
        rampe.color_ramp.elements[0].color = (1.0, 1.0, 1.0, 1.0)
        rampe.color_ramp.elements[1].position = schwelle
        rampe.color_ramp.elements[1].color = (0.0, 0.0, 0.0, 1.0)
        funkeln = baum.nodes.new("ShaderNodeTexNoise")
        funkeln.inputs["Scale"].default_value = skala * 0.07
        anteil, a, b, ergebnis = _jon_mischen(baum, "MULTIPLY")
        anteil.default_value = 1.0
        sterne = baum.nodes.new("ShaderNodeBackground")
        sterne.inputs["Strength"].default_value = staerke * helligkeit
        plus = baum.nodes.new("ShaderNodeAddShader")
        baum.links.new(koordinaten.outputs["Generated"], zellen.inputs["Vector"])
        baum.links.new(zellen.outputs["Distance"], rampe.inputs["Fac"])
        baum.links.new(rampe.outputs["Color"], a)
        baum.links.new(funkeln.outputs["Color"], b)
        baum.links.new(koordinaten.outputs["Generated"], funkeln.inputs["Vector"])
        baum.links.new(ergebnis, sterne.inputs["Color"])
        baum.links.new(summe, plus.inputs[0])
        baum.links.new(sterne.outputs["Background"], plus.inputs[1])
        summe = plus.outputs["Shader"]
    baum.links.new(summe, ausgabe.inputs["Surface"])
    return welt


def _jon_scheibenmaterial(name, farbe, leuchten, innen, aussen, wirbel=True):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    baum = material.node_tree
    baum.nodes.clear()
    ausgabe = baum.nodes.new("ShaderNodeOutputMaterial")
    licht = baum.nodes.new("ShaderNodeEmission")
    durch = baum.nodes.new("ShaderNodeBsdfTransparent")
    shader = baum.nodes.new("ShaderNodeMixShader")
    koordinaten = baum.nodes.new("ShaderNodeTexCoord")
    teile = baum.nodes.new("ShaderNodeSeparateXYZ")
    abstand = baum.nodes.new("ShaderNodeVectorMath")
    abstand.operation = "LENGTH"
    winkel = baum.nodes.new("ShaderNodeMath")
    winkel.operation = "ARCTAN2"
    bereich = baum.nodes.new("ShaderNodeMapRange")
    bereich.inputs["From Min"].default_value = innen
    bereich.inputs["From Max"].default_value = aussen
    rampe = baum.nodes.new("ShaderNodeValToRGB")
    stufen = rampe.color_ramp.elements
    stufen[0].position = 0.0
    stufen[0].color = (1.0, 0.97, 0.9, 1.0)
    stufen[1].position = 1.0
    stufen[1].color = (0.0, 0.0, 0.0, 1.0)
    mitte = stufen.new(0.18)
    mitte.color = _jon_farbe((min(1.0, farbe[0] * 1.2), min(1.0, farbe[1] * 1.2), min(1.0, farbe[2] * 1.2)))
    rot = stufen.new(0.55)
    rot.color = _jon_farbe((farbe[0] * 0.55, farbe[1] * 0.18, farbe[2] * 0.08))
    rand = baum.nodes.new("ShaderNodeMapRange")
    rand.interpolation_type = "SMOOTHSTEP"
    rand.inputs["From Min"].default_value = 0.55
    rand.inputs["From Max"].default_value = 1.0
    baum.links.new(koordinaten.outputs["Object"], teile.inputs["Vector"])
    baum.links.new(koordinaten.outputs["Object"], abstand.inputs[0])
    baum.links.new(teile.outputs["Y"], winkel.inputs[0])
    baum.links.new(teile.outputs["X"], winkel.inputs[1])
    baum.links.new(abstand.outputs["Value"], bereich.inputs["Value"])
    baum.links.new(bereich.outputs["Result"], rampe.inputs["Fac"])
    baum.links.new(bereich.outputs["Result"], rand.inputs["Value"])
    farbe_aus = rampe.outputs["Color"]
    if wirbel:
        polar = baum.nodes.new("ShaderNodeCombineXYZ")
        ringe = baum.nodes.new("ShaderNodeMath")
        ringe.operation = "MULTIPLY"
        ringe.inputs[1].default_value = 7.0
        baum.links.new(abstand.outputs["Value"], ringe.inputs[0])
        baum.links.new(ringe.outputs["Value"], polar.inputs["X"])
        baum.links.new(winkel.outputs["Value"], polar.inputs["Y"])
        rauschen = baum.nodes.new("ShaderNodeTexNoise")
        rauschen.inputs["Scale"].default_value = 2.2
        rauschen.inputs["Detail"].default_value = 9.0
        _jon_eingang(rauschen, "Distortion").default_value = 0.6
        kontrast = baum.nodes.new("ShaderNodeValToRGB")
        kontrast.color_ramp.elements[0].position = 0.25
        kontrast.color_ramp.elements[0].color = (0.25, 0.25, 0.25, 1.0)
        kontrast.color_ramp.elements[1].position = 0.75
        kontrast.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
        baum.links.new(polar.outputs["Vector"], rauschen.inputs["Vector"])
        baum.links.new(rauschen.outputs["Fac"], kontrast.inputs["Fac"])
        anteil, a, b, ergebnis = _jon_mischen(baum, "MULTIPLY")
        anteil.default_value = 1.0
        baum.links.new(rampe.outputs["Color"], a)
        baum.links.new(kontrast.outputs["Color"], b)
        farbe_aus = ergebnis
    baum.links.new(farbe_aus, licht.inputs["Color"])
    licht.inputs["Strength"].default_value = leuchten
    baum.links.new(rand.outputs["Result"], shader.inputs["Fac"])
    baum.links.new(licht.outputs["Emission"], shader.inputs[1])
    baum.links.new(durch.outputs["BSDF"], shader.inputs[2])
    baum.links.new(shader.outputs["Shader"], ausgabe.inputs["Surface"])
    _jon_durchsichtig(material)
    return material


def _jon_ring(name, haupt, dick, ort, material, flach=1.0, kippen=0.0, leuchtet=True):
    bpy.ops.mesh.primitive_torus_add(major_radius=haupt, minor_radius=dick, major_segments=160, minor_segments=40, location=ort)
    ring = _jon_neu(bpy.context.active_object, name, leuchtet)
    ring.scale = (1.0, 1.0, flach)
    ring.rotation_euler = (math.radians(kippen), 0.0, 0.0)
    ring.data.materials.append(material)
    _jon_glatt(ring)
    return ring


def jon_schwarzes_loch(groesse=1.0, neigung=9.0, scheibenfarbe=(1.0, 0.55, 0.15), leuchten=6.0, ort=(0.0, 0.0, 0.0), linse=True, kamera=True):
    r = float(groesse)
    leuchten = max(1.0, min(float(leuchten), 7.0))
    mitte = Vector(ort)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=96, ring_count=48, location=mitte)
    horizont = _jon_neu(bpy.context.active_object, "Ereignishorizont", True)
    horizont.data.materials.append(jon_leuchtmaterial("Ereignishorizont", (0.0, 0.0, 0.0), 0.0))
    _jon_glatt(horizont)
    innen, aussen = r * 1.6, r * 6.0
    scheibe = _jon_ring("Akkretionsscheibe", (innen + aussen) / 2, (aussen - innen) / 2, mitte, _jon_scheibenmaterial("Akkretionsscheibe", scheibenfarbe, leuchten, innen, aussen), flach=0.025)
    zur_kamera = 90.0 - neigung
    teile = {"horizont": horizont, "scheibe": scheibe}
    if linse:
        bogen_material = _jon_scheibenmaterial("GelinsteScheibe", scheibenfarbe, leuchten * 0.5, r * 1.3, r * 2.2, wirbel=True)
        teile["linse"] = _jon_ring("GelinsteScheibe", r * 1.75, r * 0.45, mitte, bogen_material, flach=0.03, kippen=zur_kamera)
    photonen = jon_leuchtmaterial("Photonenring", (1.0, 0.85, 0.65), leuchten * 2.5)
    teile["photonenring"] = _jon_ring("Photonenring", r * 1.06, r * 0.025, mitte, photonen, kippen=zur_kamera)
    if kamera:
        richtung = Vector((0.0, -math.cos(math.radians(neigung)), math.sin(math.radians(neigung))))
        jon_kamera(richtung=richtung, brennweite=50.0, objekte=[horizont, scheibe] + ([teile["linse"]] if linse else []), rand=1.05)
    return teile


def jon_planet(radius=1.0, farbe=(0.25, 0.45, 0.85), ort=(0.0, 0.0, 0.0), ringe=False, atmosphaere=True, name="Planet", ringfarbe=(0.85, 0.78, 0.62)):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, segments=128, ring_count=64, location=ort)
    planet = _jon_neu(bpy.context.active_object, name)
    _jon_glatt(planet)
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    baum = material.node_tree
    bsdf = baum.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = 0.75
    rauschen = baum.nodes.new("ShaderNodeTexNoise")
    rauschen.inputs["Scale"].default_value = 3.5
    rauschen.inputs["Detail"].default_value = 12.0
    rampe = baum.nodes.new("ShaderNodeValToRGB")
    rampe.color_ramp.elements[0].position = 0.35
    rampe.color_ramp.elements[0].color = _jon_farbe((farbe[0] * 0.35, farbe[1] * 0.35, farbe[2] * 0.35))
    rampe.color_ramp.elements[1].position = 0.7
    rampe.color_ramp.elements[1].color = _jon_farbe((min(1.0, farbe[0] * 1.3), min(1.0, farbe[1] * 1.3), min(1.0, farbe[2] * 1.3)))
    relief = baum.nodes.new("ShaderNodeBump")
    relief.inputs["Strength"].default_value = 0.25
    baum.links.new(rauschen.outputs["Fac"], rampe.inputs["Fac"])
    baum.links.new(rampe.outputs["Color"], bsdf.inputs["Base Color"])
    baum.links.new(rauschen.outputs["Fac"], relief.inputs["Height"])
    baum.links.new(relief.outputs["Normal"], bsdf.inputs["Normal"])
    planet.data.materials.append(material)
    teile = {"planet": planet}
    if atmosphaere:
        bpy.ops.mesh.primitive_uv_sphere_add(radius=radius * 1.035, segments=96, ring_count=48, location=ort)
        huelle = _jon_neu(bpy.context.active_object, f"{name}Atmosphaere", True)
        _jon_glatt(huelle)
        luft = bpy.data.materials.new(f"{name}Atmosphaere")
        luft.use_nodes = True
        luftbaum = luft.node_tree
        luftbaum.nodes.clear()
        ausgabe = luftbaum.nodes.new("ShaderNodeOutputMaterial")
        schicht = luftbaum.nodes.new("ShaderNodeLayerWeight")
        schicht.inputs["Blend"].default_value = 0.35
        rampe = luftbaum.nodes.new("ShaderNodeValToRGB")
        rampe.color_ramp.elements[0].position = 0.45
        rampe.color_ramp.elements[1].position = 1.0
        licht = luftbaum.nodes.new("ShaderNodeEmission")
        licht.inputs["Color"].default_value = _jon_farbe((min(1.0, farbe[0] * 0.6 + 0.4), min(1.0, farbe[1] * 0.6 + 0.4), min(1.0, farbe[2] * 0.6 + 0.4)))
        licht.inputs["Strength"].default_value = 1.6
        durch = luftbaum.nodes.new("ShaderNodeBsdfTransparent")
        shader = luftbaum.nodes.new("ShaderNodeMixShader")
        luftbaum.links.new(schicht.outputs["Facing"], rampe.inputs["Fac"])
        luftbaum.links.new(rampe.outputs["Color"], shader.inputs["Fac"])
        luftbaum.links.new(durch.outputs["BSDF"], shader.inputs[1])
        luftbaum.links.new(licht.outputs["Emission"], shader.inputs[2])
        luftbaum.links.new(shader.outputs["Shader"], ausgabe.inputs["Surface"])
        _jon_durchsichtig(luft)
        huelle.data.materials.append(luft)
        if hasattr(huelle, "visible_shadow"):
            huelle.visible_shadow = False
        teile["atmosphaere"] = huelle
    if ringe:
        ringmaterial = bpy.data.materials.new(f"{name}Ringe")
        ringmaterial.use_nodes = True
        ringbaum = ringmaterial.node_tree
        ringbsdf = ringbaum.nodes.get("Principled BSDF")
        ringbsdf.inputs["Roughness"].default_value = 0.9
        ringkoord = ringbaum.nodes.new("ShaderNodeTexCoord")
        wellen = ringbaum.nodes.new("ShaderNodeTexWave")
        wellen.wave_type = "RINGS"
        if hasattr(wellen, "rings_direction"):
            wellen.rings_direction = "SPHERICAL"
        wellen.inputs["Scale"].default_value = 2.2
        wellen.inputs["Distortion"].default_value = 1.5
        wellen.inputs["Detail"].default_value = 6.0
        bandrampe = ringbaum.nodes.new("ShaderNodeValToRGB")
        bandrampe.color_ramp.elements[0].color = _jon_farbe((ringfarbe[0] * 0.35, ringfarbe[1] * 0.35, ringfarbe[2] * 0.35))
        bandrampe.color_ramp.elements[1].color = _jon_farbe(ringfarbe)
        dichte = ringbaum.nodes.new("ShaderNodeMapRange")
        dichte.inputs["To Min"].default_value = 0.25
        dichte.inputs["To Max"].default_value = 0.95
        ringbaum.links.new(ringkoord.outputs["Object"], wellen.inputs["Vector"])
        ringbaum.links.new(wellen.outputs["Fac"], bandrampe.inputs["Fac"])
        ringbaum.links.new(wellen.outputs["Fac"], dichte.inputs["Value"])
        ringbaum.links.new(bandrampe.outputs["Color"], ringbsdf.inputs["Base Color"])
        ringbaum.links.new(dichte.outputs["Result"], ringbsdf.inputs["Alpha"])
        _jon_durchsichtig(ringmaterial, gemischt=False)
        teile["ringe"] = _jon_ring(f"{name}Ringe", radius * 2.0, radius * 0.55, Vector(ort), ringmaterial, flach=0.004, kippen=22.0, leuchtet=False)
        for flaeche in teile["ringe"].data.polygons:
            flaeche.use_smooth = False
    return teile


def jon_sonne(radius=1.0, ort=(-9.0, -16.0, 7.0), farbe=(1.0, 0.86, 0.6), staerke=4.0, ziel=(0.0, 0.0, 0.0)):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, segments=64, ring_count=32, location=ort)
    sonne = _jon_neu(bpy.context.active_object, "Sonne", True)
    sonne["jon_hintergrund"] = True
    if hasattr(sonne, "visible_shadow"):
        sonne.visible_shadow = False
    _jon_glatt(sonne)
    sonne.data.materials.append(jon_leuchtmaterial("Sonne", farbe, 25.0))
    daten = bpy.data.lights.new("Sonnenlicht", type="SUN")
    daten.energy = staerke
    daten.color = farbe
    licht = bpy.data.objects.new("Sonnenlicht", daten)
    bpy.context.collection.objects.link(licht)
    richtung = Vector(ziel) - Vector(ort)
    licht.location = Vector(ort)
    licht.rotation_euler = richtung.to_track_quat("-Z", "Y").to_euler()
    return sonne


def jon_galaxie(arme=2, sterne=5000, radius=6.0, farbe=(0.7, 0.8, 1.0), kernfarbe=(1.0, 0.82, 0.55), ort=(0.0, 0.0, 0.0), samen=7):
    zufall = random.Random(samen)
    punkte = []
    for nummer in range(int(sterne)):
        anteil = zufall.random() ** 0.65
        winkel = anteil * 4.8 + (nummer % max(1, int(arme))) * 2.0 * math.pi / max(1, int(arme)) + zufall.gauss(0.0, 0.22)
        streu = 0.07 * radius * (1.15 - anteil * 0.6)
        weite = anteil * radius
        punkte.append((weite * math.cos(winkel) + zufall.gauss(0.0, streu), weite * math.sin(winkel) + zufall.gauss(0.0, streu), zufall.gauss(0.0, 0.035 * radius * (1.3 - anteil))))
    netz = bpy.data.meshes.new("GalaxiePunkte")
    netz.from_pydata(punkte, [], [])
    traeger = bpy.data.objects.new("Galaxie", netz)
    traeger["jon_selbstleuchtend"] = True
    bpy.context.collection.objects.link(traeger)
    traeger.location = ort
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=radius * 0.0028, location=(0.0, 0.0, 0.0))
    stern = _jon_neu(bpy.context.active_object, "GalaxieStern", True)
    stern.data.materials.append(jon_leuchtmaterial("GalaxieStern", farbe, 5.0))
    stern.parent = traeger
    traeger.instance_type = "VERTS"
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius * 0.06, segments=48, ring_count=24, location=ort)
    kern = _jon_neu(bpy.context.active_object, "Galaxiekern", True)
    kern.scale = (1.0, 1.0, 0.4)
    kern.data.materials.append(jon_leuchtmaterial("Galaxiekern", kernfarbe, 6.0))
    _jon_glatt(kern)
    return {"galaxie": traeger, "kern": kern}


def _jon_ecken(objekte):
    punkte = []
    for objekt in objekte:
        punkte.extend(objekt.matrix_world @ Vector(ecke) for ecke in objekt.bound_box)
    return punkte


def _jon_flach(dinge):
    if isinstance(dinge, dict):
        dinge = list(dinge.values())
    if not isinstance(dinge, (list, tuple, set)):
        dinge = [dinge]
    ergebnis = []
    for ding in dinge:
        if isinstance(ding, (dict, list, tuple, set)):
            ergebnis.extend(_jon_flach(ding))
        elif ding is not None and hasattr(ding, "type"):
            ergebnis.append(ding)
            ergebnis.extend(getattr(ding, "children_recursive", []))
    return ergebnis


def jon_motiv(objekte=None):
    alle = _jon_flach(objekte) if objekte else list(bpy.context.scene.objects)
    kandidaten = [o for o in alle if o.type in _JON_GEOMETRIE and not o.hide_render and not o.get("jon_hintergrund") and (o.parent is None or o.parent.instance_type == "NONE")]
    if not objekte and len(kandidaten) >= 2:
        groessen = sorted(max(o.dimensions) for o in kandidaten)
        grenze = max(groessen[(len(groessen) - 1) // 2], 1e-6) * 8.0
        kleiner = [o for o in kandidaten if max(o.dimensions) <= grenze or min(o.dimensions) > max(o.dimensions) * 0.01]
        kandidaten = kleiner or kandidaten
    return kandidaten


def _jon_sichtfeld(kamera, szene):
    breite = szene.render.resolution_x * szene.render.pixel_aspect_x
    hoehe = szene.render.resolution_y * szene.render.pixel_aspect_y
    if kamera.data.type != "PERSP":
        return None
    halb = math.tan(kamera.data.angle / 2.0)
    if breite >= hoehe:
        return halb, halb * hoehe / breite
    return halb * breite / hoehe, halb


def jon_kamera(richtung=None, brennweite=None, ziel=None, rand=1.1, objekte=None):
    szene = bpy.context.scene
    kamera = szene.camera
    if kamera is None:
        daten = bpy.data.cameras.new("JonKamera")
        kamera = bpy.data.objects.new("JonKamera", daten)
        szene.collection.objects.link(kamera)
        szene.camera = kamera
    if brennweite:
        kamera.data.lens = float(brennweite)
    bpy.context.view_layer.update()
    motiv = jon_motiv(objekte)
    if not motiv:
        return kamera
    punkte = _jon_ecken(motiv)
    kleinste = Vector((min(p.x for p in punkte), min(p.y for p in punkte), min(p.z for p in punkte)))
    groesste = Vector((max(p.x for p in punkte), max(p.y for p in punkte), max(p.z for p in punkte)))
    mitte = Vector(ziel) if ziel is not None else (kleinste + groesste) / 2.0
    if richtung is None:
        bisher = kamera.location - mitte
        frisch = kamera.location.length < 1e-6 or bisher.length < 1e-6 or abs(bisher.normalized().z) > 0.97
        richtung = Vector((0.85, -1.0, 0.55)) if frisch else bisher
    richtung = Vector(richtung).normalized()
    drehung = (-richtung).to_track_quat("-Z", "Y")
    kamera.rotation_mode = "XYZ"
    kamera.rotation_euler = drehung.to_euler()
    radius = max(max((p - mitte).length for p in punkte), 1e-3)
    feld = _jon_sichtfeld(kamera, szene)
    if feld is None:
        kamera.location = mitte + richtung * radius * 3.0
        kamera.data.ortho_scale = radius * 2.0 * rand
        return kamera
    tx, ty = feld[0] / rand, feld[1] / rand
    zurueck = drehung.to_matrix().inverted()
    lokal = [zurueck @ (p - mitte) for p in punkte]

    def passt(abstand):
        for q in lokal:
            tiefe = abstand - q.z
            if tiefe <= 1e-4 or abs(q.x) / tiefe > tx or abs(q.y) / tiefe > ty:
                return False
        return True

    unten, oben = 0.0, radius / math.sin(math.atan(min(tx, ty))) * 1.5 + radius
    for _ in range(48):
        probe = (unten + oben) / 2.0
        if passt(probe):
            oben = probe
        else:
            unten = probe
    kamera.location = mitte + richtung * oben
    kamera.data.clip_start = max(0.001, min(0.1, oben * 0.001))
    kamera.data.clip_end = max(kamera.data.clip_end, (oben + radius) * 4.0, 12000.0)
    return kamera


def jon_kamera_fest():
    bpy.context.scene["jon_kamera_fest"] = True
'''

PRUEFUNG = r'''
def _jon_leuchtet(objekt):
    if objekt.get("jon_selbstleuchtend"):
        return True
    materialien = [s.material for s in objekt.material_slots if s.material is not None]
    if not materialien:
        return False
    for material in materialien:
        if not material.use_nodes:
            return False
        leuchtend = False
        for knoten in material.node_tree.nodes:
            if knoten.type == "EMISSION" and knoten.inputs["Strength"].default_value > 0:
                leuchtend = True
            if knoten.type == "BSDF_PRINCIPLED":
                staerke = knoten.inputs.get("Emission Strength")
                if staerke is not None and staerke.default_value > 0:
                    leuchtend = True
        if not leuchtend:
            return False
    return True


def _jon_kamera_pruefen():
    from bpy_extras.object_utils import world_to_camera_view

    szene = bpy.context.scene
    bpy.context.view_layer.update()
    motiv = jon_motiv()
    if szene.camera is None:
        jon_kamera()
        return "neu"
    if any(o.get("jon_hintergrund") for o in szene.objects) and szene.camera.data.clip_end < 12000.0:
        szene.camera.data.clip_end = 12000.0
    if szene.get("jon_kamera_fest") or not motiv:
        return "fest"
    sicht = [world_to_camera_view(szene, szene.camera, p) for p in _jon_ecken(motiv)]
    if any(s.z <= 0 for s in sicht) or any(s.x < -0.03 or s.x > 1.03 or s.y < -0.03 or s.y > 1.03 for s in sicht):
        jon_kamera()
        return "ausgerichtet"
    if max(max(s.x for s in sicht) - min(s.x for s in sicht), max(s.y for s in sicht) - min(s.y for s in sicht)) < 0.35:
        jon_kamera()
        return "naeher"
    return "passt"


def _jon_licht_pruefen():
    szene = bpy.context.scene
    if [o for o in szene.objects if o.type == "LIGHT"]:
        return "vorhanden"
    unbeleuchtet = [o for o in jon_motiv() if not _jon_leuchtet(o)]
    if not unbeleuchtet:
        return "selbstleuchtend"
    daten = bpy.data.lights.new("JonSonne", type="SUN")
    daten.energy = 3.5
    daten.angle = math.radians(4.0)
    sonne = bpy.data.objects.new("JonSonne", daten)
    szene.collection.objects.link(sonne)
    sonne.rotation_euler = (math.radians(50.0), math.radians(10.0), math.radians(35.0))
    if not szene.get("jon_weltraum"):
        fuell = bpy.data.lights.new("JonFuelllicht", type="SUN")
        fuell.energy = 0.8
        aufheller = bpy.data.objects.new("JonFuelllicht", fuell)
        szene.collection.objects.link(aufheller)
        aufheller.rotation_euler = (math.radians(60.0), 0.0, math.radians(-140.0))
    return "sonne"


if "_jon_moebel_pruefen" in globals():
    print("JON_MOEBEL=%s" % _jon_moebel_pruefen())
print("JON_KAMERA=%s" % _jon_kamera_pruefen())
print("JON_LICHT=%s" % _jon_licht_pruefen())
'''

GLANZ = r'''
def _jon_glanz(szene):
    leuchtet = False
    for material in bpy.data.materials:
        if material.users and material.use_nodes:
            for knoten in material.node_tree.nodes:
                staerke = knoten.inputs.get("Strength") if knoten.type == "EMISSION" else knoten.inputs.get("Emission Strength") if knoten.type == "BSDF_PRINCIPLED" else None
                if staerke is not None and (staerke.is_linked or staerke.default_value >= 2.0):
                    leuchtet = True
    if not leuchtet:
        return "aus"
    if hasattr(szene.eevee, "use_bloom"):
        szene.eevee.use_bloom = True
    try:
        if hasattr(szene, "compositing_node_group"):
            baum = bpy.data.node_groups.new("JonGlanz", "CompositorNodeTree")
            szene.compositing_node_group = baum
            baum.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
            ausgang = baum.nodes.new("NodeGroupOutput")
            ziel = ausgang.inputs[0]
        else:
            szene.use_nodes = True
            baum = szene.node_tree
            ausgang = next((k for k in baum.nodes if k.type == "COMPOSITE"), None) or baum.nodes.new("CompositorNodeComposite")
            ziel = ausgang.inputs["Image"]
        ebenen = next((k for k in baum.nodes if k.type == "R_LAYERS"), None) or baum.nodes.new("CompositorNodeRLayers")
        glanz = baum.nodes.new("CompositorNodeGlare")
        for name, wert in (("glare_type", "FOG_GLOW"), ("quality", "HIGH"), ("threshold", 1.0), ("size", 7)):
            if hasattr(glanz, name):
                try:
                    setattr(glanz, name, wert)
                except Exception:
                    pass
        for name, wert in (("Type", "Fog Glow"), ("Quality", "High"), ("Threshold", 1.0), ("Size", 0.5), ("Strength", 0.8)):
            eingang = glanz.inputs.get(name)
            if eingang is not None:
                try:
                    eingang.default_value = wert
                except Exception:
                    pass
        baum.links.new(ebenen.outputs["Image"], glanz.inputs["Image"])
        baum.links.new(glanz.outputs["Image"], ziel)
    except Exception as fehler:
        print("JON_GLANZ_FEHLER %s" % fehler)
        return "fehler"
    return "an"
'''
