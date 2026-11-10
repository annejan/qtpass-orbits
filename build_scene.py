"""QtPass as a solar system: every class a planet, sized by its lines,
circling the sun in order of age.

blender -b --factory-startup -P build_scene.py -- [--stills 300,1100]
        [--anim --start N --end M] [--pct 25] [--samples 16] [--out frames]

The planets, orbits, labels and release shockwaves are set from
timeline.py for every frame before it renders.
"""
import math
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import system as S  # noqa: E402
import timeline as TL  # noqa: E402

FPS, FRAMES = TL.FPS, TL.FRAMES
LATO = os.path.expanduser("~/.local/share/fonts/Lato/Lato-Regular.ttf")
# The colour of a planet: the era it was born in.
ERA = [(2014, (1.0, 0.72, 0.32)), (2016, (1.0, 0.48, 0.25)), (2018, (0.95, 0.32, 0.5)),
       (2019, (0.6, 0.45, 1.0)), (2026, (0.3, 0.8, 1.0))]
LABEL_LINES = 500   # planets this big carry their name


def era(k):
    from datetime import datetime
    y = datetime.fromtimestamp(S.TIMES[S.BORN[k]]).year
    c = ERA[0][1]
    for y0, col in ERA:
        if y >= y0:
            c = col
    return c


def node(nt, kind, loc, **props):
    n = nt.nodes.new(kind)
    n.location = loc
    for k, v in props.items():
        setattr(n, k, v)
    return n


def link(ob):
    bpy.context.scene.collection.objects.link(ob)
    return ob


def glow_material(name, rgb, strength, blended=True):
    """Emission, additive over what is behind it."""
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    nt.nodes.clear()
    out = node(nt, "ShaderNodeOutputMaterial", (600, 0))
    em = node(nt, "ShaderNodeEmission", (200, 100))
    em.inputs["Color"].default_value = (*rgb, 1)
    em.inputs["Strength"].default_value = strength
    if blended:
        tr = node(nt, "ShaderNodeBsdfTransparent", (200, -100))
        add = node(nt, "ShaderNodeAddShader", (400, 0))
        nt.links.new(em.outputs[0], add.inputs[0])
        nt.links.new(tr.outputs[0], add.inputs[1])
        nt.links.new(add.outputs[0], out.inputs[0])
        m.surface_render_method = "BLENDED"
    else:
        nt.links.new(em.outputs[0], out.inputs[0])
    return m, em.inputs["Strength"]


def sphere(name, radius, mat, segments=48):
    me = bpy.data.meshes.new(name)
    import bmesh
    bm = bmesh.new()
    bm.loops.layers.uv.new("UVMap")
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=segments // 2,
                              radius=radius, calc_uvs=True)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(mat)
    return link(bpy.data.objects.new(name, me))


def ring_mesh(name, k, width, mat, n=256):
    """A flat band along body k's orbit (radius 1, scaled per frame), tilted
    as the orbit is. width is relative to the radius."""
    verts, faces = [], []
    for i in range(n):
        a = 2 * math.pi * i / n
        z = math.sin(a - S.PHASE[k]) * S.TILT[k] if k else 0.0
        for r in (1 - width / 2, 1 + width / 2):
            verts.append((r * math.cos(a), r * math.sin(a), z))
    for i in range(n):
        j = (i + 1) % n
        faces.append((2 * i, 2 * i + 1, 2 * j + 1, 2 * j))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.materials.append(mat)
    ob = link(bpy.data.objects.new(name, me))
    ob.visible_shadow = False
    return ob


# ---------------------------------------------------------------- the sun

class Sun:
    def __init__(self):
        m, self.core = glow_material("Sun", (1.0, 0.86, 0.6), 18.0, blended=False)
        self.ob = sphere("Sun", 1.0, m, 64)
        self.ob.visible_shadow = False
        # no corona shell: blended over the inner planets it washed them
        # out; the glow comes from the bloom in finish.sh
        lamp = bpy.data.lights.new("Sunlight", "POINT")
        lamp.energy = 6000
        lamp.color = (1.0, 0.9, 0.75)
        lamp.shadow_soft_size = 1.0
        self.lamp = lamp
        link(bpy.data.objects.new("Sunlight", lamp))

    def update(self, frame, flare):
        self.core.default_value = 18.0 + 30.0 * flare


