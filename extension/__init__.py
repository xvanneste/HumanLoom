"""Create editable human models from the bundled realistic base."""

from pathlib import Path
import random

import bpy
import bmesh
from bpy_extras.io_utils import ExportHelper, ImportHelper

from . import anatomy, landmark_sets, character_presets, measurements, geometry_quality, surface_fix, body_profiles, age_shapes, skin_relief, groom, human
from . import accessories_ui, cloth_ui, crowd, crowd_ui, garments, garments_ui
from .animation import ui as animation_ui
from .proportions import BASE_ID, BODY_CONTROLS, FAT_CONTROLS, MUSCLE_CONTROLS, FACE_CONTROLS, CONTROLS, CURRENT_SCHEMA, FACE_COMMANDS, FACE_COMMAND_LABELS, FACE_PRESETS, bind_control, property_name

# Ancien moteur (schéma 9) : l'asset n'est plus livré dans le paquet (lot 5) ; il n'existe que dans le dépôt, sous tools/data.
# Dans une extension installée, il est absent : `human_modeling.create` refuse alors de créer un humain de l'ancien moteur.
ASSET_PATH = Path(__file__).resolve().parent.parent / "tools" / "data" / "realistic.blend"
ASSET_COLLECTION = "Realistic Human Base"
BODY_MARKER = "human_modeling_body"
MORPH_NAME = "Morphologie"
SURFACE_MODIFIER = "Human Modeling · Surface"


def active_body(context):
    """Le corps actif : humain natif (schéma 10) ou corps de l'ancien moteur."""
    return human.body_of(context.active_object)


def has_proportions(body, minimum=2):
    """Un humain natif a toujours ses réglages ; l'ancien moteur les a à partir du schéma 2."""
    return body is not None and (human.is_native(body) or body.data.get("human_modeling_schema", 0) >= minimum)


def add_smooth_preview(body):
    for obj in (body, *body.children):
        if obj.type == "MESH":
            for polygon in obj.data.polygons:
                polygon.use_smooth = True
    modifier = body.modifiers.get(SURFACE_MODIFIER)
    if modifier is None:
        modifier = body.modifiers.new(SURFACE_MODIFIER, "SUBSURF")
        modifier.levels = 1
        modifier.render_levels = 2
    # Apply fine relief to the subdivided surface, preserving its sampling.
    relief = body.modifiers.get(skin_relief.NAME)
    if relief is not None:
        stack = list(body.modifiers)
        if stack.index(modifier) > stack.index(relief):
            body.modifiers.move(stack.index(modifier), stack.index(relief))
    return modifier


class HUMANMODELING_OT_create(bpy.types.Operator):
    bl_idname = "human_modeling.create"
    bl_label = "Créer un humain"
    bl_description = "Ajoute une base humaine réaliste à la position du curseur"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT" and ASSET_PATH.exists()  # absent d'une extension installée : plus d'humain de l'ancien moteur

    def execute(self, context):
        try:
            with bpy.data.libraries.load(str(ASSET_PATH), link=False) as (source, target):
                if ASSET_COLLECTION not in source.collections:
                    self.report({"ERROR"}, "La collection du personnage est absente.")
                    return {"CANCELLED"}
                target.collections = [ASSET_COLLECTION]
        except (OSError, RuntimeError) as error:
            self.report({"ERROR"}, f"Impossible de charger la base humaine ({error}).")
            return {"CANCELLED"}

        collection = target.collections[0]
        if collection is None:
            self.report({"ERROR"}, "Le chargement de la collection a échoué.")
            return {"CANCELLED"}

        body = next((obj for obj in collection.objects if obj.get(BODY_MARKER)), None)
        if body is None:
            bpy.data.collections.remove(collection)
            self.report({"ERROR"}, "La collection ne contient aucune base humaine.")
            return {"CANCELLED"}
        context.scene.collection.children.link(collection)
        add_smooth_preview(body)
        body.location = context.scene.cursor.location
        for obj in tuple(context.selected_objects):
            obj.select_set(False)
        body.select_set(True)
        context.view_layer.objects.active = body
        return {"FINISHED"}


class HUMANMODELING_OT_height(bpy.types.Operator):
    bl_idname = "human_modeling.set_height"
    bl_label = "Régler la taille"
    bl_description = "Ajuste uniformément le corps et les yeux à la taille demandée"
    bl_options = {"REGISTER", "UNDO"}

    height: bpy.props.FloatProperty(
        name="Taille", default=1.70, min=0.000001, unit="LENGTH",
        description="Taille du modèle selon son axe vertical local",
    )

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT" and active_body(context) is not None

    def invoke(self, context, event):
        body = active_body(context)
        try:
            self.height = measurements.measure(body, context)["height_m"] / context.scene.unit_settings.scale_length
        except ValueError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        body = active_body(context)
        try:
            current = measurements.measure(body, context)["height_m"]
        except ValueError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        if current <= 0:
            self.report({"ERROR"}, "La hauteur du modèle doit être positive.")
            return {"CANCELLED"}
        body.scale *= self.height * context.scene.unit_settings.scale_length / current
        return {"FINISHED"}


class HUMANMODELING_OT_smooth(bpy.types.Operator):
    bl_idname = "human_modeling.smooth"
    bl_label = "Activer l’aperçu lissé"
    bl_description = "Ajoute une subdivision éditable à cette base humaine"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT" and active_body(context) is not None

    def execute(self, context):
        body = active_body(context)
        if body.modifiers.get(SURFACE_MODIFIER):
            self.report({"INFO"}, "L’aperçu lissé est déjà actif : réglez le niveau dans « Subdivision ».")
        add_smooth_preview(body)
        return {"FINISHED"}


