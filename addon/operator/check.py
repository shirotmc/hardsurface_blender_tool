import bpy
import bmesh
import mathutils
import array

from ..ui import controller
from ..utility import variable

class TMC_OP_CheckAll(bpy.types.Operator):  # check all
    bl_idname = "tmc.check_all"
    bl_label = "Check All"
    bl_description = 'check all'

    def execute(self, context):
        check_all(self, context)
        return {'FINISHED'}

class TMC_OP_CheckNgonsFace(bpy.types.Operator):   # check ngons face
    bl_idname = "tmc.check_ngons_face"
    bl_label = "Check Ngons Face"
    bl_description = 'check n-gons face from selected objects'

    def execute(self, context):
        check_ngons_face_function(self, context)
        return {'FINISHED'}

class TMC_OP_CheckNonManifold(bpy.types.Operator):
    bl_idname = "tmc.check_non_manifold"
    bl_label = "Check Non Manifold"
    bl_description = 'check non-manifold from selected objects'

    def execute(self, context):
        check_non_manifold_function(self, context)
        return {'FINISHED'}

class TMC_OP_CheckIntersectFace(bpy.types.Operator):
    bl_idname = "tmc.check_intersect_face"
    bl_label = "Check Intersect Face"
    bl_description = 'check intersect face from selected objects'

    def execute(self, context):
        check_intersect_face_function(self, context)
        return {'FINISHED'}

class TMC_OP_CheckZeroEdgeLength(bpy.types.Operator):
    bl_idname = "tmc.check_zero_edge_length"
    bl_label = "Check Zero Edge Length"
    bl_description = 'check zero edge length from selected objects'

    def execute(self, context):
        check_zero_edge_length_function(self, context)
        return {'FINISHED'}

class TMC_OP_CheckZeroFaceArea(bpy.types.Operator):
    bl_idname = "tmc.check_zero_face_area"
    bl_label = "Check Tiny Edge Face"
    bl_description = 'check tiny edge face from selected objects'

    def execute(self, context):
        check_zero_face_area_function(self, context)
        return {'FINISHED'}

class TMC_OP_CheckIsolatedVertex(bpy.types.Operator):
    bl_idname = "tmc.check_isolated_vertex"
    bl_label = "Isolated Vertex"
    bl_description = 'check isolated vertex from selected objects'

    def execute(self, context):
        check_isolated_vertex_function(self, context)
        return {'FINISHED'}
class TMC_OP_CheckSilhouette(bpy.types.Operator):
    bl_idname = "tmc.check_silhouette"
    bl_label = "Check Silhouette"
    bl_description = 'check silhouette from selected objects'

    def execute(self, context):
        preview_silhouette_function(self, context)
        return {'FINISHED'}

#region SUPPORT FUNCTION
def check_all(self, context):
    selection = [obj for obj in bpy.context.selected_objects]
    if selection:
        err = []
        bpy.ops.object.select_all(action='DESELECT')
        for obj in selection:
            obj.select_set(True)
        err = list(set(err + check_ngons_face_function(self, context)))
        bpy.ops.object.mode_set(mode='OBJECT')

        bpy.ops.object.select_all(action='DESELECT')
        for obj in selection:
            obj.select_set(True)
        err = list(set(err + check_non_manifold_function(self, context)))
        bpy.ops.object.mode_set(mode='OBJECT')

        bpy.ops.object.select_all(action='DESELECT')
        for obj in selection:
            obj.select_set(True)
        err = list(set(err + check_intersect_face_function(self, context)))
        bpy.ops.object.mode_set(mode='OBJECT')

        bpy.ops.object.select_all(action='DESELECT')
        for obj in selection:
            obj.select_set(True)
        err = list(set(err + check_zero_edge_length_function(self, context)))
        bpy.ops.object.mode_set(mode='OBJECT')

        bpy.ops.object.select_all(action='DESELECT')
        for obj in selection:
            obj.select_set(True)
        err = list(set(err + check_zero_face_area_function(self, context)))
        bpy.ops.object.mode_set(mode='OBJECT')

        bpy.ops.object.select_all(action='DESELECT')
        for obj in selection:
            obj.select_set(True)
        err = list(set(err + check_isolated_vertex_function(self, context)))
        bpy.ops.object.mode_set(mode='OBJECT')

        # Select error mesh
        for obj in err:
            obj.select_set(True)
    else:
        controller.show_message(context, "ERROR", "Please select object to checking!")

