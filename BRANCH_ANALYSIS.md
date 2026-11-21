# BRANCH_ANALYSIS — Branches Git

Observé le 2026-11-21 (`git branch -a -vv`, `git rev-list --count`). Remote : `origin` = https://github.com/xvanneste/HumanLoom.git. Aucune fusion effectuée.

Historique : `5a56367` (Human Modeling 0.14 + prototypes groom) → `87db29f`/`be67efb` (licence GitHub) → `94d639b` (présentation, = `main` = `codex/modelisation`) → `bc81789` (groom natif 0.15) → `409d3bb` (viewport/rendu séparés, 0.15.1) → `443d278` (densité + gravité, 0.15.2, = `codex/groom`).

| Branche | Fonctionnalités | État | Problèmes | Recommandation |
|---|---|---|---|---|
| `main` / `origin/main` (`94d639b`) | Modélisation 0.14 : corps, visage, morphologies, âge, mesures, préréglages. Pas de groom intégré. | Partiel : voir TEST_REPORT (2 échecs sur 9 scripts exécutés) | `validate_model`/`validate_controls` en échec ; README signale corpulence et abdomen insuffisants | Conserver comme référence ; corriger les échecs de test ici ou sur `modelisation` |
| `codex/modelisation` (`94d639b`) | Identique à `main` : 0 commit d'avance et de retard | Idem `main` | Aucun travail propre : branche vide de différences | Conserver pour le travail corps/visage, ou la supprimer si la séparation n'est pas utilisée (décision utilisateur) |
| `codex/groom` (`443d278`) | +3 commits, 23 fichiers, +2033/−32 : `extension/groom.py` (626 l.), `groom_fibers.py`, panneau UI, JSON import/export, 11 zones, viewport/rendu séparés, densités, XPBD expérimental, 15 scripts `tools/` | Partiel : `validate_groom25`, `workflow25`, `quality26` validés ; `reopen25`, `collision29` non testés | Voir ISSUES (I-03…I-06) : XPBD non validé en général ; 3 fichiers `collision29` non suivis ; `extension/LICENSE.txt` ajouté (674 lignes) | **Conserver** comme base de développement groom ; fusion dans `main` à décider avec l'utilisateur après correction des échecs communs |

## Comparaisons

- Aucune fonctionnalité n'existe en deux implémentations concurrentes entre branches. À l'intérieur de `codex/groom`, les prototypes `tools/hair_prototype20.py`, `hair_nature21.py`, `hair_physics22.py` (historique, avant intégration) ont été remplacés par `extension/groom.py`. Ils restent dans `tools/` et sont à archiver, pas à supprimer sans accord.
- Les corrections de bugs propres à `codex/groom` portent sur la densité par défaut (700 000 → 1 800 000 /m²) et le libellé du mode « Suivi sans physique ». Rien n'est présent uniquement sur `main`.
- Modification dangereuse potentielle : `blender_manifest.toml` borne `blender_version_max = "5.3.0"` ; bump de version 0.15.x à vérifier à chaque fusion (README, `docs/groom.md`, manifeste, `groom.py`).
- Travail non suivi dans l'arbre de travail : `tools/audit_groom_collision29.py`, `groom_collision_guard29.py`, `validate_groom_collision29.py`. À committer ou écarter par l'auteur ; non évalué.
