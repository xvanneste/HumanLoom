# Reprise des proportions après la revue utilisateur

La 0.13 ne doit pas être considérée comme anatomiquement validée. Les contrôles de croisements précédents vérifient une propriété géométrique, pas la justesse d'une morphologie. La critique utilisateur invalide l'acceptation visuelle de ce lot.

## Erreurs confirmées et limites du diagnostic

1. **Repère iliaque placé trop bas.** `tools/global_physique_fields.py` plaçait le relief nommé iliaque à environ `0.529 × stature`, avec une faible variation latérale. Les références adultes sélectionnées dans ANSUR II placent l'iliocristale vers 0.59–0.63 de leur stature. Sur les deux références centrales retenues, le décalage de calcul est d'environ 12–13 cm aux dimensions de notre base. Une bosse au niveau de la hanche ne peut pas être renommée « crête iliaque » sans vérifier son emplacement sur la surface.
2. **Déformations définies par bandes et ratios choisis à la main.** Les gains de largeur et de profondeur, axes des membres et centres de relief n'étaient pas ajustés à un atlas de repères ni à des dimensions observées. Le grossissement multiplicatif du thorax conservait et accentuait la silhouette en V. L'écartement supplémentaire des bras dans le champ mélangeait aussi pose et tissus corporels.
3. **Motif costal non validé.** Les trois bandes de côtes et les creux voisins étaient générés mathématiquement. Ils n'étaient ni une identification des côtes de cette base ni un ajustement à une cage thoracique documentée. Ils sont retirés du candidat adulte.
4. **Mesures mal comparables aux protocoles.** La coupe technique à 76 % de la hauteur pouvait inclure des raccords avec les bras ; elle n'est pas un tour de poitrine clinique. Un ruban peut franchir les creux, contrairement au périmètre d'un contour de coupe concave. Les tours de bras fléchi et de cou ne se comparent pas automatiquement à des coupes horizontales dans notre pose. Ces équivalences ne sont plus utilisées.
5. **Correspondances articulaires encore approximatives.** Les centres d'épaule, coude, poignet, hanche, genou et cheville du moteur de travail sont des repères d'ingénierie. Ils ne constituent pas un atlas anatomique validé. Une distance entre centres articulaires ne peut pas être comparée directement à une longueur mesurée entre repères de surface du protocole.

Les niveaux d'un ventre musculaire, d'une surface mammaire et d'un repère osseux ne sont pas interchangeables. La proximité de leurs hauteurs ne prouve donc pas, à elle seule, qu'un groupe musculaire est correctement ou incorrectement placé.

## Données réellement examinées

