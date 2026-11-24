"""Animations DÉRIVÉES (lot L5) : de nouvelles animations obtenues en COMBINANT des clips existants (aucune donnée de mouvement inventée) et étiquetées « dérivée » ; boucles sans raccord.

Méthode : calques par groupes d'os. Le clip de BASE donne tout ; pour les os d'un groupe (bras droit, haut du corps…), la rotation est remplacée par celle du clip de SUPERPOSITION, soit tenue sur une image
(« figée » : par exemple le bras qui tient un parapluie pris sur un clip « bras levés »), soit jouée en boucle étirée sur la durée de la base (« étirée »), avec un fondu aux limites du groupe (le tronc suit le
mouvement de la base). Le résultat est un `retarget.Motion` / une action de NOS os ; il est étiqueté (propriété `hl_derived` de l'action : base, superposition, groupes, mode, boucle).

Exemples : marche + bras tenu = « marche avec parapluie » ; attente + gestes d'un clip de conversation = « discussion » ; téléphone : un clip où la main est près de l'oreille, sur le bras voulu.
Les boucles : fondu enchaîné de la fin sur le début (rotations par slerp) ; le raccord est mesuré (`loop_seam`)."""
import json

import numpy as np

LABEL = "dérivée"


# --- groupes d'os -------------------------------------------------------------------------------------------------------------------------------
def bone_group(names, group):
    """Indices des os de `names` du groupe : « bras.L », « bras.R », « doigts.L », « doigts.R », « tete », « buste » (colonne, cou, tête, clavicules), « haut_du_corps » (tout sauf bassin, jambes et racine), « jambes »."""
    out = []
    for i, name in enumerate(names):
        side = name[-2:] if name[-2:] in (".L", ".R") else ""
        base = name[:-2] if side else name
        arm = base.startswith(("arm_", "hand")) or base.startswith(("clavicle",))
        finger = base.startswith(("thumb", "index", "middle", "ring", "pinky"))
        leg = base.startswith(("leg_", "foot", "toe", "ball"))
        axis = base.startswith(("spine", "neck", "head"))
        if group in ("bras.L", "bras.R") and arm and side == group[-2:]:
            out.append(i)
        elif group in ("doigts.L", "doigts.R") and finger and side == group[-2:]:
            out.append(i)
        elif group == "tete" and base.startswith(("neck", "head")):
            out.append(i)
        elif group == "buste" and (axis or base.startswith("clavicle")):
            out.append(i)
        elif group == "haut_du_corps" and (axis or arm or finger):
            out.append(i)
        elif group == "jambes" and leg:
            out.append(i)
    return out


GROUPS = ("bras.L", "bras.R", "doigts.L", "doigts.R", "tete", "buste", "haut_du_corps", "jambes")


# --- quaternions (wxyz) -------------------------------------------------------------------------------------------------------------------------
def slerp(a, b, t):
    """Interpolation sphérique entre rotations `a` et `b` (..., 4) ; `t` diffusable (...,)."""
    a = a / np.linalg.norm(a, axis=-1, keepdims=True)
    b = b / np.linalg.norm(b, axis=-1, keepdims=True)
    dot = np.sum(a * b, axis=-1, keepdims=True)
    b = np.where(dot < 0, -b, b)
    dot = np.abs(dot)
    t = np.asarray(t, float)[..., None]
    theta = np.arccos(np.clip(dot, -1.0, 1.0))
    sin = np.sin(theta)
    small = sin < 1e-6
    wa = np.where(small, 1.0 - t, np.sin((1.0 - t) * theta) / np.where(small, 1.0, sin))
    wb = np.where(small, t, np.sin(t * theta) / np.where(small, 1.0, sin))
    out = wa * a + wb * b
    return out / np.linalg.norm(out, axis=-1, keepdims=True)


def angle_between(a, b):
    """Angle (degrés) entre deux rotations (..., 4)."""
    return np.degrees(2 * np.arccos(np.clip(np.abs(np.sum(a * b, axis=-1) / (np.linalg.norm(a, axis=-1) * np.linalg.norm(b, axis=-1))), 0, 1)))


# --- clips -------------------------------------------------------------------------------------------------------------------------------------------
def resample(quat, frames):
    """Étire ou comprime (F, N, 4) à `frames` images (interpolation sphérique)."""
    count = quat.shape[0]
    if count == frames:
        return quat.copy()
    position = np.linspace(0.0, count - 1.0, frames)
    low = np.floor(position).astype(int)
    high = np.minimum(low + 1, count - 1)
    return slerp(quat[low], quat[high], (position - low)[:, None])