def check_ngons_face_function(self, context):
    selection = [obj for obj in bpy.context.selected_objects]
    if selection:
        err_obj = []
        # check n-gons face
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type='FACE')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.mesh.select_face_by_sides(number=4, type='GREATER', extend=True)

        # Get error mesh list
        for obj in selection:
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_mode(type='FACE')
            bm = bmesh.from_edit_mesh(context.edit_object.data)
            selected_faces = [f for f in bm.faces if f.select]
            if len(selected_faces) > 0:
                err_obj.append(obj)

        # Select error elements on mesh
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        if len(err_obj) > 0: 
            for obj in err_obj:
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_mode(type='FACE')
            # Change button icon
            context.scene.check_ngons_face = False
        else:
            context.scene.check_ngons_face = True
        return err_obj
    else:
        controller.show_message(context, "ERROR", "Please select object to checking!")
        return None

def check_non_manifold_function(self, context):
    selection = [obj for obj in bpy.context.selected_objects]
    if selection:
        err_obj = []
        # check non-manifold
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type='VERT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.mesh.select_non_manifold(extend=True)

        # Get error mesh list
        for obj in selection:
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_mode(type='VERT')
            bm = bmesh.from_edit_mesh(context.edit_object.data)
            selected_verts = [v for v in bm.verts if v.select]
            if len(selected_verts) > 0:
                err_obj.append(obj)

        # Select error elements on mesh
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        if len(err_obj) > 0: 
            for obj in err_obj:
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_mode(type='VERT')
            # Change button icon
            context.scene.check_non_manifold = False
        else:
            context.scene.check_non_manifold = True
        return err_obj
    else:
        controller.show_message(context, "ERROR", "Please select object to checking!")
        return None

def check_intersect_face_function(self, context):
    selection = [obj for obj in bpy.context.selected_objects]
    if selection:
        err_obj = []
        for obj in selection:
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode = 'EDIT')
            bpy.ops.mesh.select_mode(type="FACE")
            bpy.ops.mesh.select_all(action = 'DESELECT')

            selected_faces = []
            me = context.edit_object.data
            bm = bmesh.from_edit_mesh(me)
            tree = mathutils.bvhtree.BVHTree.FromBMesh(bm, epsilon=0.00001)
            overlap = tree.overlap(tree)
            selected_faces = list({i for i_pair in overlap for i in i_pair})
            bm.faces.ensure_lookup_table()
            for i in selected_faces:
                bm.faces[i].select = True

            bpy.ops.object.mode_set(mode='OBJECT')

        # Get error mesh list
        for obj in selection:
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_mode(type='FACE')
            bm = bmesh.from_edit_mesh(context.edit_object.data)
            selected_faces = [f for f in bm.faces if f.select]
            if len(selected_faces) > 0:
                err_obj.append(obj)

        # Select error elements on mesh
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        if len(err_obj) > 0: 
            for obj in err_obj:
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_mode(type='FACE')
            # Change button icon
            context.scene.check_intersect_face = False
        else:
            context.scene.check_intersect_face = True
        return err_obj
    else:
        controller.show_message(context, "ERROR", "Please select object to checking!")
        return None

def check_zero_edge_length_function(self, context):
    selection = [obj for obj in bpy.context.selected_objects]
    if selection:
        err_obj = []
        # check small edge
        tolerance = context.scene.min_edge_length_value  # increase to something like .1 or 1 to ignore small edge
        for obj in selection:
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode = 'EDIT') 
            bpy.ops.mesh.select_mode(type="EDGE")
            bpy.ops.mesh.select_all(action = 'DESELECT')

            edge_lengths = []
            me = context.edit_object.data
            bm = bmesh.from_edit_mesh(me)
            for e in bm.edges:
                if e.calc_length() < tolerance:
                    e.select_set(True)
                    edge_lengths.append(e)
            bpy.ops.object.mode_set(mode='OBJECT')
        # Get error mesh list
        for obj in selection:
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_mode(type='EDGE')
            bm = bmesh.from_edit_mesh(context.edit_object.data)
            selected_edges = [e for e in bm.edges if e.select]
            if len(selected_edges) > 0:
                err_obj.append(obj)

        # Select error elements on mesh
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        if len(err_obj) > 0: 
            for obj in err_obj:
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_mode(type='EDGE')
            # Change button icon
            context.scene.check_zero_edge_length = False
        else:
            context.scene.check_zero_edge_length = True
        return err_obj
    else:
        controller.show_message(context, "ERROR", "Please select object to checking!")
        return None

