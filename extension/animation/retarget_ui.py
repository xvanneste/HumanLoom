"""Interface du retargeting (lots A3 et F0-b) : appliquer l'animation sélectionnée dans la galerie au rig du corps (aperçu, NLA, remplacement), réglages (mode de pose, root motion,
vitesse, découpe, échelle), vignettes générées hors processus, publication des favoris dans l'Asset Browser.

Prérequis : un rig installé (rig_ui), une armature source choisie et un mapping calculé (mapping_ui), une animation sélectionnée (ui). L'action source est chargée seule
depuis la bibliothèque de l'utilisateur (jamais écrite), convertie par `retarget`, puis l'action convertie est écrite pour NOS os. Aucune lecture de .blend à l'enregistrement.
"""
import threading
import time

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty

from .. import human
from . import index as index_module
from . import mapping, retarget, retarget_bpy, skeleton, thumbnails, ui

_preview = retarget_bpy.Preview()
_state = {"message": "", "report": None, "thumb_thread": None, "thumb_result": None}


def _rig_object(context):
    body = human.body_of(context.active_object)
    rigs = skeleton.rigs_of(body) if human.is_native(body) else []
    return rigs[0] if len(rigs) == 1 else None


def _entry_for(entry_id):
    index = ui._state["index"]
    position = index.positions.get(entry_id) if index is not None else None
    if position is None:
        return None, None
    return index.entry(position), (index.actions[position] if index.actions else None)


def _selected_entry(context):
    wm = context.window_manager
    if ui._state["index"] is None or not (0 <= wm.hl_anim_active < len(wm.hl_anim_results)):
        return None, None
    return _entry_for(wm.hl_anim_results[wm.hl_anim_active].entry_id)


def _library_blend(context):
    library, _cache = ui.settings(context)
    found = index_module.find_source(library) if library else None
    folder = found[1].parent if found else None
    blend = folder / "HumanLoom_Actions.blend" if folder and (folder / "HumanLoom_Actions.blend").is_file() else None
    if blend is None and folder:
        blends = sorted(folder.glob("*.blend"))
        blend = blends[0] if blends else None
    return blend


def convert(context, entry, action_name):
    """Convertit une animation pour le rig actif avec les réglages courants. Retourne (action convertie, Result, durée) ; lève ValueError avec un message lisible."""
    wm = context.window_manager
    rig_object = _rig_object(context)
    source_object = wm.hl_map_source
    if source_object is None or not len(wm.hl_map_rows):
        raise ValueError("Choisissez une armature source et calculez le mapping (panneau Mapping).")
    blend = _library_blend(context)
    if not action_name or blend is None:
        raise ValueError("Nom d'action introuvable dans la bibliothèque (importez-la, ou résolvez les noms d'action).")
    started = time.perf_counter()
    source = retarget.rig_from_armature(source_object)
    target = retarget.rig_from_armature(rig_object)
    links = {row.target: row.source for row in wm.hl_map_rows if row.source}
    if mapping.duplicates(links):
        raise ValueError("Conflit dans le mapping : une même source sert plusieurs os.")
    options = retarget.Options(pose_mode=wm.hl_ret_pose, root_motion=wm.hl_ret_root, translation_scale=wm.hl_ret_scale if wm.hl_ret_scale > 0 else None)
    key = retarget.signature(source, links, options, f"{entry['id']}|{action_name}")
    _library, cache = ui.settings(context)
    directory = ui.cache_directory(cache)
    result = retarget_bpy.cache_load(directory, key)
    first = 1
    if result is None:
        with bpy.data.libraries.load(str(blend), link=False) as (_available, wanted):  # une seule action par chargement
            wanted.actions = [action_name]
        loaded = wanted.actions[0]
        if loaded is None:
            raise ValueError("Action introuvable dans le fichier de bibliothèque.")
        try:
            motion, first = retarget_bpy.read_action(loaded, source)
        finally:
            bpy.data.actions.remove(loaded)
        result = retarget.retarget(source, target, links, motion, options)
        retarget_bpy.cache_save(directory, key, result)
    else:
        result.report.update(noms_cibles=list(target.names))
    if wm.hl_ret_speed != 1.0 or wm.hl_ret_trim_start > 0 or wm.hl_ret_trim_end > 0:
        shaped = retarget.trim_and_speed(result, wm.hl_ret_trim_start, wm.hl_ret_trim_end if wm.hl_ret_trim_end > 0 else None, wm.hl_ret_speed)
        shaped.report.update(cache=result.report.get("cache"))
        result = shaped
    converted = retarget_bpy.write_action(rig_object, result, f"{entry['name']}@HumanLoom", first_frame=first)
    return converted, result, time.perf_counter() - started


