"""Sonde (lecture seule) : biais de repos au retargeting. On retargete la pose de REPOS de la source (quaternions identité) : toute rotation non nulle des os cibles est un biais dû à la différence des poses de repos / des repères
(un mannequin au repos doit rester au repos). Affiche, pour les os des bras et des jambes, l'angle total, l'angle de flexion (autour de X local) et l'angle hors axe.

  blender --background --factory-startup --offline-mode --python-exit-code 0 --python tools/probe_wrist_bias.py -- --library DOSSIER"""
import math
from pathlib import Path
import sys

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import extension as addon  # noqa: E402
from extension.animation import mapping, retarget, skeleton  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:]
LIB = ARGS[ARGS.index("--library") + 1]
addon.register()
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.humanloom.create()
body = bpy.context.object
rig = skeleton.install(body)
target = retarget.rig_from_armature(rig)
target_map = mapping.from_armature(rig)
library = sorted(Path(LIB).glob("*.blend"))[0]
with bpy.data.libraries.load(str(library), link=False) as (names, _):
    armature_names = list(names.armatures)
best = None
for name in armature_names:
    with bpy.data.libraries.load(str(library), link=False) as (_, wanted):
        wanted.armatures = [name]
    data = wanted.armatures[0]
    if len(data.bones) < 80:
        bpy.data.armatures.remove(data)
        continue
    pairs, report = mapping.auto_map(target_map, mapping.from_armature(data))
    score = (report.coverage, -len(report.low_confidence))
    if best is None or score > best[0]:
        best = (score, name, {t: p.source for t, p in pairs.items()})
    bpy.data.armatures.remove(data)
with bpy.data.libraries.load(str(library), link=False) as (_, wanted):
    wanted.armatures = [best[1]]
source = retarget.rig_from_armature(wanted.armatures[0])
links = best[2]
print("source :", best[1], "couverture", best[0][0])
frames = 1
loc = np.zeros((frames, len(source.names), 3))
quat = np.tile([1.0, 0.0, 0.0, 0.0], (frames, len(source.names), 1))
motion = retarget.Motion(loc, quat, 30.0)


def report(label, options):
    result = retarget.retarget(source, target, links, motion, options)
    print(label)
    for name in ("clavicle.L", "arm_upper.L", "arm_lower.L", "hand.L", "leg_upper.L", "leg_lower.L", "foot.L", "spine.03", "head"):
        q = result.quat[0, target.index[name]]
        w, x, y, z = q
        total = math.degrees(2 * math.acos(min(1.0, abs(w))))
        flex = math.degrees(2 * math.atan2(x * math.copysign(1, w), abs(w)))
        off = math.degrees(2 * math.atan2(math.hypot(y, z), abs(w)))
        print(f"  {name:12s} rotation totale {total:6.1f}° ; autour de X {flex:7.1f}° ; hors axe (Y,Z) {off:6.1f}°")


report("ABSOLU + IK jambes (défaut) :", retarget.Options(pose_mode=retarget.ABSOLUTE_IK, root_motion=retarget.KEEP, ik_limbs=("leg",)))
report("ABSOLU (sans IK) :", retarget.Options(pose_mode=retarget.ABSOLUTE, root_motion=retarget.KEEP))
report("DELTA :", retarget.Options(pose_mode=retarget.DELTA, root_motion=retarget.KEEP))

print("--- directions avant-bras / main (monde) ---")
result = retarget.retarget(source, target, links, motion, retarget.Options(pose_mode=retarget.ABSOLUTE_IK, root_motion=retarget.KEEP, ik_limbs=("leg",)))
t_pos = retarget.joint_positions(target, result.loc, result.quat)[0]
t_rest = retarget.joint_positions(target, np.zeros((1, len(target.names), 3)), np.tile([1.0, 0, 0, 0], (1, len(target.names), 1)))[0]
s_rest = retarget.joint_positions(source, loc, quat)[0]


def angle(a, b):
    return math.degrees(math.acos(float(np.clip(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)), -1, 1))))


for side in (".L",):
    elbow, wrist, finger = "arm_lower" + side, "hand" + side, "middle.01" + side
    for label, pos, idx, names in (("cible repos", t_rest, target.index, (elbow, wrist, finger)), ("cible retargetée", t_pos, target.index, (elbow, wrist, finger)),
                                   ("source repos", s_rest, source.index, tuple(links[n] for n in (elbow, wrist, finger)))):
        e, w, f = (pos[idx[n]] for n in names)
        print(f"  {label:18s} : angle coude→poignet / poignet→doigt = {angle(w - e, f - w):5.1f}°")
    print("  appariement : ", {n: links[n] for n in (elbow, wrist, finger)})

print("--- sur le rig posé par le retargeting du repos de la source ---")
for b in rig.pose.bones:
    b.rotation_mode = "QUATERNION"
    b.rotation_quaternion = (1, 0, 0, 0)
bpy.context.view_layer.update()


def axis_of(name):
    b = rig.pose.bones[name]
    h, t = np.array((rig.matrix_world @ b.head)[:]), np.array((rig.matrix_world @ b.tail)[:])
    return t - h


rest_angle = angle(axis_of("arm_lower.L"), axis_of("hand.L"))
for i, nme in enumerate(target.names):
    pb = rig.pose.bones[nme]
    pb.rotation_quaternion = tuple(result.quat[0, i])
    pb.location = tuple(result.loc[0, i])
bpy.context.view_layer.update()
posed_angle = angle(axis_of("arm_lower.L"), axis_of("hand.L"))
q = rig.pose.bones["hand.L"].rotation_quaternion
print(f"  angle entre l'axe de l'avant-bras et l'axe de la main : repos {rest_angle:.1f}° ; posé {posed_angle:.1f}° ; quaternion locale de la main {tuple(round(v, 3) for v in q)}")
print("  la flexion mesurée par la rotation locale est donc", "COHÉRENTE" if abs(posed_angle - rest_angle) > 40 else "NON cohérente (axes locaux différents) avec la déformation géométrique")

print("--- essai : enfant principal de la main = articulation du majeur (middle.01) au lieu du premier enfant apparié ---")
default_child = {}
for i, p in enumerate(target.parents):
    if p >= 0 and target.names[p] in links and target.names[i] in links:
        default_child.setdefault(target.names[p], target.names[i])
print("  enfant principal par défaut de hand.L :", default_child.get("hand.L"), "; de foot.L :", default_child.get("foot.L"))
custom = dict(default_child)
for side in (".L", ".R"):
    if "middle.01" + side in links:
        custom["hand" + side] = "middle.01" + side
result2 = retarget.retarget(source, target, links, motion, retarget.Options(pose_mode=retarget.ABSOLUTE_IK, root_motion=retarget.KEEP, ik_limbs=("leg",)), main_child=custom)
for i, nme in enumerate(target.names):
    pb = rig.pose.bones[nme]
    pb.rotation_quaternion = tuple(result2.quat[0, i])
    pb.location = tuple(result2.loc[0, i])
bpy.context.view_layer.update()
q = rig.pose.bones["hand.L"].rotation_quaternion
w, x, y, z = q
print(f"  hand.L : angle axe avant-bras / axe main {angle(axis_of('arm_lower.L'), axis_of('hand.L')):.1f}° (repos {rest_angle:.1f}°) ; quaternion locale {tuple(round(v, 3) for v in q)} ; rotation totale {math.degrees(2 * math.acos(min(1.0, abs(w)))):.1f}°")