def check_zero_face_area_function(self, context):
    selection = [obj for obj in bpy.context.selected_objects]
    if selection:
        err_obj = []
        # check small edge
        tolerance = context.scene.min_face_area_value  # increase to something like .001 or .00001 to ignore small face
        for obj in selection:
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode = 'EDIT') 
            bpy.ops.mesh.select_mode(type="FACE")
            bpy.ops.mesh.select_all(action = 'DESELECT')

            face_areas = []
            me = context.edit_object.data
            bm = bmesh.from_edit_mesh(me)
            for f in bm.faces:
                if f.calc_area() < tolerance:
                    f.select_set(True)
                    face_areas.append(f)
            bpy.ops.object.mode_set(mode='OBJECT')
        # Get error mesh list
        for obj in selection:
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_mode(type='FACE')
            bm = bmesh.from_edit_mesh(context.edit_object.data)
            selected_faces = [f for f in bm.faces if f.select]
            if len(selected_faces) > 0:
                err_obj.append(obj)

        # Select error elements on mesh
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        if len(err_obj) > 0: 
            for obj in err_obj:
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_mode(type='FACE')
            # Change button icon
            context.scene.check_zero_face_area = False
        else:
            context.scene.check_zero_face_area = True
        return err_obj
    else:
        controller.show_message(context, "ERROR", "Please select object to checking!")
        return None

def check_isolated_vertex_function(self, context):
    selection = [obj for obj in bpy.context.selected_objects]
    if selection:
        err_obj = []
        # check isolated vertex
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type='VERT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.mesh.select_loose(extend=True)

        # Get error mesh list
        for obj in selection:
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_mode(type='VERT')
            bm = bmesh.from_edit_mesh(context.edit_object.data)
            selected_verts = [v for v in bm.verts if v.select]
            if len(selected_verts) > 0:
                err_obj.append(obj)

        # Select error elements on mesh
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        if len(err_obj) > 0: 
            for obj in err_obj:
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_mode(type='VERT')
            # Change button icon
            context.scene.check_isolated_vertex = False
        else:
            context.scene.check_isolated_vertex = True
        return err_obj
    else:
        controller.show_message(context, "ERROR", "Please select object to checking!")
        return None

def preview_silhouette_function(self, context):
    
    light_types = ["STUDIO", "MATCAP", "FLAT"]
    bg_types = ["THEME", "WORLD", "VIEWPORT"]
    bg_black = [0.0, 0.0, 0.0]
    bg_default = [0.188, 0.188, 0.188]

    
    for area in bpy.context.screen.areas: 
        if area.type == 'VIEW_3D':
            for space in area.spaces: 
                if space.type == 'VIEW_3D':
                    if variable.CHECK_SILHOUETTE == False:
                        # Light
                        space.shading.type = 'SOLID'
                        space.shading.light = light_types[2]
                        space.shading.color_type = 'SINGLE'
                        space.shading.single_color = bg_black
                        # Background
                        space.shading.background_type = bg_types[2]
                        space.shading.background_color = list(context.scene.viewport_background_color)
                        # Overlays
                        bpy.context.space_data.overlay.show_overlays = False

                        variable.CHECK_SILHOUETTE  = not variable.CHECK_SILHOUETTE
                    else:
                        # Light
                        space.shading.type = 'SOLID'
                        space.shading.light = light_types[0]
                        space.shading.color_type = 'MATERIAL'
                        space.shading.single_color = bg_black
                        # Background
                        space.shading.background_type = bg_types[0]
                        # Overlays
                        bpy.context.space_data.overlay.show_overlays = True

                        variable.CHECK_SILHOUETTE  = not variable.CHECK_SILHOUETTE 
#endregion
