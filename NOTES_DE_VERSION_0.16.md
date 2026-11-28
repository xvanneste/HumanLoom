# HumanLoom 0.16.0 - notes de version (28 nov. 2026)

Branche `codex/natif`, Blender 5.2 exclusivement. Tout ce qui suit est écrit en français comme le reste du projet ; les chiffres viennent de `tools/` et de `validation/` (non versionné) et sont ceux d'une machine de développement.

## Nouveautés
- **Squelette** : deux modificateurs Armature (linéaire et quaternions duals avec « Preserve Volume »), poids symétrisés (version 2 du squelette avec migration et retour arrière), torsion de l'avant-bras pilotée par la main.
- **Retargeting** : rythme scapulo-huméral ACTIF par défaut (case désactivable), rééchantillonnage selon la cadence de la scène (une action à 30 i/s dans une scène à 24 i/s garde sa durée), options inactives : rotation du cou répartie, rotation tibiale couplée.
- **Vêtements** : peau en deux modificateurs Armature comme le corps, import transactionnel (un échec ne laisse rien), pièces importées conservées par les tenues, matériaux propres à chaque pièce et accessoire, passe de dégagement Shrinkwrap « OUTSIDE ».
- **Accessoires** : la pose de l'utilisateur est sauvegardée puis restaurée au retrait.
- **Visage** : jawLeft/jawRight/jawForward (ARKit), couverture pondérée 0,56 (les 8 coefficients de regard reclassés « approchés » : yeux indépendants non pris en charge) ; la pose faciale lue contient maintenant le regard.
- **Foule** : masquage hors caméra (rendu), vêtements dans la foule, simulation à la cadence de la scène, refus clair d'effacer une foule dont une robe a le tissu actif.
- **Mesures** : la stature se mesure en pose de repos (le calibrage de stature n'est plus faussé par une pose).
- **Correctifs de flexion** : recalcul transactionnel (annuler ou une erreur conserve les correctifs d'avant), coupés par défaut, bouton d'activation.

## À savoir à la mise à jour
- Un squelette de version 1 est signalé *À configurer* : utilisez **Mettre à jour le squelette**.
- Les retargetings déjà faits ne sont pas rejoués.
- Dents et langue : **Mettre à jour le squelette** après un changement de morphologie.

## Limites connues
- Épaule levée vers l'avant au-delà de 135° : section de la peau trop faible (0,56 à 0,64 pour 0,85 visé), limite documentée.
- Coude de la veste : 8 à 13 mm de pénétration sans la passe de dégagement (coût 15 ms par pièce).
- Tissu : expérimental (Blender 5.2), coût 28 à 54 ms par robe et par image en direct ; cuire le cache.
- ARKit : 6 coefficients non couverts (fossettes, lèvres roulées, lèvre basse abaissée).
- Valgus du coude et rétroversion du bassin non traités.
- Le rig n'est pas livré comme export externe ; les vignettes et la bibliothèque d'animations sont celles de l'utilisateur.
