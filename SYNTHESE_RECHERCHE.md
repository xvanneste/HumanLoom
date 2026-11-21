# SYNTHESE_RECHERCHE — peau, morphologie, rig, mapping : ce qu'on en tire

Date : 2026-11-21. À lire avec `RECHERCHE_PEAU.md`, `RECHERCHE_MORPHOLOGIE.md`, `RECHERCHE_RIG.md`, `RECHERCHE_PLUGINS.md`. Public visé : **film, rendu stylisé et réaliste (D-12)**. Tout ce qui suit est une **proposition** ; rien n'est testé dans HumanLoom ; plusieurs sources sont des extraits à relire (⚠).

## 1. Constats principaux

1. **Peau** : la science donne un cadre clair (deux couches, mélanine + hémoglobine + huile, diffusion par canal) mais Blender n'en expose qu'une approximation (Principled, Random Walk Skin, rayon RVB). Un **groupe de nœuds paramétrique** (comme MPFB2) est la bonne forme ; la **teinte se décrit par des grandeurs continues**, pas par un phototype (Fitzpatrick est un mauvais descripteur).
2. **Morphologie** : les modèles récents (STAR, Anny) confirment **les bases locales et les paramètres interprétables** déjà choisis (D-05). Les vrais manques de HumanLoom sont la **corpulence unifiée avec distribution régionale** (dépendant du sexe et de l'âge) et des **entrées anthropométriques** (taille, poids, tours).
3. **Rig** : Rigify est l'outil natif ; les autres plugins livrent rigs et poids en **données** ; le point différenciant possible est un **méta-rig placé automatiquement sur le maillage évalué** (régression linéaire de sommets, comme SMPL). Les expressions de film restent un chantier de **contenu** (FACS + visèmes, ARKit en option).
4. **Mapping (UV)** : **peu de sources ont été lues sur ce thème** (seulement la microgéométrie). C'est la lacune principale ; voir §3.

## 2. Ordre recommandé (proposition, à valider par l'utilisateur)

Les trois chantiers n'ont pas les mêmes dépendances :

| Chantier | Dépend de | Bloque |
|---|---|---|
| Tranche verticale native (nœuds, façade) | — | rig (articulations suivent l'identité), expressions |
| **Mapping/UV** | topologie fixe du corps (déjà figée par `realistic.blend`) ; **indépendant des nœuds** | textures, microrelief, matériaux d'âge |
| **Matériau de peau** | UV (pour masques/textures) ; **indépendant** des nœuds | rendu des essais de film |
| **Rig** | repères automatiques + identité en nœuds stable | expressions pilotées par rig, animation |

Donc : (1) **tranche verticale native** ; en parallèle possible (2) **audit et conception du mapping UV** (rapide, sans conflit) puis (3) **matériau de peau v1** (réaliste + stylisé) ; (4) **repères automatiques puis rig** ; (5) expressions et correctifs. Raisons : les textures et le microrelief dépendent du dépliage, qu'il faut figer **avant** de peindre/baker ; le rig dépend de l'architecture de nœuds, donc après elle.

## 3. Mapping : ce qu'on ne sait pas encore (à instruire avant toute décision)

- État mesuré (audit antérieur) : **1 UV** (`UVMap`) ; qualité du dépliage (îlots, coutures, étirement, densité de texel, symétrie, tête/corps/mains) **non évaluée**.
- Questions : une ou plusieurs UV ? UDIM pour le film (têtes/corps/mains) ? symétrie miroir vs unicité ? yeux, dents, langue séparés ? densité de texel pour le microrelief (pores ≈ 0,1 mm) ? compatibilité avec le niveau de subdivision au rendu ?
- Proposition : test **T-U1** (audit chiffré du dépliage actuel avec un script d'analyse, sans rien modifier) avant toute proposition de nouveau dépliage.

## 4. Candidats pour `IDEES.md` / `SUIVI_REPRISE.md`

- Groupe « HL Skin » (nœuds, entrées physiques, masques régionaux, curseur de style réaliste↔stylisé).
- Peau liée à l'âge (rides, taches, rayon SSS) — sans calibration clinique revendiquée.
- Distribution de graisse androïde↔gynoïde selon sexe/âge ; solveur « taille/poids/tour de taille ».
- Méta-rig Rigify placé par régression sur le maillage évalué ; poids calculés une fois ; correctifs de pose.
- Jeu d'expressions FACS + visèmes (+ compat ARKit 52).
- Tests proposés : T-S1…S3 (peau), T-M1…M2 (morpho), T-R1…R3 (rig), T-U1 (UV).

## 5. Risques et limites de cette recherche

- Résumés de recherche, **pas de relecture des équations** (Burley, Donner), pas de valeurs mélanine/hémoglobine extraites.
- Licences : SMPL (recherche), Anny (Apache 2.0), MPFB2/CharMorph (GPL), MB-Lab (AGPL) — **aucune reprise décidée**.
- Blender 5.2 n'a **pas été interrogé** sur le shading (manuel 4.x/dev cité) ; un module tiers évoque des « nœuds d'éclairage de matériau » en 5.3 (**hors périmètre 5.2**, D-13).
- Aucun test exécuté dans cette passe ; aucun fichier de l'extension modifié.
