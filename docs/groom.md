# Groom : état et points d'entrée

Les sources expérimentales sont versionnées dans `tools/`. La branche `codex/groom` part de la même base complète que la branche de modélisation. Les fichiers `.blend` générés et leurs rapports restent dans `validation/`, hors Git.

## Cheveux natifs

- `tools/hair_prototype20.py` : construction des guides, surface d'attache et pile de modificateurs.
- `tools/build_hair20.py` : génération de la scène et des premiers rendus.
- `tools/validate_hair20.py`, `tools/validate_dense_hair20.py`, `tools/reopen_hair20.py` : contrôles des guides, de l'interpolation et de la réouverture.

Le prototype utilise des Hair Curves éditables et les groupes natifs Blender 5.2, avec attache sur la surface, UV de racine, interpolation et Hair Dynamics. L'implantation, la stabilité entre subdivisions et les collisions complètes restent à finaliser. Aucun système de particules historique n'est utilisé pour ce prototype.

## Nature de fibre

- `tools/hair_nature21.py` : forme de repos et réglages de nature de fibre.
- `tools/build_nature21.py`, `tools/check_nature21.py`, `tools/render_fibers21.py` : scène comparative et contrôles.

`build_nature21.py` attend la scène produite par `build_hair20.py`. La nature des fibres est un modèle artistique documenté dans `Recherche-scientifique-cheveux.md`, pas une mesure biologique individuelle.

## Physique

- `tools/hair_physics22.py` : configuration du banc de physique.
- `tools/build_physics22.py`, `tools/validate_physics_profile22.py`, `tools/finalize_physics22.py` : construction, vérification et préparation de la scène.
- `tools/diagnose_xpbd22.py`, `tools/inspect_bake22.py` : diagnostics du solveur et du cache.

Le banc teste une configuration limitée de guides ; il ne vaut pas validation d'une coiffure dense complète. Consulter les résultats locaux dans `validation/physique-cheveux-22/` lorsqu'ils sont disponibles.

## Exécution isolée

Depuis la racine du dépôt, avec Blender 5.2 installé :

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --factory-startup --offline-mode --threads 4 --python-exit-code 1 --python tools/build_hair20.py
```

Lire chaque script avant exécution et adapter ses éventuels chemins locaux. Les constructeurs travaillent dans une scène isolée ; ne pas les lancer dans une scène utilisateur à conserver.

Les sourcils, la barbe, la moustache et les poils corporels restent à développer et à intégrer à partir de masques et de directions propres à chaque région. L'intégration de ces prototypes au panneau de l'extension n'est pas encore livrée.
