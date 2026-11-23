# CONCEPTION F0-f — dents, langue, gencives (rapport d'étape : conception amorcée, rien produit)

Date : 2026-11-23. **Statut : non réalisé.** Ce document dit ce qui a été fait (recherche de données, un essai de mesure), ce qui ne l'a pas été, et ce qu'il reste à faire. Principe D-35 : données publiées plutôt que valeurs au jugé, « non vérifié » quand une valeur n'est pas vérifiable ; rien n'est présenté comme calibré cliniquement.

## 1. Données publiées trouvées (fichier `extension/data/dental_reference.json`)
- **Dents maxillaires antérieures, adultes — VÉRIFIÉ dans le texte intégral** : Alsahli A., Qali M., Baskaradoss J.K., AlOuda D., Alsaeed M., *Maxillary Anterior Teeth Dimensions: A Biometric Analysis in a Kuwaiti Population*, Clin Cosmet Investig Dent 2025;17:539-548, doi:10.2147/CCIDE.S551820 (126 adultes, modèles 3D en résine, couronne clinique). Largeur moyenne (écart-type) : centrale **8,83 (0,50)**, latérale **6,83 (0,53)**, canine **7,76 (0,43)** mm ; longueur : 9,83 (1,02), 8,00 (0,96), 9,14 (1,07) mm ; par sexe dans `dental_reference.json` (Table 3). Réserve : les écarts-types du résumé (0,65 / 0,52 / 0,58) diffèrent de ceux de la Table 2 ; on garde les tables. Une seule population : pas de généralisation.
- Les valeurs 8,71 / 6,75 / 7,81 mm (PubMed 25858215, 2015) rapportées plus tôt **n'ont pas pu être lues** (mur de cookies) : non vérifiées, non utilisées.
- **Dents lactéales** : deux études tabulées existent (islandaise, Acta Odontologica Scandinavica ; taïwanaise, JOCPD 25(2)) mais **aucun chiffre n'a été lu** : non vérifié.
- **Non trouvés** : largeur d'arcade et distance intercanine (enfant/adulte), dimensions de la langue, hauteur gingivale, usure du senior, éruption (calendrier des dentures lactéale/mixte/adulte). Le fichier le dit explicitement (`valeur: null`, `statut: non vérifié`).
La recherche web n'a pas donné accès aux tables de référence classiques (traités d'anatomie dentaire) : elles sont **protégées** ; seules des valeurs numériques issues d'articles ouverts peuvent être reprises, avec leur source.

## 2. Mesures de conception sur le corps natif
- La bouche du maillage natif est **fermée** (maillage fermé, 0 arête de bord dans la tête : mesuré en F0-b/A2) ; il n'y a pas d'intérieur de bouche.
- Une mesure de « largeur de la bouche » par bande horizontale a été tentée sur 5 morphologies ; **elle est invalide** (110–120 mm : elle englobe la largeur du visage à ce niveau, pas la fente buccale). La largeur de bouche exige des **repères placés sur les commissures** (`ch_l`, `ch_r` existent dans `landmark_sets.py` mais ne sont pas posés automatiquement sur un humain natif) : à placer, puis à vérifier à l'œil sur planche. **Aucune taille de dents n'est donc déductible à ce stade.** Hauteur nez–menton mesurée (distance 3D entre la pointe du nez et le menton, repères automatiques approximatifs) : 82,6 mm (défaut), 78,7 (homme âgé), 76,3 (femme jeune), 55,1 (enfant), 81,8 (homme adulte).

## 3. Conception proposée (à réaliser après validation des données)
- **Objets** : dents (incisives, canines, prémolaires, molaires, arcade supérieure et inférieure), langue, gencives, produits **procéduralement** (pas d'asset tiers), accrochés à la topologie de la tête par des repères de bouche ; matériaux d'émail, de gencive et de langue procéduraux.
- **Mâchoire** : os `jaw` enfant de `head` (à ajouter à la table du squelette), mandibule et dents inférieures pondérées dessus ; ouverture de la bouche = rotation de `jaw` ; le maillage natif étant fermé, l'ouverture exige une **fente buccale** dans les couches du groupe de nœuds (non existante).
- **Âge** : denture lactéale / mixte / adulte avec dimensions bornées d'après les tables publiées (non lues) ; usure chez le senior (non documentée).
- **Intégration** : `create`, `duplicate`, `rig_install/update/remove`, validateur (dimensions dans les plages publiées, pas d'interpénétration dents/lèvres, volume de cavité), planche bouche fermée et ouverte sur 3 morphologies.

## 4. Ce qui reste (tout)
1. Lire les tableaux publiés (dents permanentes et lactéales, largeur d'arcade, langue, gencive) et remplir `dental_reference.json` avec auteur, année, table, effectifs ; vérifier les trois valeurs déjà rapportées.
2. Poser les repères de bouche sur les humains natifs et vérifier la largeur de la fente à l'œil.
3. Créer la fente buccale et l'intérieur de bouche (travail sur le groupe de nœuds, lié à I-49 : la zone lèvres/nez se recoupe pour les formes masculines).
4. Générer, accrocher, peser, tester, photographier.
