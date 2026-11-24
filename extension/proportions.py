"""Stable identifiers shared by the editable asset and its interface."""

BODY_CONTROLS = (
    ("corpulence", "Corpulence"),
    ("shoulders", "Carrure"),
    ("waist", "Tour de taille"),
    ("hips", "Largeur du bassin"),
    ("torso_depth", "Profondeur du buste"),
    ("neck", "Largeur du cou"),
    ("legs", "Longueur des jambes"),
    ("torso", "Longueur du buste"),
)

MUSCLE_CONTROLS = (
    ("muscles", "Musculature globale"),
    ("muscles_shoulders", "Épaules"),
    ("muscles_chest", "Pectoraux"),
    ("muscles_back", "Dos"),
    ("muscles_arms", "Bras"),
    ("muscles_abdomen", "Abdomen"),
    ("muscles_glutes", "Fessiers"),
    ("muscles_thighs", "Cuisses"),
    ("muscles_calves", "Mollets"),
    ("muscle_definition", "Définition musculaire"),
)

FAT_CONTROLS = (
    ("whole_body", "Corpulence globale"),
    ("body_mass", "Volume hérité · 0.12"),
    ("adiposity", "Couverture régionale"),
    ("fat_abdomen", "Abdomen"),
    ("fat_flanks", "Flancs"),
    ("fat_hips", "Bassin et fessiers"),
    ("fat_thighs", "Cuisses"),
    ("fat_arms", "Bras"),
    ("fat_face", "Visage"),
)

FACE_CONTROLS = (
    ("head_width", "Largeur de la tête"),
    ("head_height", "Hauteur de la tête"),
    ("jaw", "Mâchoire (largeur et angle)"),
    ("chin", "Avancée du menton"),
    ("cheeks", "Pommettes"),
    ("nose_length", "Avancée du nez"),
    ("nose_width", "Largeur du nez"),
    ("mouth", "Largeur de la bouche"),
    ("lips", "Lèvres (relief et épaisseur)"),
    ("eye_spacing", "Écartement des yeux"),
    ("eye_height", "Position verticale des yeux"),
    ("forehead", "Hauteur du front"),
    ("ears_size", "Taille des oreilles"),
    ("ears_angle", "Orientation des oreilles"),
    ("eyelid_aperture", "Ouverture des paupières"),
    ("nose_bridge", "Relief de l’arête nasale"),
    ("lip_thickness", "Épaisseur des lèvres"),
    ("mouth_corner", "Hauteur des commissures"),
    ("jaw_angle", "Angle de la mâchoire"),
    ("facial_asymmetry", "Asymétrie du visage"),
    ("skin_relief", "Relief de peau âgée"),
)

CONTROLS = BODY_CONTROLS + FAT_CONTROLS + MUSCLE_CONTROLS + FACE_CONTROLS
# Schéma 10 (lot 3, I-46) : une seule échelle de corpulence (`whole_body`). Ces deux contrôles de l'ancien moteur n'existent
# plus dans le groupe de nœuds « HL Human » ; ils restent dans CONTROLS tant que l'ancien moteur existe (lot 5).
REMOVED_IN_SCHEMA_10 = ("corpulence", "body_mass")
# Schéma 10 (lot 3 bis, décision D-26) : deux paires de contrôles proches sont fusionnées. Le contrôle fusionné garde le nom du premier ;
# le second n'est plus une entrée du groupe de nœuds : ses couches lisent la valeur du premier (les deux champs s'ajoutent).
MERGED_IN_SCHEMA_10 = {"lip_thickness": "lips", "jaw_angle": "jaw"}
# Commandes de visage ajoutées au groupe de nœuds APRÈS sa génération (tools/build_face_layers.py) : entrées du groupe qui ne viennent pas des clés de forme de l'ancien moteur.
# `mouth_open` : correctif d'ouverture de bouche, PILOTÉ par la rotation de l'os `jaw` (skeleton.attach_mouth_driver), 0 = fermée, 1 = ouverte à 30°.
FACE_COMMANDS = ("mouth_open", "brow_up", "brow_down", "brow_inner_up", "smile_L", "smile_R", "cheek_puff", "lip_pucker", "nose_wrinkle", "mouth_down", "blink_L", "blink_R",
                 "eye_wide", "eye_squint", "brow_together", "upper_lip_raise", "lip_stretch", "lips_press", "chin_raise", "lower_lip_depress",
                 "cheek_raise", "nasolabial_deepen", "crows_feet", "smile_pull", "smile_duchenne",
                 "forehead_wrinkles", "glabella_wrinkles", "nose_bridge_wrinkles", "nostril_flare", "dimpler_L", "dimpler_R")
