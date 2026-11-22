# ECART_FONCTIONNALITES — ce que font les autres générateurs d'humains et que HumanLoom ne prévoit pas

Date : 2026-11-22. Branche `codex/natif`. Demande de l'utilisateur : lister les fonctionnalités des autres plugins qui ne sont **même pas planifiées** chez nous. Analyse seulement, aucun code d'autrui repris (licences : voir `RECHERCHE_PLUGINS.md`).

## Fiabilité des sources (à lire d'abord)

| Niveau | Outils | Origine de l'information |
|---|---|---|
| **A — dépôt lu en local** | MPFB2, CharMorph (+ packs) | `REFERENCE_PLUGINS.md`, `Audit-CharMorph-MPFB.md`, `RECHERCHE_PLUGINS.md` : structure, modules, docs lus ; rien exécuté |
| **B — résumés web, non revérifiés ici** | MB-Lab, Human Generator, Globalskin | `RECHERCHE_PLUGINS.md` (sources citées) |
| **C — connaissance générale, non vérifiée dans cette session** | Character Creator, Daz, MetaHuman, Human Generator (détails de fonctionnalités), MPFB2 (liste fine des fonctions) | **à confirmer avant toute décision** ; classé « à vérifier » dans le tableau |

Je n'ai relu aucun de ces outils aujourd'hui : la colonne « Source » dit d'où vient chaque ligne.

## Ce que HumanLoom prévoit déjà (`SUIVI_REPRISE.md` §9, `PLAN_SCHEMA_10.md`)

Lots 2 à 5 du schéma 10 (humain natif, contrôles regroupés, amplitudes ×6) ; repères automatiques (étape 7) ; nouveaux contrôles tronc/membres/visage et types de corps (8) ; UV, matériau de peau « HL Skin », yeux et dents (9) ; dents, langue, gencives (10) ; rig Rigify, expressions FACS/visèmes, « Bake pour export » (11) ; anatomie adulte optionnelle (12) ; cheveux et pilosité natifs, déjà livrés (11 zones, dont sourcils).

## Fonctionnalités des autres plugins **non planifiées** chez HumanLoom

