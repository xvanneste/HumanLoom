# CONCEPTION — animation du visage et de la bouche (lot F, étape de conception)

Date : 2026-11-23. **Statut : conception et prototype de décision, aucun code de production.** Contexte : l'animation du visage ET de la bouche fait partie du court métrage final (décision relayée par la session de revue) ; D-34 : les expressions sont écrites par nous (aucun visage tiers livré, ANALYSE_RIG_VISAGE.md) ; D-35 : toute donnée numérique vient d'une source publiée citée, sinon « non vérifié ». Le détail de ce qui est mesuré / non mesuré est dit à chaque ligne.

## 1. Point de départ (mesuré sur la cage native, 10 582 sommets)
- Fait (F0) : os `jaw` (81 os), dents/gencives/langue sous le rig, cavité buccale native (93 × 68 mm au défaut), fente labiale de 0,9–1,5 mm. L'ouverture à 20° donne 32–34 mm de fente.
- Défauts connus qui bornent le visage : (1) **les commissures forment des « rails » tendus à l'ouverture** (la cage n'a aucune déformation propre aux coins de bouche) ; (2) **I-49** : les lèvres s'interpénètrent de quelques dixièmes de mm aux commissures pour sexe ≈ 0 (écart de fente min. −0,7 mm), donc tout sourire (tirage des commissures) l'aggravera ; (3) paupières natives incomplètes (`validate_eyelids_native` = ÉCHEC CONNU, F0-a) ; (4) aucune donnée publiée lue pour les amplitudes d'expressions.
- Conséquence : **avant toute production de commande de bouche, I-49 doit être traité** (piste : imposer un écart de fente minimal dans les clés de forme sexe/âge de `tools/data/realistic.blend`, puis régénérer `human_nodes.blend`). Les expressions de la zone yeux/sourcils n'en dépendent pas.

## 2. Jeu de commandes proposé (écrit par nous, d'après le découpage en unités d'action FACS)
Source du découpage : le Facial Action Coding System (Ekman & Friesen, 1978 ; manuel révisé Ekman, Friesen & Hager, 2002). **Ce document n'en reproduit que la numérotation des unités d'action (faits publics), pas le texte du manuel.** Les noms de commandes sont les nôtres.

| groupe | commandes (L/R = côté) | UA | méthode proposée |
|---|---|---|---|
| sourcils | `brow_inner_up`, `brow_outer_up.L/.R`, `brow_down.L/.R` | 1, 2, 4 | couches |
| yeux | `lid_raise.L/.R`, `lid_tighten.L/.R`, `blink.L/.R` (fermeture complète), `squint.L/.R` | 5, 7, 43/45 | couches (+ paupières natives à finir) |
| regard | `gaze_h`, `gaze_v` (par œil) | — | os `eye.L/.R` visant (les yeux sont déjà des objets rattachés à `head`) |
| joues et nez | `cheek_raise.L/.R`, `cheek_puff`, `nose_wrinkle.L/.R`, `nostril_flare.L/.R` | 6, 9, 38 | couches |
| lèvres | `upper_lip_raise.L/.R`, `lip_corner_pull.L/.R`, `lip_corner_depress.L/.R`, `lip_stretch.L/.R`, `lip_pucker`, `lip_funnel`, `lip_press`, `lip_tighten`, `lower_lip_depress.L/.R`, `chin_raise`, `lips_part` | 10, 12, 15, 20, 18, 22, 24, 23, 16, 17, 25 | couches |
| mâchoire | `jaw_open`, `jaw_side`, `jaw_forward` | 26/27, 30, 29 | os `jaw` (existe) |
| langue | `tongue_out`, `tongue_up`, `tongue_side` | 19 | os (2-3 os sous `jaw`, à ajouter) |
Total : **≈ 44 commandes de peau (couches), 1 os de mâchoire (fait), 2 os de regard, 2-3 os de langue**. Le nombre est un objectif de conception, pas une mesure.
Expressions « émotionnelles » (joie, tristesse, colère…) : combinaisons **de ces commandes**, écrites en JSON par nous, jamais des couches supplémentaires (une couche = un mouvement localisable).

## 3. Visèmes (parole)
Visèmes = combinaisons prédéfinies des commandes de bouche + `jaw_open`. Liste de principe : silence, P/B/M, F/V, TH, T/D/N/L, K/G, CH/J/SH, S/Z, R, A, E, I, O, U (≈ 15). **Provenance non vérifiée** : cette liste est celle que reprennent les normes d'animation faciale (famille MPEG-4) et la littérature sur la confusion visuelle des consonnes ; aucune des deux sources n'a été lue ici. Les amplitudes de chaque visème sont à calibrer par nous, à l'œil puis sur des mesures publiées à chercher (ouverture, protrusion). Une table phonèmes → visèmes (anglais ET français) et un moteur de synchronisation labiale sont HORS de ce lot : ils relèvent de la production (étape T).

