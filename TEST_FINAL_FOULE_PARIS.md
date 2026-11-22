# TEST_FINAL_FOULE_PARIS — test de réception final (D-33) et galerie de vêtements

Date : 2026-11-22. Demande de l'utilisateur : (1) ajouter une **galerie de vêtements** au personnage ; (2) le **dernier test** de l'ensemble est le scénario « Paris Golden Hour Crowd Stress Test » ci-dessous ; (3) **l'analyste (Claude) exécute ce test final**, l'utilisateur teste ensuite l'interface lui-même.

Ce document contient : A. le scénario d'origine (texte intégral de l'utilisateur) ; B. l'analyse d'écart (ce que HumanLoom aura, ce qu'il n'aura pas, ce qui relève de Blender ou d'outils externes) ; C. la conception de la galerie de vêtements ; D. les lots ajoutés au plan ; E. le protocole d'exécution et les critères de réussite.

Règle du scénario à respecter dans le rapport final : **ne jamais prétendre qu'une fonction est native à HumanLoom si elle ne l'est pas** ; trois catégories explicites : « natif HumanLoom », « Blender seul », « outil supplémentaire ».

---

## A. Scénario (texte de l'utilisateur, intégral)

### HUMAN LOOM — PARIS GOLDEN HOUR CROWD STRESS TEST

**Objectif** : créer dans Blender une scène cinématographique photoréaliste représentant une rue parisienne très fréquentée en fin de journée, juste après une averse, avec une foule de personnages générés et animés à l'aide du plugin HumanLoom. Stress test complet en conditions de production : qualité des personnages, diversité morphologique, vêtements, rigging, animations, déplacements, interactions, stabilité, performances. **Priorité absolue : utiliser HumanLoom pour la génération et l'animation des humains** ; ne pas remplacer ses fonctions par des solutions externes sans le signaler.

**1. Environnement — rue parisienne** (Marais, Saint-Germain-des-Prés, Grands Boulevards) : immeubles haussmanniens en pierre claire, balcons en fer forgé, fenêtres détaillées, boutiques de vêtements à vitrines éclairées, boulangeries, cafés, restaurants, terrasses, enseignes et néons, lampadaires allumés, voitures garées et quelques véhicules en circulation, passages piétons, trottoirs, mobilier urbain, arbres, pavés et asphalte mouillés, flaques de tailles variées avec reflets réalistes. Rue assez longue pour observer des déplacements sur plusieurs dizaines de mètres.

**2. Ambiance — 19 h 30, été** : soleil très bas visible entre les immeubles ; lumière chaude orange et dorée ; rayons traversant la rue ; ombres longues ; éclairage indirect et rebonds ; reflets du soleil dans les flaques ; vitrines aux lumières colorées ; phares réfléchis sur la chaussée ; halos de lampadaires ; légère brume ; contraste lumière naturelle chaude / artificielle plus froide. Cycles pour le rendu final, éclairage physiquement cohérent, matériaux PBR.

**3. Foule — 150 personnages visibles** (niveaux de détail si nécessaire) : 80 marchant normalement, 25 marchant vite, 20 courant, 10 sautant ou franchissant des flaques, 10 immobiles ou discutant, 5 réalisant des actions spécifiques. Variété de tailles, silhouettes, morphologies, apparences ; adultes et seniors ; visages, coiffures, couleurs de cheveux ; proportions ; démarches, postures, vitesses, orientations, directions. Pas de clones ni de répétitions évidentes ; identité visuelle crédible.

**4. Vêtements et accessoires** : tous habillés, adaptés à une soirée parisienne après la pluie. Tenues : costumes et vestes élégantes, trench-coats, manteaux légers, jeans, pantalons, chemises, pulls, robes, jupes, streetwear, vestes en cuir, sweats à capuche, tenues sportives pour ceux qui courent ; sneakers, bottines, chaussures de ville, talons. Accessoires : sacs à main, sacs à dos, sacs de courses, téléphones, parapluies ouverts et fermés, casquettes, lunettes, écharpes. Combinaisons variées de matériaux, couleurs, textures, accessoires. Les vêtements suivent le corps sans intersections importantes avec la peau ou entre eux. Si HumanLoom gère la simulation textile, l'activer sur un groupe représentatif.

**5. Animations — 30 s à 24 i/s = 720 images**, toutes testées simultanément : *marche* (lente, normale, rapide, avec sac, avec téléphone, en groupe, avec changement de direction) ; *course* (jogging, sprint court, évitement d'obstacles, accélération/décélération, marche→course, course→arrêt) ; *sauts* (vertical, en avant, au-dessus d'une flaque, petit bond pour éviter une zone mouillée, réception avec flexion des genoux, reprise de la marche) ; *actions secondaires* (regarder son téléphone, discuter, se retourner, lever le bras, attendre au passage piéton, porter des sacs de courses, ouvrir un parapluie si disponible). Transitions sans changement brusque de posture.

**6. Interactions avec l'environnement** : déplacement naturel ; éviter les collisions entre personnages ; respecter trottoirs et passages piétons ; contourner les obstacles ; éviter les véhicules ; adapter les déplacements à la densité ; certains traversent la rue ; certains sautent les flaques. Effets secondaires si techniquement possible : éclaboussures, ondulations de l'eau, ombres animées, reflets dynamiques, mouvement des vêtements et accessoires. Pas de glissement au sol, pas de traversée d'objets.

**7. Quatre caméras** : A plan général de la rue ; B travelling à hauteur humaine au milieu des piétons ; C contre-jour vers le soleil (silhouettes, reflets, halos, volumétrie) ; D gros plans (marche, course, saut ; déformations, vêtements, mains, pieds, animations). Profondeur de champ modérée, mouvements fluides.

**8. Qualité visuelle** : Cycles, 3840 × 2160, 24 i/s, 30 s, matériaux PBR, soleil + sources locales, réflexions réalistes, volumétrie légère, flou de mouvement, débruitage, gestion des couleurs AgX ; version de prévisualisation plus légère sous Eevee.

**9. Tests de performance** pour 10, 25, 50, 100, 150 personnages : fps du viewport, temps de génération des personnages, temps de préparation des animations, temps de calcul d'une image, RAM, VRAM si disponible, stabilité des animations, collisions/déformations, qualité visuelle de près et de loin. Niveaux de détail pour les personnages éloignés si possible.

**10. Livrables** : (1) fichier Blender organisé en collections (personnages, bâtiments, lumières, véhicules, effets) ; (2) animation de 30 s ; (3) quatre caméras ; (4) image finale 4K photoréaliste ; (5) prévisualisation de l'animation ; (6) tableau de performances par densité ; (7) rapport des problèmes : collisions, clipping, rigging, vêtements, animations, ralentissements.

**Règles** : pas d'animation identique synchronisée sur toute la foule (décaler cycles, varier vitesses et directions) ; pieds ancrés au sol pendant les contacts ; sauts avec impulsion, phase aérienne, réception crédibles ; vêtements adaptés à chaque morphologie ; animations fluides avec plusieurs types simultanés ; **ne pas prétendre qu'une fonction est native si elle ne l'est pas** (distinguer natif HumanLoom, Blender seul, outils supplémentaires).

**Résultat attendu** : une scène parisienne spectaculaire, vivante et crédible, foule dense variée, habillée et animée, dans une rue mouillée au coucher du soleil ; évaluation technique objective des capacités et limites de HumanLoom.

---

## B. Analyse d'écart : que couvrira HumanLoom, que faudra-t-il ajouter

Légende : **N** = natif HumanLoom (dans l'addon livré) ; **B** = fait avec Blender seul, hors addon (script du test) ; **X** = outil ou ressource supplémentaire (hors addon, à signaler) ; **?** = faisabilité à mesurer.

| Exigence du scénario | Source prévue | Écart / lot |
|---|---|---|
| Générer 150 humains variés (sexe, âge adulte/senior, morphologie, taille) | **N** : `create_human` + 46 contrôles + façade `humanloom` | **Manque** : un **générateur de foule aléatoire** (tirage borné et reproductible par graine, garde-fous anatomiques). Lot C1 |
| Visages, coiffures, couleurs de cheveux | **N** : modèles de visage/morphologie, groom 11 régions (cheveux natifs) | 150 grooms natifs = coût énorme : **?** ; prévoir cheveux en version légère pour la foule (LOD, lot C2) |
| Vêtements et accessoires | **Absent aujourd'hui** (ECART_FONCTIONNALITES #1, #15, #21 : « non planifié ») | **Nouveau lot V** (galerie de vêtements), voir §C |
| Rig corps compatible bibliothèque | **N** : A2 (en cours) | dépend de A2, A2b |
| Animations de marche / course / saut / actions | **N** : galerie + retargeting (A1…A3) sur la **bibliothèque locale de l'utilisateur** (non redistribuée, D-27) | À mesurer : présence réelle des clips voulus (marche avec sac, téléphone, parapluie, discuter, saut sur flaque…). Tout clip absent est **déclaré absent** dans le rapport, jamais simulé en silence |
| Transitions marche→course→arrêt, boucles, décalage de phase | **N** (partiel) : NLA, décalage, vitesse | **Manque** : couche de **locomotion** (voir C3) |
| Déplacement le long de trajets, évitement des personnes/obstacles/véhicules, trottoirs, passages piétons | **Non prévu dans HumanLoom** | **B/X** : script de test (trajectoires précalculées, évitement simple) ; HumanLoom ne fournira pas de moteur de foule. À écrire dans le rapport comme « outil supplémentaire » |
| Pieds sans glissement, sauts crédibles (impulsion, vol, réception) | **N** (partiel) : root motion géré (A3), mesure du glissement | La vitesse du root motion doit correspondre à la vitesse de translation de l'objet ; mesure automatique du glissement des pieds. Sauts = clips de la bibliothèque, avec le root motion extrait |
| Éclaboussures, ondulations, reflets dynamiques | **B/X** (Blender : simulation de fluide ou nœuds de géométrie, plans réfléchissants) | hors périmètre HumanLoom ; signalé |
| Mouvement des vêtements et accessoires (tissu) | **N** si lot V4 (cloth sim optionnelle) sinon **B** | **?** |
| Rue parisienne, immeubles, véhicules, lumières, brume | **B/X** | **Hors HumanLoom.** Aucun asset tiers n'est inclus dans le dépôt ; le décor sera construit en procédural (blocs, matériaux PBR, éclairage) ou avec des ressources libres de droits que l'utilisateur acceptera nommément. Qualité « film à gros budget » **non garantie** : à annoncer honnêtement |
| 4 caméras, profondeur de champ, flou de mouvement, AgX, Cycles/Eevee | **B** | simple |
| LOD pour les lointains | **Non prévu** | **Nouveau lot C2** : niveaux de détail corps (sous-division, modificateurs de nœuds désactivés, cheveux simplifiés, rig sans visage) |
| Tableau de performances 10/25/50/100/150 | **B** : harnais de mesure hors processus (script), RAM/VRAM via psutil / nvidia-smi | à écrire (lot T) |

**Réserves honnêtes à annoncer dès maintenant**
1. Le rendu **4K Cycles de 720 images** n'est pas réalisable dans un délai raisonnable sur une machine individuelle ; livrables prévus : une **image finale 4K** (Cycles) + la séquence de **prévisualisation Eevee** à résolution réduite, plus le **temps mesuré par image** et l'extrapolation du coût total. La machine (GPU, RAM) sera relevée en début de test.
2. La qualité de l'environnement dépendra de ce qu'on peut construire sans assets tiers redistribués ; ce n'est pas une fonctionnalité de HumanLoom.
3. Le fichier .blend du test contiendra des animations de la bibliothèque locale de l'utilisateur : il **ne sera pas commité** (D-27, `.gitignore`).
4. La physique textile et l'éclaboussure sont des pistes **à mesurer**, pas des promesses.
5. Les visages animés (expressions) ne sont pas indispensables à ce test : les gros plans de la caméra D se feront avec le visage neutre si le lot facial n'est pas livré, ce qui sera indiqué.

---

## C. Galerie de vêtements (nouveau, lot V)

### C1. Principes
- **Topologie fixe du corps** (10 582 sommets) : on peut accrocher un vêtement au corps par **correspondance de surface** (triangle d'ancrage + coordonnées barycentriques + décalage normal) calculée une fois, puis recalculée à la demande quand la morphologie change (le corps est un MESH natif évalué avec ses modificateurs, comme pour le groom).
- **Vêtement d'origine HumanLoom (livrable, GPL)** : générés **procéduralement à partir de régions de la surface du corps** (masques de sommets : torse+bras, jambes, pieds, mains, cou…) → offset normal, épaisseur, ourlets, déformation par nœuds. Cela donne des **pièces de base originales** (t-shirt, chemise, pull, pantalon, jean, short, jupe, robe, veste, manteau/trench simple, capuche, chaussures de plusieurs formes, chapeau/casquette, écharpe, lunettes) **sans aucun asset tiers**, donc sans problème de licence. Ils seront « schématiques mais propres » ; le réalisme vient des matériaux et variantes.
- **Vêtements importés** (de l'utilisateur ou de packs qu'il choisit, jamais redistribués par nous) : import .blend/.fbx/.obj, **ajustement automatique** (Surface Deform ou liaison propre, transfert des poids de peau depuis le corps), vérification de pénétration, réglage de l'ajustement.
- **Masquage de la peau** sous les vêtements (masques de sommets du corps), pour éviter la peau qui traverse et alléger le rendu.
- **Couches** (sous-vêtement, haut, veste, manteau) avec ordre, épaisseur croissante, pas d'intersection entre couches (offset cumulatif).
- **Peau/déformation** : les vêtements héritent des **poids de peau du corps** (A2), donc suivent le rig et les animations importées. Correctifs au niveau des articulations (coude, genou) mesurés : volume, étirement.
- **Accessoires** : points d'attache (sockets) sur la main, l'épaule, la tête, le visage, le dos : sacs à main, sacs à dos, sacs de courses, téléphone, parapluie (ouvert/fermé), lunettes. Le téléphone et le parapluie nécessitent des **poses de main** (A-poses de préhension) : lot V3.
- **Matériaux** : variantes de couleurs/textures (procédurales : tissage, cuir, denim, laine) sans textures tierces ; chaque pièce expose couleur, rugosité, motif.
- **Simulation de tissu** (cloth) : option par pièce (robe, manteau, écharpe) avec cache ; à mesurer sur 5 personnages représentatifs ; désactivée par défaut dans la foule.

### C2. Galerie (interface)
Même schéma que la galerie d'animations (index + cache + recherche + catégories + favoris + vignettes générées hors processus) : catégories (Hauts, Bas, Robes, Vestes, Chaussures, Couvre-chefs, Accessoires), vignettes, boutons « Ajouter », « Retirer », « Couleur… », ordre des couches, indicateur de pénétration, « Importer un vêtement… » (dossier de l'utilisateur), **tenues** enregistrables (liste de pièces + couleurs).

### C3. Ce qui NE sera pas promis
- Patrons de couture réalistes, glissement des tissus, plis dynamiques de qualité production sans simulation (à mesurer).
- Pièces tierces fournies dans le dépôt.
- Ajustement parfait pour toute morphologie extrême : un **rapport de pénétration chiffré** sera produit sur un jeu de morphologies de test.

---

## D. Lots ajoutés au plan (à valider par l'utilisateur, ordre proposé)

| Lot | Contenu | Dépend de |
|---|---|---|
| **V0** | Conception : accrochage par surface, masques du corps, poids hérités, mesures de pénétration, jeu de 5 morphologies de test, planche de contrôle | A2 |
| **V1** | Vêtements procéduraux d'origine (≈ 15 pièces de base) + ajustement + masque de peau + couches + matériaux | A2, V0 |
| **V2** | Galerie de vêtements (panneau, index, catégories, favoris, tenues) + import de vêtements de l'utilisateur avec ajustement auto | V1, modèle de la galerie d'animations |
| **V3** | Accessoires + points d'attache + poses de main (téléphone, sac, parapluie) | V1, A3 |
| **V4** | Simulation de tissu optionnelle (cache, mesure) | V1 |
| **C1** | **Moteur de foule natif** : ensembles d'éléments variables, tirage aléatoire à graine, foule **figée** (enregistrée, modifiée seulement sur demande), garde-fous, diversité mesurée (pas de clones), comportements et trajectoires, évitement, décalage de phase | modèles, V2, A3 |
| **C2** | Niveaux de détail (LOD) pour personnages éloignés | A2, V1 |
| **T** | **Test final « Paris Golden Hour »** : exécuté par l'analyste, rapport complet, tableau de performances | tous les lots ci-dessus + A3 |

Ordre global révisé : **A2 → A2b → A3 → V0–V3 → C1, C2 → A4 (vignettes, favoris) → T → (V4)**. Le visage (Fa–Fe) et A5 ne bloquent pas le test final et peuvent passer avant ou après selon la priorité de l'utilisateur ; sans lot facial, les gros plans utilisent le visage neutre.

---

## D bis. Précision de l'utilisateur (2026-11-22) : les manques sont à combler par l'analyste

Les points manquants (moteur de foule, trajectoires, évitement, animations absentes comme le **parapluie**, etc.) seront **réalisés par l'analyste**, en **analysant les autres animations de la bibliothèque** : composition et adaptation d'actions existantes plutôt que renoncement. Conséquences :
- **Animations manquantes** : inventaire des clips voisins (ex. parapluie = geste de lever le bras + maintien de la main en préhension ; téléphone = bras plié + tête inclinée ; discuter = gestes de bras + orientation de la tête), puis **création d'actions dérivées** par script (mélange de couches NLA, découpe/boucle de segments, retouche de quelques os), étiquetées « dérivée, générée par l'analyste » et mesurées (continuité, absence de glissement). Si un résultat n'est pas crédible, il est signalé tel quel dans le rapport.
- **Foule (révisé, même jour)** : le moteur de foule devient une **fonctionnalité native de HumanLoom** (lot C1, classe N). Principe : l'utilisateur définit des **ensembles d'éléments variables** (plages de morphologie/âge/sexe, visages, coiffures et couleurs, tenues et pièces de la galerie, accessoires, animations par comportement, vitesses) et un **moteur aléatoire à graine** tire chaque personnage dans ces ensembles. La foule est **figée** : le résultat (graine, tirages, personnages créés) est enregistré dans le fichier et **ne change plus** à la réouverture, au rechargement ni à un changement de réglage ; seule une demande explicite (« Régénérer », « Régénérer ce personnage », changement de graine) la modifie. Les trajectoires, l'évitement simple et le placement sur zones (trottoirs, passages) font aussi partie du moteur (comportements : marche, course, saut, attente, discussion), avec décalage de phase et vitesses variées. Le moteur est utilisé tel quel pour le court métrage du test final.
- **Livrable vidéo (révisé)** : au lieu d'une simple prévisualisation, un **fichier vidéo d'environ 30 secondes, en cycle (boucle sans raccord visible)**, produit depuis la scène du test (le cycle impose des trajectoires et animations périodiques : personnages qui sortent du champ et rentrent aux positions de départ, cycles de marche/course calés sur la durée). Rendu : Cycles si le budget temps le permet, sinon Eevee, avec le choix annoncé et les temps mesurés ; image 4K fixe en plus.
- Ces développements ne doivent ajouter aucune dépendance de l'addon livré à des fichiers de la bibliothèque (D-27).

---

## E. Protocole du test final (réalisé par l'analyste)

**Condition préalable (utilisateur, 2026-11-22)** : le court métrage ne démarre qu'**après** la fin, les tests et la validation de l'addon (tous les lots A, V, C, avec 0 régression, `validate_install` vert, suite complète verte). Pas de scène de test tant que l'addon n'est pas validé ; le film est la réception, pas un moyen de développer.

1. **Isolé** : script exécuté dans un processus Blender 5.2 distinct, avec une installation propre de l'extension (zip), jamais dans la session de l'utilisateur. Machine relevée (CPU, RAM, GPU/VRAM).
2. **Palier par palier** : 10 → 25 → 50 → 100 → 150 personnages, chaque palier mesuré (génération, habillage, application des animations, fps viewport, temps image, RAM/VRAM), avec arrêt et diagnostic si un palier échoue.
3. **Attribution** : chaque fonction utilisée est étiquetée N / B / X dans le rapport.
4. **Mesures automatiques** : glissement des pieds (cm/s pendant les contacts), pénétration vêtement/peau (volume, nombre de sommets), distance minimale entre personnages (collisions), unicité visuelle (distance minimale entre vecteurs de contrôles et d'habits), continuité des transitions (saut de pose maximal), planchers de fps.
5. **Images de contrôle** pour validation à l'œil par l'utilisateur : 4 caméras, une planche de 12 personnages en gros plan, une planche de transitions.
6. **Livrables** : ceux du §10, dans un dossier hors dépôt (le fichier .blend n'est pas commité), plus un rapport `RAPPORT_TEST_FINAL.md` (commitable, sans contenu de la bibliothèque) avec tableau de performances et liste des problèmes.
7. **Critères de réussite** (à figer au démarrage de T, valeurs indicatives) : 0 plantage ; 150 personnages générés et habillés ; glissement des pieds < 2 cm/s en contact sur 95 % des clips ; pénétration vêtement/peau < 1 mm sur 99 % des sommets de pièce proche ; aucune interpénétration personne-personne ; unicité : aucun couple de personnages avec même contrôles et même tenue ; fps viewport mesuré et publié (pas de seuil promis) ; temps par image publié.
8. Le test ne remplace pas les tests unitaires : chaque lot garde ses validateurs dans `tools/` ; le test final est un test de **réception**.
9. Après T : l'utilisateur teste l'interface (installation du zip dans son Blender, clics, annulation Ctrl+Z, panneaux).
