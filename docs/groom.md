# HumanLoom 0.15 - Cheveux et pilosité

Le groom est intégré à l'extension, exclusivement dans Blender 5.2. Le code de production est dans `extension/groom.py` et `extension/groom_fibers.py`. Il ne dépend pas des scripts de prototype ni des fichiers de validation.

## Utilisation

Sélectionner un corps HumanLoom, puis ouvrir **Humain > HumanLoom · Cheveux et pilosité**. Onze zones indépendantes sont disponibles : cheveux, sourcils, barbe, moustache, torse, abdomen, dos, bras, jambes, aisselles et pubis.

Les boutons Court, Long, Bouclé, Crépu et Barbe courte ajoutent des points de départ procéduraux. **Pilosité adulte** ajoute les neuf zones communes ; aisselles et pubis sont des ajouts explicites. Ces boutons préservent les couches déjà présentes. Pour changer une coiffure existante, modifier ses réglages et reconstruire ses guides. La présence des couches n'est déduite ni du sexe, ni de l'âge, ni d'une origine du personnage.

Chaque zone possède longueur de contour, nature de fibre, variation de longueur, irrégularité, direction, nombre de guides, densité par m², quantité d'aperçu, rayon, graine, couleur, proportion de fibres grises et rugosité.

**Appliquer matière / densité / dynamique** conserve les guides sculptés. Les changements de longueur, nature, direction, graine ou nombre de guides nécessitent **Reconstruire les guides** : cette opération remplace la sculpture de la zone et peut être annulée dans Blender.

**Sélectionner les guides** permet ensuite d'utiliser Curves Sculpt. **Peindre la densité** sélectionne le groupe de poids correspondant sur le corps et entre en Weight Paint. Revenir en Object Mode après peinture. La reconstruction conserve ce masque et rééchantillonne les guides dedans. Un masque entièrement vide provoque un message et conserve le groom précédent.

Le JSON transfère les **réglages procéduraux**, sans les positions sculptées ni les poids peints. Enregistrer le `.blend` pour conserver le groom complet. L'import refuse de remplacer une couche existante ; la supprimer explicitement ou utiliser un autre personnage. Les matériaux sont indépendants entre personnages.

## Blender 5.2 natif

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
