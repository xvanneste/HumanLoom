# REFERENCE_PLUGINS — Références dans `G:\_dev\BlenderDev`

**Profondeur de l'étude : première passe, limitée.** J'ai lu les licences, la liste des fichiers des archives et `docs/code-structure.md` de MPFB2. Je n'ai pas extrait ni lu le code source des plugins, ni ouvert les modèles. Aucun code n'a été copié.

| Élément | Licence observée | Notes |
|---|---|---|
| `mpfb2-master.zip` (MPFB2, MakeHuman Plugin For Blender) | Code **GPLv3** (`LICENSE.CODE.md`) ; assets **CC0** (`LICENSE.ASSETS.md`) ; sortie des modèles : voir section D de `LICENSE.md` | Réutilisation de code possible sous GPLv3 (HumanLoom est GPL-3.0-or-later) mais à vérifier fichier par fichier et à créditer. Assets : vérifier au cas par cas. |
| `CharMorph-downloader.zip` | Code **GPLv3** (`license.txt`, © 2020-2021 Michael Vigovsky) | Ce n'est que le « downloader » (75 fichiers : `morphing.py`, `rigify.py`, `randomize.py`, `pose.py`, `library.py`, `toonify.py`…). Les assets sont téléchargés séparément avec leurs licences propres. |
| `human-base-meshes-bundle-v1.4.1.zip` | **Non vérifiée** | Un `.blend` de 49 Mo (corps, têtes, yeux, mains, crâne…). Licence à lire avant tout usage. `extension/CREDITS.md` mentionne la provenance de la base HumanLoom. |
| `Beautiful_girl_…_3D_print`, `FREE_Stylized_Basemesh…`, `Ultimate_Metahuman_Body…` | **Non vérifiées** (modèles tiers FBX/Maya/MetaHuman) | Références visuelles uniquement tant que la licence n'est pas lue. |

## Enseignements architecturaux (MPFB2, d'après `docs/code-structure.md`)

- Trois couches : `services/` (singletons sans état, méthodes statiques), `entities/` (modèles de données), `ui/` (panneaux et opérateurs), plus `data/` passif ; la dépendance va dans un seul sens.
- Enregistrement centralisé : un `ClassManager` collecte les classes puis les enregistre ; imports différés dans `register()`.
- Tests dans un dossier `test/` exécuté dans Blender ; documentation technique par domaine ; `pyrightconfig.json` et `.pylintrc`.
- Idées applicables à HumanLoom : séparer `__init__.py` en couches, un enregistrement centralisé de classes, un vrai dossier de tests avec lanceur, docs par module.

## CharMorph — analyse (dépôts clonés le 2026-11-21, analyse seule, rien exécuté ni copié)

Dépôts dans `G:\_dev\BlenderDev` : `CharMorph` (add-on, commit `ec5e13d`, 2024-10-10), `CharMorph-db` (base, `a8512ac`, 2023-12-11), packs `CharMorph-Vitruvian`, `-Antonia`, `-Reom`, `-MB-Lab-Female`, `-MB-Lab-Male`. Portée de la lecture : structure, `lib/morpher*.py`, `lib/morphs.py`, `lib/fit_calc.py`, `lib/charlib.py` en partie, configs YAML des personnages. Je n'ai pas lu `rigging.py`, `hair.py` ni `materials.py` en détail, ni exécuté l'add-on : les points ci-dessous qui s'y rapportent viennent des noms de classes et de la config.

**Licences observées :** code de l'add-on GPLv3 (`license.txt`). Packs : Vitruvian et Reom — licence non confirmée dans les fichiers lus (README/`config.yaml`, `lists.json` annonce CC0 et CC-BY) ; Antonia a un `license.txt` avec conditions de dérivation ; MB-Lab Female/Male sous AGPL (fichier `LICENSE`). `CharMorph-db` n'a pas de fichier de licence à la racine. À lire avant toute réutilisation.

