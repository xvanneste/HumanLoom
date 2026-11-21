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
from extension.proportions import BODY_CONTROLS

LABEL = dict(BODY_CONTROLS)
RES = {}

def make_prop(name):
    def get(self):
        return float(self.id_data.data.shape_keys.get("hm_" + name, 0.0))
    def set_(self, v):
        k = self.id_data.data.shape_keys
        k["hm_" + name] = float(v)
        k.update_tag()
    return bpy.props.FloatProperty(name=LABEL[name], min=-1.0, max=1.0, default=0.0, get=get, set=set_)

Facade = type("Facade", (bpy.types.PropertyGroup,), {"__annotations__": {i: make_prop(i) for i, _ in BODY_CONTROLS}})

def is_human(o):
    return o is not None and o.type == "MESH" and bool(o.get("human_modeling_body"))

class P_PT_obj(bpy.types.Panel):
    bl_label = "Human"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"
    @classmethod
    def poll(cls, context):
        return is_human(context.object)
    def draw(self, context):
        self.layout.use_property_split = True
        for i, _ in BODY_CONTROLS:
            self.layout.prop(context.object.hlface, i, slider=True)

class P_OT_add(bpy.types.Operator):
    bl_idname = "protohl.add_human"
    bl_label = "Human"
    bl_options = {"REGISTER", "UNDO"}
    sex: bpy.props.FloatProperty(name="Sex", min=0.0, max=1.0, default=1.0)
    age: bpy.props.FloatProperty(name="Age stage", min=0.0, max=3.0, default=2.0)
    shoulders: bpy.props.FloatProperty(name="Shoulders", min=-1.0, max=1.0, default=0.0)
    def execute(self, context):
        bpy.ops.human_modeling.create()
        b = context.object
        k = b.data.shape_keys
        k.key_blocks["Morphologie"].value = self.sex
        k["human_modeling_age"] = self.age
        k["hm_shoulders"] = self.shoulders
        k.update_tag()
        return {"FINISHED"}

class P_OT_guarded(bpy.types.Operator):
    bl_idname = "protohl.guarded"
    bl_label = "HumanLoom: guarded action"
    bl_description = "Needs a selected human"
    @classmethod
    def poll(cls, context):
        if not is_human(context.object):
            cls.poll_message_set("Select a HumanLoom body first.")
            return False
        return True
    def execute(self, context):
        self.report({"INFO"}, "guarded action ran")
        return {"FINISHED"}

class P_MT_pie(bpy.types.Menu):
    bl_label = "Human pie"
    def draw(self, context):
        pie = self.layout.menu_pie()
        pie.operator("protohl.add_human", text="Child").age = 0.0
        pie.operator("protohl.add_human", text="Teen").age = 1.0
        pie.operator("protohl.add_human", text="Adult").age = 2.0
        pie.operator("protohl.add_human", text="Senior").age = 3.0

class P_MT_add(bpy.types.Menu):
    bl_label = "Human"
    def draw(self, context):
        self.layout.operator("protohl.add_human", text="Adult").age = 2.0
        self.layout.operator("protohl.add_human", text="Child").age = 0.0

def add_menu(self, context):
    self.layout.menu("P_MT_add", icon="OUTLINER_OB_ARMATURE")

def obj_menu(self, context):
    self.layout.separator()
    self.layout.operator("protohl.guarded")

class P_GGT(bpy.types.GizmoGroup):
    bl_idname = "P_GGT_shoulders"
    bl_label = "Human shoulders gizmo"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_options = {"3D", "PERSISTENT"}
    @classmethod
    def poll(cls, context):
        return is_human(context.object)
    def setup(self, context):
        gz = self.gizmos.new("GIZMO_GT_arrow_3d")
        gz.target_set_prop("offset", context.object.hlface, "shoulders")
        gz.color = 1.0, 0.5, 0.0
        gz.scale_basis = 0.4
        gz.use_draw_modal = True
        self.gz = gz
    def refresh(self, context):
        o = context.object
        from mathutils import Matrix, Vector
        gz = self.gz
        gz.matrix_basis = Matrix.Translation(o.matrix_world @ Vector((0.0, 0.0, 1.45)))

class P_TOOL(bpy.types.WorkSpaceTool):
    bl_space_type = "VIEW_3D"
    bl_context_mode = "OBJECT"
    bl_idname = "protohl.tool"
    bl_label = "Human morph"
    bl_description = "Prototype tool"
    bl_icon = "ops.generic.select"
    bl_widget = "P_GGT_shoulders"
    bl_keymap = ()

bpy.utils.register_class(Facade)
bpy.types.Object.hlface = bpy.props.PointerProperty(type=Facade)
for c in (P_PT_obj, P_OT_add, P_OT_guarded, P_MT_pie, P_MT_add, P_GGT):
    bpy.utils.register_class(c)
try:
    bpy.utils.register_tool(P_TOOL, after={"builtin.cursor"}, separator=True)
    RES["tool_registered"] = True
except Exception as e:
    RES["tool_registered"] = "ERR " + str(e)[:150]
bpy.types.VIEW3D_MT_add.append(add_menu)
bpy.types.VIEW3D_MT_object.append(obj_menu)
kc = bpy.context.window_manager.keyconfigs.addon
km = kc.keymaps.new(name="3D View", space_type="VIEW_3D")
km.keymap_items.new("protohl.add_human", "H", "PRESS", ctrl=True, shift=True)
kp = km.keymap_items.new("wm.call_menu_pie", "P", "PRESS", ctrl=True, shift=True)
kp.properties.name = "P_MT_pie"
RES["keymap_items"] = ["Ctrl+Shift+H add human", "Ctrl+Shift+P pie"]

OUT = SP / "proto_ui2"
OUT.mkdir(exist_ok=True)
state = {"n": 0}

def view(kind):
    win = bpy.context.window_manager.windows[0]
    for a in win.screen.areas:
        if a.type == kind:
            return win, a

def tick():
    n = state["n"]
    state["n"] += 1
    try:
        if n == 0:
            w, a = view("VIEW_3D")
            a.spaces[0].show_region_ui = True
            RES["guarded_poll_without_human"] = bpy.ops.protohl.guarded.poll()
            return 1.0
        if n == 1:
            # workspace + asset browser prototype
            try:
                bpy.ops.workspace.duplicate()
                ws = bpy.context.window.workspace
                ws.name = "Character"
                RES["workspace_created"] = ws.name
                for a in bpy.context.window.screen.areas:
                    if a.type == "DOPESHEET_EDITOR" or a.ui_type == "TIMELINE":
                        a.ui_type = "ASSETS"
                        RES["asset_browser_area"] = a.ui_type
            except Exception as e:
                RES["workspace_err"] = str(e)[:200]
            (OUT / "res.json").write_text(json.dumps(RES, indent=1), encoding="utf-8")
            return None
    except Exception as e:
        RES["tick_err_%d" % n] = str(e)[:200]
        (OUT / "res.json").write_text(json.dumps(RES, indent=1), encoding="utf-8")
    return None

bpy.app.timers.register(tick, first_interval=2.5)