# Commandes pilotes (lot visage) : libellés de l'interface (`mouth_open` n'est pas affichée : elle est pilotée par la mâchoire). Amplitudes : voir `extension/data/face_reference.json` et `mesh["hl_face_layers"]`.
FACE_COMMAND_LABELS = {"brow_up": "Sourcils levés", "brow_down": "Sourcils froncés", "brow_inner_up": "Sourcils : intérieur levé", "smile_L": "Sourire gauche", "smile_R": "Sourire droit",
                       "cheek_puff": "Joues gonflées", "lip_pucker": "Lèvres en avant", "nose_wrinkle": "Nez plissé", "mouth_down": "Commissures abaissées", "blink_L": "Clignement gauche", "blink_R": "Clignement droit",
                       "eye_wide": "Yeux grands ouverts", "eye_squint": "Yeux plissés", "brow_together": "Sourcils rapprochés", "upper_lip_raise": "Lèvre supérieure relevée",
                       "lip_stretch": "Lèvres étirées", "lips_press": "Lèvres serrées", "chin_raise": "Menton relevé", "lower_lip_depress": "Lèvre inférieure abaissée",
                       "cheek_raise": "Joues remontées (pommettes)", "nasolabial_deepen": "Sillon naso-génien creusé", "crows_feet": "Pattes d'oie", "smile_pull": "Commissures tirées vers l'oreille", "smile_duchenne": "Sourire (intensité unique)",
                       "forehead_wrinkles": "Rides du front", "glabella_wrinkles": "Rides entre les sourcils", "nose_bridge_wrinkles": "Plis du nez", "nostril_flare": "Narines dilatées",
                       "dimpler_L": "Fossette gauche (AU14)", "dimpler_R": "Fossette droite (AU14)"}
