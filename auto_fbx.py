import os
import bpy
from bpy.app.handlers import persistent

bl_info = {
    "name": "Auto FBX export",
    "author": "Flavelius",
    "description":"Automatically export fbx when saving file",
    "version": (0, 1),
    "blender": (2, 80, 0),
    "category":"Import-Export",
    "support":"COMMUNITY",
    "location": "View3D -> Properties -> AutoFBX"
}

def get_active_preset():
    return bpy.context.scene.autofbx_settings.preset

def path_to_presetname(path):
    return os.path.splitext(os.path.basename(path))[0]

def get_savepath():
    return os.path.splitext(bpy.path.abspath(bpy.data.filepath))[0]+'.fbx'

class PresetPropertyGroup(bpy.types.PropertyGroup):
    key: bpy.props.StringProperty()
    path: bpy.props.StringProperty()     

class AutoFBXSettings(bpy.types.PropertyGroup):
    is_enabled: bpy.props.BoolProperty("Enabled")
    preset: bpy.props.StringProperty(name="Preset")
    presets: bpy.props.CollectionProperty(type=PresetPropertyGroup)
    
    def items_callback(self, context):
        return [(item.key, item.key, '') for item in self.presets]
    def items_selected(self, context):
        context.scene.autofbx_settings.preset = context.scene.autofbx_settings.enum_prop
    enum_prop: bpy.props.EnumProperty(items=items_callback, update=items_selected)

    def reload_presets(self):
        preset_path = bpy.utils.preset_paths('operator/export_scene.fbx/')
        self.presets.clear()
        new_item = self.presets.add()
        new_item.key = "NONE"
        new_item.path = "NONE"
        if preset_path:
            listed_files = os.listdir(preset_path[0])
            for i in range(len(listed_files)):
                if listed_files[i].endswith('.py'):
                    preset_file = os.path.join(preset_path[0], listed_files[i])
                    new_item = self.presets.add()
                    new_item.key = path_to_presetname(preset_file)
                    new_item.path = preset_file
        for item in self.presets:
            if item.key == self.enum_prop:
                return
        self.enum_prop = 'NONE'

class EXPORT_SCENE_OT_autofbx_presetreloader(bpy.types.Operator):
    bl_idname = "export_scene.autofbx_reload"
    bl_label = "Reload AutoFBX presets"

    def execute(self, context):
        context.scene.autofbx_settings.reload_presets()
        return {'FINISHED'}

class EXPORT_SCENE_OT_autofbx(bpy.types.Operator):
    bl_idname = "export_scene.autofbx"
    bl_label = "Auto FBX Save"

    def export_fbx(self, outpath, presetpath):
        class Container():
            __slots__ = ('__dict__',)

        op = Container()
        file = open(presetpath, 'r')

        # storing the values from the preset on the class
        for line in file.readlines()[3::]:
            exec(line, globals(), locals())
        
        # pass class dictionary to the operator
        op.filepath = outpath
        kwargs = op.__dict__
        bpy.ops.export_scene.fbx(**kwargs)

    def preset_to_path(self, context, preset):
        settings = context.scene.autofbx_settings
        for item in settings.presets:
            if item.key == preset:
                return item.path

    def execute(self, context):
        save_path = get_savepath()
        preset = get_active_preset()
        if not save_path:
            self.report({'ERROR'}, 'file not saved')
            return {'CANCELLED'}
        elif not preset or preset == 'NONE':
            self.report({'ERROR'}, 'No Preset')
            return {'CANCELLED'}
        else:
            self.report({'INFO'}, "Exporting "+save_path+" with preset: "+preset)
            preset_path = self.preset_to_path(context, preset)
            self.export_fbx(get_savepath(), preset_path)
            return {'FINISHED'}

class AutoFBXPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_auto_fbx"
    bl_label = "Auto FBX"
    bl_category = "Auto FBX"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'

    def draw(self, context):
        settings = context.scene.autofbx_settings
        layout = self.layout
        row = layout.row()
        row.prop(settings, "is_enabled", text="Enabled")
        row = layout.row()
        row.label(text="Preset")
        row.prop_menu_enum(settings, "enum_prop", text=settings.preset)
        row = layout.row(align=True)
        row.operator("export_scene.autofbx_reload", text="Reload Presets")
        row.operator("export_scene.autofbx", text="Export")
        row = layout.row()

def preset_warning(self, context):
    self.layout.label(text="AutoFBX: Missing preset, disabling")
    context.scene.autofbx_settings.is_enabled = False

@persistent
def on_save(dummy):
    settings = bpy.context.scene.autofbx_settings
    if settings is None:
        return
    if not settings.is_enabled:
        return
    if settings.preset == 'NONE':
        bpy.context.window_manager.popover(preset_warning)
        return
    bpy.ops.export_scene.autofbx()

@persistent
def on_load(dummy):
    if bpy.context.scene.autofbx_settings:
        bpy.context.scene.autofbx_settings.reload_presets()

registerable_classes = [
    PresetPropertyGroup,
    AutoFBXSettings,
    AutoFBXPanel,
    EXPORT_SCENE_OT_autofbx,
    EXPORT_SCENE_OT_autofbx_presetreloader
]

def register():
    for item in registerable_classes:
        bpy.utils.register_class(item)
    bpy.types.Scene.autofbx_settings = bpy.props.PointerProperty(type=AutoFBXSettings)
    bpy.app.handlers.save_post.append(on_save)
    bpy.app.handlers.load_post.append(on_load)

def unregister():
    for item in registerable_classes:
        bpy.utils.unregister_class(item)
    del bpy.types.Scene.autofbx_settings
    bpy.app.handlers.save_post.remove(on_save)
    bpy.app.handlers.load_post.remove(on_load)
