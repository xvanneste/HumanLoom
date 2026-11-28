"""Interface du moteur de foule (lots C1/C2) : panneau « Foule » et opérateurs. La foule est figée : seuls « Régénérer » et « Effacer » la modifient."""
import bpy

from . import crowd, human


class HUMANLOOM_OT_crowd_generate(bpy.types.Operator):
    bl_idname = "humanloom.crowd_generate"
    bl_label = "Générer la foule"
    bl_description = "Crée une foule figée (tirage à graine) : personnages, squelettes, trajets, animations de comportement. Une foule existante n'est pas modifiée"
    bl_options = {"REGISTER", "UNDO"}
    count: bpy.props.IntProperty(name="Personnages", default=20, min=1, max=300)
    seed: bpy.props.IntProperty(name="Graine", default=1, min=0)
    frames: bpy.props.IntProperty(name="Images", default=240, min=24, max=3000)

    @classmethod
    def poll(cls, context):
        return not context.scene.get(crowd.KEY)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        spec = crowd.default_spec(self.count, self.seed)
        spec["frames"] = self.frames
        try:
            summary = crowd.generate(context, spec)
        except crowd.CleanupError as error:
            self.report({"WARNING"}, str(error))
            return {"FINISHED"}
        except Exception as error:
            self.report({"ERROR"}, f"Génération de la foule interrompue : {error}")
            return {"CANCELLED"}
        self.report({"INFO"}, f"{summary['personnages']} personnages ; distance minimale de diversité {summary['diversite'].get('distance_min', 0):.2f}.")
        if summary.get("diversite_non_garantie"):
            self.report({"WARNING"}, f"Diversité non garantie pour {len(summary['diversite_non_garantie'])} personnage(s) (aucun tirage assez différent en 50 essais) : élargissez les plages ou réduisez la distance minimale.")
        return {"FINISHED"}


class HUMANLOOM_OT_crowd_regenerate_member(bpy.types.Operator):
    bl_idname = "humanloom.crowd_regenerate_member"
    bl_label = "Régénérer ce personnage"
    bl_description = "Nouveau tirage du personnage actif ; les autres ne changent pas"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        body = human.body_of(context.active_object)
        return body is not None and body.get(crowd.OBJECT_KEY) is not None and bool(context.scene.get(crowd.KEY))

    def execute(self, context):
        try:
            crowd.regenerate_member(context, int(human.body_of(context.active_object)[crowd.OBJECT_KEY]))
        except crowd.CleanupError as error:
            self.report({"WARNING"}, str(error))
            return {"FINISHED"}
        except Exception as error:
            self.report({"ERROR"}, f"Régénération du personnage interrompue : {error}")
            return {"CANCELLED"}
        return {"FINISHED"}


class HUMANLOOM_OT_crowd_regenerate_all(bpy.types.Operator):
    bl_idname = "humanloom.crowd_regenerate_all"
    bl_label = "Régénérer toute la foule"
    bl_description = "Remplace TOUTE la foule par un nouveau tirage (demande explicite)"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return bool(context.scene.get(crowd.KEY))

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        try:
            crowd.regenerate_all(context)
        except crowd.CleanupError as error:
            self.report({"WARNING"}, str(error))
            return {"FINISHED"}
        except Exception as error:
            self.report({"ERROR"}, f"Régénération de la foule interrompue : {error}")
            return {"CANCELLED"}
        return {"FINISHED"}


class HUMANLOOM_OT_crowd_lod(bpy.types.Operator):
    bl_idname = "humanloom.crowd_lod"
    bl_label = "Niveaux de détail selon la caméra"
    bl_description = "Réduit le détail des personnages éloignés (subdivision coupée, dents masquées, cage figée, décimation) : irréversible sans régénération"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return bool(context.scene.get(crowd.KEY)) and context.scene.camera is not None

    def execute(self, context):
        try:
            levels = crowd.auto_lod(context.scene)
        except ValueError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}

        self.report({"INFO"}, "Niveaux : " + ", ".join(f"{k}→{v}" for k, v in sorted(levels.items())[:12]))
        return {"FINISHED"}


