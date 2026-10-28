"""Build a stylised, static post-timeskip Luffy in Blender (front is -Y).

Run with Blender 4.2+: blender -b -t 4 --python model/build_luffy.py
Or with bpy installed: python model/build_luffy.py
Set LUFFY_RENDER=0 to skip the preview. Exports are written beside this script.
The GLB contains only the character meshes, not the camera, lights or backdrop.
"""
import math
import os
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.read_factory_settings(use_empty=True)
# Regeneration should not leave timestamped .blend backup files in the project.
bpy.context.preferences.filepaths.save_version = 0


def material(name, color, roughness=0.7):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    shader = m.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Roughness'].default_value = roughness
    return m

M = {
    'skin': material('Skin | warm', (0.73, 0.39, 0.25)),
    'skin_light': material('Skin | highlights', (0.86, 0.53, 0.36)),
    'skin_shadow': material('Skin | detail', (0.49, 0.23, 0.16)),
    'hair': material('Hair | ink', (0.012, 0.017, 0.025)),
    'hair_light': material('Hair | blue black', (0.025, 0.037, 0.052)),
    'eye': material('Eyes | ivory', (0.95, 0.91, 0.80)),
    'ink': material('Face | dark lines', (0.025, 0.015, 0.018)),
    'scar': material('Scars | muted rose', (0.54, 0.23, 0.21)),
    'red': material('Jacket | vermilion', (0.63, 0.028, 0.026)),
    'red_dark': material('Jacket | shadow', (0.34, 0.014, 0.018)),
    'red_light': material('Jacket | seams', (0.82, 0.07, 0.045)),
    'straw': material('Hat | straw', (0.75, 0.49, 0.20)),
    'straw_light': material('Hat | weave', (0.94, 0.69, 0.32)),
    'band': material('Hat | red band', (0.62, 0.035, 0.026)),
    'gold': material('Buttons | brass', (0.92, 0.58, 0.10), 0.4),
    'sash': material('Sash | golden yellow', (0.94, 0.61, 0.035)),
    'sash_dark': material('Sash | folds', (0.68, 0.36, 0.025)),
    'blue': material('Shorts | indigo', (0.035, 0.12, 0.31)),
    'blue_light': material('Shorts | seams', (0.12, 0.25, 0.46)),
    'cuff': material('Shorts | turned cuffs', (0.80, 0.82, 0.76)),
    'sole': material('Sandals | sole', (0.31, 0.16, 0.07)),
    'strap': material('Sandals | leather', (0.46, 0.24, 0.10)),
}
root = bpy.data.objects.new('Luffy', None)
bpy.context.collection.objects.link(root)


def finish(obj, mat, smooth=True):
    obj.data.materials.append(M[mat])
    if smooth:
        for p in obj.data.polygons:
            p.use_smooth = True
    obj.parent = root
    return obj


def uv(name, loc, scale, mat, segments=32, rings=20):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=loc)
    o = bpy.context.object; o.name = name; o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return finish(o, mat)


def loft(name, rings, mat, n=48):
    """Horizontal elliptical rings: (z, center x, center y, radius x, radius y)."""
    verts = []
    for z, x, y, rx, ry in rings:
        for i in range(n):
            a = 2 * math.pi * i / n
            verts.append((x + rx * math.cos(a), y + ry * math.sin(a), z))
    faces = []
    faces.append(tuple(reversed(range(n))))
    for j in range(len(rings) - 1):
        for i in range(n):
            k = (i + 1) % n
            faces.append((j*n+i, j*n+k, (j+1)*n+k, (j+1)*n+i))
    faces.append(tuple((len(rings)-1)*n+i for i in range(n)))
    mesh = bpy.data.meshes.new(name); mesh.from_pydata(verts, [], faces); mesh.update()
    o = bpy.data.objects.new(name, mesh); bpy.context.collection.objects.link(o)
    return finish(o, mat)


def tube(name, points, radius, mat, resolution=3):
    curve = bpy.data.curves.new(name, 'CURVE'); curve.dimensions = '3D'
    curve.resolution_u = 12; curve.bevel_depth = radius; curve.bevel_resolution = resolution
    spline = curve.splines.new('BEZIER'); spline.bezier_points.add(len(points)-1)
    for p, co in zip(spline.bezier_points, points):
        p.co = co; p.handle_left_type = 'AUTO'; p.handle_right_type = 'AUTO'
    o = bpy.data.objects.new(name, curve); bpy.context.collection.objects.link(o)
    bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.convert(target='MESH'); o.select_set(False)
    return finish(o, mat)


