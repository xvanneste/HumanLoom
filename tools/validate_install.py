"""Test d'installation isolée : construit le zip de l'extension, l'installe dans un dossier utilisateur Blender temporaire
(BLENDER_USER_RESOURCES : ni la session ni la configuration de l'utilisateur ne sont touchées), puis démarre Blender avec
l'extension activée comme au démarrage normal (`bpy.data` restreint pendant l'enregistrement) et crée un humain.

Usage (Python ordinaire, pas Blender) : python tools/validate_install.py <dossier_de_travail>
Vérifie : l'enregistrement réussit, la façade existe, un humain natif se crée (schéma 10), l'ancien moteur n'est plus créable,
l'asset de l'ancien moteur n'est pas dans le paquet."""
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLENDER = os.environ.get("BLENDER", r"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe")
work = Path(sys.argv[1]).resolve()
shutil.rmtree(work, ignore_errors=True)
(work / "build").mkdir(parents=True)
(work / "res").mkdir()
env = dict(os.environ, BLENDER_USER_RESOURCES=str(work / "res"))
common = [BLENDER, "--background", "--factory-startup", "--offline-mode"]

subprocess.run(common + ["--command", "extension", "build", "--output-dir", str(work / "build")], cwd=ROOT / "extension", check=True,
               capture_output=True, text=True, timeout=600)
package = next((work / "build").glob("*.zip"))
names = zipfile.ZipFile(package).namelist()
assert not any(n.endswith("realistic.blend") for n in names), "l'asset de l'ancien moteur est dans le paquet"
assert any(n.endswith("human_nodes.blend") for n in names) and any(n.endswith("human_eyes.blend") for n in names) and any(n.endswith("human_sockets.json") for n in names)
subprocess.run(common + ["--command", "extension", "install-file", "-r", "user_default", "--enable", str(package)], env=env, check=True,
               capture_output=True, text=True, timeout=600)

probe = work / "probe.py"
probe.write_text('''
import bpy
assert hasattr(bpy.types.Object, "humanloom"), "façade absente : l'enregistrement a échoué"
assert bpy.ops.humanloom.create() == {"FINISHED"}
body = bpy.context.object
assert body.humanloom.schema_version == 10 and body.humanloom.eye_left is not None
assert not bpy.ops.human_modeling.create.poll(), "l'ancien moteur est encore créable"
body.humanloom.age = 3.0
bpy.context.view_layer.update()
mesh = body.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
assert len(mesh.vertices) >= 10582  # la surface lissée (Subsurf) s'ajoute à la cage de 10 582 sommets
print("INSTALL_OK", len(mesh.vertices))
''', encoding="utf-8")
# Sans --factory-startup : les préférences isolées (extension activée par install-file) sont lues comme au démarrage réel.
run = subprocess.run([BLENDER, "--background", "--offline-mode", "--python-exit-code", "1", "--python", str(probe)], env=env, capture_output=True, text=True, timeout=600)
print(run.stdout[-1500:], run.stderr[-800:])
assert run.returncode == 0 and "INSTALL_OK" in run.stdout, "installation isolée en échec"
print("VALIDATE_INSTALL_PASS", package.stat().st_size, "octets")
