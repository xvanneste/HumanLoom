"""Valide le groupe de nœuds « HL Human » (schéma 10, lot 1) contre le moteur actuel (clés de forme + pilotes).

Usage : blender --background --factory-startup --offline-mode --python-exit-code 1 --python tools/validate_human_nodes.py -- <human_nodes.blend> <sortie.json>
Importe `extension` depuis le dépôt (corps de référence créé par l'opérateur actuel) ; n'écrit que dans le dossier de sortie.

Critères (PLAN_SCHEMA_10.md, lot 1) :
- cage des nœuds contre cage du moteur actuel sur >= 25 états : écart max < 2e-5 m (0,02 mm), écart max par état donné ;
- (a) médiane >= 20 changements de curseur avec Subsurf niveau 1, nœuds et moteur actuel (ms) ;
- (b) rappel d'une commande à 0 : la forme revient au neutre à 1e-6 m (nœuds et moteur) ;
- (c) fichier enregistré puis rouvert SANS l'extension : même forme ;
- (d) 21 états de `tools/data/neutral_reference.json` : < 1e-5 m.
Aucun critère n'est assoupli : un dépassement fait échouer le test et la liste des états/contrôles fautifs est écrite."""
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import extension as addon
import neutral_reference as neutral
from extension.proportions import CONTROLS

BLEND, OUT = [Path(p).resolve() for p in sys.argv[sys.argv.index("--") + 1:][:2]]
OUT.parent.mkdir(parents=True, exist_ok=True)
CRITERION = 2e-5
CONTROL_IDS = [c[0] for c in CONTROLS]
result = {"criterion_m": CRITERION}

