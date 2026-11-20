# HumanLoom 0.15 - Cheveux et pilosité

Le groom est intégré à l'extension, exclusivement dans Blender 5.2. Le code de production est dans `extension/groom.py` et `extension/groom_fibers.py`. Il ne dépend pas des scripts de prototype ni des fichiers de validation.

## Utilisation

Sélectionner un corps HumanLoom, puis ouvrir **Humain > HumanLoom · Cheveux et pilosité**. Onze zones indépendantes sont disponibles : cheveux, sourcils, barbe, moustache, torse, abdomen, dos, bras, jambes, aisselles et pubis.

Les boutons Court, Long, Bouclé, Crépu et Barbe courte ajoutent des points de départ procéduraux. **Pilosité adulte** ajoute les neuf zones communes ; aisselles et pubis sont des ajouts explicites. Ces boutons préservent les couches déjà présentes. Pour changer une coiffure existante, modifier ses réglages et reconstruire ses guides. La présence des couches n'est déduite ni du sexe, ni de l'âge, ni d'une origine du personnage.

Chaque zone possède longueur de contour, nature de fibre, variation de longueur, irrégularité, direction, nombre de guides, densité par m², quantité d'aperçu, rayon, graine, couleur, proportion de fibres grises et rugosité.

### Viewport léger et rendu dense (0.15.1)

Le bloc **Viewport et rendu** sépare **Densité au rendu / m²** et **Viewport (% du rendu)**. Le rendu utilise la densité complète, quelle que soit la fraction d'aperçu. Les boutons **Léger** (10 %), **Équilibré** (30 %) et **Complet** (100 %) permettent un choix rapide ; le curseur et **Appliquer mon pourcentage** permettent toute valeur entre 0 et 100 %. À 0 %, les mèches interpolées sont masquées dans le viewport, tout en restant présentes au rendu.

Ces commandes concernent la zone sélectionnée, ou toutes les zones du personnage si la case correspondante est cochée. Elles préservent les guides sculptés, la densité au rendu et les paramètres de simulation. Les pourcentages par zone sont conservés dans le `.blend` et les exports JSON existants. La densité complète s'applique via le bouton de matière / densité / dynamique.

La fraction désigne une densité de distribution, pas un nombre exact imposé de cheveux. Un niveau de subdivision du corps différent entre aperçu et rendu peut aussi modifier légèrement le nombre de mèches échantillonnées. `tools/validate_groom_quality26.py` compare les vrais graphes d'évaluation VIEWPORT et RENDER à résolution de surface identique et vérifie leur indépendance.

**Appliquer matière / densité / dynamique** conserve les guides sculptés. Les changements de longueur, nature, direction, graine ou nombre de guides nécessitent **Reconstruire les guides** : cette opération remplace la sculpture de la zone et peut être annulée dans Blender.

**Sélectionner les guides** permet ensuite d'utiliser Curves Sculpt. **Peindre la densité** sélectionne le groupe de poids correspondant sur le corps et entre en Weight Paint. Revenir en Object Mode après peinture. La reconstruction conserve ce masque et rééchantillonne les guides dedans. Un masque entièrement vide provoque un message et conserve le groom précédent.

Le JSON transfère les **réglages procéduraux**, sans les positions sculptées ni les poids peints. Enregistrer le `.blend` pour conserver le groom complet. L'import refuse de remplacer une couche existante ; la supprimer explicitement ou utiliser un autre personnage. Les matériaux sont indépendants entre personnages.

## Blender 5.2 natif

### Correction de couverture et diagnostic de gravité (0.15.2)

