"""Validation du lot A1b : importation d'animations (FBX, BVH, glTF, .blend) dans une bibliothèque utilisateur, puis relecture par l'index du lot A1.

Aucun fichier d'une bibliothèque tierce : les sources sont GÉNÉRÉES ici depuis un squelette synthétique (4 os), dans un dossier temporaire.
Exécution : blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_animation_import.py -- [--out FICHIER.json]
Chaque import tourne dans un processus Blender séparé (comme en production).
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile

import bpy

ROOT = Path(__file__).resolve().parents[1]
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = ARGS[ARGS.index("--out") + 1] if "--out" in ARGS else None


def load(name):
    spec = importlib.util.spec_from_file_location(f"hl_anim_{name}", ROOT / f"extension/animation/{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


index_module = load("index")
importer = load("importer")
results, failures = {}, []


def check(name, ok, detail=None):
    results[name] = {"ok": bool(ok), "detail": detail}
    print(("OK  " if ok else "KO  ") + name, detail if detail is not None else "")
    if not ok:
        failures.append(name)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_rig():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.object.armature_add()
    arm = bpy.context.object
    arm.name = "SynthRig"
    bpy.ops.object.mode_set(mode="EDIT")
    bones = arm.data.edit_bones
    root = bones[0]
    root.name, root.head, root.tail = "root", (0, 0, 0), (0, 0, 0.1)
    pelvis = bones.new("pelvis")
    pelvis.head, pelvis.tail, pelvis.parent = (0, 0, 1), (0, 0, 1.2), root
    spine = bones.new("spine_01")
    spine.head, spine.tail, spine.parent = (0, 0, 1.2), (0, 0, 1.5), pelvis
    head = bones.new("head")
    head.head, head.tail, head.parent = (0, 0, 1.5), (0, 0, 1.75), spine
    bpy.ops.object.mode_set(mode="POSE")
    for bone in arm.pose.bones:
        bone.rotation_mode = "QUATERNION"
    bpy.context.scene.render.fps = 30
    return arm


def animate(arm, kind):
    """Nouvelle action « kind » : walk/run déplacent l'os racine de 3 m, idle/wave/nod seulement des rotations (valeurs différentes)."""
    arm.animation_data_clear()
    angle = {"walk": 0.4, "run": 0.7, "idle": 0.1, "wave": 0.9, "nod": 0.5}[kind]
    bone = {"walk": "spine_01", "run": "spine_01", "idle": "spine_01", "wave": "pelvis", "nod": "head"}[kind]
    for frame in (1, 16, 31):
        if kind in ("walk", "run"):
            arm.pose.bones["root"].location = (0, 3.0 * (frame - 1) / 30, 0)
            arm.pose.bones["root"].keyframe_insert("location", frame=frame)
        a = angle * (frame - 1) / 30
        arm.pose.bones[bone].rotation_quaternion = (1 - a * a / 2, a, 0, 0)
        arm.pose.bones[bone].keyframe_insert("rotation_quaternion", frame=frame)
    bpy.context.scene.frame_start, bpy.context.scene.frame_end = 1, 31
    arm.animation_data.action.name = kind
    return arm.animation_data.action


def only_current_action(arm):
    """glTF exporte toutes les actions du fichier : on ne garde que l'action courante pour que chaque source contienne une seule animation."""
    for action in list(bpy.data.actions):
        if action != arm.animation_data.action:
            bpy.data.actions.remove(action)


def select(arm):
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm


work = Path(tempfile.mkdtemp(prefix="hl_anim_import_"))
try:
    src = work / "sources"
    for folder in ("Walk", "Run", "Idle", "Packs", "Bad"):
        (src / folder).mkdir(parents=True)
    arm = build_rig()
    animate(arm, "walk"); select(arm)
    bpy.ops.export_scene.fbx(filepath=str(src / "Walk/walk.fbx"), use_selection=True, bake_anim=True)
    shutil.copyfile(src / "Walk/walk.fbx", src / "Walk/walk_bytes_copy.fbx")  # même octets : « inchangé »
    bpy.ops.export_scene.fbx(filepath=str(src / "Walk/walk_reexport.fbx"), use_selection=True, bake_anim=True)  # même animation, fichier différent : « doublon »
    bpy.ops.object.mode_set(mode="POSE")
    animate(arm, "run"); only_current_action(arm); select(arm)
    bpy.ops.export_anim.bvh(filepath=str(src / "Run/run.bvh"), root_transform_only=False)
    bpy.ops.object.mode_set(mode="POSE")
    animate(arm, "idle"); only_current_action(arm); select(arm)
    bpy.ops.export_scene.gltf(filepath=str(src / "Idle/idle.glb"), use_selection=True)
    bpy.ops.object.mode_set(mode="POSE")
    wave = animate(arm, "wave"); wave["ualm_fps"] = 30.0; wave.use_fake_user = True
    nod_arm_action = None
    arm.animation_data_clear()
    nod = animate(arm, "nod"); nod.use_fake_user = True; nod["ualm_flags"] = "additive"  # chaîne, comme dans la bibliothèque UALM (mesuré)
    bpy.data.libraries.write(str(src / "Packs/pack.blend"), {wave, nod}, fake_user=True)
    (src / "Bad/broken.fbx").write_bytes(b"ceci n'est pas un fichier FBX" * 20)

    # Faux dossier d'export de l'outil Unreal (manifest.json + inventory.json + animations/<squelette>/<dossier>/<Nom>.fbx) : fabriqué ici.
    export = work / "export"
    skeleton_id = "Characters_Test_Meshes_SK_TestRig"
    declared_files = {}
    arm = build_rig()
    for kind, folder in (("walk", "Walk"), ("idle", "Idle"), ("wave", "Gestures")):
        animate(arm, kind); only_current_action(arm); select(arm)
        relative = f"animations/{skeleton_id}/Characters/Test/Animations/{folder}/Fake_{kind}.fbx"
        (export / relative).parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.export_scene.fbx(filepath=str(export / relative), use_selection=True, bake_anim=True)
        bpy.ops.object.mode_set(mode="POSE")
        declared_files[kind] = relative
    mesh_file = export / f"characters/{skeleton_id}/SKM_Fake.fbx"  # maillage de personnage : présent dans le dossier, absent des animations du manifest
    mesh_file.parent.mkdir(parents=True)
    bpy.ops.mesh.primitive_cube_add()
    bpy.ops.export_scene.fbx(filepath=str(mesh_file), use_selection=True)
    declarations = {  # volontairement différentes de ce que l'heuristique mesurerait
        "walk": {"root_motion": False, "additive": "NONE", "frame_rate": 24.0, "flags": [], "num_frames": 31},
        "idle": {"root_motion": True, "additive": "NONE", "frame_rate": 60.0, "flags": ["root_motion"], "num_frames": 31},
        "wave": {"root_motion": False, "additive": "ROTATION_OFFSET_MESH_SPACE", "frame_rate": 30.0, "flags": ["additive"], "num_frames": 31},
    }
    manifest_animations = {}
    for kind, relative in declared_files.items():
        sha1 = importer.sha1(export / relative)
        if kind == "wave":
            sha1 = "0" * 40  # empreinte volontairement fausse : avertissement attendu
        manifest_animations[f"/Game/Test/Animations/Fake_{kind}"] = {"id": f"/Game/Test/Animations/Fake_{kind}", "name": f"Fake_{kind}", "folder": f"Characters/Test/Animations/{relative.split('/')[-2]}",
                                                                   "skeleton": skeleton_id, "file": relative, "fbx_sha1": sha1, "length": 1.0, **declarations[kind]}
    for name in ("manifest.json", "inventory.json"):
        (export / name).write_text(json.dumps({"schema": 1, "animations": manifest_animations}), encoding="utf-8")

    source_files = sorted(p for p in src.rglob("*") if p.is_file()) + sorted(p for p in export.rglob("*") if p.is_file())
    sha_before = {p.name: sha(p) for p in source_files}
    library = work / "ma_bibliotheque"
    exe = bpy.app.binary_path

    report = importer.import_sources([src], library, exe, fps=30.0)
    by_name = {f["source"]: f for f in report["fichiers"]}
    print("RAPPORT", json.dumps({k: v for k, v in report.items() if k != "fichiers"}, ensure_ascii=False), {n: f["statut"] for n, f in by_name.items()})
    check("I1_statuts", by_name["walk.fbx"]["statut"] == "importé" and by_name["run.bvh"]["statut"] == "importé" and by_name["idle.glb"]["statut"] == "importé"
          and by_name["pack.blend"]["statut"] == "importé" and by_name["pack.blend"]["ajoutées"] == 2 and by_name["walk_bytes_copy.fbx"]["statut"] == "inchangé"
          and by_name["walk_reexport.fbx"]["statut"] in ("doublon", "inchangé") and by_name["broken.fbx"]["statut"] == "échec",
          {n: f["statut"] for n, f in by_name.items()})
    check("I2_compte", report["ajoutées"] == 5 and report["échecs"] == 1, {"ajoutées": report["ajoutées"], "doublons": report["doublons"], "inchangés": report["inchangés"],
                                                                               "échecs": report["échecs"], "message_échec": by_name["broken.fbx"].get("message")})
    check("I3_source_inchangee", report["sources_modifiées"] == [] and {p.name: sha(p) for p in source_files} == sha_before, {"fichiers": len(source_files)})

    cache = work / "cache"
    index, origin = index_module.open_index(library, cache)
    by_entry = {index.entry(i)["name"]: index.entry(i) | {"category": index.category(i)} for i in range(len(index))}
    check("I4_index_relit_l_import", len(index) == 5 and origin == "inventory", {"entrées": len(index), "noms": sorted(by_entry)})
    categories = {k: v for k, v in index.categories().items() if v}
    check("I5_categories_d_apres_dossier", categories == {"Walk": 1, "Run": 1, "Idle": 1, "Packs": 2}, categories)
    flags = {n: e["root_motion"] for n, e in by_entry.items()}
    check("I6_root_motion_mesure", flags.get("walk") and flags.get("run") and not any(flags[n] for n in ("idle", "wave", "nod")), flags)
    check("I6b_drapeaux_ualm_en_chaine", by_entry["nod"]["additive"] and not by_entry["nod"]["root_motion"] and not by_entry["wave"]["additive"], {"nod": {"additive": by_entry["nod"]["additive"], "root_motion": by_entry["nod"]["root_motion"]}})
    fps = {n: e["fps"] for n, e in by_entry.items()}
    frames = {n: e["frames"] for n, e in by_entry.items()}
    check("I7_fps_et_images", fps["walk"] == 30 and fps["run"] == 30 and fps["idle"] == 30 and fps["wave"] == 30 and fps["nod"] == 0 and all(abs(frames[n] - 31) <= 1 for n in ("walk", "run", "idle", "wave", "nod")),
          {"fps": fps, "images": frames})

    # Les noms d'action déclarés existent dans le .blend de bibliothèque (bijection), une action chargée porte les métadonnées ualm_*.
    blend = library / importer.LIBRARY_BLEND
    blend_names = [r[0] for r in index_module.names_from_blend(blend)]
    check("I8_actions_dans_la_bibliotheque", index.actions is not None and sorted(index.actions) == sorted(blend_names) and len(blend_names) == 5, {"noms_blend": sorted(blend_names)})
    target = next(a for a in index.actions if a.endswith("walk"))
    with bpy.data.libraries.load(str(blend), link=False) as (_from, to):
        to.actions = [target]
    action = to.actions[0]
    meta = {k: (action[k] if k in action else None) for k in ("ualm_id", "ualm_category", "ualm_family", "ualm_skeleton", "ualm_fps", "ualm_digest", "ualm_rest_height")}
    curves = sum(len(b.fcurves) for l in action.layers for s in l.strips for b in s.channelbags)
    check("I9_metadonnees_ualm", all(v not in (None, "") for v in meta.values()) and meta["ualm_family"] == "HumanLoom import" and curves > 0 and meta["ualm_category"] == "Walk",
          {"métadonnées": {k: (v if k != "ualm_digest" else str(v)[:10]) for k, v in meta.items()}, "courbes": curves})

    # Seconde passe : tout est déjà importé, rien n'est ajouté ; le fichier cassé échoue toujours ; bibliothèque inchangée.
    library_sha = sha(blend)
    again = importer.import_sources([src], library, exe, fps=30.0)
    check("I10_reimport_sans_ajout", again["ajoutées"] == 0 and again["échecs"] == 1 and again["inchangés"] >= 5 and sha(blend) == library_sha,
          {"ajoutées": again["ajoutées"], "inchangés": again["inchangés"], "échecs": again["échecs"], "bibliothèque_identique": sha(blend) == library_sha})

    # Déduplication par contenu : même animation, autre fichier (pas les mêmes octets) = « doublon », même si le nom diffère.
    shutil.copyfile(src / "Walk/walk.fbx", src / "Walk/zz_copie.fbx")
    data = (src / "Walk/zz_copie.fbx").read_bytes()
    (src / "Walk/zz_copie.fbx").write_bytes(data + b"\n; commentaire ajoute\n")
    third = importer.import_sources([src / "Walk/zz_copie.fbx"], library, exe, fps=30.0)
    status = third["fichiers"][0]
    check("I11_doublon_par_contenu", third["ajoutées"] == 0 and third["doublons"] >= 1 and status["statut"] in ("doublon", "échec"),
          {"statut": status["statut"], "message": status.get("message"), "doublons": status.get("doublons")})

    # Dossier d'export de l'outil Unreal : métadonnées DÉCLARÉES (pas l'heuristique), maillages ignorés, empreinte vérifiée.
    library2 = work / "ma_bibliotheque_export"
    export_report = importer.import_sources([export], library2, exe)
    states = {f["source"]: f for f in export_report["fichiers"]}
    index2, origin2 = index_module.open_index(library2, work / "cache_export")
    entries2 = {index2.entry(i)["name"]: index2.entry(i) | {"category": index2.category(i)} for i in range(len(index2))}
    check("E1_statuts_export", [states[f"Fake_{k}.fbx"]["statut"] for k in ("walk", "idle", "wave")] == ["importé"] * 3 and states["SKM_Fake.fbx"]["statut"] == "ignoré"
          and export_report["ajoutées"] == 3 and export_report["ignorés"] == 1 and export_report["échecs"] == 0 and export_report["sources_modifiées"] == [],
          {n: {k: v for k, v in f.items() if k != "doublons"} for n, f in states.items()})
    check("E2_metadonnees_declarees", entries2["Fake_walk"]["fps"] == 24 and entries2["Fake_idle"]["fps"] == 60 and entries2["Fake_idle"]["root_motion"] and not entries2["Fake_walk"]["root_motion"]
          and entries2["Fake_wave"]["additive"] and states["Fake_walk.fbx"]["metadonnees"].startswith("déclarées"),
          {n: {"fps": e["fps"], "root_motion": e["root_motion"], "additive": e["additive"]} for n, e in entries2.items()})
    check("E3_categorie_dossier_unreal", {n: e["category"] for n, e in entries2.items()} == {"Fake_walk": "Walk", "Fake_idle": "Idle", "Fake_wave": "Gestures"}, {n: e["category"] for n, e in entries2.items()})
    check("E4_empreinte_et_heuristique_de_repli", "SHA-1" in states["Fake_wave.fbx"].get("avertissement", "") and "avertissement" not in states["Fake_walk.fbx"]
          and by_name["walk.fbx"]["statut"] == "importé" and by_entry["walk"]["root_motion"], states["Fake_wave.fbx"].get("avertissement"))
    check("E5_noms_d_action_declares", index2.actions is not None and all(a.startswith("SK_TestRig__") for a in index2.actions) and all(e["skeleton"] == skeleton_id for e in entries2.values()),
          {"actions": index2.actions})

    # Garde-fou : un dossier cible qui contient l'inventaire d'un autre outil est refusé (la source n'est jamais modifiée).
    foreign = work / "autre_inventaire"
    foreign.mkdir()
    (foreign / "inventory.json").write_text(json.dumps({"schema": 1, "animations": {}}), encoding="utf-8")
    foreign_sha = sha(foreign / "inventory.json")
    try:
        importer.import_sources([src / "Walk/walk.fbx"], foreign, exe)
        refused = False
    except ValueError:
        refused = True
    check("I12_refus_inventaire_etranger", refused and sha(foreign / "inventory.json") == foreign_sha)

    # Aucun chemin local dans l'inventaire écrit.
    text = (library / importer.INVENTORY).read_text(encoding="utf-8")
    report_text = json.dumps([report, again, third], ensure_ascii=False)
    check("I13_pas_de_chemin_local", str(work) not in text and str(work) not in report_text and Path.home().name not in report_text and str(Path.home()) not in text and "\\\\" not in text.replace("\\n", ""))
finally:
    shutil.rmtree(work, ignore_errors=True)

if OUT:
    Path(OUT).write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
print("RESULT", "FAIL " + ", ".join(failures) if failures else "PASS")
sys.exit(1 if failures else 0)
