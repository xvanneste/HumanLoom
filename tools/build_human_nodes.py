"""Génère hors ligne `extension/data/human_nodes.blend` : le groupe de nœuds « HL Human » (schéma 10, lot 1).

Usage (long : plusieurs minutes, à faire une seule fois) :
  blender --background --factory-startup --offline-mode --python tools/build_human_nodes.py -- <sortie.blend> [--tolerance 1e-5] [--report rapport.json]

Principe (prototype `tools/audit/cproto3_1e4.py`, mesures `docs/audit/mesures-noeuds-c.md`) :
- les poids de chacune des clés de forme de `extension/data/realistic.blend` sont compilés en nœuds Math à partir des pilotes
  (expressions de sexe, d'âge et de commandes, avec partage des sous-expressions) ;
- les écarts des clés d'un même contrôle (y compris Atlas14, D-19) sont réduits par SVD en une base locale (une ou plusieurs
  couches de sommets « b<n> » par contrôle) ; seules les couches dont la valeur singulière dépasse `tolerance` x la plus grande
  sont gardées ;
- les clés non pilotées à valeur constante sont incorporées à la forme de base ;
- la sortie du groupe supprime les couches (`Remove Named Attribute`, motif `b*`) pour que la subdivision reste rapide ;
- le fichier contient deux blocs : le groupe `HL Human` et le maillage `HL Human Base` (forme de base + couches). Pas d'objet.
Expressions hors périmètre : yeux, cheveux, relief de peau (modificateur Displace), préréglages."""
import ast
import hashlib
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from extension.proportions import CONTROLS  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:]
OUT = Path(ARGS[0]).resolve()
TOL = float(ARGS[ARGS.index("--tolerance") + 1]) if "--tolerance" in ARGS else 1e-5
REPORT = Path(ARGS[ARGS.index("--report") + 1]).resolve() if "--report" in ARGS else None
GROUP_NAME = "HL Human"
MESH_NAME = "HL Human Base"
VERSION = 1
CONTROL_IDS = [c[0] for c in CONTROLS]
INPUTS = ["sex", "age"] + CONTROL_IDS
OPS = {ast.Add: "ADD", ast.Sub: "SUBTRACT", ast.Mult: "MULTIPLY", ast.Div: "DIVIDE"}

bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(ROOT / "extension/data/realistic.blend"), link=False) as (_, target):
    target.collections = ["Realistic Human Base"]
collection = target.collections[0]
bpy.context.scene.collection.children.link(collection)
body = next(o for o in collection.objects if o.get("human_modeling_body"))
keys = body.data.shape_keys
vertex_count = len(body.data.vertices)


def coords(key):
    values = np.empty(vertex_count * 3, np.float32)
    key.data.foreach_get("co", values)
    return values


base = coords(keys.reference_key)
blocks = [k for k in keys.key_blocks if k != keys.reference_key]
drivers = {d.data_path: d.driver for d in keys.animation_data.drivers}


def token(variable):
    path = variable.targets[0].data_path
    if path.startswith('["hm_'):
        return path[5:-2]
    if path == '["human_modeling_age"]':
        return "age"
    if 'key_blocks["Morphologie"].value' in path:
        return "sex"
    raise ValueError(path)


group = bpy.data.node_groups.new(GROUP_NAME, "GeometryNodeTree")
group.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
group.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
for name in INPUTS:
    socket = group.interface.new_socket(name, in_out="INPUT", socket_type="NodeSocketFloat")
    if name == "sex":
        socket.min_value, socket.max_value, socket.default_value = 0., 1., 0.
    elif name == "age":
        socket.min_value, socket.max_value, socket.default_value = 0., 3., 2.
    else:
        socket.min_value, socket.max_value, socket.default_value = -1., 1., 0.
group_input = group.nodes.new("NodeGroupInput")
group_output = group.nodes.new("NodeGroupOutput")
set_position = group.nodes.new("GeometryNodeSetPosition")
group.links.new(group_input.outputs[0], set_position.inputs["Geometry"])
sockets = {n: group_input.outputs[i + 1] for i, n in enumerate(INPUTS)}
counts = {"math": 0}
cache = {}


def sid(value):
    return value if isinstance(value, (int, float)) else value.node.name + "|" + value.identifier


