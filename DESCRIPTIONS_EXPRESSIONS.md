# DESCRIPTIONS_EXPRESSIONS — cahier des charges anatomique des expressions (pour validation à l'œil)

Date : 2026-11-24. Rédigé par l'analyste dans le même format que la description du sourire donnée par l'utilisateur. Chaque expression est décrite par ses mouvements anatomiques, puis par les unités d'action FACS (Action Units, AU) du prototype de la littérature. **Les AU et leur combinaison viennent du FACS (Ekman et Friesen, 1978 ; mise à jour Ekman, Friesen et Hager, 2002) et des prototypes émotionnels d'Ekman (EMFACS)** ; ils sont rappelés de mémoire et **non revérifiés à la page** dans cette session : à confirmer contre la source avant de les citer comme vérifiés. Le FACS décrit quels muscles bougent, **pas de quelle amplitude** : toute amplitude en mm est « non vérifiée » sauf mention contraire dans `CONCEPTION_EXPRESSIONS.md`.

Règles communes à toutes les expressions (critères de validation) :
- mouvement progressif et synchronisé : un seul curseur d'intensité, courbe commune ;
- conservation approximative du volume des tissus mous (ce qui monte ici gonfle ou plisse ailleurs) ;
- le menton et la mandibule ne se déforment pas comme des tissus mous (os en dessous) : seule la lèvre inférieure et le sillon labio-mentonnier bougent ;
- aucune face retournée, pas d'interpénétration des lèvres, des paupières ni des dents ;
- un mouvement coordonné de tout le visage, jamais la bouche seule.

## 1. Joie (sourire de Duchenne) — AU6 + AU12 (± AU25/26 si rire)
Voir la description détaillée de l'utilisateur : commissures tirées en diagonale vers l'extérieur et le haut ; joues remontées et bombées sur les pommettes ; paupières inférieures poussées vers le haut (yeux réduits) ; sillons nasogéniens creusés ; pattes d'oie ; volume conservé. Rire : même base, plus ouverture de la mâchoire (AU25/26), lèvre inférieure abaissée (AU16), dents du haut et du bas visibles.

## 2. Surprise — AU1 + AU2 + AU5 + AU26
Les sourcils sont relevés dans leur ensemble (partie interne AU1 et partie externe AU2), arqués et plus hauts ; la peau du front se plisse en rides horizontales ; les paupières supérieures se relèvent et les yeux s'ouvrent grand, laissant voir la sclère au-dessus de l'iris ; la mâchoire tombe sans effort (AU26) et la bouche s'ouvre de façon détendue, lèvres non tendues, commissures non étirées. Les joues ne remontent pas, les sillons nasogéniens restent neutres.

## 3. Tristesse — AU1 + AU4 + AU15 (± AU17)
Les extrémités internes des sourcils sont relevées et rapprochées (AU1 avec AU4), ce qui forme un triangle oblique : la partie interne monte, la partie externe reste basse ; le front se plisse au centre ; la paupière supérieure s'affaisse légèrement ; les commissures des lèvres sont tirées vers le bas (AU15) ; le menton se relève et la lèvre inférieure est poussée vers le haut (AU17), avec un menton plissé ; le regard est souvent légèrement baissé. Pas de tension des narines.

## 4. Colère — AU4 + AU5 + AU7 + AU23
Les sourcils sont abaissés et rapprochés (AU4), avec deux rides verticales entre eux (glabelle) ; les paupières supérieures sont relevées (AU5, regard fixe) tandis que les paupières inférieures se tendent (AU7) : l'œil paraît dur ; les lèvres sont serrées et amincies (AU23, ± AU24), les commissures légèrement abaissées ; la mâchoire peut avancer ; les narines peuvent se dilater. Variante bouche ouverte et dents serrées (AU10/25) pour la colère criée.

