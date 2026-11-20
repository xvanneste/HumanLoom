"""Editable artistic starting points; not measured composition categories."""

PROFILES = {
    "REFERENCE": ("Référence", 0., 0.),
    "MINCE": ("Mince", -1., -.5),
    "FITNESS": ("Fitness", -.6, .55),
    "MUSCLE": ("Musclé", -.15, 1.),
    "AMPLE": ("Ample", 1., 0.),
    "AMPLE_MUSCLE": ("Ample et musclé", 1., 1.),
    "VERY_LEAN": ("Très mince", -.7, -.5),
    "LARGE": ("Forte corpulence", 1., 0.),
}

EXTENDED_MASS={"VERY_LEAN":-1.,"LARGE":1.}

WHOLE_BODY={"REFERENCE":0.,"MINCE":-.65,"FITNESS":-.4,"MUSCLE":-.25,
            "AMPLE":.65,"AMPLE_MUSCLE":.65,"VERY_LEAN":-1.,"LARGE":1.}
