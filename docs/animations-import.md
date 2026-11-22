# Importer ses propres animations dans HumanLoom

HumanLoom **ne fournit aucune animation**. La galerie lit une bibliothèque qui vous appartient et que vous remplissez avec vos fichiers. Ce guide explique comment les obtenir (notamment depuis Unreal Engine 5) et les importer.

> **Licence — à lire avant tout.** Les animations, mannequins et personnages d'Unreal Engine, de ses projets d'exemple (Game Animation Sample, Lyra…), de MetaHuman ou d'une boutique restent soumis à **leurs propres licences**, qui limitent en général leur usage à des projets Unreal. **Vous êtes seul responsable de vos droits** sur les fichiers que vous importez. HumanLoom ne contient aucune donnée Epic ni aucune animation tierce, et n'en redistribue pas ; la bibliothèque, l'index et les miniatures sont créés dans **votre** dossier, hors du dépôt et hors du paquet de l'extension.

## 1. Obtenir ses animations

### Méthode recommandée : exporter tout un projet Unreal avec l'outil du dépôt

Le dossier `tools/unreal_export/` contient les scripts d'export de l'outil personnel de l'auteur (« UnrealBlenderBridge »), qui s'exécutent **dans l'éditeur Unreal**. Ils exportent toutes les `AnimSequence` d'un projet en FBX et écrivent les métadonnées que la galerie sait lire.

**Prérequis**
- Unreal Engine avec le plugin **Python Editor Script Plugin** activé. L'outil indique avoir été utilisé avec **Unreal Engine 5.8** (le dossier d'export de l'auteur est marqué 5.8.4). **Nous n'avons pas testé d'autre version d'Unreal, ni cette procédure sur votre projet** : seul le lot d'import côté Blender est testé, sur des fichiers synthétiques.
- Faire **File > Save All** avant l'export : la détection des changements lit les `.uasset` enregistrés.
- Des animations dont vous détenez les droits d'usage (voir l'avertissement de licence en tête de ce guide).

**Procédure**
1. Dans la console de l'éditeur Unreal (ou *Tools > Execute Python Script*), vérifier l'API : `py "<dépôt>/tools/unreal_export/unreal/ue_probe.py"` (chaque ligne doit afficher OK).
2. Lancer l'export : `py "<dépôt>/tools/unreal_export/unreal/run_export.py"`. Options utiles : `--analyze-only` (inventaire sans export), `--out D:/Export`, `--root /Game/Characters`, `--filter Locomotion`. L'export est incrémental (les animations inchangées sont sautées).
3. Sortie par défaut : `<Projet>/Saved/BlenderExport/` avec `manifest.json`, `inventory.json`, `export_report.json` et `animations/<squelette>/<dossier Unreal>/<Nom>.fbx` (FBX 2020, sans maillage, temps local).
4. Dans HumanLoom, importer **ce dossier** (bouton « Importer un dossier » de la galerie, ou `importer.import_sources`, voir §2). Ne pointez pas la bibliothèque HumanLoom vers ce dossier : c'est la source, elle n'est jamais modifiée.

**Ce que l'import en tire** (au lieu de l'heuristique) : quand un `manifest.json` est trouvé au-dessus des FBX, chaque FBX listé dans ses `animations` reprend les valeurs **déclarées** : nom, dossier Unreal (devient la catégorie), squelette, cadence, root motion, additif. Les FBX du dossier qui ne sont pas des animations déclarées (par exemple les maillages de `characters/`) sont **ignorés** et comptés comme tels. L'empreinte SHA-1 du FBX est comparée à celle du manifest : un écart produit un avertissement dans le rapport (fichier modifié depuis l'export ?), sans bloquer l'import. Un FBX isolé, sans manifest au-dessus de lui, retombe sur l'heuristique décrite plus bas.

### Depuis Unreal Engine 5 (FBX), à la main

1. Dans le navigateur de contenu, clic droit sur l'**Animation Sequence** → *Asset Actions* → *Export…* (ou *Export* dans la barre de l'éditeur d'animation).
2. Choisissez le format **FBX** et un dossier dont **le nom sera la catégorie** dans la galerie (voir §3).
3. Dans la fenêtre d'options FBX, gardez la version FBX proposée (Epic documente FBX 2020 pour l'import dans Unreal ; HumanLoom importe via Blender 5.2) et laissez les animations activées.
4. Exportez une animation par fichier. Un dossier de fichiers FBX convient très bien.

Points à connaître (sources en fin de document) :
- **Échelle** : Unreal travaille en centimètres, Blender en mètres. HumanLoom importe sans reconversion cachée et **note la hauteur du squelette au repos** (`ualm_rest_height`) pour que l'application sur un personnage corrige l'échelle (lot ultérieur). Une animation « minuscule » ou « géante » après import signale ce décalage.
- **Root motion** : un FBX ne déclare pas si l'animation porte du root motion. HumanLoom pose le drapeau `root_motion` si l'os racine se déplace de plus de 5 % de la hauteur du squelette (règle mesurée, pas une information de la source). Un déplacement de l'os racine peut être faussé par un export Blender qui ajoute un os supplémentaire au-dessus de la racine (problème connu des FBX Blender → Unreal).
- **Additif** : le caractère additif n'est pas lu dans un FBX ; le drapeau n'existe que pour les actions dont les métadonnées `ualm_flags` le portent déjà (cas d'un .blend produit par l'outil UALM).
- **Squelette** : l'identité du squelette est le **nom de l'objet armature** du fichier. Deux animations du même squelette doivent donc avoir des os de mêmes noms ; l'application sur un autre rig demandera un retargeting (lot ultérieur).

