"""Retargeting analytique (lot A3) : convertit une animation d'un squelette SOURCE en animation de NOS os, par le calcul (numpy), sans contraintes ni bake.

Le cœur ne dépend pas de bpy. Conventions : toutes les matrices sont en espace de l'armature, colonnes (M @ v) ; une pose d'os = `Base` (translation puis rotation
dans le repère local de l'os, relatives au repos), comme les canaux `location` / `rotation_quaternion` de Blender.

Algorithme (voir CONCEPTION_A3.md §2) :
  1. cinématique directe de la source sur toutes les images (vectorisée) ;
  2. delta monde par os source : `Δ = P_pose · R_repos⁻¹` ;
  3. orientation cible : `P_cible = Δ · G · R_repos_cible`, où `G` est la rotation d'arc minimal qui amène la direction de chaîne cible sur celle de la source
     (mode « absolu ») ou l'identité (mode « delta ») ;
  4. os cibles sans source : base identité ; repassage en local par la chaîne cible ; translation du bassin mise à l'échelle par le rapport des hauteurs de bassin ;
  5. gestionnaire de root motion : sur place / conserver / extraire vers `root` (translation horizontale).
"""
from dataclasses import dataclass, field
import hashlib
import json

import numpy as np

ABSOLUTE, DELTA, ABSOLUTE_IK = "absolu", "delta", "absolu_ik"  # absolu_ik : absolu + compensation de la longueur des membres (IK à 2 os, voir `limb_ik`)
IN_PLACE, KEEP, EXTRACT = "sur_place", "conserver", "extraire"


@dataclass
class Rig:
    """Repos d'un squelette : noms, parents (-1 : racine), matrices de repos en espace de l'armature (N, 4, 4)."""
    names: list
    parents: list
    rest: np.ndarray
    index: dict = field(default_factory=dict, repr=False)

    def __post_init__(self):
        self.rest = np.asarray(self.rest, float)
        self.index = {n: i for i, n in enumerate(self.names)}
        for i, p in enumerate(self.parents):
            assert p < i, "les parents doivent précéder leurs enfants"

    def local_rest(self):
        local = self.rest.copy()
        for i, p in enumerate(self.parents):
            if p >= 0:
                local[i] = np.linalg.inv(self.rest[p]) @ self.rest[i]
        return local

    def head(self, name):
        return self.rest[self.index[name]][:3, 3]


@dataclass
class Motion:
    """Animation échantillonnée : `loc` (F, N, 3) et `quat` (F, N, 4, wxyz) par os de la source (identité si le canal manque)."""
    loc: np.ndarray
    quat: np.ndarray
    fps: float = 30.0

    @property
    def frames(self):
        return self.loc.shape[0]


@dataclass
class Options:
    pose_mode: str = ABSOLUTE_IK
    root_motion: str = KEEP
    translation_scale: float = None   # None : rapport des hauteurs de bassin (automatique)
    ik_limbs: tuple = ("leg",)  # membres corrigés par l'IK en mode absolu+IK : défaut « jambes seules » (validé à l'œil le 2026-11-24) ; ajouter « arm » pour les contacts mains-objets
    clavicle_scale: float = 1.0       # facteur sur la rotation (monde) des CLAVICULES par rapport au repos : 1 = fidèle à la source ; < 1 réduit le haussement d'épaule (moins de plis du cou et du trapèze) ; l'orientation du bras et de tous les autres os est CONSERVÉE (positions relatives à la racine du membre inchangées, mesuré 0,00 mm sur 30 actions)
    limb_blend: float = 0.0           # mode absolu+IK : 0 = la main/le pied vise la position de la source mise à l'échelle du BASSIN ; 1 = à l'échelle de la LONGUEUR DU MEMBRE (rapport des longueurs de segments), depuis l'épaule/la hanche


@dataclass
class Result:
    quat: np.ndarray                  # (F, N_cible, 4) rotations de base par os cible
    loc: np.ndarray                   # (F, N_cible, 3) translations de base (non nulles : bassin et root)
    report: dict


# --- algèbre -----------------------------------------------------------------------------------------------------------------------------------------

def quat_to_matrix(q):
    """(..., 4) wxyz → (..., 3, 3)."""
    q = q / np.linalg.norm(q, axis=-1, keepdims=True)
    w, x, y, z = q[..., 0], q[..., 1], q[..., 2], q[..., 3]
    return np.stack([
        np.stack([1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], -1),
        np.stack([2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)], -1),
        np.stack([2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)], -1)], -2)


