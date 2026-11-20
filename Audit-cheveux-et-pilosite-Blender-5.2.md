# Cheveux et pilosité dans Blender 5.2

20 novembre 2026. Étude technique pour Human Modeling 0.14, sans modification de l'extension installée ni de la scène de travail. Le futur système couvre cheveux, sourcils, moustache, barbe et poils du corps. Il utilise des objets Hair Curves et les assets Geometry Nodes natifs de Blender 5.2. Les particules historiques ne sont pas retenues.

## Résultat de la comparaison

Les archives examinées sont celles de l'audit initial : `G:/_dev/BlenderDev/CharMorph-downloader.zip` et `mpfb2-master.zip`. Leurs empreintes et les textes sources examinés sont consignés dans `validation/pilosite-19/sources-cheveux.json`. Les chemins et lignes ci-dessous désignent ces archives locales ; ils ne supposent pas que la branche Internet actuelle soit identique.

**CharMorph utilise les particules historiques. MPFB contient deux voies : les accessoires de bibliothèque MakeHuman et un éditeur Hair Curves plus récent.** Il serait donc incorrect de classer tout MPFB dans l'ancien système.

| Sujet | CharMorph fourni | MPFB fourni | Choix pour notre plugin |
| --- | --- | --- | --- |
| Représentation | Systèmes de particules, mèches en `hair_keys`, données de refit NPZ | Accessoires de bibliothèque et éditeur avec objets `CURVES` et modificateurs Geometry Nodes | Hair Curves éditables ; aucun système de particules créé |
| Implantation | Cuir chevelu séparé extrait de groupes de sommets, ou émission sur le personnage | Attache des courbes à la base, parentage ; catalogues par catégories | Régions explicites, masques peignables et attache versionnée à notre surface |
| Réglages | Coiffure, couleur, refit, options de cuir chevelu et shrinkwrap | Longueur, densité, épaisseur, frizz, clump, noise, curl, couleurs de racine ; contrôles analogues pour la pilosité | Paramètres communs avec plages propres à chaque région et unités explicites |
| Pilosité | Mécanisme générique de styles de particules | Catalogues sourcils, barbe/moustache et quinze entrées de pilosité/fourrure | Séparer les besoins humains des styles de fourrure ; permettre des combinaisons régionales |
| Adaptation | Recalcul des mèches ; le refit avertit qu'il perd le coiffage manuel | Réassignation de la surface de l'asset, hypothèse de base compatible | Préserver les guides sculptés ; diagnostiquer UV, surface et version avant adaptation |
| Export | À vérifier pour les styles effectivement disponibles | Outils de hair cards, bake et surcouche corporelle | Conserver les courbes natives ; dérivés d'export sur copie dans une phase ultérieure |

Les listes MPFB contiennent notamment deux sourcils, quatre entrées barbe/moustache, puis bras, avant-bras, torse, dos, ventre et jambes. Les quinze entrées incluent aussi des styles de fourrure comme une crinière : elles ne sont pas quinze modèles de pilosité humaine validés. Aucun `hair.blend` ou `fur.blend` n'est inclus dans l'archive fournie. Les opérateurs et listes sont lisibles, mais le rendu et la déformation de ces packs externes n'ont pas été testés dans cette étude.

## Défauts et risques identifiés

