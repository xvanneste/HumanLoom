"""Interface du retargeting (lots A3 et F0-b) : appliquer l'animation sélectionnée dans la galerie au rig du corps (aperçu, NLA, remplacement), réglages (mode de pose, root motion,
vitesse, découpe, échelle), vignettes générées hors processus, publication des favoris dans l'Asset Browser.

Prérequis : un rig installé (rig_ui), une armature source choisie et un mapping calculé (mapping_ui), une animation sélectionnée (ui). L'action source est chargée seule
depuis la bibliothèque de l'utilisateur (jamais écrite), convertie par `retarget`, puis l'action convertie est écrite pour NOS os. Aucune lecture de .blend à l'enregistrement.
"""
from concurrent.futures import CancelledError
import threading
import time

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty

from .. import human
from . import mapping, retarget, retarget_bpy, skeleton, thumbnails, ui

_preview = retarget_bpy.Preview()
_state = {"message": "", "report": None, "thumb_thread": None, "thumb_result": None, "thumb_error": "", "thumb_cancel": None}


def _rig_object(context):
    body = human.body_of(context.active_object)
    rigs = skeleton.rigs_of(body) if human.is_native(body) else []
    return rigs[0] if len(rigs) == 1 else None


def _entry_for(entry_id):
    index = ui._state["index"]
    position = index.positions.get(entry_id) if index is not None else None
    if position is None:
        return None, None
    return index.entry(position), ui.action_for(entry_id)


def _selected_entry(context):
    wm = context.window_manager
    if ui._state["index"] is None or not (0 <= wm.hl_anim_active < len(wm.hl_anim_results)):
        return None, None
    return _entry_for(wm.hl_anim_results[wm.hl_anim_active].entry_id)


def _library_blend(context):
    library, _cache = ui.settings(context)
    return ui.library_blend(library)


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
    options = retarget.Options(pose_mode=wm.hl_ret_pose, root_motion=wm.hl_ret_root, translation_scale=wm.hl_ret_scale if wm.hl_ret_scale > 0 else None,
                               ik_limbs=("arm", "leg") if wm.hl_ret_ik_arms else ("leg",), clavicle_scale=wm.hl_ret_clavicle,
                               clavicle_mode="rythme" if wm.hl_ret_rhythm else "source")
    with bpy.data.libraries.load(str(blend), link=False) as (_available, wanted):  # une seule action par chargement
        wanted.actions = [action_name]
    loaded = wanted.actions[0]
    if loaded is None:
        raise ValueError("Action introuvable dans le fichier de bibliothèque.")
    try:
        # La source du mapping sert de squelette de référence pour ce clip autonome.
        motion, first = retarget_bpy.read_action(loaded, source, euler_order=ui.euler_order(wm))
    finally:
        bpy.data.actions.remove(loaded)
    key = retarget_bpy.conversion_cache_key(source, target, links, options, motion, f"{entry['id']}|{action_name}")
    _library, cache = ui.settings(context)
    directory = ui.cache_directory(cache)
    result = retarget_bpy.cache_load(directory, key)
    if result is None:
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
        _state["thumb_error"] = ""
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
        _state["thumb_error"] = ""
        published, failed = 0, []
        wm = context.window_manager
        _library, cache = ui.settings(context)
        directory = ui.cache_directory(cache)
        source = wm.hl_map_source
        blend = _library_blend(context)
        revision, scope = None, None
        if source is not None and blend is not None and any((directory / "thumbs").glob("*.png")):
            try:
                _rig, revision, scope = ui.thumbnail_sources(source, blend, ui.euler_order(wm))
            except (OSError, ValueError):
                pass
        for entry_id in sorted(ui._state["user"].favorites):
            entry, action_name = _entry_for(entry_id)
            if entry is None:
                failed.append(f"{entry_id} : absente de l'index")
                continue
            try:
                converted, _result, _seconds = convert(context, entry, action_name)
            except ValueError as error:
                failed.append(f"{entry['name']} : {error}")
                continue
            converted.asset_mark()
            converted.asset_data.description = f"Animation « {entry['name']} » convertie pour HumanLoom (catégorie {ui._state['index'].category(ui._state['index'].positions[entry_id])})"
            converted.asset_data.tags.new(ui._state["index"].category(ui._state["index"].positions[entry_id])[:60], skip_if_exists=True)
            try:
                current = scope is not None and _library_blend(context) == blend and thumbnails.request_library_revision(blend) == revision
            except (OSError, ValueError):
                current = False
            key = thumbnails.key_for(entry_id, action_name, scope) if current else None
            thumb = thumbnails.thumb_path(directory, key) if key is not None else None
            if thumb is not None and thumb.is_file():
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


