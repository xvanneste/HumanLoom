# Morphologie globale 0.13

**Statut révisé après revue utilisateur : proportions anatomiques non validées.** Les résultats géométriques ci-dessous restent des preuves techniques ; ils ne valident pas les placements ni les proportions. Voir `Audit-proportions-et-reprise.md` pour les erreurs identifiées et la reprise de méthode. La 0.13 reste conservée comme état de développement.

Cette passe corrige le défaut de conception signalé sur la 0.12 : le ventre dominait la variation, alors que la corpulence doit concerner l'ensemble du corps. Les références, populations, conséquences et limites sont consignées dans `Recherche-morphologie-globale.md`.

## Comportement livré

Le nouveau réglage « Corpulence globale » agit sur le thorax, le dos, l'abdomen, le bassin, les bras, les avant-bras, les cuisses, les mollets, le cou et des tissus limités du bas du visage. Ses pôles de minceur et d'adiposité sont distincts. Une intégration de champ continu remplace la juxtaposition de renflements abdominaux ; une couverture lisse atténue les petits reliefs sous la graisse. Les doigts, pieds, poignets et orbites sont protégés.

La minceur reçoit une couche de modelé séparée pour les clavicules, le sternum, les côtes inférieures, les repères iliaques, les omoplates et les genoux. Les muscles restent paramétrables indépendamment. Leur relief est renforcé par groupes et atténué par la couverture adipeuse. Ces repères de surface sont des approximations sculptées sur la topologie existante ; le détail costal reste grossier à cette résolution.

Le total est de 48 réglages. Les huit silhouettes utilisent maintenant la nouvelle corpulence globale et la musculature ; elles remettent les anciens volumes à zéro. Les trois anciens réglages globaux sont conservés dans une section repliée « Volumes des anciennes versions » pour permettre la lecture des anciens préréglages et leur ajustement. Ils ne constituent plus la méthode conseillée pour créer une silhouette.

Les clés, UV et indices existants sont conservés. La migration ajoute les nouvelles clés et le nouveau paramètre à zéro, et conserve les valeurs des réglages. Les personnages ayant une musculature positive peuvent recevoir le nouveau modelé musculaire même si la corpulence reste à zéro : la conservation exacte de leur surface n'est donc pas revendiquée. La scène 0.12 est conservée séparément.

## Vérifications du candidat 04

- 72 configurations au niveau de rendu, subdivision 2 et 338 720 triangles par corps : trois morphologies, quatre formes d'âge, minceur, adiposité et combinaisons avec la musculature ; aucun croisement transversal détecté du corps ni avec les yeux. Rapport `surface-rendu-04.json`.
- 54 configurations aux trois transitions d'âge intermédiaires, subdivision 1 : aucun croisement détecté. Rapport `transitions-04.json`.
- 109 cas adultes féminins et 109 masculins : extrêmes des 48 contrôles, combinaisons graisse/muscles et huit combinaisons aléatoires par morphologie. Aucun croisement, bord non manifold ou face d'aire nulle détecté. Les yeux sont contrôlés sur les cas explicitement identifiés dans les rapports `extremes-feminin-04.json` et `extremes-masculin-04.json`.
- Sections techniques sur huit régions : les périmètres augmentent du pôle mince au neutre puis au pôle adipeux sur les deux morphologies. Rapport `sections-04.json`. Les coupes horizontales des bras sont obliques à leur axe ; ces valeurs ne sont pas des tours cliniques standardisés.
- Préréglages, huit silhouettes, huit ajustements de stature, migration depuis la 0.12, identité des UV et de la topologie et réouverture : `validation-workflow.json`.

Les preuves se trouvent dans `validation/morphologie-globale-13`. Les corps entiers de face, profil, dos et trois-quarts sont dans `revue-livraison-04` ; les détails anatomiques face/dos dans `details-04`. `Morphologies-corporelles.blend` conserve les huit exemples éditables.

## Portée scientifique

La documentation guide les compartiments, la localisation et les interactions. Les amplitudes ne sont pas ajustées à des scans individuels ou à une distribution clinique. Aucun poids, IMC ou pourcentage de graisse n'est calculé. L'adaptation aux âges utilise des limites artistiques, avec des détails osseux et musculaires réduits chez l'enfant ; elle ne constitue pas une courbe pédiatrique validée. La diversité des répartitions et les formes extrêmes restent à affiner visuellement. Les tests de croisement ne suffisent pas à certifier l'anatomie.
