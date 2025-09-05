import os
import math
import bpy
from ..ui import controller
from ..utility import variable

class TMC_OP_RenameHighpoly(bpy.types.Operator):
    bl_idname = "tmc.rename_highpoly"
    bl_label = "Rename Highpoly"
    bl_description = "Rename highpoly object"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selected_object_list = [obj for obj in bpy.context.selected_objects]
        if len(selected_object_list) == 0:
            controller.show_message(context, "ERROR", "Please select mesh for rename!")
            return False
        
        i = 1
        new_name = "HSTool_High_1"
        for m in selected_object_list:
            object_list = [obj.name for obj in bpy.context.scene.objects]
            while new_name in object_list:
                i += 1
                new_name = "HSTool_High_" + str(i)
            m.name = new_name

        controller.show_message(context, "INFO", "Rename Highpoly: Done!")

        return {'FINISHED'}

class TMC_OP_CreateBakeSet(bpy.types.Operator):
    bl_idname = "tmc.create_bakeset"
    bl_label = "Create Bake Set"
    bl_description = "Create bake set for selected object"

    def execute(self, context):
        object_pair_list = []
        checked_object_list = []
        selected_object_list = [obj for obj in bpy.context.selected_objects]
        for i in range(0, len(selected_object_list)):
            for j in range(i+1, len(selected_object_list)):
                if i not in checked_object_list:
                    if check_overlap(context, selected_object_list[i], selected_object_list[j]):
                        object_pair_list.append([selected_object_list[i], selected_object_list[j]])
                        checked_object_list.append(j)
                        break
        
        for obj_pair in object_pair_list:
            if check_highpoly_name(obj_pair[0].name):
                highpoly_mesh = obj_pair[0]
                lowpoly_mesh = obj_pair[1]
            elif check_highpoly_name(obj_pair[-1].name):
                highpoly_mesh = obj_pair[1]
                lowpoly_mesh = obj_pair[0]

            # Rename & group mesh
            object_list = [obj.name for obj in bpy.context.scene.objects]
            i = 1
            bakeset_name = context.scene.bakeset_name + "_1"
            while bakeset_name in object_list:
                i += 1
                bakeset_name = context.scene.bakeset_name + "_" + str(i)
            bakeset_empty = make_empty(bakeset_name, (0,0,0))
            high_group = make_empty("High_" + str(i), (0,0,0))
            low_group = make_empty("Low_" + str(i), (0,0,0))
            high_group.parent = bakeset_empty
            low_group.parent = bakeset_empty

            # Assign mesh to group
            highpoly_mesh.parent = high_group
            lowpoly_mesh.parent = low_group

            highpoly_mesh.name = bakeset_name + "_High"
            lowpoly_mesh.name = bakeset_name + "_Low"

        controller.show_message(context, "INFO", "Auto create Bakeset: Done!")
        return {'FINISHED'}

class TMC_OP_AutoCreateBakeSet(bpy.types.Operator):
    bl_idname = "tmc.auto_create_bakeset"
    bl_label = "Auto Create Bake Set"
    bl_description = "Auto create bake set for all objects in scene"

    def execute(self, context):
        # Create BakeSet group
        selected_object_list = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']

        # Get lowpoly & highpoly mesh list
        highpoly_mesh_list = []
        lowpoly_mesh_list = []
        for i in range(0, len(selected_object_list)):
            if check_highpoly_name(selected_object_list[i].name):
                highpoly_mesh_list.append(selected_object_list[i].name)
            else:
                lowpoly_mesh_list.append(selected_object_list[i].name)

        # Combine highpoly mesh
        bpy.ops.object.select_all(action='DESELECT')
        highpoly_mesh = join_mesh(highpoly_mesh_list)

        # Combine lowpoly mesh
        bpy.ops.object.select_all(action='DESELECT')
        lowpoly_mesh = join_mesh(lowpoly_mesh_list)

        # Rename & group mesh
        object_list = [obj.name for obj in bpy.context.scene.objects]
        i = 1
        bakeset_name = context.scene.bakeset_name + "_1"
        while bakeset_name in object_list:
            i += 1
            bakeset_name = context.scene.bakeset_name + "_" + str(i)
        bakeset_empty = make_empty(bakeset_name, (0,0,0))
        high_group = make_empty("High_" + str(i), (0,0,0))
        low_group = make_empty("Low_" + str(i), (0,0,0))
        high_group.parent = bakeset_empty
        low_group.parent = bakeset_empty

        # Assign mesh to group
        highpoly_mesh.parent = high_group
        lowpoly_mesh.parent = low_group

        highpoly_mesh.name = bakeset_name + "_High"
        lowpoly_mesh.name = bakeset_name + "_Low"

        controller.show_message(context, "INFO", "Auto Create Bakeset: Done!")
        
        return {'FINISHED'}

class TMC_OP_ExportBakeSet(bpy.types.Operator):
    bl_idname = "tmc.export_bakeset"
    bl_label = "Export Bake Set"
    bl_description = "Export bake set for selected object"

    def execute(self, context):
        export_bakeset_function(context, 'all')
        return {'FINISHED'}
    
