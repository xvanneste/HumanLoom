# PLAN_LOT2 — Tranche verticale native (proposition à relire ; rien n'est codé)

Date : 2026-11-22. Entrée : lot 1 terminé (groupe `HL Human`, `extension/data/human_nodes.blend`, 45 OK / 0 régression, SUIVI §4 P T-L1 à T-L16). Références : `PLAN_SCHEMA_10.md` §3, `DESIGN_NATIF.md` §4 et §10, décisions D-05, D-07, D-19, D-21, D-22.
**Statut : plan seulement. Je n'ai pas codé le lot 2.** Raison : l'accord de l'utilisateur que j'ai obtenu en direct couvre le lot 1 ; la consigne de poursuivre toute la nuit me vient d'une autre session et je n'ai pas pu la vérifier. Si l'utilisateur confirme, ce plan sert de départ.

## 1. Ce que le lot 2 change (et ne change pas)

Remplacer, pour **un nouveau corps**, le moteur « 461 clés de forme + 459 pilotes » par le modificateur de nœuds `HL Human`, et brancher dessus l'interface, les yeux, les cheveux et les mesures. Hors lot 2 : fusion des contrôles (lot 3), amplitudes ×6 (lot 4), retrait du code de migration (lot 5, après inventaire montré), rig, matériaux, UV, dents.

## 2. Impact mesuré avant de commencer (grep, pas une estimation)

- `extension/` : références aux clés `hm_*`, au bloc de clés ou aux marqueurs `human_modeling_*` : `__init__.py` 68, `character_presets.py` 15, `measurements.py` 8, `surface_fix.py` 7, `anatomy.py` 5, `proportions.py` 4, `groom.py` 3, `landmark_sets.py` 3, `age_shapes.py` 2, `muscle_upgrade.py` 2, `skin_relief.py` 2, `geometry_quality.py` 1.
- **33 scripts de test** (`validate_*`, `check_*`) lisent ou écrivent des `hm_*` ou `shape_keys[...]` : tous à porter sur la façade, ou à classer obsolètes avec l'accord de l'utilisateur. **C'est le principal risque du lot** : sans ce portage, le lot complet casse.

## 3. Modèle de données (D-07, D-22)

`Object.humanloom` (`PropertyGroup`) sur le corps :
- `is_human` (bool), `uuid` (str, nouveau à la création et à la duplication), `schema_version` = 10, `generator_version` = 1 (version de `human_nodes.blend`).
- Une propriété flottante par entrée du groupe, **nom = identifiant du socket** : `sex`, `age`, puis les 48 contrôles (`shoulders`, `waist`, …, `skin_relief`). Chacune est une façade : getter/setter lisent et écrivent `modifiers["HL Human"].properties.inputs.<identifiant>.value` (tableau nom → identifiant de socket **versionné**, lu dans le groupe à la création, jamais deviné) ; si le modificateur manque : valeur 0 et message d'inactivité.
- `links` : `PointerProperty` vers les deux yeux et les zones de cheveux (jamais par nom).
- Marqueurs : `human_modeling_body` / `human_modeling_schema` (propriétés personnalisées) sont **remplacés** par `humanloom.is_human` / `schema_version` (D-22 : propriétés de personnage renommées ; l'id d'extension `human_modeling` est conservé).

## 4. Création (Ajouter > Humain, F9)

1. Charger depuis `human_nodes.blend` le groupe et le maillage de base ; copier le maillage (mono-utilisateur) ; créer l'objet corps ; ajouter le modificateur `HL Human` (groupe **local**, pas lié : fichier portable), puis `Subsurf` niveau 1 **après** (ordre explicite par `modifiers.move`), puis le relief de peau (Displace) comme aujourd'hui.
2. Yeux : repris de `realistic.blend` (deux maillages) ; leurs pilotes lisent **les entrées du modificateur** (chemin `modifiers["HL Human"].properties.inputs.<id>.value`, validé en T-CF), plus le bloc de clés du corps.
3. UV, groupe de sommets du relief : copiés depuis l'asset (le maillage du lot 1 les contient pour l'UV ; le groupe de sommets est à recréer sur l'objet, **à vérifier**).
4. Options F9 : sexe, âge, taille ; `SKIP_SAVE` sur les propriétés de l'opérateur de création (I-38).
5. Opérateur `human_modeling.create` conservé comme alias le temps du lot (scripts et tests), nouveau `humanloom.create` ; les deux appellent la même fonction.

