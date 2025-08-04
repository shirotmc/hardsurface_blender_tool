import bpy, traceback

from ..utility.mouse import mouse_warp
from ..utility.draw import draw_quad, draw_text, get_blf_text_dims
from ..utility.addon import get_prefs

from ..ui import controller

class TMC_OP_RenameUV1(bpy.types.Operator):
    bl_idname = "tmc.rename_uv1"
    bl_label = "Rename UV1"
    bl_description = "Rename UV1"
    
    def execute(self, context):
        mesh_list = [obj for obj in bpy.context.scene.objects if obj.type=='MESH']
        for obj in mesh_list:
            uv_maps = obj.data.uv_layers
            try:
                uv_maps[0].name = context.scene.uvset1_name
            except:
                pass
        return {'FINISHED'}

class TMC_OP_DeleteRedundantUV(bpy.types.Operator):
    bl_idname = "tmc.delete_redundant_uv"
    bl_label = "Delete Redundant UV"
    bl_description = "Delete Redundant UV"
    
    def execute(self, context):
        mesh_list = [obj for obj in bpy.context.scene.objects if obj.type=='MESH']
        for obj in mesh_list:
            uv_maps = obj.data.uv_layers
            while len(uv_maps) > 1:
                uv_maps.remove(uv_maps[len(uv_maps)-1])
        return {'FINISHED'}