### Depuis un autre format
- **BVH** (capture de mouvement) : cadence lue dans l'en-tête (`Frame Time`). Le nom du squelette est le nom du fichier.
- **glTF / GLB** : le format stocke des secondes, pas des images : l'import utilise la cadence demandée (30 i/s par défaut, option `fps`).
- **Un .blend contenant des actions** (vos propres fichiers ou un export de l'outil UALM) : les actions sont copiées **une par une** ; les métadonnées `ualm_*` existantes (catégorie, squelette, cadence, drapeaux) sont conservées. Si le .blend est volumineux (1 Go ou plus), l'import est lent (une lecture du fichier par action) : utilisez le filtre par nom ou la limite.

## 2. Importer

L'import se fait dans un **processus Blender séparé** par fichier : si un fichier est corrompu ou plante, les autres continuent et l'échec est consigné.

Depuis un script ou la console Python de Blender (l'interface de la galerie viendra avec l'enregistrement de l'extension) :

```python
import bpy
from bl_ext.user_default.human_modeling.animation import importer   # « user_default » : nom de votre dépôt d'extensions
rapport = importer.import_sources(
    ["D:/mes_animations_fbx"],            # fichiers et/ou dossiers (parcours récursif)
    "D:/MaBibliothequeHumanLoom",         # dossier de bibliothèque à vous
    bpy.app.binary_path,
)
print(rapport["ajoutées"], rapport["doublons"], rapport["inchangés"], rapport["échecs"])
```

- La **bibliothèque** est un dossier qui contient `HumanLoom_Actions.blend` (les actions) et `inventory.json` (l'index lu par la galerie). Choisissez un dossier **dédié** : un dossier contenant déjà l'`inventory.json` d'un autre outil est refusé, pour ne jamais modifier une bibliothèque qui n'est pas la vôtre.
- **Vos fichiers sources ne sont jamais écrits** : le rapport indique `sources_modifiées` (vide) d'après une empreinte SHA-256 avant et après.
- **Doublons** : un fichier déjà importé (mêmes octets) est « inchangé » ; une animation de contenu identique sous un autre nom ou dans un autre fichier est un « doublon » (empreinte des courbes) et n'est pas ajoutée deux fois.
- **Rapport** : chaque fichier a un statut (`importé`, `doublon`, `inchangé`, `ignoré` pour un FBX non déclaré d'un dossier d'export, `échec` avec le message), la provenance des métadonnées (`déclarées (manifest.json)` ou `heuristique`) et un éventuel avertissement. Les chemins locaux sont retirés des messages.

## 3. Catégories, favoris, recherche

- La **catégorie** est le dossier de la source relatif au dossier importé (`Marche/Rapide/…`), ou, pour un .blend, la catégorie déjà présente dans les actions, sinon « Importées/<nom du fichier> ». Elle est corrigeable à la main dans la galerie ; les favoris et corrections sont gardés dans le dossier utilisateur de Blender.
- La recherche est instantanée (préfixes, plusieurs mots).

## 4. Limites connues (mesurées ou documentées)

- Aucune conversion d'axes ni d'échelle n'est appliquée à l'import ; elle sera faite à l'application sur le personnage.
- Le root motion et l'additif ne sont pas déclarés par un FBX (voir plus haut).
- Un FBX **ASCII** n'est pas pris en charge par l'importeur de Blender 5.2 (échec consigné) ; utilisez le FBX binaire.
- Un FBX contenant plusieurs animations crée plusieurs actions (une entrée chacune).
- Ni le retargeting vers un autre squelette, ni l'export vers Unreal ne sont faits dans cette étape.
- Ce guide n'a pas été validé sur des fichiers Unreal réels ni sur votre version d'Unreal (les tests utilisent des fichiers synthétiques, dont un faux dossier d'export avec manifest.json, générés par les scripts de `tools/`).

## Sources consultées
- Epic Games, [FBX Animation Pipeline in Unreal Engine](https://dev.epicgames.com/documentation/unreal-engine/fbx-animation-pipeline-in-unreal-engine) : version FBX 2020 attendue, animations à activer à l'export.
- Forum Unreal, [Blender to UE4 root motion not working](https://forums.unrealengine.com/t/blender-to-ue4-root-motion-not-working/109988) : os supplémentaire au-dessus de la racine dans les FBX Blender.
- Blender, [Scale problems when export to Unreal #99075](https://developer.blender.org/T99075) : unité Blender 1 m contre Unreal 1 cm, facteur 0,01.
- Blender, documentation de l'API 5.2 (`BlendDataLibraries`) : lecture des noms de blocs sans chargement ; le chargement d'une seule action par appel est une consigne de prudence mesurée sur Blender 5.2 (plantage constaté en chargeant plusieurs types de blocs).