## 5. Interface

Même fonction de dessin dans la barre latérale (onglet « Humain ») et dans Propriétés > Objet (`bl_context='object'`), `poll` sur `humanloom.is_human`. Les sous-panneaux du visage et le grisage de `skin_relief` (étape 1) sont conservés, lisent la façade.

## 6. Autres modules

- `groom.py` : `body_from`, `build` testent `human_modeling_body` / schéma ≥ 9 : à passer sur `humanloom.is_human` ; racines des cheveux inchangées (T-C5 : 0,03 mm sur un corps déformé par un modificateur). Format `humanloom.groom` inchangé (D-22).
- `measurements`, `anatomy`, `landmark_sets`, `geometry_quality`, `character_presets` : lisent la forme évaluée ou les contrôles → à porter sur la façade. **Préréglages JSON anciens abandonnés (D-22)** : nouveau format, version 2.
- `muscle_upgrade`, `surface_fix`, opérateur de mise à jour, panneau des volumes hérités : **laissés tels quels mais désactivés** (poll faux pour un corps schéma 10) ; leur retrait relève du lot 5 (jamais sans inventaire montré).

## 7. Ce qui est coupé ou reporté volontairement

Duplication « personnage complet » (opérateur dédié) : minimum = nouvel UUID à la duplication ; l'opérateur complet reste dans le lot 2 s'il tient, sinon noté. Animation : entrées animables par images clés (mesuré T-CF) ; test dans l'interface réelle **non automatisable ici** (limite connue : pas de saisie clavier) → vérifié par script + image clé + annulation scriptée, **pas** par l'interface.

## 8. Critères (`DESIGN_NATIF.md` §10, onze cases) et comment chacun sera prouvé

| Case | Preuve prévue |
|---|---|
| Installation et activation sans exception | construction du paquet (`extension build`) dans un dossier isolé + activation en arrière-plan |
| Ajouter > Humain, options F9 | appel de l'opérateur, lecture des propriétés ; F9 : **non vérifiable par script** (déjà vu en T-U2) |
| `MESH` ordinaire + `is_human` + UUID | test automatique |
| Panneau seulement sur un humain, même code aux deux endroits | enregistreur de dessin (comme T-Q1) ; rendu réel non vu |
| Les paramètres déplacent la géométrie comme avant | `validate_human_nodes` (< 2e-5 m) + test par la façade |
| Animables et annulables | images clés scriptées ; Ctrl+Z réel **non testable ici** |
| Deux humains indépendants, duplication avec nouvel UUID | test automatique |
| Sauvegarde / rechargement | test automatique, y compris **sans l'extension** (déjà prouvé pour le groupe seul, T-L6) |
| Désactivation / réactivation sans résidu | `unregister`/`register` ×3 (déjà fait en T-A3 pour l'ancien moteur) |
| Temps ≤ 33 ms sur la cage | `validate_human_nodes` (T-L13 : 12 ms) |
| Tests automatisés + captures | tests oui ; captures d'interface : **non faites** |

## 9. Questions pour l'utilisateur (à trancher avant de coder)

1. **Les 33 tests qui lisent `hm_*`** : les porter tous sur la façade (long) ou en classer une partie obsolète ? Recommandation : porter ceux qui couvrent des fonctions conservées, classer OBSOLÈTE ceux qui testent le moteur à clés.
2. **Yeux** : pilotes lisant les entrées du modificateur (validé) ou valeurs dans la façade ? Recommandation : entrées du modificateur.
3. **Alias `human_modeling.*`** : les garder pendant le lot 2 puis les retirer au lot 5 ? Recommandation : oui.
4. **Ordre** : le lot 2 casse la compatibilité des tests tant que le portage n'est pas fini ; faire le portage **dans le même lot**, jamais en laissant le lot complet en échec.