def matrix_to_quat(m):
    """(..., 3, 3) → (..., 4) wxyz, calcul stable (branche selon la plus grande composante)."""
    m = np.asarray(m, float)
    shape = m.shape[:-2]
    m = m.reshape(-1, 3, 3)
    trace = m[:, 0, 0] + m[:, 1, 1] + m[:, 2, 2]
    q = np.empty((len(m), 4))
    a = trace > 0
    s = np.sqrt(np.maximum(trace[a] + 1.0, 1e-18)) * 2
    q[a] = np.stack([0.25 * s, (m[a, 2, 1] - m[a, 1, 2]) / s, (m[a, 0, 2] - m[a, 2, 0]) / s, (m[a, 1, 0] - m[a, 0, 1]) / s], -1)
    for axis in range(3):
        i, j, k = axis, (axis + 1) % 3, (axis + 2) % 3
        b = ~a & (m[:, i, i] >= m[:, j, j]) & (m[:, i, i] >= m[:, k, k])
        a = a | b
        s = np.sqrt(np.maximum(1.0 + m[b, i, i] - m[b, j, j] - m[b, k, k], 1e-18)) * 2
        out = np.empty((b.sum(), 4))
        out[:, 0] = (m[b, k, j] - m[b, j, k]) / s
        out[:, 1 + i] = 0.25 * s
        out[:, 1 + j] = (m[b, j, i] + m[b, i, j]) / s
        out[:, 1 + k] = (m[b, k, i] + m[b, i, k]) / s
        q[b] = out
    q /= np.linalg.norm(q, axis=-1, keepdims=True)
    return q.reshape(shape + (4,))


def continuous(q):
    """Rend les quaternions (F, ..., 4) continus dans le temps (signe)."""
    q = q.copy()
    for f in range(1, len(q)):
        flip = (q[f] * q[f - 1]).sum(-1) < 0
        q[f][flip] *= -1
    return q


def arc_rotation(a, b):
    """Rotation 3×3 d'arc minimal qui amène le vecteur a sur le vecteur b."""
    a, b = a / (np.linalg.norm(a) + 1e-18), b / (np.linalg.norm(b) + 1e-18)
    v, c = np.cross(a, b), float(a @ b)
    if c < -0.999999:
        axis = np.cross(a, [1, 0, 0] if abs(a[0]) < 0.9 else [0, 1, 0])
        axis /= np.linalg.norm(axis)
        return 2 * np.outer(axis, axis) - np.eye(3)
    k = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + k + k @ k / (1 + c)


def arc_rotations(a, b):
    """Rotations 3×3 d'arc minimal (F, 3, 3) qui amènent chaque vecteur a[f] sur b[f]."""
    a = a / (np.linalg.norm(a, axis=-1, keepdims=True) + 1e-18)
    b = b / (np.linalg.norm(b, axis=-1, keepdims=True) + 1e-18)
    v = np.cross(a, b)
    c = (a * b).sum(-1)
    k = np.zeros(a.shape[:1] + (3, 3))
    k[:, 0, 1], k[:, 0, 2], k[:, 1, 0], k[:, 1, 2], k[:, 2, 0], k[:, 2, 1] = -v[:, 2], v[:, 1], v[:, 2], -v[:, 0], -v[:, 1], v[:, 0]
    out = np.eye(3)[None] + k + np.einsum("fij,fjk->fik", k, k) / (1 + c)[:, None, None]
    opposite = c < -0.999999
    for f in np.nonzero(opposite)[0]:
        out[f] = arc_rotation(a[f], b[f])
    return out


def basis_matrix(loc, quat):
    """(F, 3), (F, 4) → (F, 4, 4)."""
    m = np.zeros((len(loc), 4, 4))
    m[:, :3, :3] = quat_to_matrix(quat)
    m[:, :3, 3] = loc
    m[:, 3, 3] = 1
    return m


def forward_kinematics(rig, loc, quat):
    """Matrices monde (F, N, 4, 4) de toutes les os pour des bases (loc (F,N,3), quat (F,N,4))."""
    local = rig.local_rest()
    frames = loc.shape[0]
    world = np.zeros((frames, len(rig.names), 4, 4))
    for i, p in enumerate(rig.parents):
        pose = local[i][None] @ basis_matrix(loc[:, i], quat[:, i])
        world[:, i] = pose if p < 0 else world[:, p] @ pose
    return world


