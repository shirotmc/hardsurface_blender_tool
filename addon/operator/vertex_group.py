import bpy

class TMC_OP_CleanVertexGroup(bpy.types.Operator):# Operator class should have _OT_ in it
    bl_idname = "tmc.clean_vertex_group"
    bl_label = "Clean Vertex Group"
    bl_description = "Clean vertex group from vertex/object(s)"
    
    @classmethod
    def poll(cls, context):

        if context.active_object != None:
            if context.active_object.type == 'MESH':
                return True
        return False

    def execute(self, context):
        mode = bpy.context.active_object.mode
        if mode == 'OBJECT':
            obj = bpy.context.selected_objects
            for o in obj:
                vg_list = o.vertex_groups
                for vg in vg_list:
                    if vg is not None:
                        o.vertex_groups.remove(vg)
        else:
            bpy.ops.object.vertex_group_remove_from(use_all_groups=True)

        return {'FINISHED'}