### Architecture
- Séparation nette : un paquet `lib/` (logique, indépendant de l'UI, avec `charlib`, `morpher`, `morphs`, `fitting`, `rigging`, `hair`, `materials`, `drivers`) et des modules racine pour l'UI (`morphing.py`, `rig.py`, `hair.py`, `finalize.py`, `library.py`…). C'est le découpage que `ARCHITECTURE.md` propose pour HumanLoom.
- Données séparées du code : le personnage est décrit par un `config.yaml` (objet, base, matériaux, assets, armatures, cheveux), des fichiers de morphs, un `char.blend`, des poids et des joints. Ajouter un personnage ne demande pas de code.
- Niveaux de morphs : L1 (base/ethnie, vecteur complet `.npy`), L2 (morphs fins `.npz` par base), L3 ; métapropriétés (`morphs_meta.yaml`, ex. section `age` qui mappe des morphs vers deux valeurs) qui pilotent plusieurs morphs d'un coup.

### Morphing et performance
- Deux moteurs : `ShapeKeysMorpher` (clés de forme) et `NumpyMorpher` (somme de deltas numpy appliquée sur un tableau de sommets), plus `AltTopoMorpher` pour appliquer les morphs à une autre topologie. Chargement paresseux des morphs (`LazyMorph*`), formats compacts `.npy/.npz` avec morphs partiels (indices + deltas : `PartialMorph`). Un message d'erreur est produit si le nombre de sommets diffère.
- Comparé à HumanLoom : HumanLoom pilote des shape keys par drivers (simples, natifs, sauvegardés dans le `.blend`). Le moteur numpy est un modèle pour mesurer/optimiser si les sliders deviennent lents ; aucune mesure de performance n'a été faite ici, donc aucun gain n'est établi.

### Ajustement de vêtements et accessoires
- `fit_calc.py` : liaison asset→corps par `KDTree` (16 plus proches voisins), puis raffinement par `BVHTree` (distance aux faces, coordonnées barycentriques), et liaison inverse ; `SoftBinder` / `HardBinder`, `fitting_subset.npz` pour restreindre la géométrie. Le tout se recalcule quand le corps change. Piste pour les vêtements de HumanLoom (absents aujourd'hui).

### Rig, cheveux, matériaux
- Rig créé à la finalisation (Rigify complet avec visage, ou ARP, ou rigs fournis) ; les joints et poids sont des données du personnage, `sliding_joints.py` ajuste les articulations. README : le rig n'est pas morphé en temps réel.
- Cheveux : `HairFitter` hérite du calcul d'ajustement ; coiffures en bibliothèque `.blend`, ajustées par shrinkwrap/objet « scalp ». HumanLoom utilise au contraire des Hair Curves natives générées procéduralement : approches différentes, non comparables sans test.
- Matériaux : bibliothèque partagée (`shared_lib.blend`), textures par jeu (ex. 4K), couleur de peau et d'yeux directe, déplacement par matériau.

### Enseignements retenus
1. Données de personnage déclaratives (YAML) + code générique.
2. Morphs creux (indices + deltas) et chargement paresseux pour limiter mémoire et temps.
3. Métasliders qui agrègent des morphs fins (âge, etc.).
4. Logique dans `lib/` sans UI, testable.
5. Ajustement d'assets par binding recalculé, utile quand HumanLoom aura des vêtements.

### Limites et risques
- Base de morphs d'origine MB-Lab/ManuelbastioniLAB (AGPL) : à ne pas mélanger au code GPL de HumanLoom sans analyse juridique.
- Version `0.4.0` pour Blender 4.4 : compatibilité 5.2 non vérifiée.
- Non étudié : `randomize.py`, `pose.py`, `toonify.py`, `cmedit/` (édition de personnage), éditeur de morphs.

## À étudier ensuite

MPFB2 (services de cibles, rig, proxies, matériaux de peau), le code de `rigging.py`/`hair.py`/`materials.py` de CharMorph, les trois modèles tiers et le bundle de maillages (licences). Décisions de réutilisation : uniquement après lecture de licence et accord.
