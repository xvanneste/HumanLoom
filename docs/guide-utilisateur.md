# HumanLoom — guide de démarrage (animation)

Ce guide couvre, dans l'ordre : installer l'extension, créer un humain, poser le squelette, choisir et appairer une armature source, parcourir la galerie, appliquer une animation. HumanLoom est une extension **Blender 5.2** ; il ne fournit **aucune animation** : vous utilisez les vôtres (voir `animations-import.md` pour les obtenir et les importer, et l'avertissement de licence).

## 1. Installer
1. Construire le paquet : `blender --command extension build` dans le dossier `extension/`, ou utiliser le zip fourni.
2. Blender → Préférences → Extensions → « Installer depuis le disque » → choisir le zip, puis activer HumanLoom.
3. Dans les préférences de l'extension, **Dossier de bibliothèque** = le dossier de VOS animations (il contient `inventory.json`, et au besoin le fichier `.blend` des actions) ; **Dossier de cache** facultatif (vide = dossier utilisateur de l'extension). Rien n'est lu ni écrit ailleurs ; vos fichiers sources ne sont jamais modifiés.

## 2. Créer un humain et poser le squelette
- **Ajouter ▸ Maillage ▸ Humain** (ou le bouton du panneau Humain). Réglez la morphologie dans la barre latérale (touche N, onglet Humain).
- Panneau **Squelette du corps** → **Appliquer le squelette** : choisir les poids de peau, **stockés** (instantané, reproductible) ou **recalculés** sur la morphologie actuelle (quelques secondes ; peut échouer sur une morphologie dont la cage se recoupe, un message l'indique et rien n'est créé).
- La mâchoire est l'os `jaw` (enfant de `head`) : les lèvres du bas, le menton et le plancher de la bouche la suivent ; la bouche s'ouvre en tournant `jaw` autour de l'axe X (20° ≈ 3 cm de fente sur nos modèles : mesure de notre modèle, pas une donnée clinique). Le squelette crée aussi dents, gencives et langue (procédurales, adaptées à l'âge et au sexe ; seules les largeurs/longueurs des incisives et canines supérieures sont des données publiées, le reste est provisoire). Elles sont mises à jour avec le squelette et retirées avec lui.
- Statuts : *Non installé*, *Installé*, *Obsolète* (la morphologie a changé : **Mettre à jour le squelette** repose les os sans toucher aux poids ni aux animations), *À configurer* (rig incomplet ou en double). **Retirer le squelette** supprime armature, groupes de poids et modificateur. Les yeux suivent l'os `head`.
- Dupliquer l'humain copie son squelette.

## 3. Choisir la source et appairer (panneau « Mapping des animations »)
1. Importez ou liez dans la scène l'**armature d'origine** des animations de votre bibliothèque (les animations sont rangées par squelette source).
2. **Source** = cette armature, puis **Appairer automatiquement** : appariement par les noms, puis la structure, puis la géométrie ; chaque os reçoit un **score** (en rouge sous 0,6 : à vérifier).
3. Corrigez à la main : pour chaque os de HumanLoom, le champ de recherche choisit l'os source ; la croix efface l'appariement. Un conflit (une même source pour deux os) est signalé et empêche l'enregistrement.
4. **Enregistrer le profil** (JSON dans le dossier utilisateur) pour le réutiliser ; **Charger un profil** (dossier de la bibliothèque) le réapplique ; un profil périmé (os renommés) est signalé.
Les os sans équivalent (torsions, os de colonne en trop…) sont listés ; ils restent sans rotation propre.

