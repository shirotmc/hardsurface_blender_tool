
import os
import bpy
from ..ui import controller
from ..utility import variable

class TMC_OP_ToggleModifier(bpy.types.Operator):
    bl_idname = "tmc.toggle_modifier"
    bl_label = "Toggle Modifier"
    bl_description = "Toggle Modifier"

    def execute(self, context):
        object_list = bpy.context.selected_objects
        if len(object_list) == 0:
            object_list = bpy.context.scene.objects
        for obj in object_list:
            try:
                modifier_list = obj.modifiers
                for mod in modifier_list:
                    if mod.show_viewport != variable.TOGGLE_MODIFIER_BOOL:
                        mod.show_viewport = variable.TOGGLE_MODIFIER_BOOL
                    if mod.show_in_editmode != variable.TOGGLE_MODIFIER_BOOL:
                        mod.show_in_editmode = variable.TOGGLE_MODIFIER_BOOL
                    if mod.show_render != variable.TOGGLE_MODIFIER_BOOL:
                        mod.show_render = variable.TOGGLE_MODIFIER_BOOL
            except:
                pass
        variable.TOGGLE_MODIFIER_BOOL = not variable.TOGGLE_MODIFIER_BOOL
        return {'FINISHED'}
    
class TMC_OP_ApplyModifier(bpy.types.Operator):
    bl_idname = "tmc.apply_modifier"
    bl_label = "Apply Modifier"
    bl_description = "Apply Modifier"

    def execute(self, context):
        object_list = bpy.context.selected_objects
        if len(object_list) == 0:
            object_list = bpy.context.scene.objects
        for obj in object_list:
            try:
                bpy.context.view_layer.objects.active = obj
                for mod in obj.modifiers:
                    name = mod.name
                    try:
                        bpy.ops.object.modifier_apply(modifier = name)
                    except:
                        obj.modifiers.remove(mod)
            except:
                pass
        return {'FINISHED'}
    