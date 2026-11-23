"""Moteur de mapping (lot A2b) : relie les os d'un squelette SOURCE quelconque à NOS os, automatiquement puis à la main.

Le cœur ne dépend pas de bpy (numpy seulement) : il se teste sur des squelettes synthétiques ; `from_armature` lit une armature Blender.
Principes (D-31, STRATEGIE_ANIMATION.md §3) :
- AUCUN nom ni profil d'un rig tiers n'est livré : le dictionnaire de synonymes est GÉNÉRIQUE (vocabulaire d'anatomie et de conventions courantes),
  les profils sont produits à l'exécution puis enregistrés par l'utilisateur ;
- trois niveaux, du plus fiable au moins fiable, chacun avec un score de confiance par os :
    1. noms : normalisation (espaces de noms, casse, séparateurs, côté Left/L/.L, chiffres) puis rôle anatomique (partie, côté, indice, torsion) ;
    2. structure : paires d'enfants non appariés sous un parent apparié, départagés par la direction et la longueur ;
    3. géométrie : positions de repos normalisées par la stature, côté par la coordonnée x, appariement un-à-un glouton ;
- un os source ne sert qu'une fois ; les conflits sont consignés ; rapport : os cibles sans source, os sources inutilisés (auxiliaires, torsions, bouts), faible confiance.

Méthode inspirée des outils de retargeting existants (appariement par noms d'abord, repli sur la hiérarchie, vérification de cohérence), sans copier leurs tables.
"""
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import re

import numpy as np

FORMAT = "humanloom.mapping"
VERSION = 1
LOW_CONFIDENCE = 0.6
GEOMETRY_LIMIT = 0.2  # coût maximal (fraction de la stature) pour un appariement par la géométrie
# Préfixes d'espace de noms ou de famille d'os, sans signification anatomique (liste générique de conventions de nommage courantes).
PREFIX_TOKENS = {"def", "org", "bip", "bip01", "cc", "rig", "skel", "armature", "jnt", "mixamorig", "bone", "sk"}
SIDE_LEFT, SIDE_RIGHT = {"l", "left", "lt", "lft"}, {"r", "right", "rt", "rgt"}
END_TOKENS = {"end", "tip", "nub", "null", "leaf"}
AUX_TOKENS = {"jaw", "ik", "pole", "ctrl", "control", "controller", "helper", "offset", "attach", "weapon", "prop", "props", "socket", "poi", "aim", "target", "tgt", "mch", "gun", "com", "fk",
              # os d'aide à la déformation (correctifs de pose, muscles) : jamais un os de squelette principal
              "corrective", "correctiveroot", "slide", "adj", "adjust", "fwd", "bck", "in", "out", "inner", "outer", "scap", "pec", "latissimus", "bend",
              # accessoires et vêtements animés par os (jupes, capes, cheveux, plaques d'armure) : hors du squelette principal
              "skirt", "cape", "cloak", "cloth", "dress", "jacket", "coat", "scarf", "hair", "ponytail", "tail", "strap", "plate", "armor", "armour", "flare", "belt", "pouch", "sleeve"}
FINGERS = ("thumb", "index", "middle", "ring", "pinky")
FINGER_RULES = (("thumb", "thumb|pollex"), ("index", "index|pointer"), ("middle", "middle|longfinger"), ("ring", "ring"), ("pinky", "pinky|pinkie|little|small"))
PART_RULES = (  # appliquées dans l'ordre sur la clé canonique (mots collés) ; premier qui correspond
    ("arm_lower", "lowerarm|forearm|elbow"), ("arm_upper", "upperarm|humerus|uparm"), ("leg_lower", "lowerleg|calf|shin|tibia|knee"),
    ("leg_upper", "upperleg|thigh|femur|upleg"), ("clavicle", "clavicle|collar|scapula"), ("hand", "hand|wrist"), ("foot", "foot|ankle"),
    ("toe", "toe|ball"), ("neck", "neck"), ("head", "head|skull"), ("spine", "spine|chest|torso|abdomen|trunk|waist|stomach|belly|^back$"),
    ("pelvis", "pelvis|hips|sacrum"), ("root", "root|master|world"),
)
AMBIGUOUS = {"shoulder": "shoulder?", "arm": "arm?", "leg": "leg?", "hip": "hip?"}


