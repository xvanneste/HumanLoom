"""Interface du visage complet (lot L1) : galerie de poses avec vignettes et favoris, mélangeur de deux poses, langue articulée, formes cuites pour l'export, clip facial en NLA, couverture ARKit.
Aucune lecture de fichier à l'enregistrement : les vignettes sont chargées à la première ouverture du panneau."""
import json
from pathlib import Path

import bpy
import bpy.utils.previews

from .. import human
from . import dental, face, skeleton

DATA = Path(__file__).resolve().parent.parent / "data"
THUMBS = DATA / "face_thumbs"
INDEX = DATA / "face_gallery.json"
_previews = None
_index = None


def _body(context):
    body = human.body_of(context.active_object)
    return body if human.is_native(body) else None


def _gallery_index():
    global _index
    if _index is None:
        try:
            _index = {e["id"]: e for e in json.loads(INDEX.read_text(encoding="utf-8"))}
        except (OSError, ValueError):
            _index = {}
    return _index


def _icon(pose_id):
    global _previews
    entry = _gallery_index().get(pose_id)
    if entry is None:
        return 0
    if _previews is None:
        _previews = bpy.utils.previews.new()
    if pose_id not in _previews:
        path = THUMBS / entry["vignette"]
        if not path.is_file():
            return 0
        _previews.load(pose_id, str(path), "IMAGE")
    return _previews[pose_id].icon_id


def _pose_items(self, context):
    return [(row["id"], row["label"], row["source"], 0, i) for i, row in enumerate(face.gallery(context.scene))]


class HUMANLOOM_OT_face_pose_apply(bpy.types.Operator):
    bl_idname = "humanloom.face_pose_apply"
    bl_label = "Appliquer la pose"
    bl_description = "Applique la pose du visage (commandes, mâchoire, langue, regard)"
    bl_options = {"REGISTER", "UNDO"}
    pose_id: bpy.props.StringProperty()

    @classmethod
    def poll(cls, context):
        return _body(context) is not None

    def execute(self, context):
        rows = {r["id"]: r for r in face.gallery(context.scene)}
        if self.pose_id not in rows:
            self.report({"ERROR"}, "Pose inconnue : " + self.pose_id)
            return {"CANCELLED"}
        face.apply_pose(_body(context), rows[self.pose_id]["pose"])
        return {"FINISHED"}


class HUMANLOOM_OT_face_pose_favorite(bpy.types.Operator):
    bl_idname = "humanloom.face_pose_favorite"
    bl_label = "Favori"
    bl_description = "Ajoute ou retire la pose des favoris (enregistrés dans la scène)"
    bl_options = {"REGISTER", "UNDO"}
    pose_id: bpy.props.StringProperty()

    def execute(self, context):
        face.toggle_favorite(context.scene, self.pose_id)
        return {"FINISHED"}


class HUMANLOOM_OT_face_pose_save(bpy.types.Operator):
    bl_idname = "humanloom.face_pose_save"
    bl_label = "Enregistrer la pose actuelle"
    bl_description = "Enregistre le visage actuel (commandes, mâchoire, langue) dans la galerie de cette scène"
    bl_options = {"REGISTER", "UNDO"}
    name: bpy.props.StringProperty(name="Nom", default="Ma pose")

    @classmethod
    def poll(cls, context):
        return _body(context) is not None

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        face.save_pose(context.scene, self.name.strip() or "Ma pose", face.read_pose(_body(context)))
        return {"FINISHED"}


class HUMANLOOM_OT_face_pose_mix(bpy.types.Operator):
    bl_idname = "humanloom.face_pose_mix"
    bl_label = "Appliquer le mélange"
    bl_description = "Applique le mélange linéaire des deux poses choisies selon le curseur"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return _body(context) is not None

    def execute(self, context):
        wm = context.window_manager
        rows = {r["id"]: r["pose"] for r in face.gallery(context.scene)}
        if wm.hl_face_mix_a not in rows or wm.hl_face_mix_b not in rows:
            self.report({"ERROR"}, "Choisissez deux poses.")
            return {"CANCELLED"}
        face.apply_pose(_body(context), face.mix_poses(rows[wm.hl_face_mix_a], rows[wm.hl_face_mix_b], wm.hl_face_mix_factor))
        return {"FINISHED"}


class HUMANLOOM_OT_face_bake_shapes(bpy.types.Operator):
    bl_idname = "humanloom.face_bake_shapes"
    bl_label = "Cuire les formes pour l'export"
    bl_description = "Crée une copie de la cage du corps avec une forme par commande de visage et par coefficient ARKit couvert (export vers d'autres logiciels)"
    bl_options = {"REGISTER", "UNDO"}
    arkit: bpy.props.BoolProperty(name="Noms ARKit", default=True)

    @classmethod
    def poll(cls, context):
        return _body(context) is not None

    def execute(self, context):
        obj, report = face.bake_shapes(_body(context), arkit=self.arkit)
        self.report({"INFO"}, f"{len(report['formes'])} formes ({report['arkit_cuits']} ARKit) sur « {obj.name} ».")
        return {"FINISHED"}


class HUMANLOOM_OT_face_clip(bpy.types.Operator):
    bl_idname = "humanloom.face_clip"
    bl_label = "Créer un clip facial"
    bl_description = "Crée un clip de la pose A à la pose B (piste NLA « Visage », indépendante de l'animation du corps)"
    bl_options = {"REGISTER", "UNDO"}
    start: bpy.props.IntProperty(name="Image de départ", default=1)
    length: bpy.props.IntProperty(name="Durée (images)", default=24, min=1)
    name: bpy.props.StringProperty(name="Nom", default="Visage")

    @classmethod
    def poll(cls, context):
        return _body(context) is not None

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        wm = context.window_manager
        rows = {r["id"]: r["pose"] for r in face.gallery(context.scene)}
        if wm.hl_face_mix_a not in rows or wm.hl_face_mix_b not in rows:
            self.report({"ERROR"}, "Choisissez les poses A et B dans le mélangeur.")
            return {"CANCELLED"}
        strips = face.build_clip(_body(context), self.name, [(self.start, rows[wm.hl_face_mix_a]), (self.start + self.length, rows[wm.hl_face_mix_b])], start=self.start)
        self.report({"INFO"}, f"{len(strips)} bande(s) dans la piste « {face.FACE_TRACK} ».")
        return {"FINISHED"}


