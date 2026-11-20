# Lot de modélisation 0.10

Blender 5.2 LTS uniquement. Corps et visage ; rig, cheveux et vêtements exclus du lot.

| Axe demandé | Travail réalisé | Portée de la validation |
| --- | --- | --- |
| Yeux et orbites | Ajustement réversible des globes : recul de 2 mm et réduction du rayon de 8 % ; masque des paupières âgées limité à leur surface antérieure | Aucun croisement transversal détecté dans les essais retenus ; contacts coplanaires et volumes imbriqués exclus |
| Âges | Quatre références 5/15/30/75, transition de formes et correctifs des réglages selon le stade ; développement facial et vieillissement régional | 21 transitions neutres ; amplitudes et trajectoire entre références artistiques |
| Corpulences | Adiposité globale et six régions : abdomen, flancs, bassin/fessiers, cuisses, bras, visage ; combinaison avec l'ancienne corpulence | Extrêmes individuels et combinaisons graisse/muscles ; aucun poids ou taux de graisse déduit |
| Musculature | Réglages global et régionaux conservés ; définition atténuée par la couverture adipeuse ; adaptation aux références d'âge | Le facteur d'atténuation musculaire enfant reste artistique |
| Visage | Huit réglages supplémentaires : oreilles taille/orientation, ouverture des paupières, arête nasale, épaisseur des lèvres, commissures, angle mandibulaire, asymétrie | Extrêmes et combinaisons sur les quatre âges ; vues de face/profil/trois-quarts |
| Calibration et intégrité | Ajustement explicite de stature aux références OMS/NCHS ; métadonnées d'âge dans les rapports ; UV/topologie conservées ; diagnostic indépendant yeux/corps | Huit ajustements de stature, préréglages et migration, sauvegarde/réouverture ; pas de certification biologique complète |

## Interface

45 réglages de proportions et de volumes, plus la transition d'âge. Les boutons 5/15/30/75 sélectionnent des formes ; la valeur intermédiaire n'est pas présentée comme un âge chronologique validé. « Stature source F/M » applique la médiane de la catégorie publiée choisie : OMS à 5 et 15 ans, NCHS États-Unis groupes 30–39 et 70–79 aux deux autres repères. Le groupe de 70–79 ans n'est pas une observation à exactement 75 ans.

Les six silhouettes restent éditables. Elles modifient corpulence, adiposité et muscles, avec remise à zéro des ajustements régionaux. Le visage, les proportions structurelles et le stade d'âge sont conservés. Les anciennes configurations omettant les nouveaux réglages et l'âge se chargent avec ces réglages neutres et le stade adulte.

## Preuves techniques

- `validation/modelisation-10/validation-lot-10.json` : matrice de 824 cas, dont 720 extrêmes individuels, 32 combinaisons graisse/muscles, 64 combinaisons simultanées et 8 neutres, sur les deux morphologies et quatre âges.
- Les références 5/15/30 ont été vérifiées dans les lots `final-F/M-0/1/2`. Les seniors affinés sont vérifiés dans `senior07-0/1`. `identite-hors-senior.json` prouve l'identité des 391 clés et expressions hors senior entre ces versions ; aucune régression d'une autre famille de formes n'est supposée sans vérification.
- 270 extrêmes et 32 combinaisons supplémentaires couvrent l'intégrité des réglages, les normales, les personnages indépendants et la mise à niveau historique.
- `transitions-finales.json` : 21 transitions âge/morphologie, avec contrôle corps et yeux.
- `validation-workflow.json` : huit statures, égalité des UV et de la connectivité avec 0.9, préréglages d'âge, migration 0.9 et réouverture avec drivers valides. Les méthodes antérieures de mesures et de repères passent leurs régressions.
- `ages-livraison`, `corps-livraison`, `visages-livraison` : scènes éditables et vues en argile ; les cadres de corps entier incluent les pieds.

Une conversion BMesh du maillage évalué provoquait un accès mémoire invalide dans Blender avec ce nombre de clés et la subdivision. Le diagnostic lit désormais directement les indices de sommets, arêtes et boucles, sans conversion BMesh. Les fixtures connues de croisement, séparation, coplanarité, bords ouverts et coordonnées invalides passent.

## Limites conservées explicitement

Le lot couvre les six axes fonctionnels demandés. Il ne termine pas toute la validation anatomique : les amplitudes de graisse, muscles, visage et vieillissement ne sont pas ajustées à des données individuelles de population. La calibration quantitative livrée porte sur la stature. Les plis très fins, les rides de peau détaillées et la totalité des grandes corpulences restent à approfondir. La section de tête de l'enfant est un substitut technique au périmètre crânien ; son protocole clinique n'est pas validé. Les données adultes de composition corporelle ne sont pas extrapolées comme normes pour les enfants.

Les sources et populations sont détaillées dans `Documentation-biologique.md` et `Specification-morphologies-corporelles.md`. Les champs de déformation et correctifs sont propres au projet. MPFB fournit des références géométriques CC0 ; CharMorph reste une référence fonctionnelle. Ce lot n'annonce pas une parité exhaustive avec leurs catalogues de morphs.
