"""Interface minimale de la bibliothèque d'animations (lot A1c) : préférences, panneau « Bibliothèque d'animations », import.

Aucune animation n'est appliquée ici (lot A3). Règles d'enregistrement (D-27 et pièges) : `register()` ne lit ni .blend ni `bpy.data.libraries.load`
(bpy.data est restreint au démarrage) ; l'index est chargé à la demande (bouton Actualiser, recherche), jamais au démarrage.
L'import tourne dans un fil qui lance des processus Blender séparés (`importer.import_sources`) : l'interface reste utilisable.
"""
from pathlib import Path
import threading

import bpy
from bpy.props import BoolProperty, CollectionProperty, EnumProperty, IntProperty, StringProperty
from bpy_extras.io_utils import ImportHelper

from . import importer, thumbnails
from . import index as index_module
from . import derive_ui, face_ui, mapping_ui, retarget_ui, rig_ui

ADDON_ID = __package__.rpartition(".")[0]
RESULT_LIMIT = 200
PAGE_SIZE = 12
COLUMNS = 3
_previews = {"collection": None}
ALL = "__all__"
OVERRIDE = {}  # tests : {"library_dir": ..., "cache_dir": ...} remplace les préférences
_state = {"index": None, "user": None, "origin": None, "error": None, "thread": None, "import_result": None, "import_message": "", "categories": [], "thumbnail_revision_wait": None}


class HumanLoomAnimationPreferences(bpy.types.AddonPreferences):
    bl_idname = ADDON_ID

    library_dir: StringProperty(
        name="Dossier de bibliothèque", subtype="DIR_PATH",
        description="Dossier qui contient l'inventory.json (et les actions) de VOS animations ; il n'est jamais fourni par HumanLoom")
    cache_dir: StringProperty(
        name="Dossier de cache", subtype="DIR_PATH",
        description="Index, favoris et corrections de catégorie. Vide : dossier utilisateur de l'extension")

    def draw(self, context):
        column = self.layout.column()
        column.prop(self, "library_dir")
        column.prop(self, "cache_dir")
        column.label(text="HumanLoom ne fournit aucune animation : importez vos propres fichiers (docs/animations-import.md).", icon="INFO")
        column.label(text="Vous êtes responsable de vos droits sur les animations importées.")


def settings(context=None):
    """(dossier de bibliothèque, dossier de cache) d'après les préférences ; chaînes vides si non définis."""
    if OVERRIDE:
        return OVERRIDE.get("library_dir", ""), OVERRIDE.get("cache_dir", "")
    context = context or bpy.context
    entry = context.preferences.addons.get(ADDON_ID)
    if entry is None or not hasattr(entry.preferences, "library_dir"):
        return "", ""
    return bpy.path.abspath(entry.preferences.library_dir), bpy.path.abspath(entry.preferences.cache_dir)


def cache_directory(cache):
    return Path(cache) if cache else index_module.default_cache_dir()


def library_blend(library):
    return index_module.find_blend(library)


def euler_order(wm):
    order = getattr(wm, "hl_ret_euler_order", "NONE")
    return None if order == "NONE" else order


def thumbnail_sources(source, blend, euler_order=None):
    """Squelette de référence et révision de bibliothèque lus par la galerie."""
    from . import retarget
    rig = retarget.rig_from_armature(source)
    revision = thumbnails.request_library_revision(blend)
    return rig, revision, thumbnails.scope_for(rig, revision, euler_order) if revision is not None else None


def _poll_thumbnail_revision():
    blend = _state["thumbnail_revision_wait"]
    try:
        if blend is not None and thumbnails.request_library_revision(blend) is None:
            return 0.2
    except (OSError, ValueError):
        pass
    _state["thumbnail_revision_wait"] = None
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            area.tag_redraw()
    return None


def _watch_thumbnail_revision(blend):
    _state["thumbnail_revision_wait"] = blend
    if not bpy.app.timers.is_registered(_poll_thumbnail_revision):
        bpy.app.timers.register(_poll_thumbnail_revision, first_interval=0.2)


