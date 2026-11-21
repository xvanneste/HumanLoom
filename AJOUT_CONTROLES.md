# AJOUT_CONTROLES — contrôles manquants et contrôles que l'on pourrait ajouter

Date : 2026-11-21. Branche de travail : `codex/natif`. **Proposition, rien n'est implémenté.** Sources : (a) état réel du dépôt (`extension/proportions.py`, `anatomy.py`, liste des 462 clés de forme `docs/audit/cles-forme-liste.json`) ; (b) liste des cibles de MPFB2/MakeHuman relevée dans ses docs locales (216 illustrations nommées, ✅ lues ; la liste n'est pas exhaustive des modificateurs) ; (c) noms d'exemples d'Anny (`head-fat`, `upperleg-height`, `stomach-pregnant`) ; (d) connaissance anatomique générale (⚠ non sourcée ici). Les licences de ces listes ne sont **pas** vérifiées : on s'inspire des **noms de fonctions**, on ne copie aucune cible.

## 1. Ce qui existe (48 contrôles) et ce qui manque d'après l'audit

**Corps** : corpulence, carrure, taille, bassin, profondeur du buste, cou (largeur), jambes, buste. **Graisse** : globale, volume hérité, couverture régionale, abdomen, flancs, bassin et fessiers, cuisses, bras, visage. **Muscles** : globale, épaules, pectoraux, dos, bras, abdomen, fessiers, cuisses, mollets, définition. **Visage (21)** : largeur/hauteur de tête, mâchoire (largeur, angle), menton, pommettes, nez (avancée, largeur, arête), bouche (largeur, commissures), lèvres (relief, épaisseur), yeux (écartement, hauteur, ouverture), front, oreilles (taille, orientation), asymétrie, relief de peau âgée.

