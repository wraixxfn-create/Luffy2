"""
Genera un modello 3D stilizzato di Monkey D. Luffy (dopo il timeskip) con Blender.

Il modello e' costruito da primitive (sfere, cilindri, coni, tori, box) con
modificatori di bevel e boolean, in scala reale (metri). Asse Z verso l'alto,
il personaggio guarda verso -Y.

Uso (con il modulo Python `bpy` installato):
    python build_luffy.py

Produce nella stessa cartella:
    luffy.blend   - scena Blender sorgente
    luffy.glb     - export glTF 2.0 (apribile in qualsiasi viewer 3D)
    preview.png   - render di anteprima
"""

import math
import os

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_BLEND = os.path.join(HERE, "luffy.blend")
OUT_GLB = os.path.join(HERE, "luffy.glb")
OUT_PREVIEW = os.path.join(HERE, "preview.png")
RENDER_PREVIEW = os.environ.get("LUFFY_RENDER", "1") == "1"

# ---------------------------------------------------------------- scena vuota
bpy.ops.wm.read_factory_settings(use_empty=True)


# ---------------------------------------------------------------- materiali
def make_material(name, color, roughness=0.55):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


M = {
    "skin":    make_material("Skin",     (0.93, 0.72, 0.55)),
    "hair":    make_material("Hair",     (0.03, 0.03, 0.04), 0.4),
    "white":   make_material("EyeWhite", (0.97, 0.97, 0.97), 0.2),
    "black":   make_material("Black",    (0.01, 0.01, 0.01), 0.3),
    "scar":    make_material("Scar",     (0.78, 0.45, 0.45), 0.7),
    "red":     make_material("Jacket",   (0.78, 0.07, 0.07), 0.6),
    "redband": make_material("HatBand",  (0.80, 0.08, 0.08), 0.5),
    "straw":   make_material("Straw",    (0.86, 0.68, 0.33), 0.9),
    "button":  make_material("Button",   (0.95, 0.80, 0.25), 0.25),
    "yellow":  make_material("Sash",     (0.98, 0.82, 0.12), 0.7),
    "blue":    make_material("Shorts",   (0.12, 0.25, 0.72), 0.75),
    "fur":     make_material("Fur",      (0.96, 0.96, 0.98), 1.0),
    "sandal":  make_material("Sandal",   (0.55, 0.38, 0.20), 0.85),
}

ROOT = bpy.data.objects.new("Luffy", None)
bpy.context.collection.objects.link(ROOT)


# ---------------------------------------------------------------- helper
def _finish(obj, mat_key, smooth=True, bevel=0.0):
    obj.data.materials.append(M[mat_key])
    if smooth:
        for p in obj.data.polygons:
            p.use_smooth = True
    if bevel > 0:
        bpy.context.view_layer.objects.active = obj
        mod = obj.modifiers.new("Bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        bpy.ops.object.modifier_apply(modifier=mod.name)
    obj.parent = ROOT
    return obj


def sphere(name, loc, scale, mat_key, segs=24, rings=16):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segs, ring_count=rings, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(scale=True)
    return _finish(obj, mat_key)


def cylinder(name, loc, radius, depth, mat_key, rot=(0, 0, 0), verts=24,
             radius2=None, bevel=0.0, scale=(1, 1, 1)):
    if radius2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius, depth=depth,
                                            location=loc, rotation=rot)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=radius, radius2=radius2,
                                        depth=depth, location=loc, rotation=rot)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(scale=True)
    return _finish(obj, mat_key, True, bevel)


def box(name, loc, size, mat_key, rot=(0, 0, 0), bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = size
    bpy.ops.object.transform_apply(scale=True)
    return _finish(obj, mat_key, False, bevel)


def torus(name, loc, major, minor, mat_key, rot=(0, 0, 0), scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor,
                                     major_segments=40, minor_segments=12,
                                     location=loc, rotation=rot)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(scale=True)
    return _finish(obj, mat_key)


def boolean_cut(target, loc, size):
    """Taglia un box dal target (apertura frontale della giacca)."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    cutter = bpy.context.active_object
    cutter.scale = size
    bpy.ops.object.transform_apply(scale=True)
    bpy.context.view_layer.objects.active = target
    mod = target.modifiers.new("Opening", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


def point_along(obj, direction):
    """Orienta l'asse Z locale di obj lungo `direction`."""
    d = Vector(direction).normalized()
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d)