class HUMANLOOM_OT_face_clip_remove(bpy.types.Operator):
    bl_idname = "humanloom.face_clip_remove"
    bl_label = "Retirer les clips faciaux"
    bl_description = "Supprime la piste NLA « Visage » et remet le visage au neutre ; l'animation du corps n'est pas touchée"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        body = _body(context)
        return body is not None and bool(face.clip_strips(body))

    def execute(self, context):
        face.remove_clips(_body(context))
        return {"FINISHED"}


class HUMANLOOM_OT_face_arkit_report(bpy.types.Operator):
    bl_idname = "humanloom.face_arkit_report"
    bl_label = "Couverture ARKit"
    bl_description = "Affiche dans la console système la table des 52 coefficients ARKit et ce que le visage en couvre (aucun coefficient inventé)"

    def execute(self, context):
        report = face.arkit_report()
        print(json.dumps(report, indent=1, ensure_ascii=False))
        self.report({"INFO"}, f"ARKit : {report['par_categorie']} ; couverture pondérée {report['couverture_ponderee']:.0%} (voir la console).")
        return {"FINISHED"}


class HUMANLOOM_PT_face_gallery(bpy.types.Panel):
    bl_label = "Poses du visage"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Humain"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        body = _body(context)
        return body is not None and human.has_control(body, "smile_L")

    def draw(self, context):
        layout, wm, body = self.layout, context.window_manager, _body(context)
        rows = face.gallery(context.scene)
        shown = [r for r in rows if wm.hl_face_filter in ("ALL", r["categorie"]) and (not wm.hl_face_only_favorites or r["favori"])]
        layout.prop(wm, "hl_face_filter", expand=True)
        layout.prop(wm, "hl_face_only_favorites")
        grid = layout.grid_flow(row_major=True, columns=3, even_columns=True, align=True)
        for row in shown:
            cell = grid.column(align=True)
            op = cell.operator("humanloom.face_pose_apply", text=row["label"], icon_value=_icon(row["id"]) if _icon(row["id"]) else 0)
            op.pose_id = row["id"]
            star = cell.operator("humanloom.face_pose_favorite", text="", icon="SOLO_ON" if row["favori"] else "SOLO_OFF")
            star.pose_id = row["id"]
        layout.operator("humanloom.face_pose_save", icon="ADD")
        box = layout.box()
        box.label(text="Mélangeur", icon="MOD_TIME")
        box.prop(wm, "hl_face_mix_a", text="A")
        box.prop(wm, "hl_face_mix_b", text="B")
        box.prop(wm, "hl_face_mix_factor", slider=True)
        box.operator("humanloom.face_pose_mix", icon="CHECKMARK")
        box.operator("humanloom.face_clip", icon="NLA")
        if face.clip_strips(body):
            box.operator("humanloom.face_clip_remove", icon="TRASH")
        tongue = face._tongue_object(body)
        if tongue is not None and tongue.data.shape_keys is not None:
            box = layout.box()
            box.label(text="Langue", icon="MOD_SMOOTH")
            for key in tongue.data.shape_keys.key_blocks:
                if key.name in dental.TONGUE_SHAPES:
                    box.prop(key, "value", text=dental.TONGUE_SHAPES[key.name][0], slider=True)
        box = layout.box()
        box.label(text="Export", icon="EXPORT")
        box.operator("humanloom.face_bake_shapes", icon="SHAPEKEY_DATA")
        box.operator("humanloom.face_arkit_report", icon="INFO")


CLASSES = (HUMANLOOM_OT_face_pose_apply, HUMANLOOM_OT_face_pose_favorite, HUMANLOOM_OT_face_pose_save, HUMANLOOM_OT_face_pose_mix, HUMANLOOM_OT_face_bake_shapes, HUMANLOOM_OT_face_clip,
           HUMANLOOM_OT_face_clip_remove, HUMANLOOM_OT_face_arkit_report, HUMANLOOM_PT_face_gallery)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    wm = bpy.types.WindowManager
    wm.hl_face_filter = bpy.props.EnumProperty(name="Catégorie", items=[("ALL", "Tout", ""), ("expression", "Expressions", ""), ("visème", "Visèmes", ""), ("utilisateur", "Mes poses", "")], default="ALL")
    wm.hl_face_only_favorites = bpy.props.BoolProperty(name="Favoris seulement", default=False)
    wm.hl_face_mix_a = bpy.props.EnumProperty(name="Pose A", items=_pose_items)
    wm.hl_face_mix_b = bpy.props.EnumProperty(name="Pose B", items=_pose_items)
    wm.hl_face_mix_factor = bpy.props.FloatProperty(name="Mélange", default=0.5, min=0.0, max=1.0, description="0 : pose A, 1 : pose B")


def unregister():
    global _previews
    wm = bpy.types.WindowManager
    for name in ("hl_face_filter", "hl_face_only_favorites", "hl_face_mix_a", "hl_face_mix_b", "hl_face_mix_factor"):
        if hasattr(wm, name):
            delattr(wm, name)
    if _previews is not None:
        bpy.utils.previews.remove(_previews)
        _previews = None
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
