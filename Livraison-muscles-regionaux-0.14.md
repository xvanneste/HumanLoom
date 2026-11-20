# Muscles régionaux · version 0.14.0

Livraison du 19 novembre 2026 pour Blender 5.2 uniquement (minimum 5.2.0, maximum exclu 5.3.0). Le schéma des personnages passe à 9. Installation et rechargement dans la session Blender 5.2.0 LTS vérifiés ; les deux personnages existants ont été migrés avec leurs réglages conservés. Code source : `extension/`. Outils reproductibles : `tools/`.

## Comportement livré

Le pôle musculaire adulte est reconstruit par régions : épaules, bras, avant-bras, poitrine, dos, bassin/fessiers, cuisses et mollets. Les volumes se raccordent progressivement aux articulations. La commande globale et les huit commandes régionales utilisent le même calcul, avec saturation pour éviter de cumuler deux fois un muscle au maximum. Les 48 paramètres existants et les huit silhouettes restent disponibles.

Le neutre adulte du candidat 15 est conservé exactement au niveau de la cage. Les formes des étapes 5, 15 et 75 ans conservent le comportement publié en 0.13 ; la nouvelle construction musculaire atteint son plein effet à 30 ans, avec interpolation entre les étapes voisines. Cela ne constitue pas une nouvelle calibration de la musculature des enfants ou des personnes âgées.

Une zone de raccord sous les aisselles évite les croisements apparus dans le premier essai associant forte corpulence et muscles. La migration met aussi à jour les drivers existants : ajouter seulement les nouvelles clés laisserait les anciennes déformations se cumuler. Les drivers concernés sont sauvegardés avant remplacement et restaurés en cas d'échec.

## Références et limites

Le modèle masculin fourni guide la répartition visuelle des volumes. Ses sommets ne sont pas transférés dans l'extension et ses proportions stylisées ne remplacent pas notre corps neutre. Les autres modèles ajoutés restent des comparateurs indépendants, avec leurs propres conditions de réutilisation.

L'organisation régionale s'appuie sur OpenStax : [muscles du membre supérieur](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-5-muscles-of-the-pectoral-girdle-and-upper-limbs) et [muscles du membre inférieur](https://openstax.org/books/anatomy-and-physiology-2e/pages/11-6-appendicular-muscles-of-the-pelvic-girdle-and-lower-limbs). Les amplitudes de nos curseurs sont des choix artistiques, pas des coefficients de masse musculaire mesurés dans ces sources.

Les contrôles géométriques ne prouvent pas une anatomie parfaite. Les reliefs, notamment aux épaules et au haut du dos au maximum, restent à apprécier visuellement. La diversité des répartitions de graisse, la saillie des os en minceur et la calibration musculaire par âge restent à affiner. Rig, cheveux et vêtements restent hors de cette livraison.

## Validation

Rapports dans `validation/muscles-regionaux-18/`, obtenus avec Blender 5.2.0 LTS, build `fbe6228777e7`.

| Contrôle | Cas | Rapport |
| --- | ---: | --- |
| Muscle global et corpulence, trois morphologies | 27 | `croisements-04.json` |
| Huit régions aux deux extrêmes, trois morphologies | 48 | `regions-04.json` |
| Transitions d'âge avec relief cutané actif | 24 | `transitions-relief-final.json` |
| Huit silhouettes, trois morphologies | 24 | `profils-final.json` |
| Neutres et compatibilité des autres étapes d'âge | 57 | `compatibilite-04.json` |
| Migration comparée à une création neuve | 18 | `migration-0.14.json` |
| Réouverture de la session et des comparatifs | 3 fichiers | `reouverture-livraison.json` |

Les 123 cas géométriques passent le contrôle des croisements transversaux corps/corps et corps/yeux à subdivision 2. Le détecteur exclut les triangles voisins et les contacts coplanaires ; il ne garantit pas la détection de toutes les enveloppes imbriquées. Les contrôles de compatibilité et de migration sont distincts de ces 123 cas. La migration vérifie aussi les 48 réglages et la validité des drivers après réouverture.

## Fichiers livrés

- `validation/muscles-regionaux-18/Session-modelisation-14.blend` : session courante mise à jour, affichage 3D enregistré.
- `validation/muscles-regionaux-18/Session-avant-0.14.blend` : copie avant migration. Le fichier de session 0.13 reste conservé.
- `validation/muscles-regionaux-18/extension-installee-avant-0.14/` : sauvegarde de l'extension précédente.
- `validation/muscles-regionaux-18/human_modeling-0.14.0.zip` : extension installable, manifest et asset vérifiés contre les sources.
- `validation/muscles-regionaux-18/session-installee-0.14.json` : version et chemin réels de l'installation, deux objets migrés.
- `validation/muscles-regionaux-18/apercus/` : face, dos, profil et trois-quarts, neutre à gauche et muscles à droite. Les deux fichiers `*-inspection.blend` gardent les personnages éditables.

SHA-256 de `extension/data/realistic.blend`, identique dans le ZIP et l'installation : `0EB9600A06F46D43F17BA5579AFDC6614DBE82C450E069BFF0F4FE87D33E3413`.
