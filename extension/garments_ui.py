"""Interface des vêtements (lot V1) : panneau « Vêtements » (pièces par catégorie, couleur, dégagement, masque de peau, tenues). La galerie complète avec vignettes et l'import sont du lot V2."""
import json
from pathlib import Path

import bpy
import bpy.utils.previews

from . import garments, human, skin_mask
from .animation import skeleton

OUTFITS_KEY = "humanloom_outfits"
FAVORITES_KEY = "humanloom_garment_favorites"
DATA = Path(__file__).resolve().parent / "data"
THUMBS = DATA / "garment_thumbs"
_previews = None


def _icon(key):
    """Vignette de la pièce (chargée à la première ouverture du panneau, pas à l'enregistrement)."""
    global _previews
    path = THUMBS / (key + ".png")
    if not path.is_file():
        return 0
    if _previews is None:
        _previews = bpy.utils.previews.new()
    if key not in _previews:
        _previews.load(key, str(path), "IMAGE")
    return _previews[key].icon_id


def favorites(scene):
    try:
        return list(json.loads(scene.get(FAVORITES_KEY, "[]")))
    except ValueError:
        return []


ERRORS = (ValueError, RuntimeError, KeyError, IndexError, StopIteration, AttributeError, TypeError)  # GRM-016 : une erreur de ressource ou d'état est rapportée, jamais un traceback


def _object_mode(context):
    return context.mode == "OBJECT"


def _body(context):
    body = human.body_of(context.active_object)
    return body if human.is_native(body) else None


class HUMANLOOM_OT_garment_add(bpy.types.Operator):
    bl_idname = "humanloom.garment_add"
    bl_label = "Ajouter la pièce"
    bl_description = "Ajoute la pièce au personnage actif (squelette requis : la pièce hérite des poids du corps)"
    bl_options = {"REGISTER", "UNDO"}
    piece: bpy.props.StringProperty()

    @classmethod
    def poll(cls, context):
        body = _body(context)
        return _object_mode(context) and body is not None and bool(skeleton.rigs_of(body))

    def execute(self, context):
        try:
            garments.add_garment(_body(context), self.piece)
        except ERRORS as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}


class HUMANLOOM_OT_garment_color(bpy.types.Operator):
    bl_idname = "humanloom.garment_color"
    bl_label = "Couleur de la pièce"
    bl_options = {"REGISTER", "UNDO"}
    piece: bpy.props.StringProperty()
    color: bpy.props.FloatVectorProperty(name="Couleur", subtype="COLOR", size=3, min=0, max=1)

    @classmethod
    def poll(cls, context):
        return _object_mode(context) and _body(context) is not None

    def _piece(self, context):
        return next((g for g in garments.garments_of(_body(context))
                     if g[garments.MARKER] == self.piece), None)

    def invoke(self, context, event):
        garment = self._piece(context)
        if garment is None or not garment.material_slots or garment.material_slots[0].material is None:
            return {"CANCELLED"}
        self.color = garments.color_of(garment)
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        garment = self._piece(context)
        if garment is None or not garment.material_slots or garment.material_slots[0].material is None:
            return {"CANCELLED"}
        garments.set_color(garment, self.color)
        return {"FINISHED"}


class HUMANLOOM_OT_garment_favorite(bpy.types.Operator):
    bl_idname = "humanloom.garment_favorite"
    bl_label = "Favori"
    bl_description = "Ajoute ou retire la pièce des favoris (enregistrés dans la scène)"
    bl_options = {"REGISTER", "UNDO"}
    piece: bpy.props.StringProperty()

    def execute(self, context):
        fav = favorites(context.scene)
        if self.piece in fav:
            fav.remove(self.piece)
        else:
            fav.append(self.piece)
        context.scene[FAVORITES_KEY] = json.dumps(fav)
        return {"FINISHED"}


class HUMANLOOM_OT_garment_import(bpy.types.Operator):
    bl_idname = "humanloom.garment_import"
    bl_label = "Importer un vêtement…"
    bl_description = "Importe un vêtement de VOTRE dossier (.obj, .fbx, .blend), l'ajuste au corps (poids transférés ou suivi de surface) et affiche un rapport de pénétration chiffré ; un échec est signalé, jamais masqué"
    bl_options = {"REGISTER", "UNDO"}
    filepath: bpy.props.StringProperty(subtype="FILE_PATH")
    mode: bpy.props.EnumProperty(name="Ajustement", items=[("pose", "Suit la pose (poids du corps)", "Poids de peau transférés du corps + armature : suit les animations"),
                                                           ("morphologie", "Suit la morphologie (surface)", "Surface Deform lié au corps : suit les changements de morphologie")], default="pose")

    @classmethod
    def poll(cls, context):
        return _object_mode(context) and _body(context) is not None

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        try:
            produced = garments.import_garment(_body(context), self.filepath, self.mode)
        except ERRORS as error:
            self.report({"ERROR"}, str(error)[:300])
            return {"CANCELLED"}
        for obj, report in produced:
            self.report({"INFO"}, f"{obj.name} : distance moyenne {report['distance_moyenne_m'] * 100:.1f} cm, {report['part_a_l_interieur_avant'] * 100:.1f} % à l'intérieur avant ajustement, {report['sommets_repousses']} sommets repoussés.")
        return {"FINISHED"}


