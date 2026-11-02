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

class TMC_OP_CheckMeshNoTris(bpy.types.Operator):  # check mesh no tris
    bl_idname = "tmc.check_mesh_no_tris"
    bl_label = "Check Mesh No Tris"
    bl_description = 'check mesh no tris from selected objects'

    def execute(self, context):
        check_mesh_no_tris_function(self, context)
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

# Map a mesh select-mode type to its bmesh element sequence attribute.
_BM_SEQUENCE = {'VERT': 'verts', 'EDGE': 'edges', 'FACE': 'faces'}


def _get_selection():
    return [obj for obj in bpy.context.selected_objects]


def _collect_and_mark_errors(context, selection, select_type, scene_prop):
    """Shared tail used by every edit-mode check.

    Walks the current selection, collects objects that still have selected
    components of ``select_type`` (the per-object/global selection pass must
    run beforehand), then re-selects those error objects, enters Edit mode on
    them and toggles ``scene_prop`` (False when errors exist, True otherwise).
    Returns the list of error objects, mirroring the previous behaviour.
    """
    err_obj = []
    seq_attr = _BM_SEQUENCE[select_type]

    # Get error mesh list
    for obj in selection:
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type=select_type)
        bm = bmesh.from_edit_mesh(context.edit_object.data)
        if any(elem.select for elem in getattr(bm, seq_attr)):
            err_obj.append(obj)

    # Select error elements on mesh
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    if len(err_obj) > 0:
        for obj in err_obj:
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type=select_type)
        # Change button icon
        setattr(context.scene, scene_prop, False)
    else:
        setattr(context.scene, scene_prop, True)
    return err_obj


def _check_with_global_select(context, select_type, scene_prop, select_op):
    """Checks that select error components once across the whole selection
    using a built-in mesh operator (ngons / non-manifold / isolated verts)."""
    selection = _get_selection()
    if not selection:
        controller.show_message(context, "ERROR", "Please select object to checking!")
        return None

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_mode(type=select_type)
    bpy.ops.mesh.select_all(action='DESELECT')
    select_op()

    return _collect_and_mark_errors(context, selection, select_type, scene_prop)


def _check_per_object(context, select_type, scene_prop, select_bm):
    """Checks that select error components per object via a bmesh callback
    (intersecting faces / zero-length edges / zero-area faces)."""
    selection = _get_selection()
    if not selection:
        controller.show_message(context, "ERROR", "Please select object to checking!")
        return None

    for obj in selection:
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type=select_type)
        bpy.ops.mesh.select_all(action='DESELECT')

        bm = bmesh.from_edit_mesh(context.edit_object.data)
        select_bm(bm)
        bpy.ops.object.mode_set(mode='OBJECT')

    return _collect_and_mark_errors(context, selection, select_type, scene_prop)


def check_all(self, context):
    selection = _get_selection()
    if not selection:
        controller.show_message(context, "ERROR", "Please select object to checking!")
        return

    err = []
    # Order preserved from the original implementation.
    check_functions = [
        check_ngons_face_function,
        check_non_manifold_function,
        check_intersect_face_function,
        check_zero_edge_length_function,
        check_zero_face_area_function,
        check_isolated_vertex_function,
        check_mesh_no_tris_function,
    ]
    for check_function in check_functions:
        bpy.ops.object.select_all(action='DESELECT')
        for obj in selection:
            obj.select_set(True)
        err = list(set(err + (check_function(self, context) or [])))
        bpy.ops.object.mode_set(mode='OBJECT')

    # Select error mesh
    for obj in err:
        obj.select_set(True)

def check_mesh_no_tris_function(self, context):
    selection = _get_selection()
    if not selection:
        controller.show_message(context, "ERROR", "Please select object to checking!")
        return None

    err_obj = []
    # objects without any face are considered errors (object-level check)
    for obj in selection:
        if obj.type == 'MESH':
            if len(obj.data.polygons) == 0:
                err_obj.append(obj)

    # Select error mesh
    bpy.ops.object.select_all(action='DESELECT')
    if len(err_obj) > 0:
        for obj in err_obj:
            obj.select_set(True)
        # Change button icon
        context.scene.check_mesh_no_tris = False
    else:
        context.scene.check_mesh_no_tris = True
    return err_obj

def check_ngons_face_function(self, context):
    return _check_with_global_select(
        context, 'FACE', 'check_ngons_face',
        lambda: bpy.ops.mesh.select_face_by_sides(number=4, type='GREATER', extend=True),
    )

def check_non_manifold_function(self, context):
    return _check_with_global_select(
        context, 'VERT', 'check_non_manifold',
        lambda: bpy.ops.mesh.select_non_manifold(extend=True),
    )

def check_intersect_face_function(self, context):
    def select_intersecting(bm):
        tree = mathutils.bvhtree.BVHTree.FromBMesh(bm, epsilon=0.00001)
        overlap = tree.overlap(tree)
        selected_faces = list({i for i_pair in overlap for i in i_pair})
        bm.faces.ensure_lookup_table()
        for i in selected_faces:
            bm.faces[i].select = True

    return _check_per_object(context, 'FACE', 'check_intersect_face', select_intersecting)

def check_zero_edge_length_function(self, context):
    tolerance = context.scene.min_edge_length_value  # increase to something like .1 or 1 to ignore small edge

    def select_short_edges(bm):
        for e in bm.edges:
            if e.calc_length() < tolerance:
                e.select_set(True)

    return _check_per_object(context, 'EDGE', 'check_zero_edge_length', select_short_edges)

def check_zero_face_area_function(self, context):
    tolerance = context.scene.min_face_area_value  # increase to something like .001 or .00001 to ignore small face

    def select_tiny_faces(bm):
        for f in bm.faces:
            if f.calc_area() < tolerance:
                f.select_set(True)

    return _check_per_object(context, 'FACE', 'check_zero_face_area', select_tiny_faces)

def check_isolated_vertex_function(self, context):
    return _check_with_global_select(
        context, 'VERT', 'check_isolated_vertex',
        lambda: bpy.ops.mesh.select_loose(extend=True),
    )

class TMC_OP_CheckZeroUVSet(bpy.types.Operator):
    bl_idname = "tmc.check_zero_uvset"
    bl_label = "Check Zero UV Set"
    bl_description = "Check if any mesh has zero UV set"

    def execute(self, context):
        err_obj = []
        selection = [obj for obj in bpy.context.selected_objects]
        for obj in selection:
            # Check if the object is a mesh type
            if obj.type == 'MESH':
                # Access the mesh data
                mesh = obj.data

                # Check if the mesh has any UV layers
                if not mesh.uv_layers:  # An empty uv_layers collection evaluates to False
                    # Select the object if it has no UV layers
                    err_obj.append(obj)

        # Select error mesh
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        if len(err_obj) > 0:
            for obj in err_obj:
                obj.select_set(True)
            # Change button icon
            context.scene.check_zero_uvset = False
        else:
            context.scene.check_zero_uvset = True
        return {'FINISHED'}

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
