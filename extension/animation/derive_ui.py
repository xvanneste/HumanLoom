"""Interface des animations dérivées (lot L5) : panneau « Animations dérivées » (calques de deux actions de nos os, boucle sans raccord, étiquette « dérivée »)."""
import bpy
from bpy.props import BoolProperty, EnumProperty, IntProperty

from .. import human
from . import derive, retarget_bpy, skeleton


def _body(context):
    body = human.body_of(context.active_object)
    return body if human.is_native(body) else None


def _action_items(self, context):
    return [(a.name, a.name, "") for a in bpy.data.actions if a.get("hl_label") != derive.LABEL] or [("", "(aucune action)", "")]


def _derived_items(self, context):
    return [(a.name, a.name, "") for a in derive.derived_actions()] or [("", "(aucune)", "")]


class HUMANLOOM_OT_derive(bpy.types.Operator):
    bl_idname = "humanloom.derive_animation"
    bl_label = "Créer l'animation dérivée"
    bl_description = "Combine deux actions de NOS os : les os du groupe choisi prennent la pose (tenue ou étirée) de la superposition, le reste suit la base ; l'action créée est étiquetée « dérivée »"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        body = _body(context)
        return body is not None and bool(skeleton.rigs_of(body)) and len([a for a in bpy.data.actions if a.get("hl_label") != derive.LABEL]) >= 2

    def execute(self, context):
        wm = context.window_manager
        base, over = bpy.data.actions.get(wm.hl_derive_base), bpy.data.actions.get(wm.hl_derive_overlay)
        if base is None or over is None or base == over:
            self.report({"ERROR"}, "Choisissez deux actions différentes.")
            return {"CANCELLED"}
        rig = skeleton.rigs_of(_body(context))[0]
        try:
            action = derive.derive_action(rig, base, over, [wm.hl_derive_group], wm.hl_derive_mode, wm.hl_derive_hold, wm.hl_derive_loop, wm.hl_derive_blend)
        except ValueError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        retarget_bpy.add_to_nla(rig, action)
        self.report({"INFO"}, f"« {action.name} » ajoutée au NLA.")
        return {"FINISHED"}


class HUMANLOOM_PT_derive(bpy.types.Panel):
    bl_label = "Animations dérivées"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Humain"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return _body(context) is not None

    def draw(self, context):
        layout, wm = self.layout, context.window_manager
        layout.label(text="Calques de deux actions de nos os (déjà re-ciblées)", icon="INFO")
        layout.prop(wm, "hl_derive_base", text="Base")
        layout.prop(wm, "hl_derive_overlay", text="Superposition")
        layout.prop(wm, "hl_derive_group", text="Os repris")
        layout.prop(wm, "hl_derive_mode", text="Mode")
        if wm.hl_derive_mode == "figee":
            layout.prop(wm, "hl_derive_hold", text="Image tenue")
        row = layout.row(align=True)
        row.prop(wm, "hl_derive_loop", text="Boucle sans raccord")
        row.prop(wm, "hl_derive_blend", text="Fondu")
        layout.operator("humanloom.derive_animation", icon="NLA")
        derived = derive.derived_actions()
        if derived:
            box = layout.box()
            box.label(text=f"{len(derived)} action(s) dérivée(s)", icon="ACTION")
            for action in derived[:6]:
                box.label(text=action.name[:60])


CLASSES = (HUMANLOOM_OT_derive, HUMANLOOM_PT_derive)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    wm = bpy.types.WindowManager
    wm.hl_derive_base = EnumProperty(name="Base", items=_action_items)
    wm.hl_derive_overlay = EnumProperty(name="Superposition", items=_action_items)
    wm.hl_derive_group = EnumProperty(name="Os repris", items=[(g, g.replace("_", " ").replace(".", " "), "") for g in derive.GROUPS], default="bras.R")
    wm.hl_derive_mode = EnumProperty(name="Mode", items=[("figee", "Pose tenue", "Une image de la superposition est tenue (bras qui tient un objet)"), ("etiree", "Jouée, étirée sur la base", "La superposition est jouée sur la durée de la base")], default="figee")
    wm.hl_derive_hold = IntProperty(name="Image tenue", default=0, min=0)
    wm.hl_derive_loop = BoolProperty(name="Boucle sans raccord", default=True, description="Fondu de la fin sur le début (le clip perd les images du fondu)")
    wm.hl_derive_blend = IntProperty(name="Fondu", default=8, min=1, max=60)


def unregister():
    wm = bpy.types.WindowManager
    for name in ("hl_derive_base", "hl_derive_overlay", "hl_derive_group", "hl_derive_mode", "hl_derive_hold", "hl_derive_loop", "hl_derive_blend"):
        if hasattr(wm, name):
            delattr(wm, name)
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