FACE_ONLY = "jaw"  # os de la mâchoire de HumanLoom : jamais apparié par la structure ou la géométrie (les squelettes de corps n'en ont pas) ; reste appariable à la main

# --- squelette -----------------------------------------------------------------------------------------------------------------------------------

@dataclass
class Skeleton:
    names: list
    parents: list        # indice du parent, -1 pour une racine
    heads: np.ndarray    # (N, 3) positions de repos, repère monde (Z haut, avant -Y)
    tails: np.ndarray
    source: str = ""
    _children: dict = field(default_factory=dict, repr=False)

    def __post_init__(self):
        self.heads, self.tails = np.asarray(self.heads, float), np.asarray(self.tails, float)
        for index, parent in enumerate(self.parents):
            self._children.setdefault(parent, []).append(index)

    def __len__(self):
        return len(self.names)

    def children(self, index):
        return self._children.get(index, [])

    def depth(self, index):
        count = 0
        while self.parents[index] >= 0:
            index, count = self.parents[index], count + 1
        return count

    def signature(self):
        """Empreinte des noms et de la hiérarchie : une source change d'empreinte si ses os changent (profil périmé)."""
        text = json.dumps(sorted((n, self.names[p] if p >= 0 else None) for n, p in zip(self.names, self.parents)))
        return hashlib.sha1(text.encode()).hexdigest()[:16]


def from_table(table, source=""):
    """Squelette depuis une liste de dictionnaires {name, parent(nom ou None), head, tail} (ex. `skeleton.bone_table`)."""
    names = [b["name"] for b in table]
    index = {n: i for i, n in enumerate(names)}
    return Skeleton(names, [index[b["parent"]] if b["parent"] else -1 for b in table], [b["head"] for b in table], [b["tail"] for b in table], source)


def from_armature(obj):
    """Squelette d'une armature Blender (repos, repère monde) ; accepte aussi des données d'armature seules (repère local, utile pour une armature chargée seule)."""
    data = getattr(obj, "data", obj)
    matrix = getattr(obj, "matrix_world", None)
    bones = list(data.bones)
    index = {b.name: i for i, b in enumerate(bones)}
    place = (lambda v: list(matrix @ v)) if matrix is not None else (lambda v: list(v))
    return Skeleton([b.name for b in bones], [index[b.parent.name] if b.parent else -1 for b in bones], [place(b.head_local) for b in bones], [place(b.tail_local) for b in bones],
                    getattr(obj, "name", ""))


def duplicates(mapping):
    """Sources utilisées par plusieurs cibles dans un mapping éditable {cible: nom de source} : {source: [cibles]} (vide si aucun conflit)."""
    used = {}
    for target, source in mapping.items():
        if source:
            used.setdefault(source, []).append(target)
    return {s: t for s, t in used.items() if len(t) > 1}


# --- niveau 1 : noms -------------------------------------------------------------------------------------------------------------------------------

def tokens(name):
    """Jetons minuscules : espace de noms retiré, CamelCase et chiffres séparés, préfixes de convention retirés."""
    name = re.split(r"[:|]", name)[-1]
    name = re.sub(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Za-z])(?=[0-9])|(?<=[0-9])(?=[A-Za-z])", " ", name)
    return [t.lower() for t in re.split(r"[^0-9A-Za-z]+", name) if t and t.lower() not in PREFIX_TOKENS]


def canonical(key):
    for a, b in (("armupper", "upperarm"), ("armlower", "lowerarm"), ("legupper", "upperleg"), ("leglower", "lowerleg"), ("uparm", "upperarm"), ("upleg", "upperleg")):
        key = key.replace(a, b)
    return key


