# HumanLoom - Générateur humain pour Blender 5.2

Générateur humain en développement : modélisation du corps et du visage, morphologies et âges, puis groom natif Blender. Extension actuelle **0.14.0**, schéma de formes **9**. Cible exclusive : **Blender 5.2**, conformément au manifeste de l'extension. Le nom affiché par la version actuelle de l'extension reste « Human Modeling » ; le projet communautaire porte désormais le nom **HumanLoom**.

## Organisation

- `extension/` : extension installable, interface, opérateurs, mesures et contrôles de morphologie.
- `extension/data/realistic.blend` : base géométrique nécessaire au fonctionnement, incluse dans Git. Provenance et crédits dans `extension/CREDITS.md`.
- `tools/` : constructeurs, diagnostics, migrations, validations et rendus de développement. Les prototypes de groom s'y trouvent également.
- `docs/groom.md` : état et reproduction des prototypes de cheveux, nature de fibre et physique.
- `unreal/HumanReferenceStudy/` : configuration et scripts du projet d'étude des références Unreal.
- Documents à la racine : audits, recherches, spécifications et plan d'implémentation.

`validation/` contient les scènes d'essai, anciennes copies, caches et planches générées. Ce dossier reste local et n'est pas versionné. Les sources des outils qui les produisent sont conservées dans `tools/` ; certains essais historiques nécessitent aussi des références externes ou des résultats intermédiaires. Un clone neuf ne contient donc pas tous les résultats d'expérimentation.

## Branches

- `main` : instantané commun du code au démarrage du dépôt.
- `codex/modelisation` : travail sur le corps, le visage, les âges et les corpulences.
- `codex/groom` : travail sur les cheveux et la pilosité.

Les deux branches partent du même instantané complet. Une branche ne retire pas les fichiers de l'autre domaine ; les évolutions seront séparées par leurs commits.

```powershell
git switch codex/modelisation
git switch codex/groom
```

Enregistrer ou committer les changements en cours avant de changer de branche.

## Installation et exécution

Le dossier `extension/` est la racine de l'extension Blender : l'archive installable doit contenir `blender_manifest.toml` à sa racine. La commande native de construction peut être lancée depuis ce dossier :

```powershell
Set-Location extension
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --command extension build
```

Installer l'archive produite dans Blender 5.2 via l'installation d'extensions depuis le disque. La création se trouve dans **Ajouter > Mesh** ; les réglages utilisent le panneau **Humain**.

Pour exécuter un outil Blender, lire son en-tête et ses dépendances avant de le lancer. Les scripts de construction peuvent recréer une scène ou produire un candidat : les utiliser en processus isolé, pas dans une scène utilisateur ouverte.

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --factory-startup --offline-mode --threads 4 --python-exit-code 1 --python tools/validate_controls.py
```

Les outils Blender utilisent `bpy` et, selon le script, NumPy fourni avec Blender. Les assembleurs de planches s'exécutent avec un Python distinct disposant de Pillow ; le dossier PDF utilise aussi ReportLab, pypdf et pypdfium2. Des outils historiques comportent des chemins locaux à adapter.

## État de validation

La géométrie et les prototypes restent en revue. Les planches de comparaison du 20 novembre 2026 montrent notamment un dosage insuffisant des extrêmes de corpulence et de la projection abdominale, surtout sur le corps masculin. Les scripts `render_corpulence24.py` et `assemble_corpulence24.py` reproduisent cette comparaison sans corriger les formes.

Le groom est expérimental et n'est pas encore intégré à l'interface de l'extension. Le rig n'est pas livré. Les recherches biologiques guident des contrôles artistiques ; elles ne constituent pas une calibration clinique des personnages.

## Dépôt et licence

Dépôt communautaire : [xvanneste/HumanLoom](https://github.com/xvanneste/HumanLoom).

Le code de l'extension est déclaré **GPL-3.0-or-later** dans son manifeste ; le texte de la GPL v3 est inclus dans `LICENSE`. Les assets et références ont leur propre provenance, décrite dans `extension/CREDITS.md`. La publication du dépôt ne signifie pas que les prototypes ou les formes en revue sont validés.
