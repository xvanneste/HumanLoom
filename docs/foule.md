# Foule HumanLoom (moteur natif, lots C1 et C2)

Moteur de foule intégré à l'extension : `extension/crowd.py` (moteur) et `extension/crowd_ui.py` (panneau « Foule » de l'onglet Humain). Tests : `tools/validate_crowd.py` (C1 à C12) ; mesures : `tools/measure_crowd.py`.

## Principes
- **Ensembles d'éléments variables** (`default_spec`) : plages de sexe, d'âge et de 24 contrôles de morphologie ; expressions pondérées ; comportements pondérés (marche, course, attente, discussion, saut, traversée) ; vitesses ; zones (trottoirs, passages piétons, aire libre) ; variantes extensibles (`variants` : tenues, coiffures…, appliquées par des fonctions enregistrées avec `register_variant_applier`, pour les lots vêtements).
- **Tirage à graine** : chaque personnage est tiré par `default_rng([graine, régénération, indice, essai])` ; même graine = même foule.
- **Garde-fous** : bornes des prises du groupe de nœuds, adiposité + muscles <= 1,4, distance minimale (0,12) entre personnages dans l'espace de diversité : un tirage trop proche d'un autre est retiré (jusqu'à 50 fois), donc pas de clones. Mesuré sur 150 personnages : distance minimale 0,72 (médiane 1,29).
- **Foule figée** : spec, tirages et résultats sont enregistrés dans la scène (`scene["humanloom_crowd"]`, JSON) et sur les objets (`hl_crowd_id`). Rien n'est recalculé à la réouverture ni au changement d'un réglage. Seuls `generate(replace=True)`, `regenerate_member` (un personnage, les autres inchangés) et `regenerate_all` la modifient ; « Générer » est refusé si une foule existe.
- **Comportements** : marche/course (trajet à vitesse propre, allers-retours), attente, discussion (paires face à face à 1 m), saut sur place, traversée d'un passage (retard de départ selon le cycle du feu). Évitement : répulsion + contournement latéral (rayon 1,1 m) ; distance minimale 0,50 m dans un flux de 6 contre 6 sur 3 m de large (0,02 m sans évitement).
- **Animations** : `spec["clips"][comportement]` = noms d'actions de la bibliothèque de l'utilisateur (déjà re-ciblées). À défaut, clips SYNTHÉTIQUES (balancement des jambes et des bras, respiration, gestes, saut) servent de bouchon et de test : aucune donnée tierce. Chaque clip est une bande NLA « Foule » avec décalage de phase tiré au hasard et échelle de vitesse selon la vitesse de marche.
- **Trajet** : clés de position et de cap toutes les 5 images (interpolation linéaire) sur le corps.
- **Mémoire** : le maillage de base (293 couches de morphologie) et le groupe de nœuds sont partagés entre tous les personnages ; fichier .blend de 21 Mo pour 10 personnages au lieu de 182 Mo.

## Niveaux de détail (C2)
0 complet ; 1 subdivision coupée et dents masquées ; 2 cage figée (nœuds géométriques retirés, groupes de poids conservés ; mêmes triangles que le niveau 1 mais évaluation environ 3 fois plus rapide) ; 3 cage décimée (30 %). `auto_lod` choisit selon la distance à la caméra (12 / 30 / 60 m). Le passage aux niveaux 2 et 3 est irréversible pour les contrôles du corps : régénérer le personnage pour revenir.

## Performances mesurées (machine de développement, 64 Go, 120 images, évaluation du graphe en arrière-plan, caméra à 30 m)

| Personnages | Génération (s) | par personnage (s) | Mémoire après génération (Mo) | .blend compressé (Mo) | Triangles évalués sans / avec LOD (millions) | Évaluation par image sans / avec LOD (ms) |
|---|---|---|---|---|---|---|
| 10 | 13 | 1,29 | 1 623 | 21 | 0,8 / 0,2 | 80 / 26 |
| 25 | 39 | 1,56 | 2 500 | 25 | 2,1 / 0,5 | 148 / 45 |
| 50 | 109 | 2,19 | 4 599 | 32 | 4,2 / 1,1 | 294 / 92 |
| 100 | 323 | 3,23 | 8 248 | 45 | 8,5 / 2,1 | 581 / 164 |
| 150 | 650 | 4,34 | 12 696 | 59 | 12,7 / 3,2 | 886 / 224 |

Lecture : la génération coûte 1,3 s par personnage pour 10, mais 4,3 s pour 150 (le coût par personnage augmente avec l'effectif : chaque nouvel objet relance la mise à jour du graphe de dépendances) ; la mémoire est d'environ 85 Mo par personnage au niveau de détail 0 ; les niveaux de détail réduisent le temps d'évaluation par image d'un facteur 3 à 4 (886 ms -> 224 ms pour 150) mais pas la mémoire (elle augmente : les cages figées s'ajoutent avant que les anciennes données soient libérées ; appliquer les niveaux de détail à la génération est une piste non faite). Ces temps sont ceux d'une évaluation du graphe sans rendu ; le rendu (Cycles, Eevee) n'est pas mesuré ici.

## Limites connues
- Pas de vêtements ni de coiffures dans la foule tant que les lots correspondants ne sont pas livrés (points d'extension prêts).
- Les clips synthétiques ne sont pas des animations de qualité : pour la production, renseigner `clips` avec des actions re-ciblées.
- Les trajectoires ne tiennent pas compte de décors (pas de collision avec des obstacles, seulement entre personnages).
- Évitement simple (pas de planification globale) : les flux très denses (plus de 2 personnes par mètre de largeur) descendent à 0,33 m de distance minimale.
- L'extension n'est pas testée au-delà de 150 personnages ; la mémoire à ce niveau (12,7 Go) suppose une machine de 32 Go ou plus.