def _thumbnail_items(entries, rig, revision, euler_order):
    scope = thumbnails.scope_for(rig, revision, euler_order)
    return [(thumbnails.key_for(entry_id, action_name, scope), action_name) for entry_id, action_name in entries]


def _thumbnail_job(directory, blender, library_blend, source_name, entries, result, rig, euler_order, cancel):
    try:
        revision = thumbnails.library_revision(library_blend, cancel=cancel)
        items = thumbnails.missing(directory, _thumbnail_items(entries, rig, revision, euler_order))
        if items:
            source_rig = {"names": rig.names, "parents": rig.parents, "rest": rig.rest.tolist()}
            result["value"] = thumbnails.generate(directory, blender, library_blend, source_name, items, source_rig=source_rig, revision=revision, euler_order=euler_order, cancel=cancel)
        else:
            result["value"] = {"produced": [], "errors": [], "cached": True}
    except CancelledError:
        return
    except (OSError, ValueError) as error:
        result["value"] = {"produced": [], "errors": [{"message": str(error)}]}


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
        source = wm.hl_map_source
        euler_order = ui.euler_order(wm)
        try:
            rig, revision, _scope = ui.thumbnail_sources(source, blend)
        except (OSError, ValueError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        _state["thumb_error"] = ""
        entries = []
        for position in range(wm.hl_anim_page * ui.PAGE_SIZE, min(len(wm.hl_anim_results), (wm.hl_anim_page + 1) * ui.PAGE_SIZE)):
            entry, action_name = _entry_for(wm.hl_anim_results[position].entry_id)
            if entry is not None and action_name:
                entries.append((entry["id"], action_name))
        if not entries or (revision is not None and not thumbnails.missing(directory, _thumbnail_items(entries, rig, revision, euler_order))):
            _state["message"] = "Vignettes déjà en cache."
            return {"FINISHED"}
        _state["thumb_result"] = {}
        cancel = threading.Event()
        thread = threading.Thread(target=_thumbnail_job, args=(directory, bpy.app.binary_path, blend, source.data.name, entries, _state["thumb_result"], rig, euler_order, cancel), daemon=True)
        _state["thumb_cancel"] = cancel
        _state["thumb_thread"] = thread
        thread.start()
        if not bpy.app.timers.is_registered(poll_thumbnails):
            bpy.app.timers.register(poll_thumbnails, first_interval=1.0)
        _state["message"] = "Préparation des vignettes en arrière-plan…"
        return {"FINISHED"}


def poll_thumbnails():
    thread = _state["thumb_thread"]
    if thread is None:
        return None
    if thread.is_alive():
        return 1.0
    _state.update(thumb_thread=None, thumb_cancel=None)
    value = (_state["thumb_result"] or {}).get("value", {"produced": [], "errors": []})
    errors = value["errors"]
    _state["message"] = "Vignettes déjà en cache." if value.get("cached") else f"Vignettes : {len(value['produced'])} générée(s)."
    if errors:
        _state["message"] += f" {len(errors)} échec(s)."
        _state["thumb_error"] = next((error["reason"] for error in errors if "reason" in error), errors[0]["message"])
    else:
        _state["thumb_error"] = ""
    for area in bpy.context.screen.areas if bpy.context.screen else ():
        area.tag_redraw()
    return None


def cancel_thumbnails():
    """Libère le panneau et annule le job qui appartenait au fichier précédent."""
    cancel = _state["thumb_cancel"]
    if cancel is not None:
        cancel.set()
    if bpy.app.timers.is_registered(poll_thumbnails):
        bpy.app.timers.unregister(poll_thumbnails)
    _state.update(thumb_thread=None, thumb_result=None, thumb_cancel=None, thumb_error="", message="")


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
        column.prop(wm, "hl_ret_euler_order", text="Ordre Euler source")
        column.prop(wm, "hl_ret_root", text="Root motion")
        column.prop(wm, "hl_ret_ik_arms", text="IK des bras (contacts mains-objets)")
        column.prop(wm, "hl_ret_rhythm")
        sub = column.column(align=True)
        sub.active = not wm.hl_ret_rhythm
        sub.prop(wm, "hl_ret_clavicle", slider=True)
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
        if _state["thumb_error"]:
            layout.label(text=_state["thumb_error"], icon="ERROR")


CLASSES = (HUMANLOOM_OT_animation_apply, HUMANLOOM_OT_animation_publish_favorites, HUMANLOOM_OT_animation_thumbnails, HUMANLOOM_PT_animation_apply)
WINDOW_PROPERTIES = ("hl_ret_euler_order", "hl_ret_pose", "hl_ret_ik_arms", "hl_ret_clavicle", "hl_ret_rhythm", "hl_ret_root", "hl_ret_speed", "hl_ret_trim_start", "hl_ret_trim_end", "hl_ret_scale")


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    wm = bpy.types.WindowManager
    wm.hl_ret_euler_order = EnumProperty(
        name="Ordre Euler du clip source",
        description="Ordre utilisé pour les clips Euler détachés de leur armature d’origine. Ce choix s’applique à la galerie, aux vignettes et aux favoris. Traitez séparément les lots d’ordres différents. Les anciens clips peuvent utiliser XYZ",
        items=[("NONE", "Non renseigné", "Refuse les clips Euler sans ordre explicite")]
              + [(order, "XYZ (convention historique)" if order == "XYZ" else order, "") for order in retarget_bpy.EULER_ORDERS],
        default="NONE")
    wm.hl_ret_pose = EnumProperty(name="Mode de pose", items=((retarget.ABSOLUTE_IK, "Absolu + IK des jambes", "Directions de la source, puis pieds replacés par IK à 2 os (jambes seules par défaut ; case « IK des bras » pour les contacts mains-objets) ; mesuré : coudes et genoux 1,2 % de la stature en médiane, mains et pieds 0,8 %"),
                                                                (retarget.ABSOLUTE, "Absolu", "Le personnage reprend les directions monde de la source"),
                                                                (retarget.DELTA, "Delta", "Rotations relatives au repos de la source")), default=retarget.ABSOLUTE_IK)
    wm.hl_ret_root = EnumProperty(name="Root motion", items=((retarget.KEEP, "Conserver", "Le déplacement reste sur le bassin"), (retarget.IN_PLACE, "Sur place", "Déplacement horizontal retiré"),
                                                              (retarget.EXTRACT, "Extraire vers root", "Déplacement horizontal porté par l'os root")), default=retarget.KEEP)
    wm.hl_ret_speed = FloatProperty(name="Vitesse", default=1.0, min=0.1, max=8.0, description="1 = vitesse d'origine ; 2 = deux fois plus rapide")
    wm.hl_ret_trim_start = IntProperty(name="Début", default=0, min=0, description="Première image conservée (0 = début)")
    wm.hl_ret_trim_end = IntProperty(name="Fin", default=0, min=0, description="Dernière image conservée (0 = fin)")
    wm.hl_ret_clavicle = FloatProperty(name="Rotation des clavicules", default=1.0, min=0.0, max=1.0, description="Part de la rotation des clavicules de la source conservée (1 = fidèle). Réduire (0,5) limite le haussement d'épaule et ses plis du cou et du trapèze (mesuré sur 30 actions : plis en zone large −27 % à 0,5) ; l'orientation du bras et des autres os est conservée (positions relatives à la racine du membre inchangées)")
    wm.hl_ret_rhythm = BoolProperty(name="Rythme scapulo-huméral", default=True, description="La clavicule est calculée d'après l'élévation du bras (la clavicule monte et pivote quand le bras dépasse 60° ; l'orientation du bras est conservée ; la main monte d'environ 4 cm à 135°). Remplace la rotation des clavicules de la source et le réglage ci-dessous. Réduit les plis de l'aisselle au-delà de 120° ; en flexion vers l'avant le gain est faible")
    wm.hl_ret_ik_arms = BoolProperty(name="IK des bras", default=False, description="Contacts mains-objets (parapluie, téléphone) : les mains sont replacées par IK à la position de celles de la source (mesuré : fidélité de pose moins bonne, mains à 2,4 % / 6,9 % contre 0,8 % / 1,8 %) ; décoché (défaut), les bras copient les directions de la source")
    wm.hl_ret_scale = FloatProperty(name="Échelle", default=0.0, min=0.0, description="Échelle des translations du bassin (0 = rapport automatique des hauteurs de bassin)")


def unregister():
    cancel_thumbnails()
    wm = bpy.types.WindowManager
    for name in WINDOW_PROPERTIES:
        if hasattr(wm, name):
            delattr(wm, name)
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
    if _preview.saved:
        _preview.stop()