# ---------------------------------------------------------------- planets

def band_image(k):
    """The planet's bands: its own lines, pole to pole, long lines bright,
    short and blank ones dark, stretched to the planet's own range."""
    p = S.PROFILES.get(k) or [0.5] * 8
    lo, hi = min(p), max(p)
    v = [(x - lo) / (hi - lo) if hi > lo else 0.5 for x in p]
    img = bpy.data.images.new("Bands " + k, 4, len(v), float_buffer=True)
    px = np.repeat(np.array(v, dtype=np.float32)[::-1], 4)  # row 0 is the south pole
    rgba = np.ones((len(v) * 4, 4), dtype=np.float32)
    rgba[:, 0] = rgba[:, 1] = rgba[:, 2] = px
    img.colorspace_settings.name = "Non-Color"  # before the pixels: it reloads the buffer
    img.pixels.foreach_set(rgba.ravel())
    img.update()
    img.pack()
    return img


def planet_material(k):
    """A gas giant banded by its own source code, swirled by noise, with a
    rim of its era's colour that flares while commits land on it."""
    rgb = era(k)
    m = bpy.data.materials.new("Planet " + k)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.55
    b.inputs["Specular IOR Level"].default_value = 0.25
    b.inputs["Emission Color"].default_value = (*rgb, 1)
    b.inputs["Emission Strength"].default_value = 0.03
    out = nt.nodes["Material Output"]
    seed = (sum(map(ord, k)) % 97) * 0.37
    # the bands: latitude, swirled
    tc = node(nt, "ShaderNodeTexCoord", (-1400, 0))
    sep = node(nt, "ShaderNodeSeparateXYZ", (-1200, 100))
    nt.links.new(tc.outputs["UV"], sep.inputs[0])
    swirl = node(nt, "ShaderNodeTexNoise", (-1200, -150))
    swirl.inputs["Scale"].default_value = 2.2
    swirl.inputs["Detail"].default_value = 6.0
    swirl.inputs["Distortion"].default_value = 1.5
    swirl.noise_dimensions = "4D"
    swirl.inputs["W"].default_value = seed
    nt.links.new(tc.outputs["Object"], swirl.inputs["Vector"])
    off = node(nt, "ShaderNodeMath", (-1000, -150), operation="MULTIPLY_ADD")
    off.inputs[1].default_value = 0.07
    off.inputs[2].default_value = -0.035
    nt.links.new(swirl.outputs["Fac"], off.inputs[0])
    lat = node(nt, "ShaderNodeMath", (-850, 50), operation="ADD")
    nt.links.new(sep.outputs["Y"], lat.inputs[0])
    nt.links.new(off.outputs[0], lat.inputs[1])
    comb = node(nt, "ShaderNodeCombineXYZ", (-700, 50))
    comb.inputs["X"].default_value = 0.5
    nt.links.new(lat.outputs[0], comb.inputs["Y"])
    tex = node(nt, "ShaderNodeTexImage", (-550, 50))
    tex.image = band_image(k)
    tex.extension = "EXTEND"
    nt.links.new(comb.outputs[0], tex.inputs["Vector"])
    # fine grain, so close-ups are not smooth
    grain = node(nt, "ShaderNodeTexNoise", (-550, -250))
    grain.inputs["Scale"].default_value = 28.0
    grain.inputs["Detail"].default_value = 8.0
    nt.links.new(tc.outputs["Object"], grain.inputs["Vector"])
    # big classes average many lines into each band, which flattens them:
    # stretch their bands harder
    c = min(max(S.SIZES[-1].get(k, max(s.get(k, 0) for s in S.SIZES)) / 2000.0, 0.0), 1.0)
    stretch = node(nt, "ShaderNodeMapRange", (-400, 50))
    stretch.inputs["From Min"].default_value = 0.3 * c
    stretch.inputs["From Max"].default_value = 1.0 - 0.3 * c
    nt.links.new(tex.outputs["Color"], stretch.inputs["Value"])
    mixv = node(nt, "ShaderNodeMix", (-300, 0), data_type="FLOAT")
    mixv.inputs["Factor"].default_value = 0.18 - 0.08 * c
    nt.links.new(stretch.outputs["Result"], mixv.inputs["A"])
    nt.links.new(grain.outputs["Fac"], mixv.inputs["B"])
    ramp = node(nt, "ShaderNodeValToRGB", (-120, 0))
    # the sun is a point light, so the inner planets get far more of it:
    # darker surfaces there keep every planet's bands readable
    lit = min(max((S.ORBIT[k] / 9.0) ** 2, 0.15), 1.0)
    e = ramp.color_ramp.elements
    e[0].position, e[0].color = 0.0, (*[c * 0.05 * lit for c in rgb], 1)
    e[1].position, e[1].color = 1.0, (*[min(c * 1.05 + 0.08, 1) * lit for c in rgb], 1)
    e.new(0.45).color = (*[c * 0.45 * lit for c in rgb], 1)
    nt.links.new(mixv.outputs["Result"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    bump = node(nt, "ShaderNodeBump", (-120, -300))
    bump.inputs["Strength"].default_value = 0.25
    bump.inputs["Distance"].default_value = 0.02
    nt.links.new(mixv.outputs["Result"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    # a rim of the planet's own colour, brighter while commits land on it
    lw = node(nt, "ShaderNodeLayerWeight", (-400, -500))
    lw.inputs["Blend"].default_value = 0.3
    pw = node(nt, "ShaderNodeMath", (-200, -500), operation="POWER")
    pw.inputs[1].default_value = 5.0
    nt.links.new(lw.outputs["Facing"], pw.inputs[0])
    glow = node(nt, "ShaderNodeValue", (-200, -700))
    glow.outputs[0].default_value = 0.0
    base = node(nt, "ShaderNodeMath", (-50, -700), operation="ADD")
    base.inputs[1].default_value = 0.7
    nt.links.new(glow.outputs[0], base.inputs[0])
    mul = node(nt, "ShaderNodeMath", (0, -500), operation="MULTIPLY")
    nt.links.new(pw.outputs[0], mul.inputs[0])
    nt.links.new(base.outputs[0], mul.inputs[1])
    em = node(nt, "ShaderNodeEmission", (150, -500))
    em.inputs["Color"].default_value = (*rgb, 1)
    nt.links.new(mul.outputs[0], em.inputs["Strength"])
    add = node(nt, "ShaderNodeAddShader", (350, -300))
    nt.links.new(b.outputs[0], add.inputs[0])
    nt.links.new(em.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], out.inputs["Surface"])
    return m, glow.outputs[0]


class Planet:
    def __init__(self, k, cam):
        self.k = k
        mat, self.glow = planet_material(k)
        self.ob = sphere("Planet " + k, 1.0, mat)
        om, self.orbit_glow = glow_material("Orbit " + k, era(k), 0.0)
        self.orbit = ring_mesh("Orbit " + k, k, 0.022 / S.ORBIT[k], om)
        self.orbit.scale = [S.ORBIT[k]] * 3
        self.label = None
        lm, self.label_glow = glow_material("Label " + k, (0.92, 0.95, 1.0), 0.0)
        cu = bpy.data.curves.new("Label " + k, "FONT")
        cu.body = S.DISPLAY[k]
        cu.size = 0.32
        cu.font = bpy.data.fonts.load(LATO, check_existing=True)
        cu.align_x = "CENTER"
        cu.materials.append(lm)
        self.label = link(bpy.data.objects.new("Label " + k, cu))
        self.label.visible_shadow = False
        c = self.label.constraints.new("TRACK_TO")
        c.target = cam
        c.track_axis = "TRACK_Z"
        c.up_axis = "UP_Y"

    def update(self, frame, cam_loc):
        k = self.k
        on = TL.alive(k, frame)
        r = TL.SIZE[k][frame] if on else 0.0
        hidden = r < 0.01
        self.ob.hide_render = hidden
        self.label.hide_render = hidden
        x, y, z = TL.place(k, frame)
        self.ob.location = (x, y, z)
        self.ob.scale = [max(r, 0.001)] * 3
        # each planet spins on its own tilted axis
        n = S.ORDER.index(k)
        self.ob.rotation_euler = (0.25 * math.sin(n * 2.1), 0.0,
                                  TL.t_of(frame) * (0.25 + 0.1 * math.sin(n)))
        self.glow.default_value = 6.0 * TL.touched(k, frame)
        # the orbit appears once the planet has reached it
        drift = 1.0
        if S.DONOR.get(k):
            drift = min(max((frame - TL.BIRTH[k]) / TL.DRIFT, 0.0), 1.0)
        dead = 1.0 if k not in TL.DEATH or frame < TL.DEATH[k] else 0.0
        self.orbit_glow.default_value = 0.12 * on * drift * dead
        self.orbit.hide_render = not (on and drift * dead > 0)
        # names: on the big planets (fewer of them the further out the
        # camera is), and on new ones for their first seconds
        n = TL.lines_at(k, frame)
        need = LABEL_LINES + 45 * max(math.dist(cam_loc, (0, 0, 0)) - 10, 0)
        big = min(max((n - need) / 250 + 1, 0.0), 1.0)
        age = (frame - TL.BIRTH[k]) / FPS
        fresh = min(max(4 - age, 0.0), 1.0) if age >= 0 else 0.0
        g = 0.0 if hidden else max(big, fresh, 1.0 if k == "mainwindow" else 0.0)
        d = math.dist(cam_loc, (x, y, z))
        self.label.location = (x, y, z + r + 0.12 + 0.02 * d)
        self.label.scale = [0.05 * d + 0.2] * 3
        self.label_glow.default_value = 2.0 * g
        self.label.hide_render = g < 0.02


# ---------------------------------------------------------------- releases

class Shockwaves:
    """A ring of light out from the sun for every release."""

    POOL = 4
    LIFE = 3.0 * FPS

    def __init__(self):
        self.rel = TL.releases()
        self.rings = []
        for i in range(self.POOL):
            m, s = glow_material(f"Wave {i}", (1.0, 0.8, 0.5), 0.0)
            ob = ring_mesh(f"Wave {i}", None, 0.006, m)
            self.rings.append((ob, s))

    def update(self, frame):
        live = [(frame - f0, name) for f0, name in self.rel if 0 <= frame - f0 < self.LIFE]
        flare = 0.0
        for i, (ob, s) in enumerate(self.rings):
            if i < len(live):
                age, name = live[i]
                u = age / self.LIFE
                big = "rc" not in name and "beta" not in name
                ob.scale = [1.2 + 26 * u ** 0.7] * 3
                s.default_value = (4.0 if big else 2.0) * (1 - u) ** 2
                ob.hide_render = False
                flare = max(flare, (1 - u) ** 4 * (1.0 if big else 0.5))
            else:
                ob.hide_render = True
        return flare


# ---------------------------------------------------------------- world

def setup_world():
    s = bpy.context.scene
    w = bpy.data.worlds.new("Space")
    s.world = w
    nt = w.node_tree
    nt.nodes.clear()
    out = node(nt, "ShaderNodeOutputWorld", (800, 0))
    bg = node(nt, "ShaderNodeBackground", (600, 0))
    tc = node(nt, "ShaderNodeTexCoord", (-800, 0))
    vor = node(nt, "ShaderNodeTexVoronoi", (-400, -200))
    vor.inputs["Scale"].default_value = 420.0
    nt.links.new(tc.outputs["Generated"], vor.inputs["Vector"])
    pt = node(nt, "ShaderNodeMapRange", (-200, -200))
    pt.inputs["From Min"].default_value = 0.0
    pt.inputs["From Max"].default_value = 0.12
    pt.inputs["To Min"].default_value = 1.0
    pt.inputs["To Max"].default_value = 0.0
    nt.links.new(vor.outputs["Distance"], pt.inputs["Value"])
    sharp = node(nt, "ShaderNodeMath", (0, -200), operation="POWER")
    sharp.inputs[1].default_value = 7.0
    nt.links.new(pt.outputs[0], sharp.inputs[0])
    # a faint band of haze across the sky
    noise = node(nt, "ShaderNodeTexNoise", (-400, 200))
    noise.inputs["Scale"].default_value = 2.5
    nt.links.new(tc.outputs["Generated"], noise.inputs["Vector"])
    haze = node(nt, "ShaderNodeValToRGB", (-200, 200))
    nt.links.new(noise.outputs["Fac"], haze.inputs["Fac"])
    e = haze.color_ramp.elements
    e[0].position, e[0].color = 0.45, (0.0, 0.0, 0.0, 1)
    e[1].position, e[1].color = 0.8, (0.012, 0.01, 0.025, 1)
    add = node(nt, "ShaderNodeMix", (300, 0), data_type="RGBA", blend_type="ADD")
    add.inputs["Factor"].default_value = 1.0
    nt.links.new(haze.outputs["Color"], add.inputs["A"])
    nt.links.new(sharp.outputs[0], add.inputs["B"])
    nt.links.new(add.outputs["Result"], bg.inputs["Color"])
    nt.links.new(bg.outputs[0], out.inputs[0])


class Camera:
    def __init__(self):
        cd = bpy.data.cameras.new("Cam")
        cd.sensor_width = 36
        cd.clip_start = 0.05
        cd.clip_end = 2000
        self.ob = link(bpy.data.objects.new("Cam", cd))
        bpy.context.scene.camera = self.ob
        self.tgt = link(bpy.data.objects.new("Target", None))
        c = self.ob.constraints.new("TRACK_TO")
        c.target = self.tgt
        c.track_axis = "TRACK_NEGATIVE_Z"
        c.up_axis = "UP_Y"

    def set(self, frame):
        cam, tgt, lens = TL.camera(frame)
        if os.environ.get("CAM"):  # x,y,z,tx,ty,tz,lens: a fixed view for tests
            v = [float(c) for c in os.environ["CAM"].split(",")]
            cam, tgt, lens = v[0:3], v[3:6], v[6]
        self.ob.location = cam
        self.tgt.location = tgt
        self.ob.data.lens = lens
        return cam


def setup_render(pct, samples):
    s = bpy.context.scene
    s.render.engine = "BLENDER_EEVEE"
    s.render.resolution_x, s.render.resolution_y = 3840, 1608
    s.render.resolution_percentage = pct
    s.render.fps = FPS
    s.frame_start, s.frame_end = 1, FRAMES
    ee = s.eevee
    ee.taa_render_samples = samples
    for prop, val in (("use_raytracing", True), ("use_shadows", True)):
        if hasattr(ee, prop):
            setattr(ee, prop, val)
    vs = s.view_settings
    vs.view_transform = "AgX"
    for look in ("AgX - Punchy", "Punchy"):
        try:
            vs.look = look
            break
        except TypeError:
            pass


class Scene:
    def __init__(self):
        setup_world()
        self.camera = Camera()
        self.sun = Sun()
        self.planets = [Planet(k, self.camera.ob) for k in S.ORDER]
        self.waves = Shockwaves()

    def update(self, f):
        cam = self.camera.set(f)
        flare = self.waves.update(f)
        self.sun.update(f, flare)
        for p in self.planets:
            p.update(f, cam)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opts = {"pct": 25, "stills": "", "anim": False, "samples": 16,
            "start": 1, "end": FRAMES, "out": "frames", "save": ""}
    i = 0
    while i < len(argv):
        k = argv[i].lstrip("-")
        if k == "anim":
            opts["anim"] = True
            i += 1
        else:
            opts[k] = argv[i + 1]
            i += 2
    bpy.ops.wm.read_factory_settings(use_empty=True)
    setup_render(int(opts["pct"]), int(opts["samples"]))
    sc = Scene()
    s = bpy.context.scene

    def render(f, path):
        s.frame_set(f)
        sc.update(f)
        s.render.filepath = path
        bpy.ops.render.render(write_still=True)

    if opts["save"]:
        f = int(opts["stills"].split(",")[0]) if opts["stills"] else 1100
        s.frame_set(f)
        sc.update(f)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, opts["save"]))
    for f in [int(v) for v in opts["stills"].split(",") if v]:
        render(f, os.path.join(HERE, "renders", f"still_{f:04d}.png"))
    if opts["anim"]:
        s.render.image_settings.file_format = "PNG"
        for f in range(int(opts["start"]), int(opts["end"]) + 1):
            render(f, os.path.join(HERE, "renders", opts["out"], f"f_{f:04d}.png"))


main()
