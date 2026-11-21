# IDEES — Brainstorming : pistes d'évolution de HumanLoom

Statut : **propositions à discuter**, rien n'est décidé ni implémenté. Elles s'appuient sur l'audit (`ETAT_DES_LIEUX.md`, `ISSUES.md`, `REFERENCE_PLUGINS.md`). Les idées de l'utilisateur seront ajoutées en §11 et fusionnées avec celles-ci avant toute priorisation.

Légende : **Constat** = ce que l'audit a mesuré ; **Idée** ; **Dépend de** ; **Risques** ; **Questions**.

---

## 0. Principe directeur (idée de l'utilisateur) : une intégration native à Blender

**Objectif :** quand l'extension est active, elle doit donner l'impression d'avoir été développée par Blender : raccourcis, éditeurs existants, menus, assets, annulation, animation, unités, traduction. Réutiliser tout ce que Blender offre avant de créer une interface propre.

**Constat :** aujourd'hui, tout passe par un seul onglet de la barre latérale (touche N) ; rien dans l'éditeur de propriétés, ni dans les menus Fichier/Objet/clic droit, ni dans l'Asset Browser, ni de raccourci clavier ; l'interface est écrite en français en dur ; 462 shape keys encombrent l'onglet Données.

**Catalogue des points d'intégration (à confirmer un par un dans l'API 5.2) :**

