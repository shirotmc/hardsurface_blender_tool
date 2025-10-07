import os
import math
import re
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

class TMC_OP_AutoCreateBakeSet(bpy.types.Operator):
    bl_idname = "tmc.auto_create_bakeset"
    bl_label = "Auto Create Bake Set"
    bl_description = "Auto create bake set for object"

    def execute(self, context):
        # build high/low lists from all meshes in the scene (not just selected)
        object_pair_list = []
        checked_object_list = []
        all_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
        highs = [o for o in all_objects if check_highpoly_name(o.name)]
        lows = [o for o in all_objects if o not in highs]
        for i in range(0, len(lows)):
            for j in range(0, len(highs)):
                if j not in checked_object_list:
                    # print("Check:", lows[i].name, highs[j].name)
                    if check_overlap(context, lows[i], highs[j]):
                        object_pair_list.append([lows[i], highs[j]])
                        checked_object_list.append(j)
                        break
        # start numbering from the next available index so consecutive runs continue numbering
        next_index = get_next_bakeset_index(context.scene.bakeset_name)
        for obj_pair in object_pair_list:
            if check_highpoly_name(obj_pair[0].name):
                highpoly_mesh = obj_pair[0]
                lowpoly_mesh = obj_pair[1]
            elif check_highpoly_name(obj_pair[-1].name):
                highpoly_mesh = obj_pair[1]
                lowpoly_mesh = obj_pair[0]
            # Rename & group mesh (use the next available index and increment for the next pair)
            i = next_index
            bakeset_name = f"{context.scene.bakeset_name}_{i}"
            next_index += 1

            # name High and Low with numeric suffix ensuring uniqueness: {bakeset_name}_High_{n}
            obj_list_names = [obj.name for obj in bpy.context.scene.objects]
            hcount = 1
            h_candidate = f"{bakeset_name}_High_{hcount}"
            while h_candidate in obj_list_names:
                hcount += 1
                h_candidate = f"{bakeset_name}_High_{hcount}"
            highpoly_mesh.name = h_candidate
            obj_list_names.append(h_candidate)

            lcount = 1
            l_candidate = f"{bakeset_name}_Low_{lcount}"
            while l_candidate in obj_list_names:
                lcount += 1
                l_candidate = f"{bakeset_name}_Low_{lcount}"
            lowpoly_mesh.name = l_candidate
            obj_list_names.append(l_candidate)

            # ensure a base collection exists with the base bakeset name
            base_collection_name = context.scene.bakeset_name
            if base_collection_name in bpy.data.collections:
                base_coll = bpy.data.collections[base_collection_name]
            else:
                base_coll = bpy.data.collections.new(base_collection_name)
                try:
                    bpy.context.scene.collection.children.link(base_coll)
                except Exception:
                    try:
                        bpy.context.scene.collection.children.link(base_coll)
                    except Exception:
                        pass

            # ensure child collection exists for this bakeset (reuse if present)
            child_coll_name = bakeset_name
            if child_coll_name in bpy.data.collections:
                child_coll = bpy.data.collections[child_coll_name]
            else:
                child_coll = bpy.data.collections.new(child_coll_name)
                try:
                    base_coll.children.link(child_coll)
                except Exception:
                    try:
                        bpy.context.scene.collection.children.link(child_coll)
                    except Exception:
                        pass

            # create or reuse High and Low sub-collections under the child collection
            high_sub_name = f"{bakeset_name}_High"
            low_sub_name = f"{bakeset_name}_Low"
            if high_sub_name in bpy.data.collections:
                high_sub = bpy.data.collections[high_sub_name]
            else:
                high_sub = bpy.data.collections.new(high_sub_name)
                try:
                    child_coll.children.link(high_sub)
                except Exception:
                    try:
                        bpy.context.scene.collection.children.link(high_sub)
                    except Exception:
                        pass

            if low_sub_name in bpy.data.collections:
                low_sub = bpy.data.collections[low_sub_name]
            else:
                low_sub = bpy.data.collections.new(low_sub_name)
                try:
                    child_coll.children.link(low_sub)
                except Exception:
                    try:
                        bpy.context.scene.collection.children.link(low_sub)
                    except Exception:
                        pass

            # move the two objects into the appropriate sub-collection (unlink from others)
            # high -> high_sub, low -> low_sub
            for obj, target_coll in ((highpoly_mesh, high_sub), (lowpoly_mesh, low_sub)):
                for uc in list(obj.users_collection):
                    if uc != target_coll:
                        try:
                            uc.objects.unlink(obj)
                        except Exception:
                            pass
                if target_coll not in obj.users_collection:
                    try:
                        target_coll.objects.link(obj)
                    except Exception:
                        pass

        controller.show_message(context, "INFO", "Auto Create Bakeset: Done!")
        return {'FINISHED'}