## 5. Dégoût — AU9 + AU15 + AU17 (table de la page Wikipédia « FACS », source secondaire ; AU10 = variante)
Le nez se plisse : la racine du nez est tirée vers le bas (AU9) et des rides apparaissent sur le dos et les côtés du nez ; la lèvre supérieure est relevée (AU10), plus au centre que sur les côtés, ce qui découvre éventuellement les dents du haut ; les joues sont poussées vers le haut, le sillon nasogénien est profond et remonte vers la narine ; les sourcils s'abaissent (AU4 faible) ; la lèvre inférieure peut être abaissée ou poussée vers le haut (AU15/17). Contrairement au sourire, les commissures ne sont pas tirées vers l'extérieur.

## 6. Peur — AU1 + AU2 + AU4 + AU5 + AU7 + AU20 + AU26 (AU7 ajouté d'après la table de la page Wikipédia « FACS », source secondaire)
Les sourcils sont relevés **et** rapprochés (AU1+2 avec AU4) : ils restent droits ou à peine arqués, plus rapprochés qu'en surprise, avec des rides au centre du front ; les paupières supérieures sont relevées au maximum et les inférieures tendues : la sclère est visible au-dessus de l'iris ; la bouche s'ouvre légèrement ; les lèvres sont étirées horizontalement vers les oreilles (AU20), commissures tirées en arrière **sans** remonter, lèvre inférieure tendue. Se distingue de la surprise par la tension (étirement horizontal, sourcils rapprochés) et du sourire par l'absence de remontée des joues.

