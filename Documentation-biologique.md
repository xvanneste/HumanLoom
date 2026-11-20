# Référentiel biologique du générateur humain

État documentaire du 20 novembre 2026. Le corps et le visage restent en validation. L'étude s'étend désormais aux cheveux : voir [nature du cheveu et intégration au prototype Blender 5.2](Recherche-scientifique-cheveux.md) pour les sources primaires, paramètres géométriques et mécaniques, essais au repos et limites actuelles sous gravité. Les préréglages de nature sont illustratifs ; ils ne constituent pas une calibration biologique du solveur.

La [passe 0.11](Livraison-finitions-0.11.md) ajoute un relief géométrique artistique du visage âgé et renforce les vérifications à subdivision 2. L'audit des dimensions de développement consigne aussi les limites des mesures de tête et de globe ; il ne transforme pas leurs substituts géométriques en mesures cliniques validées.

Mise à jour 0.10 : le [bilan de modélisation](Livraison-modelisation-0.10.md) remplace le statut expérimental des fonctions désormais livrées. Les quatre références d'âge, l'adiposité régionale et les réglages faciaux étendus sont disponibles avec des amplitudes artistiques. Les boutons de calibration ajustent uniquement la stature aux médianes OMS à 5/15 ans et NCHS par groupes 30–39/70–79 aux repères adultes. Les références NCHS restent transversales ; elles ne définissent pas une trajectoire individuelle de vieillissement. Le diagnostic inclut maintenant un contrôle distinct des yeux et des orbites.

## Statut du prototype

Les âges repères retenus par l’utilisateur le 19 novembre 2026 sont **5, 15, 30 et 75 ans**. Ils définissent les cibles du travail de calibration. Les paramètres internes des expériences MPFB ne sont pas assimilés à ces âges.

Les vingt-neuf réglages du prototype 0.9 utilisent des champs de déformation définis pour la base Blender Studio. Leurs amplitudes et leurs zones d’influence sont encore des choix artistiques. Les tests de géométrie vérifient des propriétés telles que les coordonnées finies, les aires de faces et la conservation du personnage. La version 0.5 a ajouté une comparaison dimensionnelle et un ajustement de stature à des références publiées. La version 0.6 a ajouté les repères locaux et l’ajustement de dimensions mesurées. La version 0.7 permet leur transport et la proposition de partenaires symétriques à vérifier. La version 0.8 ajoute le diagnostic géométrique et la correction locale des paupières internes. La version 0.9 ajoute une première musculature adulte globale et régionale.

Les formes d’âge issues de MPFB servent à expérimenter le transfert entre topologies. La convention nominale d'âge du logiciel est documentée dans le cache des références ; elle ne valide pas biologiquement ses formes. MPFB et CharMorph restent des références de fonctionnalités pour notre propre implémentation.

## Sources et caractéristiques à documenter