# ================================================================ TESTA
sphere("Head", (0, 0, 1.36), (0.20, 0.19, 0.215), "skin", segs=32, rings=24)
sphere("Nose", (0, -0.195, 1.33), (0.022, 0.02, 0.02), "skin", segs=12, rings=8)
for side, x in (("L", -0.205), ("R", 0.205)):
    sphere(f"Ear{side}", (x, 0.0, 1.36), (0.03, 0.02, 0.045), "skin", segs=12, rings=8)

# Occhi grandi e tondi (bianco + pupilla)
for side, x in (("L", -0.075), ("R", 0.075)):
    sphere(f"EyeWhite{side}", (x, -0.165, 1.40), (0.052, 0.03, 0.058), "white", segs=20, rings=12)
    sphere(f"Pupil{side}", (x, -0.19, 1.395), (0.022, 0.015, 0.024), "black", segs=12, rings=8)

# Sorriso largo
box("SmileL", (-0.055, -0.19, 1.29), (0.06, 0.012, 0.012), "black", rot=(0, 0, -0.45))
box("SmileR", (0.055, -0.19, 1.29), (0.06, 0.012, 0.012), "black", rot=(0, 0, 0.45))

# Cicatrice sotto l'occhio (lato destro dell'immagine)
box("FaceScar", (0.115, -0.175, 1.37), (0.012, 0.01, 0.06), "scar", rot=(0.15, 0.0, -0.5))

# Capelli neri: calotta + ciuffi appuntiti
sphere("HairCap", (0, 0.01, 1.42), (0.215, 0.205, 0.17), "hair", segs=32, rings=20)
HAIR_TUFTS = [
    # (posizione base, direzione della punta)
    ((-0.16, 0.02, 1.50), (-0.6, 0.0, 0.5)),
    ((0.16, 0.02, 1.50), (0.6, 0.0, 0.5)),
    ((-0.12, -0.10, 1.52), (-0.4, -0.5, 0.6)),
    ((0.12, -0.10, 1.52), (0.4, -0.5, 0.6)),
    ((-0.20, 0.10, 1.40), (-0.9, 0.3, 0.1)),
    ((0.20, 0.10, 1.40), (0.9, 0.3, 0.1)),
    ((0.0, 0.18, 1.48), (0.0, 0.9, 0.4)),
    ((0.0, 0.04, 1.58), (0.0, 0.1, 1.0)),
]
for i, (base, direction) in enumerate(HAIR_TUFTS):
    d = Vector(direction).normalized()
    tuft = cylinder(f"HairTuft{i}", base, radius=0.055, depth=0.16, mat_key="hair",
                    verts=6, radius2=0.0)
    point_along(tuft, d)
    tuft.location = Vector(base) + d * 0.06

# ================================================================ CAPPELLO DI PAGLIA
torus("StrawBrimEdge", (0, 0, 1.56), 0.40, 0.02, "straw", scale=(1, 1, 0.5))
cylinder("StrawBrim", (0, 0, 1.555), radius=0.40, depth=0.03, mat_key="straw",
         verts=48, bevel=0.008)
cylinder("StrawCrown", (0, 0, 1.64), radius=0.20, depth=0.16, mat_key="straw",
         verts=40, radius2=0.205, bevel=0.012)
cylinder("HatBand", (0, 0, 1.59), radius=0.2175, depth=0.045, mat_key="redband", verts=40)

# ================================================================ TORSO
sphere("Torso", (0, 0, 1.00), (0.175, 0.115, 0.27), "skin", segs=32, rings=20)

# Addominali accennati (tre file da due)
for row, z in enumerate((0.99, 0.93, 0.87)):
    for side, x in (("L", -0.045), ("R", 0.045)):
        sphere(f"Ab{row}{side}", (x, -0.115, z), (0.035, 0.012, 0.022), "skin", segs=12, rings=8)

# Cicatrice a X sul petto: due barrette inclinate di +/-40 gradi nel piano XZ
for side, angle in (("A", 0.7), ("B", -0.7)):
    box(f"ChestScar{side}", (0, -0.135, 1.06), (0.12, 0.008, 0.014), "scar",
        rot=(0, angle, 0))

# Giacca rossa: guscio attorno al torso con apertura frontale
jacket = sphere("Jacket", (0, 0, 1.00), (0.20, 0.135, 0.29), "red", segs=32, rings=20)
boolean_cut(jacket, (0, -0.16, 1.02), (0.11, 0.12, 0.42))

# Bottoni dorati sul lato sinistro della giacca
for z in (1.16, 1.06, 0.96, 0.86):
    sphere(f"Button{z:.2f}", (-0.085, -0.125, z), (0.018, 0.018, 0.018), "button",
           segs=12, rings=8)