class HUMANLOOM_OT_garment_remove(bpy.types.Operator):
    bl_idname = "humanloom.garment_remove"
    bl_label = "Retirer la pièce"
    bl_options = {"REGISTER", "UNDO"}
    piece: bpy.props.StringProperty()

    @classmethod
    def poll(cls, context):
        return _object_mode(context) and _body(context) is not None

    def execute(self, context):
        selected = [g for g in garments.garments_of(_body(context)) if g[garments.MARKER] == self.piece]
        try:
            skin_mask.guard_garments(selected)
            for garment in selected:
                garments.remove_garment(garment)
        except ERRORS as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}


class HUMANLOOM_OT_garment_update(bpy.types.Operator):
    bl_idname = "humanloom.garment_update"
    bl_label = "Ajuster les pièces à la morphologie"
    bl_description = "Recalcule les positions de toutes les pièces d'après la morphologie actuelle (topologie fixe)"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        body = _body(context)
        return _object_mode(context) and body is not None and bool(garments.garments_of(body))

    def execute(self, context):
        selected = garments.garments_of(_body(context))
        try:
            skin_mask.guard_garments(selected)
            for garment in selected:
                garments.update_garment(garment)
        except ERRORS as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}


SKIN_MODES = (
    (skin_mask.OFF, "Désactivé", "Affiche toute la peau sous les vêtements"),
    (skin_mask.RENDER, "Rendu uniquement", "Masque la peau dans le rendu EEVEE et Cycles. Conserve la surface pour les simulations, les attaches et le groom. La peau peut rester visible en mode Solide"),
    (skin_mask.GEOMETRY, "Géométrie", "Masque la peau en mode Solide et au rendu. Peut modifier les simulations, les attaches et le groom"),
)
LEGACY_SKIN_MODES = SKIN_MODES + ((skin_mask.LEGACY, "Conserver le masque historique", "Garde le masque et sa pile existants"),)


def _skin_modes(operator, context):
    body = _body(context) if context else None
    return LEGACY_SKIN_MODES if body is not None and skin_mask.mode_of(body) == skin_mask.LEGACY else SKIN_MODES


class HUMANLOOM_OT_garment_options(bpy.types.Operator):
    bl_idname = "humanloom.garment_options"
    bl_label = "Options des vêtements"
    bl_options = {"REGISTER", "UNDO"}
    clearance_action: bpy.props.EnumProperty(name="Dégagement sous pose", items=(
        ("KEEP", "Conserver les réglages", "Garde le réglage de chaque pièce"),
        ("ON", "Activer sur les pièces", "Repousse les sommets qui pénètrent le corps sous une pose"),
        ("OFF", "Désactiver sur les pièces", "Désactive le dégagement sur la tenue actuelle"),
    ))
    clearance: bpy.props.BoolProperty(options={"HIDDEN", "SKIP_SAVE"})
    skin_mode: bpy.props.EnumProperty(name="Masque de peau", items=_skin_modes)
    hide_skin: bpy.props.BoolProperty(options={"HIDDEN", "SKIP_SAVE"})

    @classmethod
    def poll(cls, context):
        body = _body(context)
        return body is not None and body.mode == "OBJECT" and body.is_editable

    def invoke(self, context, event):
        body = _body(context)
        self.skin_mode = skin_mask.mode_of(body)
        self.clearance_action = "KEEP"
        return context.window_manager.invoke_props_dialog(self, width=470)

    def draw(self, context):
        self.layout.prop(self, "clearance_action")
        self.layout.prop(self, "skin_mode", expand=True)
        if self.skin_mode == skin_mask.RENDER:
            self.layout.label(text="Surface complète pour les simulations, attaches et le groom.")
            self.layout.label(text="La peau peut rester visible en mode Solide.")
        elif self.skin_mode == skin_mask.GEOMETRY:
            self.layout.label(text="Visible en mode Solide et au rendu.")
            self.layout.label(text="Peut affecter les simulations, les attaches et le groom.", icon="INFO")
        elif self.skin_mode == skin_mask.LEGACY:
            self.layout.label(text="Les changements de tenue gardent le masque historique.", icon="INFO")

    def execute(self, context):
        body = _body(context)
        current = skin_mask.mode_of(body)
        mode = current
        if self.properties.is_property_set("skin_mode"):
            mode = self.skin_mode
        elif self.properties.is_property_set("hide_skin"):
            mode = skin_mask.GEOMETRY if self.hide_skin else skin_mask.OFF
        clearance = self.clearance_action
        if clearance == "KEEP" and self.properties.is_property_set("clearance"):
            clearance = "ON" if self.clearance else "OFF"
        explicit = self.properties.is_property_set("skin_mode") or self.properties.is_property_set("hide_skin")
        repair = explicit and clearance == "KEEP" and skin_mask.needs_repair(body, mode)
        if mode != skin_mask.LEGACY and (mode != current or repair):
            try:
                garments.set_skin_mask_mode(body, mode)
            except ERRORS as error:
                self.report({"ERROR"}, str(error))
                return {"CANCELLED"}
        if clearance != "KEEP":
            for garment in garments.garments_of(body):
                garments.set_clearance(garment, clearance == "ON")
        return {"FINISHED"}


