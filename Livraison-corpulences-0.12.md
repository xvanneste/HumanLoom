# Corpulences étendues 0.12

Blender 5.2 uniquement. Le lot reste consacré à la modélisation du visage et du corps.

Le nouveau réglage « Corpulence étendue » porte le total à 47 réglages. Il augmente ou réduit les volumes du tronc et des membres autour de leurs axes. La bande des aisselles est protégée ; son volume reste piloté par les réglages régionaux existants. Son influence diminue lorsque les réglages existants de graisse et de corpulence sont déjà poussés, afin de limiter leur cumul. Le transport sur les formes d'âge conserve une amplitude artistique réduite chez l'enfant et l'adolescent, sans descente abdominale chez l'enfant. Ces choix ne sont pas des coefficients biologiques mesurés.

Le panneau « Silhouettes » regroupe huit points de départ éditables, dont « Très mince » et « Forte corpulence ». Le réglage de musculature reste indépendant. À zéro, le nouveau champ ne modifie pas la géométrie dans les 21 configurations comparées. Une correction de maintenance séparée traite le raccord interne de la paupière féminine adulte : 18 croisements au niveau de rendu ramenés à zéro, avec un déplacement de cage maximal de 0,0969 mm. Cette correction est exclue explicitement du test de neutralité du nouveau champ.

## Vérifications du candidat final 09

- 96 cas : trois morphologies, quatre âges, cinq intensités et des combinaisons extrêmes. Les volumes augmentent sur les séries testées ; aucun croisement transversal détecté du corps ou avec les yeux.
- 27 cas intermédiaires d'âge : aucun croisement détecté.
- 24 cas à subdivision 2, soit 338 720 triangles par corps : aucun croisement détecté du corps ou avec les yeux. Le budget hors ligne est explicitement porté à 400 000 triangles.
- 21 comparaisons à paramètre nul : différence maximale de coordonnées égale à zéro ; import/export de préréglage et migration conservant les réglages.

Rapports : `validation/corpulences-12/plage-finale-09.json`, `transitions-finales-09.json`, `surface-rendu-final-09.json` et `neutralite-et-migration.json`. Les candidats précédents et leurs échecs sont conservés séparément pour diagnostic ; ils ne sont pas livrés.

Les vues de face, profil, dos et trois-quarts des deux morphologies, avec les corps entiers, figurent dans `validation/corpulences-12/revue-livree-09`. Le fichier `Morphologies-corporelles.blend` conserve les huit exemples éditables.

## Limites et suite

Le volume d'enveloppe en litres n'est pas un poids. La section technique à 60 % de la hauteur n'est pas une mesure clinique du tour de taille. Aucun pourcentage de graisse ni IMC n'est déduit. Les champs sont originaux ; aucun code de MPFB ou CharMorph n'est incorporé.

La suite de modélisation porte sur la calibration des repères anatomiques, la répartition régionale des fortes corpulences et l'affinement des formes jeunes et âgées. La recherche d'intersections ne valide pas à elle seule l'anatomie et ne couvre pas toutes les combinaisons possibles.



Une régression complémentaire sur la forme adulte féminine couvre 107 cas, dont les extrêmes des 47 réglages et huit combinaisons aléatoires : aucun croisement, face d'aire nulle ou bord non manifold détecté. Rapport : validation/corpulences-12/extremes-final-09.json.