def world_to_basis(rig, rotations, positions=None):
    """Bases locales (loc, quat) d'un squelette dont on connaît les orientations monde `rotations` (F, N, 3, 3) ; `positions` (F, N, 3 ou None) impose la position monde
    de certains os (NaN = non imposée) : sert au bassin et à `root`. Retourne (loc, quat, world)."""
    local = rig.local_rest()
    frames, count = rotations.shape[0], len(rig.names)
    loc = np.zeros((frames, count, 3))
    quat = np.zeros((frames, count, 4))
    quat[..., 0] = 1
    world = np.zeros((frames, count, 4, 4))
    world[..., 3, 3] = 1
    for i, p in enumerate(rig.parents):
        parent_world = world[:, p] if p >= 0 else np.tile(np.eye(4), (frames, 1, 1))
        rest_rot, rest_trans = local[i][:3, :3], local[i][:3, 3]
        rot_p = parent_world[:, :3, :3]
        basis_rot = np.einsum("ij,fjk,fkl->fil", rest_rot.T, np.swapaxes(rot_p, 1, 2), rotations[:, i])
        quat[:, i] = matrix_to_quat(basis_rot)
        if positions is not None and not np.isnan(positions[:, i]).any():
            desired = positions[:, i]
            loc[:, i] = np.einsum("ij,fj->fi", rest_rot.T, np.einsum("fji,fj->fi", rot_p, desired - parent_world[:, :3, 3]) - rest_trans)
        pose = np.zeros((frames, 4, 4))
        pose[:, :3, :3] = np.einsum("ij,fjk->fik", rest_rot, quat_to_matrix(quat[:, i]))
        pose[:, :3, 3] = rest_trans + np.einsum("ij,fj->fi", rest_rot, loc[:, i])
        pose[:, 3, 3] = 1
        world[:, i] = parent_world @ pose
    return loc, quat, world


def rig_from_armature(armature):
    """`Rig` d'une armature Blender (ou de ses données) : repos en espace de l'armature, parents avant enfants."""
    data = getattr(armature, "data", armature)
    bones = sorted(data.bones, key=lambda b: len(b.parent_recursive))
    index = {b.name: i for i, b in enumerate(bones)}
    return Rig([b.name for b in bones], [index[b.parent.name] if b.parent else -1 for b in bones], np.array([np.array(b.matrix_local) for b in bones]))


# --- retargeting --------------------------------------------------------------------------------------------------------------------------------------

def chain_direction(rig, name, children_of, mapped_heads):
    """Direction de chaîne d'un os du rig (de sa tête vers la tête de son enfant principal apparié) ou None."""
    child = children_of.get(name)
    if child is None or child not in mapped_heads:
        return None
    return mapped_heads[child] - rig.head(name)


def scale_rotation(R, s):
    """Matrices de rotation `R` (..., 3, 3) mises à l'échelle `s` en angle (même axe) : formule de Rodrigues ; `s = 1` rend `R`, `s = 0` l'identité. Valable hors angles proches de π (clavicules : quelques dizaines de degrés)."""
    R = np.asarray(R, float)
    cos = np.clip((np.trace(R, axis1=-2, axis2=-1) - 1.0) / 2.0, -1.0, 1.0)
    angle = np.arccos(cos)
    axis = np.stack([R[..., 2, 1] - R[..., 1, 2], R[..., 0, 2] - R[..., 2, 0], R[..., 1, 0] - R[..., 0, 1]], axis=-1)
    norm = np.linalg.norm(axis, axis=-1, keepdims=True)
    axis = np.where(norm > 1e-9, axis / np.maximum(norm, 1e-12), 0.0)
    a = (angle * s)[..., None, None]
    K = np.zeros(R.shape)
    K[..., 0, 1], K[..., 0, 2], K[..., 1, 0], K[..., 1, 2], K[..., 2, 0], K[..., 2, 1] = -axis[..., 2], axis[..., 1], axis[..., 2], -axis[..., 0], -axis[..., 1], axis[..., 0]
    return np.eye(3) + np.sin(a) * K + (1.0 - np.cos(a)) * (K @ K)