| Où dans Blender | Mécanisme | Aujourd'hui | Proposition |
|---|---|---|---|
| **Éditeur de propriétés** (onglets Objet, Données, Modificateurs, Matériau) | `Panel` avec `bl_space_type='PROPERTIES'` et un `bl_context` | rien | panneau « Humain » dans l'onglet Objet ou Données : sexe, âge, taille, corpulence ; les réglages restent visibles comme ceux d'un modificateur |
| **Données propres typées** | `PropertyGroup` sur `Object`/`Mesh` (`bpy.props`, bornes, `update=`, défaut) au lieu de propriétés personnalisées sur le bloc de clés | propriétés `hm_*` sur le `Key` | sliders animables (touche I), pilotables par drivers, copiables (Ctrl+C/V), remise à zéro (Retour arrière), infobulles Python natives, copie du chemin de données |
| **Raccourcis** | `keyconfigs.addon` : `KeyMap` + `KeyMapItem`, modifiables dans Préférences > Keymap | aucun | raccourcis par défaut (Ctrl/Maj + lettre libre), pie menu pour âge, sexe et silhouettes, F3 (recherche d'opérateurs) |
| **Menus** | `append` aux menus existants (`VIEW3D_MT_add`, `VIEW3D_MT_object`, `VIEW3D_MT_object_context_menu`, `TOPBAR_MT_file_import/export`) | seulement Ajouter > Mesh | Ajouter > Humain (sous-menu), Objet > Humain, clic droit sur le corps, Fichier > Importer/Exporter > Préréglage HumanLoom (JSON) au lieu de boutons dans le panneau |
| **Dernière opération (F9)** | `Operator.draw`, `bl_options={'REGISTER','UNDO'}`, `invoke` | `create` sans options | options de création (sexe, âge, taille, graine, groom de départ) modifiables dans le panneau « Ajuster la dernière opération » |
| **Asset Browser** (Blender 4.x/5.x) | assets (objets, collections, matériaux, groupes de nœuds, poses) avec catalogues et vignettes | aucun | préréglages de personnages, silhouettes, visages, coiffures, matériaux de peau, poses comme assets avec vignettes et glisser-déposer ; résout « silhouettes sans aperçu » |
| **Prévisualisations dans l'interface** | `layout.template_icon_view`, `bpy.utils.previews` | boutons textuels | silhouettes et coiffures avec vignettes |
| **Mise en page standard** | `layout.use_property_split` (libellé à gauche, valeur à droite), `template_list` (liste de zones de pilosité), `prop_search` | libellés tronqués, liste déroulante | alignement Blender et liste des zones comme les groupes de sommets |
| **Opérateurs interactifs** | `modal` + `invoke` (glisser dans la vue, Maj pour le pas fin, Échap pour annuler, saisie numérique) | aucun | « Régler la taille » ou une largeur en tirant dans le viewport |
| **Gizmos** | `Gizmo`/`GizmoGroup` | aucun | poignées dans la vue (taille, carrure, hauteur de tête), comme celles de la lumière ou de la caméra |
| **Outils de la barre d'outils** | `WorkSpaceTool` | aucun | outil « Morphing » : agir sur une région du corps pointée à la souris |
| **Superpositions (overlays)** | `gpu` + `draw_handler_add` | aucun | périmètres de coupe, mesures et repères dessinés dans la vue |
| **Préférences** | `AddonPreferences` | aucune | densité par défaut, langue, unités, raccourcis |
| **Traduction** | `bpy.app.translations` | français en dur | textes sources en anglais + dictionnaire FR (et autres) : l'interface suit la langue de Blender |
| **Messages d'inactivité** | `Operator.poll_message_set` (API récente : à vérifier en 5.2) | boutons grisés sans raison | « Relief de peau : actif après 30 ans », « Intersections : réduire la subdivision » |
| **Unités** | `scene.unit_settings` | déjà respectées pour les mesures | généraliser (cm, pouces, système impérial) à tous les champs |
| **Espace de travail** | atelier (workspace) livré ou créé | aucun | atelier « Personnage » : viewport + propriétés + Asset Browser |
| **Collections et Outliner** | organisation et nommage | corps, yeux, cheveux dans des collections incohérentes (I-28) | une collection par personnage, instanciable, compatible liaison + library overrides |
| **Rig, poses, matériaux, cheveux** | Rigify, Pose Library (assets), Principled BSDF, Hair Curves et sculpt curves | cheveux déjà natifs ✅ | prolonger la logique native pour le rig (Rigify), les poses (assets) et la peau (nœuds) |
| **Animation** | clés sur les curseurs, drivers, shape keys | possible sur propriétés personnalisées | vieillissement ou perte de poids animés dans la timeline |
| **Distribution** | extensions Blender (manifeste, licence, permissions) | ✅ paquet validé | publication sur la plateforme d'extensions ; respect de ses conventions |

**Contraintes et risques :**
- Migrer les propriétés `hm_*` vers des `PropertyGroup` impose un schéma 10 et une migration testée.
- Les 462 shape keys encombrent l'onglet Données : à réduire (regrouper, ou piloter par un moteur de cibles) ou à documenter.
- Les raccourcis par défaut ne doivent pas entrer en conflit avec ceux de Blender ni d'autres extensions.
- Plusieurs API ci-dessus sont à valider en 5.2 avant d'engager le travail (prototypes jetables).

**Questions :** quel niveau d'ambition (panneau dans l'éditeur de propriétés + menus, ou aussi gizmos et outil de barre d'outils) ? L'interface en anglais d'abord, avec traduction française ?

---

## 1. Système de contrôle en couches (au lieu de 48 sliders à plat)
- **Constat :** 48 sliders sans hiérarchie, diaphonies (`shoulders` modifie taille et bassin, I-22), contrôle masqué actif, amplitudes faibles (I-13).
- **Idée :** trois niveaux.
  - *Global* : sexe, âge en années, taille, poids ou IMC.
  - *Régional* : torse, bassin, jambes, bras, tête.
  - *Fin* : visage, muscles, détails.
  Chaque niveau pilote le suivant sans le remplacer ; les valeurs fines restent éditables.
- **Pilotage par mesure :** étendre `fit_measurement` (7 mesures aujourd'hui) à tout le corps : « 85 cm de taille », « 40 cm de cuisse ». Atout face à MPFB2 et CharMorph.
- **Dépend de :** repères automatiques (§5), recalibrage (§2, §3).
- **Risques :** migration des personnages existants ; schéma 10 et script de migration testé.
- **Questions :** garder les sliders actuels en mode « avancé » ?

## 2. Corpulence repensée
- **Constat :** trois échelles incohérentes (`whole_body` +61/+35 mm au tour de taille, `adiposity` +56/+19, `body_mass` +129/+119), dépendance à l'âge incohérente (34 mm à 30 ans, 87 mm à 75 ans), rendus `rendu-corpulence-*.png` ; README : extrêmes insuffisants (I-21, I-08).
- **Idée :** un paramètre principal (IMC ou masse grasse) calibré sur NHANES/OMS déjà présents, avec une répartition régionale selon sexe et âge ; les contrôles régionaux ne servent qu'aux écarts. Retirer « Volume hérité » et `corpulence` après migration.
- **Dépend de :** §1, jeu de références de mesures par sexe/âge/IMC.
- **Risques :** calibration anthropométrique non triviale ; garder le caractère « artistique » documenté.
- **Questions :** quelle plage visée (de très maigre à IMC > 40) ?

## 3. Visage
- **Constat :** amplitudes 0,6 à 8,9 mm sur une tête de 182 × 214 mm ; dix sliders < 3 mm ; visages M/F proches ; 21 sliders en liste plate ; intérieur de bouche, dents, langue absents (I-13, I-20).
- **Idée :**
  - re-étalonner les amplitudes par région (cibles en mm ou en écarts-types) ;
  - regrouper en sous-panneaux repliables (crâne, yeux, nez, bouche, mâchoire, oreilles) ;
  - archétypes de visages mélangeables (variantes pondérées) ;
  - dents, langue, intérieur de bouche ; paupières et lacrymal propres.
- **Dépend de :** décision sur le moteur de morphs (§9).
- **Risques :** topologie du visage figée par la base ; ajouter la géométrie interne impose de changer la base ou d'ajouter des objets.

## 4. Peau et yeux (matériaux)
- **Constat :** corps et yeux sans matériau ; relief de peau quasi inactif (≤ 0,76 mm) (I-20, I-13).
- **Idée :**
  - matériau de peau procédural : mélanine, hémoglobine, sous-surface, rugosité ; réglages simples (teint, rougeur, taches) ;
  - rides et pores pilotés par l'âge ;
  - yeux : iris, sclère, pupille, humidité ;
  - compatibilité EEVEE et Cycles ; nœuds locaux comme pour les cheveux pour garder la portabilité.
- **Dépend de :** UV (1 couche `UVMap` aujourd'hui) ; décision sur les textures livrées (licences).
- **Risques :** droits des textures ; rester procédural limite ce risque.

## 5. Repères automatiques, rig et poses
- **Constat :** repères posés à la main en mode Édition ; 3 mesures sur 7 non concluantes avec mes placements ; pas de rig (I-23).
- **Idée :**
  - placement automatique des 10 repères à partir de la forme (sections, extrema, symétrie) avec contrôle de qualité ;
  - rig : Rigify (métarig ajusté sur les repères) ou armature maison ; poids calculés ; sliding joints inspirés de CharMorph ;
  - bibliothèque de poses ; export vers moteurs de jeu.
- **Dépend de :** §1 (pilotage par mesure), stabilité de la topologie.
- **Risques :** le rig doit suivre les morphs sans les réécrire ; temps de génération (Rigify lent, README CharMorph).

## 6. Cheveux et pilosité
- **Constat :** bornes float32 rejetées (variation 0,8 ; rayon) (I-19) ; premier objet hors de la collection du corps (I-28) ; XPBD très lent en lecture (I-31) ; collisions pas validées (collision29) ; messages trompeurs (I-27).
- **Idée :**
  - correctifs rapides (bornes avec tolérance, rangement des collections, messages) ;
  - performances XPBD : bornes recommandées, aperçu simplifié, bake explicite ;
  - bibliothèque de coiffures plus riche, couleurs par âge (gris), cartes (cards) pour le temps réel ;
  - répartir l'effort : le groom natif Blender 5.2 est un point fort à consolider.
- **Dépend de :** terminer `collision29`.

## 7. Interface
- **Constat :** un seul onglet, 11 sous-panneaux, sliders à moitié remplis à zéro, libellés tronqués, pas de réinitialisation par curseur, groom caché tout en bas, silhouettes sans aperçu, taille sans champ, sélecteurs de fichiers dans Documents (`UI_REVIEW.md`, I-32, I-33, I-29).
- **Idée :**
  - onglets ou panneaux frères : Corps, Visage, Âge, Cheveux, Mesures, Outils ;
  - sliders centrés, bouton de remise à zéro par réglage et par section, valeurs en cm / % / années ;
  - assistant de création guidée ; vignettes de silhouettes et de préréglages ;
  - champ de taille direct ; messages d'inactivité (« relief de peau : actif après 30 ans ») ;
  - dossier par défaut du projet et nom proposé à partir du personnage ;
  - « Dupliquer le personnage » (corps, yeux, cheveux, repères) (I-24).
- **Dépend de :** §1 pour la structure des réglages.

## 8. Qualité, tests, CI
- **Constat :** tests liés à l'extension installée (I-01), fichiers d'essai non reproductibles (I-03, I-03b), 8 scripts en échec dont plusieurs périmés (I-34), écart de forme vs 0.13 (I-30).
- **Idée :**
  - lanceur unique qui cible le dépôt ; fixtures générées par script ; résumé automatique ;
  - jeu de tests de non-régression de forme (hauteurs, largeurs, écarts vs références) ;
  - intégration continue avec Blender en ligne de commande (GitHub Actions) ;
  - tests d'interface automatisés (captures comparées) en complément.
- **Dépend de :** décision sur le sort des anciens scripts de `tools/` (archiver).

## 9. Moteur de morphs et données
- **Constat :** shape keys pilotés par 459 drivers simples ; 462 clés ; évaluation 11 ms (cage) à 42 ms (avec modificateurs) ; CharMorph utilise un cœur numpy, des morphs creux et des chargements paresseux.
- **Idée :** garder les drivers à court terme (natif, sauvegarde dans le `.blend`) ; étudier des « packs de cibles » déclaratifs (fichiers de données par région) chargés à la demande ; envisager un cœur numpy seulement si les sliders deviennent lents.
- **Dépend de :** mesures de performance dans l'interface (non faites).
- **Risques :** réécriture coûteuse pour un gain non démontré ; décider après mesure.

## 10. Organisation du dépôt et licences
- **Constat :** `codex/modelisation` = `main` ; 157 scripts dans `tools/` ; provenance de la base dans `extension/CREDITS.md` ; références GPL/AGPL/CC.
- **Idée :** fusionner `codex/groom` dans `main` après correction des tests ; archiver les prototypes anciens dans `tools/archive/` ; tag de version ; politique claire de réutilisation (code GPL oui avec crédit ; données MB-Lab AGPL non sans avis).
- **Questions :** conserver deux branches de travail (corps, cheveux) ou une seule ?

---

## 11. Idées de l'utilisateur
*(à compléter ensemble)*

| # | Idée / constat | Domaine | Lien avec les idées ci-dessus | Priorité souhaitée |
|---|---|---|---|---|
| 1 | Intégration la plus native possible : l'extension doit donner l'impression d'avoir été développée avec Blender (raccourcis, fenêtres et éditeurs existants, tout ce qui est possible) | Interface / architecture | §0, §7, §9 | à définir |
| 2 | Dossier « Human Native » rédigé avec une autre IA (humain = `MESH` natif + `PropertyGroup`, contrôleur/moteurs, Shift+A, Object Properties, bake) | Architecture / intégration | §0, §14 | à définir |
| 3 | Nœuds pour piloter l'humain (morphologie, âge, taille) afin d'animer croissance, vieillissement, longueur des cheveux — **option C choisie** (groupe de nœuds « Humain ») | Animation / nœuds | §0, §1, §15 | à définir |
|   |   |   |   |   |

## 12. Questions ouvertes pour trancher
1. **Public visé :** cinéma, jeu, impression 3D, personnages stylisés, anatomie réaliste ?
2. **Refonte ou incrémental** pour le système de contrôle (§1, §2), avec migration des anciens fichiers ?
3. L'écart de forme vs 0.13 au neutre aux âges intermédiaires est-il voulu (I-30) ?
4. Dans quel ordre : corpulence et visage (visible), repères et rig (pipeline), matériaux (rendu) ?
5. Souhaite-t-on conserver la contrainte « Blender 5.2 uniquement » (manifeste borné à 5.3.0) ?

## 13. Séquence proposée (à valider)
1. Gains rapides : I-19, I-28, I-27, tests périmés, masquage des contrôles hérités, messages d'interface.
2. Socle de test et décision I-30.
3. Corpulence et amplitudes (§1, §2, §3).
4. Matériaux (§4), puis repères automatiques et rig (§5).
5. Interface (§7) en continu ; cheveux (§6) et CI (§8) en parallèle.

---

## 15. Contrôle par nœuds et animation du personnage (idée de l'utilisateur)

**Idée :** des nœuds pour piloter l'humain (morphologie, âge, taille), afin notamment d'**animer** la croissance, le vieillissement, la longueur des cheveux, etc.

### 15.1 Ce que j'ai testé (Blender 5.2, scripts jetables, clone isolé)

| Test | Résultat |
|---|---|
| Images clés sur l'âge (stade 0 → 3) et la « corpulence globale » (−1 → +1) sur les propriétés du bloc de clés | ✅ la forme s'anime : hauteur 1,100 m (image 1), 1,377 (26), 1,690 (51), 1,679 (76), 1,670 (101) ; profondeur 0,217 → 0,388 m |
| Images clés sur l'entrée **Densité** du modificateur de cheveux (Geometry Nodes) | ✅ 0 → 4 588 → 14 682 → 29 337 mèches évaluées (chemin `modifiers["…"].properties.inputs.Socket_2.value` en 5.2) |
| Images clés sur la **longueur** des cheveux (`hl_groom.length`) | ❌ **sans effet** : la longueur moyenne des guides reste 0,0482 m ; la longueur n'est utilisée qu'à la construction des guides, et la pile de nœuds n'a aucune entrée de longueur ou de coupe |
| API 5.x d'animation | `Action` n'a plus d'attribut `fcurves` (actions par couches/slots) : tout code qui lit ou écrit des animations doit être adapté |

Autres faits utiles : l'âge n'a que quatre ancres (5, 15, 30, 75 ans) interpolées linéairement entre elles (« Transition » 0–3, sans unité) ; la stature d'âge se règle par un bouton ponctuel (`calibrate_age_height`) et non par une fonction continue de l'âge.

### 15.2 Pistes de conception (à discuter)

**A. Animer ce qui existe déjà (peu coûteux).**
- Exposer l'âge en **années** (curseur continu piloté par les ancres, ou courbe) et la stature en fonction de l'âge (courbes OMS/NHANES déjà dans le dépôt) pour que « croissance » soit une seule image clé, au lieu de bouton + échelle.
- Rendre animables les réglages utiles du groom : **longueur** (voir B), couleur et gris (`grey`), densité (✅).

**B. Cheveux : ajouter des entrées natives de longueur.**
- Ajouter à la pile de nœuds une entrée **Longueur** (rognage/prolongation des courbes, par exemple facteur de rognage 0–1, ou échelle de longueur) pour animer « la pousse » sans reconstruire les guides.
- Garder la construction des guides pour les changements structurels (nombre, direction, graine).

**C. Un groupe de nœuds de contrôle « Humain » (Geometry Nodes).**
- Groupe d'entrées : Âge, Taille, Sexe, Corpulence, Longueur de cheveux, etc., utilisable dans un modificateur ou en asset.
- **Limite connue :** Geometry Nodes ne peut pas écrire les valeurs de shape keys ; deux voies : (1) les nœuds ne portent que ce qui est géométrique (cheveux, échelle, vêtements) et les drivers relient leurs entrées aux paramètres du corps ; (2) les morphs du corps deviennent des **attributs de sommets** mélangés par nœuds (déformations en nœuds), ce qui coûte de la mémoire (462 clés × 10 582 sommets × 12 octets ≈ 58 Mo si tout est converti) et demande une réécriture. À mesurer avant de choisir.

**D. Un éditeur de nœuds propre à l'humain (type de graphe personnalisé).**
- Python permet de déclarer un `NodeTree` personnalisé avec ses propres nœuds (Âge, Taille, Temps, Courbe, Mélange, sorties vers les paramètres), comme d'autres extensions de nœuds.
- Intérêt : câblage visuel (« temps → âge → hauteur et cheveux »), courbes, bruit. Coûts : maintenance, performances, annulation, interactions avec les drivers ; à n'envisager qu'après A–C.

**E. Temps réel de la timeline.**
- Quelques cas : « accéléré » (une année par seconde), cycle de vie (NLA), variation de masse corporelle, croissance de la barbe. Garder la mention existante : les formes d'âge sont une interpolation artistique, pas une trajectoire chronologique validée.

### 15.3 Dépendances et risques
- Lié à §0 (propriétés typées sur l'objet : meilleure animation, drivers, copier-coller) et à §1 (contrôles en couches : un « âge » et une « taille » globaux).
- Les shape keys de graisse/muscle suivent des drivers non linéaires (I-18) : l'animation d'un mélange sera non linéaire.
- Les cheveux simulés (XPBD) ne se prêtent pas à la pousse animée (le cache de simulation s'invalide) ; réserver l'animation de longueur au suivi du corps.
- Compatibilité 5.x des actions à vérifier (slots).

**Questions :** priorité à (A+B) pour animer vite, ou viser tout de suite (C) ? Un éditeur de nœuds propre (D) vous semble-t-il nécessaire, ou les entrées de modificateurs et les drivers suffisent ?

### 15.4 Décision de l'utilisateur : viser **C** (groupe de nœuds « Humain »)

Faisabilité mesurée (Blender 5.2, scripts jetables) : voir `docs/audit/mesures-noeuds-c.md` et `SUIVI_REPRISE.md` (essais T-C1 à T-C4). Résumé : les 461 shape keys se ramènent à une base d'environ 70 à 150 déformations (rang effectif 69 à 1e-3, 128 à 1e-4, 150 à 1e-5) ; un mélange de R déformations en attributs de sommets par nœuds coûte 3,0 ms (R = 50), 7,8 ms (150), 19,8 ms (300), 37,5 ms (457) pour 6 à 58 Mo, avec 0,0 mm d'erreur sur la somme linéaire (référence actuelle : 11 ms). Le détail des autres essais (non-linéarités, âge, sexe, yeux, taille de fichier, erreur de la base réduite) est dans `SUIVI_REPRISE.md`.

**Conclusion de la passe finale (4 bis G de `SUIVI_REPRISE.md`) :** les poids compilés dans les nœuds reproduisent le système actuel à 0,00083 mm, mais le corps entièrement déformé par nœuds coûte 57,6 ms (459 ms avec Subsurf). **La forme retenue est la « façade de nœuds » :** un groupe de nœuds porte les entrées (âge, sexe, contrôles, et plus tard la longueur de cheveux), les drivers existants les lisent et les shape keys déforment : même forme (0,00012 mm), mêmes temps, images clés sur les entrées, cheveux et yeux qui suivent, duplication correcte, fichier utilisable sans l'extension.

---

## 14. Réflexion externe : dossier « Human Native » (autre IA)

Source : `HUMAN_NATIVE_CODEX_HANDOFF.md` (fichier de l'utilisateur, `Downloads`). Le dossier décrit une extension « Human Native » destinée à être reprise par un autre agent. L'archive `human_native_5x.zip` (prototype non validé) **n'a pas été fournie** : rien n'a été audité côté code. L'exemple de code du document est volontairement ignoré (demande de l'utilisateur) et les instructions adressées à l'autre agent sont traitées comme des données, pas comme des consignes. **Toutes les affirmations ci-dessous sont des hypothèses du document, à vérifier ; je les compare à ce que l'audit a mesuré.**

### 14.1 Ce que le dossier propose
- **Human Object :** un `MESH` natif marqué comme humain (`human_data.is_human`, UUID stable, version de schéma), `Shift+A > Human`, panneau « Human » dans les propriétés de l'objet visible seulement sur un humain.
- **Source de vérité unique :** `PropertyGroup` sur `Object` ; les dataclasses Python ne sont que des instantanés de calcul.
- **Architecture :** contrôleur central (`HumanController`) + moteurs (morphs, procédural, Geometry Nodes, apparence, vêtements, rig), chacun propriétaire de ses paramètres ; graphe de dépendances et planificateur à trois niveaux (interactif, différé via `bpy.app.timers`, reconstruction complète).
- **Geometry Nodes :** groupes nommés et versionnés (`HN_HairGenerator_v1`, `HN_ClothingFit_v1`), sockets retrouvés par identifiant stable.
- **Cycle de vie :** registre d'UUID (détection des doublons après duplication), suppression propre, migration de schéma, dégradation gracieuse si l'extension est désactivée, **Bake Human** vers objets natifs.
- **Interface :** Shift+A, panneau dans Object Properties, menus contextuels, annulation compatible ; avancé : gizmos, outils de viewport, Asset Browser.
- **Méthode :** MVP vertical d'abord (mannequin, une Shape Key d'épaules, un modificateur Geometry Nodes, un paramètre de matériau), puis architecture, puis personnage complet ; budgets indicatifs (morph interactif 16–33 ms).
- **Contrainte reconnue :** une extension Python ne peut pas créer un nouveau type d'objet au même niveau que `MESH` ; l'intégration passe par `Object` + propriétés, opérateurs, menus, panneaux, gizmos, assets.

### 14.2 Comparaison avec HumanLoom (état audité)

| Point du dossier | HumanLoom aujourd'hui (mesuré) | Lecture |
|---|---|---|
| `Shift+A > Human` | ✅ Ajouter > Mesh > « Créer un humain » (sous Mesh, icône générique) | Proche ; déplacer dans un sous-menu « Humain » est un gain facile (§0) |
| Objet `MESH` marqué | ✅ `human_modeling_body` + `human_modeling_schema` ; pas d'UUID | Ajouter un identifiant stable résoudrait la duplication (I-24) |
| Source de vérité sur `Object` (`PropertyGroup`) | ❌ propriétés personnalisées `hm_*` sur le bloc de clés | **Aligné avec §0** ; migration schéma 10 nécessaire |
| Panneau dans Object Properties, `poll` sur humain | ❌ barre latérale seulement | **Aligné avec §0** ; gain d'ergonomie net |
| Duplication / suppression gérées | ❌ `Shift+D` du corps seul laisse yeux, cheveux, repères (I-24) ; suppression non testée | Le dossier le traite en exigence : à reprendre |
| Dégradation gracieuse sans l'extension | 🟡 drivers à expressions simples, groupes de nœuds du groom rendus locaux (test de réouverture ✅) ; pas testé extension désactivée | À tester explicitement |
| Bake vers objets natifs | ➖ absent | Idée nouvelle utile (export, partage) |
| Registre d'UUID et migrations | 🟡 migrations de schéma 0.13 → 0.14 ✅ ; pas d'UUID | Compléter |
| Cheveux/barbe en Geometry Nodes/Curves | ✅ déjà Hair Curves natives + nœuds natifs, suivi du corps ≤ 0,22 mm | Avance de HumanLoom sur le dossier |
| Contrôleur + moteurs + graphe de dépendances + planificateur | ➖ code en un module de 1 100 lignes (I-05) ; drivers natifs font office de « graphe » | Intéressant à terme, **risque de sur-ingénierie** (voir 14.3) |
| Budgets de performance 16–33 ms | ✅ cage 11 ms ; ❌ 42 ms avec Subsurf + Displace (en arrière-plan, CPU) (I-17) | Respecté sans modificateurs, dépassé avec |
| `blender_version_min = 5.0.0` | Manifeste : 5.2.0 à 5.3.0 ; seul 5.2 testé | Étendre à 5.0/5.1 demande des tests |
| Mannequin simple d'abord | HumanLoom a déjà une base réaliste de 10 582 sommets (provenance à documenter) | Pas de besoin de repartir d'un mannequin |
| Tests en arrière-plan + logique pure Python testée | 🟡 scripts Blender nombreux, pas de lanceur, logique pure peu isolée (I-01, I-04) | Aligné avec §8 |
| Vocabulaire fonctionnel (Height, Nose Width) | ✅ libellés fonctionnels (en français) | Aligné ; traduction à prévoir (§0) |
| Plusieurs humains coexistent | ✅ 3 créations indépendantes testées (mesh et clés distincts) | OK |

### 14.3 Avis (à discuter)
**À retenir :**
1. **Un humain = un objet `MESH` natif + `PropertyGroup` sur l'objet + panneau dans Object Properties + UUID.** C'est la même direction que notre §0 et elle règle plusieurs défauts mesurés (I-24, I-26 partiel, I-28).
2. **Cycle de vie explicite :** duplication, suppression, rechargement, migration, bake. Aujourd'hui trous (I-24).
3. **Contrat versionné pour les nœuds** et identifiants stables de sockets : à appliquer au groom (groupes locaux déjà).
4. **MVP vertical avant tout :** une tranche complète testée (création → réglage → sauvegarde → undo) plutôt qu'un empilement de fonctions.

**À manier avec prudence :**
1. **Contrôleur + moteurs abstraits + graphe + planificateur** : lourd. HumanLoom tire déjà parti des drivers natifs (459 drivers valides, 11 ms) qui jouent le rôle d'un graphe de dépendances géré par Blender. Ne l'introduire que pour un besoin mesuré (par exemple recalculs coûteux de repères, ajustement de vêtements).
2. **Reprendre depuis un mannequin :** le dossier part d'un prototype simple ; HumanLoom a déjà un corps, des mesures, des repères, un groom. Repartir de zéro perdrait ce qui est validé (§1 des tests : mesures, anatomie, groom, migrations).
3. **Valeurs par défaut du dossier non vérifiées** : `Shift+A` direct, `blender_version_min = 5.0.0`, API Geometry Nodes (pilotage des entrées de modificateurs), comportement d'annulation des propriétés personnalisées : à tester en 5.2 avant d'en faire des exigences.

**Ce que le dossier ne couvre pas (et que l'audit a montré important) :**
- **Qualité et calibration du contenu :** amplitudes, corpulence, visage, intersections de maillage, provenance et licence de la base.
- **Coût des shape keys :** 462 clés dans l'onglet Données ; un modèle « un paramètre ↔ une clé » explose ; il faut décider du regroupement (§0, §9).
- **Mesure anthropométrique, repères automatiques, références (NHANES/OMS)** : atout propre de HumanLoom.
- **Tests de non-régression de forme** et intégration continue.

### 14.5 Décisions prises (2026-11-21) — voir `DESIGN_NATIF.md`
1. Human Native = HumanLoom (un seul projet).
2. Identifiant `human_modeling` conservé (décision de Claude, à confirmer) ; nouvel espace de noms de données `Object.humanloom`.
3. Adopter maintenant : propriétés typées sur l'objet, panneau Object Properties, UUID, cycle de vie, bake, intégration native ; reporter contrôleur/moteurs, gizmos, éditeur de nœuds propre. Fusion des idées et du dossier dans `DESIGN_NATIF.md`.
4. Le prototype `human_native_5x.zip` est ignoré.

### 14.4 Décisions à prendre avec l'utilisateur (questions posées, avec réponses en 14.5)
1. « Human Native » est-il (a) la même ambition qu'HumanLoom, vue autrement, (b) un second projet, (c) la future architecture d'HumanLoom ?
2. Conserve-t-on le nom et l'identifiant `human_modeling` (compatibilité des scènes existantes) ou migre-t-on vers un nouvel identifiant ?
3. Adopter tout de suite : `PropertyGroup` sur l'objet, panneau Object Properties, UUID, cycle de vie, bake. Reporter : contrôleur/moteurs/planificateur, gizmos.
4. Le prototype `human_native_5x.zip` doit-il être audité (il faudrait le fournir) ou sert-il seulement d'inspiration ?