class TMC_OP_CreateBakeSet(bpy.types.Operator):
    bl_idname = "tmc.create_bakeset"
    bl_label = "Create Bake Set"
    bl_description = "Create bake set for selected objects"

    def execute(self, context):
        # get selected object list
        selected = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
        if not selected:
            controller.show_message(context, "ERROR", "Please select one or more meshes")
            return {'CANCELLED'}

        # split selection into highs and lows using your detection function
        highs = [o for o in selected if check_highpoly_name(o.name)]
        lows = [o for o in selected if o not in highs]

        if not highs and not lows:
            controller.show_message(context, "ERROR", "No valid high/low meshes found in selection")
            return {'CANCELLED'}

        # If user selected multiple highs and lows, create a single bakeset containing them
        i = get_next_bakeset_index(context.scene.bakeset_name)
        bakeset_name = f"{context.scene.bakeset_name}_{i}"

    # no empties/groups required — we'll only use collections

        # rename highs so names are {bakeset_name}_High_{n}
        obj_list_names = [obj.name for obj in bpy.context.scene.objects]
        hcount = 1
        for h in highs:
            candidate = f"{bakeset_name}_High_{hcount}"
            while candidate in obj_list_names:
                hcount += 1
                candidate = f"{bakeset_name}_High_{hcount}"
            h.name = candidate
            obj_list_names.append(candidate)
            hcount += 1

        # rename lows so names are {bakeset_name}_Low_{n}
        lcount = 1
        for l in lows:
            candidate = f"{bakeset_name}_Low_{lcount}"
            while candidate in obj_list_names:
                lcount += 1
                candidate = f"{bakeset_name}_Low_{lcount}"
            l.name = candidate
            obj_list_names.append(candidate)
            lcount += 1

        # ensure base collection exists and child collection for this bakeset
        base_collection_name = context.scene.bakeset_name
        if base_collection_name in bpy.data.collections:
            base_coll = bpy.data.collections[base_collection_name]
        else:
            base_coll = bpy.data.collections.new(base_collection_name)
            try:
                bpy.context.scene.collection.children.link(base_coll)
            except Exception:
                try:
                    bpy.context.scene.collection.children.link(base_coll)
                except Exception:
                    pass

        child_coll_name = bakeset_name
        if child_coll_name in bpy.data.collections:
            child_coll = bpy.data.collections[child_coll_name]
        else:
            child_coll = bpy.data.collections.new(child_coll_name)
            try:
                base_coll.children.link(child_coll)
            except Exception:
                try:
                    bpy.context.scene.collection.children.link(child_coll)
                except Exception:
                    pass

        # create/reuse High/Low subcollections under the child collection
        high_sub_name = f"{bakeset_name}_High"
        low_sub_name = f"{bakeset_name}_Low"
        if high_sub_name in bpy.data.collections:
            high_sub = bpy.data.collections[high_sub_name]
        else:
            high_sub = bpy.data.collections.new(high_sub_name)
            try:
                child_coll.children.link(high_sub)
            except Exception:
                try:
                    bpy.context.scene.collection.children.link(high_sub)
                except Exception:
                    pass

        if low_sub_name in bpy.data.collections:
            low_sub = bpy.data.collections[low_sub_name]
        else:
            low_sub = bpy.data.collections.new(low_sub_name)
            try:
                child_coll.children.link(low_sub)
            except Exception:
                try:
                    bpy.context.scene.collection.children.link(low_sub)
                except Exception:
                    pass

        # move highs into high_sub and lows into low_sub (unlink from others)
        for obj in tuple(highs):
            for uc in list(obj.users_collection):
                if uc != high_sub:
                    try:
                        uc.objects.unlink(obj)
                    except Exception:
                        pass
            if high_sub not in obj.users_collection:
                try:
                    high_sub.objects.link(obj)
                except Exception:
                    pass
        for obj in tuple(lows):
            for uc in list(obj.users_collection):
                if uc != low_sub:
                    try:
                        uc.objects.unlink(obj)
                    except Exception:
                        pass
            if low_sub not in obj.users_collection:
                try:
                    low_sub.objects.link(obj)
                except Exception:
                    pass

        controller.show_message(context, "INFO", "Create Bakeset: Done!")

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
def check_highpoly_name(name):
    split_list = name.rsplit("_", 1)
    if split_list[0] == "HSTool_High" and split_list[-1].isnumeric():
        return True
    else:
        return False

