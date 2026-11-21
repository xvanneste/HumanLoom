# PLAN_SCHEMA_10 — migration schéma 9 → 10 (proposition à valider, rien n'est codé)

Date : 2026-11-21. Branche `codex/natif`. Ce plan découpe l'étape « 6. Migration schéma 10 » de `SUIVI_REPRISE.md` §9 et ses prérequis (étape 3, générateur de nœuds). **Distinction** : les faits viennent de mesures citées ; les **propositions** sont marquées « proposition » ; les **points à vérifier** sont des hypothèses non testées.

## 1. Objectif et règles qui s'imposent

Faire passer HumanLoom du schéma 9 (462 clés de forme, drivers sur `hm_*`) au schéma 10 : paramètres sur l'objet (façade D, UUID), identité du corps et du visage portée par le groupe de nœuds « HL Human » (D-05, D-07, D-14), amplitudes ×6 (D-18), contrôles redondants regroupés (I-46), **sans changer la forme d'un ancien fichier**.

| Règle | Source |
|---|---|
| Un ancien fichier garde sa forme d'origine au neutre (< 1e-6 m) ; bouton explicite « adopter la forme actuelle » | D-10, D-20 |
| La forme d'un **nouveau** personnage est celle de l'asset actuel avec Atlas14 (17,8 à 37,4 mm de plus qu'extension-13 au stade 2) | D-19 |
| Aucun `hm_*` renommé ni supprimé tant que la migration n'est pas terminée | D-02 |
| Arbitrage vitesse accepté : nœuds ≈ +16 à +20 ms avec Subsurf niveau 1 | D-09 |
| Facteur ×6, plafonné par contrôle là où des faces se retournent ; appliqué **après** le test de migration (T-A3) | D-18 |
| Blender 5.2 uniquement | D-13 |

## 2. Constat de départ (mesuré)

- Les seules clés actives qui diffèrent d'extension-13 au neutre sont `HM · Atlas14 · reference` (valeur 1 au stade 2 ; 0,5 aux stades 1,5 et 2,5 ; 0 aux stades 0 à 1 et 3) et sa clé `· correction` (pondérée par le sexe, absente au sexe 0) ; sans les 32 clés ajoutées depuis (Atlas14 ×16, Muscles18 ×16), l'écart est 0,000 mm sur 35 cas (`docs/audit/mesures-atlas14-neutre.json`, `ISSUES.md` I-37 bis).
- La mise à jour actuelle (`add_proportions`) fait passer les sessions 08 à 13 au schéma 9 (462 clés, 0 driver invalide, T-A13) **en changeant leur forme** (I-37) : c'est le défaut que D-20 corrige.
- `validate_controls` et `validate_presets` testent exactement cette règle : en échec attendu aujourd'hui, ils doivent passer OK à la livraison du lot B.
- Référence figée de la forme actuelle : `tools/data/neutral_reference.json` (21 états, SHA-256 de l'asset, tolérance 1e-5 m).

## 3. Découpage proposé (chaque lot est livrable et testable seul)

### Lot A — Prérequis de test (petit)
1. Fixtures **réelles** : les fichiers des sessions 08 à 14 de `validation/` (non versionnés) remplacent les fixtures synthétiques pour la migration ; les lister dans le lanceur avec leur schéma d'origine.
2. Harnais T-A3 : pour chaque ancien fichier, forme au neutre et déplacement d'un contrôle avant/après migration (< 1e-6 m et < 0,02 mm).
3. **Point à vérifier** : un fichier déjà passé au schéma 9 par l'extension actuelle (donc déjà déformé par Atlas14) est-il distinguable d'un fichier natif schéma 9 ? Chercher un marqueur d'origine sur le maillage ou les clés ; s'il n'y en a pas, ces fichiers ne peuvent pas être « ramenés à la forme d'origine » (cas à traiter explicitement).

### Lot B — Paramètre `shape_revision` (proposition : d'abord sur le moteur actuel)
- Un paramètre par personnage, **0 = forme d'origine, 1 = forme actuelle**, qui multiplie la contribution des clés Atlas14 (`reference` et `correction`) ; les nouveaux personnages sont créés à 1, les fichiers migrés à 0.
- **Point à vérifier** : l'expression des drivers de ces clés et la possibilité d'y ajouter ce facteur sans toucher la forme à 1.
- Bouton « adopter la forme actuelle » (opérateur annulable) : passe à 1 ; test : la cage égale la référence figée pour le sexe et le stade du personnage.
- Intérêt : livre D-20 et fait passer `controls` et `presets` à OK **sans** attendre le moteur à nœuds ; réduit le risque avant le lot D.
- Critère de sortie : `validate_controls`, `validate_presets` OK ; 0 régression sur les 44 OK actuels.

### Lot C — Façade D, UUID, `Object.humanloom` (étape 5 du plan, tranche verticale)
Selon `DESIGN_NATIF.md` §4 et §10 : `PropertyGroup` sur l'objet, UUID, duplication, sauvegarde/annulation, désactivation propre. Critères : `DESIGN_NATIF.md` §10 (onze cases). La migration copie les `hm_*` vers la façade et **conserve** les anciennes propriétés jusqu'à la fin du lot D.

### Lot D — Groupe de nœuds « HL Human » (étape 3) et bascule du moteur
- Générateur hors ligne `tools/build_human_nodes.py` (point de départ : `tools/audit/cproto3_1e4.py`) → `extension/data/human_nodes.blend` ; déterministe.
- Une couche de base locale par contrôle ; la couche Atlas14 pondérée par `shape_revision`.
- Critères : équivalence à la forme des clés de forme < 0,02 mm sur ≥ 25 états (prototype mesuré : 0,047 mm sur ~150 déformations, ~8 ms ; temps avec Subsurf à reprendre) ; suppression des couches ; zéro dépendance à l'extension pour rouvrir un fichier.
- Bascule : la migration remplace les 462 clés d'identité par le groupe de nœuds (D-14), **conserve** les expressions comme clés séparées et garde la sauvegarde de l'ancien fichier.

### Lot E — Regroupement des contrôles (I-46)
**Limite mesurée** : `corpulence`, `whole_body`, `body_mass` ne déforment pas dans la même direction (cosinus 0,73 à 0,82 ; `body_mass` +1 ≈ 93 mm contre 34 mm). Une fusion ne peut donc **pas** conserver la forme d'un ancien fichier. Proposition : les fusions (corpulence ; `lips`/`lip_thickness` ; `jaw`/`jaw_angle`) valent pour les **nouveaux** personnages ; un fichier migré garde ses couches héritées actives (visibles seulement via « Afficher les contrôles hérités », déjà en place).

### Lot F — Amplitudes ×6 (D-18, I-45)
- Facteur **par contrôle** et **par personnage** : 1 pour un fichier migré (forme inchangée), ×6 (ou le plafond) pour un nouveau personnage.
- Contrôles à ×6 : `eyelid_aperture`, `lip_thickness`, `lips`, `mouth`, `mouth_corner`, `eye_height`, `cheeks`, `jaw`, `forehead`, `nose_bridge`, `jaw_angle`, `chin`, `head_width`, `muscle_definition`. Plafonnés à ×2–×3 : `ears_size`, `ears_angle`, `eye_spacing`, `facial_asymmetry`, `nose_length`, `nose_width`, `head_height`. À reformuler : `fat_face`, `muscles_abdomen` (expressions bornées à ±1).
- Le facteur doit dépendre de l'âge (les enfants ont des plafonds plus bas ; `AMPLITUDES_CONTROLES.md` §9, matrice 2 sexes × 4 âges). **Non fait** : les cibles des contrôles plafonnés (nouvelles cibles sculptées ou déformation de région douce).

## 4. Ordre et dépendances

A → B (livre D-20 seul) → C → D → E et F (indépendants entre eux, après D). Le lot B peut être livré et poussé sans attendre le moteur à nœuds. Les étapes 7 et suivantes de `SUIVI_REPRISE.md` (repères, nouveaux contrôles, UV, dents, rig, anatomie) restent **après** le schéma 10.

## 5. Tests d'acceptation (cumulés)

| Test | Lot |
|---|---|
| `validate_controls`, `validate_presets` : forme au neutre inchangée après migration (< 1e-6 m) | B |
| Bouton « adopter » : cage = `neutral_reference.json` (< 1e-5 m) | B |
| Migration des sessions 08 à 14 réelles : forme, 0 driver invalide, yeux, cheveux | A, C |
| Équivalence nœuds / clés < 0,02 mm sur ≥ 25 états ; temps d'un curseur ≤ 33 ms (cage) | D |
| Fichier rouvert sans l'extension : forme et animation conservées | C, D |
| Aucun retournement de face aux facteurs retenus, par sexe et par âge | F |
| 0 régression sur les 44 OK du lanceur | tous |

## 6. Risques

- **Fichiers déjà migrés** par l'extension actuelle : peut-être irrécupérables à la forme d'origine (point à vérifier, lot A).
- **Bascule de moteur** : un seul faux pas peut modifier des fichiers de l'utilisateur ; imposer la copie de sauvegarde avant migration et une migration idempotente.
- **Couverture de la référence** : 1 sommet sur 25 (plus pieds, mains, paupières, yeux) ; une déformation locale ailleurs peut passer inaperçue.
- **XPBD des cheveux** : non revalidé après le changement d'ordre de pile ; sans lien direct avec le schéma 10 mais à garder en tête.
- **Amplitudes** : mesurées sur la cage seule, neutre adulte (par sexe et âge pour 21 contrôles) ; à refaire sur la surface lissée.

## 7. Décisions attendues de l'utilisateur

1. Valider le lot B comme premier livrable (D-20 sur le moteur actuel, avant les nœuds) ?
2. Fusions (lot E) : acceptes-tu qu'elles ne s'appliquent qu'aux nouveaux personnages ?
3. Amplitudes (lot F) : facteur 1 pour les fichiers migrés, ×6 pour les nouveaux : confirmé ?
4. Fichiers déjà migrés en schéma 9 : si aucun marqueur n'existe, que faire (les laisser tels quels ?).
