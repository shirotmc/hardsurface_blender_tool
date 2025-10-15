import bpy, traceback
import bmesh
from math import radians

from ..utility.mouse import mouse_warp
from ..utility.draw import draw_quad, draw_text, get_blf_text_dims
from ..utility.addon import get_prefs

from ..ui import controller

class TMC_OP_UVBySharpEdge(bpy.types.Operator):
    bl_idname = "tmc.uv_by_sharp_edge"
    bl_label = "UV by Sharp Edge"
    bl_description = "Unwrap UV by Sharp Edge"
    
    def execute(self, context):
        object_list = [obj for obj in bpy.context.selected_objects]
        for o in bpy.context.selected_objects:
            o.select_set(False)
        for obj in object_list:
            obj.select_set(True)
            # Ensure Edit mode and get bmesh from edit mesh
            bpy.ops.object.mode_set(mode='EDIT')
            me = obj.data
            bm = bmesh.from_edit_mesh(me)
            # Mark seams on edges that are selected
            for e in bm.edges:
                if not e.smooth:
                    e.seam = True
            # push changes to mesh
            bmesh.update_edit_mesh(me, loop_triangles=False, destructive=False)
            # select all faces then unwrap
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.uv.unwrap(method='ANGLE_BASED', margin=0.001)
            bpy.ops.object.mode_set(mode='OBJECT')
        return {'FINISHED'}

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