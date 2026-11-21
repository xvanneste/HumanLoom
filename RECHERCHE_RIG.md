# RECHERCHE_RIG — rig, skinning et animation faciale pour HumanLoom

> **Validation du 2026-11-21 : voir `VALIDATION_SCIENTIFIQUE.md`.** Vérifiés : Rigify (manuel *dev* = Blender 5.4, à recouper en 5.2), poids de régression d'articulations dans l'enveloppe convexe, 52 noms ARKit (compte fait par nous), Meta 15 visèmes et 70 FACS, effondrement de volume du LBS. **Non vérifiés** : gonflement du DQS et PSD dans Kavan, erreurs chiffrées de régression, « ARKit n'est pas FACS ».

Date : 2026-11-21. Statut : recherche documentaire ; **aucun rig n'existe dans le dépôt (D-15)**, rien n'a été testé. ⚠ = extrait de résumé, à vérifier.

## 1. Rigify (manuel Blender)

- Méta-rigs prédéfinis dans Ajouter > Armature ; le type « humain basique » n'a **ni visage ni doigts** (il faut le type humain complet). On place les os du méta-rig, puis **Generate Rig** ; pour modifier le rig généré, on modifie le méta-rig et on régénère. Le méta-rig doit rester dans le fichier.
- Visage : os dans la collection « Face » ; le visage « legacy » se rattache aux yeux/dents par contraintes *Child Of* ; un bouton **Upgrade Face Rig** passe au système modulaire. Le manuel note que **les os du visage sont presque inutiles si l'animation faciale se fait par shape keys**. [Basic usage](https://docs.blender.org/manual/en/dev/addons/rigify/basics.html), [Rig features](https://docs.blender.org/manual/pt/latest/addons/rigify/rig_features.html).
- Implication : Rigify est le choix natif ; **le placement du méta-rig est la partie à automatiser** (HumanLoom a déjà des repères/landmarks).

## 2. Ce que font MPFB2 et CharMorph (code local lu partiellement)

- **MPFB2** : jeux de rigs en données (`default`, `default_no_toes`, `game_engine`, `game_engine_with_breast`, `mixamo`, `mixamo_unity`, `openpose`, `cmu_mb`) avec leurs **poids** ; version Rigify (`rig.human.json`, `weights.human_toes.json`), tables de traduction vers Rigify, outils « make rig » (transfert automatique de poids, sauvegarde de poids).
- **CharMorph** (GPLv3, `lib/rigging.py`) : rig attaché par **modificateur Armature** avec *preserve volume* ; **deux modificateurs Armature** si des groupes `preserve_volume` existent (mélange de LBS et de préservation de volume) ; joints et poids stockés comme **données du personnage** ; `sliding_joints.py` ajuste les articulations ; le README précise que le rig n'est **pas morphé en temps réel**. Rigify complet avec visage, ARP ou rigs fournis.
- Leçon commune : **topologie constante → les poids se calculent une fois** et survivent aux morphs ; ce qui change, c'est la position des articulations.

## 3. Placer le squelette sur un corps morphé