class TMC_OP_ExportSelectedHighLow(bpy.types.Operator):
    bl_idname = "tmc.export_selected_highlow"
    bl_label = "Export Selected High/Low"
    bl_description = "Export selected high/low mesh"

    def execute(self, context):
        export_bakeset_function(context, 'selected')
        return {'FINISHED'}


#region SUPPORT FUNCTION
def check_highpoly_name(self, name):
    split_list = name.rsplit("_", 1)
    if split_list[0] == "HSTool_High" and split_list[-1].isnumeric():
        return True
    else:
        return False

def get_distance(self, a_pos, b_pos):
    distance = math.sqrt(pow((a_pos[0]-b_pos[0]),2) + pow((a_pos[1]-b_pos[1]),2) + pow((a_pos[2]-b_pos[2]),2))
    return distance

def get_bounding_box(self, obj):
    vertices_world = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    x, y, z = zip(*(p for p in vertices_world))
    return [(min(x), min(y), min(z)), (max(x), max(y), max(z))]

def check_overlap(self, context, object_a, object_b):
    a_bbox = self.get_bounding_box(object_a)
    b_bbox = self.get_bounding_box(object_b)
    diagonal_line_length = self.get_distance(b_bbox[0], b_bbox[-1])
    min_distance = diagonal_line_length * context.scene.threshold_value
    if self.get_distance(a_bbox[0], b_bbox[0]) >= min_distance or self.get_distance(a_bbox[-1], b_bbox[-1]) >= min_distance:
        return False
    else:
        return True

def make_empty(name, location): #string, vector, string of existing coll
    empty_obj = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(empty_obj)
    empty_obj.empty_display_type = "PLAIN_AXES"
    empty_obj.location = (0, 0, 0)
    return empty_obj

def join_mesh(mesh_list):
    for mesh_name in mesh_list:
        mesh = bpy.data.objects[mesh_name]
        mesh.select_set(state=True)
        bpy.context.view_layer.objects.active = mesh
    bpy.ops.object.join()
    obj = bpy.data.objects[mesh_list[-1]]
    return obj

def export_fbx_for_baking(context, object_name, folder_path):
    # Setting for low/high mesh
    if "high" in object_name.rsplit('_', 1)[-1].lower():
        triangle = False
    else:
        triangle = True
    # Unlock normal
    if context.scene.export_bakeset_unlock_normal:
        smooth_type = 'FACE' 
    else:
        smooth_type = 'OFF'

    fbx_path = folder_path + object_name + ".fbx"
    bpy.ops.export_scene.fbx(filepath=fbx_path,
                            check_existing=True,
                            filter_glob="*.fbx",
                            use_selection=True,
                            use_active_collection=False,
                            global_scale=1,
                            apply_unit_scale=True,
                            apply_scale_options='FBX_SCALE_ALL',
                            bake_space_transform=True,
                            object_types={'MESH','EMPTY'},
                            use_mesh_modifiers=True,
                            use_mesh_modifiers_render=True,
                            mesh_smooth_type=smooth_type,
                            use_mesh_edges=False,
                            use_tspace=False,
                            use_triangles=triangle,
                            use_custom_props=False,
                            add_leaf_bones=False,
                            primary_bone_axis='Y',
                            secondary_bone_axis='X',
                            use_armature_deform_only=False,
                            armature_nodetype='NULL',
                            bake_anim=False,
                            bake_anim_use_all_bones=False,
                            bake_anim_use_nla_strips=False,
                            bake_anim_use_all_actions=False,
                            bake_anim_force_startend_keying=False,
                            bake_anim_step=1,
                            bake_anim_simplify_factor=1,
                            path_mode='AUTO',
                            embed_textures=False,
                            batch_mode='OFF',
                            use_batch_own_dir=True,
                            use_metadata=True,
                            axis_forward='Y',
                            axis_up='Z')


def export_bakeset_function(context, mode):
    # Get FBX folder
    fbx_path = context.scene.bakeset_export_path
    
    # Get Bakeset name
    bakeset_name = context.scene.bakeset_name

    # Get object list
    if mode == 'selected':
        mesh_list = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
    else:
        mesh_list = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH' and bakeset_name in obj.name]
    # Get export mode: Single/Multiple
    export_mode = context.scene.export_bakeset_mode
    
    # Export FBX
    bpy.ops.object.select_all(action='DESELECT')
    if export_mode == "Multiple":
        # Multiple Files
        for mesh in mesh_list:
            if bakeset_name in mesh.name:
                bpy.ops.object.select_all(action='DESELECT')
                mesh.select_set(True)
                export_fbx_for_baking(context, mesh.name, fbx_path)
    else:
        # Single Files
        low_mesh_list = [m for m in mesh_list if m.name.rsplit("_", 1)[-1].lower() == "low"]
        high_mesh_list = [m for m in mesh_list if m.name.rsplit("_", 1)[-1].lower() == "high"]
        if len(low_mesh_list) > 0:
            for m in low_mesh_list:
                m.select_set(True)
            export_fbx_for_baking(context, 'Object_Low', fbx_path)
        if len(high_mesh_list) > 0:
            bpy.ops.object.select_all(action='DESELECT')
            for m in high_mesh_list:
                m.select_set(True)
            export_fbx_for_baking(context, 'Object_High', fbx_path)

    bpy.ops.object.select_all(action='DESELECT')
    controller.show_message(context, "INFO", "Export Bakeset: Done!")
#endregion