"""Interface du mapping (lot A2b) : choisir une armature source, appairer automatiquement, corriger à la main, enregistrer ou charger un profil, lire le rapport.

Le mapping relie les os d'une armature SOURCE aux os de NOTRE rig (`skeleton.py`). Rien n'est appliqué à une animation ici (lot A3).
Aucune lecture de .blend à l'enregistrement.
"""
from pathlib import Path

import bpy
from bpy.props import CollectionProperty, FloatProperty, IntProperty, PointerProperty, StringProperty
from bpy_extras.io_utils import ImportHelper

from .. import human
from . import mapping, skeleton, ui

_state = {"report": None, "message": "", "problems": []}


def _is_armature(self, obj):
    return obj.type == "ARMATURE" and not obj.get(skeleton.MARKER)


class HL_MapRow(bpy.types.PropertyGroup):
    target: StringProperty()
    source: StringProperty(description="Os de la source relié à cet os (vide : aucun)")
    score: FloatProperty()
    method: StringProperty()


def _rig(context):
    body = human.body_of(context.active_object)
    rigs = skeleton.rigs_of(body) if human.is_native(body) else []
    return rigs[0] if len(rigs) == 1 else None


def _source_skeleton(context):
    source = context.window_manager.hl_map_source
    return mapping.from_armature(source) if source is not None else None


def _rows_as_mapping(wm):
    return {row.target: row.source for row in wm.hl_map_rows if row.source}


class HUMANLOOM_OT_mapping_auto(bpy.types.Operator):
    bl_idname = "humanloom.mapping_auto"
    bl_label = "Appairer automatiquement"
    bl_description = "Appariement par les noms, puis la structure, puis la géométrie ; chaque os reçoit un score de confiance"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return _rig(context) is not None and context.window_manager.hl_map_source is not None

    def execute(self, context):
        wm = context.window_manager
        target = mapping.from_armature(_rig(context))
        source = _source_skeleton(context)
        pairs, report = mapping.auto_map(target, source)
        wm.hl_map_rows.clear()
        for name in target.names:
            row = wm.hl_map_rows.add()
            row.target = name
            if name in pairs:
                row.source, row.score, row.method = pairs[name].source, pairs[name].score, pairs[name].method
        _state.update(report=report, message="", problems=[])
        self.report({"INFO"}, f"{len(pairs)} os appariés, {len(report.unmapped_targets)} sans source, {len(report.low_confidence)} à vérifier.")
        return {"FINISHED"}


class HUMANLOOM_OT_mapping_clear_row(bpy.types.Operator):
    bl_idname = "humanloom.mapping_clear_row"
    bl_label = "Effacer cet appariement"
    bl_options = {"INTERNAL", "UNDO"}
    index: IntProperty()

    def execute(self, context):
        row = context.window_manager.hl_map_rows[self.index]
        row.source, row.score, row.method = "", 0.0, "manuel"
        return {"FINISHED"}


class HUMANLOOM_OT_mapping_save(bpy.types.Operator):
    bl_idname = "humanloom.mapping_save"
    bl_label = "Enregistrer le profil"
    bl_description = "Enregistre le mapping actuel dans le dossier utilisateur de la bibliothèque (profiles/)"

    @classmethod
    def poll(cls, context):
        return context.window_manager.hl_map_source is not None and len(context.window_manager.hl_map_rows) > 0

    def execute(self, context):
        wm = context.window_manager
        duplicate = mapping.duplicates(_rows_as_mapping(wm))
        if duplicate:
            self.report({"ERROR"}, "Conflit : une même source sert plusieurs os (voir le panneau).")
            return {"CANCELLED"}
        _library, cache = ui.settings(context)
        try:
            directory = ui.cache_directory(cache)
        except Exception as error:  # noqa: BLE001
            self.report({"ERROR"}, f"Dossier de cache indisponible : {error}")
            return {"CANCELLED"}
        path = mapping.save_profile(directory, _source_skeleton(context), _rows_as_mapping(wm), wm.hl_map_source.name)
        _state["message"] = f"Profil enregistré : {path.name}"
        self.report({"INFO"}, _state["message"])
        return {"FINISHED"}