La densité de cheveux par défaut passe de 700 000 à **1 800 000 cheveux/m²**, soit de 70 à 180 cheveux/cm² avant modulation par le masque. L'ancien réglage produisait une couverture faible même à 100 % d'aperçu. Ce nouveau point de départ artistique est cohérent avec les mesures de densité occipitale sur des volontaires adultes sains : [Comparison Between Trichoscopic and Histopathological Evaluations of Hair Parameters](https://pmc.ncbi.nlm.nih.gov/articles/PMC9113037/). Ce n'est pas une valeur universelle, notamment pour tous les âges ou toutes les régions du crâne.

Les boutons **Clairsemé / Normal / Dense** appliquent respectivement 70 / 180 / 250 cheveux/cm² au cuir chevelu. Ils ne changent que la densité : guides sculptés, matériau, niveau d'aperçu et dynamique restent conservés. Les scènes existantes gardent leurs réglages ; cliquer **Normal** corrige leur densité sans reconstruire les guides. Le masque peint continue de moduler la distribution : une densité nominale ne garantit pas une implantation uniforme.

Le mode **Suivi sans physique**, auparavant nommé « Suivre le corps », n'applique aucune chute sous gravité. Le panneau affiche maintenant le mode réellement appliqué au modificateur. Pour simuler : choisir **XPBD expérimental**, appliquer la dynamique, revenir à la première image puis lire la timeline. Une image isolée à la première frame montre la forme de départ. Voir le [manuel Hair Dynamics 5.2](https://docs.blender.org/manual/id/5.2/modeling/geometry_nodes/simulation/hair_dynamics.html).

Les anciennes planches 25 et 27 utilisaient le suivi Animation, sans gravité ; elles ne constituent pas une validation physique. `tools/diagnose_groom28.py` mesure le mouvement et les longueurs de guides sur le cuir chevelu avec collisions. `tools/render_groom28.py` compare l'ancienne densité, la nouvelle densité sur les mêmes guides, puis une forme calculée par XPBD sur 128 guides. Pour rendre cette dernière sans dépendre d'un cache de simulation différent entre viewport et rendu, le résultat natif à l'image 13 est figé puis interpolé. Aucune chute artificielle ni correction de longueur n'est ajoutée après le solveur. Cette dernière scène est une revue statique après simulation, pas un bake animé portable.

Sur ces 128 guides courts avec collisions, les essais à 4 sous-pas / 1 024 itérations puis 4 / 4 096 dépassent le seuil de diagnostic de 5 % d'allongement dès l'image 3. Passer à 2 sous-pas / 16 384 itérations aggrave le cas près de l'oreille. Le profil de revue à **8 sous-pas / 4 096 itérations**, souplesse 0,7 et souplesse des racines 0,4, reste sous **3,46 %** sur les douze pas calculés, avec racines fixes et une descente moyenne finale des pointes d'environ 25 mm. Ces erreurs résiduelles empêchent de parler de calibration biologique ou de validation générale des collisions. Les paramètres physiques existants ne sont pas réécrits automatiquement ; les essais infructueux restent dans les journaux de validation.

Les objets sont des Hair Curves attachés par UV, avec indices de triangles et coordonnées barycentriques d'origine. La pile utilise **Interpolate Hair Curves**, **Hair Dynamics**, **Set Hair Curve Profile** et **Principled Hair BSDF**. Aucun système de particules historique n'est créé. Les groupes natifs et leurs dépendances sont rendus locaux pour conserver la portabilité du fichier.

Les objets restent enfants du corps. Les clés de forme du corps ne sont pas réécrites. Le mode normal **Suivre le corps** est distinct du mode **XPBD expérimental**, qui simule les guides avant interpolation. Sous-pas, itérations, souplesse, souplesse des racines et collision de surface sont accessibles. Revenir à la première image après une modification ; les caches et bakes restent gérés par Blender.

La nature de fibre utilise une courbure et une torsion intrinsèques au repos, indépendantes du diamètre et de la couleur. Les préréglages sont des choix artistiques et ne classent pas des populations. Les paramètres natifs de souplesse ne sont pas des modules de Young. Voir `Recherche-scientifique-cheveux.md` pour le contexte et les sources.

## Vérifications et limites

- `tools/validate_groom25.py` : onze zones, 66 cas d'attache sur six combinaisons de morphologie, âge et corpulence ; corps préservé, guides éditables, reconstruction sans doublon, entrées invalides refusées.
- `tools/validate_groom_workflow25.py` : matière sans perte de sculpture, export/import JSON, deux personnages indépendants, transformations du parent et simulation native XPBD.
- `tools/validate_groom_reopen25.py` : réouverture, dépendances locales et stabilité des réglages.
- `tools/render_groom25.py` : scène complète et rendus comparatifs.

Les résultats sont produits dans `validation/groom-25/`, hors Git. Les premiers 66 cas mesurent environ **2,65 mm** d'écart maximal d'attache de cage, sur la zone pubienne. Ce contrôle ne certifie pas l'absence de pénétration de tous les segments ou de toutes les mèches interpolées. Les masques et les coiffures procédurales sont des points de départ artistiques à affiner.

Le banc XPBD teste 20 guides droits de 6 cm pendant 16 images, avec gravité et sans collision, avec un allongement maximal inférieur à 0,1 %. Il ne valide ni un matériau biologique, ni les cheveux longs, ni les boucles serrées, ni les collisions complexes. Ces usages restent expérimentaux et doivent être contrôlés dans la scène de destination. Les combinaisons de densité et de détail trop coûteuses sont refusées avant reconstruction.

## Reproduction

Depuis la racine du dépôt, dans un processus isolé :

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --factory-startup --offline-mode --threads 4 --python-exit-code 1 --python tools/validate_groom25.py
```

Utiliser la même commande pour les autres scripts. Les constructeurs recréent leur scène ; ne pas les exécuter dans une scène utilisateur à conserver. Les anciens prototypes `hair_prototype20.py`, `hair_nature21.py` et `hair_physics22.py` restent disponibles comme historique, sans remplacer les contrôles de l'intégration 0.15.