class HUMANLOOM_OT_outfit(bpy.types.Operator):
    bl_idname = "humanloom.outfit"
    bl_label = "Tenue"
    bl_description = "Enregistre la tenue actuelle (pièces, couleurs, décalages) ou recharge une tenue enregistrée"
    bl_options = {"REGISTER", "UNDO"}
    action: bpy.props.EnumProperty(items=[("SAVE", "Enregistrer", ""), ("LOAD", "Recharger", "")])
    name: bpy.props.StringProperty(name="Nom", default="Ma tenue")

    @classmethod
    def poll(cls, context):
        return _object_mode(context) and _body(context) is not None

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        body = _body(context)
        store = json.loads(context.scene.get(OUTFITS_KEY, "{}"))
        if self.action == "SAVE":
            store[self.name] = garments.outfit_of(body)
            context.scene[OUTFITS_KEY] = json.dumps(store, ensure_ascii=False)
        else:
            if self.name not in store:
                self.report({"ERROR"}, "Tenue inconnue : " + self.name)
                return {"CANCELLED"}
            try:
                garments.apply_outfit(body, store[self.name])
            except ERRORS as error:
                self.report({"ERROR"}, str(error))
                return {"CANCELLED"}
        return {"FINISHED"}


class HUMANLOOM_PT_garments(bpy.types.Panel):
    bl_label = "Vêtements"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Humain"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return _object_mode(context) and _body(context) is not None

    def draw(self, context):
        layout, body = self.layout, _body(context)
        if not skeleton.rigs_of(body):
            layout.label(text="Posez d'abord le squelette (poids hérités).", icon="INFO")
            return
        worn = {g[garments.MARKER]: g for g in garments.garments_of(body)}
        fav = favorites(context.scene)
        layout.prop(context.window_manager, "hl_garment_favorites_only")
        for category, keys in garments.categories().items():
            keys = [k for k in keys if k in fav or not context.window_manager.hl_garment_favorites_only]
            if not keys:
                continue
            box = layout.box()
            box.label(text=category)
            grid = box.grid_flow(row_major=True, columns=2, even_columns=True, align=True)
            for key in keys:
                cell = grid.column(align=True)
                row = cell.row(align=True)
                icon = _icon(key)
                if key in worn:
                    row.operator("humanloom.garment_remove", text=garments.GARMENTS[key]["label"], icon_value=icon if icon else 0, depress=True).piece = key
                else:
                    row.operator("humanloom.garment_add", text=garments.GARMENTS[key]["label"], icon_value=icon if icon else 0).piece = key
                row.operator("humanloom.garment_favorite", text="", icon="SOLO_ON" if key in fav else "SOLO_OFF").piece = key
                if key in worn:
                    slots = worn[key].material_slots
                    if slots and slots[0].material is not None:
                        cell.operator("humanloom.garment_color", text="Couleur…").piece = key
        imported = [g for g in garments.garments_of(body) if g.get(garments.IMPORT_MARKER)]
        if imported:
            box = layout.box()
            box.label(text="Importés")
            for g in imported:
                box.operator("humanloom.garment_remove", text=g.name, icon="X").piece = g[garments.MARKER]
        layout.operator("humanloom.garment_import", icon="IMPORT")
        layout.operator("humanloom.garment_update", icon="FILE_REFRESH")
        skin_mode = skin_mask.mode_of(body)
        label = next(label for value, label, _ in LEGACY_SKIN_MODES if value == skin_mode)
        if skin_mode == skin_mask.LEGACY:
            label = "Historique"
        layout.operator("humanloom.garment_options", text=f"Masque de peau · {label}…")
        row = layout.row(align=True)
        row.operator("humanloom.outfit", text="Enregistrer la tenue").action = "SAVE"
        row.operator("humanloom.outfit", text="Recharger").action = "LOAD"


CLASSES = (HUMANLOOM_OT_garment_add, HUMANLOOM_OT_garment_color, HUMANLOOM_OT_garment_favorite, HUMANLOOM_OT_garment_import, HUMANLOOM_OT_garment_remove, HUMANLOOM_OT_garment_update, HUMANLOOM_OT_garment_options, HUMANLOOM_OT_outfit, HUMANLOOM_PT_garments)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.WindowManager.hl_garment_favorites_only = bpy.props.BoolProperty(name="Favoris seulement", default=False)


def unregister():
    global _previews
    if hasattr(bpy.types.WindowManager, "hl_garment_favorites_only"):
        del bpy.types.WindowManager.hl_garment_favorites_only
    if _previews is not None:
        bpy.utils.previews.remove(_previews)
        _previews = None
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
