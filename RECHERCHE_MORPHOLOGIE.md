# RECHERCHE_MORPHOLOGIE — morphologie du corps pour la modélisation

> **Validation du 2026-11-21 : voir `VALIDATION_SCIENTIFIQUE.md`.** Vérifiés : Anny (267 paramètres, Bêta, Apache 2.0, 13 718 sommets, calibration OMS *enfants*, mise en garde sur les stéréotypes), STAR (20 %, ~10 000 scans), ANSUR II (4 082 / 1 986 / 93 ; population militaire ; « weightkg » en hectogrammes). Mis à jour avec les PDF locaux (`VALIDATION_SCIENTIFIQUE.md` §4) : graisse androïde/gynoïde, puberté et ménopause ✅ vérifiés ; Heath-Carter : méthode, 13 catégories et étude de 341 adultes (185 H / 156 F) ✅ vérifiées (Campa 2025) ; **bandes numériques non retrouvées** ⬜. « 6 890 sommets » de SMPL non retrouvé dans le texte lu.

Date : 2026-11-21. Statut : recherche documentaire ; **rien n'est implémenté**. Les extraits cités n'ont pas été relus en entier (⚠). Les références de données déjà dans le dépôt : OMS, NHANES, physique (`extension/data/`).

## 1. Modèles statistiques de corps (SMPL et suites)

| Modèle | Idée | Limites / intérêt pour HumanLoom | Source |
|---|---|---|---|
| **SMPL** | 6 890 sommets ; formes par déformations globales apprises sur scans, pose par skinning + correctifs | déformations **globales**, artefacts non locaux ; licence de recherche (non commerciale) à vérifier ⬜ | [SMPL](https://smpl.is.tue.mpg.de/) |
| **STAR** | correctifs **locaux et parcimonieux**, ≈ 20 % des paramètres de SMPL, > 10 000 scans | montre que des bases locales valent mieux que globales — **cohérent avec la base locale par contrôle de HumanLoom (D-05)** | [STAR](https://download.is.tue.mpg.de/star/star_paper.pdf) |
| **GHUM** | espace latent (VAE / flux normalisant) | boîte noire peu éditable | [arXiv 2203.01923](https://arxiv.org/pdf/2203.01923) |
| **Anny** (NAVER, 2025) | **paramètres de phénotype interprétables** (genre, âge, taille, poids, muscle, proportions) ∈ [0,1], pas de scans ; calibré sur statistiques **OMS** ; s'inspire de MakeHuman ; Apache 2.0 | **le plus proche de la philosophie de HumanLoom** ; poids/taille/IMC modélisés en lois Bêta conditionnées par âge et genre (résumé secondaire ⚠) | [arXiv 2511.03589](https://arxiv.org/abs/2511.03589v2), [HTML](https://arxiv.org/html/2511.03589v2) |
| Conditionnement anthropométrique (SHAPY) | forme déduite de taille, poids, tour de poitrine/taille/hanches | idée : exposer « taille / poids / tours » comme **entrées** et résoudre le reste | [PMC8914647](https://pmc.ncbi.nlm.nih.gov/articles/PMC8914647) |

## 2. Données anthropométriques

- **ANSUR II** (US Army, 2010-2012) : 93 mesures directes + 15 variables démographiques ; 4 082 hommes, 1 986 femmes ; **données publiques, sans scans 3D** ; rapport NATICK/TR-15/007. Population militaire américaine : **non représentative** (âge, corpulence) — usage : validation de proportions adultes, pas de calibration générale. ✅ [ANSUR II](https://www.openlab.psu.edu/ansur2/), [présentation](https://ph.health.mil/topics/workplacehealth/ergo/Pages/Anthropometric-Database.aspx), [DTIC](https://apps.dtic.mil/sti/pdfs/AD1109537.pdf).
- CAESAR (scans 3D, licence payante), NHANES, OMS : déjà partiellement dans le dépôt ; CAESAR non consulté ⬜.

## 3. Composition corporelle, graisse, sexe

- **Somatotype Heath-Carter** (endomorphie/mésomorphie/ectomorphie ; bandes : < 3 faible, 3-5 modéré, 5,5-7 élevé, ≥ 7,5 très élevé). Une étude de 2025 (341 adultes) : hommes endo-mésomorphes, femmes méso-endomorphes, centroïdes différents (p < 0,001) mais **forte variabilité intra-catégorie** ; la catégorie reflète mal masse musculaire et graisse réelles. ⚠ [Frontiers 2025](https://www.frontiersin.org/articles/10.3389/fphys.2025.1722899), [Campa et al. 2025, PMC12679298](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12679298/). → s'en servir comme **vocabulaire d'interface**, pas comme modèle.
- **Distribution de la graisse** : dimorphisme dès la puberté (femmes : plus de % de graisse, hanches/cuisses — « gynoïde » ; hommes : abdominale/viscérale — « androïde ») ; après la ménopause, la graisse centrale augmente ; mécanismes non entièrement connus, hormones centrales, déterminants génétiques. ⚠ [Biol Sex Differ 2012](https://link.springer.com/doi/10.1186/2042-6410-3-13), [PMC4348027](https://pmc.ncbi.nlm.nih.gov/articles/PMC4348027), [PMC6795075](https://pmc.ncbi.nlm.nih.gov/articles/PMC6795075).

## 4. Implications pour HumanLoom

1. **Corpulence unifiée** (déjà dans le plan) : un seul curseur « poids/IMC » + **distribution régionale de graisse** (androïde ↔ gynoïde) dont le défaut dépend du **sexe et de l'âge** (ménopause = déplacement central), plutôt que deux jeux séparés. Les fonctions « chapeau » d'âge × sexe existent déjà dans les contrôles (§7 de `SUIVI_REPRISE.md`).
2. **Entrées anthropométriques** (taille, poids, tour de taille/hanche) : un solveur (moindres carrés sur la base locale) qui propose les curseurs — à prototyper ⬜ ; ANSUR II sert à vérifier les ordres de grandeur adultes.
3. **Bases locales** (STAR) : la base locale par contrôle de D-05 est **justifiée par la littérature** ; l'écart d'Atlas14 à la migration (D-10) reste un défaut à corriger.
4. **Âge et enfance** : Anny couvre nourrisson → vieillard avec une calibration OMS ; HumanLoom a 308 clés d'âge : comparer les proportions (tête/corps selon l'âge) à l'OMS. Aucune validation clinique ne doit être revendiquée.
5. **Diversité** : prévoir des ancrages de morphologie pour plusieurs populations (le dimorphisme et les proportions varient) ; ne pas déduire la morphologie d'un teint (cf. `RECHERCHE_PEAU.md` : la teinte et la forme sont deux axes indépendants).
6. **Licences** : SMPL = licence de recherche ; Anny = Apache 2.0 (reprise de données possible après lecture ; **aucune reprise décidée**).

## 5. Lacunes

- Valeurs numériques de répartition de graisse non extraites ; CAESAR non lu ; tables OMS déjà dans `extension/data/` non ré-auditées dans cette passe.
- Anny : liste exacte des paramètres, validation et fichiers téléchargeables **non lus** ⬜.

## 6. Tests proposés (rien n'est fait)

- T-M1 : mesurer les 93 mesures ANSUR II approximables (taille, tour de taille, hanche, largeur épaules…) sur des corps HumanLoom générés vs les distributions publiées (z-scores).
- T-M2 : prototype de solveur « taille/poids/tour de taille → curseurs ».
