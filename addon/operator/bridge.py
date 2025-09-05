import os
import bpy
from ..ui import controller
from ..utility import variable

class TMC_OP_ImportFromMaya(bpy.types.Operator):
    bl_idname = "tmc.import_from_maya"
    bl_label = "Import from Maya"
    bl_description = "Import from Maya"

    def execute(self, context):
        maya_to_blender_function(self, context, variable.BLENDER_MAYA_FBX_PATH)
        return {'FINISHED'}

class TMC_OP_ExportToMaya(bpy.types.Operator):
    bl_idname = "tmc.export_to_maya"
    bl_label = "Export to Maya"
    bl_description = "Export to Maya"

    def execute(self, context):
        blender_to_maya_function(self, context, variable.BLENDER_MAYA_FBX_PATH)
        return {'FINISHED'}

#region Support Function    
def set_up_fbx_path(self):
    folder_path = r'C:/Blender_ImportExport'
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    return (folder_path)    

def get_object_names(self, assets_path):
    names = []
    with bpy.data.libraries.load(assets_path) as (data_from, data_to):
        names = [name for name in data_from.objects]
    return names

def blender_to_maya_function(self, context, temp_file):
    set_up_fbx_path(self)
    if context.scene.blender_maya_normal_radiobox == "Lock":
        lock_normal = 'OFF'
    else:
        lock_normal = 'EDGE'

    bpy.ops.export_scene.fbx(filepath=temp_file,
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
                                mesh_smooth_type=lock_normal,
                                use_mesh_edges=False,
                                use_tspace=False,
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
    
    controller.show_message(context, "INFO", "Export: Done!")

def maya_to_blender_function(self, context, temp_file):
    if os.path.isfile(temp_file) == True:
        bpy.ops.import_scene.fbx(filepath=temp_file,
                                    directory="",
                                    filter_glob="*.fbx",
                                    use_manual_orientation=False,
                                    global_scale=1,
                                    bake_space_transform=False,
                                    use_custom_normals=True,
                                    use_image_search=False,
                                    use_alpha_decals=False,
                                    decal_offset=0,
                                    use_anim=True,
                                    anim_offset=1,
                                    use_custom_props=True,
                                    use_custom_props_enum_as_string=True,
                                    ignore_leaf_bones=False,
                                    force_connect_children=False,
                                    automatic_bone_orientation=False,
                                    primary_bone_axis='Y',
                                    secondary_bone_axis='X',
                                    use_prepost_rot=True,
                                    axis_forward='-Z',
                                    axis_up='Y')
                                    
    for item in (bpy.context.selected_objects):
        if '.' in item.name:
            old_name = str(item.name)
            new_name = old_name.replace('.', '_')
            item.name = new_name

    controller.show_message(context, "INFO", "Import: Done!")

#endregion