# Expressions prédéfinies : ÉCRITES PAR NOUS (D-34), combinaisons de commandes, non calibrées.
FACE_PRESETS = {
    "neutre": {},
    # Combinaisons d'AU : Table 3 de Clark et al. 2020 (Front Psychol 11:920, doi:10.3389/fpsyg.2020.00920, règles de correspondance du guide des investigateurs FACS) et Table 1 de Lazzeri et al. 2015 (Front Bioeng
    # Biotechnol 3:64, doi:10.3389/fbioe.2015.00064), LUES via Europe PMC. Les intensités ci-dessous sont NOS choix (artistiques), jamais des intensités FACS.
    # JOIE = 12 ; 6+12
    # Sourire de Duchenne : UNE commande maîtresse (courbe progressive commune) = commissures diagonales + joues/pommettes + paupières inférieures relevées + sillon + pattes d'oie (voir tools/build_face_smile.py)
    "joie": {"smile_duchenne": 1.0},
    # RIRE = 6+12+25/26 : sourire large, joues remontées, lèvre supérieure relevée, mâchoire entrouverte (dents du bas visibles : la mâchoire les descend avec elle)
    # SOURIRE LARGE = 12 + 10 + 16 + 25 : sourire franc, lèvre supérieure relevée et lèvre inférieure abaissée, mâchoire à peine entrouverte (dents du haut et du bas visibles)
    "sourire_large": {"smile_duchenne": 1.0, "upper_lip_raise": 0.4, "lower_lip_depress": 1.0, "_jaw": 7.0},
    "rire": {"smile_duchenne": 1.0, "eye_squint": 0.4, "upper_lip_raise": 0.6, "lower_lip_depress": 1.0, "_jaw": 12.0},
    # SURPRISE = 1+2+5+26/27
    "surprise": {"brow_up": 1.0, "brow_inner_up": 0.4, "eye_wide": 1.0, "forehead_wrinkles": 1.0, "_jaw": 16.0},
    # TRISTESSE = 1+4+15 (page FACS : « Sadness 1+4+15 ») ; + AU17 (menton), paupières supérieures affaissées et regard légèrement baissé (DESCRIPTIONS_EXPRESSIONS.md)
    "tristesse": {"brow_inner_up": 1.0, "brow_down": 0.6, "brow_together": 0.6, "forehead_wrinkles": 0.4, "glabella_wrinkles": 0.6, "blink_L": 0.25, "blink_R": 0.25, "mouth_down": 1.0, "chin_raise": 0.7, "_gaze": [0.0, -8.0]},
    # COLÈRE = 4+5+7+23 ; commissures légèrement abaissées, narines dilatées, rides verticales de la glabelle (la mâchoire qui avance : non couverte)
    "colere": {"brow_down": 1.0, "brow_together": 0.8, "glabella_wrinkles": 1.0, "eye_wide": 0.7, "eye_squint": 0.5, "lips_press": 1.0, "mouth_down": 0.3, "nostril_flare": 0.6},
    # PEUR = 1+2+4+5+7+20+26 (page FACS) ; rides du front et de la glabelle, narines
    "peur": {"brow_up": 0.8, "brow_inner_up": 0.8, "brow_down": 0.3, "brow_together": 0.6, "forehead_wrinkles": 0.8, "glabella_wrinkles": 0.6, "eye_wide": 1.0, "eye_squint": 0.3, "lip_stretch": 1.0, "nostril_flare": 0.4, "_jaw": 8.0},
    # DÉGOÛT = 9+15+17 (page FACS) / 9 ou 10 : nez plissé (plis sur la racine), lèvre supérieure relevée, joue poussée vers le haut, sillon naso-génien profond, menton relevé ; commissures NON tirées vers l'extérieur
    "degout": {"nose_wrinkle": 1.0, "nose_bridge_wrinkles": 1.0, "upper_lip_raise": 1.0, "cheek_raise": 0.5, "nasolabial_deepen": 1.0, "chin_raise": 0.6, "brow_down": 0.3},
    # MÉPRIS = R12A + R14A (page FACS) : demi-sourire d'un seul côté + durcissement/fossette du coin, pas d'AU6
    "mepris": {"smile_L": 0.5, "dimpler_L": 1.0},
    "clignement": {"blink_L": 1.0, "blink_R": 1.0},
}
# Clé « _jaw » : angle d'ouverture de la mâchoire en degrés, appliqué à l'os `jaw` si le squelette est installé (le correctif `mouth_open` suit alors tout seul).
NATIVE_CONTROLS = tuple(control for control in CONTROLS if control[0] not in REMOVED_IN_SCHEMA_10 and control[0] not in MERGED_IN_SCHEMA_10)

# Schéma 10 (lot 4, I-45, D-18) : facteur d'amplitude des contrôles « timides », selon l'âge. Un tuple = facteur aux stades d'âge
# 0 (5 ans), 1 (15 ans), 2 (30 ans), 3 (75 ans), interpolé linéairement entre eux. Source : `AMPLITUDES_CONTROLES.md` §9
# (matrice sexe x âge, 1 008 mesures) : ×6 là où ×6 est sûr, ×3 là où ×3 est sûr, ×1 là où des problèmes apparaissent déjà à ×3
# (valeur prudente entre ×1 et ×3, non affinée). Un contrôle absent de ce tableau garde l'amplitude d'origine.
# Lot 3 bis : `lips` + `lip_thickness` et `jaw` + `jaw_angle` sont sommés sous un seul contrôle ; les facteurs des deux parties sont
# abaissés (essai : ×0,75 à l'âge adulte pour les deux paires, ×0,5 pour la mâchoire du senior) pour qu'aucune face de cage ne se retourne.
# Plafonnés après essai (lot 4) : `chin`, `jaw_angle` (enfant), `lip_thickness`, `mouth_corner` (enfant), `facial_asymmetry` (adulte ×2
# au lieu de ×3) : une face de cage se retournait à un âge intermédiaire (SUIVI §4 P, T-N5). Défaut préexistant, non corrigeable par
# un facteur : `facial_asymmetry` à −1 retourne déjà 1 face à ×1 (amplitude d'origine) à sexe 0 et âge 1,25.
# Non traités : `fat_face` et `muscles_abdomen` (expressions bornées à ±1, à reformuler).
AMPLITUDE_FACTORS = {
    "cheeks": (3, 3, 3, 3), "chin": (5, 5, 6, 6), "ears_angle": (3, 3, 3, 3), "ears_size": (3, 3, 3, 3),
    "eye_height": (3, 3, 6, 6), "eyelid_aperture": (6, 6, 6, 6), "facial_asymmetry": (1, 1, 2, 1), "forehead": (6, 6, 6, 6),
    "jaw": (3, 3, 4.5, 3), "jaw_angle": (5, 5, 4.5, 3), "lip_thickness": (1.9, 1.9, 4.5, 3), "lips": (4.5, 4.5, 4.5, 6),
    "mouth": (3, 3, 6, 6), "mouth_corner": (2, 2, 6, 3), "muscle_definition": (6, 6, 6, 6), "nose_bridge": (1, 1, 3, 3),
    "nose_length": (3, 3, 3, 3), "nose_width": (3, 3, 3, 3),
}