class HUMANLOOM_OT_crowd_cull(bpy.types.Operator):
    bl_idname = "humanloom.crowd_cull"
    bl_label = "Masquer hors caméra"
    bl_description = ("Masque (clés de visibilité au rendu et dans la vue) les personnages entièrement hors du champ de la caméra, image par image (caméra animée prise en compte). "
                      "Réduit surtout le TEMPS ET LA MÉMOIRE DU RENDU ; le coût de la vue 3D ne baisse pas avec une visibilité animée. À refaire si la caméra ou les trajets changent")
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return bool(context.scene.get(crowd.KEY)) and context.scene.camera is not None

    def execute(self, context):
        try:
            summary = crowd.cull(context.scene)
        except ValueError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        self.report({"INFO"}, f"{summary['masques_par_image_moyen']:.1f} personnages masqués en moyenne par image ; {summary['toujours_visibles']} toujours visibles, {len(summary['jamais_visibles'])} jamais visibles")
        return {"FINISHED"}


class HUMANLOOM_OT_crowd_uncull(bpy.types.Operator):
    bl_idname = "humanloom.crowd_uncull"
    bl_label = "Tout afficher"
    bl_description = "Retire les clés de visibilité de « Masquer hors caméra » : tous les personnages redeviennent visibles"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return bool(context.scene.get(crowd.KEY)) and crowd.CULL_KEY in context.scene

    def execute(self, context):
        crowd.uncull(context.scene)
        return {"FINISHED"}


class HUMANLOOM_OT_crowd_clear(bpy.types.Operator):
    bl_idname = "humanloom.crowd_clear"
    bl_label = "Effacer la foule"
    bl_description = "Supprime tous les personnages de la foule"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return bool(context.scene.get(crowd.KEY))

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        try:
            crowd.clear(context.scene)
        except crowd.CleanupError as error:
            self.report({"WARNING"}, str(error))
        except Exception as error:
            self.report({"ERROR"}, f"Effacement de la foule interrompu : {error}")
            return {"CANCELLED"}
        return {"FINISHED"}


class HUMANLOOM_PT_crowd(bpy.types.Panel):
    bl_label = "Foule"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Humain"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        loaded = crowd.load(context.scene)
        if loaded is None:
            layout.label(text="Aucune foule.", icon="INFO")
            layout.operator("humanloom.crowd_generate", icon="COMMUNITY")
            return
        spec, members = loaded
        layout.label(text=f"{len(members)} personnages figés (graine {spec['seed']}, régénération {spec.get('regeneration', 0)})", icon="CHECKMARK")
        counts = {}
        for member in members:
            counts[member["behavior"]] = counts.get(member["behavior"], 0) + 1
        layout.label(text=" ; ".join(f"{k} {v}" for k, v in sorted(counts.items())))
        layout.operator("humanloom.crowd_regenerate_member", icon="FILE_REFRESH")
        layout.operator("humanloom.crowd_lod", icon="MOD_DECIM")
        row = layout.row(align=True)
        row.operator("humanloom.crowd_cull", icon="HIDE_ON")
        row.operator("humanloom.crowd_uncull", icon="HIDE_OFF")
        row = layout.row(align=True)
        row.operator("humanloom.crowd_regenerate_all", icon="FILE_REFRESH")
        row.operator("humanloom.crowd_clear", icon="TRASH")


CLASSES = (HUMANLOOM_OT_crowd_generate, HUMANLOOM_OT_crowd_regenerate_member, HUMANLOOM_OT_crowd_regenerate_all, HUMANLOOM_OT_crowd_lod, HUMANLOOM_OT_crowd_cull, HUMANLOOM_OT_crowd_uncull, HUMANLOOM_OT_crowd_clear, HUMANLOOM_PT_crowd)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