def retarget(source, target, mapping, motion, options=None, main_child=None):
    """Retourne un `Result`. `mapping` : {os cible: os source}. `main_child` : {os cible: enfant cible principal} (pour la direction de chaîne) ; déduit si absent."""
    options = options or Options()
    frames = motion.frames
    s_world = forward_kinematics(source, motion.loc, motion.quat)
    s_rest_rot = source.rest[:, :3, :3]
    delta = {}
    for t_name, s_name in mapping.items():
        s = source.index[s_name]
        delta[t_name] = np.einsum("fij,jk->fik", s_world[:, s, :3, :3], s_rest_rot[s].T)
    t_local_names = target.names
    if main_child is None:  # enfant principal = enfant dont la tête est la queue : approximé par le premier enfant apparié le plus proche de l'axe
        main_child = {}
        for i, p in enumerate(target.parents):
            if p >= 0 and target.names[p] in mapping and target.names[i] in mapping:
                main_child.setdefault(target.names[p], target.names[i])
        for side in (".L", ".R"):  # la direction de la main est celle du MAJEUR (articulation du majeur) : le premier enfant apparié est l'index.00, dont la tête est quasi au poignet (vecteur court et latéral) :
            knuckle = "middle.01" + side  # sa direction, sensible à quelques degrés, pliait le poignet de ~66° sur la pose de REPOS de la source (mesuré, tools/probe_wrist_bias.py) ; avec le majeur : 9° (repos : 14°)
            if "hand" + side in mapping and knuckle in mapping:
                main_child["hand" + side] = knuckle
    s_heads = {t: source.head(s) for t, s in mapping.items()}
    t_heads = {t: target.head(t) for t in target.names}
    correction = {}
    for t_name in t_local_names:
        if t_name not in mapping:
            continue
        if options.pose_mode == DELTA or t_name not in main_child:  # delta : pas de correction ; os terminal : hérite plus bas
            correction[t_name] = None
            continue
        child = main_child[t_name]
        d_source = s_heads[child] - s_heads[t_name]
        d_target = t_heads[child] - t_heads[t_name]
        correction[t_name] = arc_rotation(d_target, d_source) if np.linalg.norm(d_source) > 1e-9 and np.linalg.norm(d_target) > 1e-9 else None
    # os terminaux (main, pied, tête…) sans enfant apparié : héritent de la correction de leur ancêtre apparié le plus proche
    for i, name in enumerate(target.names):
        if name in mapping and options.pose_mode in (ABSOLUTE, ABSOLUTE_IK) and correction.get(name) is None:
            p = target.parents[i]
            while p >= 0:
                inherited = correction.get(target.names[p])
                if inherited is not None:
                    correction[name] = inherited
                    break
                p = target.parents[p]
    rotations = np.zeros((frames, len(target.names), 3, 3))
    t_rest_rot = target.rest[:, :3, :3]
    local_rest = target.local_rest()
    for i, name in enumerate(target.names):
        if name in mapping:
            g = correction.get(name)
            base = t_rest_rot[i] if g is None else g @ t_rest_rot[i]
            rotations[:, i] = np.einsum("fij,jk->fik", delta[name], base)
    if options.clavicle_scale != 1.0:  # clavicules : rotation monde relative au repos réduite ; les autres os gardent leur orientation monde (le bras compense automatiquement dans world_to_basis)
        for side in (".L", ".R"):
            name = "clavicle" + side
            if name in mapping:
                i = target.index[name]
                delta_world = np.einsum("fij,jk->fik", rotations[:, i], t_rest_rot[i].T)
                rotations[:, i] = np.einsum("fij,jk->fik", scale_rotation(delta_world, options.clavicle_scale), t_rest_rot[i])
    # os sans source : orientation du parent + repos local (base identité)
    for i, name in enumerate(target.names):
        if name not in mapping:
            p = target.parents[i]
            parent_rot = rotations[:, p] if p >= 0 else np.eye(3)[None]
            rotations[:, i] = np.einsum("fij,jk->fik", parent_rot, local_rest[i][:3, :3])
    # translation du bassin et gestionnaire de root motion
    report = {"noms_cibles": list(target.names), "mode_pose": options.pose_mode, "root_motion": options.root_motion, "os_cibles_sans_source": [n for n in target.names if n not in mapping],
              "os_sources_non_utilises": sorted(set(source.names) - set(mapping.values()))}
    positions = np.full((frames, len(target.names), 3), np.nan)
    pelvis, root = "pelvis", "root"
    if pelvis in mapping:
        sp = source.index[mapping[pelvis]]
        source_motion = s_world[:, sp, :3, 3] - source.rest[sp, :3, 3]
        scale = options.translation_scale
        if scale is None:
            scale = target.rest[target.index[pelvis], 2, 3] / source.rest[sp, 2, 3]
        report["echelle_translation"] = float(scale)
        d = scale * source_motion
        horizontal = d.copy()
        horizontal[:, 2] = 0
        pelvis_pos = target.rest[target.index[pelvis], :3, 3] + d
        root_loc = np.zeros((frames, 3))
        if options.root_motion == IN_PLACE:
            pelvis_pos = pelvis_pos - horizontal
        elif options.root_motion == EXTRACT and root in target.index:
            root_loc = horizontal
        report["deplacement_horizontal_m"] = float(np.linalg.norm(horizontal[-1] - horizontal[0])) if frames > 1 else 0.0
        positions[:, target.index[pelvis]] = pelvis_pos
        if root in target.index:
            r = target.index[root]
            positions[:, r] = target.rest[r, :3, 3] + root_loc
    if options.pose_mode == ABSOLUTE_IK and pelvis in mapping:
        report["membres_ik"] = limb_ik(source, target, mapping, s_world, rotations, positions, report["echelle_translation"], local_rest, options.limb_blend, options.ik_limbs)
    loc, quat, _ = world_to_basis(target, rotations, positions)
    if root in target.index and options.root_motion != EXTRACT:
        loc[:, target.index[root]] = 0
    quat = continuous(quat)
    return Result(quat, loc, report)