def layer(base, overlay, groups, mode="etiree", hold_frame=0, feather=8):
    """Clip dérivé : os des `groups` pris sur `overlay`, tout le reste sur `base`. `mode` : « etiree » (la superposition jouée sur la durée de la base) ou « figee » (image `hold_frame` tenue). Les os du groupe qui
    ne sont pas des extrémités reçoivent un fondu de `feather` images au début et à la fin SEULEMENT si la base n'est pas une boucle ; ici la superposition est constante ou étirée : pas de fondu temporel.
    Retourne (quat, loc) du clip dérivé. Les os absents de la superposition restent ceux de la base."""
    names = base["names"]
    quat = base["quat"].copy()
    loc = base["loc"].copy()
    frames = quat.shape[0]
    indices = sorted({i for g in groups for i in bone_group(names, g)})
    if not indices:
        raise ValueError("Aucun os dans les groupes demandés : %r" % (groups,))
    if mode == "figee":
        pose = overlay["quat"][min(max(hold_frame, 0), overlay["quat"].shape[0] - 1)]
        quat[:, indices] = pose[indices][None]
    elif mode == "etiree":
        quat[:, indices] = resample(overlay["quat"], frames)[:, indices]
    else:
        raise ValueError("Mode inconnu : %r" % (mode,))
    return quat, loc


def make_loop(quat, loc, blend=8):
    """Boucle sans raccord : longueur L = F − blend ; les `blend` premières images sont un fondu (slerp) de la suite naturelle (images L…F−1) vers le début. Le bassin (translation) est fondu linéairement."""
    frames = quat.shape[0]
    blend = int(min(max(blend, 1), frames // 2))
    length = frames - blend
    out_q, out_l = quat[:length].copy(), loc[:length].copy()
    t = (np.arange(blend) + 1.0) / (blend + 1.0)
    out_q[:blend] = slerp(quat[length:length + blend], quat[:blend], t[:, None])
    out_l[:blend] = (1 - t)[:, None, None] * loc[length:length + blend] + t[:, None, None] * loc[:blend]
    return out_q, out_l


def loop_seam(quat):
    """Raccord d'une boucle : plus grand saut entre la dernière et la première image, rapporté au pas médian entre images consécutives (1 = aussi lisse que le reste du clip ; > 3 : raccord visible)."""
    step = angle_between(quat[1:], quat[:-1]).max(axis=-1)
    seam = float(angle_between(quat[0], quat[-1]).max())
    return seam / max(float(np.median(step)), 1e-6), seam


def label(info):
    return json.dumps(info, ensure_ascii=False)


# --- pont Blender ------------------------------------------------------------------------------------------------------------------------------------
def derive_action(rig_object, base_action, overlay_action, groups, mode="etiree", hold_frame=0, loop=True, blend=8, name=None):
    """Action dérivée pour le rig `rig_object` (nos os) à partir de deux actions de nos os (déjà re-ciblées). L'action créée est étiquetée (`hl_derived`, `hl_label` = « dérivée »). Retourne l'action."""
    from . import retarget, retarget_bpy
    rig = retarget.rig_from_armature(rig_object)
    base_motion, first = retarget_bpy.read_action(base_action, rig)
    overlay_motion, _ = retarget_bpy.read_action(overlay_action, rig)
    quat, loc = layer({"names": rig.names, "quat": base_motion.quat, "loc": base_motion.loc}, {"quat": overlay_motion.quat}, groups, mode, hold_frame)
    seam_before, jump_before = loop_seam(quat)
    applied = 0
    if loop and seam_before > 1.5:  # un clip déjà bouclé n'est pas dégradé par un fondu
        quat, loc = make_loop(quat, loc, blend)
        applied = int(blend)
    elif loop and jump_before < 0.01:  # première et dernière images identiques : on retire le doublon (sinon une image figée à chaque tour)
        quat, loc = quat[:-1], loc[:-1]
    seam_after = loop_seam(quat)[0]
    result = retarget.Result(quat, loc, {"noms_cibles": list(rig.names)})
    title = name or f"{base_action.name} + {overlay_action.name} ({LABEL})"
    action = retarget_bpy.write_action(rig_object, result, title, first_frame=first)
    info = {"base": base_action.name, "superposition": overlay_action.name, "groupes": list(groups), "mode": mode, "image_figee": int(hold_frame), "boucle": bool(loop), "fondu_images": applied,
            "raccord_avant": round(seam_before, 2), "raccord_apres": round(seam_after, 2)}
    action["hl_derived"] = label(info)
    action["hl_label"] = LABEL
    return action


def derived_actions():
    import bpy
    return [a for a in bpy.data.actions if a.get("hl_label") == LABEL]
