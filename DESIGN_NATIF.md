# DESIGN_NATIF — HumanLoom intégré naturellement à Blender (synthèse)

> **Mise à jour 2026-11-21 (fin de l'audit) :** l'architecture finale retenue (corps déformé par un groupe de nœuds, façade D sur ses entrées, arbitrage de vitesse accepté, défaut Atlas14 à corriger) est décrite dans `SUIVI_REPRISE.md` §7, qui prévaut sur les sections ci-dessous en cas de différence. Plan d'implémentation : `SUIVI_REPRISE.md` §9.

Statut : **conception proposée**, issue de la fusion de trois sources : (1) l'audit (`ETAT_DES_LIEUX.md`, `ISSUES.md`), (2) les idées du brainstorming (`IDEES.md` §0, §15), (3) le dossier « Human Native » écrit avec une autre IA (`IDEES.md` §14). Rien n'est implémenté. Tout élément marqué **[à prototyper]** est une hypothèse d'API à valider en Blender 5.2 avant de s'engager.

## 1. Décisions de l'utilisateur (2026-11-21)

| # | Question | Décision |
|---|---|---|
| 1 | Statut de « Human Native » | **C'est HumanLoom**, un seul projet. Le dossier est une réflexion externe. |
| 2 | Identifiant `human_modeling` | **Laissé à l'appréciation de Claude** : voir §3. |
| 3 | Ce qu'on adopte | Recommandation de Claude acceptée ; **fusionner** les idées de Claude et du dossier ; l'ensemble doit être **naturellement intégré dans Blender**. Contrôleur/moteurs abstraits et gizmos **reportés**. |
| 4 | Prototype `human_native_5x.zip` | **Ignoré** (code de qualité jugée insuffisante) ; on reste sur le projet HumanLoom. |

## 2. Principes directeurs

1. **Natif d'abord :** utiliser les éditeurs, menus, raccourcis, assets, annulation, animation, unités et traduction de Blender avant de créer une interface propre.
2. **Un humain = un objet `MESH` Blender ordinaire.** Une extension Python ne peut pas créer un nouveau type d'objet ; l'intégration passe par des propriétés sur l'objet, des panneaux, des menus, des opérateurs et des assets. Aucun patch de Blender.
3. **Une seule source de vérité :** des propriétés typées sur l'objet (`PropertyGroup`). Les shape keys, modificateurs et nœuds consomment ces valeurs ; aucune copie autoritaire ailleurs.
4. **Valider avant de généraliser :** une tranche complète testée de bout en bout (création → réglage → sauvegarde → annulation) avant de migrer les 49 contrôles.
5. **Ne pas sur-construire :** garder les drivers natifs comme mécanisme de mise à jour (459 drivers valides, 11 ms par changement sur la cage). Contrôleur, moteurs abstraits, graphe de dépendances et planificateur : **seulement pour un besoin mesuré**.
6. **Dégradation gracieuse :** les maillages, matériaux, cheveux et animations restent utilisables si l'extension est désactivée (les contrôles sont alors indisponibles). Test explicite à prévoir.
7. **Contenu mesurable :** calibrer sur des références (OMS, NHANES), garder les mentions « artistique » quand c'est le cas.

## 3. Identifiants et nommage (décision de Claude, à confirmer)

- **Identifiant d'extension : garder `human_modeling`.** Il identifie l'installation dans Blender (mise à jour, préférences) ; le changer ferait considérer la nouvelle version comme une autre extension et casserait les scènes qui contiennent `human_modeling_*`. Le nom affiché reste « HumanLoom ».
- **Nouvel espace de noms de données : `Object.humanloom`** (`PropertyGroup`), avec sous-groupes. Les propriétés `hm_*` (bloc de clés) restent lisibles pour la migration (schéma 9 → 10).
- **Opérateurs :** les nouveaux opérateurs en `humanloom.*` (comme le groom) ; les anciens `human_modeling.*` restent comme alias dépréciés pendant une version, pour ne pas casser les scripts existants.
- **Menu :** « HumanLoom » en libellé ; « Humain » dans l'interface française.

## 4. Modèle de données natif

```text
Object (MESH) — le corps, point d'entrée sélectionnable
└── humanloom (PropertyGroup, enregistré sur bpy.types.Object)
    ├── is_human, uuid, schema_version, generator_version
    ├── identity  : sex, age_years (ancres 5/15/30/75 + continu), height_cm
    ├── body      : mass, shoulders, waist, hips, ... (valeurs actuelles de CONTROLS)
    ├── muscles   : global + régions
    ├── face      : head_*, jaw, chin, nose_*, mouth, lips, eyes_*, ears_*
    ├── hair      : zones (liste), densité, longueur, gris, graine …
    ├── appearance: peau (mélanine, rougeur, rugosité), yeux
    └── links     : pointeurs (ObjectProperty) vers yeux, repères, zones de cheveux, rig
```

- **Pilotage (mis à jour après prototypes, voir `SUIVI_REPRISE.md` T-P1) :** ~~les drivers lisent `Object.humanloom.<chemin>` par chemin RNA~~ → **écarté** : équivalent en forme (0,0 mm) et en temps, mais **tous les drivers deviennent invalides si l'extension est absente** (458/459). Deux variantes validées : **D (recommandée)** une `PropertyGroup` **façade** sur l'objet dont le getter/setter lit et écrit les propriétés personnalisées du bloc de clés (aucun driver réécrit, dégradation gracieuse conservée, panneau et animation fonctionnent, undo ✅) ; **C** des propriétés personnalisées directement sur l'objet avec drivers vers l'objet (chemin `["hl_x"]`, valide sans l'extension). **Décision de l'utilisateur (2026-11-21) : variante D, avec précision (à confirmer) : une fois le corps déformé par un groupe de nœuds, la façade lit et écrit les entrées du modificateur de nœuds.** Les anciennes propriétés `hm_*` du bloc de clés restent la source ; la façade `Object.humanloom` (nom à confirmer) les lit et les écrit. La façade de nœuds (T-CF) devient une couche optionnelle, à tester si elle est souhaitée (longueur de cheveux, entrées animables).
- **Liens par pointeurs** (`PointerProperty` vers objets) et UUID, jamais par noms.
- **Maillage partagé :** deux objets liés au même maillage partagent les clés et donc la forme ; l'opérateur de duplication rend le maillage et les clés indépendants (voir §6).
- **Fichiers existants :** migration schéma 9 → 10 qui crée `humanloom`, recopie les `hm_*`, réécrit les drivers, conserve les anciens paramètres jusqu'à la fin de la migration (test avec `regional_upgrade18` et un fichier schéma 9).

## 5. Surfaces d'interface natives

**MVP (première tranche) :**

| Surface | Contenu |
|---|---|
| **Ajouter > Humain** (sous-menu du menu Ajouter) | Humain adulte, enfant, personnalisé ; plus tard : avec cheveux |
| **Dernière opération (F9)** à la création | Sexe, âge, taille, graine, coiffure de départ (au lieu d'un corps par défaut fixe) |
| **Propriétés > Objet > panneau « Humain »** (visible seulement sur un humain, `poll`) | Sous-panneaux : Identité, Corps, Visage, Cheveux, Mesures, Outils |
| **Même contenu dans la barre latérale (N) > Humain** | Même fonction de dessin réutilisée : un seul code, deux emplacements |
| **Clic droit sur un humain** | Dupliquer le personnage, Réinitialiser, Variation, Convertir (Bake) |
| **Fichier > Importer/Exporter** | Préréglages et réglages de groom (JSON), au lieu de boutons dans le panneau |
| **Mise en page Blender** | `use_property_split`, listes (`template_list`) pour les zones de pilosité, unités de la scène, infobulles (`bl_description`), messages d'inactivité **[à prototyper : `poll_message_set` en 5.2]** |
| **Traduction** | Textes sources en anglais + dictionnaire français (`bpy.app.translations`) |
| **Sliders** | Défaut défini (retour arrière = remise à zéro), animables (touche I), copier-coller |

**Ensuite :** Asset Browser (préréglages, silhouettes, visages, coiffures avec vignettes), pie menu et raccourcis modifiables (`keyconfigs.addon`), atelier « Personnage », opérateurs interactifs (taille en tirant dans la vue), superpositions de mesures.

**Reporté :** gizmos, outil de barre d'outils « Morphing », éditeur de nœuds propre.

## 6. Cycle de vie (repris du dossier, adapté)

| Opération | Règle |
|---|---|
| **Création** | Une collection par personnage (corps, yeux, cheveux, repères) ; UUID généré ; liens par pointeurs ; annulable |
| **Duplication** | Opérateur « Dupliquer le personnage » : copie corps, yeux, zones de cheveux, repères ; nouvel UUID ; maillage et clés indépendants ; détection d'un UUID en double si l'utilisateur duplique à la main (message + correction proposée) |
| **Suppression** | « Supprimer le personnage » retire les dépendants ; supprimer le corps seul ne laisse pas d'erreurs persistantes |
| **Rangement** | Tous les objets du personnage dans la collection du corps (corrige I-28) |
| **Sauvegarde/rechargement** | Propriétés, UUID et résultat conservés (déjà ✅ pour les drivers et le schéma 9) |
| **Annulation** | Tous les opérateurs modifiants `REGISTER`/`UNDO` ; testée dans l'interface réelle (déjà ✅ pour 4 actions) |
| **Migration** | Schéma 10 avec script testé ; anciens fichiers lisibles |
| **Bake (convertir en objets ordinaires)** | Opération explicite : applique morphs et modificateurs, supprime drivers et dépendances à l'extension, conserve matériaux et armature ; documentée comme destructive |
| **Désactivation de l'extension** | Aucun résidu de classes/handlers/timers ; maillages et animations utilisables |

## 7. Animation et nœuds (intègre §15 de `IDEES.md`)

Constat testé : âge et corpulence s'animent ; densité de cheveux s'anime ; **longueur de cheveux non** (pas d'entrée native).

Ordre proposé :
1. **A.** Âge en **années** et stature continue en fonction de l'âge (courbes OMS/NHANES) → « croissance » = une image clé.
2. **B.** Entrée native de **longueur** dans la pile de cheveux (facteur de rognage 0–1) pour animer la pousse.
3. **C (visé par l'utilisateur, décision 2026-11-21).** **Mise à jour après la passe finale (`SUIVI_REPRISE.md` 4 bis G) : forme retenue = « façade de nœuds » — le groupe de nœuds « HL Human » porte les entrées (sexe, âge, 48 contrôles), les drivers existants les lisent et les shape keys déforment (erreur 0,00012 mm, temps identique, animable, valide sans l'extension, duplication correcte). La déformation complète par nœuds est écartée comme moteur interactif (57,6 ms, 459 ms avec Subsurf).** Description d'origine : Groupe de nœuds « Humain » (Âge en années, Sexe, Taille, Corpulence, Muscles, visage, longueur de cheveux), modificateur Geometry Nodes **et** asset. Faisabilité mesurée (`docs/audit/mesures-noeuds-c.md`, détail `IDEES.md` §15.4) : les 461 shape keys se réduisent à une base de **~150 déformations** (rang effectif à 1e-5) ; un mélange de 150 déformations en attributs de sommets coûte **~8 ms et ~19 Mo** (contre 11 ms pour les shape keys + drivers) avec 0,0 mm d'erreur sur la somme linéaire. À prototyper avant d'engager : non-linéarités des drivers, interpolation d'âge et de sexe, yeux, taille du fichier, erreur de la base réduite, coût dans l'interface. Variante hybride possible (quelques shape keys éditables pour le visage).
4. **E.** Usages de timeline (accéléré, cycle de vie NLA, variation de masse).
5. **D.** Éditeur de nœuds propre : **reporté**.

Compatibilité à vérifier : actions par couches de Blender 5 (`Action` sans `fcurves`).

## 8. Ce qui est reporté (et pourquoi)

| Élément | Raison |
|---|---|
| Contrôleur central + moteurs abstraits + graphe + planificateur | Les drivers natifs jouent déjà ce rôle (11 ms) ; à introduire sur besoin mesuré (repères auto, ajustement de vêtements) |
| Gizmos et outil de barre d'outils | Après le panneau natif et l'Asset Browser |
| Éditeur de nœuds personnalisé | Coût de maintenance ; entrées de modificateurs et drivers d'abord |
| Vêtements, rig complet | Après le socle ; dépendent des repères automatiques |

## 9. Phasage (fusion de la feuille de route du dossier et de l'audit)

| Phase | Contenu | Critère de validation |
|---|---|---|
| **0 — Gains rapides** | I-19 (bornes du groom), I-28 (collection des cheveux), I-27, tests périmés (I-34), masquage des contrôles hérités, décision I-30 | tests concernés verts |
| **1 — Socle de test** | Lanceur indépendant de l'installation, fixtures générées, tests de forme, CI Blender en ligne de commande | tous les scripts utiles exécutables sur un clone neuf |
| **2 — Tranche verticale native** | `Object.humanloom` avec 4–5 paramètres (sexe, âge, taille, épaules, corpulence), drivers reliés à l'objet, panneau Objet + barre latérale, Ajouter > Humain, F9 à la création, UUID, duplication/suppression, sauvegarde, annulation | critères §10 |
| **3 — Migration complète** | Les 49 contrôles, schéma 10, migration, alias dépréciés | `regional_upgrade18` et un fichier schéma 9 ; aucune régression de forme hors I-30 |
| **4 — Contenu** | Corpulence unifiée, visage re-étalonné, intersections (I-14), amplitudes (I-13) | mesures et rendus de référence |
| **5 — Animation** | §7 A et B | test d'images clés (âge, taille, longueur de cheveux) |
| **6 — Assets, peau et yeux, repères automatiques, rig** | Asset Browser, matériaux, repères auto, Rigify | par domaine |
| **7 — Finition native** | Raccourcis, pie menu, atelier, traduction complète, documentation | revue d'ergonomie |

## 10. Critères d'acceptation de la tranche verticale (phase 2)

- [ ] L'extension s'installe (paquet isolé) et s'active sans exception sur Blender 5.2.
- [ ] Ajouter > Humain crée un humain ; les options de création sont dans « Ajuster la dernière opération ».
- [ ] L'objet est un `MESH` Blender ordinaire identifié par `humanloom.is_human` et un UUID.
- [ ] Le panneau « Humain » n'apparaît que sur un humain, dans Propriétés > Objet et dans la barre latérale (même code).
- [ ] Les 5 paramètres déplacent la géométrie (shape keys via drivers reliés à l'objet) avec les mêmes résultats que la version actuelle (tolérance à définir).
- [ ] Les paramètres sont animables (images clés) et annulables (Ctrl+Z) dans l'interface réelle.
- [ ] Deux humains coexistent et se modifient indépendamment ; la duplication crée un humain indépendant avec un nouvel UUID.
- [ ] Sauvegarde/rechargement conservent paramètres, UUID et résultat.
- [ ] Désactiver puis réactiver l'extension ne laisse aucun résidu ; le maillage reste utilisable désactivée.
- [ ] Temps de mise à jour d'un slider ≤ 33 ms sur la cage (référence : 11 ms).
- [ ] Tests automatisés (arrière-plan) et captures d'interface ajoutés.

## 11. Prototypes jetables avant la phase 2 — **résultats (2026-11-21)** (détail : `SUIVI_REPRISE.md` §4 D)

| # | Prototype | Verdict |
|---|---|---|
| 1 | Propriétés côté objet + drivers | ✅ variantes C et D ; ⛔ variante A (RNA) ; temps identique (~14 ms), duplication et images clés OK |
| 2 | Panneau dans Propriétés > Objet + barre latérale, même fonction de dessin ; undo | ✅ (menu Ajouter, F9, raccourci, `poll_message_set` enregistrés mais non exercés visuellement) |
| 3 | Entrée de longueur animable pour les cheveux | ✅ nœud Trim Curves ; ordre dans la pile à vérifier |
| 4 | Duplication du personnage complet | ✅ avec toute la hiérarchie ; ⚠ matériau de cheveux partagé à rendre unique |
| 5 | Traduction | ✅ chaînes propres ; ⚠ « Height » reste « Hauteur » (catalogue de Blender) |
| 6 | Images clés sur propriétés d'objet, API d'actions 5.x | ✅ via slots/channelbag |
| 7 | Option C (nœuds) | ✅ base de ~150 déformations (0,047 mm), ~8 ms ; ⬜ cheveux/yeux sur corps en nœuds, poids en nœuds, perf interface |

Les descriptions d'origine des prototypes sont conservées ci-dessous.

## 11 bis. Descriptions d'origine des prototypes

1. `PropertyGroup` sur `Object` (bornes, défaut, `update`) + driver d'une shape key lisant `Object.humanloom.x` ; mesurer le temps et vérifier undo, sauvegarde, copie d'objet.
2. Panneau dans Propriétés > Objet et dans la barre latérale avec une même fonction de dessin ; `poll` et `poll_message_set`.
3. Entrée d'une pile de cheveux avec un nœud de rognage animable (longueur).
4. Duplication « personnage complet » (copie des mesh/clés, drivers, pointeurs, UUID).
5. Dictionnaire de traduction : une chaîne anglaise + sa traduction française.
6. Images clés sur `Object.humanloom` et lecture/écriture d'actions avec l'API 5.x (slots).
7. **(option C)** Groupe de nœuds « Humain » : poids calculés en nœuds (courbes d'âge, non-linéarités), base réduite de ~150 déformations en attributs ; comparer la forme au rendu actuel (écart en mm), le temps dans l'interface, la taille du `.blend` et les yeux/cheveux qui suivent.

## 12. Risques

- **Migration des 459 drivers** vers l'objet : volume, performance et compatibilité des fichiers existants.
- **Maillages partagés** (liens) : la forme est commune ; imposer des maillages indépendants à la création et à la duplication.
- **462 shape keys** dans l'onglet Données : à réduire ou regrouper (voir `IDEES.md` §9).
- **API 5.x** non vérifiées (actions, `poll_message_set`, propriétés de modificateurs) : prototypes d'abord.
- **Conflits de raccourcis** avec Blender ou d'autres extensions : choisir des combinaisons libres, toutes modifiables.
- **Étendre la compatibilité** (Blender 5.0/5.1) : à tester ; actuellement 5.2 seulement.