def action_for(entry_id):
    index = _state["index"]
    position = index.positions.get(entry_id) if index is not None else None
    return index.actions[position] if position is not None and index.actions else None


def load_state(force=False):
    """Charge l'index (cache < 1 s) et les données utilisateur. Retourne l'index ou None (message dans `_state["error"]`)."""
    _state["error"] = None
    library, cache = settings()
    if not library:
        _state["index"], _state["error"] = None, "Dossier de bibliothèque non défini (Préférences de l'extension)."
        return None
    try:
        directory = cache_directory(cache)
        index, origin = index_module.open_index(library, directory, force=force)
        user = index_module.UserData(directory)
        user.apply(index)
    except (OSError, ValueError, RuntimeError) as error:
        _state["index"], _state["error"] = None, f"Bibliothèque illisible : {error}"
        return None
    _state.update(index=index, user=user, origin=origin)
    _state["categories"] = sorted(index.categories().items(), key=lambda kv: (-kv[1], kv[0]))
    return index


class HL_AnimResult(bpy.types.PropertyGroup):
    entry_id: StringProperty()
    category: StringProperty()
    favorite: BoolProperty()
    root_motion: BoolProperty()


def refresh_results(wm, context=None):
    wm.hl_anim_results.clear()
    index, user = _state["index"], _state["user"]
    if index is None:
        return 0
    category = wm.hl_anim_category if wm.hl_anim_category not in ("", ALL) else None
    found = index.search(wm.hl_anim_query, category=category, favorites=user.favorites if wm.hl_anim_favorites else None, limit=RESULT_LIMIT)
    for position in found:
        entry = index.entry(position)
        item = wm.hl_anim_results.add()
        item.name, item.entry_id, item.category = entry["name"], entry["id"], index.category(position)
        item.favorite, item.root_motion = entry["id"] in user.favorites, entry["root_motion"]
    _state["found"] = len(found)
    return len(found)


def preview_icon(key, cache_dir):
    """Identifiant d'icône d'une vignette du cache disque (chargement paresseux), 0 si elle n'existe pas encore."""
    from bpy.utils import previews
    path = thumbnails.thumb_path(cache_dir, key)
    if not path.is_file():
        return 0
    if _previews["collection"] is None:
        _previews["collection"] = previews.new()
    collection = _previews["collection"]
    if key not in collection:
        collection.load(key, str(path), "IMAGE")
    return collection[key].icon_id


def _update_results(self, context):
    self.hl_anim_page = 0
    refresh_results(self, context)


def _category_items(self, context):
    items = [(ALL, "Toutes les catégories", "")]
    items += [(name, f"{name} ({count})", "") for name, count in _state["categories"] if count]
    _state["category_items"] = items  # garde les chaînes vivantes
    return items