def parse(name):
    """Rôle anatomique d'un nom : {part, side, number, twist, meta, end, aux}. `part` vaut None si le nom n'est pas reconnu."""
    words = tokens(name)
    side = "L" if any(w in SIDE_LEFT for w in words) else "R" if any(w in SIDE_RIGHT for w in words) else None
    numbers = [int(w) for w in words if w.isdigit()]
    letters = [w for w in words if not w.isdigit() and w not in SIDE_LEFT | SIDE_RIGHT]
    key = canonical("".join(letters))
    result = {"part": None, "side": side, "number": numbers[0] if numbers else None, "twist": "twist" in key or "roll" in key, "meta": bool(re.search(r"meta|palm|carpal", key)),
              "end": any(w in END_TOKENS for w in words), "aux": any(w in AUX_TOKENS for w in words), "ambiguous": None}
    if "toe" in key and any(re.search(pattern, key) for _name, pattern in FINGER_RULES):  # doigts de pied (« little toe »…) : pas des doigts de main
        result["aux"] = True
        return result
    for finger, pattern in FINGER_RULES:
        if re.search(pattern, key):
            result["part"] = finger
            if result["number"] == 0:  # numérotation à partir de 0 : le premier os est le métacarpien
                result["meta"] = True
            return result
    for part, pattern in PART_RULES:
        if re.search(pattern, key):
            result["part"] = part
            return result
    for word, mark in AMBIGUOUS.items():
        if key == word or key.endswith(word):
            result["ambiguous"] = mark
            return result
    if result["meta"] and result["number"] in (1, 2, 3, 4):  # os de paume numérotés de l'index (1) au petit doigt (4)
        result["part"] = FINGERS[result["number"]]
    return result


def _ordered_chain(skel, indices):
    return sorted(indices, key=skel.depth)


def _main_chain(skel, indices):
    """Chaîne principale d'un ensemble d'os : de la racine de l'ensemble vers l'enfant qui a le plus de descendants dans l'ensemble (les autres sont des aides)."""
    members = set(indices)
    memo = {}

    def below(i):
        if i not in memo:
            memo[i] = max((1 + below(c) for c in skel.children(i) if c in members), default=0)
        return memo[i]

    roots = [i for i in indices if skel.parents[i] not in members]
    if not roots:
        return []
    chain = [max(roots, key=lambda r: (below(r), -skel.depth(r)))]
    while True:
        kids = [c for c in skel.children(chain[-1]) if c in members]
        if not kids:
            return chain
        chain.append(max(kids, key=below))


def roles(skel, aux_filter=True):
    """Rôle de chaque os d'un squelette, avec résolution des mots ambigus et attribution des indices (colonne, doigts) par la structure."""
    info = [parse(n) for n in skel.names]
    by_side = lambda side: [i for i, r in enumerate(info) if r["side"] == side]
    # mots ambigus : « arm » = haut du bras ; « hip » avec côté = haut de la jambe, sans côté = bassin ; « leg » = haut de la jambe sauf si « upper leg » existe ;
    # « shoulder » = clavicule si un haut de bras existe du même côté, sinon haut du bras (résolu en dernier)
    for mark_now in ("arm?", "hip?", "leg?", "shoulder?"):
      for i, r in enumerate(info):
        mark = r["ambiguous"]
        if mark != mark_now:
            continue
        if mark == "shoulder?":
            has_arm = any(info[c]["part"] in ("arm_upper", "arm_lower", None) and not info[c]["aux"] for c in skel.children(i))
            r["part"] = "clavicle" if has_arm and any(x["part"] == "arm_upper" for x in map(lambda k: info[k], by_side(r["side"]))) else "arm_upper"
        elif mark == "arm?":
            r["part"] = "arm_upper"
        elif mark == "leg?":
            r["part"] = "leg_lower" if any(x["part"] == "leg_upper" for x in map(lambda k: info[k], by_side(r["side"]))) else "leg_upper"
        elif mark == "hip?":
            r["part"] = "leg_upper" if r["side"] else "pelvis"
    # indices : colonne et cou par profondeur ; doigts par ordre de chaîne
    for part in ("spine", "neck"):
        chain = _ordered_chain(skel, [i for i, r in enumerate(info) if r["part"] == part and not r["twist"]])
        for rank, i in enumerate(chain):
            info[i]["index"] = rank
    for side in ("L", "R", None):
        for finger in FINGERS:
            members = [i for i, r in enumerate(info) if r["part"] == finger and r["side"] == side and not r["twist"] and not r["aux"]]
            chain = _main_chain(skel, members)
            for i in members:
                if i not in chain:
                    info[i]["aux"] = True  # os d'aide (hors de la chaîne principale du doigt)
            if not chain:
                continue
            has_meta = info[chain[0]]["meta"]
            if finger == "thumb":  # nos pouces n'ont pas de métacarpe : un os métacarpien source reste sans équivalent
                usable, first = (chain[1:4], 1) if has_meta else (chain[:3], 1)
            else:
                usable, first = (chain[:4], 0) if has_meta else (chain[:3], 1)
            for rank, i in enumerate(usable):
                info[i]["index"] = first + rank
            for i in chain:
                if i not in usable:
                    info[i]["end"] = True
    for i, r in enumerate(info):
        r.setdefault("index", None)
        if r["part"] in ("arm_upper", "arm_lower", "leg_upper", "leg_lower") and r["twist"]:
            r["index"] = r["number"]
    for part in ("arm_upper", "arm_lower", "leg_upper", "leg_lower"):  # os de torsion d'un même membre : indices 1, 2 par profondeur si les chiffres manquent
        for side in ("L", "R"):
            twists = _ordered_chain(skel, [i for i, r in enumerate(info) if r["part"] == part and r["side"] == side and r["twist"]])
            for rank, i in enumerate(twists):
                info[i]["index"] = rank + 1
    return info


