# UI_REVIEW — Interface observée et pistes d'amélioration

Méthode : ma propre instance de Blender 5.2 (démarrage d'usine, extension du clone `codex/groom` @ `443d278`, tous les sous-panneaux dépliés pour la capture), jamais la session ouverte de l'utilisateur. Captures : `docs/audit/ui-sidebar-haut.png`, `ui-sidebar-visage.png`, `ui-sidebar-bas.png`. Non testé : corps non sélectionné, mode Édition, redimensionnement étroit du panneau, thème clair, interactions à la souris, undo.

## Observé

Un seul onglet **Humain** dans la barre latérale ; tout y est dans un panneau parent « HumanLoom · Modélisation » avec 11 sous-panneaux, groom compris (dernier, sous « Contrôle du maillage »).

1. **Sliders -1..+1 affichés à moitié remplis à 0** (barre bleue à 50 % pour tous), difficile à lire pour savoir si un réglage a été touché ; pas de réinitialisation par curseur (seulement « Réinitialiser les proportions » global).
2. **Liste plate de 21 sliders « Visage »** sans regroupement (yeux, nez, bouche, oreilles, mâchoire) ni recherche ; 10 sliders de musculature et 7 de corpulence idem.
3. **Contrôles redondants ou hérités visibles par défaut** : « Corpulence globale », « Volume initial », « Couverture régionale », « Volume 0.12 » (panneau « Volumes des anciennes versions ») en plus de « Couverture régionale » dans « Corpulence et tissus ». Quatre notions proches de corpulence pour l'utilisateur.
4. **Âge : « Transition 2.000 »** est un paramètre sans unité (0–3) alors que les boutons affichent 5/15/30/75 ans ; texte explicatif tronqué (« amplitude artis… »).
5. **« Régler la taille »** n'affiche pas de champ de taille ; une boîte de dialogue s'ouvre. Le panneau « Mesures » affiche la stature (168,9 cm) séparément, avec un second bouton « Appliquer la stature de référence ».
6. **Libellés tronqués** dans la largeur par défaut : « Groupe … », « Sexe de … », « Zone de pilo… », « Contacts coplanaire…es imbriqués exclus ». Les notes explicatives sont des lignes de texte non repliées.
7. **Silhouettes** : boutons textuels sans aperçu.
8. **Champ « Subdivision »** en haut du panneau, sans explication de ce qu'il pilote (viewport, niveau 1 ; rendu 2).
9. **Contrôles sans effet visible** : voir ISSUES I-13 (plusieurs sliders de visage déplacent moins de 2 mm à ±1, « Relief de peau âgée » est inactif avant 30 ans et ≤ 0,8 mm à 75 ans) mais rien n'indique à l'utilisateur qu'un curseur est inactif.
10. Message « Zones manquantes ajoutées. » même si rien n'est ajouté (`groom.py`, `HL_OT_groom_preset`).

## Pistes (à discuter, aucune implémentée)

- **Onglets séparés** : Corps / Visage / Âge / Cheveux / Mesures / Outils, ou panneaux frères au lieu d'un parent unique. Le groom mérite son propre onglet.
- **Sliders** : style « centré » (barre partant de 0), bouton de remise à zéro par réglage et bouton « réinitialiser la section », valeurs en unités compréhensibles (cm, %, années).
- **Visage** : sous-sections repliables par région ; vues rapides de la caméra sur la tête ; possibilité de n'afficher que les réglages modifiés.
- **Âge** : un seul curseur en années avec ancres 5/15/30/75 ; griser les contrôles dépendants de l'âge (relief de peau) quand ils sont sans effet.
- **Corpulence** : masquer les contrôles hérités (« anciennes versions ») sous un réglage avancé ; une seule échelle de corpulence principale.
- **Silhouettes et préréglages** : vignettes d'aperçu, prévisualisation avant application, bibliothèque de préréglages (au-delà de l'enregistrement/chargement de JSON).
- **Taille** : champ numérique directement dans le panneau.
- **Retours** : infobulles précises (déjà présentes pour certains opérateurs), message adapté quand aucune zone n'est ajoutée, avertissement de géométrie (intersections) visible au lieu d'un bouton à lancer.
- **Ajouts fonctionnels à étudier** (non présents) : choix de l'origine/ethnie de base, couleur et textures de peau et d'yeux, dents, rig et poses, vêtements, export (FBX/glTF/USD) avec options, sauvegarde de personnage complète (corps + cheveux).