| Domaine | Source scientifique retenue | Données et population | Utilisation proposée |
| --- | --- | --- | --- |
| Croissance de l’enfant | Standards de croissance OMS | Taille, périmètre crânien, périmètre du bras et plis cutanés selon les indicateurs et les âges couverts | Calibrer des mesures de référence pour les premières étapes du développement. [OMS](https://www.who.int/tools/child-growth-standards/standards) |
| Croissance de 5 à 19 ans | Référence OMS de taille selon l’âge | Courbes par âge et sexe | Préparer la stature de référence et ses variations. [OMS 5–19 ans](https://www.who.int/tools/growth-reference-data-for-5to19-years/indicators/height-for-age) |
| Données numériques de croissance | Tables CDC avec paramètres LMS | Courbes américaines de taille, poids et autres indicateurs, selon le fichier choisi | Conserver les percentiles et les paramètres de la courbe avec leur source. [CDC](https://www.cdc.gov/growthcharts/cdc-data-files.htm) |
| Mensurations corporelles | NCHS, NHANES août 2021–août 2023, rapport publié en 2025 | Population des États-Unis de 2 ans et plus, mesures et distributions par groupes | Définir les références de stature, de circonférences et de longueurs pour les variables effectivement publiées. [Rapport NCHS](https://stacks.cdc.gov/view/cdc/174595) |
| Rapport jambes et tronc | Étude longitudinale de proportions corporelles | Enfants et adolescents japonais, taille debout, taille assise et longueur des jambes | Construire des trajectoires distinctes pour les segments du corps. [Étude](https://pubmed.ncbi.nlm.nih.gov/21561299/) |
| Repères et dimensions du visage | 3D Facial Norms, FaceBase | Repères anatomiques, distances de surface et mesures au compas, données décrites pour une population d’ascendance européenne | Définir les mesures faciales et leurs méthodes. Les statistiques agrégées et les données individuelles ont des modalités d’accès propres. [Notes techniques](https://www.facebase.org/resources/human/facial_norms/notes/) |
| Croissance du visage | Étude de trajectoires fondée sur 3D Facial Norms | Modèles de développement de la forme et de la taille faciales | Déterminer des régions à modifier selon le développement. [Étude](https://pmc.ncbi.nlm.nih.gov/articles/PMC10776214/) |
| Vieillissement facial | Analyse de 456 surfaces faciales 3D | Étude transversale, 14–83 ans, population d’Europe centrale | Étudier les trajectoires régionales de vieillissement et leurs différences selon le sexe. [Étude](https://pmc.ncbi.nlm.nih.gov/articles/PMC9759541/) |
| Musculature | Janssen et collaborateurs, 2000 | IRM corps entier de 468 hommes et femmes de 18 à 88 ans | Documenter la masse et la répartition musculaires. La conversion en volume extérieur demande un modèle anatomique supplémentaire. [Notice de l’étude](https://pubmed.ncbi.nlm.nih.gov/10904038/) |
| Composition corporelle et vieillissement | Suivi longitudinal sur vingt ans | Participants de 60 ans et plus, composition corporelle, alimentation et activité physique | Distinguer les variations de masse grasse et de masse maigre dans les formes de référence. [Étude](https://pubmed.ncbi.nlm.nih.gov/33255771/) |
| Asymétrie du visage | Étude de photogrammétrie 3D | Mesure globale d’asymétrie faciale dans l’échantillon étudié | Préparer un contrôle de l’asymétrie avec alignement et méthode définis. [Notice de l’étude](https://pubmed.ncbi.nlm.nih.gov/24406564/) |

Les notices d’études musculaires et d’asymétrie constituent ici un repérage bibliographique. Leur méthode complète et leurs tableaux doivent être examinés avant d’en déduire des amplitudes de déformation.

## Mesures qui guideront les réglages

La [spécification des morphologies corporelles](Specification-morphologies-corporelles.md) complète ce référentiel : graisse et musculature globales et régionales, structure, définition et interactions avec l'âge. Elle répertorie les sources DXA, IRM et scans 3D retenues pour l'étude. Aucun pourcentage de graisse ou poids musculaire n'est encore calibré dans le générateur.

Cette correspondance est une proposition d’ingénierie pour le générateur. Chaque mesure doit reprendre le protocole de sa source.

| Réglage ou famille | Mesures à établir sur le personnage | Travail nécessaire |
| --- | --- | --- |
| Taille réelle | Distance entre le plan d’appui des pieds et le sommet du crâne, avec une pose définie | Consigner pose, unité et niveau d’évaluation du maillage |
| Longueurs des jambes et du buste | Repères de bassin et mesures compatibles avec les définitions de taille assise et de longueur des jambes | Établir la correspondance entre repères du modèle et protocole anthropométrique |
| Carrure, cou, bassin et profondeur du buste | Largeurs, profondeurs ou circonférences avec niveaux de coupe identifiés | Compléter les sources pour chaque définition et placer les repères |
| Tour de taille | Circonférence d’une coupe dont la hauteur et le protocole sont enregistrés | Comparer uniquement des mesures prises selon une définition compatible |
| Corpulence | Plusieurs circonférences et profils de surface, avec informations de composition corporelle lorsque disponibles | Développer une répartition anatomique des volumes et tester les combinaisons |
| Largeur et hauteur de tête | Mesures crâniennes et mesures faciales distinctes | Contrôler plusieurs dimensions lorsqu’un curseur modifie toute la tête |
| Mâchoire et menton | Largeur mandibulaire et projection du profil sur un référentiel défini | Compléter le protocole de profil et le placement des repères |
| Nez | Largeur entre les alares, hauteur et protrusion selon le protocole retenu | Placer les repères anatomiques correspondants |
| Bouche et lèvres | Largeur entre les commissures, hauteurs et relief des lèvres | Distinguer les dimensions modifiées par chaque contrôle |
| Yeux | Distances entre canthi et dimensions des ouvertures palpébrales | Vérifier ensemble les paupières, les orbites et les globes oculaires |
| Pommettes et front | Dimensions régionales du visage et profils de surface | Compléter les mesures avant de calibrer les amplitudes |

FaceBase documente notamment les repères alare, cheilion et endocanthion ainsi que des mesures crâniennes obtenues au compas. Les distances de surface et les mesures directes gardent leurs protocoles respectifs dans notre correspondance. [Définitions FaceBase](https://www.facebase.org/resources/human/facial_norms/notes/)

## Structure d’une référence de calibration

Chaque valeur intégrée au futur système de mesures devra être accompagnée des informations suivantes.

- Identifiant de la mesure et définition anatomique.
- Unité et méthode de mesure.
- Source, tableau ou figure, version et date de consultation.
- Population étudiée, effectif, âge et autres variables effectivement renseignées.
- Type d’étude, en distinguant suivi longitudinal et comparaison entre individus.
- Statistique publiée, par exemple moyenne, médiane, percentile, écart-type ou erreur standard.
- Repères du maillage et méthode de calcul utilisée dans Blender.
- Écart entre le modèle généré et la référence choisie.

La moyenne, la médiane, l’écart-type et l’erreur standard seront conservés sous leurs intitulés propres. Le calcul d’une distribution conjointe de plusieurs traits demandera les corrélations ou les données appropriées. Le tirage indépendant actuel des curseurs reste une variation artistique.

## Conséquences pour la construction des personnages

1. **Croissance**. Calibrer séparément stature, segments corporels et proportions faciales. Les observations longitudinales sur les jambes et le tronc soutiennent cette séparation. [Étude des proportions](https://pubmed.ncbi.nlm.nih.gov/21561299/)
2. **Âge et maturation**. Préparer plusieurs formes de référence et conserver une plage de variations individuelles. Les trajectoires faciales étudiées motivent des transitions régionales, avec la population de référence conservée dans les données. [Trajectoires faciales](https://pmc.ncbi.nlm.nih.gov/articles/PMC10776214/)
3. **Vieillissement**. Développer les formes du visage et les variations de composition corporelle avec des sources distinctes. [Vieillissement facial](https://pmc.ncbi.nlm.nih.gov/articles/PMC9759541/) · [Composition corporelle](https://pubmed.ncbi.nlm.nih.gov/33255771/)
4. **Variabilité individuelle**. Utiliser les distributions disponibles pour choisir des références variées et rendre explicite leur population d’origine. [Distributions NHANES](https://stacks.cdc.gov/view/cdc/174595)
5. **Validation**. Associer les tests du maillage à un contrôle dimensionnel et à une revue visuelle en vues de face, de profil et de trois-quarts.

## Lot 0.5 livré · Stature adulte et contrôle dimensionnel

Le tableau 7 du rapport NCHS NHANES 2021–2023 fournit les références de stature adulte intégrées. Les groupes vont de 20–29 ans à 80 ans et plus, avec les catégories féminine et masculine publiées et les percentiles P05, P50 et P95. Quarante valeurs publiées ont été transcrites manuellement depuis le tableau officiel, page imprimée 8. Les deux P95 du groupe 80 ans et plus sont indisponibles et restent explicitement absents. Le rapport est dans le domaine public. [Rapport NCHS, tableau 7](https://stacks.cdc.gov/view/cdc/174595/cdc_174595_DS1.pdf)

Les références décrivent une population des États-Unis. Les différences entre groupes d’âge proviennent d’une enquête transversale et ne représentent pas une courbe de vieillissement d’un individu. Choisir un groupe change la référence de taille, sans générer une forme anatomique d’âge. Appliquer la référence ajuste uniformément l’échelle du personnage. Aucune interpolation entre percentiles ou extrapolation des valeurs absentes n’est proposée.

Le panneau « Mesures et référence » calcule les étendues du corps évalué selon les axes locaux transformés, avec les unités de scène. La stature est l’étendue sur l’axe local vertical. La pose adulte de référence est nécessaire pour l’interprétation anthropométrique. Une pose fléchie ou une déformation extrême peut modifier cette mesure. La largeur affichée est une étendue de boîte englobante qui comprend les bras.

Un repère bassin peut être placé manuellement sur un sommet en mode Édition. Son parentage suit les déformations du corps. Les distances sol→repère et repère→sommet constituent des contrôles techniques. Leur placement anatomique reste à valider et elles ne constituent pas encore une mesure normalisée de longueur des jambes ou de taille assise.

L’export JSON conserve les mesures, l’écart à la référence, la population, le tableau, la période d’enquête, la source et l’empreinte SHA-256 du fichier de valeurs intégré. Il inclut la base, les réglages et la transformation du modèle pour rendre le contrôle reproductible. Les préréglages conservent aussi le choix de référence. Les anciens préréglages restent lisibles.

Les contrôles Blender 5.2 couvrent rotations, échelles non uniformes, parent transformé, scènes en centimètres, absence d’un percentile, persistance de la référence, déplacement du repère, export et réouverture. La scène `validation/calibration-05/Calibration-stature.blend` compare les six références P05/P50/P95 des adultes de 20–29 ans. Elle illustre uniquement la stature sur les deux bases adultes.

## Lot 0.6 livré · Repères et dimensions locales

Le panneau « Repères et dimensions locales » propose dix repères manuels. Le bassin sert au rapport de segmentation. Trois niveaux de coupe servent à l’abdomen, au bassin et au thorax. Les six repères faciaux sont les alares, les commissures labiales et les canthi internes, à gauche et à droite du personnage. FaceBase fournit les définitions anatomiques de ces points. Il précise notamment que le placement des alares demande une vérification sous plusieurs angles. Aucune statistique faciale n’a été importée à ce stade. [Définitions FaceBase](https://www.facebase.org/resources/human/facial_norms/notes/)

Chaque repère est attaché à un sommet. Il suit les déformations et reste déplaçable vers un autre sommet avec la commande de placement. Sa précision est limitée par la densité et la topologie du maillage. Il faut contrôler son emplacement en vues de face, de profil et sous le nez. La scène de revue utilise des placements approximatifs de test, et ne constitue pas un atlas anatomique validé. Les repères sont sauvegardés dans le fichier Blender. Les préréglages JSON de réglages ne transportent pas encore cet atlas de repères.

Les largeurs du nez et de la bouche et la distance intercanthale sont des distances droites entre deux points de surface. Les périmètres du buste sont calculés sur des intersections du maillage évalué avec le plan XY local passant par le repère. Les contours sont assemblés par identité d’arête, puis le contour fermé unique entourant l’axe local du buste est retenu. Les contours séparés des bras sont exclus. Une coupe ouverte ou ambiguë est refusée. Lorsqu’un plan traverse exactement des sommets, un déplacement numérique minime évite la dégénérescence et est consigné dans le rapport. Les transformations et les unités sont prises en compte.

Ces périmètres de surface ne reproduisent pas tous les effets d’un ruban de mesure, notamment les concavités et la compression. Le protocole NHANES du tour abdominal situe le niveau près du bord supérieur latéral de l’ilium droit, à la ligne médio-axillaire, avec une posture et une respiration définies. Une coupe à la taille visuelle la plus fine ne suffit donc pas à établir cette équivalence. Aucun percentile de tour de taille n’est appliqué automatiquement. [NHANES, section 3.4.8](https://stacks.cdc.gov/view/cdc/127207)

Sept mesures peuvent piloter un réglage existant : les trois périmètres, les trois distances faciales et le rapport sol→repère bassin / stature. L’ajustement échantillonne cinq valeurs du réglage, vérifie leur sens de variation, puis cherche la cible dans les limites −1 à +1. Une cible hors plage ou un échec restaure le réglage initial. Les dimensions voisines peuvent changer avec le réglage. L’ajustement du rapport bassin utilise « Longueur des jambes » et peut aussi changer la stature. Il ne déduit aucune norme de longueur de jambe ou de taille assise.

Le rapport dimensionnel passe en version 2 et conserve les indices et positions des repères, les méthodes, les valeurs et les éventuelles erreurs de coupe. Le format des préréglages reste en version 1.

Les contrôles couvrent une section polygonale de périmètre analytique connu, des contours séparés, le refus d’un contour ouvert, les plans passant par des sommets, les transformations et les unités. Les sept ajustements ont été vérifiés sur les morphologies féminine, intermédiaire et masculine. Le placement par opérateur, le refus d’un repère décalé de son sommet, la restauration hors plage et la réouverture ont été contrôlés. Les quatre images et la scène sont dans `validation/anatomie-06`. Les traits colorés de cette scène sont des instantanés de revue, à régénérer après une modification du corps.

## Lot 0.7 livré · Transport et symétrie des repères

Un jeu de repères peut être exporté et importé seul, ou inclus dans un préréglage de personnage. Le format `human_modeling.landmarks` version 1 conserve les indices des sommets et une empreinte SHA-256 de la topologie indexée d’origine. L’empreinte utilise les sommets comptés, les arêtes, les polygones et leurs coins. Les coordonnées et les déformations restent libres. Les deux morphologies sur notre topologie commune peuvent ainsi partager un jeu de repères. Un nombre de sommets identique ne suffit pas à autoriser le transfert.

L’import fusionne les repères fournis et conserve les autres repères du destinataire. À 100 %, un préréglage de personnage transporte les repères s’il en contient. Avec une intensité inférieure à 100 %, les repères existants restent en place. Les anciens préréglages sans repères restent compatibles. Une erreur restaure les réglages et les objets de repère, avec leur apparence précédente, et supprime les seuls objets créés pendant la tentative.

La commande « Compléter les paires par symétrie » recherche les partenaires absents des alares, commissures et canthi internes par réflexion sur la forme neutre. Elle conserve les partenaires déjà présents. Les points proposés portent le statut `mirrored_review`, visible dans le panneau et dans le rapport, jusqu’à un nouveau placement manuel. Cette proposition facilite le repérage. Elle ne démontre pas une symétrie biologique et ne remplace pas la revue de chaque côté du visage.

La compatibilité de topologie assure la correspondance des indices. Elle ne valide pas la position anatomique après changement de morphologie ou sculpture du maillage. Les jeux fournis dans `validation/reperes-07` conservent les placements approximatifs de travail et ne constituent pas un atlas anatomique certifié. Aucune donnée biologique chiffrée supplémentaire n’est introduite dans ce lot.

Les contrôles couvrent l’export et l’import natifs, le transfert entre morphologies, les préréglages et leurs mélanges, dix contenus invalides, une connectivité différente à nombre de sommets constant, la symétrie sans remplacement, deux échecs simulés avec restauration, et la réouverture. Les essais de mesures et des préréglages précédents restent valides.

## Lot 0.8 · Contrôle géométrique et paupières internes

Le panneau « Contrôle du maillage » calcule un diagnostic du corps évalué avec les modificateurs actifs. Il conserve un instantané et permet un nouvel export JSON. Le contrôle couvre les coordonnées finies, les composantes, les bords ouverts, les arêtes non manifold, les faces sans aire et les croisements transversaux de triangles sans sommet commun. Les contacts coplanaires, les volumes imbriqués, certains replis entre faces voisines et les intersections avec les yeux séparés sont exclus. Au-delà de 250 000 triangles, la recherche des croisements est explicitement indiquée comme non calculée. Un résultat nul ne constitue donc pas une certification anatomique.

Sur la base adulte brute, le test détectait des croisements aux pieds et dans la tête. Avec la subdivision de niveau 1 utilisée dans la revue, 82 paires subsistaient sur la surface interne des paupières féminines. La morphologie masculine et le mélange à 50 % n’en présentaient pas avec ce test. Les chiffres concernent des paires de triangles et ne représentent pas 82 défauts anatomiques indépendants.

Une correction locale des surfaces internes ramène ce nombre à zéro avec un déplacement maximal de 0,877 mm environ. Elle est portée par des clés de forme dédiées, modulées par la morphologie et les réglages concernés. Elle préserve les indices de sommets et les formes de base d’origine. Les nouveaux personnages la contiennent. Pour les personnages existants, la commande « Corriger les paupières internes » ajoute la couche sans remplacer les réglages. La couche reste réversible dans les clés de forme.

Les essais vérifient cinq morphologies neutres, 24 extrêmes autour des yeux et de la tête, l’application sur une ancienne base, la répétition sans doublon, les dépendances, les préréglages et la réouverture. Les 120 extrêmes et 32 combinaisons des réglages restent valides. Les vues de face, de trois-quarts et du corps entier sont dans `validation/qualite-08`. La correction reste localisée à l’intérieur des orbites et ne constitue pas une refonte du visage.

## Expériences d’âge du 19 novembre 2026

Les essais `age-transfert-03` à `age-transfert-05` utilisent des correspondances de triangles et un recalage régional des bras et des pieds. Le recalage des bras réduit l’écart maximal de correspondance d’environ 23 cm à moins de 10 cm dans l’essai féminin, mais des irrégularités anatomiques et des croisements supplémentaires subsistent. Ces essais ne sont pas intégrés à l’extension.

Les essais `age-champ-01` à `age-champ-03` explorent un champ continu avec une transformation verticale monotone et des échelles transversales positives. Les profils géométriques et les repères sources sont conservés dans `validation/source-growth/references.npz`, issus des géométries CC0 MPFB 2.0.18. Les coefficients de mélange et d’atténuation sont des choix artistiques expérimentaux. La correspondance avec les cibles de 5, 15, 30 et 75 ans reste à établir. La revue de profil révèle encore des volumes du thorax à corriger. Les résultats restent des études, sans commande d’âge livrée.

## Ordre du prochain travail de calibration

### Première musculature adulte · 0.9

Les neuf champs de musculature sont des déformations artistiques originales de la surface adulte, indépendantes du réglage actuel de corpulence. Ils ne représentent pas une segmentation interne des muscles. Les paramètres locaux corrigent le global avec une saturation dans la plage prévue. La masse maigre DXA n'est pas interprétée comme une masse musculaire, et aucun pourcentage de graisse ou poids de muscles n'est annoncé.

Les six silhouettes proposées sont des points de départ éditables. Le nom « fitness » ne mesure ni la performance ni la santé du personnage. Les amplitudes restent modérées et ne constituent pas une couverture de toutes les corpulences. Les données répertoriées dans la spécification seront utilisées pour une calibration ultérieure, avec les méthodes et populations correspondantes. Les tests de ce lot portent sur l'intégrité et la compatibilité technique ; ils ne valident pas les amplitudes biologiques.

### Repères retenus : 5, 15, 30 et 75 ans

Les essais `age-cibles-01` à `age-cibles-05` utilisent les âges demandés. Le cache source conserve ces cibles et les paramètres nominaux MakeHuman dans `validation/source-growth/references-5-15-30-75.json`. Cette conversion suit la convention du logiciel source ; elle n'est pas une courbe biologique validée. Les autres dimensions de la base adulte ne deviennent pas automatiquement représentatives d'une personne de 30 ans.

À 60 mois, les références OMS utilisées sont les médianes arrondies de stature : 109,4 cm pour les filles et 110,0 cm pour les garçons. Les repères de périmètre crânien sont 49,9 et 50,7 cm. Ils sont ajustés séparément ; leur combinaison n'est pas un percentile conjoint. La section horizontale mesurée sur le maillage reste un substitut technique dont le protocole doit être comparé à la mesure clinique. Les tableaux et lignes sources sont consignés dans `validation/source-growth/who-60-months.json`. [Stature OMS 0–5 ans](https://www.who.int/tools/child-growth-standards/standards/length-height-for-age)

À 180 mois, les statures médianes arrondies utilisées sont 161,7 cm pour les filles et 169,0 cm pour les garçons. La correction verticale est distribuée sous la tête. Les rapports régionaux ne sont pas calibrés par ce tableau. Les lignes publiées et les sources sont conservées dans `validation/source-growth/who-180-months.json`. [Stature OMS 5–19 ans](https://www.who.int/tools/growth-reference-data-for-5to19-years/indicators/height-for-age)

Les variations de joues, nez et menton de l'enfant restent artistiques. Pour le senior, les premiers essais modifient les paupières, les lèvres, le nez et les tissus de la partie inférieure du visage. Les tendances sont informées par l'étude transversale de Velemínská et collègues ; les amplitudes ne sont pas ajustées aux données individuelles. La peau et les rides fines ne sont pas traitées. La revue visuelle montre encore une différenciation insuffisante entre adulte et senior. [Étude du vieillissement facial](https://doi.org/10.1038/s41598-022-26376-8)

Le contrôle de `age-cibles-04` porte sur 21 combinaisons : trois morphologies et sept positions du paramètre d'âge. Aucun croisement transversal n'a été détecté après subdivision de niveau 1. `age-cibles-05` conserve la même géométrie avec les âges cibles inscrits dans l'asset et les légendes corrigées. Les 48 essais de largeur/hauteur de tête et position des yeux sur les formes de 5, 15 et 75 ans ne détectent pas non plus de croisement. Les quatre statures de 5 et 15 ans sur la surface subdivisée restent à moins de 2 mm des références choisies. Ces contrôles ne valident ni les collisions entre yeux et corps ni les seize autres réglages adultes appliqués aux formes d'âge. Les résultats dimensionnels et les essais de réglages sont consignés dans `age-cibles-05/dimensions-et-reglages.json`. Ces candidats restent hors de l'extension installée.

La subdivision réduit la stature de 0,83 à 0,92 mm par rapport à la cage ajustée. Elle réduit aussi la section de tête de l'enfant d'environ 2,6 mm par rapport à la cible. Ce dernier écart est enregistré ; il ne doit pas être présenté comme un ajustement exact du périmètre crânien évalué.

Un contrôle distinct entre les objets yeux et corps détecte 250 à 284 paires croisées par œil sur les adultes neutres, et 304 à 310 sur les seniors expérimentaux. Le défaut n'est donc pas limité au transfert d'âge. Les comptes incluent les surfaces orbitales internes et ne sont pas un décompte des défauts visibles. Les paires doivent être localisées et examinées en coupe avant correction. Les résultats figurent dans `age-cibles-05/ajustement-yeux.json`. Le diagnostic nul du corps seul ne permet pas de conclure à l'absence d'interpénétrations de l'ensemble du personnage.

La stature adulte dispose d’un premier contrôle. Les outils de repérage et de mesure locale sont disponibles. La suite porte sur la validation d’un atlas anatomique des repères sur les deux morphologies, puis la calibration du rapport jambes/tronc et des dimensions faciales avec des protocoles et populations compatibles. Les formes d’âge expérimentales seront réexaminées à partir de ces contrôles, puis la musculature et la répartition des volumes corporels seront enrichies.

### Mise à jour 0.12 : corpulence étendue

Huit silhouettes sont maintenant proposées. Les champs radiaux et leur adaptation aux âges sont artistiques et leurs amplitudes ne sont pas calibrées sur des poids ou des pourcentages de graisse. Les volumes d'enveloppe et sections techniques servent au contrôle de monotonie ; ils ne remplacent pas des mesures anthropométriques cliniques. Les résultats géométriques finaux et leurs limites figurent dans Livraison-corpulences-0.12.md.


### Reprise de la morphologie globale en 0.13

La quantité de tissus, leur répartition régionale, la musculature et les reliefs osseux sont maintenant traités séparément. Le nouveau réglage concerne tronc et membres ; la minceur ne se réduit plus au signe négatif d'un ventre. Les références examinées, leurs populations et les décisions de modélisation sont détaillées dans Recherche-morphologie-globale.md. Les amplitudes restent artistiques et les détails osseux sont approximatifs sur cette topologie. Aucun coefficient biologique ajusté n'est revendiqué.


### Statut corrigé après revue des proportions

La documentation de la 0.13 avait informé le vocabulaire des paramètres sans calibrer correctement leurs positions et proportions. Cette insuffisance est explicitement reconnue. Les CSV ANSUR II originaux et leur manuel ont maintenant été examinés ; des références adultes cohérentes et des ajustements expérimentaux sont conservés séparément. Les équivalences de mesure non établies sont exclues. Voir Audit-proportions-et-reprise.md. Ni les candidats adultes ni leurs accords sur quelques tours ne valident les formes d'âge ou l'anatomie complète.