def limb(name, a, b, r1, r2, mat):
    a, b = Vector(a), Vector(b); d = b-a
    bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=r1, radius2=r2, depth=d.length, location=(a+b)/2)
    o = bpy.context.object; o.name = name
    o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = Vector((0,0,1)).rotation_difference(d.normalized())
    bevel = o.modifiers.new('Soft edges', 'BEVEL'); bevel.width = min(r1,r2)*0.16; bevel.segments = 3
    bpy.context.view_layer.objects.active = o; bpy.ops.object.modifier_apply(modifier=bevel.name)
    return finish(o, mat)


def patch(name, verts, mat, thickness=0.006):
    mesh = bpy.data.meshes.new(name); mesh.from_pydata(verts, [], [tuple(range(len(verts)))]); mesh.update()
    o = bpy.data.objects.new(name, mesh); bpy.context.collection.objects.link(o)
    solid = o.modifiers.new('Fabric thickness', 'SOLIDIFY'); solid.thickness = thickness
    bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.modifier_apply(modifier=solid.name); o.select_set(False)
    return finish(o, mat, False)

# LEGS, FEET AND SANDALS: a relaxed, slightly wider stance.
for s, label in [(-1, 'L'), (1, 'R')]:
    x = s*0.125
    limb('Shin '+label, (x+s*.018,0,0.115), (x,0,0.49), .047, .059, 'skin')
    uv('Knee '+label, (x,-.008,.48), (.061,.064,.07), 'skin')
    # Ellipsoids give the sole and toes a rounded rather than blocky silhouette.
    uv('Sandal sole '+label, (x+s*.018,-.045,.045), (.075,.145,.025), 'sole')
    uv('Foot '+label, (x+s*.018,-.055,.075), (.065,.124,.039), 'skin')
    for i in range(4):
        tx = x+s*.018 + (i-1.5)*.027
        uv('Toe %s %s'%(label,i), (tx,-.155,.071), (.015,.026,.016), 'skin', 16, 10)
    tube('Sandal thong '+label, [(x+s*.018,-.15,.092),(x+s*.018,-.10,.11),(x+s*.018,-.045,.112)], .008, 'strap')
    tube('Sandal straps '+label, [(x-.052,-.015,.077),(x+s*.018,-.085,.112),(x+.052,-.015,.077)], .010, 'strap')

# SHORTS, individually flared legs and folded hems.
loft('Shorts hips', [(0.65,0,0,.17,.105),(.78,0,0,.175,.105),(.82,0,0,.15,.10)], 'blue')
for s,label in [(-1,'L'),(1,'R')]:
    x=s*.11
    loft('Shorts leg '+label,[(.465,x,0,.102,.108),(.49,x,0,.108,.11),(.68,x*.95,0,.102,.105),(.72,x*.9,0,.09,.10)], 'blue', 32)
    loft('Turned cuff '+label,[(.462,x,0,.105,.111),(.47,x,0,.11,.115),(.505,x,0,.109,.114),(.512,x,0,.105,.11)], 'cuff', 32)
    tube('Shorts seam '+label, [(s*.19,-.071,.73),(s*.20,-.085,.61),(s*.20,-.075,.52)], .0025,'blue_light')

# TORSO: tapered anatomy rather than a stack of balls. Jacket back stays behind it.
loft('Jacket back',[(.78,0,.025,.17,.10),(.9,0,.035,.185,.105),(1.10,0,.035,.23,.115),(1.20,0,.035,.20,.10),(1.24,0,.04,.12,.07)], 'red_dark')
loft('Torso',[(.79,0,0,.132,.087),(.87,0,0,.14,.09),(1.00,0,0,.155,.10),(1.13,0,0,.197,.105),(1.19,0,0,.185,.10),(1.23,0,0,.11,.075)], 'skin')
limb('Neck',(0,0,1.18),(0,0,1.32),.065,.066,'skin')
# Subtle chest anatomy and the iconic X scar sit on top of the visible chest.
for s in (-1,1):
    tube('Clavicle',[(s*.015,-.091,1.19),(s*.075,-.102,1.18),(s*.14,-.084,1.19)],.003,'skin_shadow')
    tube('Chest contour',[(s*.02,-.105,1.095),(s*.075,-.106,1.083),(s*.13,-.085,1.10)],.0025,'skin_shadow')