class HUMANLOOM_UL_animations(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        operator = row.operator("humanloom.animation_favorite", text="", icon="SOLO_ON" if item.favorite else "SOLO_OFF", emboss=False)
        operator.entry_id = item.entry_id
        row.label(text=item.name)
        row.label(text=item.category)
        if item.root_motion:
            row.label(text="", icon="CON_LOCLIKE")


class HUMANLOOM_OT_animation_refresh(bpy.types.Operator):
    bl_idname = "humanloom.animation_refresh"
    bl_label = "Actualiser la bibliothèque"
    bl_description = "Relit l'index de votre bibliothèque d'animations (cache) ; ne lit jamais le .blend de la bibliothèque"
    force: BoolProperty(name="Reconstruire", default=False, description="Ignore le cache et relit inventory.json")

    def execute(self, context):
        index = load_state(force=self.force)
        count = refresh_results(context.window_manager)
        if index is None:
            self.report({"WARNING"}, _state["error"])
            return {"CANCELLED"}
        self.report({"INFO"}, f"{len(index)} animations ({_state['origin']}), {count} affichées.")
        return {"FINISHED"}


class HUMANLOOM_OT_animation_select(bpy.types.Operator):
    bl_idname = "humanloom.animation_select"
    bl_label = "Choisir cette animation"
    bl_options = {"INTERNAL"}
    index: IntProperty()

    def execute(self, context):
        context.window_manager.hl_anim_active = self.index
        return {"FINISHED"}


class HUMANLOOM_OT_animation_page(bpy.types.Operator):
    bl_idname = "humanloom.animation_page"
    bl_label = "Page"
    bl_options = {"INTERNAL"}
    delta: IntProperty()

    def execute(self, context):
        wm = context.window_manager
        pages = max(1, -(-len(wm.hl_anim_results) // PAGE_SIZE))
        wm.hl_anim_page = max(0, min(pages - 1, wm.hl_anim_page + self.delta))
        return {"FINISHED"}


class HUMANLOOM_OT_animation_favorite(bpy.types.Operator):
    bl_idname = "humanloom.animation_favorite"
    bl_label = "Favori"
    bl_options = {"INTERNAL"}
    entry_id: StringProperty()

    def execute(self, context):
        if _state["user"] is None:
            return {"CANCELLED"}
        _state["user"].toggle_favorite(self.entry_id)
        refresh_results(context.window_manager)
        return {"FINISHED"}


class HUMANLOOM_OT_animation_set_category(bpy.types.Operator):
    bl_idname = "humanloom.animation_set_category"
    bl_label = "Corriger la catégorie"
    bl_description = "Corrige la catégorie de l'animation sélectionnée (vide : revient à la catégorie du dossier)"
    category: StringProperty(name="Catégorie")

    @classmethod
    def poll(cls, context):
        wm = context.window_manager
        return _state["index"] is not None and 0 <= wm.hl_anim_active < len(wm.hl_anim_results)

    def invoke(self, context, event):
        wm = context.window_manager
        self.category = wm.hl_anim_results[wm.hl_anim_active].category
        return wm.invoke_props_dialog(self)

    def execute(self, context):
        wm = context.window_manager
        item = wm.hl_anim_results[wm.hl_anim_active]
        _state["user"].set_category(item.entry_id, self.category.strip())
        _state["user"].apply(_state["index"])
        _state["categories"] = sorted(_state["index"].categories().items(), key=lambda kv: (-kv[1], kv[0]))
        refresh_results(wm)
        return {"FINISHED"}


def _import_thread(sources, library, exe, result):
    try:
        result["report"] = importer.import_sources(sources, library, exe)
    except Exception as error:  # noqa: BLE001 - affiché à l'utilisateur
        result["error"] = f"{type(error).__name__}: {error}"


def poll_import():
    """Minuteur : attend la fin du fil d'importation, puis actualise l'index et prépare le message."""
    thread = _state["thread"]
    if thread is not None and thread.is_alive():
        return 0.5
    result = _state["import_result"] or {}
    _state["thread"] = None
    if "error" in result:
        _state["import_message"] = f"Import refusé : {result['error']}"
    elif "report" in result:
        report = result["report"]
        _state["import_message"] = (f"Import : {report['ajoutées']} ajoutée(s), {report['doublons']} doublon(s), {report['inchangés']} inchangé(s), "
                                    f"{report['échecs']} échec(s).")
        failed = [f"{f['source']} : {f.get('message', '')}" for f in report["fichiers"] if f["statut"] == "échec"]
        if failed:
            _state["import_message"] += " Échecs : " + " ; ".join(failed[:3])
        load_state()
        try:
            refresh_results(bpy.context.window_manager)
        except (AttributeError, RuntimeError):
            pass
    return None


class HUMANLOOM_OT_animation_import(bpy.types.Operator, ImportHelper):
    bl_idname = "humanloom.animation_import"
    bl_label = "Importer des animations"
    bl_description = ("Importe VOS fichiers (FBX, BVH, glTF/GLB, .blend ou dossier) dans votre bibliothèque, dans des processus Blender séparés ; "
                      "les sources ne sont jamais modifiées")
    filter_glob: StringProperty(default="*.fbx;*.bvh;*.glb;*.gltf;*.blend", options={"HIDDEN"})
    directory_mode: BoolProperty(name="Dossier", default=False, description="Importer tout un dossier (parcours récursif)")

    def execute(self, context):
        library, _ = settings(context)
        if not library:
            self.report({"ERROR"}, "Dossier de bibliothèque non défini (Préférences de l'extension).")
            return {"CANCELLED"}
        if _state["thread"] is not None:
            self.report({"WARNING"}, "Un import est déjà en cours.")
            return {"CANCELLED"}
        source = Path(self.filepath)
        if self.directory_mode and not source.is_dir():
            source = source.parent
        if not source.exists():
            self.report({"ERROR"}, "Source introuvable.")
            return {"CANCELLED"}
        _state["import_result"] = {}
        _state["import_message"] = "Import en cours…"
        thread = threading.Thread(target=_import_thread, args=([str(source)], library, bpy.app.binary_path, _state["import_result"]), daemon=True)
        _state["thread"] = thread
        thread.start()
        bpy.app.timers.register(poll_import, first_interval=0.5)
        self.report({"INFO"}, "Import lancé en arrière-plan.")
        return {"FINISHED"}


class HUMANLOOM_PT_animation_library(bpy.types.Panel):
    bl_label = "Bibliothèque d'animations"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Humain"
    bl_options = {"DEFAULT_CLOSED"}

    @staticmethod
    def draw_grid(context, layout):
        """Grille de vignettes paginée (3 colonnes × 4 lignes) ; l'animation active est surlignée ; étoile = favori."""
        wm = context.window_manager
        library, cache = settings(context)
        try:
            directory = cache_directory(cache)
            source = getattr(wm, "hl_map_source", None)
            blend = library_blend(library) if source is not None and (directory / "thumbs").is_dir() else None
            scope = thumbnail_sources(source, blend, euler_order(wm))[2] if blend is not None else None
            if blend is not None and scope is None:
                _watch_thumbnail_revision(blend)
        except Exception:  # noqa: BLE001 - pas de dossier de cache : icônes génériques
            directory, scope = None, None
        total = len(wm.hl_anim_results)
        pages = max(1, -(-total // PAGE_SIZE))
        page = max(0, min(pages - 1, wm.hl_anim_page))
        grid = layout.grid_flow(row_major=True, columns=COLUMNS, align=True)
        for position in range(page * PAGE_SIZE, min(total, (page + 1) * PAGE_SIZE)):
            item = wm.hl_anim_results[position]
            cell = grid.box().column(align=True)
            action_name = action_for(item.entry_id) if scope else None
            key = thumbnails.key_for(item.entry_id, action_name, scope) if action_name else None
            icon_id = preview_icon(key, directory) if key is not None else 0
            if icon_id:
                cell.template_icon(icon_value=icon_id, scale=4.5)
            row = cell.row(align=True)
            button = row.operator("humanloom.animation_select", text=item.name[:11], icon="NONE" if icon_id else "ARMATURE_DATA", depress=(position == wm.hl_anim_active))
            button.index = position
            row.operator("humanloom.animation_favorite", text="", icon="SOLO_ON" if item.favorite else "SOLO_OFF", emboss=False).entry_id = item.entry_id
        row = layout.row(align=True)
        row.operator("humanloom.animation_page", text="", icon="TRIA_LEFT").delta = -1
        row.label(text=f"Page {page + 1} / {pages}")
        row.operator("humanloom.animation_page", text="", icon="TRIA_RIGHT").delta = 1

    def draw(self, context):
        layout, wm = self.layout, context.window_manager
        library, _ = settings(context)
        if not library:
            layout.label(text="Définissez votre dossier de bibliothèque", icon="ERROR")
            layout.label(text="dans les préférences de l'extension.")
        layout.operator("humanloom.animation_refresh", icon="FILE_REFRESH")
        if _state["error"] and library:
            layout.label(text=_state["error"][:80], icon="ERROR")
        index = _state["index"]
        if index is not None:
            layout.label(text=f"{len(index)} animations · {_state['origin']}")
            layout.prop(wm, "hl_anim_query", icon="VIEWZOOM", text="")
            row = layout.row(align=True)
            row.prop(wm, "hl_anim_category", text="")
            row.prop(wm, "hl_anim_favorites", text="", icon="SOLO_ON")
            HUMANLOOM_PT_animation_library.draw_grid(context, layout)
            layout.label(text=f"{_state.get('found', 0)} résultat(s)" + (f" (affichage limité à {RESULT_LIMIT})" if _state.get("found", 0) >= RESULT_LIMIT else ""))
            layout.operator("humanloom.animation_set_category", icon="OUTLINER_COLLECTION")
        row = layout.row(align=True)
        row.operator("humanloom.animation_import", text="Importer un fichier", icon="IMPORT").directory_mode = False
        row.operator("humanloom.animation_import", text="Importer un dossier", icon="FILE_FOLDER").directory_mode = True
        if _state["import_message"]:
            layout.label(text=_state["import_message"][:120])
        layout.label(text="Vos propres fichiers uniquement (licences : voir le guide).", icon="INFO")


CLASSES = (HumanLoomAnimationPreferences, HL_AnimResult, HUMANLOOM_UL_animations, HUMANLOOM_OT_animation_refresh, HUMANLOOM_OT_animation_select, HUMANLOOM_OT_animation_page, HUMANLOOM_OT_animation_favorite,
           HUMANLOOM_OT_animation_set_category, HUMANLOOM_OT_animation_import, HUMANLOOM_PT_animation_library)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    rig_ui.register()
    face_ui.register()
    derive_ui.register()
    mapping_ui.register()
    retarget_ui.register()
    wm = bpy.types.WindowManager
    wm.hl_anim_query = StringProperty(name="Recherche", description="Préfixes de mots (ex. « walk fwd »)", update=_update_results)
    wm.hl_anim_category = EnumProperty(name="Catégorie", items=_category_items, update=_update_results)
    wm.hl_anim_favorites = BoolProperty(name="Favoris seulement", default=False, update=_update_results)
    wm.hl_anim_results = CollectionProperty(type=HL_AnimResult)
    wm.hl_anim_active = IntProperty()
    wm.hl_anim_page = IntProperty(name="Page", default=0, min=0)
    if _stop_thumbnail_tasks not in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.append(_stop_thumbnail_tasks)
    # Aucun chargement ici : l'index est lu à la demande.


def _stop_import_job():
    """Détache la tâche d'import avant un chargement de fichier ou une désactivation (ANI-023) : le minuteur est retiré et le résultat tardif du fil (écrit dans un dictionnaire désormais détaché) est ignoré. Les imports sont transactionnels (journal) : relancer reprend proprement ; le fil ne peut pas être tué, il se termine seul."""
    if bpy.app.timers.is_registered(poll_import):
        bpy.app.timers.unregister(poll_import)
    if _state["thread"] is not None:
        _state["import_message"] = "Import interrompu par un changement de fichier ou la désactivation de l'extension : relancez-le (il reprend sans perte)."
    _state["thread"] = None
    _state["import_result"] = None


@bpy.app.handlers.persistent
def _stop_thumbnail_tasks(_unused=None):
    _stop_import_job()
    retarget_ui.cancel_thumbnails()
    thumbnails.cancel_library_revisions()
    if bpy.app.timers.is_registered(_poll_thumbnail_revision):
        bpy.app.timers.unregister(_poll_thumbnail_revision)
    _state["thumbnail_revision_wait"] = None


def unregister():
    if _stop_thumbnail_tasks in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.remove(_stop_thumbnail_tasks)
    _stop_thumbnail_tasks()
    retarget_ui.unregister()
    mapping_ui.unregister()
    derive_ui.unregister()
    face_ui.unregister()
    rig_ui.unregister()
    wm = bpy.types.WindowManager
    for name in ("hl_anim_page", "hl_anim_active", "hl_anim_results", "hl_anim_favorites", "hl_anim_category", "hl_anim_query"):
        if hasattr(wm, name):
            delattr(wm, name)
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
    if _previews["collection"] is not None:
        from bpy.utils import previews
        previews.remove(_previews["collection"])
        _previews["collection"] = None
    _state.update(index=None, user=None, origin=None, error=None, thread=None)