class HUMANMODELING_OT_face_preset(bpy.types.Operator):
    bl_idname = "humanloom.face_preset"
    bl_label = "Expression prédéfinie"
    bl_description = "Règle les commandes d'expression du visage (combinaisons écrites par HumanLoom, non calibrées) ; « Neutre » les remet à zéro"
    bl_options = {"REGISTER", "UNDO"}
    preset: bpy.props.StringProperty(name="Expression", default="neutre")

    @classmethod
    def poll(cls, context):
        body = human.body_of(context.active_object)
        return body is not None and human.is_native(body) and human.has_control(body, "smile_L")

    def execute(self, context):
        body = human.body_of(context.active_object)
        values = FACE_PRESETS.get(self.preset)
        if values is None:
            self.report({"ERROR"}, "Expression inconnue : " + self.preset)
            return {"CANCELLED"}
        from .animation import face as _face  # commandes, mâchoire (« _jaw »), regard (« _gaze ») et langue, si le squelette est installé
        _face.apply_pose(body, values)
        return {"FINISHED"}


class HUMANMODELING_OT_reset(bpy.types.Operator):
    bl_idname = "human_modeling.reset_proportions"
    bl_label = "Réinitialiser les proportions"
    bl_description = "Remet les réglages du corps et du visage à zéro"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        body = active_body(context)
        return context.mode == "OBJECT" and has_proportions(body)

    def execute(self, context):
        body = active_body(context)
        for identifier, _ in CONTROLS:
            if human.has_control(body, identifier):
                human.set_value(body, identifier, 0.0)
        human.touch(body)
        if context.area:
            context.area.tag_redraw()
        return {"FINISHED"}


class HUMANMODELING_OT_upgrade(bpy.types.Operator):
    bl_idname = "human_modeling.add_proportions"
    bl_label = "Ajouter les réglages corps et visage"
    bl_description = "Ajoute les réglages à une base humaine créée avec une version précédente"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        body = active_body(context)
        return context.mode == "OBJECT" and body is not None and not human.is_native(body) and body.data.get("human_modeling_schema", 0) < CURRENT_SCHEMA

    def execute(self, context):
        body = active_body(context)
        collection = None
        added_keys = []
        added_properties = []
        driver_backups = []
        existing_names = set(body.data.shape_keys.key_blocks.keys())
        try:
            with bpy.data.libraries.load(str(ASSET_PATH), link=False) as (_, target):
                target.collections = [ASSET_COLLECTION]
            collection = target.collections[0]
            source = next(obj for obj in collection.objects if obj.get(BODY_MARKER))
            source_eyes = sorted(source.children, key=lambda obj: obj.data.shape_keys.key_blocks["Basis"].data[0].co.x)
            eyes = sorted(
                [obj for obj in body.children if obj.type == "MESH" and obj.data.shape_keys
                 and "Morphologie" in obj.data.shape_keys.key_blocks],
                key=lambda obj: obj.data.shape_keys.key_blocks["Basis"].data[0].co.x,
            )
            if len(eyes) != 2:
                raise ValueError("Les deux yeux de la base doivent être présents.")
            pairs = [(body, source), *zip(eyes, source_eyes)]
            for current, original in pairs:
                if len(current.data.vertices) != len(original.data.vertices):
                    raise ValueError("La topologie de cette base a été modifiée.")
                current_faces = [tuple(face.vertices) for face in current.data.polygons]
                original_faces = [tuple(face.vertices) for face in original.data.polygons]
                if current_faces != original_faces:
                    raise ValueError("La topologie de cette base a été modifiée.")
            owner = body.data.shape_keys
            for identifier, label in CONTROLS:
                prop = property_name(identifier)
                matching = [
                    key for key in body.data.shape_keys.key_blocks
                    if key.name == "HM · " + identifier or key.name.startswith("HM · " + identifier + " · ")
                ]
                if (prop in owner) != bool(matching):
                    raise ValueError("Un réglage du même nom existe déjà sur cette base.")
            for identifier, label in CONTROLS:
                prop = property_name(identifier)
                if prop in owner:
                    continue
                owner[prop] = 0.0
                added_properties.append(prop)
                owner.id_properties_ui(prop).update(
                    min=-1.0, max=1.0, default=0.0, description=label,
                )
            for current, original in pairs:
                base = current.data.shape_keys.key_blocks["Basis"]
                original_base = original.data.shape_keys.key_blocks["Basis"]
                for source_key in original.data.shape_keys.key_blocks:
                    age_names = {"Enfant", "Adolescent", "Senior", "Enfant · morphologie", "Adolescent · morphologie", "Senior · morphologie"}
                    if not (source_key.name.startswith(("HM · ", "Age · ")) or source_key.name in age_names or source_key.name == "Surface · Ajustement orbital"):
                        continue
                    if source_key.name in current.data.shape_keys.key_blocks:
                        continue
                    key = current.shape_key_add(name=source_key.name)
                    added_keys.append((current, key.name))
                    for index, point in enumerate(key.data):
                        point.co = base.data[index].co + source_key.data[index].co - original_base.data[index].co
                    key.slider_min = source_key.slider_min
                    key.value = 1 if key.name == "Surface · Ajustement orbital" else 0
                    source_animation = original.data.shape_keys.animation_data
                    curve = next((curve for curve in source_animation.drivers if curve.data_path == source_key.path_from_id("value")), None) if source_animation else None
                    if curve:
                        driver = key.driver_add("value").driver
                        driver.type = "SCRIPTED"
                        for variable in curve.driver.variables:
                            new = driver.variables.new()
                            new.name = variable.name
                            new.type = "SINGLE_PROP"
                            new.targets[0].id_type = "KEY"
                            new.targets[0].id = owner
                            new.targets[0].data_path = variable.targets[0].data_path
                        driver.expression = curve.driver.expression
            if "human_modeling_age" not in owner:
                owner["human_modeling_age"] = 2.0
                added_properties.append("human_modeling_age")
                owner.id_properties_ui("human_modeling_age").update(min=0., max=3., default=2.)
            skin_relief.attach(body,source)
            from . import muscle_upgrade
            driver_backups = muscle_upgrade.refresh(body,source,existing_names)
            body.data["human_modeling_schema"] = CURRENT_SCHEMA
            body.data["human_modeling_base"] = BASE_ID
            self.report({"INFO"}, "Les réglages corps et visage sont disponibles.")
            return {"FINISHED"}
        except (OSError, RuntimeError, ValueError, StopIteration) as error:
            if driver_backups:
                from . import muscle_upgrade
                muscle_upgrade.rollback(body,driver_backups)
            for obj, name in reversed(added_keys):
                obj.shape_key_remove(obj.data.shape_keys.key_blocks[name])
            for name in added_properties:
                del body.data.shape_keys[name]
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        finally:
            if collection:
                for obj in tuple(collection.objects):
                    mesh = obj.data
                    bpy.data.objects.remove(obj, do_unlink=True)
                    if mesh.users <= int(mesh.use_fake_user):
                        bpy.data.meshes.remove(mesh)
                bpy.data.collections.remove(collection)