def trim_and_speed(result, start=0, end=None, speed=1.0):
    """Découpe (images `start` à `end` incluses) puis change la vitesse (1 = inchangée ; 2 = deux fois plus rapide) par rééchantillonnage (nlerp des quaternions, linéaire des translations).
    Retourne un nouveau `Result` ; la durée est divisée par `speed`."""
    frames = result.quat.shape[0]
    end = frames - 1 if end is None else min(int(end), frames - 1)
    start = max(0, min(int(start), end))
    quat, loc = result.quat[start:end + 1], result.loc[start:end + 1]
    if abs(speed - 1.0) > 1e-9 and len(quat) > 1:
        count = max(2, int(round((len(quat) - 1) / speed)) + 1)
        position = np.linspace(0, len(quat) - 1, count)
        low = np.floor(position).astype(int)
        high = np.minimum(low + 1, len(quat) - 1)
        t = (position - low)[:, None, None]
        flip = ((quat[low] * quat[high]).sum(-1) < 0)[..., None]
        blend = quat[low] * (1 - t) + np.where(flip, -quat[high], quat[high]) * t
        quat = blend / np.linalg.norm(blend, axis=-1, keepdims=True)
        loc = loc[low] * (1 - t) + loc[high] * t
    report = dict(result.report, decoupe=[start, end], vitesse=speed)
    return Result(quat, loc, report)