def _key(r):
    return (r["part"], r["side"], r.get("index"), r["twist"])


# --- géométrie --------------------------------------------------------------------------------------------------------------------------------------

def normalization(skel, info):
    """(centre, stature, retourné) : centre x/y médians, sol = 1er centile de z ; os auxiliaires exclus ; `retourné` si le côté « gauche » des noms est à x < 0."""
    usable = [i for i, r in enumerate(info) if not r["aux"]] or list(range(len(skel)))
    points = np.vstack([skel.heads[usable], skel.tails[usable]])
    z0, z1 = np.percentile(points[:, 2], 1), np.percentile(points[:, 2], 99)
    heads = skel.heads[usable]
    cx = float(np.median(heads[:, 0]))
    midline = heads[np.abs(heads[:, 0] - cx) < 0.05 * (z1 - z0)]  # avant-arrière : os de la ligne médiane seulement (les doigts et membres déplaceraient la médiane)
    center = np.array([cx, float(np.median(midline[:, 1])) if len(midline) else float(np.median(heads[:, 1])), float(z0)])
    signs = [np.sign(skel.heads[i][0] - center[0]) for i, r in enumerate(info) if r["side"] == "L" and abs(skel.heads[i][0] - center[0]) > 0.02 * (z1 - z0)]
    flipped = bool(signs) and np.mean(np.array(signs) > 0) < 0.3
    return center, float(z1 - z0), flipped


def normalized(skel, info):
    center, stature, flipped = normalization(skel, info)
    heads, tails = (skel.heads - center) / stature, (skel.tails - center) / stature
    if flipped:
        heads[:, 0], tails[:, 0] = -heads[:, 0], -tails[:, 0]
    return heads, tails


# --- appariement ------------------------------------------------------------------------------------------------------------------------------------

@dataclass
class Pair:
    target: str
    source: str
    score: float
    method: str


@dataclass
class Report:
    pairs: list
    unmapped_targets: list
    unused_sources: dict          # {catégorie: [noms]}
    conflicts: list
    low_confidence: list
    parent_mismatches: list
    coverage: float               # part des os cibles déformants (hors root, torsions et métacarpes) appariés

    def summary(self):
        return {"appariés": len(self.pairs), "cibles_sans_source": len(self.unmapped_targets), "sources_inutilisées": {k: len(v) for k, v in self.unused_sources.items()},
                "conflits": len(self.conflicts), "faible_confiance": len(self.low_confidence), "parents_incohérents": len(self.parent_mismatches), "couverture": round(self.coverage, 3)}


