"""Interface du rig corps (lot A2) : panneau « Squelette » et opérateurs Appliquer / Mettre à jour / Retirer. Aucune lecture de .blend à l'enregistrement."""
import bpy

from .. import human
from . import correctives, skeleton


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


class HUMANLOOM_OT_correctives_toggle(bpy.types.Operator):
    bl_idname = "humanloom.correctives_toggle"
    bl_label = "Correctifs de flexion"
    bl_description = ("Active ou coupe les formes correctives du coude et du genou (défaut : coupées ; le coude et le genou sont corrects sans elles, les correctifs peuvent former des rides). Le recalcul reste disponible")
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        body = _body(context)
        return body is not None and correctives.installed(body)

    def execute(self, context):
        body = _body(context)
        state = not correctives.enabled(body)
        correctives.set_enabled(body, state)
        self.report({"INFO"}, "Correctifs de flexion " + ("activés." if state else "coupés."))
        return {"FINISHED"}


class HUMANLOOM_OT_correctives_rebuild(bpy.types.Operator):
    bl_idname = "humanloom.correctives_rebuild"
    bl_label = "Recalculer les correctifs de flexion"
    bl_description = ("Recalcule les formes correctives du coude et du genou sur la morphologie ACTUELLE (quelques minutes ; la barre de progression avance angle par angle ; Échap annule et remet les correctifs génériques). "
                      "Les correctifs génériques livrés sont calculés pour le corps par défaut ; recalculés pour une morphologie, ils réduisent les plis du creux de 80 à 90 % (mesuré)")
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        body = _body(context)
        return body is not None and bool(skeleton.rigs_of(body))

    def invoke(self, context, event):
        body = _body(context)
        self._body, self._rig = body, skeleton.rigs_of(body)[0]
        self._steps = correctives.rebuild_steps(self._body, self._rig)
        wm = context.window_manager
        wm.progress_begin(0, 100)
        self._timer = wm.event_timer_add(0.05, window=context.window)
        wm.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def _end(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        wm.progress_end()

    def modal(self, context, event):
        if event.type == "ESC":
            self._steps.close()  # le « finally » du générateur remet la pose et retire la clé temporaire
            if not correctives.installed(self._body):
                correctives.install(self._body, self._rig)
            self._end(context)
            self.report({"WARNING"}, "Recalcul annulé : correctifs génériques remis.")
            return {"CANCELLED"}
        if event.type != "TIMER":
            return {"RUNNING_MODAL"}
        try:
            label, done, total = next(self._steps)
            context.window_manager.progress_update(100.0 * done / max(total, 1))
            context.workspace.status_text_set(f"Correctifs de flexion : {done}/{total} ({label})")
            return {"RUNNING_MODAL"}
        except StopIteration:
            context.workspace.status_text_set(None)
            self._end(context)
            self.report({"INFO"}, "Correctifs de flexion recalculés pour cette morphologie.")
            return {"FINISHED"}


class HUMANLOOM_OT_gaze_set(bpy.types.Operator):
    bl_idname = "humanloom.gaze_set"
    bl_label = "Orienter le regard"
    bl_description = "Oriente les yeux par la pose des os de regard (horizontal, vertical, convergence en degrés)"
    bl_options = {"REGISTER", "UNDO"}
    yaw: bpy.props.FloatProperty(name="Horizontal", default=0.0, min=-45.0, max=45.0, description="Positif : vers la gauche du personnage (+x)")
    pitch: bpy.props.FloatProperty(name="Vertical", default=0.0, min=-35.0, max=35.0, description="Positif : vers le haut")
    convergence: bpy.props.FloatProperty(name="Convergence", default=0.0, min=0.0, max=30.0, description="Angle total entre les axes des deux yeux")

    @classmethod
    def poll(cls, context):
        body = _body(context)
        return body is not None and bool(skeleton.rigs_of(body))

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        body = _body(context)
        if not skeleton.set_gaze(body, self.yaw, self.pitch, self.convergence):
            self.report({"ERROR"}, "Ce squelette n'a pas d'os de regard : mettez-le à jour.")
            return {"CANCELLED"}
        return {"FINISHED"}


class HUMANLOOM_OT_gaze_track(bpy.types.Operator):
    bl_idname = "humanloom.gaze_track"
    bl_label = "Suivre un objet du regard"
    bl_description = "Les yeux suivent l'objet sélectionné (autre que le corps) ; la convergence vient de sa distance"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        body = _body(context)
        return body is not None and bool(skeleton.rigs_of(body)) and len([o for o in context.selected_objects if o != body and o.type != "ARMATURE"]) >= 1

    def execute(self, context):
        body = _body(context)
        targets = [o for o in context.selected_objects if o != body and o.type != "ARMATURE"]
        if not skeleton.track_gaze(body, targets[0]):
            self.report({"ERROR"}, "Ce squelette n'a pas d'os de regard : mettez-le à jour.")
            return {"CANCELLED"}
        return {"FINISHED"}


class HUMANLOOM_OT_gaze_clear(bpy.types.Operator):
    bl_idname = "humanloom.gaze_clear"
    bl_label = "Regard droit devant"
    bl_description = "Arrête le suivi de cible et remet les yeux droit devant"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        body = _body(context)
        return body is not None and bool(skeleton.rigs_of(body))

    def execute(self, context):
        skeleton.clear_gaze(_body(context))
        return {"FINISHED"}


class HUMANLOOM_OT_lid_follow(bpy.types.Operator):
    bl_idname = "humanloom.lid_follow"
    bl_label = "Paupières qui suivent le regard"
    bl_description = "Active ou désactive le suivi : les commandes Clignement et Yeux grands ouverts sont alors pilotées par la rotation verticale des yeux (non réglables à la main)"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        body = _body(context)
        return body is not None and bool(skeleton.rigs_of(body))

    def execute(self, context):
        body = _body(context)
        if skeleton.lid_follow_enabled(body):
            skeleton.detach_lid_follow(body)
        elif not skeleton.attach_lid_follow(body):
            self.report({"ERROR"}, "Ce squelette n'a pas d'os de regard : mettez-le à jour.")
            return {"CANCELLED"}
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
        if state != skeleton.NOT_INSTALLED:
            status = correctives.status(body)
            text = {"absent": "Correctifs de flexion : absents", "generique": "Correctifs de flexion : génériques (corps par défaut)",
                    "a_jour": "Correctifs de flexion : recalculés pour ce corps", "obsolete": "Correctifs de flexion : à recalculer (morphologie changée)"}[status]
            layout.label(text=text, icon="CHECKMARK" if status == "a_jour" else "INFO")
            if correctives.installed(body):
                layout.operator("humanloom.correctives_toggle", depress=correctives.enabled(body), icon="MOD_SHAPEKEY")
            layout.operator("humanloom.correctives_rebuild", icon="FILE_REFRESH")
        if state != skeleton.NOT_INSTALLED:
            box = layout.box()
            box.label(text="Regard", icon="HIDE_OFF")
            row = box.row(align=True)
            row.operator("humanloom.gaze_set", text="Orienter")
            row.operator("humanloom.gaze_track", text="Suivre l'objet")
            row.operator("humanloom.gaze_clear", text="Droit")
            box.operator("humanloom.lid_follow", depress=skeleton.lid_follow_enabled(_body(context)))


CLASSES = (HUMANLOOM_OT_rig_install, HUMANLOOM_OT_rig_update, HUMANLOOM_OT_rig_remove, HUMANLOOM_OT_correctives_toggle, HUMANLOOM_OT_correctives_rebuild, HUMANLOOM_OT_gaze_set, HUMANLOOM_OT_gaze_track, HUMANLOOM_OT_gaze_clear, HUMANLOOM_OT_lid_follow, HUMANLOOM_PT_rig)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
