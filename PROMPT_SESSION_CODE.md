# Prompt pour la session « code » (HumanLoom, branche `codex/natif`)

Copier-coller le bloc ci-dessous dans la nouvelle session.

---

Tu reprends le projet HumanLoom (extension Blender 5.2 uniquement, id `human_modeling`, version 0.15.2, schéma 9) dans `G:\_dev\BlenderDev\HumanLoom`. Tout se fait en français (UI, docs, messages).

## À lire d'abord, dans cet ordre
1. `CLAUDE.md`, puis `SUIVI_REPRISE.md` (décisions D-01 à D-18, registre des tests, pièges d'environnement, plan §9).
2. `ISSUES.md` (I-01 à I-47), `PROMPT_NOUVELLE_SESSION.md`.
3. Selon la tâche : `DESIGN_NATIF.md`, `AMPLITUDES_CONTROLES.md`, `REGROUPEMENT_CONTROLES.md`, `AJOUT_CONTROLES.md`, `docs/audit/baseline-tests.json`.

## Règles non négociables
- Branche `codex/natif` (D-17). **Aucun commit, aucune suppression, aucun merge sans accord explicite de l'utilisateur.**
- Ne jamais toucher à la session Blender de l'utilisateur ni aux autres versions de Blender installées (3.6, 4.4, 5.0, 5.3). Tests uniquement en Blender 5.2 headless, dans un clone isolé ou un dossier de sortie dédié, jamais dans `validation/` de l'utilisateur.
- Ne pas renommer l'id `human_modeling`, ni les propriétés `hm_*` / `human_modeling_*`. Ne rien supprimer côté `hm_*` (les anciennes scènes doivent rouvrir).
- Pas de couche de compatibilité pour d'autres versions de Blender.
- Ne pas modifier les fichiers WIP de l'utilisateur : `tools/validate_controls.py`, `tools/validate_model.py`, `tools/audit_groom_collision29.py`, `tools/groom_collision_guard29.py`, `tools/validate_groom_collision29.py`.
- Distinguer mesuré / supposé dans tout compte rendu. Pas de « validé » sans preuve exécutée.
- Pas d'architecture nouvelle (groupe de nœuds « HL Human », schéma 10, migration d'amplitude) sans accord : c'est l'étape 3, hors périmètre ici.

## Périmètre de cette itération (plan §9)
**Étape 1 — gains rapides** (chacun = un changement petit, vérifiable, relié à son I-xx) :
- I-19 : tolérance float32 dans `groom.validate`.
- I-28 : le premier objet de cheveux va dans la collection du corps.
- I-36 : ordre des modificateurs imposé par `modifiers.move` explicite (cible : nœuds d'identité → armature → subsurf ; Rigify donne sinon SUBSURF, DISPLACE, ARMATURE, mesuré).
- I-35 : garde-fou du budget de densité des masques.
- I-27 : messages de retour de l'interface (UI).
- Interface seulement : masquer `body_mass` et `corpulence` (redondants, I-46), regrouper les sous-sections du visage, griser `skin_relief`.

**Étape 2 — lanceur de tests** `tools/run_tests.py` : reprendre le registre d'arguments de `tools/audit/run_baseline.py`, générer les fixtures manquantes (I-47 : `adult-original.blend`, `legacy-03.blend`), un Blender par test, sortie JSON comparable à `docs/audit/baseline-tests.json`.

## Référence de non-régression (mesurée, clone isolé)
**40 tests OK sur 46 exécutés, 1 obsolète** (I-34 traité : `validate_delivery12_reopen`, `validate_muscle_workflow`, `validate_global_physique` mis à jour ; `validate_surface_fix` obsolète). Échecs connus restants : fixtures absentes (`validate_controls`, `validate_presets`), non élucidés (`validate_age_transitions`, `validate_body_mass_neutral`, `validate_musculature`). Toute modification ne doit **pas** ajouter d'échec par rapport à cette liste.

## Ce que tu dois produire pour chaque changement
1. Le diff minimal, limité à `extension/` ou `tools/`.
2. La commande exacte de vérification et sa sortie (test headless 5.2).
3. La mention de l'issue traitée (I-xx) et de la section d'analyse qui la justifie.
4. Les écarts : tout ce qui diffère de ce que décrit l'analyse, et pourquoi.
5. Mise à jour de `SUIVI_REPRISE.md` (registre) et `ISSUES.md` (statut), en gardant mesuré / supposé.

Termine chaque lot par un résumé que l'autre session (relecture) puisse vérifier : liste des fichiers touchés, tests lancés, résultats bruts, points non vérifiés.
---

## Contrôle côté relecture (pour moi, session d'analyse)
Pour chaque lot reçu, je vérifie : (1) le diff ne touche que ce que l'issue vise ; (2) aucun `hm_*` renommé ou supprimé ; (3) l'ordre des modificateurs est bien imposé explicitement ; (4) la liste des tests en échec n'a pas grandi par rapport à la référence ; (5) les affirmations « validé » sont adossées à une sortie de test réelle ; (6) aucun commit n'a été fait.
