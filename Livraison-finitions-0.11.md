# Finitions de modélisation 0.11

Blender 5.2 LTS uniquement. Cette passe poursuit la modélisation et ne constitue pas une validation anatomique complète.

## Relief du visage âgé

Un relief géométrique supplémentaire décrit les plis du front, la zone glabellaire et les plis latéraux près des yeux. Une texture de déplacement originale, calculée sur les UV et intégrée au fichier Blender, pilote un modificateur Displace après la subdivision. La cage, les UV et les formes d'âge sont conservées. Aucun scan ou image externe n'est utilisé.

Le nouveau réglage « Relief de peau âgée » porte le total à 46 réglages. À −1, il désactive ce relief supplémentaire ; 0 est la référence et +1 l'accentue. Son influence est nulle aux références de 5, 15 et 30 ans. Elle augmente entre les formes adulte et senior. Les amplitudes et motifs sont artistiques et ne sont pas des courbes biologiques ajustées.

## Correction révélée au niveau de rendu

Le contrôle à subdivision 2 détectait 18 paires croisées à l'intérieur des paupières de la forme féminine âgée, même sans le nouveau relief. Une correction locale dans une clé séparée les ramène à zéro avec un déplacement maximal de 0,0996 mm. Elle est modulée par la transition d'âge et la morphologie. La surface visible du regard et les globes n'ont pas été remplacés.

## Vérifications

- 30 cas de relief sur trois morphologies et cinq positions d'âge ; aucun croisement détecté du corps ou des yeux, et déplacement nul avant la transition vers le senior.
- 45 cas au niveau de rendu, soit 338 720 triangles, avec les intensités du relief et les extrêmes de six réglages de tête/yeux. Le budget a été porté explicitement à 400 000 triangles pour ces essais hors ligne ; le budget interactif reste à 250 000.
- 105 cas seniors masculins et 105 féminins, dont les extrêmes des 46 réglages et les combinaisons. La correction interne finale est vérifiée dans `extremes-feminin-final.json` ; sa pondération est nulle au pôle masculin.
- 21 transitions neutres et huit ajustements de stature ; préréglages, migration, texture intégrée et drivers après réouverture. Les rapports sont dans `validation/finitions-11`.
- Comparaisons avant/après et corps entiers dans `validation/finitions-11/avant-apres`.

## Audit des dimensions de développement

`dimensions-developpement.json` conserve stature, section technique de tête et enveloppe des globes selon les quatre références. Chez l'enfant, l'enveloppe Y des globes est d'environ 19,5–19,8 mm. Cette mesure de maillage n'est pas assimilée à la longueur axiale biométrique des études ophtalmologiques. Le rapport enregistre cette limite ; aucune correction automatique fondée sur une équivalence non établie n'a été appliquée. [Étude de développement axial](https://pmc.ncbi.nlm.nih.gov/articles/PMC6520278/) · [Biométrie pédiatrique en Allemagne centrale](https://pubmed.ncbi.nlm.nih.gov/33960004/)

Les proportions anatomiques fines des jeunes personnages, la diversité du vieillissement et les grandes corpulences restent des chantiers ouverts. La validation géométrique seule ne clôt pas ces travaux.
