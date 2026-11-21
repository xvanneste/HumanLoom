# RECHERCHE_PLUGINS — autres générateurs d'humains (analyse, pas de réutilisation)

Date : 2026-11-21. Prolonge `REFERENCE_PLUGINS.md` (première passe sur MPFB2 et CharMorph). Cette passe a lu : `lib/materials.py` et `lib/rigging.py` de CharMorph, la liste des fichiers et les docs de matériau/rig de MPFB2, plus des résumés web. **Aucun code n'a été copié.** Licences : à relire avant toute reprise, et HumanLoom garde sa propre licence.

| Outil | Licence (d'après les sources) | Peau | Rig | Morphologie | Ce qu'on en retient |
|---|---|---|---|---|---|
| **MPFB2** (MakeHuman pour Blender) | GPL v3+ ([extensions.blender.org](https://extensions.blender.org/add-ons/mpfb/)) | groupe de nœuds `MpfbSkin` : couleur de peau, taches, veines, SSS à rayons X/Y/Z, sous-nœuds de variation de couleur/normale ; peau « enhanced » avec échelle SSS selon l'unité | jeux de rigs en données (default, game_engine, mixamo, openpose, cmu_mb) + Rigify + outils make-rig / transfert de poids | cibles MakeHuman (paramétrique) | peau = **groupe de nœuds paramétrique + masques procéduraux** ; rigs et poids **en données** |
| **CharMorph** | code GPLv3 ; packs : licences variables, MB-Lab sous AGPL | matériaux en bibliothèque `.blend`, textures par jeu (résolution réglable), couleur de peau/yeux directe, déplacement | Rigify complet (ou ARP), joints/poids en données, `sliding_joints`, double modificateur Armature avec *preserve volume* ; **rig non morphé en temps réel** | moteur numpy, fitting d'assets | séparation logique/interface ; **le rig suit la morphologie à la finalisation**, pas en continu |
| **MB-Lab** | AGPL/GPL (sources divergentes ; vérifier le dépôt officiel) ; développement arrêté, continué par CharMorph ([GitHub](https://github.com/animate1978/MB-Lab), [doc](https://mb-lab-docs.readthedocs.io/en/latest/updates.html)) | nouveau shader (1.7.6), carte de mélanine (1.8), textures SSS/rugosité/spéculaire/bump/déplacement | rig proposé | morphs d'origine ManuelbastioniLAB | **ne pas mélanger sa base de morphs (AGPL) au code HumanLoom** |
| **Human Generator** | commercial ([BlenderNation](https://www.blendernation.com/2021/03/15/human-generator-for-blender-now-available/)) | textures de teint, morphs ; jugé meilleur que MB-Lab/MakeHuman dans une plage limitée (avis d'un testeur) | — | — | référence de **qualité attendue** ; pas de reprise possible |
| **Globalskin** | commercial ([Blender Market](https://blendermarket.com/products/globalskin-ultimate-skin-shader/faq)) | shader de peau ; un utilisateur signale qu'il casse des fonctions d'ajustement de Human Generator | — | — | un shader de peau **tiers** peut entrer en conflit : prévoir un matériau remplaçable sans casser les contrôles |
| **Blender Studio** | assets/outils ouverts | rendus toon (Wing It!) | rigs de production (Rigify, rigs de personnages) | — | référence **stylisée** documentée (voir `RECHERCHE_PEAU.md`) |

Non étudiés dans cette passe : Character Creator / Daz / MetaHuman (fermés, licences propres ; le dépôt contient des dossiers MetaHuman locaux non analysés ⬜), Auto-Rig Pro, MakeHuman natif.

## Points à retenir pour HumanLoom

1. **Données, pas code** : peau, rigs, poids et joints sont des **fichiers de ressources** (cohérent avec `human_nodes.blend` de D-05).
2. **Un matériau de peau par groupe de nœuds** remplaçable et paramétrable, avec **masques régionaux** — là où les autres plugins sont soit proprement paramétriques (MPFB2), soit basés sur des textures par jeu (CharMorph/MB-Lab).
3. **Le rig de CharMorph n'est pas morphé en temps réel** : HumanLoom peut faire mieux seulement si le méta-rig est recalculé depuis le maillage évalué (voir `RECHERCHE_RIG.md`) — **à démontrer**.
4. **Licences** : GPL (MPFB2, CharMorph), AGPL (packs MB-Lab) ⇒ toute reprise de données ou de code exige une décision juridique explicite de l'utilisateur ; par défaut, **analyse seulement**.