## 7. Mépris (à ajouter) — AU12 unilatéral + AU14 unilatéral
Une seule commissure est tirée et légèrement relevée en un demi-sourire, avec une fossette ou un durcissement du coin de la bouche (AU14, buccinateur) ; le reste du visage reste presque neutre ; asymétrie nette gauche/droite. Pas de plissement des yeux (pas d'AU6).

## 8. Clignement — AU45
Les deux paupières supérieures descendent jusqu'à toucher les inférieures, puis remontent ; l'œil se ferme complètement (limite actuelle du modèle : ≈ 73 % de fermeture) ; la fermeture est plus rapide que la réouverture ; le globe tourne légèrement vers le haut (phénomène de Bell). Aucune autre partie du visage ne bouge.

## 9. Neutre
Visage au repos, muscles détendus, lèvres jointes sans pression, paupières à mi-hauteur de l'iris, sourcils à leur position de repos : référence de toutes les autres poses.

## Utilisation pour la validation
Pour chaque expression, l'utilisateur compare la planche aux points listés ci-dessus. Écarts à signaler dans le rapport : tout élément listé et absent du rendu, et tout mouvement présent qui n'est pas listé. Sources et amplitudes : voir `CONCEPTION_EXPRESSIONS.md` ; ce qui n'y figure pas avec sa source est « non vérifié ».

## Vérification des AU contre une source (ajout de la session de modélisation, 24 nov. 2026)
Source lue : page Wikipédia « Facial Action Coding System » (source SECONDAIRE ; le manuel FACS lui-même n'a pas été lu). Noms et muscles confirmés : AU1 inner brow raiser (frontalis pars medialis), AU2 outer brow raiser (frontalis pars lateralis), AU4 brow lowerer (corrugator, depressor glabellae/supercilii), AU5 upper lid raiser (levator palpebrae), AU6 cheek raiser (orbicularis oculi pars orbitalis), AU7 lid tightener (orbicularis pars palpebralis), AU9 nose wrinkler, AU10 upper lip raiser, AU11 nasolabial deepener (zygomaticus minor), AU12 lip corner puller (zygomaticus major), AU14 dimpler (buccinator), AU15 lip corner depressor, AU16 lower lip depressor, AU17 chin raiser (mentalis), AU20 lip stretcher (risorius + platysma), AU23/24 lip tightener / pressor, AU25 lips part, AU26 jaw drop, AU45 blink.
Table des émotions de la page (exemples EMFACS-7, Friesen & Ekman 1983, manuscrit non publié, d'après la page) : joie 6+12 ; tristesse 1+4+15 ; surprise 1+2+5B+26 ; peur 1+2+4+5+7+20+26 ; colère 4+5+7+23 ; dégoût 9+15+17 ; mépris R12A+R14A.
Écarts avec le présent document : **peur** : la page ajoute AU7 (paupières inférieures tendues) — conforme au texte de la section 6 ; **dégoût** : la page donne 9+15+17 (la variante « 9 ou 10 » du document n'est pas dans la page) ; **mépris** : R12A+R14A, côté droit et intensité A (faible) dans la page — réalisé côté +x du personnage, intensité 0,5 ; **clignement, neutre** : hors table de la page. Les descriptions anatomiques détaillées (rides, regard baissé, narines…) ne figurent pas dans la page : elles restent « non vérifiées ».

## Revue des présets contre ce document (24 nov. 2026)
Légende : ✔ présent ; ✚ ajouté dans cette revue ; ✘ non réalisable pour l'instant.
- **Joie** : tout ✔ (commande unique `smile_duchenne`, voir CONCEPTION_L1.md) ; mouvement non décrit présent : la lèvre supérieure ne bouge pas (sourire fermé), RAS.
- **Surprise** : sourcils ✔, yeux grands ouverts ✔, mâchoire ✔, joues neutres ✔ ; ✚ rides horizontales du front (`forehead_wrinkles`) ; sclère « visible au-dessus de l'iris » : dépend de la fente palpébrale (pas mesuré) → à valider à l'œil.
- **Tristesse** : coins internes relevés/rapprochés ✔, partie externe basse ✔ (brow_down 0,6), commissures vers le bas ✔, menton relevé ✔ ; ✚ plis au centre du front, ✚ rides de glabelle, ✚ paupières supérieures affaissées (blink 0,25), ✚ regard baissé (8°). Mouvement présent non décrit : brow_down 0,6 abaisse aussi le milieu des sourcils (cohérent avec AU4).
- **Colère** : sourcils bas et rapprochés ✔, paupières supérieures levées ✔ et inférieures tendues ✔ (eye_squint 0,5), lèvres serrées ✔ ; ✚ rides verticales de la glabelle, ✚ commissures légèrement abaissées, ✚ narines dilatées ; ✘ mâchoire qui avance (pas de translation de la mandibule dans le rig, `jawForward` non couvert) ; variante bouche ouverte non faite.
- **Dégoût** : nez plissé ✔, lèvre supérieure relevée ✔, menton relevé ✔ ; ✚ plis sur la racine et le dos du nez, ✚ joues poussées vers le haut (cheek_raise 0,5), ✚ sillon naso-génien creusé ; commissures non tirées vers l'extérieur ✔. Lèvre inférieure abaissée (AU16) optionnelle : non ajoutée.
- **Peur** : sourcils relevés et rapprochés ✔, yeux grands ouverts ✔, bouche entrouverte ✔, lèvres étirées ✔, sans remontée des joues ✔ ; ✚ paupières inférieures tendues (eye_squint 0,3, AU7 de la page), ✚ rides du front et de la glabelle, ✚ narines ; lèvre inférieure « tendue » : non distinguée de `lip_stretch`.
- **Mépris** : ✚ ajouté (`mepris` : `smile_L` 0,5 + `dimpler_L`, côté +x seulement, pas d'AU6) ; l'asymétrie est nette sur les planches ; le côté droit reste neutre.
- **Clignement** : fermeture ≈ 73 % (limite connue), pas de phénomène de Bell (rotation des yeux au clignement non modélisée), fermeture plus rapide que la réouverture : non gérée (pas de courbe temporelle asymétrique).
- **Règles communes** : curseur unique par expression = seul le sourire l'a (`smile_duchenne`) ; les autres émotions se règlent par l'intensité globale d'un préset (planches 0/50/100 %) ou par leurs commandes ; menton/mandibule stables ✔ (F6) ; 0 face retournée ✔ (F2).
