# HumanLoom - Générateur humain pour Blender 5.2

Générateur humain en développement : modélisation du corps et du visage, morphologies et âges, groom natif Blender. Cette branche fournit **HumanLoom 0.16.0**, schéma de formes **9** (ancien moteur ; le corps natif est au schéma 10), avec squelette natif, retargeting d'animations, visage, vêtements, accessoires, foule et tissu (voir la section « État de la branche »), avec cheveux et pilosité intégrés à l'interface. Cible exclusive : **Blender 5.2**. L'identifiant d'extension `human_modeling` est conservé pour permettre la mise à jour des installations et des scènes existantes.

## État de la branche codex/natif (28 nov. 2026)

Contenu livré (détails : `docs/guide-utilisateur.md`, `docs/foule.md`, `docs/groom.md`, `CONCEPTION_*.md`, `NOTES_DE_VERSION_0.16.md`) : corps humain natif (nœuds géométriques, sexe, âge, morphologie), squelette HumanLoom avec deux modificateurs Armature (linéaire et quaternions duals), mâchoire, yeux, dents et langue, retargeting analytique d'animations de VOTRE bibliothèque (aucun fichier tiers n'est livré), visage (poses, visèmes, correspondance ARKit à 56 % pondérée), vêtements procéduraux et importés, accessoires, foule (jusqu'à 150 personnages mesurés), tissu natif des robes (expérimental), groom.

**Migration d'un fichier existant** : un squelette posé avant cette version est de version 1 ; il passe à l'état *À configurer* jusqu'à **Mettre à jour le squelette** (les poids sont sauvegardés dans le fichier d'abord ; `skeleton.restore_weights_backup` les restitue). Les retargetings DÉJÀ faits ne sont pas rejoués : refaites-les pour profiter du rythme scapulo-huméral (actif par défaut, désactivable). Les correctifs de flexion du coude et du genou sont coupés par défaut (bouton pour les activer). Dents et langue ne suivent une nouvelle morphologie qu'après **Mettre à jour le squelette**.

**État de validation** : suite de tests (`python tools/run_tests.py`, Blender 5.2) : 77/78 tests requis OK au 28 nov. 2026, le seul en échec (`validate_groom_collision29`) est un travail en cours. Les mesures de foule, de tissu et de rendu sont celles d'UNE machine ; les formes de visage, les correctifs de flexion, le groom et le tissu restent à valider à l'œil par l'utilisateur ; l'épaule levée vers l'avant au-delà de 135° est une limite documentée (`CONCEPTION_RIG_CORRECTIFS.md` §12).

## Masque de peau sous les vêtements

Sélectionnez un personnage en mode Objet et ouvrez **Humain → Vêtements → Masque de peau**. Le mode est enregistré avec le personnage dans le fichier Blender. La couverture se recalcule lorsque vous ajoutez, retirez ou remplacez des pièces avec HumanLoom. Retirer le dernier vêtement réaffiche le corps entier et conserve le mode pour la tenue suivante. Confirmer le mode courant dans le panneau permet aussi de retirer les doublons du masque dans la pile, sous réserve de la protection des simulations.

| Mode | Effet |
| --- | --- |
| **Désactivé** | Toute la peau du corps reste présente et visible. |
| **Rendu uniquement** | EEVEE et Cycles rendent transparente la peau couverte. La surface complète reste disponible pour les simulations, les attaches, les grooms et les exports de géométrie. Le mode Solide peut montrer la peau. |
| **Géométrie** | Le modificateur retire les faces couvertes de la surface évaluée, en mode Solide et au rendu. Les simulations, les attaches et les grooms qui utilisent le corps peuvent être affectés. Choisissez ce mode avant de lier ces dépendances ou d’activer la simulation. |

Le masque garde les faces qui franchissent la limite de couverture. Les identifiants de provenance sont des attributs partagés du Mesh source. Le masque les utilise sans changer ses sommets, ses UV ni son partage entre personnages. Une face privée d’identifiant valide reste visible. Le masque suppose la topologie de cage native. Une retopologie ou un générateur qui recopie la provenance sur de nouvelles faces est hors contrat. Les vêtements importés peuvent être ajustés et attachés au corps, et ne fournissent pas de couverture de peau automatique. Les grooms restent visibles et peuvent traverser un vêtement. Pour changer les matériaux de peau d’un corps, utilisez **Désactivé** pendant l’édition et réactivez le mode voulu ensuite.

Un fichier existant garde son masque historique et l’ordre de ses modificateurs à l’ouverture. Choisissez un mode dans le panneau pour adopter le nouveau comportement. Les copies historiques portant le nom d’origine ou un suffixe numérique Blender sont converties si elles utilisent le groupe de sommets historique en mode inversé. Un masque renommé hors de cette convention reste sous votre contrôle. Tant que le mode **Historique** est affiché, la couverture existante est conservée. Un vêtement avec une simulation de tissu native active est protégé, car Blender 5.2 ne fournit pas à HumanLoom d’indicateur fiable de cuisson pour ce cache. HumanLoom refuse alors de retirer ou reconstruire la pièce, ainsi que de changer le masque géométrique d’un corps dont dépend la simulation. Gérez la simulation explicitement avant ces opérations. Les changements entre Désactivé et Rendu uniquement sur un fichier moderne, et le réglage du dégagement des vêtements, restent disponibles.

## Organisation

- `extension/` : extension installable, interface, opérateurs, mesures et contrôles de morphologie.
- `extension/data/realistic.blend` : base géométrique nécessaire au fonctionnement, incluse dans Git. Provenance et crédits dans `extension/CREDITS.md`.
- `tools/` : constructeurs, diagnostics, migrations, validations et rendus de développement. Les prototypes de groom s'y trouvent également.
- `docs/groom.md` : utilisation du groom intégré, vérifications et limites.
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
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --factory-startup --offline-mode --threads 4 --python-exit-code 1 --python tools/validate_groom25.py
```

Les outils Blender utilisent `bpy` et, selon le script, NumPy fourni avec Blender. Les assembleurs de planches s'exécutent avec un Python distinct disposant de Pillow ; le dossier PDF utilise aussi ReportLab, pypdf et pypdfium2. Des outils historiques comportent des chemins locaux à adapter.

## État de validation

La géométrie et les prototypes restent en revue. Les planches de comparaison du 20 novembre 2026 montrent notamment un dosage insuffisant des extrêmes de corpulence et de la projection abdominale, surtout sur le corps masculin. Les scripts `render_corpulence24.py` et `assemble_corpulence24.py` reproduisent cette comparaison sans corriger les formes.

Le groom 0.15 est intégré au panneau **Humain > HumanLoom · Cheveux et pilosité**. Les coiffures procédurales restent des points de départ à affiner en Curves Sculpt. La physique XPBD est expérimentale ; son banc court ne valide pas toutes les coiffures ni les collisions complexes. Le rig n'est pas livré. Les recherches biologiques guident des contrôles artistiques ; elles ne constituent pas une calibration clinique des personnages.

## Dépôt et licence

Dépôt communautaire : [xvanneste/HumanLoom](https://github.com/xvanneste/HumanLoom).

Le code de l'extension est déclaré **GPL-3.0-or-later** dans son manifeste ; le texte de la GPL v3 est inclus dans `LICENSE`. Les assets et références ont leur propre provenance, décrite dans `extension/CREDITS.md`. La publication du dépôt ne signifie pas que les prototypes ou les formes en revue sont validés.