def make_math(op, a, b=None):
    node = group.nodes.new("ShaderNodeMath")
    node.operation = op
    counts["math"] += 1
    for i, value in enumerate((a, b)):
        if value is None:
            continue
        if isinstance(value, (int, float)):
            node.inputs[i].default_value = float(value)
        else:
            group.links.new(value, node.inputs[i])
    return node.outputs[0]


def math(op, a, b=None):
    """Nœud Math avec partage des sous-expressions identiques (commutativité prise en compte)."""
    key = (op, sid(a), sid(b) if b is not None else None)
    if op in ("ADD", "MULTIPLY", "MAXIMUM", "MINIMUM") and b is not None and str(key[1]) > str(key[2]):
        key = (op, key[2], key[1])
    if key not in cache:
        cache[key] = make_math(op, a, b)
    return cache[key]


def compile_expression(node, env):
    if isinstance(node, ast.Expression):
        return compile_expression(node.body, env)
    if isinstance(node, ast.Constant):
        return float(node.value)
    if isinstance(node, ast.Name):
        return env[node.id]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        value = compile_expression(node.operand, env)
        return -value if isinstance(value, float) else math("MULTIPLY", value, -1.0)
    if isinstance(node, ast.BinOp):
        a, b = compile_expression(node.left, env), compile_expression(node.right, env)
        if isinstance(a, float) and isinstance(b, float):
            return {ast.Add: a + b, ast.Sub: a - b, ast.Mult: a * b, ast.Div: a / b}[type(node.op)]
        return math(OPS[type(node.op)], a, b)
    if isinstance(node, ast.Call):
        name = node.func.id
        args = [compile_expression(a, env) for a in node.args]
        if name == "abs":
            return abs(args[0]) if isinstance(args[0], float) else math("ABSOLUTE", args[0])
        if all(isinstance(a, float) for a in args):
            return max(args) if name == "max" else min(args)
        return math("MAXIMUM" if name == "max" else "MINIMUM", args[0], args[1])
    raise ValueError(str(type(node)))


started = time.perf_counter()
constant_offset = np.zeros(vertex_count * 3, np.float64)
layers_by_control = defaultdict(list)
for key in blocks:
    path = 'key_blocks["' + key.name + '"].value'
    delta = (coords(key) - coords(key.relative_key)).astype(np.float64)
    if key.name == "Morphologie":
        weight = sockets["sex"]
    elif path in drivers:
        driver = drivers[path]
        weight = compile_expression(ast.parse(driver.expression.strip(), mode="eval"), {v.name: sockets[token(v)] for v in driver.variables})
    else:
        constant_offset += float(key.value) * delta
        continue
    if isinstance(weight, float):
        constant_offset += weight * delta
        continue
    if np.abs(delta).max() < 1e-9:
        continue
    weight = math("MINIMUM", math("MAXIMUM", weight, float(key.slider_min)), float(key.slider_max))
    found = re.search(r"HM · ([a-z_0-9]+)", key.name)
    layers_by_control[found.group(1) if found else "other:" + key.name].append((weight, delta))
weights_seconds = time.perf_counter() - started