| Niveau de preuve | Constat | Conséquence pour notre conception |
| --- | --- | --- |
| CharMorph, lecture du code | `hair.py:135–141` crée `PARTICLE_SYSTEM` et des enfants interpolés ; `lib/hair.py` manipule `hair_keys` | Reprendre les besoins de bibliothèque et d'adaptation, pas ce moteur |
| CharMorph, défaut reproduit sur fonction isolée | `lib/hair.py:82–97` ignore une mèche incompatible sans avancer l'index des données et retourne `True`. Avec une première mèche incompatible, la deuxième reçoit les positions de la première | Valider toute la structure avant mutation ; refuser un état incohérent sans succès trompeur |
| CharMorph, limite annoncée dans le code | `hair.py:182` indique que le refit supprime le coiffage manuel et ne supporte pas l'ajout/retrait de particules | Séparer les guides de style et leur évaluation ; un morph ne réinitialise pas la sculpture |
| CharMorph, lecture du code | `hair.py:38–58` efface le graphe matériau lors de la recoloration et affecte des entrées par indices | Un changement de couleur agit sur notre matériau géré ; aucun effacement d'un matériau utilisateur |
| MPFB, lecture du code | `haireditorservices.py:113–124` déduit la vétusté du pack de la taille de `hair.blend` | Manifeste explicite avec schéma, identifiant et version de chaque asset |
| MPFB, lecture du code | `haireditorservices.py:224–263` réassigne `surface` sans vérifier dans cette fonction la compatibilité des UV ou des coordonnées d'attache | Vérifier l'UV d'attache et les racines avant publication. Ce constat n'établit pas à lui seul un échec sur les packs MPFB compatibles |
| MPFB, lecture du code | `apply_hair_operator.py:53–92` prépare le personnage avant de vérifier le chargement de l'asset ; un échec peut laisser cette préparation | Prévalidation des dépendances puis création transactionnelle dans une collection temporaire |
| MPFB, lecture du code | `hairproperties.py:22–73` dépend de noms précis de modificateurs et d'identifiants de sockets de ses assets | Interface propre versionnée et adaptateur contrôlé vers chaque asset natif 5.2 ; ne pas recopier ses identifiants |

La reproduction CharMorph utilise la fonction originale extraite par AST, avec des substituts contrôlés de particules. Elle démontre le défaut d'indexation et le retour de succès dans ce cas ; elle ne remplace pas un essai complet sur un personnage. Script : `tools/reproduce_hair_refit19.py`. Preuve : `validation/pilosite-19/charmorph-refit-reproduction.json`.

## Capacités vérifiées dans le Blender installé

Sonde en arrière-plan, hors ligne, profil temporaire, Blender **5.2.0 LTS**, build `fbe6228777e7`. Aucune activation de l'un des plugins étudiés et aucune sauvegarde de la scène utilisateur.

- `procedural_hair_node_assets.blend` contient Generate Hair Curves, Interpolate Hair Curves, Trim Hair Curves, Set Hair Curve Profile, Clump, Curl, Frizz et Hair Curves Noise.
- `geometry_nodes_dynamics_assets.blend` contient Hair Dynamics et Collider ; le nœud intégré `GeometryNodeXPBDSolver` est instanciable.
- **Capture Rest Geometry est un groupe asset dans `geometry_nodes_essentials.blend`**, pas un type intégré nommé `GeometryNodeCaptureRestGeometry`. Cette distinction est vérifiée par la sonde.
- L'opérateur natif `object.curves_empty_hair_add()` fonctionne sur une copie en mémoire de notre base : objet `CURVES`, bonne référence `surface`, `surface_uv_map = UVMap`, activation de l'attribut de repos et ajout de Capture Rest Geometry sur le corps, Hair Dynamics sur les courbes.
- Notre asset de corps possède une UV `UVMap`. Il ne contient pas encore de données de pilosité ; la présence de cette UV ne garantit pas son aptitude à toutes les attaches.

Preuve complète, interfaces de sockets et piles natives : `validation/pilosite-19/blender52-capacites.json`. Rejeu : `tools/probe_hair52_19.py` avec Blender 5.2, `--background --factory-startup --offline-mode --python-exit-code 1 --python` et un profil temporaire.

