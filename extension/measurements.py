"""Measure evaluated geometry and compare stature with a published adult reference."""

from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path

from mathutils import Vector
import numpy as np

from . import anatomy, landmark_sets, human
from .proportions import CONTROLS, NATIVE_CONTROLS


GROUPS = (
    ("20_29", "20–29 ans", ""), ("30_39", "30–39 ans", ""),
    ("40_49", "40–49 ans", ""), ("50_59", "50–59 ans", ""),
    ("60_69", "60–69 ans", ""), ("70_79", "70–79 ans", ""),
    ("80_PLUS", "80 ans et plus", ""),
)
REFERENCE_FILE = Path(__file__).parent / "data" / "references" / "nhanes_stature_2021_2023.json"
LANDMARK_KEY = "hm_measurement_landmark"


@lru_cache(maxsize=1)
def reference_data():
    raw = REFERENCE_FILE.read_bytes()
    data = json.loads(raw.decode("utf-8"))
    data["sha256"] = hashlib.sha256(raw).hexdigest()
    if data["unit"] != "cm" or data["table"] != 7:
        raise ValueError("La référence de stature est invalide.")
    for group in data["groups"].values():
        for percentiles in group.values():
            values = [value for value in percentiles.values() if value is not None]
            if not all(math.isfinite(value) and value > 0 for value in values) or values != sorted(values):
                raise ValueError("Les percentiles de stature sont invalides.")
    return data


def measure(body, context):
    """Return evaluated extents projected onto the object's transformed local axes."""
    evaluated = body.evaluated_get(context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        if not mesh or not mesh.vertices:
            raise ValueError("Le corps ne contient aucun sommet mesurable.")
        coords = np.empty(len(mesh.vertices) * 3, dtype=np.float64)
        mesh.vertices.foreach_get("co", coords)
        coords = coords.reshape((-1, 3))
        if not np.isfinite(coords).all():
            raise ValueError("Le corps contient des coordonnées invalides.")
        matrix = evaluated.matrix_world.to_3x3()
        if not np.isfinite(np.array(matrix)).all():
            raise ValueError("La transformation du corps contient des valeurs invalides.")
        measures = []
        lower_projection = None
        vertical_axis = None
        for direction in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
            axis = matrix @ Vector(direction)
            if axis.length == 0:
                raise ValueError("L’échelle du corps doit être non nulle.")
            axis.normalize()
            projection = np.array(matrix.transposed() @ axis)
            values = coords @ projection
            measures.append(float(np.ptp(values)) * context.scene.unit_settings.scale_length)
            lower_projection = float(values.min()) + evaluated.matrix_world.translation.dot(axis)
            vertical_axis = axis
        result = dict(zip(("width_m", "depth_m", "height_m"), measures))
        if result["height_m"] <= 0:
            raise ValueError("La stature du corps doit être positive.")
        marker = next((obj for obj in body.children if obj.get(LANDMARK_KEY) == "pelvis"), None)
        if marker and marker.get("vertex_count") == len(body.data.vertices):
            position = marker.evaluated_get(context.evaluated_depsgraph_get()).matrix_world.translation
            lower_height = (position.dot(vertical_axis) - lower_projection) * context.scene.unit_settings.scale_length
            result["segments"] = {
                "source": "Manually selected vertex, anatomical placement requires verification",
                "vertex": marker.parent_vertices[0],
                "below_landmark_m": lower_height,
                "above_landmark_m": result["height_m"] - lower_height,
                "lower_fraction": lower_height / result["height_m"],
            }
        return result
    finally:
        evaluated.to_mesh_clear()


def target(body):
    data = reference_data()
    try:
        return data["groups"][body.hm_reference_group][body.hm_reference_sex][body.hm_reference_percentile]
    except KeyError as error:
        raise ValueError("La sélection de référence est invalide.") from error


def report(body, context):
    from . import age_shapes
    data = reference_data()
    geometry = measure(body, context)
    expected_cm = target(body)
    return {
        "format": "human_modeling.measurement_report",
        "version": 2,
        "character": body.name,
        "model": {
            "base": body.data.get("human_modeling_base"),
            "schema": body.humanloom.schema_version if human.is_native(body) else body.data.get("human_modeling_schema"),
            "age_reference": age_shapes.metadata(body),
            "surface_revision": body.data.get("human_modeling_surface_revision", 0),
            "topology_sha256": landmark_sets.topology(body),
            "morphology": human.get_value(body, "sex"),
            "controls": (
                {name: human.get_value(body, name) for name, _ in NATIVE_CONTROLS} if human.is_native(body)
                else {name: body.data.shape_keys[name] for name in body.data.shape_keys.keys() if name.startswith("hm_")}
            ),
            "matrix_world": [list(row) for row in body.matrix_world],
            "scene_unit_scale_m": context.scene.unit_settings.scale_length,
        },
        "measurement": geometry,
        "local_anatomy": anatomy.local_report(body, context),
        "local_anatomy_scope": "Manually placed surface landmarks. Mesh sections are not tape measurements; no age norms assigned.",
        "protocol_sources": {
            "facial_landmark_definitions": "https://www.facebase.org/resources/human/facial_norms/notes/",
            "waist_protocol_to_match_before_population_comparison": "https://stacks.cdc.gov/view/cdc/127207",
        },
        "method": "Evaluated body projected onto transformed local axes, scene unit scale included",
        "reference": {
            "id": data["id"],
            "population": data["population"],
            "source_url": data["source_url"],
            "doi": data["doi"],
            "sha256": data["sha256"],
            "survey_period": data["survey_period"],
            "table": data["table"],
            "printed_page": data["printed_page"],
            "group": body.hm_reference_group,
            "sex": body.hm_reference_sex,
            "percentile": body.hm_reference_percentile,
            "height_cm": expected_cm,
        },
        "height_difference_cm": None if expected_cm is None else geometry["height_m"] * 100 - expected_cm,
        "scope": "Stature comparison. Regional anatomy and age morphology require separate calibration.",
    }