**Constats** :
- **Aucun repère ni vertex group régional** : l'objet n'a qu'un groupe de sommets (`HM · Relief visage`) ; les 10 repères d'`anatomy.py` ne couvrent que taille/bassin/thorax, nez, bouche, yeux. **Seins, mamelons, nombril, mains, doigts, pieds, dents, langue : aucun repère, aucun contrôle** (vérifié : aucune occurrence de ces termes dans le code de `extension/` ; le **contenu du maillage** n'a pas été inspecté région par région). Ajouter ces contrôles suppose d'abord de **repérer ces régions** sur le maillage (repères automatiques, étape du plan 7).
- **Âge** (308 clés), **sexe**, **stature** (opérateur « Régler la taille ») existent mais hors des 48.
- Les **seins** ne sont **pas** pilotés par un contrôle propre : ils ne varient que par « Corpulence », « Couverture régionale » et « Pectoraux ».
- Le **ventre** : `fat_abdomen` et `muscles_abdomen` existent ; pas de forme (rond, tombant), de grossesse, de nombril, de tonicité.

## 2. Méthode pour ne pas créer 200 curseurs

MakeHuman décline presque chaque région en « translation x/y/z » et « échelle x/y/z ». Pour HumanLoom, deux niveaux :
1. **Contrôles de forme nommés** (ce document) : peu nombreux, parlants pour un artiste.
2. **Transformation de région générique** (mode avancé) : n'importe quelle région repérée (masque pondéré) reçoit *déplacer / mettre à l'échelle / gonfler*, sans multiplier les curseurs. Chaque contrôle de forme = un masque de région + une opération + (si besoin) une cible sculptée.

Chaque contrôle ajouté devient une couche de base locale de plus dans le groupe « HL Human » (DESIGN §7) ; le coût en vitesse est mesuré par ≈ +0,1 ms par couche, donc non bloquant (⚠ ordre de grandeur issu des prototypes, à remesurer).

## 3. Catalogue des contrôles candidats

Priorité pour le **film** (D-12) : **P1** = indispensable, **P2** = très utile, **P3** = utile / spécialisé. « Région » = existe-t-il déjà un repère exploitable ? Non = à créer.

### 3.1 Poitrine et tronc

| Contrôle | Priorité | Région | Note |
|---|---|---|---|
| **Volume des seins** | P1 | non | à relier à la corpulence et au sexe |
| Fermeté / affaissement des seins | P1 | non | lien avec l'âge (gravité) |
| Hauteur d'attache des seins | P2 | non | |
| Écartement des seins | P2 | non | |
| Pointe / projection des seins | P2 | non | |
| Asymétrie des seins | P3 | non | |
| Taille et projection des mamelons / aréoles | P2 | non | surtout un sujet de **matériau** (aréoles) |
| **Forme du ventre** (rond, plat, tombant) | P1 | partielle (abdomen) | |
| **Ventre de grossesse** | P2 | partielle | présent chez Anny (`stomach-pregnant`) et MPFB2 |
| Tonicité du ventre | P2 | partielle | |
| Nombril (hauteur, profondeur) | P3 | non | |
| Forme en V du buste (`torso-vshape`) | P2 | partielle | |
| Cage thoracique (largeur, profondeur) | P2 | partielle | `torso_depth` existe |
| Dos : cyphose, lordose, scoliose légère | P2 | non | posture |
| Trapèzes / pente des épaules | P1 | partielle | `shoulders` = carrure seule |
| Clavicules (relief) | P3 | non | |
| Poignées d'amour / bourrelets du dos | P3 | partielle | `fat_flanks` |
| Asymétrie du tronc | P3 | non | |

### 3.2 Bassin, fessiers, jambes

| Contrôle | Priorité | Région | Note |
|---|---|---|---|
| **Volume des fessiers** (séparé des hanches) | P1 | partielle | `fat_hips` mélange bassin et fessiers |
| Forme des fessiers (haut/rond) | P2 | partielle | |
| Écart entre les cuisses (« thigh gap ») | P3 | partielle | |
| Genoux : valgus / varus (jambes en X ou en O) | P2 | non | `l-leg-valgus` chez MPFB2 |
| Longueur de la cuisse / du mollet séparément | P2 | partielle | `legs` = longueur globale |
| Mollets : graisse (le muscle existe) | P3 | non | |
| Chevilles, tendons d'Achille | P3 | non | |
| Genoux (volume, relief de la rotule) | P3 | non | |

### 3.3 Bras et mains

| Contrôle | Priorité | Région | Note |
|---|---|---|---|
| Longueur du bras / de l'avant-bras / de la main | P1 | partielle | proportions des membres |
| Avant-bras : graisse et muscle | P2 | non | |
| Épaule : deltoïde (volume séparé du dos) | P2 | partielle | |
| **Mains : taille, longueur et épaisseur des doigts, écart des doigts** | P1 (film : gros plans) | non | forme du maillage des mains à vérifier ⬜ |
| Poignets, coudes (relief) | P3 | non | |
| Ongles | P3 | non | surtout géométrie et matériau |

### 3.4 Pieds

Taille, largeur, longueur des orteils, voûte plantaire, chevilles : **P2**, région non repérée. Détail de la forme du maillage des pieds à vérifier ⬜.

### 3.5 Cou et tête

| Contrôle | Priorité | Note |
|---|---|---|
| **Longueur du cou** | P1 | seule la largeur existe |
| Double menton / graisse sous-mentonnière | P1 | `neck-double`, `head-fat` |
| Pomme d'Adam | P2 | selon le sexe |
| Inclinaison de la tête / posture du cou | P2 | posture |
| **Forme de la tête** (ronde, ovale, carrée, rectangulaire, triangulaire, losange) | P1 | MPFB2 en propose 8 ; utile comme préréglages |
| Profondeur de la tête, occiput | P2 | |

### 3.6 Visage — détails absents

| Zone | Contrôles candidats | Priorité |
|---|---|---|
| **Sourcils** | hauteur, angle, avancée, arcade sourcilière | P1 |
| **Yeux** | poches sous les yeux, pli de la paupière (hauteur, angle, concavité), épicanthus, coins interne/externe, volume du globe, profondeur d'orbite, taille de l'œil (le globe est un objet séparé) | P1 |
| **Nez** | bosse, pointe (hauteur, largeur), ailes (évasement), narines (angle, largeur), septum, base, profil (concave/convexe), volume | P1 |
| **Bouche et lèvres** | arc de Cupidon, philtrum, lèvre supérieure/inférieure (volume, largeur, hauteur), sillons naso-géniens, fossettes, hauteur de la bouche | P1 |
| **Menton** | fente, proéminence, hauteur, largeur, prognathisme | P2 |
| **Joues et pommettes** | creux des joues, volume, hauteur, os | P1 |
| **Tempes, front** | forme du front (bombé, fuyant), tempes creuses | P2 |
| **Oreilles** | lobe, pavillon (décollement), forme pointue/carrée, hauteur d'attache | P2 |
| **Mâchoire** | muscle masséter, largeur du menton | P2 |
| **Dents, gencives, langue (manque confirmé)** | alignement, taille, dents du haut/du bas, canines, écart, couleur, gencives, langue ; **vérifié : `realistic.blend` ne contient que 3 objets maillage (Corps, Œil droit, Œil gauche), aucun code de dents/langue dans `extension/`** ; la cavité buccale du corps n'est pas inspectée ⬜ | **P1 pour le film** (sourire, parole, gros plans) : nécessite de **nouveaux objets** (dents, langue), leurs UV/matériaux et le lien avec l'ouverture de la bouche et les visèmes |

### 3.7 Peau, âge et morphologie globale

| Contrôle | Priorité | Note |
|---|---|---|
| **Stature en cm (champ numérique)** | P1 | fait aujourd'hui par un opérateur à dialogue |
| Proportion tête/corps (nombre de têtes) | P2 | Anny/MakeHuman |
| Dimorphisme (curseur de masculinité/féminité séparé du sexe) | P2 | à relier à la graisse et à la musculature |
| Gravité / affaissement avec l'âge (visage, seins, ventre, bras) | P1 | lien âge → forme |
| Cellulite, vergetures, rides, taches | P2 | **matériau et cartes**, pas de la géométrie (voir `RECHERCHE_PEAU.md`) |
| Pilosité du corps | P2 | déjà géré par le groom |
| Type de corps : poire, pomme, sablier, rectangle, triangle inversé | P2 | **préréglages** de graisse régionale, pas des contrôles de plus |
| Grossesse (corps entier : seins, ventre, bassin) | P3 | assemblage de contrôles |
| **Anatomie génitale (ajoutée sur demande de l'utilisateur)** | P3 | Contrôles anatomiques sobres, comme MPFB2 (`penis-length`, `penis-circ`, `penis-testicles`) et CharMorph (matériaux « censurés » + préférence « mode adulte ») : **masculin** : longueur, circonférence, testicules ; **féminin** : vulve (volume, lèvres), pilosité pubienne (groom). **Garde-fous proposés** : option **désactivée par défaut** (préférence de l'extension « Anatomie adulte »), **jamais disponible sur les âges enfant/adolescent** (désactivée si l'âge est inférieur à l'âge adulte), géométrie **séparée** (objet ou couche masquable) avec un matériau de recouvrement par défaut, aucune pose ni scène explicite. Nécessite de **nouveaux repères et zones** (comme les seins) |

### 3.8 Asymétries gauche/droite

Seule `facial_asymmetry` existe. Candidats : asymétrie de l'œil, de la bouche, de l'oreille, du nez, des épaules, des seins, des jambes (MPFB2 : 30+ `asym-*`). **P2** : un seul contrôle « asymétrie » par région plutôt que 30 curseurs.

## 4. Totaux et recommandation

- Environ **90 contrôles candidats** listés (hors génitaux et dents), dont **P1 ≈ 25**, P2 ≈ 40, P3 ≈ 25. Chiffres approximatifs : à recompter une fois la liste arrêtée.
- **Anatomie génitale** : ajoutée à la demande de l'utilisateur, avec garde-fous (option désactivée par défaut, indisponible aux âges enfant/adolescent).
- **Ce qui conditionne tout** : les **repères et zones automatiques** (seins, nombril, mains, pieds, bouche détaillée). Sans eux, impossible de construire les masques. C'est l'étape « repères automatiques » du plan, à placer **avant** les nouveaux contrôles.
- **Ordre proposé** : (1) repères/zones automatiques ; (2) contrôles P1 du tronc (seins, ventre, fessiers, trapèzes) et des proportions de membres ; (3) P1 du visage (sourcils, yeux, nez, lèvres, joues) ; (4) préréglages de type de corps/tête ; (5) le reste.
- **Limites** : j'ai **vérifié** l'absence de repères et de groupes régionaux, mais **pas** la qualité du maillage dans les mains, les pieds et la bouche (résolution suffisante pour des doigts et des lèvres détaillées ?). C'est un test à faire avant de promettre ces contrôles.
