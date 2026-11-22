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
    ("jaw", "Largeur de la mâchoire"),
    ("chin", "Avancée du menton"),
    ("cheeks", "Pommettes"),
    ("nose_length", "Avancée du nez"),
    ("nose_width", "Largeur du nez"),
    ("mouth", "Largeur de la bouche"),
    ("lips", "Relief des lèvres"),
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
NATIVE_CONTROLS = tuple(control for control in CONTROLS if control[0] not in REMOVED_IN_SCHEMA_10)
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