| # | Fonctionnalité | Qui l'a | Source | Statut chez nous | Pourquoi ça compte |
|---|---|---|---|---|---|
| 1 | **Vêtements et accessoires ajustés au corps** (liaison par KDTree/BVH recalculée quand le corps change ; bibliothèque) | CharMorph (`fit_calc.py`), MPFB2 (proxies/clothes), Human Generator | A, A, C | **Cité dans `ROADMAP.md` D (« vêtements ») mais absent du plan §9 et sans conception** | C'est la première chose qu'un utilisateur ajoute à un personnage |
| 2 | **Bibliothèque / packs de personnages** (un personnage = données déclaratives + `.blend`, ajout sans code) | CharMorph (`config.yaml`, packs), MPFB2 | A | Idée notée (`REFERENCE_PLUGINS`) ; pas planifiée | Permet à des tiers d'ajouter des corps sans toucher au code |
| 3 | **Phénotypes / ethnicités** (curseurs ou mélanges de populations) | MPFB2 (macro-détails), MB-Lab, CharMorph (niveau L1 « base/ethnie ») | A, B, A | **Aucune mention de plan** (`UI_REVIEW`/`REFERENCE_PLUGINS` seulement en passant) ; HumanLoom n'a ni phénotypes ni teint par population | Variété immédiate des personnages ; sujet sensible (voir remarque en fin de document) |
| 4 | **Éditeur de morphs / création de nouvelles cibles par l'utilisateur** (MakeTarget, `cmedit`) | MPFB2, CharMorph | A | **Non planifié** (le plan ajoute des contrôles écrits par nous, pas par l'utilisateur) | Permet de prolonger le générateur sans passer par nous |
| 5 | **Peau texturée : grain de beauté, taches, cicatrices, tatouages, maquillage, rides par âge** (couches de textures/masques) | Human Generator, MB-Lab, MPFB2 (taches, veines) | B, B, A | Le matériau « HL Skin » (étape 9) vise teint et variation ; **tatouages, maquillage, cicatrices ne sont pas dans le plan** (cités seulement dans `RECHERCHE_PEAU.md`) | Très demandé en production |
| 6 | **Cils** (objet/pilosité dédiés) | Human Generator, MPFB2 | C, A | Les 11 zones de groom incluent les sourcils ; **les cils ne sont pas une zone** ; mention éparse dans `AJOUT_CONTROLES` | Détail visible en gros plan |
| 7 | **Ongles (mains, pieds)** | Human Generator, Character Creator | C | Cités dans `AJOUT_CONTROLES`/`DESIGN_NATIF` sans étape ; pas de planification | Les mains sont visibles dans tous les plans |
| 8 | **Bibliothèque de poses et d'animations / retargeting de capture de mouvement** (BVH, Mixamo, OpenPose) | MPFB2 (jeux de rigs, poses), CharMorph (`pose.py`), MB-Lab | A, A, B | Le **rig** est planifié (étape 11) mais **ni poses, ni catalogue de poses, ni retargeting de capture** | Sans poses, le personnage reste en T/A |
| 9 | **Rigs multiples pour moteurs de jeu** (Mixamo, Unreal/Unity « game engine », OpenPose) | MPFB2, CharMorph | A | Étape 11 : Rigify + bake export seulement ; **pas de rigs alternatifs** | Cible « jeu » |
| 10 | **Niveaux de détail (LOD) et maillage proxy basse résolution** | MPFB2 (proxies), Character Creator | A, C | **Non planifié** (`Analyse-modeles-ajoutes.md` mentionne le sujet) | Temps réel, foules |
| 11 | **Génération par lots / foules** (variations aléatoires en série) | Human Generator (batch), CharMorph (`randomize.py`) | C, A | HumanLoom a un opérateur « hasard » pour **un** personnage ; **pas de lot ni de foule** | Productions avec figurants |
| 12 | **Ajustement sur photo ou scan** (reconstruction d'un visage réel) | Character Creator, MetaHuman (outils tiers) | C | **Non planifié** (et sensible : voir fin de document) | Ressemblance avec une personne |
| 13 | **Style stylisé / « toonify »** (conversion non réaliste) | CharMorph (`toonify.py`) | A | La peau stylisée est prévue (matériau) ; **pas de morphologie stylisée** | Public animation |
| 14 | **Expressions complètes avec rides dynamiques (cartes de normales pilotées)** | Character Creator, MetaHuman | C | Expressions FACS/visèmes prévues (11) ; **rides pilotées par l'expression non prévues** | Réalisme des gros plans |
| 15 | **Simulation de tissu pour vêtements** | Character Creator, Daz | C | **Non planifié** (dépend de #1) | Vêtements crédibles |
| 16 | **Import/export de formats d'autres outils** (`.mhm` MakeHuman, FBX/glTF/USD optimisés moteur) | MPFB2, CharMorph | A | « Bake pour export » prévu ; **pas d'import des personnages d'autres outils** | Migration d'utilisateurs |
| 17 | **Assets du navigateur d'assets** (préréglages, silhouettes, matériaux, poses avec vignettes) | MPFB2, CharMorph (bibliothèques) | A | Idée dans `IDEES.md` §0 ; **pas d'étape dans le plan §9** | Intégration native promise par l'utilisateur |
| 18 | **Interface multilingue** (textes sources anglais + traductions) | MPFB2, CharMorph | A | Idée dans `IDEES.md` ; **pas d'étape** | Public hors francophone |
| 19 | **Cheveux « mesh » en bibliothèque (coiffures prêtes, ajustées par shrinkwrap)** | CharMorph (`HairFitter`), MPFB2, Human Generator | A, A, C | Choix inverse : cheveux procéduraux natifs ; **pas de bibliothèque de coiffures prêtes** (les préréglages sont des points de départ artistiques) | Gain de temps ; choix de conception à assumer |

## Ce qui est sans doute inutile de copier

- **Rig non morphé en temps réel** (CharMorph) : HumanLoom vise mieux (méta-rig recalculé depuis le maillage évalué, `RECHERCHE_RIG.md`, **à démontrer**).
- **Textures par jeu 4K** (MB-Lab, CharMorph) : le choix « un matériau de peau par groupe de nœuds » (`RECHERCHE_PLUGINS.md` §2) évite la dépendance aux textures — mais n'est pas prouvé visuellement.

## Remarques

1. **Sujets sensibles** (#3 phénotypes, #12 photo/scan) : ils posent des questions de représentation, de consentement et de licences de données. Je les liste parce que tu l'as demandé, **pas** comme recommandation de les faire ; ils demandent une décision explicite.
2. **Licences** : MPFB2 et CharMorph sont sous GPL ; les packs MB-Lab sous AGPL. Toute reprise de code ou de données exige ta décision (`RECHERCHE_PLUGINS.md`).
3. **Priorité proposée (à valider)** : #1 vêtements, #8 poses, #5 couches de peau (tatouages, cicatrices), #6 cils et #7 ongles (petits, forte valeur visuelle), puis #17 et #18 (intégration Blender déjà voulue). Les #10, #11, #12, #14, #15 sont des chantiers lourds, à garder pour après le rig.
4. **Limite** : les lignes de niveau C n'ont pas été relues ; avant de planifier, une passe de vérification sur les documentations officielles est nécessaire.