def get_distance(a_pos, b_pos):
    distance = math.sqrt(pow((a_pos[0]-b_pos[0]),2) + pow((a_pos[1]-b_pos[1]),2) + pow((a_pos[2]-b_pos[2]),2))
    return distance

def get_bounding_box(obj):
    vertices_world = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    x, y, z = zip(*(p for p in vertices_world))
    return [(min(x), min(y), min(z)), (max(x), max(y), max(z))]


def get_next_bakeset_index(base_name: str) -> int:
    """Return the next numeric index for bakeset naming.

    Scans objects and collections for names matching base_name_N and returns N+1 where N is the max found.
    """
    pattern = re.compile(rf"^{re.escape(base_name)}_(\d+)$")
    max_index = 0

    # check objects in the scene
    for obj in bpy.context.scene.objects:
        m = pattern.match(obj.name)
        if m:
            try:
                idx = int(m.group(1))
                if idx > max_index:
                    max_index = idx
            except Exception:
                pass

    # check collections
    for coll in bpy.data.collections:
        m = pattern.match(coll.name)
        if m:
            try:
                idx = int(m.group(1))
                if idx > max_index:
                    max_index = idx
            except Exception:
                pass

    return max_index + 1

def check_overlap(context, object_a, object_b):
    a_bbox = get_bounding_box(object_a)
    b_bbox = get_bounding_box(object_b)
    diagonal_line_length = get_distance(b_bbox[0], b_bbox[-1])
    min_distance = diagonal_line_length * context.scene.threshold_value
    # print("Min Distance:", min_distance)
    # print("Distance A:", get_distance(a_bbox[0], b_bbox[0]))
    # print("Distance B:", get_distance(a_bbox[-1], b_bbox[-1]))
    if get_distance(a_bbox[0], b_bbox[0]) >= min_distance or get_distance(a_bbox[-1], b_bbox[-1]) >= min_distance:
        return False
    else:
        return True

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
    fbx_path = context.scene.get("bakeset_export_path", "")

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
    print(export_mode)
    if export_mode == "Multiple":
        # Multiple Files
        for mesh in mesh_list:
            if bakeset_name in mesh.name:
                bpy.ops.object.select_all(action='DESELECT')
                mesh.select_set(True)
                export_fbx_for_baking(context, mesh.name, fbx_path)
    else:
        # Single Files
        highs = [o for o in mesh_list if o.name.rsplit("_", 2)[-2].lower() == "high"]
        lows = [o for o in mesh_list if o not in highs]
        if len(lows) > 0:
            for m in lows:
                m.select_set(True)
            export_fbx_for_baking(context, 'Object_Low', fbx_path)
        if len(highs) > 0:
            bpy.ops.object.select_all(action='DESELECT')
            for m in highs:
                m.select_set(True)
            export_fbx_for_baking(context, 'Object_High', fbx_path)

    bpy.ops.object.select_all(action='DESELECT')
    controller.show_message(context, "INFO", "Export Bakeset: Done!")
#endregion