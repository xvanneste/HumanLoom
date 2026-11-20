# Audit des générateurs humains Blender

18 novembre 2026

## Périmètre et résultats

Les sources examinées proviennent de `G:/_dev/BlenderDev/CharMorph-downloader.zip` (version déclarée 0.4.0) et de `G:/_dev/BlenderDev/mpfb2-master.zip` (manifeste 2.0.18). Les essais ont tourné en arrière-plan et hors ligne dans des profils Blender temporaires. Les archives d’origine ont servi de référence.

Les skills internes BCMA Python Blender et Blender Character Workflow sont en cours de validation. Ils ont servi de guides de travail provisoires. Le niveau de confiance de chaque constat vient de sa preuve propre, issue des essais Blender, du code des archives ou d’une hypothèse signalée comme telle. Les essais décrits ici couvrent des scénarios ciblés. La validation des skills demande de confronter leurs procédures à des cas reproductibles, y compris les échecs, et de consigner les écarts observés.

| Contrôle | MPFB | CharMorph |
| --- | --- | --- |
| Blender 4.4.3, 5.0.1 et 5.2.0 LTS | Activation sous le namespace d’extension, création de deux humains indépendants, rig standard, refit et création d’une copie d’export réussis | Activation sous le nom `CharMorph`, bibliothèque vide, import impossible sans pack de personnage |
| Géométrie nominale | 19 158 sommets, 18 486 faces, une couche UV et 11 shape keys sur l’objet de base, géométrie auxiliaire comprise. Le rig standard généré compte 137 os. | Maillage, UV, morphs et rig à mesurer sur un pack complet |
| Export | L’opérateur a créé la copie Blender. Le contrôle de réimportation FBX ou glTF reste à faire. | Finalisation et export à tester avec un personnage |

La création MPFB avec réglages par défaut a pris environ 0,3 à 0,4 seconde par appel après activation. Ce chiffre mesure un cas simple dans cet environnement. La suite de tests complète, les tests visuels, les poses extrêmes et les essais avec une garde-robe complète restent à réaliser.

Blender 5.0.1 a également installé et activé directement `mpfb2-master.zip` via la commande d’installation d’une extension depuis un fichier, dans un profil vierge distinct. Les essais fonctionnels ont utilisé la même source, placée dans le dépôt d’extensions local.

## Bugs et points faibles

| Priorité | Constat | Correction proposée |
| --- | --- | --- |
| P0 · CharMorph · reproduit | Charger le code sous son nom de dossier d’archive `CharMorph-downloader` provoque `ModuleNotFoundError: No module named 'CharMorph'`. `lib/drivers.py:4` importe le logger via un chemin absolu. Le chargement sous `CharMorph` passe. | Utiliser un import relatif et tester l’activation depuis le paquet distribué dans un profil Blender vierge. |
| P0 · CharMorph · confirmé | L’archive contient `data/lists.json` et aucun dossier `data/characters`. Le rechargement renvoie `FINISHED` alors que la bibliothèque est vide. L’import signale ensuite « Please select base model ». Repères dans `lib/charlib.py:498` et `library.py:32,77–86`. | Fournir une base installable hors ligne. Signaler l’absence du pack dès le chargement et désactiver l’import tant qu’aucune base valide n’est disponible. |
| P1 · CharMorph · lecture du code | Échap retire la minuterie et l’affichage, tandis que le fil de téléchargement peut continuer à écrire et marquer le personnage comme installé. Les requêtes n’ont pas de délai d’attente explicite, le ZIP est conservé en mémoire, puis extrait directement dans la bibliothèque. La branche d’erreur du modal termine avec `FINISHED`. Repères dans `prefs.py:419–455,468–544`. | Télécharger vers un fichier temporaire, vérifier le pack, interrompre le travail sur annulation et publier le pack seulement après extraction et validation complètes. Signaler distinctement succès, échec et annulation. |
| P1 · CharMorph · lecture du code | La finalisation applique les morphs et peut importer des expressions avant de tenter le rig. Une exception de rig peut conduire à `CANCELLED` après des mutations. Une erreur renvoyée sous forme de texte peut laisser la finalisation poursuivre. Repères dans `finalize.py:382–410`. | Vérifier les dépendances et préparer la finalisation sur une copie. Conserver l’original si un stade échoue. |
| P1 · CharMorph · risque à reproduire | Le repli de finalisation crée une shape key avec `from_mix=True`. Si des clés hors morphologie sont actives, ce mélange peut incorporer une expression ou un correctif dans le résultat. Un commentaire source identifie cette limite. Repère dans `finalize.py:81–94`. | Tester un sourire actif pendant la finalisation et vérifier séparément le visage neutre, l’expression et les drivers. |
| P1 · MPFB · reproduit | Un préréglage fourni avec le dépôt, modifié pour demander un vêtement absent, renvoie `FINISHED` et affiche « Human created ». Le journal indique l’absence du vêtement ainsi que d’autres ressources manquantes dans le profil vierge. Repères dans `services/humanservice.py:695–779,928–941` et `ui/new_human/newhuman/operators/humanfrompresets.py:114`. | Vérifier les dépendances avant la création et afficher leur liste dans Blender. Si une création partielle est permise, indiquer explicitement les éléments omis. |
| P1 · MPFB · lecture du code | Le refit ajuste les accessoires avant de vérifier que le rig généré possède encore son méta-rig. Si le méta-rig manque, le service signale l’erreur puis rend la main. L’opérateur annonce ensuite « Assets have been refitted » et renvoie `FINISHED`. Repères dans `services/humanservice.py:1778–1794` et `ui/model/operators/refithuman.py:26–29`. | Vérifier le rig avant de modifier les accessoires et renvoyer un résultat qui distingue refit complet et état partiel. |
| P2 · MPFB · reproduit | Un JSON syntaxiquement valide dépourvu de `phenotype` déclenche une `KeyError` et produit une erreur générique. Repère dans `services/humanservice.py:1170`. | Valider le schéma en amont, afficher le champ ou la version en cause et migrer les formats pris en charge. |
| P2 · MPFB · lecture du code | Le script `test/test_headless.py:9–13` imprime le code d’échec de pytest sans le propager au processus. Un appelant qui ne lit que le code de sortie peut manquer un échec. | Propager le résultat au processus et vérifier le comportement avec un test volontairement en échec. |

