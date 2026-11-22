# PLAN_FONCTIONNALITES — lots pour combler l'écart avec les autres générateurs (proposition à valider)

Date : 2026-11-22. Entrée : `ECART_FONCTIONNALITES.md` (21 fonctionnalités non planifiées) et `SUIVI_REPRISE.md` §9 (étapes 7 à 12 déjà prévues). Demande de l'utilisateur : analyser les fonctionnalités manquantes pour les ajouter **par lot**. **Rien n'est codé ni lancé** ; les lots F démarrent après le schéma 10 (lots 2 à 5), un lot à la fois, avec rapport et accord.

## Principes

- Un lot = livrable et testable seul, avec ses critères chiffrés et ses preuves (comme les lots du schéma 10). Ce qui n'est pas atteint est dit tel quel.
- **Données déclaratives, code générique** (leçon CharMorph/MPFB2, `RECHERCHE_PLUGINS.md`) : vêtements, poses, matériaux, rigs sont des assets ; pas de code par asset.
- Natif Blender d'abord : Asset Browser, nœuds de géométrie, Hair Curves, Rigify, décalques par nœuds de matériau.
- Licences : aucune reprise de code ou de données GPL/AGPL sans décision explicite de l'utilisateur ; par défaut, **réimplémentation indépendante**.
- Les lots **sensibles** (F11 phénotypes, F12 photo/scan) ne démarrent que sur décision explicite ; ils ne sont pas recommandés par défaut.

## Séquence globale proposée (étapes existantes en gras)

Schéma 10 (lots 2 à 5) → **7 repères** → **8 nouveaux contrôles** → **9 UV + peau + yeux** → **10 dents/langue** → **11 rig + expressions + bake** → F-lots dans l'ordre ci-dessous. Les lots F0, F2 et F9 ne dépendent que des repères et peuvent s'intercaler plus tôt.

## Lots

| Lot | Contenu (lignes de l'écart) | Dépend de | Critères d'acceptation (à chiffrer au démarrage) | Risques |
|---|---|---|---|---|
| **F0 Assets déclaratifs** | Format de personnage et d'asset (fichier de description + `.blend`), catalogues dans l'Asset Browser (#2, #17) | schéma 10 | un asset ajouté sans code, visible dans l'Asset Browser, rechargé sans l'extension ; test d'installation | Format à figer trop tôt ; versionnage des assets |
| **F1 Peau avancée** | Décalques par nœuds : tatouages, cicatrices, grains de beauté, taches, maquillage, masques régionaux, rides statiques selon l'âge (#5) | étape 9 (UV, matériau « HL Skin »), F0 | couches empilables, réglables et animables ; aucun décalque ne casse les contrôles (leçon Globalskin) ; rendu de contrôle par région | Densité UV ; coûts de rendu |
| **F2 Cils et ongles** | Zone de groom « cils » ; ongles mains/pieds (objets, UV, matériau, contrôles de forme) (#6, #7) | étape 7 (repères mains/pieds), 9 | cils sans intersection avec la paupière à l'ouverture 0 et 1 ; ongles ajustés aux doigts à toutes les silhouettes | Repères des mains non vérifiés visuellement (I-48 connexe) |
| **F3 Vêtements v1** | Ajustement d'un vêtement au corps par liaison recalculée (KDTree + BVH, coordonnées barycentriques), bibliothèque F0, contrôle d'interpénétration (#1, #21) | F0, étape 7 | un vêtement suit 10 morphologies sans intersection > seuil mesuré ; recalcul < temps fixé ; sauvegarde/réouverture | Interpénétration en pose ; licence des modèles de vêtements |
| **F4 Poses** | Bibliothèque de poses (assets de pose), application et réinitialisation, import BVH et retargeting simple (#8) | étape 11 (rig), F0 | pose appliquée puis annulée sans résidu ; BVH importé sur 3 morphologies | Rig d'abord ; retargeting de qualité inégale |
| **F5 Export moteurs** | Rigs alternatifs (Mixamo-compatible, jeu), LOD / maillage proxy, cartes de cheveux, import `.mhm` (#9, #10, #16, #20) | étape 11 (bake), F3 | export FBX/glTF ouvert dans un moteur de test ; nombre de polygones par LOD mesuré ; cartes de cheveux sans trou visible | Cible moteur à choisir ; formats tiers |
| **F6 Lots et foules** | Génération par lots avec graine, contraintes de variété, nommage et collections (#11) | schéma 10, F0 | N personnages uniques reproductibles par graine ; temps par personnage mesuré | Mémoire ; unicité des noms |
| **F7 Expressions avancées** | Rides dynamiques pilotées par l'expression (cartes de normales/plis), jeu de correctifs de pose (#14) | étape 11, F1 | rides visibles sur 6 expressions sans déformation du maillage ; coût mesuré | Dépend des UV et de la peau |
| **F8 Style stylisé** | Morphologie stylisée (proportions caricaturales, yeux grands) en plus du matériau stylisé (#13) | lots 3–4 (amplitudes) | contrôles de style bornés, aucun retournement de face | Compatibilité avec les contrôles réalistes |
| **F9 Interface multilingue et préférences** | Textes sources en anglais, dictionnaire FR, préférences de l'extension, raccourcis (#18) | schéma 10 (interface) | interface suit la langue de Blender ; aucun texte en dur détecté par un test | Gros volume de chaînes |
| **F10 Éditeur de cibles utilisateur** | L'utilisateur sculpte une cible et la rattache à un contrôle ; export/import (#4) | schéma 10, F0 | une cible utilisateur devient un contrôle réglable, sauvegardé, sans toucher au code | Contrôle de qualité des cibles ; conflits avec la base |
| **F13 Tissu** | Simulation de vêtements (cache, collisions avec le corps morphé) (#15) | F3, F4 | vêtement stable sur 3 poses ; temps de simulation mesuré | Instabilités ; coût |
| **F11 Phénotypes** *(sensible, décision requise)* | Contrôles de variation par population (#3) | décision de l'utilisateur, source de données documentée | à définir avec sources et garde-fous | Représentation, risque de stéréotypes ; **non recommandé par défaut** |
| **F12 Photo / scan** *(sensible, décision requise)* | Ajustement sur la ressemblance d'une personne réelle (#12) | décision de l'utilisateur | à définir | Consentement, données personnelles ; **non recommandé** |

## Ordre recommandé et pourquoi

1. **F9 (multilingue)** dès que l'interface du lot 2 est stable : plus on attend, plus il y a de textes en dur.
2. **F0 (assets)** : prérequis de F1, F3, F4, F6, F10.
3. **F2 (cils, ongles)** : petits, forte valeur visuelle, dépendent seulement des repères.
4. **F1 (peau avancée)** après l'étape 9.
5. **F3 (vêtements)** puis **F4 (poses)** puis **F5 (export)** après le rig.
6. **F6, F7, F8, F10** selon tes priorités ; **F13** après F3 et F4 ; **F11 et F12** seulement sur décision.

## Décisions attendues de l'utilisateur

1. Valider l'ordre (en particulier F9 tôt).
2. Les lots sensibles F11 et F12 : écartés par défaut ?
3. Cible d'export pour F5 : Unreal, Unity, les deux ?
4. Licences : réimplémentation indépendante (défaut) ou reprise de ressources GPL/CC0 après lecture ?