class HUMANLOOM_OT_animation_apply(bpy.types.Operator):
    bl_idname = "humanloom.animation_apply"
    bl_label = "Appliquer l'animation"
    bl_description = "Convertit l'animation sélectionnée pour le rig du corps (retargeting analytique) puis l'aperçoit, l'ajoute au NLA ou remplace l'action"
    bl_options = {"REGISTER", "UNDO"}
    action: EnumProperty(name="Action", items=(("PREVIEW", "Aperçu", "Aperçu non destructif"), ("NLA", "Ajouter au NLA", ""), ("REPLACE", "Remplacer", "Remplace l'action active"),
                                                  ("STOP", "Fin de l'aperçu", "Restaure l'état initial")), default="PREVIEW")

    @classmethod
    def poll(cls, context):
        return _rig_object(context) is not None

    def execute(self, context):
        rig_object = _rig_object(context)
        if self.action == "STOP":
            _preview.stop()
            _state["message"] = "Aperçu terminé, état restauré."
            return {"FINISHED"}
        entry, action_name = _selected_entry(context)
        if entry is None:
            self.report({"ERROR"}, "Sélectionnez une animation dans la bibliothèque.")
            return {"CANCELLED"}
        try:
            converted, result, seconds = convert(context, entry, action_name)
        except ValueError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        if self.action == "PREVIEW":
            _preview.start(rig_object, converted)
        elif self.action == "NLA":
            retarget_bpy.add_to_nla(rig_object, converted)
        else:
            retarget_bpy.replace_action(rig_object, converted)
        _state["message"] = f"{converted.name} : {result.quat.shape[0]} images en {seconds:.2f} s ({'cache' if result.report.get('cache') else 'calcul'})."
        _state["report"] = result.report
        self.report({"INFO"}, _state["message"])
        return {"FINISHED"}


class HUMANLOOM_OT_animation_publish_favorites(bpy.types.Operator):
    bl_idname = "humanloom.animation_publish_favorites"
    bl_label = "Publier les favoris dans l'Asset Browser"
    bl_description = ("Convertit les animations favorites pour le rig actif et les marque comme assets du fichier courant (catalogue = catégorie, vignette du cache) : "
                      "glisser-déposer natif depuis l'Asset Browser (« Fichier courant »)")
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return _rig_object(context) is not None and ui._state["user"] is not None and bool(ui._state["user"].favorites)

    def execute(self, context):
        published, failed = 0, []
        wm = context.window_manager
        _library, cache = ui.settings(context)
        directory = ui.cache_directory(cache)
        source_name = wm.hl_map_source.data.name if wm.hl_map_source is not None else ""
        for entry_id in sorted(ui._state["user"].favorites):
            entry, action_name = _entry_for(entry_id)
            if entry is None:
                failed.append(f"{entry_id} : absente de l'index")
                continue
            try:
                converted, _result, _seconds = convert(context, entry, action_name)
            except ValueError as error:
                failed.append(f"{entry['name']} : {error}")
                break  # même cause pour toutes (mapping, bibliothèque) : inutile de répéter
            converted.asset_mark()
            converted.asset_data.description = f"Animation « {entry['name']} » convertie pour HumanLoom (catégorie {ui._state['index'].category(ui._state['index'].positions[entry_id])})"
            converted.asset_data.tags.new(ui._state["index"].category(ui._state["index"].positions[entry_id])[:60], skip_if_exists=True)
            thumb = thumbnails.thumb_path(directory, thumbnails.key_for(entry_id, source_name))
            if thumb.is_file():
                try:
                    with bpy.context.temp_override():
                        image = bpy.data.images.load(str(thumb))
                        preview = converted.preview_ensure()
                        preview.image_size = tuple(image.size)
                        preview.image_pixels_float = list(image.pixels)
                        bpy.data.images.remove(image)
                except Exception:  # noqa: BLE001 - la vignette est un confort, pas une condition
                    pass
            published += 1
        _state["message"] = f"{published} favori(s) publié(s) dans l'Asset Browser" + (f" ; échecs : {failed[0]}" if failed else ".")
        self.report({"WARNING" if failed else "INFO"}, _state["message"])
        return {"FINISHED"} if published else {"CANCELLED"}


def _thumbnail_job(directory, blender, library_blend, source_name, items, result):
    result["value"] = thumbnails.generate(directory, blender, library_blend, source_name, items)


class HUMANLOOM_OT_animation_thumbnails(bpy.types.Operator):
    bl_idname = "humanloom.animation_thumbnails"
    bl_label = "Générer les vignettes de la page"
    bl_description = "Génère les vignettes manquantes de la page affichée dans un processus Blender séparé (cache disque dans le dossier utilisateur)"

    @classmethod
    def poll(cls, context):
        return ui._state["index"] is not None and context.window_manager.hl_map_source is not None and _state["thumb_thread"] is None

    def execute(self, context):
        wm = context.window_manager
        blend = _library_blend(context)
        if blend is None:
            self.report({"ERROR"}, "Bibliothèque introuvable.")
            return {"CANCELLED"}
        _library, cache = ui.settings(context)
        directory = ui.cache_directory(cache)
        source_name = wm.hl_map_source.data.name
        items = []
        for position in range(wm.hl_anim_page * ui.PAGE_SIZE, min(len(wm.hl_anim_results), (wm.hl_anim_page + 1) * ui.PAGE_SIZE)):
            entry, action_name = _entry_for(wm.hl_anim_results[position].entry_id)
            if entry is not None and action_name:
                items.append((thumbnails.key_for(entry["id"], source_name), action_name))
        todo = thumbnails.missing(directory, items)
        if not todo:
            _state["message"] = "Vignettes déjà en cache."
            return {"FINISHED"}
        _state["thumb_result"] = {}
        thread = threading.Thread(target=_thumbnail_job, args=(directory, bpy.app.binary_path, blend, source_name, todo, _state["thumb_result"]), daemon=True)
        _state["thumb_thread"] = thread
        thread.start()
        bpy.app.timers.register(poll_thumbnails, first_interval=1.0)
        _state["message"] = f"Génération de {len(todo)} vignette(s) en arrière-plan…"
        return {"FINISHED"}


