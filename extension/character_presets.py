"""Portable modeling settings with validation before scene mutation."""

import json
import math
import os
import tempfile
from pathlib import Path

from .proportions import BASE_ID, CONTROLS, property_name
from . import landmark_sets, measurements


FORMAT = "human_modeling.character"
VERSION = 1


def number(value, label, lower=None, upper=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} doit être un nombre fini.")
    try:
        value = float(value)
    except OverflowError as error:
        raise ValueError(f"{label} doit être un nombre fini.") from error
    if not math.isfinite(value):
        raise ValueError(f"{label} doit être un nombre fini.")
    if lower is not None and not lower <= value <= upper:
        raise ValueError(f"{label} doit être compris entre {lower} et {upper}.")
    return value


def validate(payload):
    if not isinstance(payload, dict) or payload.get("format") != FORMAT:
        raise ValueError("Ce fichier ne contient pas un préréglage Human Modeling.")
    if type(payload.get("version")) is not int or payload["version"] != VERSION:
        raise ValueError("Cette version de préréglage n’est pas prise en charge.")
    if payload.get("base") != BASE_ID:
        raise ValueError("Ce préréglage utilise une autre base de personnage.")
    controls = payload.get("controls")
    if not isinstance(controls, dict):
        raise ValueError("Les réglages du préréglage sont absents ou invalides.")
    known = {identifier for identifier, _ in CONTROLS}
    unknown = set(controls) - known
    if unknown:
        raise ValueError("Réglages inconnus dans le préréglage " + ", ".join(sorted(unknown)))
    scale = payload.get("scale")
    if not isinstance(scale, list) or len(scale) != 3:
        raise ValueError("L’échelle du personnage doit contenir trois valeurs.")
    reference = payload.get("measurement_reference")
    if reference is not None:
        data = measurements.reference_data()
        if (
            not isinstance(reference, dict) or reference.get("id") != data["id"]
            or not all(isinstance(reference.get(key), str) for key in ("group", "sex", "percentile"))
            or reference.get("group") not in data["groups"]
            or reference.get("sex") not in ("M", "F")
            or reference.get("percentile") not in ("P05", "P50", "P95")
        ):
            raise ValueError("La référence de mesure du préréglage est invalide.")
        reference = {key: reference[key] for key in ("id", "group", "sex", "percentile")}
    return {
        "format": FORMAT,
        "version": VERSION,
        "base": BASE_ID,
        "morphology": number(payload.get("morphology"), "La morphologie", 0, 1),
        "age_stage": number(payload.get("age_stage", 2.0), "La transition d’âge", 0, 3),
        "controls": {
            identifier: number(controls.get(identifier, 0.0), label, -1, 1)
            for identifier, label in CONTROLS
        },
        "scale": [number(value, "L’échelle") for value in scale],
        "measurement_reference": reference,
        "landmarks": landmark_sets.validate(payload["landmarks"]) if payload.get("landmarks") is not None else None,
    }


def capture(body):
    keys = body.data.shape_keys
    return validate({
        "format": FORMAT,
        "version": VERSION,
        "base": body.data.get("human_modeling_base", BASE_ID),
        "morphology": keys.key_blocks["Morphologie"].value,
        "age_stage": keys.get("human_modeling_age", 2.0),
        "controls": {
            identifier: keys.get(property_name(identifier), 0.0) for identifier, _ in CONTROLS
        },
        "scale": list(body.scale),
        "measurement_reference": {
            "id": measurements.reference_data()["id"],
            "group": body.hm_reference_group,
            "sex": body.hm_reference_sex,
            "percentile": body.hm_reference_percentile,
        },
        "landmarks": landmark_sets.capture(body) if any(obj.get("hm_measurement_landmark") for obj in body.children) else None,
    })


def assign(body, state):
    keys = body.data.shape_keys
    for identifier, value in state["controls"].items():
        prop = property_name(identifier)
        if prop in keys:
            keys[prop] = value
    keys.key_blocks["Morphologie"].value = state["morphology"]
    if "human_modeling_age" in keys:
        keys["human_modeling_age"] = state["age_stage"]
    body.scale = state["scale"]
    reference = state.get("measurement_reference")
    if reference:
        body.hm_reference_group = reference["group"]
        body.hm_reference_sex = reference["sex"]
        body.hm_reference_percentile = reference["percentile"]
    keys.update_tag()
    if state.get("landmarks") is not None:
        landmark_sets.apply(body, state["landmarks"])


def apply(body, payload, factor=1.0):
    requested = validate(payload)
    factor = number(factor, "L’intensité", 0, 1)
    if not body.is_editable or not body.data.shape_keys.is_editable:
        raise ValueError("Le personnage et ses clés de forme doivent être éditables.")
    keys = body.data.shape_keys
    missing = [
        identifier for identifier, value in requested["controls"].items()
        if property_name(identifier) not in keys and value != 0
    ]
    if missing:
        raise ValueError("Ajoutez d’abord les derniers réglages corps et visage à ce personnage.")
    if requested["age_stage"] != 2.0 and "human_modeling_age" not in keys:
        raise ValueError("Ajoutez d’abord les formes d’âge à ce personnage.")
    if factor == 1 and requested.get("landmarks") is not None:
        landmark_sets.check_compatible(body, requested["landmarks"])
    previous = capture(body)
    combined = {
        **requested,
        "morphology": previous["morphology"] * (1 - factor) + requested["morphology"] * factor,
        "age_stage": previous["age_stage"] * (1 - factor) + requested["age_stage"] * factor,
        "controls": {
            identifier: previous["controls"][identifier] * (1 - factor) + value * factor
            for identifier, value in requested["controls"].items()
        },
        "scale": [old * (1 - factor) + new * factor for old, new in zip(previous["scale"], requested["scale"])],
        "measurement_reference": (
            requested["measurement_reference"] if factor == 1 and requested["measurement_reference"]
            else previous["measurement_reference"]
        ),
        "landmarks": requested["landmarks"] if factor == 1 and requested["landmarks"] is not None else None,
    }
    with landmark_sets.transaction(body):
        try:
            assign(body, combined)
        except Exception:
            assign(body, previous)
            raise


def write(path, payload):
    write_json(path, validate(payload))


def write_json(path, payload):
    destination = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=destination.parent, suffix=".tmp", delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump(payload, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def read(path):
    with open(path, encoding="utf-8") as stream:
        return validate(json.load(stream))