Les [notes de version Blender 5.2](https://developer.blender.org/docs/release_notes/5.2/physics/) confirment le nouveau montage Hair Dynamics / Capture Rest Geometry et son caractère expérimental. Le [manuel Hair Dynamics 5.2](https://docs.blender.org/manual/id/5.2/modeling/geometry_nodes/simulation/hair_dynamics.html) distingue le suivi Animation et la simulation Physics fondée sur XPBD. La présence des assets est vérifiée ici ; aucune stabilité de simulation en production n'est encore revendiquée.

## Architecture retenue pour le prototype

### Surfaces et racines

Commencer par l'attache directe à notre corps de topologie stable. Garder une variante avec surface dédiée dérivée du corps pour comparer les erreurs d'attache et les coûts. Une simple copie figée du cuir chevelu ne suit pas les morphs ; sa correspondance au corps doit être explicite si cette variante est retenue.

Chaque région possède un identifiant stable, des masques de densité, de longueur et d'exclusion, ainsi qu'un champ de direction. Les guides sont stockés au repos et restent éditables en Curves Sculpt. Une graine par région et des identifiants persistants de racines doivent préserver le coiffage lors d'un recalcul. Un changement de densité ou de niveau d'aperçu ne doit pas redistribuer les mèches conservées : ce sera un critère mesuré, pas une propriété supposée du seul curseur Seed.

Vérifier les UV superposées, les coutures, les déformations de subdivision et l'écart à la peau évaluée, notamment après le relief de peau. Une UV dédiée à l'attache pourra être ajoutée si nécessaire sans remplacer l'UV des matériaux. Le [nœud Deform Curves on Surface](https://docs.blender.org/manual/fi/5.2/modeling/geometry_nodes/curve/operations/deform_curves_on_surface.html) exige des coordonnées de racine et des données de repos cohérentes ; son manuel signale aussi l'effet du lissage des UV après subdivision. Ce nœud est un outil de comparaison, pas une seconde déformation à cumuler automatiquement avec Hair Dynamics.

### Évaluation des courbes

Montage initial à vérifier : surface et repos préparés → guides coiffés au repos → génération/interpolation au repos → Hair Dynamics en mode Animation → profil/rayon et matériau. Il reprend le suivi natif 5.2. Aucun Deform Curves on Surface supplémentaire n'est ajouté par défaut.

Le mode Physics remplace ensuite le suivi Animation pour les zones choisies. Le premier essai garde un nombre réduit de courbes pour isoler les contraintes et collisions. L'optimisation vers une simulation des seuls guides, puis une densification des courbes déformées, demande un essai distinct : l'ordre des nœuds et leur état de repos ne peuvent pas être inversés sans contrôle.

Les sourcils gauche/droit et les parties de la moustache ne doivent pas partager les guides voisins par simple proximité. La raie des cheveux doit aussi séparer les directions. [Interpolate Hair Curves](https://docs.blender.org/manual/id/5.2/modeling/geometry_nodes/hair/generation/interpolate_hair_curves.html) sait séparer les îlots de maillage, mais deux zones d'une même surface continue ne deviennent pas automatiquement deux îlots. Employer des objets de guides/régions séparés ou une partition explicite.

### Paramètres et interface

Ajouter un bloc Pilosité au panneau existant, sans ouvrir la boîte de création d'humain. Catégories : Cheveux, Sourcils, Moustache, Barbe, Corps. Réglages simples visibles en premier ; guides, masques et dynamique dans les options avancées.

| Zone | Paramètres propres, en plus de longueur, densité, rayon, couleur et variation |
| --- | --- |
| Cheveux | Ligne d'implantation, tempes/nuque, raie, direction, volume, regroupement, boucles, frisottis |
| Sourcils | Forme de l'arc, tête/corps/queue, épaisseur de la bande, orientation ; symétrie liée ou côtés indépendants |
| Moustache | Largeur, hauteur, séparation centrale, couverture, direction des deux côtés, exclusion du bord des lèvres |
| Barbe | Favoris, joues, menton, mâchoire, cou ; densités distinctes et raccord moustache/barbe |
| Corps | Torse, ventre, dos, bras/avant-bras, mains, cuisses/jambes, pieds, aisselles et pubis ; masques d'exclusion et orientation par zone |

Prévoir du duvet distinct des poils terminaux et une variation du rayon racine/pointe. La densité par surface doit conserver une signification lors du changement d'échelle. Les limites et presets seront artistiques tant que leurs plages biologiques ne sont pas documentées. Les styles restent indépendants du mélange de morphologie ; les âges 5/15/30/75 pourront proposer des presets, sans imposer une pilosité ou une calvitie à tous les personnages du même âge. Le grisonnement et la ligne d'implantation restent éditables.

La physique est désactivée par défaut sur les sourcils et poils courts. Elle devient optionnelle pour cheveux et barbes longues. Un aspect immobile utilise le suivi de surface natif, sans lancer inutilement XPBD.

### Données, matériaux et performances

Les paramètres de pilosité sont versionnés séparément des 48 contrôles corporels. Référencer les objets par pointeurs et identifiants, sans extraire l'identité depuis un nom d'objet. Stocker surface/version/UV, style/version, guides, masques, graine, réglages et provenance. Copier les datablocks éditables lors d'une duplication indépendante ; partager uniquement les ressources explicitement immuables.

Créer un petit adaptateur vers les assets Blender 5.2. Il vérifie présence, type, direction et identifiant des sockets attendus. Plusieurs sockets peuvent avoir le même libellé : Hair Dynamics possède par exemple deux entrées Gravity, de types différents. L'interface de notre plugin ne dépend pas d'un index de socket arbitraire.

Cycles utilise Principled Hair BSDF. Prévoir un matériau d'aperçu EEVEE adapté et le comparer sous le même éclairage : le [manuel du Principled Hair BSDF](https://docs.blender.org/manual/id/5.2/render/shader_nodes/shader/hair_principled.html) l'indique comme spécifique à Cycles. L'identité de rendu entre moteurs ne doit pas être promise.

Budget séparé aperçu/rendu, nombre de guides réduit, points par mèche adaptés à la longueur. Réserver la simulation aux zones sélectionnées. Une modification du corps, des guides ou des paramètres de physique doit invalider explicitement le cache concerné. Le futur rig devra déformer la surface avant le suivi des courbes ; les tests de poses et d'expressions viendront avec lui.

## Plan de réalisation et critères de passage

Premier prototype commencé le 20 novembre : [scène et bilan des cheveux courts](validation/cheveux-20/README.md). Les guides, l'interpolation native et le suivi Hair Dynamics Animation sont développés dans une scène séparée. Les essais couvrent 36 cas de guides et 12 cas de densification. La ligne d'implantation, les contrôles complets de collisions, les autres régions de pilosité et le mode Physics restent à développer. La 0.14 installée n'est pas remplacée.

| Étape | Livrable | Vérification avant de continuer |
| --- | --- | --- |
| 1. Attache et cycle de vie | Scène isolée avec cheveux courts, deux sourcils et trois régions de poils sur notre base | Morphologies 0/0,5/1, âges 5/15/30/75, contrôles de tête/visage et corpulence. Mesurer distance des racines à la peau, direction, exclusions et conservation des guides. Tester subdivisions 0/1/2 |
| 2. Styles et zones | Raie, moustache/barbe, poils corporels dirigés, masques peignables | Pas d'interpolation entre zones opposées, pas de mèches dans les lèvres/yeux ou zones exclues ; inspection rapprochée et corps entier |
| 3. Gestion dans le plugin | Panneau existant, presets, duplication, remplacement/suppression propre | Deux personnages indépendants ; annulation ; échec d'asset sans mutation partielle ; sauvegarde/réouverture et ressources embarquées |
| 4. Rendu et charge | Matériaux Cycles/EEVEE, qualité aperçu/rendu | Mesures de temps et mémoire sur la machine locale, contrôle du changement de densité sans déplacement des racines conservées |
| 5. Dynamique 5.2 | Cheveux longs et barbe longue, Animation puis Physics | Déplacement de surface, espace de simulation, collisions tête/épaules/torse, reset, cache, réouverture. Vérifier les pénétrations visuellement et l'erreur résiduelle XPBD |
| 6. Intégration au futur rig/export | Tests d'expressions et poses, dérivés selon moteur cible | Mâchoire et sourcils suivent sans double transformation. Valider l'export par réimportation ; aucune promesse de courbes natives via FBX/glTF |

Le premier lot de développement peut commencer par l'attache et les zones sans attendre le rig. Le rendu final et la dynamique demandent leurs propres scènes de validation. Les nouveautés XPBD sont utilisées via les assets de Blender, sans réimplémentation de solveur.