def poll_thumbnails():
    thread = _state["thumb_thread"]
    if thread is not None and thread.is_alive():
        return 1.0
    _state["thumb_thread"] = None
    value = (_state["thumb_result"] or {}).get("value", {"produced": [], "errors": []})
    _state["message"] = f"Vignettes : {len(value['produced'])} générée(s)" + (f", {len(value['errors'])} échec(s)" if value["errors"] else ".")
    for area in bpy.context.screen.areas if bpy.context.screen else ():
        area.tag_redraw()
    return None


class HUMANLOOM_PT_animation_apply(bpy.types.Panel):
    bl_label = "Appliquer l'animation"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Humain"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout, wm = self.layout, context.window_manager
        if _rig_object(context) is None:
            layout.label(text="Installez d'abord le squelette du corps.", icon="INFO")
        entry, _action = _selected_entry(context)
        layout.label(text=f"Animation : {entry['name']}" if entry else "Aucune animation sélectionnée", icon="ACTION")
        column = layout.column(align=True)
        column.prop(wm, "hl_ret_pose", text="Pose")
        column.prop(wm, "hl_ret_root", text="Root motion")
        column.prop(wm, "hl_ret_speed", text="Vitesse")
        row = column.row(align=True)
        row.prop(wm, "hl_ret_trim_start", text="Début")
        row.prop(wm, "hl_ret_trim_end", text="Fin (0 = tout)")
        column.prop(wm, "hl_ret_scale", text="Échelle (0 = auto)")
        row = layout.row(align=True)
        row.operator("humanloom.animation_apply", text="Aperçu").action = "PREVIEW"
        row.operator("humanloom.animation_apply", text="Fin", icon="X").action = "STOP"
        row = layout.row(align=True)
        row.operator("humanloom.animation_apply", text="Ajouter au NLA", icon="NLA").action = "NLA"
        row.operator("humanloom.animation_apply", text="Remplacer").action = "REPLACE"
        layout.operator("humanloom.animation_thumbnails", icon="IMAGE_DATA")
        layout.operator("humanloom.animation_publish_favorites", icon="ASSET_MANAGER")
        if _state["message"]:
            layout.label(text=_state["message"][:90])


CLASSES = (HUMANLOOM_OT_animation_apply, HUMANLOOM_OT_animation_publish_favorites, HUMANLOOM_OT_animation_thumbnails, HUMANLOOM_PT_animation_apply)
WINDOW_PROPERTIES = ("hl_ret_pose", "hl_ret_root", "hl_ret_speed", "hl_ret_trim_start", "hl_ret_trim_end", "hl_ret_scale")


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    wm = bpy.types.WindowManager
    wm.hl_ret_pose = EnumProperty(name="Mode de pose", items=((retarget.ABSOLUTE_IK, "Absolu + IK des membres", "Directions de la source, puis mains et pieds replacés par IK à 2 os malgré des segments plus courts (mesuré : 2,57 % de la stature en médiane)"),
                                                                (retarget.ABSOLUTE, "Absolu", "Le personnage reprend les directions monde de la source"),
                                                                (retarget.DELTA, "Delta", "Rotations relatives au repos de la source")), default=retarget.ABSOLUTE_IK)
    wm.hl_ret_root = EnumProperty(name="Root motion", items=((retarget.KEEP, "Conserver", "Le déplacement reste sur le bassin"), (retarget.IN_PLACE, "Sur place", "Déplacement horizontal retiré"),
                                                              (retarget.EXTRACT, "Extraire vers root", "Déplacement horizontal porté par l'os root")), default=retarget.KEEP)
    wm.hl_ret_speed = FloatProperty(name="Vitesse", default=1.0, min=0.1, max=8.0, description="1 = vitesse d'origine ; 2 = deux fois plus rapide")
    wm.hl_ret_trim_start = IntProperty(name="Début", default=0, min=0, description="Première image conservée (0 = début)")
    wm.hl_ret_trim_end = IntProperty(name="Fin", default=0, min=0, description="Dernière image conservée (0 = fin)")
    wm.hl_ret_scale = FloatProperty(name="Échelle", default=0.0, min=0.0, description="Échelle des translations du bassin (0 = rapport automatique des hauteurs de bassin)")


def unregister():
    wm = bpy.types.WindowManager
    for name in WINDOW_PROPERTIES:
        if hasattr(wm, name):
            delattr(wm, name)
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
    if _preview.saved:
        _preview.stop()
