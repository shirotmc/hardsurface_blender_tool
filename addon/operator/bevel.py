import bpy
from ..ui import controller

class TMC_OP_BevelCustomSetting(bpy.types.Operator):
    bl_idname = "tmc.bevel_with_custom_setting"
    bl_label = "Custom Bevel"
    bl_description = "Bevel with custom setting"

    def execute(self, context):
        # Get the custom bevel settings from the scene properties
        is_exists = False
        obj = context.active_object
        for mod in obj.modifiers:
            if mod.type == "BEVEL":
                if mod.name == context.scene.bevel_modifier_name:
                    is_exists = True
                    break
        if not is_exists:
            # Create Bevel Vertex Group Modifier
            mod = obj.modifiers.new(context.scene.bevel_modifier_name, 'BEVEL')
            mod.offset_type = 'OFFSET'
            mod.width = context.scene.bevel_unit_value
            mod.segments = context.scene.bevel_segment_value
            mod.limit_method = context.scene.bevel_type
            mod.miter_outer = 'MITER_ARC'
            mod.miter_inner = 'MITER_SHARP'
            mod.use_clamp_overlap = False
            mod.loop_slide = True
            if context.scene.bevel_type == "VGROUP":
                # Create Vertex Group
                new_vertex_group = bpy.context.object.vertex_groups.new(name=context.scene.bevel_modifier_name)
                bpy.ops.object.vertex_group_assign()
                mod.vertex_group = new_vertex_group.name
            elif context.scene.bevel_type == "WEIGHT":
                mode = bpy.context.active_object.mode
                if mode != 'OBJECT':
                    # we need to switch from Edit mode to Object mode so the selection gets updated
                    bpy.ops.object.mode_set(mode='OBJECT')
                    obj = bpy.context.active_object
                    obj_data = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
                    # create bevel weight edge data
                    if 'bevel_weight_edge' not in obj_data.attributes:
                        obj.data.attributes.new(
                            name='bevel_weight_edge',
                            type='FLOAT',
                            domain='EDGE'
                        )
                    for index, edge in enumerate(obj.data.edges):
                        if edge.select:
                            obj.data.attributes['bevel_weight_edge'].data[index].value = 1.0
                    # back to whatever mode we were in
                    bpy.ops.object.mode_set(mode=mode)
            elif context.scene.bevel_type == "ANGLE":
                mod.angle_limit = 1.0471975512 # 60 Degrees
        else:
            controller.show_message(context, "ERROR", "This name already exists. Please enter another name!")
        return {'FINISHED'}

class TMC_OP_GetBevelModifiersFromVertex(bpy.types.Operator):
    bl_idname = "tmc.get_bevel_modifiers_from_vertex"
    bl_label = "Get Bevel Modifiers From Vertex"
    bl_description = "Get bevel modifiers from vertex"

    def execute(self, context):
        vtg_list = []
        have_vertex_group_bevel = False
        obj = bpy.context.selected_objects[0]
        # Get selected verties
        edit_mode = bpy.context.active_object.mode
        bpy.ops.object.mode_set(mode='OBJECT')
        selected_vertices = [v.index for v in bpy.context.active_object.data.vertices if v.select]
        bpy.ops.object.mode_set(mode=edit_mode)
    
        for vert in selected_vertices:
            for group in obj.vertex_groups:
                vert_in_group = [vert.index for vert in obj.data.vertices if group.index in [i.group for i in vert.groups]]
                if vert in vert_in_group and group.name not in vtg_list:
                    vtg_list.append(group.name)

        modifier_list = obj.modifiers
        for mod in modifier_list:
            if mod.type == "BEVEL":
                if mod.limit_method == "VGROUP":
                    if mod.vertex_group in vtg_list:
                        mod.show_expanded = True
                        have_vertex_group_bevel = True
                    else:
                        mod.show_expanded = False
                else:
                    mod.show_expanded = False
            else:
                mod.show_expanded = False
        if not have_vertex_group_bevel:
            controller.show_message(context, "ERROR", "Object doesn't have bevel vertex group modifier!")
        return {'FINISHED'}