# ROADMAP

## A — Stabilisation
- Objectifs : lanceur de tests qui cible le dépôt (I-01) ; diagnostiquer `validate_model` et `validate_controls` (I-02) ; fixtures reproductibles (I-03).
- Dépendances : aucune. Critère : tous les scripts existants de base (`validate_*` hors groom) passent sur un clone neuf, avec résumé automatique.
- Résultat : base fiable pour modifier le code. Aussi : décision de l'utilisateur sur les 3 fichiers `collision29` non suivis.

## B — Consolidation
- Découper `__init__.py` par domaine (ISSUES I-05), archiver les prototypes de `tools/`, mesurer la latence des sliders avant toute optimisation, ajouter test d'installation (archive) et de rechargement unregister/register, test undo/redo.
- Critère : couverture des opérateurs par au moins un test ; temps de réponse des sliders mesuré.

## C — Qualité du générateur
- Corpulence extrême et abdomen (README), visage, âge, symétrie. Chaque correction accompagnée de planches de comparaison et de critères chiffrés. Dépend de A et du banc de mesures.

## D — Fonctionnalités avancées
- Groom : critères d'acceptation XPBD et collisions (I-06). Puis matériaux de peau, rigging, vêtements, presets enrichis. Étudier d'abord MPFB2/CharMorph (REFERENCE_PLUGINS) avec contrôle de licence.

## E — Expérience utilisateur
- Panneaux cohérents, ordre logique des étapes, messages d'erreur, préréglages avec aperçus, documentation utilisateur. Dépend de B (UI isolée).

**Phasage mis à jour (fusion avec la conception native) : voir `DESIGN_NATIF.md` §9** (phases 0 à 7 : gains rapides, socle de test, tranche verticale native, migration complète, contenu, animation, assets/rig, finition). Les étapes A à E ci-dessus restent le cadre général.

Pistes détaillées de brainstorming (contrôle en couches, corpulence, visage, matériaux, rig, interface, CI) : voir `IDEES.md` ; elles complètent cette feuille de route et sont à prioriser avec l'utilisateur.

Aucune étape n'est lancée sans accord de l'utilisateur pour les modifications d'architecture, suppressions ou fusions.