addon.register()
for obj in tuple(bpy.context.scene.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.human_modeling.create()
engine = bpy.context.object
keys = engine.data.shape_keys
for modifier in engine.modifiers:
    modifier.show_viewport = False
with bpy.data.libraries.load(str(BLEND), link=False) as (_, target):
    target.node_groups = ["HL Human"]
    target.meshes = ["HL Human Base"]
group, mesh = target.node_groups[0], target.meshes[0]
nodes_obj = bpy.data.objects.new("HL Human nodes", mesh)
bpy.context.scene.collection.objects.link(nodes_obj)
modifier = nodes_obj.modifiers.new("HL Human", "NODES")
modifier.node_group = group
identifier = {s.name: s.identifier for s in group.interface.items_tree if s.item_type == "SOCKET" and s.in_out == "INPUT" and s.socket_type == "NodeSocketFloat"}
assert set(identifier) == {"sex", "age", *CONTROL_IDS}, set(identifier) ^ {"sex", "age", *CONTROL_IDS}
result["group"] = {"nodes": len(group.nodes), "links": len(group.links), "layers": sum(a.startswith("b") and a[1:].isdigit() for a in mesh.attributes.keys()),
                   "fingerprint": group.get("hl_graph_fingerprint"), "tolerance": group.get("hl_tolerance"), "blend_bytes": BLEND.stat().st_size}


def set_engine(state):
    keys.key_blocks["Morphologie"].value = state["sex"]
    keys["human_modeling_age"] = state["age"]
    for control in CONTROL_IDS:
        keys["hm_" + control] = state.get(control, 0.)


def set_nodes(state):
    for name, ident in identifier.items():
        getattr(modifier.properties.inputs, ident).value = float(state.get(name, 2. if name == "age" else 0.))


def evaluated(obj):
    obj.update_tag()
    keys.update_tag()
    bpy.context.view_layer.update()
    mesh_eval = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
    points = np.array([v.co[:] for v in mesh_eval.vertices])
    obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh_clear()
    return points


def both(state):
    set_engine(state)
    set_nodes(state)
    return evaluated(engine), evaluated(nodes_obj)


# --- états : sexes 0/0,5/1 x stades 0/1/2/3, commandes à +1 ou -1, tirages à graine fixe ----------------------------------
states = []
for sex in (0., .5, 1.):
    for age in (0., 1., 2., 3.):
        states.append({"name": f"neutre sexe={sex:g} age={age:g}", "sex": sex, "age": age})
        states.append({"name": f"tout +1 sexe={sex:g} age={age:g}", "sex": sex, "age": age, **{c: 1. for c in CONTROL_IDS}})
for sex in (0., 1.):
    for age in (0., 1., 2., 3.):
        states.append({"name": f"tout -1 sexe={sex:g} age={age:g}", "sex": sex, "age": age, **{c: -1. for c in CONTROL_IDS}})
rng = np.random.default_rng(3)
for i in range(20):
    state = {c: float(rng.uniform(-1, 1)) for c in CONTROL_IDS}
    states.append({"name": f"tirage {i}", "sex": float(rng.uniform(0, 1)), "age": float(rng.uniform(0, 3)), **state})
rows = []
for state in states:
    a, b = both(state)
    rows.append({"state": state["name"], "max_error_m": float(np.abs(a - b).max())})
worst = max(rows, key=lambda r: r["max_error_m"])
result["equivalence"] = {"states": len(rows), "max_error_m": worst["max_error_m"], "worst_state": worst["state"],
                         "median_error_m": statistics.median(r["max_error_m"] for r in rows), "per_state": rows}
failing = [r for r in rows if r["max_error_m"] >= CRITERION]
result["equivalence"]["failing_states"] = [r["state"] for r in failing]
if failing:  # diagnostic : quels contrôles, seuls à +/-1, sont fautifs dans les états en échec
    culprits = {}
    for r in failing[:6]:
        state = next(s for s in states if s["name"] == r["state"])
        for control in CONTROL_IDS:
            for amount in (-1., 1.):
                single = {"sex": state["sex"], "age": state["age"], control: amount}
                a, b = both(single)
                error = float(np.abs(a - b).max())
                if error >= CRITERION:
                    culprits.setdefault(r["state"], []).append([control, amount, error])
    result["equivalence"]["culprits"] = culprits

# --- (a) temps d'un changement de curseur avec Subsurf niveau 1 ------------------------------------------------------------
def timing(setter, obj, runs=30):
    sample = np.random.default_rng(1)
    times = []
    state = {"sex": 1., "age": 2.}
    for _ in range(runs):
        state[CONTROL_IDS[int(sample.integers(len(CONTROL_IDS)))]] = float(sample.uniform(-1, 1))
        setter(state)
        started = time.perf_counter()
        evaluated(obj)
        times.append((time.perf_counter() - started) * 1000)
    return {"runs": runs, "median_ms": round(statistics.median(times), 1), "p90_ms": round(sorted(times)[int(.9 * runs)], 1)}


timings = {"nodes_cage": timing(set_nodes, nodes_obj)}
sub_nodes = nodes_obj.modifiers.new("sub", "SUBSURF")
sub_nodes.levels = 1
timings["nodes_subsurf1"] = timing(set_nodes, nodes_obj)
nodes_obj.modifiers.remove(sub_nodes)
timings["engine_cage"] = timing(set_engine, engine)
sub_engine = engine.modifiers.new("sub", "SUBSURF")
sub_engine.levels = 1
timings["engine_subsurf1"] = timing(set_engine, engine)
engine.modifiers.remove(sub_engine)
timings["note"] = "CPU, arrière-plan, to_mesh ; dépend de la charge de la machine ; prototype : 58,5 ms (nœuds + Subsurf 1, tolérance 1e-4) contre 42,6 ms (clés)"
result["timing"] = timings

# --- (b) rappel d'une commande à 0 : retour au neutre à 1e-6 ---------------------------------------------------------------
neutral_state = {"sex": .5, "age": 2.}
set_engine(neutral_state); set_nodes(neutral_state)
neutral_engine, neutral_nodes = evaluated(engine), evaluated(nodes_obj)
returns, weak = [], []
for control in CONTROL_IDS:
    state = {**neutral_state, control: 1.}
    a, b = both(state)
    effect = float(np.abs(b - neutral_nodes).max())
    if effect < 1e-6:
        weak.append(control)
    a, b = both(neutral_state)
    returns.append({"control": control, "nodes_effect_at_1_m": effect, "nodes_return_error_m": float(np.abs(b - neutral_nodes).max()),
                    "engine_return_error_m": float(np.abs(a - neutral_engine).max())})
result["return_to_neutral"] = {"max_nodes_return_error_m": max(r["nodes_return_error_m"] for r in returns),
                               "max_engine_return_error_m": max(r["engine_return_error_m"] for r in returns),
                               "controls_without_effect_at_1": weak, "per_control": returns}

# --- (d) référence figée (21 états) ----------------------------------------------------------------------------------------
reference = neutral.load()
indices = neutral.body_indices(engine)
reference_rows = []
for sex in neutral.SEXES:
    for stage in neutral.STAGES:
        set_nodes({"sex": sex, "age": stage})
        points = evaluated(nodes_obj)[indices]
        expected = np.array(reference["states"][neutral.key(sex, stage)]["points"]).reshape(-1, 3)
        reference_rows.append({"sex": sex, "stage": stage, "max_error_m": float(np.abs(points - expected).max())})
result["frozen_reference"] = {"states": len(reference_rows), "max_error_m": max(r["max_error_m"] for r in reference_rows),
                              "per_state": reference_rows, "note": "corps seul (yeux non couverts par les nœuds)"}

# --- (c) enregistré puis rouvert sans l'extension --------------------------------------------------------------------------
check_states = [states[0], states[1], states[25], states[40], states[-1]]
expected_by_state = []
for state in check_states:
    set_nodes(state)
    expected_by_state.append(evaluated(nodes_obj))
sub = nodes_obj.modifiers.new("sub", "SUBSURF")
sub.levels = 1
sub.show_viewport = False  # présent dans le fichier mais coupé : la comparaison porte sur la cage
for other in tuple(bpy.context.scene.objects):
    if other is not nodes_obj:
        bpy.data.objects.remove(other, do_unlink=True)
saved = OUT.parent / "human_nodes_scene.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(saved), compress=True)
probe = OUT.parent / "reopen_probe.py"
probe.write_text("""
import bpy, sys, json, numpy as np
out, states = sys.argv[-2], json.loads(open(sys.argv[-1], encoding='utf-8').read())
bpy.ops.wm.open_mainfile(filepath=sys.argv[-3])
obj = bpy.data.objects['HL Human nodes']; md = obj.modifiers['HL Human']
ids = {s.name: s.identifier for s in md.node_group.interface.items_tree if s.item_type == 'SOCKET' and s.in_out == 'INPUT' and s.socket_type == 'NodeSocketFloat'}
res = []
for st in states:
    for n, i in ids.items():
        getattr(md.properties.inputs, i).value = float(st.get(n, 2.0 if n == 'age' else 0.0))
    obj.update_tag(); bpy.context.view_layer.update()
    e = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()); m = e.to_mesh()
    res.append([list(v.co) for v in m.vertices]); e.to_mesh_clear()
json.dump({'points': res, 'extension_loaded': any(k.startswith('bl_ext') and 'human_modeling' in k for k in sys.modules), 'extension_enabled': 'human_modeling' in ' '.join(bpy.context.preferences.addons.keys())}, open(out, 'w'))
print('REOPEN_OK')
""", encoding="utf-8")
states_file = OUT.parent / "reopen_states.json"
states_file.write_text(json.dumps(check_states), encoding="utf-8")
answer = OUT.parent / "reopen_answer.json"
run = subprocess.run([bpy.app.binary_path, "--background", "--factory-startup", "--offline-mode", "--python-exit-code", "1", "--python", str(probe), "--",
                      str(saved), str(answer), str(states_file)], capture_output=True, text=True, timeout=600)
assert run.returncode == 0 and "REOPEN_OK" in run.stdout, run.stdout[-800:] + run.stderr[-800:]
reopened = json.loads(answer.read_text(encoding="utf-8"))
errors = [float(np.abs(np.array(got) - want).max()) for got, want in zip(reopened["points"], expected_by_state)]
result["reopen_without_extension"] = {"states": len(errors), "max_error_m": max(errors), "extension_loaded": reopened["extension_loaded"],
                                      "extension_enabled": reopened["extension_enabled"], "scene_bytes": saved.stat().st_size}

# --- verdict ---------------------------------------------------------------------------------------------------------------
verdict = {
    "equivalence < 2e-5 m": result["equivalence"]["max_error_m"] < CRITERION,
    "retour au neutre < 1e-6 m (nœuds)": result["return_to_neutral"]["max_nodes_return_error_m"] < 1e-6,
    "référence figée < 1e-5 m": result["frozen_reference"]["max_error_m"] < 1e-5,
    "rouvert sans extension identique (< 1e-6 m) et extension absente": result["reopen_without_extension"]["max_error_m"] < 1e-6
    and not result["reopen_without_extension"]["extension_loaded"] and not result["reopen_without_extension"]["extension_enabled"],
}
result["verdict"] = verdict
OUT.write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
summary = {k: result[k] for k in ("group", "timing", "verdict")}
summary["equivalence"] = {k: result["equivalence"][k] for k in ("states", "max_error_m", "worst_state", "median_error_m", "failing_states")}
summary["return_to_neutral"] = {k: result["return_to_neutral"][k] for k in ("max_nodes_return_error_m", "max_engine_return_error_m", "controls_without_effect_at_1")}
summary["frozen_reference_max_error_m"] = result["frozen_reference"]["max_error_m"]
summary["reopen_without_extension"] = result["reopen_without_extension"]
print("HUMAN_NODES_VALIDATION", json.dumps(summary, ensure_ascii=False))
assert all(verdict.values()), verdict
print("HUMAN_NODES_PASS")