def auto_map(target, source):
    """Apparie `target` (nos os) et `source`. Retourne (dict cible → Pair, Report)."""
    t_info, s_info = roles(target), roles(source)
    pairs, taken = {}, set()
    conflicts = []

    def add(t, s, score, method, log=True):
        if t in pairs or s in taken:
            if log and s in taken and t not in pairs:
                conflicts.append(f"{source.names[s]} réclamé par plusieurs cibles (gardé pour {target.names[next(k for k, p in pairs.items() if p.source == source.names[s])]})")
            return False
        pairs[t] = Pair(target.names[t], source.names[s], round(float(score), 3), method)
        taken.add(s)
        return True

    # niveau 1 : clés de rôle identiques ; plusieurs candidats pour une clé : on garde le plus proche du parent apparié, sinon le premier par profondeur
    s_by_key = {}
    for i, r in enumerate(s_info):
        if r["part"] and not r["aux"] and not r["end"]:
            s_by_key.setdefault(_key(r), []).append(i)
    for t, r in enumerate(t_info):
        if r["part"] is None or r["part"] in ("spine", "neck"):
            continue
        candidates = s_by_key.get(_key(r), [])
        if candidates:
            add(t, sorted(candidates, key=source.depth)[0], 0.9 if r["side"] is not None or r["part"] in ("spine", "neck", "pelvis", "head", "root") else 0.8, "nom")
    # niveau 1b : colonne et cou de longueurs différentes : rééchantillonnage monotone le long de la chaîne
    for part in ("spine", "neck"):
        t_chain = _ordered_chain(target, [i for i, r in enumerate(t_info) if r["part"] == part and not r["twist"]])
        s_chain = [i for i in _ordered_chain(source, [i for i, r in enumerate(s_info) if r["part"] == part and not r["twist"] and not r["aux"]]) if i not in taken]
        free_t = [t for t in t_chain if t not in pairs]
        if s_chain and free_t:
            for rank, s in enumerate(s_chain):
                wanted = int(round(rank * (len(t_chain) - 1) / max(len(s_chain) - 1, 1))) if len(s_chain) > 1 else (len(t_chain) - 1 if part == "spine" else 0)
                if not free_t:  # plus de cibles libres : les os de colonne restants de la source restent inutilisés
                    break
                best = min(free_t, key=lambda t: abs(t_chain.index(t) - wanted))
                if add(best, s, 0.9 if len(s_chain) == len(t_chain) else 0.7, "nom (chaîne)" if len(s_chain) == len(t_chain) else "nom (chaîne rééchantillonnée)"):
                    free_t.remove(best)
    # niveau 2 : enfants non appariés sous un parent apparié, par direction et longueur
    def direction(skel, i):
        v = skel.tails[i] - skel.heads[i]
        n = np.linalg.norm(v)
        return v / n if n > 1e-9 else v

    for _ in range(4):
        progress = False
        for t in list(pairs):
            s = [i for i, n in enumerate(source.names) if n == pairs[t].source][0]
            t_free = [c for c in target.children(t) if c not in pairs and t_info[c]["part"] not in ("root",) and not t_info[c]["twist"] and target.names[c] != FACE_ONLY]
            s_free = [c for c in source.children(s) if c not in taken and not s_info[c]["aux"] and not s_info[c]["end"] and not s_info[c]["twist"]]
            if not t_free or not s_free:
                continue
            costs = sorted((float(1 - direction(target, a) @ direction(source, b)), ai, bi) for ai, a in enumerate(t_free) for bi, b in enumerate(s_free))
            used_a, used_b = set(), set()
            for cost, ai, bi in costs:
                if ai in used_a or bi in used_b or cost > 0.9:
                    continue
                if add(t_free[ai], s_free[bi], max(0.3, 0.65 - cost * 0.3), "structure", log=False):
                    used_a.add(ai)
                    used_b.add(bi)
                    progress = True
        if not progress:
            break
    # niveau 3 : géométrie normalisée (têtes + queues + longueur), un-à-un glouton, côté par x
    t_head, t_tail = normalized(target, t_info)
    s_head, s_tail = normalized(source, s_info)
    free_t = [t for t in range(len(target)) if t not in pairs and t_info[t]["part"] not in ("root",) and not t_info[t]["twist"] and target.names[t] != FACE_ONLY]
    free_s = [s for s in range(len(source)) if s not in taken and not s_info[s]["aux"] and not s_info[s]["end"]]
    options = []
    for t in free_t:
        for s in free_s:
            ds, dt = np.linalg.norm(t_head[t] - s_head[s]), np.linalg.norm(t_tail[t] - s_tail[s])
            length_t, length_s = np.linalg.norm(t_tail[t] - t_head[t]), np.linalg.norm(s_tail[s] - s_head[s])
            side_t = "L" if t_head[t][0] > 0.015 else "R" if t_head[t][0] < -0.015 else None
            side_s = "L" if s_head[s][0] > 0.015 else "R" if s_head[s][0] < -0.015 else None
            if side_t and side_s and side_t != side_s:
                continue
            if s_info[s]["side"] and t_info[t]["side"] and s_info[s]["side"] != t_info[t]["side"]:
                continue
            if s in taken:
                continue
            cost = ds + dt + 0.7 * abs(length_t - length_s) + 0.01 * abs(target.depth(t) - source.depth(s))
            if cost < GEOMETRY_LIMIT and (t_info[t]["part"] is None or s_info[s]["part"] is None or t_info[t]["part"] == s_info[s]["part"]):
                options.append((cost, t, s))
    for cost, t, s in sorted(options):
        add(t, s, max(0.25, 0.55 - cost * 5), "géométrie", log=False)

    # rapport
    pair_of = {p.target: p for p in pairs.values()}
    unmapped = [target.names[t] for t in range(len(target)) if t not in pairs]
    used_names = {p.source for p in pairs.values()}
    unused = {"auxiliaires": [], "bouts": [], "torsions": [], "inconnus": []}
    for s, name in enumerate(source.names):
        if name in used_names:
            continue
        r = s_info[s]
        unused["auxiliaires" if r["aux"] else "bouts" if r["end"] or not source.children(s) and r["part"] in FINGERS else "torsions" if r["twist"] else "inconnus"].append(name)
    mismatches = []
    for t, p in pairs.items():
        s = [i for i, n in enumerate(source.names) if n == p.source][0]
        parent_t, parent_s = target.parents[t], source.parents[s]
        if parent_t >= 0 and parent_s >= 0 and parent_t in pairs:
            ancestor = parent_s
            ok = False
            while ancestor >= 0:  # le parent apparié doit être un ancêtre de la source (les os intermédiaires non appariés sont permis)
                if source.names[ancestor] == pairs[parent_t].source:
                    ok = True
                    break
                ancestor = source.parents[ancestor]
            if not ok:
                mismatches.append(f"{p.target} ← {p.source}")
    # couverture : os cibles déformants hors torsions et métacarpes (os que beaucoup de squelettes n'ont pas : leur absence n'est pas un défaut de l'appariement)
    deform = [t for t in range(len(target)) if t_info[t]["part"] not in (None, "root") and not t_info[t]["twist"] and not t_info[t]["meta"]]
    report = Report(list(pairs.values()), unmapped, unused, conflicts, [p.target for p in pairs.values() if p.score < LOW_CONFIDENCE], mismatches,
                    sum(1 for t in deform if t in pairs) / max(len(deform), 1))
    return {target.names[t]: p for t, p in pairs.items()}, report