## 4. Parcourir la galerie (panneau « Bibliothèque d'animations »)
- **Actualiser la bibliothèque** lit l'index (cache, moins d'une seconde pour 2 000 animations). Recherche par préfixes de mots, filtre par catégorie, étoile = favori, **Corriger la catégorie** pour reclasser.
- Grille de vignettes paginée (12 par page). Les vignettes sont générées **hors du processus principal** : bouton **Générer les vignettes de la page** (panneau « Appliquer l'animation ») ; elles sont gardées dans le cache.
- **Importer un fichier / un dossier** : FBX, BVH, glTF, `.blend` ou le dossier d'export de l'outil `tools/unreal_export` (métadonnées lues dans `manifest.json`).

## 5. Appliquer une animation (panneau « Appliquer l'animation »)
Sélectionnez une animation dans la grille, puis réglez :
- **Pose** : *Absolu + IK des membres* (défaut : directions de la source, puis mains et pieds replacés par IK à 2 os ; meilleure fidélité mesurée), *Absolu* ou *Delta*.
- **Root motion** : *Conserver* (le déplacement reste sur le bassin), *Sur place* (déplacement horizontal retiré), *Extraire vers root* (porté par l'os `root`).
- **Vitesse**, **Début / Fin** (découpe en images), **Échelle** des translations (0 = automatique d'après les hauteurs de bassin).
Puis : **Aperçu** (non destructif ; **Fin** restaure l'état initial), **Ajouter au NLA** (nouvelle piste) ou **Remplacer** (action active). Les conversions sont mises en cache.
- **Publier les favoris dans l'Asset Browser** convertit vos animations favorites et les marque comme assets du fichier courant (glisser-déposer natif depuis « Fichier courant »).

## 6. Visage : regard, langue, poses, visèmes, ARKit, export, animation (panneaux « Squelette du corps » et « Poses du visage »)
Prérequis : squelette posé (os `jaw`, `eye.L`, `eye.R`). Tout le contenu du visage est écrit par HumanLoom (aucune donnée de visage tierce) ; les valeurs non lues dans une publication sont déclarées « non vérifié ».
- **Regard** (panneau « Squelette du corps ») : *Orienter* (horizontal, vertical, convergence en degrés), *Suivre l'objet* (sélectionnez un objet : les deux yeux le suivent, bornés à 45° / 35° — limites provisoires), *Droit*. **Paupières qui suivent le regard** pilote Clignement et Yeux grands ouverts par la rotation verticale des yeux : tant que le suivi est actif, ces deux commandes ne se règlent plus à la main.
- **Galerie** : vignettes, étoile = favori (enregistré dans la scène), **Enregistrer la pose actuelle**. Catégories : expressions (dont *sourire large* et *rire*, où les dents du bas sont visibles), visèmes (15, « non vérifié »), vos poses.
- **Mélangeur** : deux poses A et B, curseur de mélange, *Appliquer le mélange*. **Créer un clip facial** fabrique un clip A → B dans une piste NLA « Visage » séparée de l'animation du corps (on peut les couper indépendamment) ; *Retirer les clips faciaux* remet le visage au neutre.
- **Langue** : sept curseurs (pointe haut/bas, dos relevé, sortie, gauche/droite, étroite), amplitudes provisoires.
- **Export** : *Cuire les formes* crée une copie de la cage avec une forme par commande et par coefficient ARKit couvert ; *Couverture ARKit* affiche la table dans la console : sur 52 coefficients, 7 directs, 9 portés par un os, 1 par la langue, 23 approchés, 12 non couverts (liste dans le rapport). Les noms ARKit viennent de mémoire de la documentation d'Apple (non relue) et le sens gauche/droite n'est pas vérifié.
- Les amplitudes des commandes du visage sont réduites chez l'enfant (facteur 0,895 à l'âge 0, 1,0 à l'âge 2) d'après la profondeur de tête de **notre** modèle, pas d'une publication.

## 7. Limites connues (à lire)
- La fidélité de position (mains, pieds, coudes, genoux) mesurée sur 30 animations réelles est de **2,6 % de la stature en médiane** (7,5 % au 95e centile) avec le mode par défaut absolu + IK (absolu seul : 3,9 % / 7,7 % ; delta : 4,6 % / 10,0 %). Le seuil visé (95e centile ≤ 6 %) n'est **pas atteint**.
- Les animations **additives** ne sont pas prises en charge. Animation faciale : voir §6 (poses, mélange, clips NLA) ; les amplitudes du visage et la langue sont provisoires, les parois de la bouche restent presque droites.
- Un nouveau défaut est connu (I-49) : à partir de l'âge 2,5 la surface du corps peut se recouper près des yeux.
- Les vignettes sont des figures en bâtons du squelette source, pas un rendu du personnage.
- Aucune garantie de licence sur vos animations : vous êtes responsable de vos droits.
