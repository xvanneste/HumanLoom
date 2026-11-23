"""Interface du rig corps (lot A2) : panneau « Squelette » et opérateurs Appliquer / Mettre à jour / Retirer. Aucune lecture de .blend à l'enregistrement."""
import bpy

from .. import human
from . import skeleton


def _body(context):
    body = human.body_of(context.active_object)
    return body if human.is_native(body) else None


class HUMANLOOM_OT_rig_install(bpy.types.Operator):
    bl_idname = "humanloom.rig_install"
    bl_label = "Appliquer le squelette"
    bl_description = "Crée le squelette du corps (81 os, dont `root` et la mâchoire `jaw`) d'après la morphologie actuelle, avec ses poids de peau"
    bl_options = {"REGISTER", "UNDO"}
    method: bpy.props.EnumProperty(name="Poids de peau", items=skeleton.WEIGHT_METHODS, default=skeleton.STORED)

    @classmethod
    def poll(cls, context):
        body = _body(context)
        return body is not None and not skeleton.rigs_of(body)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        body = _body(context)
        try:
            skeleton.install(body, self.method)
        except (ValueError, RuntimeError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        self.report({"INFO"}, "Squelette installé.")
        return {"FINISHED"}


class HUMANLOOM_OT_rig_update(bpy.types.Operator):
    bl_idname = "humanloom.rig_update"
    bl_label = "Mettre à jour le squelette"
    bl_description = "Repose les os d'après la morphologie actuelle ; les poids et les poses sont conservés"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        body = _body(context)
        return body is not None and len(skeleton.rigs_of(body)) == 1

    def execute(self, context):
        try:
            skeleton.update(_body(context), dental=True)
        except (ValueError, RuntimeError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        self.report({"INFO"}, "Squelette mis à jour.")
        return {"FINISHED"}


class HUMANLOOM_OT_rig_remove(bpy.types.Operator):
    bl_idname = "humanloom.rig_remove"
    bl_label = "Retirer le squelette"
    bl_description = "Supprime l'armature, ses groupes de poids et son modificateur"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        body = _body(context)
        return body is not None and bool(skeleton.rigs_of(body))

    def execute(self, context):
        count = skeleton.remove(_body(context))
        self.report({"INFO"}, f"Squelette retiré ({count} éléments).")
        return {"FINISHED"}


class HUMANLOOM_PT_rig(bpy.types.Panel):
    bl_label = "Squelette du corps"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Humain"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return _body(context) is not None

    def draw(self, context):
        layout = self.layout
        body = _body(context)
        state, problems = skeleton.status(body)
        layout.label(text=skeleton.LABELS[state], icon={"INSTALLED": "CHECKMARK", "NOT_INSTALLED": "BONE_DATA", "OUTDATED": "TIME", "NEEDS_CONFIGURATION": "ERROR"}[state])
        for problem in problems[:4]:
            layout.label(text=problem[:70])
        row = layout.row(align=True)
        row.operator("humanloom.rig_install", icon="ARMATURE_DATA")
        row.operator("humanloom.rig_update", icon="FILE_REFRESH")
        layout.operator("humanloom.rig_remove", icon="TRASH")


CLASSES = (HUMANLOOM_OT_rig_install, HUMANLOOM_OT_rig_update, HUMANLOOM_OT_rig_remove, HUMANLOOM_PT_rig)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