# --- profils JSON (dossier utilisateur) ---------------------------------------------------------------------------------------------------------------

def profile_dict(source, mapping, name=None):
    return {"format": FORMAT, "version": VERSION, "name": name or source.source, "source_signature": source.signature(),
            "mapping": {t: (p.source if isinstance(p, Pair) else p) for t, p in mapping.items()},
            "scores": {t: p.score for t, p in mapping.items() if isinstance(p, Pair)}}


def save_profile(directory, source, mapping, name=None):
    """Écrit le profil dans `directory/profiles/<nom>.json` (atomique). Retourne le chemin."""
    import os
    import tempfile
    data = profile_dict(source, mapping, name)
    safe = re.sub(r"[^0-9A-Za-z_.-]+", "_", data["name"]) or "profil"
    folder = Path(directory) / "profiles"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{safe}.json"
    handle, temp = tempfile.mkstemp(dir=str(folder), suffix=".tmp")
    with os.fdopen(handle, "w", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=1)
    os.replace(temp, path)
    return path


def load_profile(path, source=None):
    """Lit un profil ; si `source` est donné, retourne aussi la liste des problèmes (os absents, empreinte différente). Lève ValueError si le fichier n'est pas un profil."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("format") != FORMAT or not isinstance(data.get("mapping"), dict):
        raise ValueError("Ce fichier n'est pas un profil de mapping HumanLoom.")
    problems = []
    if source is not None:
        missing = [s for s in data["mapping"].values() if s not in source.names]
        if missing:
            problems.append(f"{len(missing)} os absents de la source (ex. {missing[0]}).")
        if data.get("source_signature") != source.signature():
            problems.append("La hiérarchie de la source a changé depuis l'enregistrement du profil.")
    return data, problems


def apply_profile(data, source):
    """Mapping {cible: nom de source} d'un profil, limité aux os présents dans la source (les autres sont ignorés et listés par `load_profile`)."""
    return {t: s for t, s in data["mapping"].items() if s in source.names}