tube('Chest scar A',[(-.070,-.108,1.14),(0,-.113,1.065),(.063,-.105,1.00)],.006,'scar')
tube('Chest scar B',[(.070,-.108,1.14),(0,-.114,1.065),(-.063,-.105,1.00)],.006,'scar')
# Sculpted open jacket panels, with a clear V-shaped opening and lapels.
for s,label in [(-1,'L'),(1,'R')]:
    panel=[(s*.20,-.025,1.22),(s*.145,-.093,1.20),(s*.085,-.111,1.10),(s*.075,-.103,.93),(s*.115,-.085,.80),(s*.185,-.055,.79),(s*.20,-.02,.96),(s*.235,-.01,1.13)]
    patch('Jacket front '+label,panel,'red')
    tube('Jacket opening piping '+label,[(s*.145,-.098,1.20),(s*.088,-.116,1.10),(s*.078,-.108,.94),(s*.116,-.090,.80)],.006,'red_light')
    patch('Collar '+label,[(s*.20,-.03,1.23),(s*.14,-.095,1.23),(s*.065,-.11,1.16),(s*.105,-.12,1.13),(s*.16,-.105,1.17)],'red')
    for z in (.84,.91,.98,1.05):
        uv('Brass button '+label,(s*.129,-.106,z),(.010,.006,.010),'gold',16,10)
    # Arms angle outward slightly; sleeves end at the elbow.
    limb('Upper sleeve '+label,(s*.205,.005,1.17),(s*.27,.005,.96),.083,.071,'red')
    uv('Shoulder '+label,(s*.205,.005,1.155),(.085,.09,.085),'red')
    limb('Sleeve cuff '+label,(s*.27,.005,.965),(s*.279,.005,.92),.076,.078,'red_dark')
    limb('Forearm '+label,(s*.28,.005,.93),(s*.315,-.012,.73),.052,.043,'skin')
    uv('Hand '+label,(s*.32,-.014,.70),(.056,.046,.066),'skin')
    uv('Thumb '+label,(s*.275,-.050,.70),(.024,.026,.038),'skin_light',20,12)
    for j in range(3):
        tube('Knuckle '+label,[(s*(.29+j*.018),-.055,.704),(s*(.29+j*.018),-.056,.682)],.002,'skin_shadow')

# Wide wrapped sash with a knot and two hanging fabric ends.
loft('Sash',[(.76,0,0,.168,.107),(.78,0,0,.18,.115),(.84,0,0,.18,.115),(.86,0,0,.17,.11)], 'sash')
for z in (.785,.825,.847):
    tube('Sash fold', [(-.16,-.055,z),(-.09,-.106,z+.006),(0,-.118,z),(.09,-.106,z-.004),(.16,-.05,z)], .0025,'sash_dark')
uv('Sash knot',(.16,-.095,.80),(.055,.04,.046),'sash')
patch('Sash hanging end',[(.16,-.105,.79),(.22,-.09,.77),(.25,-.085,.55),(.19,-.09,.57)],'sash')
patch('Sash second end',[(.17,-.08,.78),(.22,-.065,.77),(.19,-.055,.63),(.15,-.065,.61)],'sash_dark')

# HEAD: exposed face, expressive linework, eyes and the small scar below his left eye.
uv('Head',(0,0,1.42),(.175,.145,.195),'skin_light',48,32)
for s,label in [(-1,'L'),(1,'R')]:
    uv('Ear '+label,(s*.174,0,1.42),(.035,.026,.052),'skin',24,16)
    tube('Ear detail '+label,[(s*.18,-.025,1.44),(s*.19,-.026,1.425),(s*.18,-.027,1.405)],.003,'skin_shadow')
    uv('Eye outline '+label,(s*.067,-.132,1.465),(.048,.016,.060),'ink',32,20)
    uv('Eye white '+label,(s*.067,-.146,1.466),(.041,.010,.052),'eye',32,20)
    uv('Pupil '+label,(s*.065,-.155,1.463),(.013,.008,.021),'ink',24,16)
    uv('Eye glint '+label,(s*.061,-.162,1.474),(.004,.003,.005),'eye',16,8)
    tube('Eyebrow '+label,[(s*.027,-.139,1.536),(s*.065,-.14,1.547),(s*.104,-.123,1.535)],.005,'hair')
uv('Nose',(0,-.153,1.405),(.018,.019,.023),'skin_light',24,16)
tube('Smile',[(-.077,-.119,1.371),(-.05,-.143,1.35),(0,-.154,1.34),(.05,-.143,1.35),(.077,-.119,1.371)],.0045,'ink')
for s in (-1,1):
    uv('Smile dimple',(s*.077,-.119,1.371),(.006,.005,.006),'skin_shadow',16,8)