def amplitude(control, age):
    """Facteur d'amplitude du contrôle à l'âge donné (stade 0 à 3), 1 si le contrôle n'est pas amplifié."""
    factors = AMPLITUDE_FACTORS.get(control)
    if not factors:
        return 1.0
    return float(sum(f * max(0.0, 1.0 - abs(age - stage)) for stage, f in enumerate(factors)))
CURRENT_SCHEMA = 9
BASE_ID = "blender_studio_realistic_v1"


def property_name(identifier):
    return "hm_" + identifier


def key_name(identifier, corrective=False, pole=None):
    name = "HM · " + identifier + (" · correction" if corrective else "")
    if pole:
        name += " · " + pole
    return name


def bind_control(key, owner_keys, identifier, corrective=False, pole=None):
    driver = key.driver_add("value").driver
    driver.type = "SCRIPTED"
    for variable in tuple(driver.variables):
        driver.variables.remove(variable)
    control = driver.variables.new()
    control.name = "amount"
    control.type = "SINGLE_PROP"
    control.targets[0].id_type = "KEY"
    control.targets[0].id = owner_keys
    control.targets[0].data_path = f'["{property_name(identifier)}"]'
    driver.expression = "amount"
    if identifier == "body_mass":
        for name,path in (("fat",'["hm_adiposity"]'),("bulk",'["hm_corpulence"]')):
            variable=driver.variables.new();variable.name=name;variable.type="SINGLE_PROP"
            variable.targets[0].id_type="KEY";variable.targets[0].id=owner_keys;variable.targets[0].data_path=path
        driver.expression = "(max(amount,0)+.35*min(amount,0))*(1-.35*abs(fat))*(1-.15*abs(bulk))"
    if identifier == "adiposity":
        driver.expression = "(max(amount,0)+.4*min(amount,0))"
    if identifier.startswith("fat_") or identifier == "muscle_definition":
        overall = driver.variables.new()
        overall.name = "fat"
        overall.type = "SINGLE_PROP"
        overall.targets[0].id_type = "KEY"
        overall.targets[0].id = owner_keys
        overall.targets[0].data_path = '["hm_adiposity"]'
        if identifier.startswith("fat_"):
            effective = "min(max(fat+amount,-1),1)"
            driver.expression = f"(max({effective},0)+.4*min({effective},0)-max(fat,0)-.4*min(fat,0))"
        else:
            driver.expression = "amount*(1-.7*max(fat,0))"
    if identifier.startswith("muscles_"):
        overall = driver.variables.new()
        overall.name = "overall"
        overall.type = "SINGLE_PROP"
        overall.targets[0].id_type = "KEY"
        overall.targets[0].id = owner_keys
        overall.targets[0].data_path = '["hm_muscles"]'
        # The global key already contributes overall * sum(regional fields).
        # This correction makes each effective region clamp(overall+amount).
        driver.expression = "(min(max(overall+amount,-1),1)-overall)"
    if pole == "gain":
        driver.expression = "max(amount,0)"
    elif pole == "perte":
        driver.expression = "max(-amount,0)"
    if corrective:
        morph = driver.variables.new()
        morph.name = "morph"
        morph.type = "SINGLE_PROP"
        morph.targets[0].id_type = "KEY"
        morph.targets[0].id = owner_keys
        morph.targets[0].data_path = 'key_blocks["Morphologie"].value'
        driver.expression += "*morph"