mesh = body.data.copy()
mesh.name = MESH_NAME
holder = bpy.data.objects.new("_hl_holder", mesh)
bpy.context.scene.collection.objects.link(holder)
holder.shape_key_clear()
mesh.vertices.foreach_set("co", (base.astype(np.float64) + constant_offset).astype(np.float32))
mesh.update()
accumulated = None
layer_count = 0
layer_digests = []
for control, items in layers_by_control.items():
    matrix = np.stack([d for _, d in items])
    left, singular, right = np.linalg.svd(matrix, full_matrices=False)
    rank = int((singular > singular[0] * TOL).sum())
    for j in range(rank):
        sign = 1.0 if right[j][np.argmax(np.abs(right[j]))] >= 0 else -1.0  # SVD sign is arbitrary: fix it for determinism
        layer = (sign * singular[j] * right[j]).astype(np.float32)
        attribute = mesh.attributes.new("b" + str(layer_count), "FLOAT_VECTOR", "POINT")
        attribute.data.foreach_set("vector", layer)
        layer_digests.append(hashlib.sha256(np.round(layer, 7).tobytes()).hexdigest()[:16])
        mix = None
        for i, (weight, _) in enumerate(items):
            coefficient = float(sign * left[i, j])
            if abs(coefficient) < 1e-9:
                continue
            term = math("MULTIPLY", weight, coefficient)
            mix = term if mix is None else math("ADD", mix, term)
        named = group.nodes.new("GeometryNodeInputNamedAttribute")
        named.data_type = "FLOAT_VECTOR"
        named.inputs["Name"].default_value = "b" + str(layer_count)
        scale = group.nodes.new("ShaderNodeVectorMath")
        scale.operation = "SCALE"
        group.links.new(named.outputs["Attribute"], scale.inputs[0])
        group.links.new(mix, scale.inputs[3])
        if accumulated is None:
            accumulated = scale.outputs[0]
        else:
            add = group.nodes.new("ShaderNodeVectorMath")
            add.operation = "ADD"
            group.links.new(accumulated, add.inputs[0])
            group.links.new(scale.outputs[0], add.inputs[1])
            accumulated = add.outputs[0]
        layer_count += 1
group.links.new(accumulated, set_position.inputs["Offset"])
remove = group.nodes.new("GeometryNodeRemoveAttribute")
remove.inputs["Pattern Mode"].default_value = "Wildcard"
remove.inputs["Name"].default_value = "b*"
group.links.new(set_position.outputs["Geometry"], remove.inputs["Geometry"])
group.links.new(remove.outputs["Geometry"], group_output.inputs[0])
bpy.data.objects.remove(holder, do_unlink=True)


def graph_fingerprint(tree):
    """Empreinte logique du graphe : types, opérations, valeurs par défaut non reliées (arrondies) et liens, indépendante des octets du .blend."""
    rows = []
    for node in sorted(tree.nodes, key=lambda n: n.name):
        defaults = []
        for socket in node.inputs:
            if not socket.is_linked and hasattr(socket, "default_value"):
                value = socket.default_value
                if isinstance(value, str):
                    pass
                elif isinstance(value, (int, float)):
                    value = round(float(value), 6)
                else:
                    try:
                        value = [round(float(x), 6) for x in value]
                    except (TypeError, ValueError):
                        value = str(value)
                defaults.append((socket.identifier, value))
        rows.append([node.name, node.bl_idname, getattr(node, "operation", ""), getattr(node, "data_type", ""), defaults])
    links = sorted((l.from_node.name, l.from_socket.identifier, l.to_node.name, l.to_socket.identifier) for l in tree.links)
    interface = [(s.name, s.in_out, s.socket_type, round(getattr(s, "default_value", 0) or 0, 6) if s.socket_type == "NodeSocketFloat" else 0)
                 for s in tree.interface.items_tree]
    return hashlib.sha256(json.dumps([rows, links, interface], default=str, sort_keys=True).encode()).hexdigest()


fingerprint = graph_fingerprint(group)
base_digest = hashlib.sha256(np.round(np.array([v.co[:] for v in mesh.vertices]), 7).tobytes()).hexdigest()
group["hl_version"] = VERSION
group["hl_tolerance"] = TOL
group["hl_graph_fingerprint"] = fingerprint
mesh["hl_version"] = VERSION
group.use_fake_user = True
mesh.use_fake_user = True
OUT.parent.mkdir(parents=True, exist_ok=True)
bpy.data.libraries.write(str(OUT), {group, mesh}, compress=True)
report = {
    "version": VERSION, "tolerance": TOL, "inputs": INPUTS, "keys_total": len(blocks), "control_groups": len(layers_by_control),
    "basis_layers": layer_count, "math_nodes": counts["math"], "total_nodes": len(group.nodes), "links": len(group.links),
    "vertices": vertex_count, "weights_compile_s": round(weights_seconds, 1), "total_s": round(time.perf_counter() - started, 1),
    "graph_fingerprint": fingerprint, "base_digest": base_digest,
    "layers_digest": hashlib.sha256("".join(layer_digests).encode()).hexdigest(), "blend_bytes": OUT.stat().st_size,
}
if REPORT:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
print("HUMAN_NODES_OK", json.dumps(report, ensure_ascii=False))
