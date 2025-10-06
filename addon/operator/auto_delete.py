import bpy

def find_connected_verts(me, found_index):
    edges = me.edges
    connecting_edges = [i for i in edges if found_index in i.vertices[:]]
    return len(connecting_edges)

class TMC_OP_AutoDelete(bpy.types.Operator):
    """ Dissolves mesh elements based on context instead
    of forcing the user to select from a menu what
    it should dissolve.
    """
    bl_idname = "tmc.auto_delete"
    bl_label = "HS - Auto Delete"
    bl_options = {'UNDO'}

    use_verts = bpy.props.BoolProperty(name="Use Verts", default=False)

    @classmethod
    def poll(cls, context):
        return context.mode in ['EDIT_CURVE', 'OBJECT', 'EDIT_MESH']

    def execute(self, context):
        if bpy.context.mode == 'OBJECT':
            sel = bpy.context.selected_objects

            bpy.ops.object.delete(use_global=True)

        elif bpy.context.mode == 'EDIT_MESH':
            select_mode = context.tool_settings.mesh_select_mode
            me = context.object.data
            if select_mode[0]:
                vertex = me.vertices

                bpy.ops.mesh.dissolve_verts()

                if vertex == me.vertices:
                    bpy.ops.mesh.delete(type='VERT')


            elif select_mode[1] and not select_mode[2]:
                edges1 = me.edges

                bpy.ops.mesh.dissolve_edges(use_verts=True, use_face_split=False)
                if edges1 == me.edges:
                    bpy.ops.mesh.delete(type='EDGE')

                bpy.ops.mesh.select_mode(type='EDGE')

                bpy.ops.object.mode_set(mode='OBJECT')
                bpy.ops.object.mode_set(mode='EDIT')
                vs = [v.index for v in me.vertices if v.select]
                bpy.ops.mesh.select_all(action='DESELECT')
                bpy.ops.object.mode_set(mode='OBJECT')

                for v in vs:
                    vv = find_connected_verts(me, v)
                    if vv == 2:
                        me.vertices[v].select = True
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.dissolve_verts()
                bpy.ops.mesh.select_all(action='DESELECT')

                for v in vs:
                    me.vertices[v].select = True


            elif select_mode[2] and not select_mode[1]:
                bpy.ops.mesh.delete(type='FACE')
            else:
                bpy.ops.mesh.dissolve_verts()

        elif bpy.context.mode == 'EDIT_CURVE':
            bpy.ops.curve.delete(type='VERT')
        return {'FINISHED'}

