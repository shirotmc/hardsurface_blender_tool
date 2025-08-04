import bpy
import bmesh

class TMC_OP_Set_Normal_With_Active_Face(bpy.types.Operator):# Operator class should have _OT_ in it
    bl_idname = "tmc.set_normal_with_active_face"
    bl_label = "Set Normal With Active Face"
    bl_description = 'Set vertex normal with current active face normal'

    @classmethod
    def poll(cls, context):

        if context.active_object != None:
            if context.active_object.type == 'MESH':
                return True
        return False

    def get_active_face_index(self):
        bm = bmesh.from_edit_mesh(bpy.context.active_object.data)
        if bm.select_history:
            elem = bm.select_history[-1]
            if isinstance(elem, bmesh.types.BMFace):
                return elem.index
        return 0

    def execute(self, context):
        active_face_index = self.get_active_face_index()
        face_normal_vector = (0,0,0)
        for f in bmesh.from_edit_mesh(bpy.context.active_object.data).faces:
            if f.select and f.index == active_face_index:
                face_normal_vector = tuple(f.normal)
                break
        
        bpy.ops.object.mode_set(mode = 'OBJECT')
        
        mesh = bpy.context.object.data
        selected_vertices = [v.index for v in bpy.context.active_object.data.vertices if v.select]


        normals = []
        for l in mesh.loops:
            if l.vertex_index in selected_vertices:
                normals.append(face_normal_vector)
            else:
                normals.append(tuple(l.normal))
        mesh.normals_split_custom_set(normals)
        
        bpy.ops.object.mode_set(mode = 'EDIT')

        return {'FINISHED'}