## 4. Prototype de décision : coût d'évaluation de trois méthodes (MESURÉ)
`tools/proto_face_method_cost.py` : cage de 10 582 sommets, 52 commandes, décalages ALÉATOIRES sur 1 800 sommets (on mesure le coût, pas la qualité), 30 changements de 6 valeurs, évaluation du graphe de dépendances + lecture du maillage évalué, un seul objet évalué à la fois, Blender 5.2 headless :
| méthode | médiane | p90 | résultats différents | mémoire des décalages |
|---|---|---|---|---|
| sans modificateur (référence) | 0,66 ms | 0,72 ms | 0/29 | — |
| S : 52 clés de forme | **2,58 ms** | 3,87 ms | 29/29 | 52 × 10 582 × 12 o ≈ 6,6 Mo |
| N : groupe de nœuds, 52 couches vectorielles | **3,15 ms** | 3,40 ms | 29/29 | idem ≈ 6,6 Mo |
| B : 40 os de visage, 4 influences, 1 800 sommets | **0,84 ms** | 0,90 ms | 29/29 | poids ≈ négligeable |
(Un premier essai N donnait « 0,6 ms, 0/29 résultats différents » : le modificateur n'était pas réévalué ; corrigé par `update_tag`. Le contrôle « résultats différents » est donc dans le script.)
**Lecture** : les trois méthodes sont très en dessous du budget de 33 ms du groupe `HL Human` (validate_human_nodes) ; **le coût ne départage pas** les méthodes. Non mesuré : coût avec le Subsurf et les autres modificateurs, mémoire GPU, comportement dans une vue 3D réelle (le test est headless).

## 5. Décision proposée (à valider), fondée sur les critères autres que le coût
1. **Peau : couches dans le groupe de nœuds `HL Human`** (méthode N), après les couches de morphologie. Raisons : (a) les déformations s'ajoutent à la cage DÉJÀ morphée et peuvent être mises à l'échelle par la taille de la tête (un sourire d'enfant ≠ celui d'un adulte), ce que des clés de forme sur le maillage de base ne font pas (elles agissent AVANT le groupe de nœuds) ; (b) un seul mécanisme pour toute la morphologie ; (c) coût de 3 ms. Risque : le groupe de nœuds est régénéré hors ligne (`tools/build_human_nodes.py`, minutes) : tout ajout de commande exige cette régénération et la suite complète.
2. **Export** : les couches ne s'exportent pas telles quelles vers les moteurs de jeu ou de rendu temps réel. Un opérateur « Cuire les formes du visage » évaluerait chaque commande à 1 et créerait des clés de forme (nommées par commande) sur une COPIE du corps pour l'export. **À vérifier** : le comportement des exporteurs de Blender 5.2 (non lu ici).
3. **Mâchoire, regard, langue : os.** Pas de couche pour une rotation de corps rigide.
4. **Retargeting de capture faciale** (hors périmètre pour l'instant) : un jeu de courbes nommées par commande, écrites en F-curves sur les propriétés du corps ; pas de capture livrée.
5. **Paupières** : terminer d'abord la correction native des paupières (test `validate_eyelids_native`) ; la commande `blink` en dépend.

## 6. Données publiées à lire AVANT la production (D-35, aucune lue à ce jour)
- amplitude des mouvements faciaux (déplacement de la commissure au sourire, élévation de la paupière, ouverture maximale de la bouche, protrusion des lèvres) ; durée d'un clignement (ordre de grandeur non vérifié) ; proportions du visage par âge et sexe (la base `extension/data` contient déjà des référentiels anthropométriques de corps, pas de visage) ;
- table phonèmes-visèmes publiée ; ouverture de la bouche à la parole.
Chaque valeur retenue ira dans `extension/data/face_reference.json` avec auteur, année, table, ou « non vérifié ».

## 7. Plan de production proposé (ordre, critères)
1. **I-49 + déformation des commissures** (prérequis) : critère : écart de fente ≥ 0,3 mm sur toutes les morphologies et 0 croisement dans la tête ; plus de « rails » à 20°.
2. Paupières natives (ÉCHEC CONNU → OK).
3. 12 commandes pilotes (sourcils, paupières, sourire, ouverture, pincement) : couches + planche sur 3 morphologies + test d'amplitude (déplacement de repères mesuré, bornes écrites).
4. Reste des commandes + os de langue et de regard.
5. Visèmes et expressions JSON ; opérateur de cuisson des formes ; planches ; validateur ; intégration create/duplicate/rig.
Critères communs : suite complète + `validate_install` à chaque étape ; aucun critère assoupli ; amplitudes bornées et documentées ; jamais présenté comme calibré cliniquement.