- SMPL calcule les centres d'articulation par une **régression linéaire sur les sommets** (poids positifs sommant à 1 pour rester dans la surface) ; la régression d'origine est jugée imprécise (hanches) et raffinée par des travaux ultérieurs ; un travail de 2025 apprend un régresseur vers des articulations anatomiques. ⚠ [arXiv 2205.00076](https://arxiv.org/pdf/2205.00076v1.pdf), [arXiv 2509.06607](https://arxiv.org/pdf/2509.06607).
- Aucune source trouvée pour « squelette depuis points de repère de surface seuls » : il faudra le **construire** (ou régresser à partir de nos propres corps).
- Pour HumanLoom : les articulations = **combinaisons linéaires de sommets du maillage évalué** (donc suivent le groupe de nœuds). Poids de régression à **ajuster** (anatomie connue : centres de hanche/épaule/genou) puis **valider visuellement** ⬜.

## 4. Déformation (skinning) et correctifs

- LBS : volume perdu, auto-intersections, effet « candy-wrapper » ; DQS supprime le candy-wrapper mais crée du **gonflement** ; solutions : centres de rotation optimisés (Disney), séparer flexion et torsion (Kavan), **pose-space deformation** (correctifs par pose) y compris sur DQS. ⚠ [Disney CoR](https://la.disneyresearch.com/wp-content/uploads/Real-time-Skeletal-Skinning-with-Optimized-Centers-of-Rotation-Paper.pdf), [Kavan 2009](https://users.cs.utah.edu/~ladislav/kavan09automatic/kavan09automatic.pdf), [Kavan 2012](https://www-old.cs.utah.edu/~ladislav/kavan12elasticity/kavan12elasticity.pdf), [PSD sur DQS (thèse TCD 2008)](https://publications.scss.tcd.ie/theses/diss/2008/TCD-SCSS-DISSERTATION-2008-018.pdf).
- Dans Blender : modificateur Armature avec *preserve volume* (variante DQS) + **correctifs en shape keys pilotées par la rotation des os** (drivers) — déjà la mécanique de HumanLoom pour les contrôles.
- ⬜ **Question d'architecture à tester** : ordre de pile **Nœuds de déformation (identité) → Armature → Subsurf** ; les shape keys d'expressions s'évaluent avant ; les poids restent valides car la topologie est constante. À prototyper (T-R1).

## 5. Animation faciale

- **ARKit 52** : jeu courant dans les moteurs de jeu ; **n'est pas FACS** (obtenu par ACP/clustering) ; correspondance partielle vers les Action Units dans la littérature. **FACS** : actions musculaires (≈ 70 muscles cités par Meta pour sa variante). **Visèmes** : 15 formes chez Meta. Nombre de blendshapes de personnages : de ≈ 50 à plus de 900 selon la précision. Le cinéma utilise des rigs **sur mesure basés sur FACS**, bien plus riches (non couvert par les sources). ⚠ [Apple ARKit](https://developer.apple.com/documentation/arkit/arfaceanchor/blendshapes.md), [Meta](https://developers.meta.com/horizon/documentation/unity/move-face-tracking/), [Turrisi et al.](https://iris.cnr.it/retrieve/b57d9fa2-3eb6-403b-8190-dbe4bbda0a16/Blendshape%20features%20meet%20action%20units%20pre-proof.pdf).
- Cohérent avec D-14 : identité du visage en nœuds ; **expressions en shape keys séparées** (additives, vérifié T-X1) ; Rigify facial peut piloter ces shape keys.

## 6. Implications pour HumanLoom (propositions)

1. **Rig = Rigify** (natif) : (a) un méta-rig « HumanLoom » dont les os sont **placés par régression sur le maillage évalué** ; (b) un opérateur « Ajuster le rig » qui replace le méta-rig après changement d'identité puis régénère ; (c) export de rigs standards (game engine, Mixamo) en second temps, via les tables de MPFB2 **comme référence, sans copie de code** sans accord (GPL).
2. **Poids** : calculés **une fois** sur la topologie fixe (transfert depuis Rigify automatique + correction), stockés dans le `.blend` de ressources.
3. **Correctifs** : jeu minimal de shape keys pilotées par pose (épaules, coudes, genoux, hanches) ; viser *preserve volume*.
4. **Visage** : jeu d'expressions FACS + visèmes d'abord, compatibilité ARKit 52 en option ; la livraison dépend du contenu à créer (**gros chantier**).
5. **Film** : plusieurs personnages par scène ⇒ noms d'os et collections uniques par UUID ; compatibilité USD/Alembic/FBX (à tester ; l'export FBX avec modificateurs perd les shape keys, T-X2).

## 7. Lacunes

- Détails du rig facial modulaire de Rigify et des contrôles non lus ; Auto-Rig Pro non étudié ; rigs de cinéma (Pixar/Weta) non couverts.
- Aucune mesure de qualité de déformation, aucun test de régression d'articulations.

## 8. Tests proposés (rien n'est fait)

- T-R1 : pile Nœuds → Armature → Subsurf sur un corps ; vérifier déformation et poids.
- T-R2 : régresseur d'articulations (ajustement sur Rigify généré sur 5 corps) : erreur en mm.
- T-R3 : Rigify complet + visage généré depuis un méta-rig placé automatiquement.
