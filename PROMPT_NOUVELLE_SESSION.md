# PROMPT_NOUVELLE_SESSION — message à coller au début d'une nouvelle session

Copier-coller le bloc ci-dessous comme premier message.

---

Tu reprends le projet **HumanLoom** (extension Blender 5.2 de génération d'humains) dans `G:\_dev\BlenderDev\HumanLoom`, branche de travail **`codex/natif`** (créée depuis `codex/groom` ; aucun commit sans mon accord explicite). Un audit complet, des prototypes, une recherche documentaire et un plan sont terminés ; **tout est documenté, ne refais pas les tests déjà faits**.

**Lis dans cet ordre :** `CLAUDE.md` → `SUIVI_REPRISE.md` (décisions D-01 à D-17, registre des tests avec verdicts §4, architecture finale §7, pièges §8, plan §9, questions ouvertes §10) → `DESIGN_NATIF.md` → `ISSUES.md` (I-01 à I-46) → `SYNTHESE_RECHERCHE.md` et `VALIDATION_SCIENTIFIQUE.md` (peau, morphologie, rig ; ce qui est vérifié ou non) → `AJOUT_CONTROLES.md`, `AMPLITUDES_CONTROLES.md`, `REGROUPEMENT_CONTROLES.md`. Les preuves sont dans `docs/audit/` et les scripts de mesure dans `tools/audit/` (README inclus).

**Décisions acquises (ne pas rediscuter) :**
- Un humain = un `MESH` ordinaire ; identifiant d'extension `human_modeling` conservé (propriétés `hm_*` jamais renommées).
- Le corps est déformé par un **groupe de nœuds Geometry Nodes « HL Human »** (base locale par contrôle, poids compilés des formules actuelles, suppression des couches avant la subdivision), fabriqué **hors ligne** et livré dans un `.blend`. Les nœuds se mettent dans le graphe de Blender et se lient à d'autres objets. Surcoût accepté : ≈ 58 ms avec Subsurf contre 43 ms pour les shape keys.
- **Façade D** : `PropertyGroup` sur l'objet qui lit/écrit les entrées du modificateur ; panneau dans Propriétés > Objet et dans la barre latérale ; intégration native maximale.
- Visage : identité en nœuds, expressions en shape keys séparées, bake à la demande (D-14). L'écart de forme Atlas14 à la migration est un défaut à corriger (D-10).
- **Public : film, rendus réalistes et stylisés** ; **seul Blender 5.2** est ciblé et testé (D-12, D-13).
- **Nouveaux contrôles** : peu de contrôles nommés + mode avancé de transformation de région ; chaque contrôle = une couche du groupe « HL Human » ; inspiration des noms de MPFB2, aucune donnée reprise (D-16). Dents et anatomie génitale (option « Anatomie adulte » désactivée par défaut, indisponible aux âges enfant/adolescent) sont au catalogue.
- Reportés : contrôleur/moteurs abstraits, éditeur de nœuds propre, gizmos. **Rig, texturing, mapping UV, dents : non commencés** ; l'ordre est dans `SUIVI_REPRISE.md` §9.

**Règles :**
1. Réponds en français ; l'interface du plugin est en français (source en anglais + traduction à terme).
2. **Ne touche jamais** à ma session Blender ni aux autres versions de Blender installées (3.6, 4.4, 5.0, 5.3). Teste dans une instance séparée de Blender 5.2, en lecture seule quand c'est possible (voir `SUIVI_REPRISE.md` §8 : `tools/audit/shim.py`, pièges d'évaluation, d'interface, de Windows, de shell, de PDF).
3. Ne committe, supprime ni fusionne rien sans mon accord explicite. L'arbre contient des fichiers non suivis voulus (rapports, `docs/audit/`, `tools/audit/`) et mon travail en cours (`tools/*collision29*.py`).
4. Distingue toujours **mesuré** de **supposé** ; ne marque rien « validé » sans test exécuté ; ajoute chaque nouveau test dans le registre de `SUIVI_REPRISE.md` (§4) avec verdict et preuve.
5. Avant une action destructive ou une décision d'architecture, demande.

**Première mission :** résume en dix lignes ce que tu as compris (état, décisions, risques). Puis exécute le plan de `SUIVI_REPRISE.md` §9 dans l'ordre : confirme avec moi les questions ouvertes du §10 (amplitudes, tests périmés, UV, liste de contrôles, regroupement), commence par l'**état de référence des tests** (les scripts `tools/validate_*.py` ont chacun leurs arguments : lis leur en-tête, ne les boucle pas aveuglément), puis les gains rapides de l'étape 1. Ne passe à l'étape 3 (générateur hors ligne du groupe de nœuds) qu'après mon accord.