class HUMANMODELING_OT_save_preset(bpy.types.Operator, ExportHelper):
    bl_idname = "human_modeling.save_preset"
    bl_label = "Enregistrer le préréglage"
    bl_description = "Enregistre la morphologie, les proportions et l’échelle dans un fichier JSON"
    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(default="*.json", options={"HIDDEN"})

    @classmethod
    def poll(cls, context):
        return HUMANMODELING_OT_reset.poll(context)

    def execute(self, context):
        try:
            character_presets.write(self.filepath, character_presets.capture(active_body(context)))
        except (OSError, ValueError, TypeError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        self.report({"INFO"}, "Préréglage enregistré.")
        return {"FINISHED"}


class HUMANMODELING_OT_load_preset(bpy.types.Operator, ImportHelper):
    bl_idname = "human_modeling.load_preset"
    bl_label = "Charger un préréglage"
    bl_description = "Charge ou mélange un préréglage avec le personnage sélectionné"
    bl_options = {"REGISTER", "UNDO"}
    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(default="*.json", options={"HIDDEN"})
    factor: bpy.props.FloatProperty(
        name="Intensité", default=1.0, min=0.0, max=1.0, subtype="FACTOR",
        description="À 100 %, remplace les réglages. À 50 %, mélange les deux configurations",
    )

    @classmethod
    def poll(cls, context):
        return HUMANMODELING_OT_reset.poll(context)

    def draw(self, context):
        self.layout.prop(self, "factor")

    def execute(self, context):
        try:
            character_presets.apply(active_body(context), character_presets.read(self.filepath), self.factor)
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        self.report({"INFO"}, "Préréglage appliqué.")
        return {"FINISHED"}


class HUMANMODELING_OT_randomize(bpy.types.Operator):
    bl_idname = "human_modeling.randomize"
    bl_label = "Créer une variation"
    bl_description = "Fait varier les proportions avec une graine reproductible"
    bl_options = {"REGISTER", "UNDO"}
    seed: bpy.props.IntProperty(name="Graine", default=0, min=0, max=2147483647)
    strength: bpy.props.FloatProperty(name="Amplitude", default=.45, min=0.0, max=1.0, subtype="FACTOR")
    scope: bpy.props.EnumProperty(
        name="Zone",
        items=(("FACE", "Visage", ""), ("BODY", "Corps", ""), ("ALL", "Corps et visage", "")),
        default="FACE",
    )

    @classmethod
    def poll(cls, context):
        return HUMANMODELING_OT_reset.poll(context)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        body = active_body(context)
        scopes = {"FACE": FACE_CONTROLS, "BODY": BODY_CONTROLS + FAT_CONTROLS + MUSCLE_CONTROLS, "ALL": CONTROLS}
        for identifier, _ in scopes[self.scope]:
            rng = random.Random(f"{self.seed}:{identifier}")
            value = rng.uniform(-self.strength, self.strength)
            if human.has_control(body, identifier):
                human.set_value(body, identifier, value)
        human.touch(body)
        return {"FINISHED"}


class HUMANMODELING_PT_model(bpy.types.Panel):
    bl_label = "HumanLoom · Modélisation"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Humain"

    def draw(self, context):
        layout = self.layout
        layout.operator(human.HUMANLOOM_OT_create.bl_idname, icon="ADD", text="Créer un humain")
        body = active_body(context)
        if body is not None and human.is_native(body):
            state = human.modifier_status(body)[0]
            if state != "ok":
                box = layout.box()
                box.alert = state != "renamed"
                box.label(text={"renamed": "Modificateur « HL Human » renommé.", "missing": "Modificateur « HL Human » absent.",
                                "duplicate": "Modificateur « HL Human » en double.", "incompatible": "Groupe de nœuds incompatible."}[state], icon="ERROR")
                if state == "renamed":
                    box.operator(human.HUMANLOOM_OT_repair_modifier.bl_idname, icon="TOOL_SETTINGS")
            elif body.animation_data is not None:
                layout.operator(human.HUMANLOOM_OT_facade_animation_to_native.bl_idname, icon="DRIVER")
        if body and (human.is_native(body) or body.data.shape_keys):
            if human.has_control(body, "sex"):
                human.draw_control(layout, body, "sex", "Morphologie")
                row = layout.row()
                row.label(text="Féminine")
                row.alignment = "EXPAND"
                right = row.row()
                right.alignment = "RIGHT"
                right.label(text="Masculine")
            layout.operator(HUMANMODELING_OT_height.bl_idname)
            surface = body.modifiers.get(SURFACE_MODIFIER)
            if surface:
                layout.prop(surface, "levels", text="Subdivision")
            else:
                layout.operator(HUMANMODELING_OT_smooth.bl_idname)
            if not human.is_native(body) and body.data.get("human_modeling_schema", 0) < CURRENT_SCHEMA:
                layout.operator(HUMANMODELING_OT_upgrade.bl_idname)
            if human.is_native(body):
                layout.operator(human.HUMANLOOM_OT_duplicate.bl_idname, icon="DUPLICATE")
            if has_proportions(body):
                layout.operator(HUMANMODELING_OT_reset.bl_idname, icon="LOOP_BACK")
                layout.operator(HUMANMODELING_OT_randomize.bl_idname)


class HUMANMODELING_PT_body(bpy.types.Panel):
    bl_label = "Corps"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Humain"
    bl_parent_id = "HUMANMODELING_PT_model"

    @classmethod
    def poll(cls, context):
        return has_proportions(active_body(context))

    def draw(self, context):
        body = active_body(context)
        for identifier, label in BODY_CONTROLS:
            if identifier == "corpulence" and human.has_control(body, "whole_body"):
                continue
            if human.has_control(body, identifier):
                human.draw_control(self.layout, body, identifier, label)


class HUMANMODELING_OT_body_profile(bpy.types.Operator):
    bl_idname = "human_modeling.body_profile"
    bl_label = "Appliquer une silhouette"
    bl_description = "Règle corpulence, volumes adipeux et musculature ; remet les ajustements régionaux à zéro"
    bl_options = {"REGISTER", "UNDO"}

    profile: bpy.props.EnumProperty(
        name="Silhouette", items=tuple((key, value[0], "Point de départ artistique modifiable") for key, value in body_profiles.PROFILES.items()),
    )

    @classmethod
    def poll(cls, context):
        body = active_body(context)
        return context.mode == "OBJECT" and has_proportions(body, CURRENT_SCHEMA)

    def execute(self, context):
        body = active_body(context)
        _, fat, muscle = body_profiles.PROFILES[self.profile]
        if human.has_control(body, "corpulence"):
            human.set_value(body, "corpulence", 0.)
        for identifier, _ in FAT_CONTROLS:
            if human.has_control(body, identifier):
                human.set_value(body, identifier, 0.)
        for identifier, _ in MUSCLE_CONTROLS:
            human.set_value(body, identifier, muscle if identifier == "muscles" else max(muscle,0.) if identifier == "muscle_definition" else 0.)
        human.set_value(body, "whole_body", body_profiles.WHOLE_BODY[self.profile])
        human.touch(body)
        return {"FINISHED"}


class HUMANMODELING_PT_silhouettes(bpy.types.Panel):
    bl_label = "Silhouettes"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Humain"
    bl_parent_id = "HUMANMODELING_PT_model"

    @classmethod
    def poll(cls,context):
        return HUMANMODELING_OT_body_profile.poll(context)

    def draw(self,context):
        grid=self.layout.grid_flow(columns=2,align=True)
        for identifier,(label,_,_) in body_profiles.PROFILES.items():
            grid.operator(HUMANMODELING_OT_body_profile.bl_idname,text=label).profile=identifier


class HUMANMODELING_PT_muscles(bpy.types.Panel):
    bl_label = "Musculature"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Humain"
    bl_parent_id = "HUMANMODELING_PT_model"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        body = active_body(context)
        return body is not None and human.has_control(body, "muscles")

    def draw(self, context):
        body = active_body(context)
        self.layout.label(text="Volumes artistiques")
        for identifier, label in MUSCLE_CONTROLS:
            if human.has_control(body, identifier):
                human.draw_control(self.layout, body, identifier, label)


class HUMANMODELING_OT_age_reference(bpy.types.Operator):
    bl_idname = "human_modeling.age_reference"
    bl_label = "Choisir une forme d’âge"
    bl_options = {"REGISTER", "UNDO"}
    stage: bpy.props.IntProperty(min=0, max=3, default=2)

    @classmethod
    def poll(cls, context):
        body = active_body(context)
        return context.mode == "OBJECT" and body is not None and human.has_control(body, "age")

    def execute(self, context):
        body = active_body(context)
        human.set_value(body, "age", float(self.stage))
        human.touch(body)
        return {"FINISHED"}


class HUMANMODELING_OT_calibrate_age_height(bpy.types.Operator):
    bl_idname = "human_modeling.calibrate_age_height"
    bl_label = "Appliquer la stature de référence"
    bl_description = "Ajuste la stature à la médiane publiée du repère d’âge ; les autres proportions restent artistiques"
    bl_options = {"REGISTER", "UNDO"}
    sex: bpy.props.EnumProperty(name="Catégorie de la source", items=(("F","Féminine",""),("M","Masculine","")))

    @classmethod
    def poll(cls,context):
        return HUMANMODELING_OT_age_reference.poll(context)

    def execute(self,context):
        body=active_body(context)
        try:
            ref=age_shapes.stature_reference(body,self.sex)
            measured=measurements.measure(body,context)["height_m"]
            if measured<=0:raise ValueError("Stature mesurable absente.")
            body.scale *= (ref["height_cm"]/100)/measured
            self.report({"INFO"},f"Stature ajustée à {ref['height_cm']:.1f} cm. Autres proportions non calibrées.")
        except (OSError,ValueError) as error:
            self.report({"ERROR"},str(error));return {"CANCELLED"}
        return {"FINISHED"}


class HUMANMODELING_PT_age(bpy.types.Panel):
    bl_label = "Âge · formes de référence"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Humain"
    bl_parent_id = "HUMANMODELING_PT_model"

    @classmethod
    def poll(cls, context):
        body = active_body(context)
        return body is not None and human.has_control(body, "age")

    def draw(self, context):
        body = active_body(context)
        row = self.layout.row(align=True)
        for index, label in enumerate(("5 ans", "15 ans", "30 ans", "75 ans")):
            row.operator(HUMANMODELING_OT_age_reference.bl_idname, text=label).stage = index
        human.draw_control(self.layout, body, "age", "Transition")
        self.layout.label(text="Interpolation de formes · amplitude artistique")
        row=self.layout.row(align=True)
        row.operator(HUMANMODELING_OT_calibrate_age_height.bl_idname,text="Stature source F").sex="F"
        row.operator(HUMANMODELING_OT_calibrate_age_height.bl_idname,text="Stature source M").sex="M"


class HUMANMODELING_PT_fat(bpy.types.Panel):
    bl_label = "Corpulence et tissus"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Humain"
    bl_parent_id = "HUMANMODELING_PT_model"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        body = active_body(context)
        return body is not None and human.has_control(body, "adiposity")

    def draw(self, context):
        body = active_body(context)
        for identifier, label in FAT_CONTROLS:
            # body_mass is redundant with whole_body (cosine 0.81, I-46): kept in the file, hidden unless legacy controls are shown.
            if identifier == "body_mass" and human.has_control(body, "whole_body"):
                continue
            if human.has_control(body, identifier):
                human.draw_control(self.layout, body, identifier, label)
        if human.has_control(body, "whole_body") and not human.is_native(body):
            self.layout.prop(context.window_manager, "human_modeling_show_legacy", text="Afficher les contrôles hérités")


class HUMANMODELING_PT_legacy_volumes(bpy.types.Panel):
    bl_label = "Volumes des anciennes versions"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Humain"
    bl_parent_id = "HUMANMODELING_PT_fat"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        body = active_body(context)
        # Schéma 10 : `corpulence` et `body_mass` n'existent plus (lot 3) ; ce panneau ne concerne que l'ancien moteur.
        return body is not None and not human.is_native(body) and human.has_control(body, "whole_body") and context.window_manager.human_modeling_show_legacy

    def draw(self, context):
        body = active_body(context)
        for identifier, label in (("corpulence", "Volume initial"), ("body_mass", "Volume 0.12")):
            human.draw_control(self.layout, body, identifier, label)


class HUMANMODELING_PT_face(bpy.types.Panel):
    bl_label = "Visage"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Humain"
    bl_parent_id = "HUMANMODELING_PT_model"

    @classmethod
    def poll(cls, context):
        return HUMANMODELING_PT_body.poll(context)

    def draw(self, context):
        # Controls are drawn by the sub-panels below; any control missing from FACE_GROUPS still appears here.
        body = active_body(context)
        grouped = {identifier for _, _, identifiers in FACE_GROUPS for identifier in identifiers}
        for identifier, label in FACE_CONTROLS:
            if identifier not in grouped and human.has_control(body, identifier):
                human.draw_control(self.layout, body, identifier, label)


FACE_GROUPS = (
    ("eyes", "Yeux", ("eye_spacing", "eye_height", "eyelid_aperture")),
    ("nose", "Nez", ("nose_length", "nose_width", "nose_bridge")),
    ("mouth", "Bouche et lèvres", ("mouth", "lips", "lip_thickness", "mouth_corner")),
    ("jaw", "Mâchoire et menton", ("jaw", "jaw_angle", "chin")),
    ("ears", "Oreilles", ("ears_size", "ears_angle")),
    ("head", "Tête et front", ("head_width", "head_height", "forehead", "cheeks", "facial_asymmetry")),
    ("skin", "Peau", ("skin_relief",)),
)


class HUMANMODELING_PT_face_group(bpy.types.Panel):
    """Base of the face sub-panels (not registered): subclasses give bl_label and identifiers."""
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Humain"
    bl_parent_id = "HUMANMODELING_PT_face"
    bl_options = {"DEFAULT_CLOSED"}
    identifiers = ()

    @classmethod
    def poll(cls, context):
        return HUMANMODELING_PT_face.poll(context)

    def draw(self, context):
        body = active_body(context)
        labels = {**dict(FACE_CONTROLS), **FACE_COMMAND_LABELS}
        if "expressions" in self.__class__.__name__:
            row = self.layout.row(align=True)
            for key in FACE_PRESETS:
                row.operator("humanloom.face_preset", text=key.capitalize()).preset = key
        for identifier in self.identifiers:
            if not human.has_control(body, identifier):
                continue
            row = self.layout.row()
            if identifier == "skin_relief":
                # The Displace modifier is driven by max(0, stage - 2): no effect up to the 30-year reference.
                inactive = human.get_value(body, "age", 0.) <= 2.
                row.active = not inactive
            human.draw_control(row, body, identifier, labels[identifier])
            if identifier == "skin_relief" and inactive:
                self.layout.label(text="Sans effet avant 30 ans (âge > 2,00)", icon="INFO")


def _face_group_class(key, label, identifiers):
    return type(f"HUMANMODELING_PT_face_{key}", (HUMANMODELING_PT_face_group,), {"bl_label": label, "identifiers": identifiers})


FACE_GROUP_CLASSES = tuple(_face_group_class(*group) for group in FACE_GROUPS)
# Expressions (commandes pilotes du groupe de nœuds) : sous-panneau à part, hors de FACE_GROUPS (ces commandes ne sont pas des contrôles de morphologie)
FACE_EXPRESSIONS_CLASS = _face_group_class("expressions", "Expressions (commandes pilotes)", tuple(c for c in FACE_COMMANDS if c != "mouth_open"))


class HUMANMODELING_PT_presets(bpy.types.Panel):
    bl_label = "Préréglages"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Humain"
    bl_parent_id = "HUMANMODELING_PT_model"

    @classmethod
    def poll(cls, context):
        return HUMANMODELING_OT_reset.poll(context)

    def draw(self, context):
        self.layout.operator(HUMANMODELING_OT_save_preset.bl_idname, icon="EXPORT")
        self.layout.operator(HUMANMODELING_OT_load_preset.bl_idname, icon="IMPORT")


class HUMANMODELING_OT_reference_height(bpy.types.Operator):
    bl_idname = "human_modeling.reference_height"
    bl_label = "Appliquer la stature de référence"
    bl_description = "Ajuste uniformément la hauteur au percentile adulte sélectionné"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT" and active_body(context) is not None

    def execute(self, context):
        body = active_body(context)
        try:
            expected = measurements.target(body)
            if expected is None:
                raise ValueError("Ce percentile n’est pas publié pour ce groupe.")
            current = measurements.measure(body, context)["height_m"]
            if current <= 0:
                raise ValueError("La hauteur du corps doit être positive.")
            body.scale *= (expected / 100) / current
        except (OSError, ValueError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}


class HUMANMODELING_OT_measurement_report(bpy.types.Operator, ExportHelper):
    bl_idname = "human_modeling.measurement_report"
    bl_label = "Exporter le contrôle dimensionnel"
    bl_description = "Enregistre les mesures, la référence publiée et l’écart de stature"
    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(default="*.json", options={"HIDDEN"})

    @classmethod
    def poll(cls, context):
        return HUMANMODELING_OT_reference_height.poll(context)

    def execute(self, context):
        try:
            body = active_body(context)
            character_presets.write_json(self.filepath, measurements.report(body, context))
        except (OSError, ValueError, TypeError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        self.report({"INFO"}, "Contrôle dimensionnel enregistré.")
        return {"FINISHED"}


class HUMANMODELING_OT_mark_pelvis(bpy.types.Operator):
    bl_idname = "human_modeling.mark_pelvis"
    bl_label = "Placer le repère bassin"
    bl_description = "Attache un repère au sommet sélectionné. Son placement anatomique est manuel"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.mode == "EDIT_MESH" and active_body(context) is context.active_object

    def execute(self, context):
        body = context.active_object
        mesh = bmesh.from_edit_mesh(body.data)
        mesh.verts.ensure_lookup_table()
        mesh.verts.index_update()
        selected = [vertex for vertex in mesh.verts if vertex.select]
        if len(selected) != 1:
            self.report({"ERROR"}, "Sélectionnez un seul sommet pour placer le repère.")
            return {"CANCELLED"}
        try:
            anatomy.attach(body, "pelvis", selected[0].index)
        except ValueError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}


class HUMANMODELING_OT_mark_anatomy(bpy.types.Operator):
    bl_idname = "human_modeling.mark_anatomy"
    bl_label = "Placer sur le sommet sélectionné"
    bl_description = "Place ou remplace le repère choisi sur un seul sommet du corps"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return HUMANMODELING_OT_mark_pelvis.poll(context)

    def execute(self, context):
        body = context.active_object
        mesh = bmesh.from_edit_mesh(body.data)
        mesh.verts.ensure_lookup_table()
        mesh.verts.index_update()
        selected = [vertex for vertex in mesh.verts if vertex.select]
        if len(selected) != 1:
            self.report({"ERROR"}, "Sélectionnez un seul sommet du corps.")
            return {"CANCELLED"}
        try:
            anatomy.attach(body, body.hm_landmark, selected[0].index)
        except ValueError as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}