# Maniche rosse larghe
for side, x in (("L", -0.23), ("R", 0.23)):
    # manica affusolata: piu' stretta in spalla, larga al polso (cono)
    cylinder(f"Sleeve{side}", (x, 0, 0.98), radius=0.055, depth=0.34, mat_key="red",
             verts=20, radius2=0.068)
    cylinder(f"SleeveCuff{side}", (x, 0, 0.78), radius=0.068, depth=0.08, mat_key="red",
             verts=20, radius2=0.085)
    # avambraccio nudo e pugno
    cylinder(f"Forearm{side}", (x, 0, 0.62), radius=0.04, depth=0.24, mat_key="skin", verts=16)
    sphere(f"Fist{side}", (x, 0, 0.47), (0.06, 0.055, 0.065), "skin", segs=16, rings=12)

# ================================================================ FASCIA GIALLA
torus("Sash", (0, 0, 0.88), 0.165, 0.045, "yellow", scale=(1.0, 0.75, 1.0))
box("SashTail", (0.12, 0.11, 0.70), (0.05, 0.02, 0.24), "yellow", rot=(0.0, 0.25, 0.0), bevel=0.005)

# ================================================================ PANTALONCINI BLU
cylinder("ShortsWaist", (0, 0, 0.84), radius=0.15, depth=0.12, mat_key="blue",
         verts=32, scale=(1.0, 0.75, 1.0))
for side, x in (("L", -0.09), ("R", 0.09)):
    cylinder(f"ShortLeg{side}", (x, 0, 0.68), radius=0.095, depth=0.30, mat_key="blue", verts=24)
    torus(f"Fur{side}", (x, 0, 0.53), 0.095, 0.03, "fur", scale=(1, 1, 1))

# ================================================================ GAMBE E PIEDI
for side, x in (("L", -0.09), ("R", 0.09)):
    cylinder(f"Leg{side}", (x, 0, 0.30), radius=0.06, depth=0.50, mat_key="skin", verts=20)
    sphere(f"Foot{side}", (x, -0.025, 0.05), (0.06, 0.11, 0.04), "skin", segs=16, rings=10)
    box(f"Sole{side}", (x, -0.02, 0.012), (0.11, 0.22, 0.024), "sandal", bevel=0.006)
    # cinghie del sandalo
    box(f"StrapA{side}", (x, -0.035, 0.05), (0.095, 0.012, 0.012), "sandal", rot=(0, 0, 0.0))
    box(f"StrapB{side}", (x, -0.06, 0.065), (0.012, 0.09, 0.012), "sandal", rot=(0, 0, 0.0))

# ================================================================ SISTEMAZIONE
# Scena: sfondo bianco, luci, camera frontale
bpy.ops.object.light_add(type="SUN", location=(2, -3, 4))
sun = bpy.context.active_object
sun.data.energy = 3.0
sun.rotation_euler = (math.radians(45), 0, math.radians(30))

bpy.ops.object.camera_add(location=(0, -4.6, 0.9), rotation=(math.radians(90), 0, 0))
cam = bpy.context.active_object
bpy.context.scene.camera = cam

world = bpy.data.worlds.new("World")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.95, 0.95, 0.97, 1.0)
bpy.context.scene.world = world

# Radice comune: tutto il personaggio e' figlio di ROOT (es. per animarlo)
bpy.context.view_layer.update()

# Export
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)

mesh_objs = [o for o in bpy.data.objects if o.type == "MESH"]
bpy.ops.object.select_all(action="DESELECT")
for o in mesh_objs:
    o.select_set(True)
bpy.context.view_layer.objects.active = mesh_objs[0]
bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format="GLB", use_selection=True,
                          export_apply=True)
print(f"[luffy] {len(mesh_objs)} mesh esportate -> {OUT_GLB}")

# Render di anteprima
if RENDER_PREVIEW:
    scene = bpy.context.scene
    # Cycles su CPU: non richiede GPU / OpenGL, quindi funziona anche headless
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 64
    scene.render.resolution_x = 600
    scene.render.resolution_y = 900
    scene.render.filepath = OUT_PREVIEW
    scene.render.image_settings.file_format = "PNG"
    try:
        bpy.ops.render.render(write_still=True)
        print(f"[luffy] anteprima -> {OUT_PREVIEW}")
    except Exception as exc:  # il render puo' fallire senza GPU/display
        print(f"[luffy] render non disponibile: {exc}")