class HUMANLOOM_OT_mapping_load(bpy.types.Operator, ImportHelper):
    bl_idname = "humanloom.mapping_load"
    bl_label = "Charger un profil"
    bl_description = "Charge un profil de mapping (JSON) ; les os absents de la source sont signalés et ignorés"
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})

    @classmethod
    def poll(cls, context):
        return _rig(context) is not None and context.window_manager.hl_map_source is not None

    def execute(self, context):
        wm = context.window_manager
        source = _source_skeleton(context)
        try:
            data, problems = mapping.load_profile(Path(self.filepath), source)
        except (OSError, ValueError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        applied = mapping.apply_profile(data, source)
        target = mapping.from_armature(_rig(context))
        wm.hl_map_rows.clear()
        for name in target.names:
            row = wm.hl_map_rows.add()
            row.target = name
            if name in applied:
                row.source, row.score, row.method = applied[name], data.get("scores", {}).get(name, 1.0), "profil"
        _state.update(report=None, problems=problems, message=f"Profil chargé : {len(applied)} appariements.")
        self.report({"WARNING" if problems else "INFO"}, _state["message"] + (" " + " ".join(problems) if problems else ""))
        return {"FINISHED"}


class HUMANLOOM_UL_mapping(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        source = context.window_manager.hl_map_source
        column = layout.column(align=True)  # deux lignes par os : nom cible + score + effacer, puis le champ de recherche de la source sur toute la largeur
        top = column.row(align=True)
        top.label(text=item.target)
        score = top.row(align=True)
        score.alert = bool(item.source) and 0 < item.score < mapping.LOW_CONFIDENCE
        score.label(text=f"{item.score:.2f} {item.method}" if item.source and item.method not in ("manuel",) else "")
        operator = top.operator("humanloom.mapping_clear_row", text="", icon="X", emboss=False)
        operator.index = index
        if source is not None:
            column.prop_search(item, "source", source.data, "bones", text="")
        else:
            column.label(text=item.source)


class HUMANLOOM_PT_mapping(bpy.types.Panel):
    bl_label = "Mapping des animations"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Humain"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout, wm = self.layout, context.window_manager
        if _rig(context) is None:
            layout.label(text="Installez d'abord le squelette du corps.", icon="INFO")
        layout.prop(wm, "hl_map_source", text="Source")
        row = layout.row(align=True)
        row.operator("humanloom.mapping_auto", icon="SNAP_ON")
        row.operator("humanloom.mapping_load", icon="FILE_FOLDER", text="")
        if len(wm.hl_map_rows):
            duplicate = mapping.duplicates(_rows_as_mapping(wm))
            if duplicate:
                layout.label(text=f"Conflit : {next(iter(duplicate))} utilisé {len(next(iter(duplicate.values())))} fois", icon="ERROR")
            layout.template_list("HUMANLOOM_UL_mapping", "", wm, "hl_map_rows", wm, "hl_map_active", rows=8)
            layout.operator("humanloom.mapping_save", icon="FILE_TICK")
            mapped = sum(1 for r in wm.hl_map_rows if r.source)
            layout.label(text=f"{mapped} appariés sur {len(wm.hl_map_rows)} · {sum(1 for r in wm.hl_map_rows if r.source and 0 < r.score < mapping.LOW_CONFIDENCE)} à vérifier")
        report = _state["report"]
        if report is not None:
            summary = report.summary()
            layout.label(text=f"Sources inutilisées : {sum(summary['sources_inutilisées'].values())} · parents incohérents : {summary['parents_incohérents']}")
        for problem in _state["problems"][:3]:
            layout.label(text=problem[:70], icon="ERROR")
        if _state["message"]:
            layout.label(text=_state["message"][:80])


CLASSES = (HL_MapRow, HUMANLOOM_OT_mapping_auto, HUMANLOOM_OT_mapping_clear_row, HUMANLOOM_OT_mapping_save, HUMANLOOM_OT_mapping_load, HUMANLOOM_UL_mapping, HUMANLOOM_PT_mapping)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    wm = bpy.types.WindowManager
    wm.hl_map_source = PointerProperty(type=bpy.types.Object, name="Armature source", poll=_is_armature)
    wm.hl_map_rows = CollectionProperty(type=HL_MapRow)
    wm.hl_map_active = IntProperty()


def unregister():
    wm = bpy.types.WindowManager
    for name in ("hl_map_active", "hl_map_rows", "hl_map_source"):
        if hasattr(wm, name):
            delattr(wm, name)
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
    _state.update(report=None, message="", problems=[])