tube('Face scar',[(.085,-.133,1.405),(.107,-.123,1.395),(.126,-.105,1.389)],.004,'scar')
for x,z in [(.096,1.40),(.111,1.394)]:
    tube('Scar stitch',[(x-.004,-.131,z-.008),(x+.004,-.131,z+.007)],.002,'scar')

# Hair cap sits behind the face. Tapered locks frame, never cover, the eyes.
uv('Hair back',(0,.065,1.49),(.185,.137,.175),'hair',40,24)
for s in (-1,1):
    for idx,(x,y,z,dx,dz) in enumerate([(.14,.0,1.53,.085,-.08),(.16,.03,1.46,.08,-.075),(.135,.07,1.40,.06,-.07),(.12,.11,1.53,.07,.04)]):
        limb('Hair side spike', (s*x,y,z),(s*(x+dx),y-.01,z+dz),.047,.002,'hair')
# Flat tapered fringe locks lie along the forehead, above the eyebrows.
for x in (-.115,-.065,-.015,.035,.085,.13):
    tipx=x+.025
    patch('Fringe',[(x-.033,-.117,1.60),(x+.032,-.117,1.60),(tipx,-.142,1.525+abs(x)*.08)],'hair',.009)

# STRAW HAT: domed crown, narrow rolled brim, woven concentric lines.
loft('Hat brim',[(1.585,0,.012,.285,.255),(1.595,0,.012,.30,.27),(1.606,0,.012,.285,.255)],'straw',64)
loft('Hat crown',[(1.60,0,.012,.17,.155),(1.66,0,.012,.17,.155),(1.71,0,.012,.16,.145),(1.75,0,.012,.13,.12),(1.77,0,.012,.07,.065),(1.775,0,.012,.005,.005)],'straw',64)
loft('Hat red ribbon',[(1.606,0,.012,.173,.158),(1.65,0,.012,.173,.158)],'band',64)
for rx in (.20,.23,.26,.282):
    pts=[(rx*math.cos(a),.012+rx*.90*math.sin(a),1.608) for a in [i*2*math.pi/64 for i in range(65)]]
    tube('Brim weave',pts,.0015,'straw_light',2)
for z,rx,ry in [(1.66,.171,.156),(1.685,.166,.151),(1.71,.16,.145),(1.735,.146,.133)]:
    pts=[(rx*math.cos(a),.012+ry*math.sin(a),z) for a in [i*2*math.pi/64 for i in range(65)]]
    tube('Crown weave',pts,.0014,'straw_light',2)

# Studio setup. Only meshes parented to root are exported.
world=bpy.data.worlds.new('Studio'); world.use_nodes=True
world.node_tree.nodes['Background'].inputs[0].default_value=(0.16,0.20,0.25,1)
world.node_tree.nodes['Background'].inputs[1].default_value=.7
bpy.context.scene.world=world

def area(name, loc, energy, size, target):
    bpy.ops.object.light_add(type='AREA', location=loc)
    o=bpy.context.object; o.name=name; o.data.energy=energy; o.data.shape='DISK'; o.data.size=size
    o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
area('Key softbox',(-3,-4,5),450,4,(0,0,.9))
area('Fill softbox',(3,-2,2.8),250,3,(0,0,1))
area('Rim softbox',(1,3,3.5),500,3,(0,0,1))
bpy.ops.object.camera_add(location=(.45,-5.5,2.05))
cam=bpy.context.object; cam.name='Camera'; cam.rotation_euler=(Vector((0,0,.91))-cam.location).to_track_quat('-Z','Y').to_euler(); cam.data.type='ORTHO'; cam.data.ortho_scale=2.15
scene=bpy.context.scene; scene.camera=cam
scene.render.engine='CYCLES'; scene.cycles.samples=48
scene.cycles.use_denoising=True
scene.render.resolution_x=800; scene.render.resolution_y=1000; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'; scene.render.film_transparent=False
scene.render.filepath=os.path.join(HERE,'preview.png')
scene.view_settings.view_transform='AgX'
# Save after configuring the scene so opening the blend reproduces the preview.
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE,'luffy.blend'))
bpy.ops.object.select_all(action='DESELECT')
meshes=[o for o in bpy.data.objects if o.parent == root and o.type == 'MESH']
for o in meshes: o.select_set(True)
bpy.context.view_layer.objects.active=meshes[0]
bpy.ops.export_scene.gltf(filepath=os.path.join(HERE,'luffy.glb'),export_format='GLB',use_selection=True,export_apply=True)
print('Exported',len(meshes),'character meshes')
if os.environ.get('LUFFY_RENDER','1') == '1':
    scene.render.filepath=os.path.join(HERE,'preview.png')
    bpy.ops.render.render(write_still=True)
