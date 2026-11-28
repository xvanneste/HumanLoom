"""Validation du compilateur d'expressions de `tools/build_human_nodes.py` (SCI-004), sans exécuter le constructeur : la fonction `compile_expression` est extraite du fichier par son arbre syntaxique et exécutée avec un `math` factice qui consigne les nœuds.

  python tools/validate_expression_compiler.py   (Python ordinaire)
E1 table d'expressions constantes (dont opérandes nuls : a + 0, a - 0, a * 0 ne divisent plus) ; E2 division par zéro, opérateur et fonction inconnus, arité invalide REFUSÉS ; E3 expressions avec variable : nœuds attendus."""
import ast
import json
import operator
from pathlib import Path
import sys

source = (Path(__file__).resolve().parent / "build_human_nodes.py").read_text(encoding="utf-8")
tree = ast.parse(source)
wanted = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name == "compile_expression") or (isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "CONSTANT_FOLDS" for t in n.targets))]
assert len(wanted) == 2, "compile_expression ou CONSTANT_FOLDS introuvable"
nodes = []


def fake_math(op, a, b=None):
    nodes.append((op, a, b))
    return ("noeud", op, a, b)


namespace = {"ast": ast, "operator": operator, "math": fake_math, "OPS": {ast.Add: "ADD", ast.Sub: "SUBTRACT", ast.Mult: "MULTIPLY", ast.Div: "DIVIDE"}}
exec(compile(ast.Module(body=wanted, type_ignores=[]), "build_human_nodes.py", "exec"), namespace)
compile_expression = namespace["compile_expression"]
failures = []


def run(text, env=None):
    return compile_expression(ast.parse(text, mode="eval"), env or {})


table = {"2 + 0": 2.0, "2 - 0": 2.0, "2 * 0": 0.0, "0 + 0": 0.0, "6 / 3": 2.0, "abs(-3)": 3.0, "max(1, 4)": 4.0, "min(1, 4)": 1.0, "-(2 + 3)": -5.0}
rows = {}
for text, expected in table.items():
    try:
        value = run(text)
        rows[text] = value
        if value != expected:
            failures.append(text)
    except Exception as error:  # noqa: BLE001
        rows[text] = repr(error)
        failures.append(text)
refused = {}
for text in ("1 / 0", "3 + 1 / 0", "2 ** 3", "sqrt(4)", "max(1, 2, 3)", "abs(1, 2)", "min(1)"):
    try:
        run(text)
        refused[text] = "ACCEPTÉ"
        failures.append("refus:" + text)
    except ValueError:
        refused[text] = "refusé"
    except Exception as error:  # noqa: BLE001
        refused[text] = "autre erreur : " + type(error).__name__
        failures.append("refus:" + text)
variable = run("x + 0", {"x": ("variable",)})
check_nodes = variable == ("noeud", "ADD", ("variable",), 0.0)
if not check_nodes:
    failures.append("variable")
print(("OK  " if not failures else "KO  ") + "E1_E2_E3_compilateur_d_expressions", json.dumps({"constantes": rows, "refus": refused, "noeud_variable": check_nodes}, ensure_ascii=False))
print("RESULT", "PASS" if not failures else "FAIL " + ", ".join(failures))
sys.exit(1 if failures else 0)