Les deux CSV ANSUR II et le manuel de mesure ont été récupérés auprès du laboratoire OPEN de Penn State, qui diffuse les données publiques originales de l'US Army. Les fichiers comprennent 1 986 femmes et 4 082 hommes. Le manuel et le mémorandum sont conservés avec les fichiers sources, et plusieurs pages de protocole ont été examinées visuellement. [Source et téléchargements](https://www.openlab.psu.edu/ansur2/) · [Manuel de mesure](https://tools.openlab.psu.edu/publicData/ANSURII-TR11-017.pdf) · [Annonce de l'US Army](https://www.army.mil/article/188601/for_good_measure_natick_releases_raw_data_from_army_wide_anthropometric_survey)

La sélection de travail limite l'âge à 25–39 ans et la stature à ±4,5 % de celle de chaque base native : 676 dossiers féminins et 1 078 masculins restent admissibles. Une référence centrale est une ligne réelle proche du centre multivarié ; les exemples de volumes bas et haut sont aussi des lignes réelles, sélectionnées avec des contraintes de cohérence des tours et du cadre corporel. Les mesures ne sont pas un assemblage de percentiles indépendants. Les identifiants sources, critères, effectifs, unités et empreintes SHA-256 sont conservés dans `validation/proportions-14/anthropometric-profiles.json`.

Ces personnes sont des militaires adultes. Elles ne représentent pas toute la population. Les strates de tours ne permettent pas d'identifier un pourcentage de graisse, une masse musculaire ou une catégorie de santé. La normalisation linéaire par stature est une hypothèse de modélisation, pas une loi d'allométrie validée. Aucun résultat n'est extrapolé comme norme clinique à 5, 15 ou 75 ans.

## Changement de méthode dans le candidat adulte

- Utiliser des sections identifiées près des repères de poitrine et de bassin, puis une enveloppe convexe pour approcher le passage d'un ruban. Le plan ombilical reste provisoire ; soutien-gorge, respiration et compression des tissus ne sont pas simulés.
- Ajuster ensemble poitrine, abdomen et bassin avec une courbe de variation lisse préservant la forme entre les niveaux. Un accord numérique sur trois tours ne valide pas la silhouette entière.
- Reprendre les variations des tissus dans des coordonnées locales autour des membres. Les formes sculptées MakeHuman/MPFB servent de références graphiques CC0, distinctes des observations ANSUR. Les paramètres de ces formes ne sont pas des unités biologiques. Le code des autres générateurs n'est pas incorporé. [Licence officielle des assets](https://www.makehumancommunity.org/about/license.html)
- Séparer variations de graisse et de muscles, y compris leurs combinaisons. Préserver les doigts, pieds et contours orbitaires ; ne pas déplacer les axes osseux pour donner l'illusion d'un gain de masse.
- Régulariser le transport dans l'espace entre surfaces proches, notamment aux aisselles. Lisser seulement les voisins topologiques ne suffit pas lorsque deux pans de peau se font face.

Les expériences, ajustements chiffrés et rendus complets sont conservés dans `validation/proportions-14`. Elles ne remplacent pas la version installée. Les premiers candidats ont retrouvé certains tours tout en produisant des déformations des poignets, du cou ou des aisselles : ces échecs restent consignés. L'accord avec les tours n'a pas servi de critère suffisant pour les livrer.

### Diagnostic supplémentaire sur les contours et état du candidat 07

Le candidat masculin à volume haut a confirmé le problème de section : au niveau de poitrine retenu, la cage produit trois contours séparés, puis la subdivision produit un contour qui inclut les bras. Le périmètre brut passe d'environ 1,13 m à 1,37 m. Le contrôle numérique initial a donc échoué, malgré un accord sur la cage. `inspect_atlas14_sections.py` et `mesures-surface-07.json` conservent ce constat.

Une segmentation temporaire, attachée aux faces de la topologie et propagée par subdivision, distingue maintenant torse et bras pour ce diagnostic. Le contour du torse évalué est alors voisin de 1,12 m. La frontière de région reste à vérifier anatomiquement ; cette méthode n'est pas présentée comme une reproduction clinique du ruban, de la respiration ou du soutien-gorge.

Le candidat adulte 07 passe 18 configurations géométriques à subdivision 2, y compris des combinaisons avec la musculature, sans croisement transversal détecté du corps ni avec les yeux. Les trois contours suivis sur six configurations restent dans la tolérance numérique de travail de 1,5 % sur la surface évaluée. Les huit exemples éditables, leurs 48 paramètres, drivers et textures intégrées ont été vérifiés après réouverture. Ce sont des résultats techniques de candidat, pas une validation générale de l'anatomie, des longueurs des membres ou des formes d'âge. Aucun nouveau paquet n'a été installé.

## Conditions avant une nouvelle livraison

### Avancement du 19 novembre — atlas de surface 15

Un atlas de trente approximations de repères de surface est maintenant attaché à la topologie par coordonnées barycentriques. Le placement initial a révélé des rayons pelviens interceptant les avant-bras ; ce ciblage a été corrigé et contrôlé sur les deux bases. Une partition des régions par distance le long du maillage sépare aussi les membres du tronc pour leurs coupes obliques.

Les nouveaux axes servent au transport des formes, pas à identifier un squelette. Les centres de coude et de genou sont calculés sur une coupe locale : l'extrapolation des axes des ventres musculaires manquait le genou de 43 à 52 mm et ne constitue donc pas une localisation articulaire acceptable. Le détail, les captures et les limites sont conservés dans `validation/atlas-15/README.md`.

Le candidat adulte 12 ajoutait une référence d'enveloppe neutre du tronc et ajustait les trois contours sur la surface réellement subdivisée. Ses mesures et contrôles de croisements réussissaient, mais la revue visuelle a rejeté les renflements au-dessus des hanches. Le candidat 15 revient à la forme neutre précédente tout en conservant l'atlas, les centres de coupes locales et l'ajustement sur surface subdivisée. Le candidat 08 avait révélé un croisement dans une combinaison minceur et faible musculature ; le candidat 10 avait révélé un écart supérieur à 1,5 % après subdivision. Ces essais restent conservés. Le candidat actuel reste isolé de la version installée. L'attachement des repères et le calcul des axes fonctionnent sur les huit bases âge/morphologie ; ce contrôle ne valide pas leur anatomie.

### Critères toujours applicables

Les trois nouveaux ensembles fournis ont été inventoriés et les deux références FBX examinées dans Blender 5.2. La comparaison normalisée du masculin, les limites du modèle en grand écart et l'état du paquet MetaHuman sont détaillés dans [Analyse-modeles-ajoutes.md](Analyse-modeles-ajoutes.md). Ces formes artistiques complètent les comparaisons de volumes ; elles ne deviennent pas des normes de croissance ou de corpulence.

1. Vérifier un atlas de repères de surface et les axes des membres sur les deux bases, de face, profil et dos. Comparer des définitions équivalentes aux protocoles ; distinguer ce qui est mesuré, placé manuellement et seulement estimé.
2. Contrôler ensemble structure, longueurs segmentaires, largeur/profondeur du tronc et tours. Examiner les silhouettes et raccords entre niveaux, au-delà des seules sections ajustées.
3. Affiner les formes sculptées de minceur, de corpulence et de musculature à partir de références visuelles et dimensionnelles compatibles. Vérifier leurs combinaisons sans masquer un défaut par une baisse arbitraire de l'amplitude globale.
4. Traiter séparément les références de 5, 15 et 75 ans. Les coefficients adultes ne sont pas une validation des formes d'âge.
5. Terminer les contrôles géométriques, la migration et la réouverture une fois ces critères anatomiques satisfaits. Les tests logiciels viennent compléter l'acceptation anatomique.
