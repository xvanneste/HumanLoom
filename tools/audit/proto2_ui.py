import sys, types, json
import bpy
from pathlib import Path

SP = Path((__import__("os").environ.get("HL_SCRATCHPAD", "scratchpad") + r""))
sys.path.insert(0, str(SP / "hl"))
import extension
for n in ("bl_ext", "bl_ext.user_default"):
    sys.modules.setdefault(n, types.ModuleType(n))
sys.modules["bl_ext.user_default.human_modeling"] = extension
extension.register()
from extension.proportions import BODY_CONTROLS, FACE_CONTROLS

ALL = [c[0] for c in BODY_CONTROLS + FACE_CONTROLS]
LABEL = dict(BODY_CONTROLS + FACE_CONTROLS)

def make_prop(name):
    def get(self):
        return float(self.id_data.data.shape_keys.get("hm_" + name, 0.0))
    def set_(self, v):
        k = self.id_data.data.shape_keys
        k["hm_" + name] = float(v)
        k.update_tag()
    return bpy.props.FloatProperty(name=LABEL[name], min=-1.0, max=1.0, default=0.0, get=get, set=set_, description="HumanLoom prototype: " + name)

Facade = type("Facade", (bpy.types.PropertyGroup,), {"__annotations__": {i: make_prop(i) for i in ALL}})

def is_human(obj):
    return obj is not None and obj.type == "MESH" and bool(obj.get("human_modeling_body"))

def draw_human(layout, obj):
    layout.use_property_split = True
    layout.use_property_decorate = True
    col = layout.column(heading="Body")
    for i, _ in BODY_CONTROLS:
        col.prop(obj.hlface, i, slider=True)
    box = layout.column(heading="Face")
    for i, _ in FACE_CONTROLS[:6]:
        box.prop(obj.hlface, i, slider=True)

class PROTO_PT_object(bpy.types.Panel):
    bl_label = "Human"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    @classmethod
    def poll(cls, context):
        return is_human(context.object)
    def draw(self, context):
        draw_human(self.layout, context.object)

class PROTO_PT_side(bpy.types.Panel):
    bl_label = "Human (sidebar)"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Humain"
    @classmethod
    def poll(cls, context):
        return is_human(context.object)
    def draw(self, context):
        draw_human(self.layout, context.object)

class PROTO_OT_add(bpy.types.Operator):
    bl_idname = "protohl.add_human"
    bl_label = "Human"
    bl_options = {"REGISTER", "UNDO"}
    sex: bpy.props.FloatProperty(name="Sex", min=0.0, max=1.0, default=1.0)
    age: bpy.props.FloatProperty(name="Age stage", min=0.0, max=3.0, default=2.0)
    def execute(self, context):
        bpy.ops.human_modeling.create()
        b = context.object
        b.data.shape_keys.key_blocks["Morphologie"].value = self.sex
        b.data.shape_keys["human_modeling_age"] = self.age
        b.data.shape_keys.update_tag()
        return {"FINISHED"}

class PROTO_OT_guarded(bpy.types.Operator):
    bl_idname = "protohl.guarded"
    bl_label = "Guarded action"
    @classmethod
    def poll(cls, context):
        if not is_human(context.object):
            cls.poll_message_set("Select a HumanLoom body first.")
            return False
        return True
    def execute(self, context):
        return {"FINISHED"}

class PROTO_MT_add(bpy.types.Menu):
    bl_label = "Human"
    def draw(self, context):
        self.layout.operator("protohl.add_human", text="Adult").age = 2.0
        self.layout.operator("protohl.add_human", text="Child").age = 0.0

def add_menu(self, context):
    self.layout.menu("PROTO_MT_add", icon="OUTLINER_OB_ARMATURE")

classes = (Facade,)
bpy.utils.register_class(Facade)
bpy.types.Object.hlface = bpy.props.PointerProperty(type=Facade)
for c in (PROTO_PT_object, PROTO_PT_side, PROTO_OT_add, PROTO_OT_guarded, PROTO_MT_add):
    bpy.utils.register_class(c)
bpy.types.VIEW3D_MT_add.append(add_menu)

wm = bpy.context.window_manager
kc = wm.keyconfigs.addon
RES = {"keymap_registered": False}
if kc:
    km = kc.keymaps.new(name="3D View", space_type="VIEW_3D")
    kmi = km.keymap_items.new("protohl.add_human", "H", "PRESS", ctrl=True, shift=True)
    RES["keymap_registered"] = True
    RES["kmi"] = kmi.to_string() if hasattr(kmi, "to_string") else "Ctrl Shift H"

state = {"n": 0}
OUT = SP / "proto_ui"
OUT.mkdir(exist_ok=True)

def view(kind):
    win = bpy.context.window_manager.windows[0]
    for a in win.screen.areas:
        if a.type == kind:
            return win, a

def tick():
    n = state["n"]
    state["n"] += 1
    if n == 0:
        w, a = view("VIEW_3D")
        with bpy.context.temp_override(window=w, area=a, region=next(r for r in a.regions if r.type == "WINDOW")):
            bpy.ops.protohl.add_human()
        RES["poll_guarded_with_body"] = bpy.ops.protohl.guarded.poll()
        a.spaces[0].show_region_ui = True
        return 1.5
    if n == 1:
        w, a = view("VIEW_3D")
        try:
            next(r for r in a.regions if r.type == "UI").active_panel_category = "Humain"
        except Exception as e:
            RES["category_err"] = str(e)[:100]
        w2, p = view("PROPERTIES")
        try:
            p.spaces[0].context = "OBJECT"
        except Exception as e:
            RES["context_err"] = str(e)[:100]
        return 1.5
    if n == 2:
        w, p = view("PROPERTIES")
        with bpy.context.temp_override(window=w, area=p, region=next(r for r in p.regions if r.type == "WINDOW")):
            bpy.ops.screen.screenshot_area(filepath=str(OUT / "properties_object.png"))
        w, a = view("VIEW_3D")
        with bpy.context.temp_override(window=w, area=a, region=next(r for r in a.regions if r.type == "UI")):
            bpy.ops.screen.screenshot_area(filepath=str(OUT / "sidebar.png"))
        RES["panels_registered"] = [c.bl_label for c in (PROTO_PT_object, PROTO_PT_side)]
        RES["add_menu_registered"] = True
        (OUT / "proto_ui.json").write_text(json.dumps(RES, indent=1), encoding="utf-8")
        return None
    return None

bpy.app.timers.register(tick, first_interval=2.0)
