"""Prototype : couleur de base (albédo diffus, RVB linéaire) de la peau à partir de fractions de mélanine et d'hémoglobine.
Modèle : Donner & Jensen 2006/2008 (équations 3 à 8 pour l'absorption et la diffusion réduite), spectres d'hémoglobine d'OMLC (S. Prahl, Gratzer/Kollias),
épiderme 0,25 mm sur derme semi-infini combinés par Kubelka-Munk (K = 2 µa, S = s_scale·µs' avec s_scale = 0,4 : réglage provisoire choisi pour obtenir une teinte beige chaud plausible, **pas ajusté sur des mesures**), puis intégration spectrale 400-700 nm
(fonctions colorimétriques CIE approchées par Wyman et al. 2013, éclairage D65 approché par un corps noir à 6504 K).
Prototype non calibré sur des mesures : à valider (voir VALIDATION_SCIENTIFIQUE.md). Pur numpy (aucune dépendance Blender)."""
import numpy as np

LAM = np.arange(400.0, 701.0, 5.0)  # nm
_HB = np.array([  # nm, HbO2, Hb  (cm-1/M) — OMLC
    (400, 266232, 223296), (410, 466840, 303956), (420, 480360, 407560), (430, 246072, 528600), (440, 102580, 413280),
    (450, 62816, 103292), (460, 44480, 23388.8), (470, 33209.2, 16156.4), (480, 26629.2, 14550), (490, 23684.4, 16684),
    (500, 20932.8, 20862), (510, 20035.2, 25773.6), (520, 24202.4, 31589.6), (530, 39956.8, 39036.4), (540, 53236, 46592),
    (550, 43016, 53412), (560, 32613.2, 53788), (570, 44496, 45072), (580, 50104, 37020), (590, 14400.8, 28324.4),
    (600, 3200, 14677.2), (610, 1506, 9443.6), (620, 942, 6509.6), (630, 610, 5148.8), (640, 442, 4345.2), (650, 368, 3750.12),
    (660, 319.6, 3226.56), (670, 294, 2795.12), (680, 277.6, 2407.92), (690, 276, 2051.96), (700, 290, 1794.28)])


def _blood_mu_a(eps):  # mm^-1 pour du sang total à 150 g/L
    return 2.303 * eps * 150.0 / 64500.0 / 10.0


A_OXY = _blood_mu_a(np.interp(LAM, _HB[:, 0], _HB[:, 1]))
A_DEOXY = _blood_mu_a(np.interp(LAM, _HB[:, 0], _HB[:, 2]))
A_EU = 6.6e10 * LAM ** -3.33
A_PHEO = 2.9e14 * LAM ** -4.75
A_BASE = 0.0244 + 8.53 * np.exp(-(LAM - 154.0) / 66.2)
MU_S = 14.74 * LAM ** -0.22 + 2.2e11 * LAM ** -4.0  # diffusion réduite, épiderme (mm^-1)


def _g(l, mu, s1, s2):
    s = np.where(l < mu, s1, s2)
    return np.exp(-0.5 * ((l - mu) / s) ** 2)


def cmf(l):
    x = 1.056 * _g(l, 599.8, 37.9, 31.0) + 0.362 * _g(l, 442.0, 16.0, 26.7) - 0.065 * _g(l, 501.1, 20.4, 26.2)
    y = 0.821 * _g(l, 568.8, 46.9, 40.5) + 0.286 * _g(l, 530.9, 16.3, 31.1)
    z = 1.217 * _g(l, 437.0, 11.8, 36.0) + 0.681 * _g(l, 459.0, 26.0, 13.8)
    return x, y, z


def blackbody(l_nm, T=6504.0):
    l = l_nm * 1e-9
    return 1.0 / (l ** 5 * (np.exp(1.4388e-2 / (l * T)) - 1.0))


_X, _Y, _Z = cmf(LAM)
_ILL = blackbody(LAM)
_M = np.array([[3.2406, -1.5372, -0.4986], [-0.9689, 1.8758, 0.0415], [0.0557, -0.2040, 1.0570]])  # XYZ -> sRGB linéaire (D65)


def _to_linear_rgb(refl):
    xyz = np.array([np.sum(refl * _ILL * _X), np.sum(refl * _ILL * _Y), np.sum(refl * _ILL * _Z)])
    white = np.array([np.sum(_ILL * _X), np.sum(_ILL * _Y), np.sum(_ILL * _Z)])
    rgb = _M @ (xyz / white[1]); wrgb = _M @ (white / white[1])
    return rgb / wrgb  # le blanc parfait donne (1, 1, 1)


def _km_infinite(K, S):
    a = 1.0 + K / S
    return a - np.sqrt(a * a - 1.0)


def reflectance(Cm, Ch, m=0.7, oxy=0.75, d_epi=0.25, s_scale=0.4):
    a_epi = Cm * (m * A_EU + (1 - m) * A_PHEO) + (1 - Cm) * A_BASE
    a_derm = Ch * (oxy * A_OXY + (1 - oxy) * A_DEOXY) + (1 - Ch) * A_BASE
    Ke, Se = 2 * a_epi, s_scale * MU_S
    Kd, Sd = 2 * a_derm, s_scale * MU_S * 0.5
    Rg = _km_infinite(Kd, Sd)
    a = 1.0 + Ke / Se; b = np.sqrt(a * a - 1.0)
    bsd = b * Se * d_epi
    coth = 1.0 / np.tanh(bsd)
    return (1.0 - Rg * (a - b * coth)) / (a - Rg + b * coth)


def skin_rgb(Cm, Ch, m=0.7):
    return tuple(float(np.clip(c, 0, 1)) for c in _to_linear_rgb(reflectance(Cm, Ch, m)))


def srgb_encode(c):
    c = np.clip(np.array(c), 0, 1)
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * c ** (1 / 2.4) - 0.055)


if __name__ == "__main__":
    ones = np.ones_like(LAM)
    print("CMF équi-énergie X,Y,Z :", [round(float(np.sum(v)), 2) for v in (_X, _Y, _Z)], " blanc parfait RVB :", [round(float(c), 3) for c in _to_linear_rgb(ones)])
    for Cm in (0.005, 0.02, 0.05, 0.10, 0.20, 0.35):
        row = []
        for Ch in (0.002, 0.01, 0.03):
            lin = skin_rgb(Cm, Ch)
            row.append("%s -> sRGB %s" % (tuple(round(c, 3) for c in lin), tuple(int(v * 255) for v in srgb_encode(lin))))
        print("Cm=%.3f" % Cm, " | ".join(row))
