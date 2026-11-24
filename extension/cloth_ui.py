"""Interface de la simulation de tissu (lot V4) : panneau « Tissu » (robes et jupes) : activer, cuire, vider, désactiver. Fonctionnalité EXPÉRIMENTALE de Blender 5.2 ; jamais pour la foule."""
import bpy

from . import cloth_sim, garments, human


def _body(context):
    body = human.body_of(context.active_object)
    return body if human.is_native(body) else None


def _piece(context, key):
    body = _body(context)
    return next((g for g in garments.garments_of(body) if g[garments.MARKER] == key), None) if body is not None else None


class _PieceOperator(bpy.types.Operator):
    bl_options = {"REGISTER", "UNDO"}
    piece: bpy.props.StringProperty()

    @classmethod
    def poll(cls, context):
        return _body(context) is not None

    def run(self, garment):
        raise NotImplementedError

    def execute(self, context):
        garment = _piece(context, self.piece)
        if garment is None:
            self.report({"ERROR"}, "Pièce absente : " + self.piece)
            return {"CANCELLED"}
        try:
            message = self.run(garment)
        except (ValueError, RuntimeError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        if message:
            self.report({"INFO"}, message)
        return {"FINISHED"}


class HUMANLOOM_OT_cloth_enable(_PieceOperator):
    bl_idname = "humanloom.cloth_enable"
    bl_label = "Activer la simulation"
    bl_description = "Ajoute la simulation de tissu native (Cloth Dynamics, expérimental) à la pièce ; le corps reçoit un Collider après son armature"

    def run(self, garment):
        cloth_sim.enable(garment)
        return "Simulation activée (≈ 40–60 ms par image pour cette pièce)."


class HUMANLOOM_OT_cloth_bake(_PieceOperator):
    bl_idname = "humanloom.cloth_bake"
    bl_label = "Cuire la simulation"
    bl_description = "Cuit la simulation sur la plage d'images de la scène (cache emballé dans le .blend, rejouable à l'identique)"

    def run(self, garment):
        info = cloth_sim.bake(garment)
        return f"{info['images']} images cuites en {info['duree_s']} s."


class HUMANLOOM_OT_cloth_clear(_PieceOperator):
    bl_idname = "humanloom.cloth_clear"
    bl_label = "Vider le cache"
    bl_description = "Supprime le cache cuit (à faire avant de changer la plage, le corps ou l'animation)"

    def run(self, garment):
        cloth_sim.clear_bake(garment)
        return "Cache vidé."


class HUMANLOOM_OT_cloth_disable(_PieceOperator):
    bl_idname = "humanloom.cloth_disable"
    bl_label = "Désactiver la simulation"
    bl_description = "Retire la simulation de la pièce (elle suit alors les jambes comme un vêtement ajusté)"

    def run(self, garment):
        cloth_sim.disable(garment)
        return "Simulation retirée."


class HUMANLOOM_PT_cloth(bpy.types.Panel):
    bl_label = "Tissu (robes)"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Humain"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return _body(context) is not None

    def draw(self, context):
        layout, body = self.layout, _body(context)
        dresses = [g for g in garments.garments_of(body) if g.get("hl_garment") and garments.GARMENTS.get(g[garments.MARKER], {}).get("robe")]
        layout.label(text="Simulation native de Blender 5.2 (expérimentale)", icon="INFO")
        layout.label(text="Premier plan seulement : jamais pour la foule.")
        if not dresses:
            layout.label(text="Ajoutez une robe ou une jupe (panneau Vêtements).")
            return
        for g in dresses:
            box = layout.box()
            box.label(text=g.name, icon="MOD_CLOTH")
            key = g[garments.MARKER]
            if cloth_sim.is_enabled(g):
                rng = cloth_sim.baked_range(g)
                box.label(text=f"Cuite : images {rng[0]} à {rng[1]}" if rng else "Non cuite (calcul en direct)", icon="CHECKMARK" if rng else "TIME")
                row = box.row(align=True)
                row.operator("humanloom.cloth_bake", text="Cuire").piece = key
                row.operator("humanloom.cloth_clear", text="Vider").piece = key
                box.operator("humanloom.cloth_disable").piece = key
            else:
                box.operator("humanloom.cloth_enable").piece = key


CLASSES = (HUMANLOOM_OT_cloth_enable, HUMANLOOM_OT_cloth_bake, HUMANLOOM_OT_cloth_clear, HUMANLOOM_OT_cloth_disable, HUMANLOOM_PT_cloth)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