class HUMANMODELING_OT_fit_measurement(bpy.types.Operator):
    bl_idname = "human_modeling.fit_measurement"
    bl_label = "Ajuster la dimension"
    bl_description = "Ajuste le réglage associé, dans ses limites, à la dimension demandée"
    bl_options = {"REGISTER", "UNDO"}

    measurement: bpy.props.EnumProperty(name="Mesure", items=anatomy.MEASURES)
    target_cm: bpy.props.FloatProperty(name="Dimension cible (cm)", min=.001, default=80, precision=2)

    @classmethod
    def poll(cls, context):
        body = active_body(context)
        return context.mode == "OBJECT" and has_proportions(body)

    def invoke(self, context, event):
        try:
            self.target_cm = anatomy.value(active_body(context), context, self.measurement) * 100
        except (ValueError, RuntimeError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        try:
            result = anatomy.fit(active_body(context), context, self.measurement, self.target_cm / 100)
        except (ValueError, RuntimeError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        unit = "%" if self.measurement == "pelvis_ratio" else "cm"
        self.report({"INFO"}, f"Dimension obtenue : {result * 100:.2f} {unit}.")
        return {"FINISHED"}

    def draw(self, context):
        label = "Sol → repère / stature (%)" if self.measurement == "pelvis_ratio" else "Dimension cible (cm)"
        self.layout.prop(self, "target_cm", text=label)
        self.layout.label(text="Un seul réglage est ajusté, dans ses limites.")


class HUMANMODELING_PT_anatomy(bpy.types.Panel):
    bl_label = "Repères et dimensions locales"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Humain"
    bl_parent_id = "HUMANMODELING_PT_model"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return active_body(context) is not None

    def draw(self, context):
        body = active_body(context)
        layout = self.layout
        layout.label(text="Placement anatomique manuel")
        layout.prop(body, "hm_landmark", text="Repère")
        if context.mode == "EDIT_MESH":
            layout.operator(HUMANMODELING_OT_mark_anatomy.bl_idname)
            layout.label(text="Un seul sommet, puis placer le repère")
            return
        layout.label(text="Placer les repères en mode Édition")
        if context.mode != "OBJECT":
            return
        row = layout.row(align=True)
        row.operator(HUMANMODELING_OT_save_landmarks.bl_idname, text="Exporter les repères")
        row.operator(HUMANMODELING_OT_load_landmarks.bl_idname, text="Importer")
        layout.operator(HUMANMODELING_OT_mirror_landmarks.bl_idname)
        layout.label(text="Vérifier le placement après tout transfert")
        try:
            data = anatomy.local_report(body, context)
        except (ValueError, RuntimeError) as error:
            layout.label(text=str(error), icon="ERROR")
            return
        if any(point.get("status") == "mirrored_review" for point in data["landmarks"].values()):
            layout.label(text="Repères symétrisés à vérifier", icon="INFO")
        for key, label, _ in anatomy.MEASURES:
            if key == "pelvis_ratio":
                continue
            entry = data["sections" if key in anatomy.SECTION_IDS else "distances"].get(key)
            if not entry:
                continue
            box = layout.box()
            box.label(text=label)
            if "error" in entry:
                box.label(text=entry["error"], icon="ERROR")
                continue
            amount = entry["perimeter_m" if key in anatomy.SECTION_IDS else "distance_m"]
            row = box.row(align=True)
            row.label(text=f"{amount * 100:.2f} cm")
            row.operator(HUMANMODELING_OT_fit_measurement.bl_idname, text="Ajuster").measurement = key
        if "pelvis" in data["landmarks"]:
            try:
                ratio = anatomy.value(body, context, "pelvis_ratio")
                box = layout.box()
                box.label(text=f"Sol → repère / stature · {ratio * 100:.2f} %")
                box.operator(HUMANMODELING_OT_fit_measurement.bl_idname, text="Ajuster la proportion").measurement = "pelvis_ratio"
            except ValueError as error:
                layout.label(text=str(error), icon="ERROR")
        layout.label(text="Coupes selon les axes locaux du corps")
        layout.label(text="Dimensions sans norme d’âge associée")


class HUMANMODELING_OT_save_landmarks(bpy.types.Operator, ExportHelper):
    bl_idname = "human_modeling.save_landmarks"
    bl_label = "Exporter les repères"
    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(default="*.json", options={"HIDDEN"})

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT" and active_body(context) is not None

    def execute(self, context):
        try:
            character_presets.write_json(self.filepath, landmark_sets.capture(active_body(context)))
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        self.report({"INFO"}, "Repères exportés avec l’empreinte de leur topologie.")
        return {"FINISHED"}


class HUMANMODELING_OT_load_landmarks(bpy.types.Operator, ImportHelper):
    bl_idname = "human_modeling.load_landmarks"
    bl_label = "Importer les repères"
    bl_description = "Fusionne les repères sur une topologie identique. Vérifier leur placement après transfert"
    bl_options = {"REGISTER", "UNDO"}
    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(default="*.json", options={"HIDDEN"})

    @classmethod
    def poll(cls, context):
        return HUMANMODELING_OT_save_landmarks.poll(context)

    def execute(self, context):
        import json
        try:
            with open(self.filepath, encoding="utf-8") as stream:
                landmark_sets.apply(active_body(context), json.load(stream))
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        self.report({"INFO"}, "Repères importés. Vérifiez leur placement anatomique.")
        return {"FINISHED"}


class HUMANMODELING_OT_mirror_landmarks(bpy.types.Operator):
    bl_idname = "human_modeling.mirror_landmarks"
    bl_label = "Compléter les paires par symétrie"
    bl_description = "Propose les partenaires manquants du visage sur la forme neutre. Placement à vérifier"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return HUMANMODELING_OT_save_landmarks.poll(context)

    def execute(self, context):
        body = active_body(context)
        try:
            payload, added = landmark_sets.mirrored(body)
            if not added:
                self.report({"INFO"}, "Aucune paire incomplète à symétriser : rien n’a été modifié.")
                return {"FINISHED"}
            landmark_sets.apply(body, payload)
        except (ValueError, RuntimeError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        self.report({"INFO"}, f"{len(added)} repères proposés. Vérifiez-les sous plusieurs angles.")
        return {"FINISHED"}


class HUMANMODELING_PT_measurements(bpy.types.Panel):
    bl_label = "Mesures et référence"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Humain"
    bl_parent_id = "HUMANMODELING_PT_model"

    @classmethod
    def poll(cls, context):
        return active_body(context) is not None

    def draw(self, context):
        body = active_body(context)
        layout = self.layout
        if context.mode == "EDIT_MESH":
            layout.operator(HUMANMODELING_OT_mark_pelvis.bl_idname)
            return
        if context.mode != "OBJECT":
            layout.label(text="Passez en mode Objet pour mesurer.")
            return
        try:
            data = measurements.measure(body, context)
            expected = measurements.target(body)
        except (OSError, ValueError) as error:
            layout.label(text=str(error), icon="ERROR")
            return
        layout.label(text=f"Stature mesurée · {data['height_m'] * 100:.1f} cm")
        layout.label(text=f"Largeur hors tout · {data['width_m'] * 100:.1f} cm")
        segments = data.get("segments")
        if segments:
            layout.label(text=f"Sol → repère · {segments['below_landmark_m'] * 100:.1f} cm")
            layout.label(text=f"Repère → sommet · {segments['above_landmark_m'] * 100:.1f} cm")
            layout.label(text="Repère bassin placé manuellement")
        else:
            layout.label(text="Repère bassin à placer en mode Édition")
        layout.separator()
        layout.label(text="NCHS · États-Unis · 2021–2023")
        layout.prop(body, "hm_reference_group", text="Groupe d’âge")
        layout.prop(body, "hm_reference_sex", text="Sexe de référence")
        layout.prop(body, "hm_reference_percentile", text="Percentile")
        if expected is None:
            layout.label(text="Percentile non publié pour ce groupe")
        else:
            layout.label(text=f"Stature de référence · {expected:.1f} cm")
            layout.label(text=f"Écart · {data['height_m'] * 100 - expected:+.1f} cm")
            layout.operator(HUMANMODELING_OT_reference_height.bl_idname)
        layout.operator(HUMANMODELING_OT_measurement_report.bl_idname)


class HUMANMODELING_OT_check_geometry(bpy.types.Operator):
    bl_idname = "human_modeling.check_geometry"
    bl_label = "Contrôler le maillage"
    bl_description = "Contrôle le corps évalué et recherche les intersections transversales. Résultat instantané"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT" and active_body(context) is not None

    def execute(self, context):
        import json
        body = active_body(context)
        try:
            result = geometry_quality.report(body, context, include_eyes=True)
            body["hm_geometry_report"] = json.dumps(result, allow_nan=False)
        except (ValueError, RuntimeError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        self.report({"INFO"}, "Contrôle effectué. Les limites du diagnostic figurent dans le rapport.")
        return {"FINISHED"}


class HUMANMODELING_OT_export_geometry(bpy.types.Operator, ExportHelper):
    bl_idname = "human_modeling.export_geometry_report"
    bl_label = "Exporter un nouveau contrôle"
    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(default="*.json", options={"HIDDEN"})

    @classmethod
    def poll(cls, context):
        return HUMANMODELING_OT_check_geometry.poll(context)

    def execute(self, context):
        try:
            character_presets.write_json(self.filepath, geometry_quality.report(active_body(context), context, include_eyes=True))
        except (OSError, ValueError, RuntimeError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}


class HUMANMODELING_PT_geometry(bpy.types.Panel):
    bl_label = "Contrôle du maillage"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Humain"
    bl_parent_id = "HUMANMODELING_PT_model"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return active_body(context) is not None

    def draw(self, context):
        import json
        layout = self.layout
        layout.operator(HUMANMODELING_OT_check_geometry.bl_idname)
        layout.operator(HUMANMODELING_OT_export_geometry.bl_idname)
        if not human.is_native(active_body(context)) and active_body(context).data.get("human_modeling_surface_revision", 0) < surface_fix.REVISION:
            layout.operator(HUMANMODELING_OT_repair_surface.bl_idname)
        layout.label(text="Instantané · relancer après modification")
        raw = active_body(context).get("hm_geometry_report")
        if raw:
            try:
                full_report = json.loads(raw)
                geometry = full_report["geometry"]
                layout.label(text=f"Sommets évalués · {geometry['vertices']}")
                layout.label(text="Coordonnées finies" if geometry["finite_coordinates"] else "Coordonnées invalides")
                for key, label in (("components", "Composantes"), ("boundary_edges", "Bords ouverts"),
                                   ("non_manifold_edges", "Arêtes non manifold"), ("zero_area_faces", "Faces sans aire")):
                    if key in geometry:
                        layout.label(text=f"{label} · {geometry[key]}")
                intersections = geometry.get("intersections", {})
                if intersections.get("status") == "computed":
                    layout.label(text=f"Paires de triangles croisées · {intersections['crossing_triangle_pairs']}")
                else:
                    layout.label(text="Intersections non calculées")
                eye_data=full_report.get("eye_fit",{})
                if eye_data.get("status")=="computed":
                    count=sum(eye["crossing_triangle_pairs"] for eye in eye_data["eyes"])
                    layout.label(text=f"Croisements yeux/corps · {count}")
            except (TypeError, ValueError, KeyError):
                layout.label(text="Ancien rapport illisible · relancer")
        layout.label(text="Contacts coplanaires et volumes imbriqués exclus")
        layout.label(text="La revue anatomique reste nécessaire")


class HUMANMODELING_OT_repair_surface(bpy.types.Operator):
    bl_idname = "human_modeling.repair_surface"
    bl_label = "Corriger les paupières internes"
    bl_description = "Ajoute une correction réversible à la surface interne des paupières de cette base"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        # Un humain natif porte déjà la correction des paupières internes dans le groupe de nœuds.
        return HUMANMODELING_OT_check_geometry.poll(context) and not human.is_native(active_body(context))

    def execute(self, context):
        try:
            changed = surface_fix.apply(active_body(context), ASSET_PATH)
        except (OSError, ValueError, RuntimeError, StopIteration) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        self.report({"INFO"}, "Correction ajoutée dans une clé de forme distincte." if changed else "Correction déjà présente.")
        return {"FINISHED"}


CLASSES = (
    HUMANMODELING_OT_face_preset,
    HUMANMODELING_OT_create,
    HUMANMODELING_OT_height,
    HUMANMODELING_OT_smooth,
    HUMANMODELING_OT_reset,
    HUMANMODELING_OT_upgrade,
    HUMANMODELING_OT_save_preset,
    HUMANMODELING_OT_load_preset,
    HUMANMODELING_OT_randomize,
    HUMANMODELING_OT_reference_height,
    HUMANMODELING_OT_measurement_report,
    HUMANMODELING_OT_mark_pelvis,
    HUMANMODELING_OT_mark_anatomy,
    HUMANMODELING_OT_fit_measurement,
    HUMANMODELING_OT_save_landmarks,
    HUMANMODELING_OT_load_landmarks,
    HUMANMODELING_OT_mirror_landmarks,
    HUMANMODELING_OT_check_geometry,
    HUMANMODELING_OT_export_geometry,
    HUMANMODELING_OT_repair_surface,
    HUMANMODELING_OT_body_profile,
    HUMANMODELING_OT_age_reference,
    HUMANMODELING_OT_calibrate_age_height,
    HUMANMODELING_PT_model,
    HUMANMODELING_PT_silhouettes,
    HUMANMODELING_PT_body,
    HUMANMODELING_PT_age,
    HUMANMODELING_PT_fat,
    HUMANMODELING_PT_legacy_volumes,
    HUMANMODELING_PT_muscles,
    HUMANMODELING_PT_face,
    *FACE_GROUP_CLASSES,
    FACE_EXPRESSIONS_CLASS,
    HUMANMODELING_PT_presets,
    HUMANMODELING_PT_measurements,
    HUMANMODELING_PT_anatomy,
    HUMANMODELING_PT_geometry,
)


def draw_add_mesh(self, context):
    self.layout.operator(human.HUMANLOOM_OT_create.bl_idname, icon="MESH_DATA", text="Humain")


def register():
    bpy.types.Object.hm_landmark = bpy.props.EnumProperty(name="Repère anatomique", items=anatomy.LANDMARKS, default="waist_level")
    bpy.types.Object.hm_reference_group = bpy.props.EnumProperty(
        name="Groupe d’âge de référence", items=measurements.GROUPS, default="20_29",
    )
    bpy.types.Object.hm_reference_sex = bpy.props.EnumProperty(
        name="Sexe de référence", items=(("M", "Masculin", ""), ("F", "Féminin", "")), default="M",
    )
    bpy.types.Object.hm_reference_percentile = bpy.props.EnumProperty(
        name="Percentile de référence",
        items=(("P05", "5e percentile", ""), ("P50", "50e percentile", ""), ("P95", "95e percentile", "")),
        default="P50",
    )
    bpy.types.WindowManager.human_modeling_show_legacy = bpy.props.BoolProperty(
        name="Afficher les contrôles hérités", description="Affiche les volumes des anciennes versions (conservés dans les fichiers)", default=False,
    )
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    groom.register()
    human.register()
    animation_ui.register()
    crowd_ui.register()
    crowd.register_variant_applier("outfit", garments.crowd_outfit)  # variante de foule « outfit » : clés de pièces procédurales
    garments_ui.register()
    accessories_ui.register()
    cloth_ui.register()
    bpy.types.VIEW3D_MT_mesh_add.append(draw_add_mesh)


def unregister():
    cloth_ui.unregister()
    accessories_ui.unregister()
    garments_ui.unregister()
    crowd.VARIANT_APPLIERS.pop("outfit", None)
    crowd_ui.unregister()
    animation_ui.unregister()
    human.unregister()
    groom.unregister()
    bpy.types.VIEW3D_MT_mesh_add.remove(draw_add_mesh)
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
    del bpy.types.WindowManager.human_modeling_show_legacy
    del bpy.types.Object.hm_reference_percentile
    del bpy.types.Object.hm_reference_sex
    del bpy.types.Object.hm_reference_group
    del bpy.types.Object.hm_landmark