## Ce que le troisième add-on peut reprendre

| Domaine | Apport de MPFB | Apport de CharMorph | Choix proposé |
| --- | --- | --- | --- |
| Création | Base fournie, création hors ligne, préréglages JSON, import MHM et variation par graine | Bibliothèque de bases et préréglages de morphs associés | Démarrer avec une base humaine incluse et un format de préréglage versionné, puis ouvrir les adaptateurs vers d’autres bases. Associer la graine aux versions des données pour pouvoir reproduire le résultat. |
| Corps et visage | Morphs MakeHuman, paramètres globaux et shape keys Blender | Moteurs NumPy et shape keys, couches de morphs, topologies alternatives | Garder une topologie de référence stable, ses UV, ses repères et ses poids. Ajouter une correspondance explicite pour chaque topologie importée. |
| Vêtements | Bibliothèque MakeHuman, format MHCLO, outils de création d’assets, refit manuel et option de refit au changement | Ajustement des éléments dans la boucle de morphing, masques combinés et transfert de poids | Prévisualiser l’ajustement pendant le réglage et exécuter un recalcul complet à la fin de l’interaction. Conserver le corps éditable sous les vêtements. |
| Animation | Rigs standards, chemin Rigify et copie d’export | Finalisation, expressions, transfert de drivers et articulations glissantes | Préserver le personnage source et produire une copie animable ou exportable. Valider la position des os, les poids, les expressions et le retarget sur cette copie. |
| Matériaux | Modèles de peau, d’yeux et matériaux d’assets | Couleurs directes et matériau de peau avec déplacement | Préparer une peau rendable dans Blender et une variante exportable, avec des textures et un jeu d’UV identifiés par base. |

**Ordre proposé.** Valider d’abord une base humaine complète, avec mains, pieds, yeux, bouche et maillage continu. Ajouter ensuite les morphs corporels et faciaux, le rig et un vêtement de référence. Éprouver cette chaîne sur trois morphologies en vues face, profil et trois-quarts, puis contrôler épaules, coudes, hanches, genoux, doigts et visage en pose. Enfin, sauvegarder, rouvrir le fichier et réimporter un export pour vérifier les dimensions, les UV, les poids, les textures et les expressions. La réussite de cette chaîne permet d’évaluer l’intérêt d’une seconde topologie sur des mesures comparables.

La reprise directe de fichiers dépend de leur provenance. Les notices des deux archives décrivent le code sous GPL. MPFB documente séparément ses assets dans `LICENSE.ASSETS.md`. CharMorph annonce des licences par personnage dans `data/lists.json` et décrit les bases MB-Lab sous AGPL dans `license.txt`. Vérifier les notices des fichiers réellement choisis avant de décider d’un modèle de distribution.

## Vérifications à poursuivre

Complément du 20 novembre 2026 : l'[audit cheveux et pilosité](Audit-cheveux-et-pilosite-Blender-5.2.md) distingue les particules historiques de CharMorph de l'éditeur Hair Curves récent inclus dans les sources MPFB fournies. Les packs `hair.blend` et `fur.blend` ne sont pas présents dans l'archive MPFB : les listes et opérateurs ont été analysés, leurs résultats visuels ne sont pas déclarés validés. Notre architecture retient les assets natifs Blender 5.2, sans réutiliser le moteur de particules.

- Installer un pack CharMorph complet et auditer le changement de morphologie, l’habillage, la finalisation, la conservation des expressions et les performances en charge. La recette officielle décrit une installation distincte des personnages. [Documentation CharMorph](https://github.com/Upliner/CharMorph/blob/master/README.md)
- Évaluer les mêmes poses et vêtements sur des morphologies comparables et mesurer la déformation. Les essais nominaux actuels permettent de confirmer les opérations MPFB et l’activation de CharMorph.
- Utiliser un paquet d’extension reproductible pour les essais d’installation. Blender 5.0.1 a construit `mpfb-2.0.18.zip` depuis `src/mpfb` et validé son manifeste. [Manuel Blender sur la création d’extensions](https://docs.blender.org/manual/en/4.2/advanced/extensions/getting_started.html)
