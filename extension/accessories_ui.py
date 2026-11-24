"""Interface des accessoires (lot V3) : panneau « Accessoires » (sacs, téléphone, parapluies, lunettes) et préhension de la main."""
import bpy

from . import accessories, human
from .animation import skeleton


def _body(context):
    body = human.body_of(context.active_object)
    return body if human.is_native(body) else None


class HUMANLOOM_OT_accessory_add(bpy.types.Operator):
    bl_idname = "humanloom.accessory_add"
    bl_label = "Ajouter l'accessoire"
    bl_description = "Ajoute l'accessoire à son point d'attache (la main se referme sur la poignée pour les objets tenus)"
    bl_options = {"REGISTER", "UNDO"}
    piece: bpy.props.StringProperty()

    @classmethod
    def poll(cls, context):
        body = _body(context)
        return body is not None and bool(skeleton.rigs_of(body))

    def execute(self, context):
        try:
            accessories.add_accessory(_body(context), self.piece)
        except ValueError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}


class HUMANLOOM_OT_accessory_remove(bpy.types.Operator):
    bl_idname = "humanloom.accessory_remove"
    bl_label = "Retirer l'accessoire"
    bl_options = {"REGISTER", "UNDO"}
    piece: bpy.props.StringProperty()

    @classmethod
    def poll(cls, context):
        return _body(context) is not None

    def execute(self, context):
        for obj in accessories.accessories_of(_body(context)):
            if obj[accessories.MARKER] == self.piece:
                accessories.remove_accessory(obj)
        return {"FINISHED"}


class HUMANLOOM_OT_grasp(bpy.types.Operator):
    bl_idname = "humanloom.grasp"
    bl_label = "Préhension de la main"
    bl_description = "Ferme ou ouvre une main selon une préhension (poignée, objet plat)"
    bl_options = {"REGISTER", "UNDO"}
    side: bpy.props.EnumProperty(items=[("L", "Gauche", ""), ("R", "Droite", "")], name="Main", default="R")
    pose: bpy.props.EnumProperty(items=[(k, k, "") for k in accessories.GRASPS] + [("ouvrir", "Ouvrir la main", "")], name="Préhension", default="poignee")
    amount: bpy.props.FloatProperty(name="Fermeture", default=1.0, min=0.0, max=1.0)

    @classmethod
    def poll(cls, context):
        body = _body(context)
        return body is not None and bool(skeleton.rigs_of(body))

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        body = _body(context)
        if self.pose == "ouvrir":
            accessories.release_grasp(body, self.side)
        else:
            accessories.apply_grasp(body, self.side, self.pose, self.amount)
        return {"FINISHED"}


class HUMANLOOM_PT_accessories(bpy.types.Panel):
    bl_label = "Accessoires"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Humain"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return _body(context) is not None

    def draw(self, context):
        layout, body = self.layout, _body(context)
        if not skeleton.rigs_of(body):
            layout.label(text="Posez d'abord le squelette.", icon="INFO")
            return
        worn = {o[accessories.MARKER] for o in accessories.accessories_of(body)}
        categories = {}
        for key, definition in accessories.ACCESSORIES.items():
            categories.setdefault(definition["categorie"], []).append(key)
        for category, keys in categories.items():
            box = layout.box()
            box.label(text=category)
            for key in keys:
                label = accessories.ACCESSORIES[key]["label"]
                if key in worn:
                    box.operator("humanloom.accessory_remove", text=label, icon="CHECKBOX_HLT").piece = key
                else:
                    box.operator("humanloom.accessory_add", text=label, icon="CHECKBOX_DEHLT").piece = key
        layout.operator("humanloom.grasp", icon="HAND")


CLASSES = (HUMANLOOM_OT_accessory_add, HUMANLOOM_OT_accessory_remove, HUMANLOOM_OT_grasp, HUMANLOOM_PT_accessories)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
