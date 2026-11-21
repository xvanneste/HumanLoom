# AUDIT — Audit technique final

Date : 2026-11-21. Base : `codex/groom` @ `443d278`, Blender 5.2.0 LTS. Documents liés : BRANCH_ANALYSIS, FEATURE_STATUS, ISSUES, ARCHITECTURE, ROADMAP, REFERENCE_PLUGINS, TEST_REPORT. Les statuts sont ceux de TEST_REPORT : seul ce qui a été exécuté est marqué validé.

## 1. État réel du projet
Extension Blender 5.2 v0.15.2 (schéma 9) fonctionnelle pour la création de corps, les mesures, les repères anatomiques et le groom natif, d'après les tests exécutés. Pas de crash ni de corruption observés. Le code est cohérent (47 opérateurs, `register`/`unregister` propres, aucun handler global, aucun appel dangereux), mais mal structuré (fichiers monolithiques, tests couplés à l'installation) et la qualité visuelle des formes reste « en revue » selon le README.

## 2. Ce qui fonctionne / ne fonctionne pas
- **Validé :** mesures, repères, anatomie, qualité géométrique, groom (11 zones, 66 cas, workflow, viewport/rendu séparés), rechargement ×3 de l'extension, 459 drivers valides, enregistrement/réouverture d'un corps.
- **Tests en échec mais produit non mis en cause :** `validate_model` (assertion sur `dimensions` au lieu de la surface lissée) et `validate_controls` (formule ignorant trois clés actives). Détail : ISSUES I-02.
- **Non testé :** interface, installation de l'archive, undo/redo, performance des sliders, visage/âge/corpulence (scripts non exécutés), réouverture du groom et collisions (fichiers absents).
- **Absent :** rig, vêtements, dents, matériaux de peau avancés.

## 3. Branches
Trois branches : `main` = `codex/modelisation` (identiques), `codex/groom` +3 commits (groom natif). Aucune fonctionnalité concurrente, aucune fusion faite. Voir BRANCH_ANALYSIS.

## 4. Plugins de référence
MPFB2 (documentation d'architecture lue) et CharMorph (add-on, base et 5 packs clonés ; moteurs de morphs, ajustement d'assets, config YAML lus). Enseignements : logique sans UI dans un paquet séparé, personnages décrits par données, morphs creux chargés à la demande, métasliders, ajustement d'assets par binding recalculé. Réserve : base de morphs MB-Lab sous AGPL. Non lus : `rigging.py`, `hair.py`, `materials.py` de CharMorph, code source de MPFB2, modèles tiers. Voir REFERENCE_PLUGINS.

## 5. Principaux problèmes techniques (détail : ISSUES)
1. Tests liés à l'extension installée, pas au dépôt (I-01) — P1.
2. Deux tests périmés (I-02) et fichiers d'essai non reproductibles (I-03) — P1.
3. Pas de lanceur ni de convention de test (I-04) ; `__init__.py` monolithique (I-05) ; imports circulaires contournés (I-10) — P2.
4. `groom.py` écrit en style compressé : 102 lignes à instructions enchaînées, 35 lignes > 140 caractères (I-09) — P2.
5. XPBD groom non validé en général (I-06) ; boucle par sommet pour le masque (I-11, non mesuré) — P2.

## 6. Améliorations les plus intéressantes
- Lanceur de tests unique, indépendant de l'installation, avec résumé.
- Réparer les deux tests, puis étendre à toutes les clés actives par défaut.
- Reformater `groom.py` sans changer le comportement (protégé par `validate_groom25`).
- Découper `__init__.py` par domaine, sur le modèle `lib/` + UI de CharMorph / services de MPFB2.
- Mesurer avant d'optimiser (sliders, construction du groom).

## 7. Architecture recommandée
Évolution progressive : `core/` (schéma, presets, mesures) sans UI, domaines `body`, `face`, `groom`, `ui/`, `tests/`. Voir ARCHITECTURE.

## 8. Cinq premières actions
1. Créer le lanceur de tests ciblant le dépôt (I-01).
2. Corriger `validate_model` et `validate_controls`, après décision sur la définition de la stature (cage ou surface lissée) et sur les clés actives par défaut.
3. Rendre les fichiers d'essai reproductibles et exécuter les ~40 scripts non testés pour compléter FEATURE_STATUS.
4. Tester l'installation de l'archive, l'interface et undo/redo en session Blender interactive.
5. Décider du sort des fichiers `collision29` et de `codex/modelisation`, puis reformater `groom.py` et découper `__init__.py`.

## Limites de l'audit
Lecture du code ciblée (opérateurs de création/hauteur/mise à jour, mesures, construction et import du groom, métriques par grep), pas exhaustive. Aucun test interactif. Aucune mesure de performance. Les résultats sont ceux d'un clone de `codex/groom` ; les scripts non suivis `collision29` n'ont pas été évalués.