def limb_ik(source, target, mapping, s_world, rotations, positions, scale, local_rest, limb_blend=0.0, ik_limbs=("leg",)):
    """Compensation de la longueur des membres (mode `absolu_ik`) : la main ou le pied cible vise la position de celle de la source, relative au bassin et mise à l'échelle
    (`scale`), dans la limite de la portée de NOS segments ; le coude ou le genou garde la direction de pôle de la source. IK analytique à 2 os, vectorisée sur les images ;
    modifie `rotations` (orientations monde du haut et du bas du membre) sur place. Retourne la liste des membres corrigés."""
    frames, count = rotations.shape[0], len(target.names)
    pelvis_pos = positions[:, target.index["pelvis"]]
    s_pelvis = s_world[:, source.index[mapping["pelvis"]], :3, 3]

    def forward():
        pos = np.zeros((frames, count, 3))
        for i, p in enumerate(target.parents):
            if not np.isnan(positions[:, i]).any():
                pos[:, i] = positions[:, i]
            elif p < 0:
                pos[:, i] = target.rest[i, :3, 3]
            else:
                pos[:, i] = pos[:, p] + np.einsum("fij,j->fi", rotations[:, p], local_rest[i][:3, 3])
        return pos

    corrected = []
    for kind, limb in (("arm", ("arm_upper", "arm_lower", "hand")), ("leg", ("leg_upper", "leg_lower", "foot"))):
        if kind not in ik_limbs:
            continue
        for side in (".L", ".R"):
            names = [n + side for n in limb]
            if not all(n in mapping and n in target.index for n in names):
                continue
            upper, lower, end = (target.index[n] for n in names)
            s_up, s_lo, s_end = (source.index[mapping[n]] for n in names)
            length_1 = float(np.linalg.norm(target.rest[lower, :3, 3] - target.rest[upper, :3, 3]))
            length_2 = float(np.linalg.norm(target.rest[end, :3, 3] - target.rest[lower, :3, 3]))
            pos = forward()
            shoulder = pos[:, upper]
            wanted = pelvis_pos + (s_world[:, s_end, :3, 3] - s_pelvis) * scale
            if limb_blend:  # échelle propre au membre : rapport des longueurs de segments, appliquée depuis l'épaule (ou la hanche) de la cible
                source_length = float(np.linalg.norm(source.rest[s_lo, :3, 3] - source.rest[s_up, :3, 3]) + np.linalg.norm(source.rest[s_end, :3, 3] - source.rest[s_lo, :3, 3]))
                limb_scale = (length_1 + length_2) / max(source_length, 1e-9)
                wanted = (1.0 - limb_blend) * wanted + limb_blend * (shoulder + (s_world[:, s_end, :3, 3] - s_world[:, s_up, :3, 3]) * limb_scale)
            direction = wanted - shoulder
            distance = np.clip(np.linalg.norm(direction, axis=-1), abs(length_1 - length_2) + 1e-7, length_1 + length_2 - 1e-7)
            unit = direction / (np.linalg.norm(direction, axis=-1, keepdims=True) + 1e-18)
            pole = (s_world[:, s_lo, :3, 3] - s_world[:, s_up, :3, 3]) * scale
            pole = pole - unit * (pole * unit).sum(-1, keepdims=True)
            fallback = pos[:, lower] - shoulder
            fallback = fallback - unit * (fallback * unit).sum(-1, keepdims=True)
            pole = np.where(np.linalg.norm(pole, axis=-1, keepdims=True) > 1e-9, pole, fallback)
            pole = pole / (np.linalg.norm(pole, axis=-1, keepdims=True) + 1e-18)
            along = (length_1 ** 2 - length_2 ** 2 + distance ** 2) / (2 * distance)
            height = np.sqrt(np.maximum(length_1 ** 2 - along ** 2, 0))
            elbow = shoulder + along[:, None] * unit + height[:, None] * pole
            reach = shoulder + distance[:, None] * unit
            rotations[:, upper] = np.einsum("fij,fjk->fik", arc_rotations(pos[:, lower] - shoulder, elbow - shoulder), rotations[:, upper])
            pos = forward()
            rotations[:, lower] = np.einsum("fij,fjk->fik", arc_rotations(pos[:, end] - pos[:, lower], reach - pos[:, lower]), rotations[:, lower])
            corrected.append(side and f"{limb[0].split('_')[0]}{side}")
    for i, name in enumerate(target.names):  # les os sans source (torsions…) suivent à nouveau leur parent corrigé
        if name not in mapping and target.parents[i] >= 0:
            rotations[:, i] = np.einsum("fij,jk->fik", rotations[:, target.parents[i]], local_rest[i][:3, :3])
    return corrected


# --- mesures (partagées par les tests) ---------------------------------------------------------------------------------------------------------------

def joint_positions(rig, loc, quat):
    """Positions monde des têtes d'os (F, N, 3)."""
    return forward_kinematics(rig, loc, quat)[:, :, :3, 3]


def foot_slide(foot_positions, foot_height, stature, fps, height_limit=0.03, speed_limit=0.03):
    """Dérive horizontale (m) des intervalles où le pied est posé : hauteur < 3 % de la stature et vitesse < 3 % de la stature par seconde. Retourne la liste des dérives."""
    speed = np.zeros(len(foot_positions))
    speed[1:] = np.linalg.norm(np.diff(foot_positions[:, :2], axis=0), axis=1) * fps
    planted = (foot_height < height_limit * stature) & (speed < speed_limit * stature)
    drifts, start = [], None
    for f, flag in enumerate(list(planted) + [False]):
        if flag and start is None:
            start = f
        elif not flag and start is not None:
            if f - start >= 3:
                drifts.append(float(np.linalg.norm(foot_positions[f - 1, :2] - foot_positions[start, :2])))
            start = None
    return drifts


def signature(source, mapping, options, action_key):
    """Clé de cache : action, mapping et options."""
    text = json.dumps({"algorithme": 2, "action": action_key, "mapping": sorted(mapping.items()), "options": [options.pose_mode, options.root_motion, options.translation_scale, options.limb_blend, list(options.ik_limbs), options.clavicle_scale], "source": list(source.names)}, sort_keys=True)
    return hashlib.sha1(text.encode()).hexdigest()[:20]
