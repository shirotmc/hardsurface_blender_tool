import bpy
import bmesh
import gpu
import blf
from bpy_extras import view3d_utils, mesh_utils
from gpu_extras.batch import batch_for_shader
import mathutils # TODO ?
from mathutils import Vector, Matrix
from mathutils.geometry import intersect_point_line, tessellate_polygon, intersect_point_tri_2d
from mathutils.kdtree import KDTree
from bpy.utils import register_class, unregister_class

from math import pi, cos, sin, radians, degrees, floor, ceil
import numpy as np

import os
import ast

# TODO Swap custom circle_shape function by build in one gpu_extras.presets.draw_circle_2d

# import time

################## TODO WARNING MEMO ####################
# This code is working proof of concept
# So it will be rewritten when all features lay down.
#########################################################


# maximum distance triggering an action
# should be consistent with Blender...
DIST_MAX = 10 # TODO add distance from object and angle to make in variable
DIST_MAX_SQR = DIST_MAX**2
_timer = None

################### Draw ######################

def draw_vertex(coords, color, size):

    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'POINTS', {"pos": coords})
    shader.bind()
    shader.uniform_float("color", color)

    gpu.state.blend_set("ALPHA")
    gpu.state.point_size_set(size)

    batch.draw(shader)  

    gpu.state.blend_set("NONE")
    gpu.state.depth_test_set('NONE')
          
def draw_edge(coords, color, indices, size):

    shader = gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'LINES', {"pos": coords}, indices=indices)
    shader.bind()

    region = bpy.context.region
    shader.uniform_float("viewportSize", (region.width, region.height))
    shader.uniform_float("color", color)
    shader.uniform_float("lineWidth", size) 

    gpu.state.blend_set("ALPHA")

    batch.draw(shader)

    gpu.state.blend_set("NONE")
    gpu.state.depth_test_set('NONE')
 
def draw_poly(coords, color, mode='TRIS', smooth=False, indices=([0,1,2],[2,3,4])):
    # 'TRIS', 'TRI_FAN'
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')

    if mode == 'TRIS':
        batch = batch_for_shader(shader, 'TRIS', {"pos": coords}, indices=indices)
    if mode == 'TRI_FAN':
        batch = batch_for_shader(shader, 'TRI_FAN', {"pos": coords})
   
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)

def drawH(self, coords, color, indices):
    size = self.width

    if len(coords) == 1: # verts
        draw_vertex(coords, color, size)
    else:
        draw_edge(coords, color, indices, size)
        
def drawAxis(coords, color, size):
    indices = ((0, 3), (1, 4), (2, 5))
    shader = gpu.shader.from_builtin('POLYLINE_SMOOTH_COLOR')
    batch = batch_for_shader(shader, 'LINES', {"pos": coords, "color": color}, indices=indices)
    shader.bind()

    region = bpy.context.region
    shader.uniform_float("viewportSize", (region.width, region.height))
    shader.uniform_float("lineWidth", size)

    gpu.state.blend_set("ALPHA")

    batch.draw(shader)

    gpu.state.blend_set("NONE")
    gpu.state.depth_test_set('NONE')

################### Init ######################

def initBM(self, obj):
    bm = bmesh.new()
    bm.from_mesh(obj.to_mesh())
    bm.normal_update() # Need to update normals

    self.bm = bm
    self.backup = obj.name

def adInit(self, context):
    self.kdt = False # Init Force raycast for nonface object
    self.transform = False # Init transform origin
    self.cursor = False
    self.transformed = False # Init transform origin
    self.multi = False
    self.rotate = False
    self.mmb_mode = False
    self.gizmo_move = False
    self.is_widget = False # THIS for checking if cursor under ui widget

    self.args = None
    self.result = None
    self.mode = None
    self._timer = None

    self.backup = []
    self.center = []
    self.bm = []
    self.kd = []
    self.axel = [] # TODO delete?

    self.is_bbox_gizmo = False

    self.axis = {'X':False, 'Y':False, 'Z':False}
    self.matrices = [] # TODO delete
    self.sel_centers = [] # TODO delete
    self.selected = []
    self.force_list = []
    self.uvs = []
    # self.sel_orients = []

    self._highlightHandles = {}
    self._bboxHandle = {}
    self._bboxHandle_lines = {}
    self._pointsHandle = {}
    self._ui_widget = {}
    self.force_2d_coords = {}

    self._AxisWidget = {}

    self.matrix = Matrix() # Init default matrix

    self.mouse_action = None # Store Main mouse action

    self.width = 2.5

    # Get blender axis color
    ax_data = bpy.context.preferences.themes[0].user_interface
    axis_x = tuple(ax_data.axis_x) + (1.0,)
    axis_y = tuple(ax_data.axis_y) + (1.0,)
    axis_z = tuple(ax_data.axis_z) + (1.0,)
    self.axisColor = (axis_x, axis_y, axis_z ,axis_x, axis_y, axis_z)

    # Init conform draw prop # TODO temp duplication of this block to insure clearing conform handle
    conform = bpy.context.window_manager.FriendlyPivotProps.conform['draw']
    if conform:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(conform, 'WINDOW')
            bpy.context.window_manager.FriendlyPivotProps.conform['draw'] = None
        except:pass   

def axisDrawPoints(self):
    '''Get axis points coordinates from given element.'''

    # Scale
    gizmo_size = bpy.context.preferences.view.gizmo_size
    ui_scale = bpy.context.preferences.system.ui_scale
    region, rv3d = bpy.context.region, bpy.context.region_data

    axis = [(0,0,0), (0,0,0), (0,0,0), (1,0,0), (0,1,0), (0,0,1)]

    elem = self.args[0]
    mx = self.args[1].matrix_world.copy()

    if self.kdt:
        l_center = elem.center
        origin_3d = l_center
        mx_new = elem.matrix_world
    else:
        # Get center of components and store it in self
        if isinstance(elem, bmesh.types.BMVert):
            l_center = elem.co
        if isinstance(elem, bmesh.types.BMEdge):
            v01, v02 = [v.co for v in elem.verts]
            l_center = v01.lerp(v02, 0.5)
        if isinstance(elem, bmesh.types.BMFace):
            l_center = elem.calc_center_median()

        origin_3d = mx @ l_center

        # This is the place of center formation
        self.center = Matrix.Translation(mx @ l_center)
        mx_new = self.center @ self.matrix.to_4x4()

    origin_2d = view3d_utils.location_3d_to_region_2d(region, rv3d, origin_3d)

    if origin_2d:
        view_point_2d = origin_2d + Vector((gizmo_size, gizmo_size))
        view_point = view3d_utils.region_2d_to_location_3d(region, rv3d, view_point_2d, origin_3d)
        coef = (view_point - origin_3d).length
    else:
        coef = 1
    
    axisSize = self.prefs.preview_size * ui_scale * coef
    coords1 = [Vector(v) * axisSize for v in axis]
    
    return [mx_new @ v for v in coords1]

##################### Get ########################

def getMinMaxVerts(v_list, index):
    extract_list = [v[index] for v in v_list]

    return min(extract_list), max(extract_list)  

def getBbox(self, context):
    data = context.window_manager.FriendlyPivotProps
    object = data.current_obj if data.current_obj else None

    if object and not data.is_init:
        if data.bbox_local:
            bpy.context.window_manager.FriendlyPivotProps.object_data['bbox'] = [Vector(co) for co in object.bound_box]
        
        if not data.bbox_local:

            dg = context.evaluated_depsgraph_get()
            eval_obj = dg.id_eval_get(object)

            # TODO DANGER this method is not optimal with hires meshes. Waiting for API
            v_coords = [eval_obj.matrix_world @ v.co for v in eval_obj.data.vertices]

            var_box = []
            for r in range(3):
                mm = getMinMaxVerts(v_coords, r)
                var_box.append(mm[0])
                var_box.append(mm[1])

            bbox = [Vector((var_box[0], var_box[2], var_box[4]))]
            bbox.append(Vector((var_box[0], var_box[2], var_box[5])))
            bbox.append(Vector((var_box[0], var_box[3], var_box[5])))
            bbox.append(Vector((var_box[0], var_box[3], var_box[4])))
            bbox.append(Vector((var_box[1], var_box[2], var_box[4])))
            bbox.append(Vector((var_box[1], var_box[2], var_box[5])))
            bbox.append(Vector((var_box[1], var_box[3], var_box[5])))
            bbox.append(Vector((var_box[1], var_box[3], var_box[4])))

            bpy.context.window_manager.FriendlyPivotProps.object_data['bbox'] = bbox

def get2DLocation(context, coords_3d):
    coords_2d = []
    for p_co in coords_3d:
        point_2d = view3d_utils.location_3d_to_region_2d(context.region, context.region_data, p_co)
        coords_2d.append(point_2d.to_tuple())
    
    return coords_2d

def intersectSurface(self, context, event):
    scene = context.scene
    region = context.region
    rv3d = context.region_data
    coord = event.mouse_region_x, event.mouse_region_y
    self.result = False

    if bpy.app.version >= (2, 91, 0):
        scene_data = context.evaluated_depsgraph_get()
    else:
        scene_data = context.view_layer
    
    # Get the ray from the viewport and mouse
    view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord) 
    ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
    
    if self.kdt: # Force Arma and Curves 
        if len(self.force_2d_coords) > 0: 
            co, index, dist = self.kd.find(Vector(coord).to_3d()) 

            if dist**2 < DIST_MAX_SQR:
                comp_2d_idx = list(self.force_2d_coords.keys())[index]
                comp_3d_idx = self.force_2d_coords[comp_2d_idx]
                return self.force_list[comp_3d_idx], self.force_list[comp_3d_idx] # TODO
            else:
                return None, None
        else:
            return None, None
    
    else: # Mesh raycast
        if context.space_data.local_view:
            # Object raycast requires evaluated mesh in object mode
            if context.mode == 'EDIT_MESH':
                bpy.ops.object.mode_set(mode='OBJECT')

            for objt in self.selection['data']:
                if objt.data.rna_type.name == 'Mesh':
                    mwi = objt.matrix_world.inverted()

                    ray_origin_mwi = mwi @ ray_origin
                    view_vector_mwi = ((mwi @ view_vector) - mwi.translation).normalized()

                    self.result, self.location, normal, index = objt.ray_cast(ray_origin_mwi, view_vector_mwi)

                    if self.result:
                        break
                else:
                    pass

            if self.selection['mode'] == 'EDIT_MESH':
                bpy.ops.object.mode_set(mode='EDIT')
        else:
            self.result, self.location, normal, index, objt, matrix = scene.ray_cast(scene_data, ray_origin, view_vector)

        # Filtering
        if self.result and objt:
            # Filter hidden objects
            if not objt.visible_get():
                self.result = None  

            # TODO Filter(exclude) linked object from execution
            if objt.library:
                self.result = None

            # Filter hidden faces 
            # Check for modifiers with Off visibility and show in EDIT MODE On
            is_hidden = False
            is_show_viewport = False
            is_show_on_ED = False
            
            if objt.mode == "EDIT":
                self.is_show_viewport = False

                for mod in objt.modifiers:
                    if mod.show_viewport and not is_show_viewport:
                        is_show_viewport = True

                    if mod.show_in_editmode and not is_show_on_ED:
                        is_show_on_ED = True

                if is_show_viewport:
                    if not is_show_on_ED:
                        is_hidden = objt.data.polygons[index].hide
                else:
                    is_hidden = objt.data.polygons[index].hide             

                if is_hidden:
                    self.result = None

            # TODO remove when other types will be
            if objt.data.rna_type.name == 'Mesh':
                return index, objt
            else:
                self.result = None

            if not self.result:
                return None, None
        else:
            return None, None

def getPointSquare(coord,coords): # TODO find blender internal analog
    x = coord[0] - coords[0]
    y = coord[1] - coords[1]
    return x*x + y*y

def getClosestPoint(coord,coords):
    vectorAP = (coord[0] - coords[0][0], coord[1] - coords[0][1])
    vectorEdge = (coords[1][0] - coords[0][0], coords[1][1] - coords[0][1])
    sEdge = vectorEdge[0]**2 + vectorEdge[1]**2
    product = vectorEdge[0]*vectorAP[0] + vectorEdge[1]*vectorAP[1] 

    if sEdge == 0.0:
        return None # Edge with zero length
    else:
        distance = product / sEdge       

    if distance < 0.0:
        return coords[0]
    elif distance > 1.0:
        return coords[1]
    else:
        return coords[0][0] + vectorEdge[0]*distance, coords[0][1] + vectorEdge[1]*distance

def getComponents(self, event, context, index, c_object):
    region = context.region
    rv3d = context.region_data
    coord = event.mouse_region_x, event.mouse_region_y

    if c_object and self.result:
        # Get editmode changes
        c_object.update_from_editmode()
        
        for o in context.selected_objects:
            o.select_set(state=False)  

        depgraph = bpy.context.evaluated_depsgraph_get()
        obj_eval = c_object.evaluated_get(depgraph)

        matrix_world = obj_eval.matrix_world # TODO self.matrix (?)  
        if obj_eval.name != self.backup: # Init bmesh
            initBM(self, obj_eval) # TODO could init face only not a whole object?

        if self.transformed: # Init bmesh after set origin
            initBM(self, obj_eval)
            self.transformed = False
            
        if self.kdt and not self.result: # If object.faces == 0
            self.bm.verts.ensure_lookup_table()
            element = self.bm.verts[index]

        else: # If args[0] == face
            # Get current face
            self.bm.verts.ensure_lookup_table()
            self.bm.faces.ensure_lookup_table()
            self.bm.edges.ensure_lookup_table()

            # Kick off result with out of range error
            try:
                poly = self.bm.faces[index]
            except:
                return

            verts, edges = poly.verts, poly.edges 
            # TODO Add raycast for search near point
            # look for verts
            cVert = {} # TODO Make it simple in future: remove vert dict and use only edges
            for vert in verts:
                point = matrix_world@vert.co
                point_2d = view3d_utils.location_3d_to_region_2d(region, rv3d, point)
                if point_2d == None:
                    pass
                else:
                    cVert[vert] = getPointSquare(coord, point_2d)
         
            # look for edges
            cEdge = {}
            for edge in edges:
                points = [matrix_world @ v.co for v in edge.verts]
                points_2d = [view3d_utils.location_3d_to_region_2d(region, rv3d, point) for point in points]
                
                percent = intersect_point_line(self.location, points[0],points[1])[1]
                fakepoint = points[0].lerp(points[1], percent) # fake edge close to cursor point
                fakepoint_2d = view3d_utils.location_3d_to_region_2d(region, rv3d, fakepoint)

                count = len([p for p in points_2d if p == None])
                if count == 1:
                    for n,p in enumerate(points_2d):
                        if p == None:
                            points_2d[n] = fakepoint_2d
                # TODO rewrite/simplify
                if count == 2:
                    cEdge[edge] = DIST_MAX_SQR * 2 # exclude edge from chance to be selected for now

                # TODO rewrite when if count == 2 will be solved
                if None not in points_2d: 
                    point_2d = getClosestPoint(coord, points_2d)
                    if point_2d:
                        cEdge[edge] = getPointSquare(coord, point_2d)
                    else:
                        cEdge[edge] = DIST_MAX_SQR * 2 # exclude edge from chance to be selected

            minVert = min(cVert, key=cVert.get)
            minEdge = min(cEdge, key=cEdge.get)

            if cVert.get(minVert) > DIST_MAX_SQR and cEdge.get(minEdge) > DIST_MAX_SQR:
                element = poly
            else:
                if cVert.get(minVert) < DIST_MAX_SQR:
                    element = minVert
                else:
                    element = minEdge

        return element, obj_eval # TODO check if addon realy need whole object data in variable maybe replace by necessary data with low store weight?

def findUniqueEdge(lens):
    '''Find the most 'unique' loop index, using list of lengths (greatest difference to others).'''
    
    difs = [abs(lens[1] - lens[2])] 
    difs.append(abs(lens[2] - lens[0]))
    difs.append(abs(lens[0] - lens[1]))
    
    eDic = {0:difs[0], 1:difs[1], 2:difs[2]}
    index = min(eDic, key=eDic.get) # Get min difference

    return index

def vTangent(elem):
    '''Align tangent to the most *unique* edge.'''

    loops = elem.loops
    edges = [l.edge for l in loops]
    lens = [e.calc_length() for e in edges]

    index = findUniqueEdge(lens)
    edge = edges[index]

    loop = [l for l in loops if l.edge == edge][0]
    
    return loop.vert.co - edge.other_vert(loop.vert).co 

def vTangentPair(args):
    '''Compute the tangent of the face, using the two longest disconnected edges.'''

    vec_a = args[3].co - args[2].co
    vec_b = args[0].co - args[1].co
    r_tangent = vec_a + vec_b

    vec_a = args[0].co - args[3].co
    vec_b = args[1].co - args[2].co
    vec = vec_a + vec_b

    if r_tangent.length_squared < vec.length_squared:
        r_tangent = vec

    return r_tangent

def vTangentLong(args):
    '''Compute the tangent of the face, using the longest edge.'''

    eDic, edges, idx = {}, [], 0

    while idx < len(args):
        if idx == len(args)-1:
            edge = args[0].co - args[idx].co
        else:
            edge = args[idx+1].co - args[idx].co

        edges.append(edge)
        eDic.update({idx : edge.length})
        idx += 1
        
    index = max(eDic, key=eDic.get) # Get max difference

    return edges[index]

def getMatrix(self, context):
    '''Get transform matrix from UI.'''

    if context.window_manager.FriendlyPivotProps.orient_active_tool:
        orient = context.scene.transform_orientation_slots[2] # Rotate Active tool
        if orient.type == 'DEFAULT':
            orient = context.scene.transform_orientation_slots[0]
    else:
        orient = context.scene.transform_orientation_slots[0]

    # Get center  of matrices
    mats = [obj.matrix_world.decompose()[0] for obj in self.selection['data']]
    loc_mat = Matrix.Translation(sum(mats, Vector()) / len(mats))

    # Get rotation matrix of active object
    if orient.type == 'LOCAL':
        # Need to normalize rotation mat to skip object's scale
        # This should fix giant gizmo scale and its error
        rot_mat = self.selection['data'][-1].matrix_world.copy().to_3x3().normalized()
    elif orient.type == 'CURSOR':
        rot_mat = context.scene.cursor.matrix.to_3x3().normalized()
    elif orient.custom_orientation:
        rot_mat = orient.custom_orientation.matrix
    # elif orient.type == 'GIMBAL': # TODO
    # elif orient.type == 'VIEW':
    else:
        rot_mat = Matrix().to_3x3() # 'GLOBAL' and Filler

    return loc_mat @ rot_mat.to_4x4()

def getCompMatrix(self, elem, mx):
    '''Get orientation matrix from given element.'''

    mw = mx.transposed().inverted()

    if isinstance(elem, bmesh.types.BMVert):
        # Set vert width
        self.width = self.prefs.highlight_vertex_size

        normal = elem.normal
        edges = elem.link_edges
        loops = elem.link_loops
        tang = Vector((0.0,0.0,1.0))

        self.elements = []

        if normal == tang or normal == Vector((0.0,0.0,-1.0)):
            tang = Vector((-1.0,0.0,0.0))
        
        if len(edges) >= 2:
            eBoundary = loops[0].edge if len(loops) > 0 else edges[0]
            
            if eBoundary.is_boundary and len(edges) == 2: 
                vPair = [edges[0].other_vert(elem), edges[1].other_vert(elem)]
                
                if edges[0].link_loops[0].vert != elem:
                    vPair[0], vPair[1] = vPair[1], vPair[0]
                
                dir01 = (mx @ elem.co - mx @ vPair[0].co).normalized() 
                dir02 = (mx @ vPair[1].co - mx @ elem.co).normalized()
                plane = normal.cross(dir01 + dir02).normalized()
            else:
                plane = normal.cross(tang).normalized()
                plane = mw @ plane
        else:
            plane = normal.cross(tang).normalized()
            plane = mw @ plane

        # Covert to object space
        normal = mw @ normal
    
        tangent = normal.cross(plane).normalized()      
        perpVec = tangent.cross(normal).normalized() # To make sure for right angles   
        
    if isinstance(elem, bmesh.types.BMEdge):
        # Set edge width    
        self.width = self.prefs.highlight_line_width

        v01, v02 = [v for v in elem.verts]

        # Get  average normal
        avrNormal = ((v01.normal + v02.normal) * 0.5)

        # Covert to object space
        tangent = mx @ Vector(v01.co) - mx @ Vector(v02.co)
        avrNormal = mw @ avrNormal
        
        perpVec = tangent.cross(avrNormal).normalized()
        normal = tangent.cross(perpVec).normalized()
        normal.negate()

    if isinstance(elem, bmesh.types.BMFace):
        # Set face edges width
        self.width = self.prefs.highlight_lineface_width

        normal = elem.normal
            
        if len(elem.verts) == 3:
            # OK for now # TODO fix occasional mismaches in some tris
            plane = vTangent(elem).normalized() 
                
        elif len(elem.verts) == 4:
            plane = elem.calc_tangent_edge_pair().normalized() # OK
        else:
            plane = elem.calc_tangent_edge().normalized() # OK
        
        # TODO does it work?
        if plane[0] == 0.0 and plane[1] == 0.0 and plane[2] == 0.0:
            plane[2] = 1.0

        # Covert to scene space
        normal = mw @ normal
        plane = mw @ plane

        perpVec = normal.cross(plane).normalized()
        tangent = normal.cross(perpVec).normalized() # To make sure for right angles

    # To make sure is everything is normalized
    perpVec.normalize()
    tangent.normalize()
    normal.normalize()

    return Matrix((perpVec, tangent, normal)).transposed()

def getDrawPoints(arg):
    '''Get points coordinates from given element.'''
    mw = arg[1].matrix_world
    elem = arg[0]
    
    if isinstance(elem, bmesh.types.BMVert):
        return tuple([Vector(mw @ elem.co)])
    if isinstance(elem, bmesh.types.BMEdge):
        return tuple([(mw @ c.co).to_tuple() for c in elem.verts])
    if isinstance(elem, bmesh.types.BMFace):
        coords = []
        for pair in elem.edges:
            for p in pair.verts:
                coords.append((mw @ p.co).to_tuple())
        return coords

def getIndices(coords, step=2, res=2):
    '''Get indices from given list.'''
    # step 2 - dotted, 1 - line
    # res = 2 - vector 2d, 3 - 3d

    if len(coords) == 1 and res == 2: return (0,0)
    if len(coords) == 1 and res == 3: return (0,0,0)

    ind = [x for  x in range(len(coords))]
    indices = tuple(ind[x:x + res] for x in range(0, len(ind), step))

    # Add first point index
    if len(indices[-1]) == res - 1:indices[-1].append(0) 
    if len(indices[-1]) == 1:
        # Add 2 indices of first point
        indices[-1].append(0) 
        indices[-1].append(1)

    return indices

def getColor(self, coords):
    if len(coords) == 1: # verts
        color =  self.prefs.highlight_vert_color
    else:
        if len(coords) == 2: # edges
            color =  self.prefs.highlight_edge_color
        else: # faces
            color =  self.prefs.highlight_face_color
    return color

def getMatrixMulti(self, args):
    '''Get orientation matrix from given elements.'''

    verts = {}
    orient_list = []
    for elem in args:
        orient_list.append(elem.orient)
        for v in elem.vertices:
            verts.update({v.hashtag : v})

        if elem.type == 'face' or elem.type == 'vert':
            edge_mode = 0
        else:
            edge_mode = 1

    length = len(verts.keys())
    l_args = list(verts.values())

    # Get normals
    normal_test = Vector((0.0,0.0,0.0))
    for c in l_args:
        normal_test += c.normal

    if length >= 3: # Calc common normal for faces
        normal_list = [v.co for v in l_args]

        # normal = averageFunction(orient_list) @ Vector((0.0,0.0,1.0))
        # normal = mathutils.geometry.normal(normal_list)

        # TODO Find right normal(like in blender)

        # Block to fix zero normal when verts are not sequenced
        # if not normal.length:

        tris_list = [normal_list[x:x+3] for x in range(0, length, 3)]

        # Remove last list with 2 and add 3 last verts as tris
        if len(tris_list[-1]) < 3:
            tris_list = tris_list[:-1]
            tris_list.append(normal_list[-3:])

        normal = Vector((0.0,0.0,0.0))
        for t in tris_list:
            tmp_normal = mathutils.geometry.normal(t)

            if normal_test.length and normal_test.dot(tmp_normal) < 0.0:
                tmp_normal.negate()

            # else:
            #     # Always positive way
            #     # Harsh way to positive # TODO TMP solution find elegant
            #     tmp_normal = Vector((abs(tmp_normal[0]),abs(tmp_normal[1]),abs(tmp_normal[2])))
                
            normal += tmp_normal
        
        normal = normal * (1 / len(tris_list))

        # Check if the normal is pointing opposite to vert normals
        if normal_test.dot(normal) < 0.0:
            normal.negate()
    
    if length == 0:
        return None

    if length == 1:
        return None

    if length == 2:
        avrNormal = normal_test * 0.5

        # Covert to object space
        tangent = l_args[1].co - l_args[0].co
        perpVec = tangent.cross(avrNormal).normalized()
        normal = tangent.cross(perpVec).normalized()

        # Check if the normal is pointing opposite to vert normals
        if normal_test.dot(normal) < 0.0:
            normal.negate()

    if length == 3:
        if edge_mode:
            plane = (l_args[0].co - l_args[1].co).normalized()
            # TODO redo from C code
            # TODO right now orientation is not as NORMAL mode
        else:
            # TODO Simplify move to vTangent function
            edges = [l_args[1].co - l_args[0].co]
            edges.append(l_args[2].co - l_args[1].co)
            edges.append(l_args[2].co - l_args[0].co)

            lens = [edges[0].length]
            lens.append(edges[1].length)
            lens.append(edges[2].length)

            index = findUniqueEdge(lens)

            plane = edges[index].normalized()

    if length == 4:
        plane = vTangentPair(l_args).normalized()

    if length > 4:
        plane = vTangentLong(l_args).normalized()

    if length >= 3: # Calc common plane for faces
        perpVec = normal.cross(plane).normalized()

    tangent = normal.cross(perpVec).normalized()

    # TODO check tangent and normal directions
    # To make sure everything is normalized
    perpVec.normalize()
    tangent.normalize()
    normal.normalize()

    return Matrix((perpVec, tangent, normal)).transposed()

def getCompMult(self):
    '''Get component for multi orientation.'''

    # Write down points coords and normals.
    elem = self.args[0]
    mx = self.args[1].matrix_world.copy()
    mw = mx.transposed().inverted()

    verts = []

    if isinstance(elem, bmesh.types.BMVert):
        elem_type = 'vert'
        p_coords = mx @ elem.co
        p_normal = mw @ elem.normal

        e_normal = None
        class vertex():
            '''Custom vertex class.'''
            type = 'vert'
            co = p_coords
            normal = p_normal
            hashtag = hash(self.args[1].data.name + type + str(elem.index))
            center = Matrix.Translation(p_coords)

        verts.append(vertex)
    else:
        if isinstance(elem, bmesh.types.BMEdge):
            elem_type = 'edge'
            norms = []
            for v in elem.verts:
                norms.append(mw @ v.normal)
            e_normal = Vector((norms[1] + norms[0]) * 0.5)

        if isinstance(elem, bmesh.types.BMFace):
            elem_type = 'face'
            e_normal = elem.normal

        for v in elem.verts:
            p_coords = mx @ v.co
            p_normal = mw @ v.normal

            class vertex():
                '''Custom vertex class.'''
                type = 'vert'
                co = p_coords
                normal = p_normal
                hashtag = hash(self.args[1].data.name + type + str(v.index))
                center = Matrix.Translation(p_coords) # Vertex coords in matrix

            verts.append(vertex)
    
    e_index = elem.index

    class component():
        '''Custom element class.'''
        type = elem_type
        normal = e_normal
        index = e_index
        vertices = verts
        hashtag = hash(self.args[1].data.name + type + str(index))
        center = self.center # Component matrix center with mw
        orient = self.matrix

    return component

######################### Store #########################

def storeSelection(self, context, arg):
    '''Store/restore selection.''' 
    if arg == 'store':
        store = context.selected_objects
        
        if len(store) >= 1:
            active = context.view_layer.objects.active
            store.remove(active)
            store.append(active)

            show_wire_list = [x.show_wire for x in store] #Bools    

            # TODO store name/index but not whole data(?)
            return dict([('mode', context.mode),('data', store),('wire', show_wire_list)]) if len(store) > 0 else None        
        else: return None
        
    if arg == 'restore':
        sel = self.selection

        for idx,obj in zip(range(len(sel['data'])), sel['data']):
            obj.select_set(state=True)
            context.view_layer.objects.active = obj.original
            obj.show_wire = sel['wire'][idx]
            
        if sel['mode'] == 'EDIT_MESH':
            # bpy.ops.object.mode_set(mode='EDIT')
            setEditMode(self, context)
    else: return None

####################### Execute ############################

def setEditMode(self, context):
    store = self.selection['data']

    active = context.view_layer.objects.active
    store.remove(active)
    store.append(active)

    for obj in store:
        context.view_layer.objects.active = obj.original
        bpy.ops.object.mode_set(mode='EDIT')

def setOrigin(self, context, obj, matrix):
    # Force renew object with modifiers, invoke DG
    dg = context.evaluated_depsgraph_get()
    eval_obj = dg.id_eval_get(obj)
    context.view_layer.update()

    if self.axel: # TODO change to self.axis
        # Adjust self.center by axis
        matrix = composeMatrix(self, obj.location, matrix)

    context.scene.cursor.location = matrix.decompose()[0]

    eval_obj.original.select_set(state=True)

    bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='MEDIAN') # TODO temp method

    if eval_obj.type == 'MESH':
        initBM(self, eval_obj) # Renew bmesh after set Origin

    eval_obj.original.select_set(state=False)

def adOrigin(self, context, matrix): 
    storeCursor = context.scene.cursor.matrix.copy()
    is_edit = False
    
    # Set Origin requires Object mode
    if context.mode == 'EDIT_MESH':
        bpy.ops.object.mode_set(mode='OBJECT')
        is_edit = True

    # TODO Set Origin only to active object in Local View
    if context.space_data.local_view:
        ob = self.selection['data'][-1] # Active object
        setOrigin(self, context, ob, matrix)
    else:
        for ob in self.selection['data']:
            setOrigin(self, context, ob, matrix)

    context.scene.cursor.matrix = storeCursor

    # Return Edit mode
    if is_edit:
        setEditMode(self, context)
    
def adCursor(self, context, matrix=None):
    if not matrix:
        matrix = self.center @ self.matrix.to_4x4()

    if self.axel:
        # Adjust self.center by axis 
        matrix = composeMatrix(self, context.scene.cursor.location, matrix)

    context.window_manager.FriendlyPivotProps.current_trans_mat = flatten(matrix) # TODO unused for now

    context.scene.cursor.matrix = matrix 

    # Set Pivot Center to 3D Cursor
    if context.window_manager.FriendlyPivotProps.set_to_3Dcursor_store:
        bpy.context.scene.tool_settings.transform_pivot_point = 'CURSOR'
               
def handlers(self, arg):
    '''Clear or reset draw handlers.'''
    
    if arg == 'clear':
        if self._highlightHandle:
            if self.mode == 10:
                space = bpy.types.SpaceImageEditor
            else:
                space = bpy.types.SpaceView3D

            space.draw_handler_remove(self._highlightHandle, 'WINDOW')
            self._highlightHandle = ()
        if self._normalHandle:
            bpy.types.SpaceView3D.draw_handler_remove(self._normalHandle, 'WINDOW')
            self._normalHandle = ()

    if arg == 'clear_points':
        if self._pointsHandle:
            bpy.types.SpaceView3D.draw_handler_remove(self._pointsHandle, 'WINDOW')
            self._pointsHandle = ()
    
    if arg == 'clear_ui':
        if self._ui_widget: # bbox ui
            for key, bbox in self._ui_widget.items():
                bbox.clear()
            for key in [key for key in self._ui_widget]: del self._ui_widget[key]

    if arg == 'reset':
        self._highlightHandle = ()
        self._normalHandle = ()
        self._conformMarker = ()
        
    if arg == 'clear multi':
        if self._highlightHandles:
            for key, value in self._highlightHandles.items():
                if self.mode == 10:
                    bpy.types.SpaceImageEditor.draw_handler_remove(value, 'WINDOW')
                else:
                    bpy.types.SpaceView3D.draw_handler_remove(value, 'WINDOW')
            for key in [key for key in self._highlightHandles]: del self._highlightHandles[key]
    
    if arg == 'clear bbox': # TODO simplify block
        if self._bboxHandle: # bbox
            for key, bbox in self._bboxHandle.items():
                bbox.clear()
            for key in [key for key in self._bboxHandle]: del self._bboxHandle[key]

        if self._bboxHandle_lines: # bbox lines
            for key, bbox in self._bboxHandle_lines.items():
                bbox.clear()
            for key in [key for key in self._bboxHandle_lines]: del self._bboxHandle_lines[key]

    if arg == 'clear_widget':
        if self._AxisWidget: # bbox lines
            for key, wid in self._AxisWidget.items():
                wid.clear()
            for key in [key for key in self._AxisWidget]: del self._AxisWidget[key]

    # Init draw prop
    conform = bpy.context.window_manager.FriendlyPivotProps.conform['draw']
    if conform:
        bpy.types.SpaceView3D.draw_handler_remove(conform, 'WINDOW')
        bpy.context.window_manager.FriendlyPivotProps.conform['draw'] = None

def secondSelectFilter(self, handler, sel_list, c_key, component):
    '''Filter second  selection component in the list.'''

    # Remove from list if second select
    if c_key in handler:
        for cl in sel_list: # Remove from list
            if c_key == cl.hashtag:
                sel_list.remove(cl)
        
        # Remove draw component
        if self.mode == 10:
            bpy.types.SpaceImageEditor.draw_handler_remove(handler[c_key], 'WINDOW')
        else:
            bpy.types.SpaceView3D.draw_handler_remove(handler[c_key], 'WINDOW')
        
        del handler[c_key]
        return False
    else:
        sel_list.append(component) # TODO Warning hidden list update, need expose
        return True

def composeMatrix(self, arg, matrix):
    '''Compose matrix from given object's locations.'''
    c_loc = matrix.decompose()[0]

    if self.axel == 'X':
        return Matrix.Translation((c_loc.x, arg.y, arg.z))

    elif self.axel == 'Y':
        return Matrix.Translation((arg.x, c_loc.y, arg.z))

    elif self.axel == 'Z':
        return Matrix.Translation((arg.x, arg.y, c_loc.z))
        
def setOrientation(self, matrix):
    '''Set pivot orientation.'''

    context = bpy.context
    scene = context.scene

    is_edit = False
    if context.mode == 'EDIT_MESH':
        bpy.ops.object.mode_set(mode='OBJECT')
        is_edit = True

    # Set Custom orientation
    orient = scene.transform_orientation_slots[0]
    bpy.ops.transform.create_orientation(name="SCPO", use=True, overwrite=True)
    orient.type = "SCPO"
    orient.custom_orientation.matrix = matrix

    # Bake Custom orientation to LOCAL one
    bake_to_local = context.window_manager.FriendlyPivotProps.set_bake_to_local_store
    if bake_to_local:
        get_affect_origin = scene.tool_settings.use_transform_data_origin
        get_affect_children = scene.tool_settings.use_transform_skip_children
        scene.tool_settings.use_transform_data_origin = True
        scene.tool_settings.use_transform_skip_children = True

        dg = context.evaluated_depsgraph_get()
        for obj in self.selection['data']:
            eval_obj = dg.id_eval_get(obj)
            context.view_layer.update()

            eval_obj.original.select_set(state=True)
            bpy.ops.transform.transform(mode='ALIGN', orient_type='SCPO', orient_matrix_type='SCPO')
            eval_obj.original.select_set(state=False)

            if eval_obj.type == 'MESH':
                initBM(self, eval_obj) # Renew bmesh after set Local

        scene.tool_settings.use_transform_skip_children = get_affect_origin
        scene.tool_settings.use_transform_data_origin = get_affect_children
        scene.transform_orientation_slots[0].type = 'LOCAL'

        context.window_manager.FriendlyPivotProps.set_bake_to_local_store = not context.window_manager.FriendlyPivotProps.set_bake_to_local_store
        
    if context.window_manager.FriendlyPivotProps.orient_active_tool:
        for n in range(4): # Number of transformation tools
            if n != 0:
                if bake_to_local:
                    scene.transform_orientation_slots[n].type = "LOCAL"
                else:
                    scene.transform_orientation_slots[n].type = "SCPO"

    if is_edit:
        setEditMode(self, context)

def averageFunction(args): 
    '''Average given list.'''

    if len(args) == 0:
        return None
    if len(args) == 1:
        return args[0]
    else:
        for n, m in zip(range(len(args)), args):
            if n == 0:
                average = m
            else:
                average = average + m

        return average * (1/len(args))

def flatten(mat):
    '''Flatten given matrix.'''
    dim = len(mat)
    return [mat[j][i] for i in range(dim) for j in range(dim)]

def setPreferences(context, list):
    '''Set preferences from given list of dicts.'''
    
    for d in list:
        if isinstance(d, dict):
            for key,  value in d.items():
                setattr(get_pivot_prefs(), key, value)

def prepfolder():
    '''Prepare directory for preset.'''

    subdir = "scpo"
    directory = os.path.join(bpy.utils.user_resource('SCRIPTS'), "presets", subdir)
    path = bpy.utils.preset_paths(subdir)

    isExist = os.path.exists(directory)

    if directory not in path:
        if not isExist:
            os.makedirs(directory)

    return directory

def setProp(property=''):
    '''Update given property.'''

    prop = bpy.context.window_manager.FriendlyPivotProps[property]
    is_on = False if prop else True
    setattr(bpy.context.window_manager.FriendlyPivotProps, property, is_on)

def getActiveTile(coords):
    '''Get bound by given coords.'''
    min_u = float(floor(coords[0]))
    min_v = float(floor(coords[1]))
    max_u = float(ceil(coords[0]))
    max_v = float(ceil(coords[1]))

    return [min_u, min_v, max_u, max_v]

def checkKey(self, shortcut):
    '''Return Dublicates Of Given Key.'''
    wm = bpy.context.window_manager
    dub_list = {}

    for key in wm.keyconfigs.user.keymaps:
        for keyX in key.keymap_items:
            if key.name in {'Object Mode', 'Mesh', 'Image', 'UV Editor', 'Armature', 'Curve'} and keyX.to_string() == shortcut and keyX.active:
                dub_list[key.name] = keyX.name
    
    return dub_list

def printKeyWarning(box, filterKeys, key_chk):
    for key, item in key_chk.items():
        if key in filterKeys:
            mode = key
            command = item + ' command.'
            box.label(text=" The shortcut has duplicate in " + mode + " with " + command, icon='ERROR')

########################## Classes #############################

class FRIENDLY_widget_dial:
    '''Widget container.'''

    # TODO optimize class, create master class

    def __init__(self, axel='z', matrix=None):
        # TODO axel == 'x'y'z', 'xy'yz'xz' or 's'(screen space, 2d)

        self.is_current = False
        self.is_draw = True

        self.type = 'DIAL'

        self.axel = axel
        self.size_line = 2 # Set line thickness $ TODO Get from prefs?
        theme_color = getattr(bpy.context.preferences.themes[0].user_interface, 'axis_' + str(axel))
        self.color = Vector(tuple(theme_color) + (0.95,)) # Set alpha

        matrix_base = Matrix()
        matrix_world = matrix if matrix else matrix_base
        self.init_mat = None

        # Set main axel for widget
        idx = 2
        if self.axel == 'x': idx = 0
        if self.axel == 'y': idx = 1
        if self.axel == 'z': idx = 2
        self.base_axel = [matrix_base.to_translation(), matrix_base[idx].to_3d()] 

        # Get shape
        self.shape = self.circle_shape_3d(self.base_axel[0], 0.6, 128, idx) # Size of widget
        
        self.prev_mouse = None
        self.base_vector = None
        self._handler = None

        shape = self.refresh_shape(matrix_world)
        shape = self.fading(shape, matrix_world)
        self.draw(shape)

    def fading(self, shape, matrix):
        coords_3d = [matrix @ x for x in self.base_axel]
        region, rv3d = bpy.context.region, bpy.context.region_data
        origin_2d = view3d_utils.location_3d_to_region_2d(region, rv3d, coords_3d[0])
        view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, origin_2d)

        dists = []
        for pt in shape:
            dists.append(mathutils.geometry.distance_point_to_plane(pt, coords_3d[0], view_vector))
        
        viz_list = []
        count = 0
        for dist, pt in zip(dists, shape):
            if dist >= 0.05: count = 0
            if dist < 0.05: # While view_vector is opposite viewplane it's search < 0
                viz_list.insert(count, pt)
                count += 1

        return viz_list

    def get_2d(self, co):
        context = bpy.context
        return view3d_utils.location_3d_to_region_2d(context.region, context.region_data, co)

    def refresh_shape(self, matrix):
        return [matrix @ Vector(x) for x in self.shape]

    def draw_prepare(self, shape):
        # Shade unselected widget
        color = self.color.copy() if self.is_current else self.color.copy() * 0.875 

        if self.is_draw:
            # Open loop
            tmp = list(getIndices(shape, 1))
            tmp.pop()
            indices = tuple(tmp)
            draw_edge(shape, color, indices, self.size_line)
                
    def draw(self, shape):
        self._handler = bpy.types.SpaceView3D.draw_handler_add(self.draw_prepare, (shape,), 'WINDOW', 'POST_VIEW') 

    def clear(self):
        bpy.types.SpaceView3D.draw_handler_remove(self._handler, 'WINDOW')
        self._handler = None
        
    def refresh(self, matrix):
        self.clear()

        shape = self.refresh_shape(matrix) # Refresh widget shape position
        shape = self.fading(shape, matrix) # Trim to visible

        self.draw(shape)

    def execute(self, event, matrix):
        cursor = Vector((event.mouse_region_x, event.mouse_region_y))

        if not self.prev_mouse:
            self.prev_mouse = cursor
            return

        # # Get axel direction from shape line
        coords_3d = [matrix @ x for x in self.base_axel]
        plane_n = (coords_3d[1] - coords_3d[0]).normalized()
            
        region, rv3d = bpy.context.region, bpy.context.region_data
        origin_view = view3d_utils.region_2d_to_origin_3d(region, rv3d, cursor, clamp=None)
        origin_view_prev = view3d_utils.region_2d_to_origin_3d(region, rv3d, self.prev_mouse, clamp=None)

        current_point = view3d_utils.region_2d_to_location_3d(region, rv3d, cursor, coords_3d[0])
        prev_point = view3d_utils.region_2d_to_location_3d(region, rv3d, self.prev_mouse, coords_3d[0])

        current_loc_on_plane = mathutils.geometry.intersect_line_plane(current_point, origin_view, coords_3d[0], plane_n)
        prev_loc_on_plane = mathutils.geometry.intersect_line_plane(origin_view_prev, prev_point, coords_3d[0], plane_n)

        current_vector = current_loc_on_plane - coords_3d[0]
        prev_vector = prev_loc_on_plane - coords_3d[0]

        rot_diff = prev_vector.rotation_difference(current_vector)

        self.prev_mouse = Vector(cursor) # Store previuos mouse position

        return rot_diff.to_matrix()

    def reset(self):
        self.prev_mouse = None

    def isActive(self, event, matrix):
        cursor = event.mouse_region_x, event.mouse_region_y
        circle = self.refresh_shape(matrix)
        circle = self.fading(circle, matrix) # Trim circle

        # Get 2d coords 
        circle_2d = [self.get_2d(x) for x in circle]

        for co in circle_2d:
            if getPointSquare(cursor, co) < (self.size_line**5):
                self.is_current = True
                break
            else:
                self.is_current = False

    def circle_shape_3d(self, co, radius, segments, index):
        idx_list = [0, 1, 2]
        idx_list.remove(index)
        coords = []

        m = (1.0 / (segments - 1)) * (pi * 2)

        for p in range(segments):
            tmp_list = [0,0,0]
            tmp_list[index] = co[index]
            tmp_list[idx_list[0]] = co[idx_list[0]] + cos(m * p) * radius
            tmp_list[idx_list[1]] = co[idx_list[1]] + sin(m * p) * radius

            coords.append(tuple(tmp_list))

        return coords


class FRIENDLY_widget_arrow:
    '''Widget container.'''

    # TODO optimize class, create master class

    def __init__(self, axel='z', matrix=None):
        # axel == 'x'y'z', 'xy'yz'xz' or 's'(screen space, 2d)

        self.is_current = False
        self.is_draw = True

        self.type = 'ARROW'

        self.axel = axel
        self.size_line = 1.5 # Set line thickness # TODO Get from prefs?
        theme_color = getattr(bpy.context.preferences.themes[0].user_interface, 'axis_' + str(axel))
        self.color = Vector(tuple(theme_color) + (0.95,)) # Set alpha

        matrix_base = Matrix()
        matrix_world = matrix if matrix else matrix_base

        # Set main axel for widget
        idx = 2
        if self.axel == 'x': idx = 0
        if self.axel == 'y': idx = 1
        if self.axel == 'z': idx = 2
        self.base_axel = [matrix_base.to_translation(), matrix_base[idx].to_3d()] 

        # Get shape
        self.shape = self.arrow_shape(self.axel, idx)
        
        self.prev_mouse = None
        self._handler = None

        shape = self.refresh_shape(matrix_world)
        self.draw(shape)

    def fading(self, color, line):
        alpha = color.w
        widget_vector = (line[1] - line[0]).normalized()
        region, rv3d = bpy.context.region, bpy.context.region_data

        origin_2d = view3d_utils.location_3d_to_region_2d(region, rv3d, line[0])

        if origin_2d:
            view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, origin_2d)

            dot_p = widget_vector.dot(view_vector)
        else:
            dot_p = 1

        bar = -0.89

        if dot_p < bar:
            alpha = alpha - (abs(dot_p) - abs(bar)) * 10

        return alpha

    def get_2d(self, co):
        context = bpy.context
        return view3d_utils.location_3d_to_region_2d(context.region, context.region_data, co)
    
    def arrow_shape(self, axel, idx):
        cone_base_point = self.base_axel[1].copy()

        base_point_axel = getattr(self.base_axel[0].copy(), axel)
        cone_base_point_axel = getattr(self.base_axel[1].copy(), axel)
        step = cone_base_point_axel * 0.2 # Get 1/5 distance
        
        setattr(cone_base_point, axel, cone_base_point_axel - step)
        cone = cone_bottom = self.circle_shape_3d(cone_base_point, step * 0.25, 20, idx)
        cone.insert(0, self.base_axel[1])

        line = [self.base_axel[0].copy(), cone_base_point.copy()]
        setattr(line[0], axel, base_point_axel + step)

        return line, cone, cone_bottom

    def refresh_shape(self, matrix):
        line = [matrix @ Vector(x) for x in self.shape[0]]
        cone = [matrix @ Vector(x) for x in self.shape[1]]
        cone_bottom = [matrix @ Vector(x) for x in self.shape[2]]
        return line, cone, cone_bottom

    def draw_prepare(self, shape):
        line, cone, cone_bottom = shape

        # Shade unselected widget
        color = self.color.copy() if self.is_current else self.color.copy() * 0.875 # fading
        color.w = self.fading(color, line)

        if self.is_draw:    
            draw_poly(cone, color, 'TRI_FAN', True)
            draw_poly(cone_bottom, color, 'TRI_FAN', True)
            draw_edge(line, color, getIndices(line, 1), self.size_line)
                
    def draw(self, shape):
        self._handler = bpy.types.SpaceView3D.draw_handler_add(self.draw_prepare, (shape,), 'WINDOW', 'POST_VIEW') 

    def clear(self):
        bpy.types.SpaceView3D.draw_handler_remove(self._handler, 'WINDOW')
        self._handler = None
        
    def refresh(self, matrix):
        self.clear()

        shape = self.refresh_shape(matrix) # Refresh widget shape position

        self.draw(shape)

    def execute(self, event, matrix):
        cursor = event.mouse_region_x, event.mouse_region_y

        if not self.prev_mouse:
            self.prev_mouse = Vector(cursor)
            return

        # Get axel direction from shape line
        coords_3d = [matrix @ x for x in self.base_axel]

        region, rv3d = bpy.context.region, bpy.context.region_data
        current_point = view3d_utils.region_2d_to_location_3d(region, rv3d, cursor, coords_3d[0])
        prev_point = view3d_utils.region_2d_to_location_3d(region, rv3d, self.prev_mouse, coords_3d[0])

        current_location = mathutils.geometry.intersect_point_line(current_point, coords_3d[0], coords_3d[1])[0]
        prev_location = mathutils.geometry.intersect_point_line(prev_point, coords_3d[0], coords_3d[1])[0]
        
        offset = current_location - prev_location
        offset_matrix = Matrix.Translation(offset)

        self.prev_mouse = Vector(cursor) # Store previuos mouse position

        return offset_matrix

    def reset(self):
        self.prev_mouse = None

    def isActive(self, event, matrix):
        cursor = event.mouse_region_x, event.mouse_region_y
        line, cone, cone_bottom = self.refresh_shape(matrix)

        # Get 2d coords 
        arrow_2d = [self.get_2d(x) for x in line]
        cone_2d = [[self.get_2d(cone[0]), self.get_2d(x)] for x in cone_bottom]

        # Create in-between points
        ran = 80
        for r in range(ran): # For line
            if r == 0 or r ==1: pass
            else: arrow_2d.append(arrow_2d[0].lerp(arrow_2d[1], r/ran))
        
        ran2 = 10
        for block in cone_2d: # For cone
            for cr in range(ran2):
                if cr == 0 or cr ==1: arrow_2d.append(block[cr])
                else: arrow_2d.append(block[0].lerp(block[1], cr/ran2))

        for co in arrow_2d:
            if getPointSquare(cursor, co) < (self.size_line**5):
                self.is_current = True
                break
            else:
                self.is_current = False

    def circle_shape_3d(self, co, radius, segments, index):
        idx_list = [0, 1, 2]
        idx_list.remove(index)
        coords = []

        m = (1.0 / (segments - 1)) * (pi * 2)

        for p in range(segments):
            tmp_list = [0,0,0]
            tmp_list[index] = co[index]
            tmp_list[idx_list[0]] = co[idx_list[0]] + cos(m * p) * radius
            tmp_list[idx_list[1]] = co[idx_list[1]] + sin(m * p) * radius

            coords.append(tuple(tmp_list))

        return coords

    def circle_shape(self, co, radius, segments):
        coords = []
        m = (1.0 / (segments - 1)) * (pi * 2)
        x, y = co[0], co[1]
        for p in range(segments):
            p1 = x + cos(m * p) * radius
            p2 = y + sin(m * p) * radius
            coords.append((p1, p2))
        return coords


class FRIENDLY_distance_widget:
    '''Draw distance widget.'''
    # TODO improve
    def __init__(self, matrix=None, f_type=None, axis = None):
        self.is_draw = False
        self._handler = None

        self.ui_scale = bpy.context.preferences.system.ui_scale

    def draw_callback_px(self, font_id, axis, mode):
        
        charac = 'V' if mode == 1 else 'D'
        blf.color(0, 1.0, 1.0, 1.0, 0.7)
        blf.position(0, 140, 67, 0)
        blf.size(0, int(15 * self.ui_scale))
        blf.draw(0, charac+axis+': ' + font_id)
                
    def draw(self, font_id, axis, mode):
        if self.is_draw :
            self._handler = bpy.types.SpaceView3D.draw_handler_add(self.draw_callback_px, (font_id, axis, mode), 'WINDOW', 'POST_PIXEL') 

    def refresh(self, font_id, axis, mode):
        self.clear()
        self.draw(font_id, axis, mode)

    def clear(self):
        if self._handler:
            bpy.types.SpaceView3D.draw_handler_remove(self._handler, 'WINDOW')
            self._handler = None


class FRIENDLY_increment_widget:
    '''Increment visual gizmo.'''
    def __init__(self, matrix=None, f_type=None, axis = None):
        self.is_draw = False
        self._handler = None
        self.type = f_type
        self.axis = axis

        self.ui_scale = bpy.context.preferences.system.ui_scale
    
    def get_2d(self, co):
        context = bpy.context
        return view3d_utils.location_3d_to_region_2d(context.region, context.region_data, co)
    
    def shape(self, matrix, step, scale):
        if matrix:
            points_list = []

            if self.type == 'DIAL':
                idx = 2
                if self.axis == 'x': idx = 0
                if self.axis == 'y': idx = 1
                if self.axis == 'z': idx = 2

                radius01 = 1.1 * scale
                radius02 = 1.0 * scale
                rad_step = int(360/step)

                radius_out = self.circle_shape_3d((0,0,0), radius01, rad_step, idx)
                radius_in = self.circle_shape_3d((0,0,0), radius02, rad_step, idx)

                for l01, l02 in zip(radius_out, radius_in):
                    points_list.append(matrix @ Vector(l01))
                    points_list.append(matrix @ Vector(l02))
            else:
                p_range = 101 
                tmp_vector = Vector()
                for r in range(p_range): # TODO find elegant way
                    setattr(tmp_vector, self.axis, (step * r)/ scale)
                    x_point = matrix @ tmp_vector
                    points_list.append(self.get_2d(x_point))

                    setattr(tmp_vector, self.axis, -((step * r)/ scale))
                    x_point = matrix @ tmp_vector
                    points_list.append(self.get_2d(x_point))
            
            return points_list
   
        else: return None

    def draw_prepare(self, shape):
        if self.is_draw and shape:  
            color = Vector((1.0,1.0,1.0,0.7))
            size = 1.5 * self.ui_scale
            if self.type == 'DIAL':
                draw_edge(shape, color, getIndices(shape, 2), size)
            else: 
                for dot_co, idx in zip(shape, range(len(shape))):
                    color_copy = color.copy()
                    if idx >= int(len(shape)/2): # Set gradient color
                        transparency = color.copy().w
                        value_step = transparency / len(shape)
                        color_copy.w = transparency - (idx * value_step)

                    circle_co = self.circle_shape(dot_co, size, 5)
                    if circle_co:
                        draw_poly(circle_co, color_copy, 'TRI_FAN', True)
                
    def draw(self, shape):
        if self.type == 'DIAL': 
            self._handler = bpy.types.SpaceView3D.draw_handler_add(self.draw_prepare, (shape,), 'WINDOW', 'POST_VIEW') 
        else:
            self._handler = bpy.types.SpaceView3D.draw_handler_add(self.draw_prepare, (shape,), 'WINDOW', 'POST_PIXEL') 


    def refresh(self, matrix, step, scale):
        self.clear()
        shape = self.shape(matrix, step, scale)
        self.visible(shape)
        self.draw(shape)

    def clear(self):
        if self._handler:
            bpy.types.SpaceView3D.draw_handler_remove(self._handler, 'WINDOW')
            self._handler = None

    def circle_shape(self, co, radius, segments):
        if co:
            coords = []
            m = (1.0 / segments) * (pi * 2)
            x, y = co[0], co[1]
            for p in range(segments):
                p1 = x + cos(m * p) * radius
                p2 = y + sin(m * p) * radius
                coords.append((p1, p2))
            return coords
        else:
            return None

    def circle_shape_3d(self, co, radius, segments, index):
        idx_list = [0, 1, 2]
        idx_list.remove(index)
        coords = []

        m = (1.0 / segments) * (pi * 2)

        for p in range(segments):
            tmp_list = [0,0,0]
            tmp_list[index] = co[index]
            tmp_list[idx_list[0]] = co[idx_list[0]] + cos(m * p) * radius
            tmp_list[idx_list[1]] = co[idx_list[1]] + sin(m * p) * radius

            coords.append(tuple(tmp_list))

        return coords

    def visible(self, shape): # To prevent widget overlaping
        # if self.type != 'DIAL':
        #     if (shape[0] - shape[3]).length > 1:
        #         self.is_draw = True
        #     else:
        #         self.is_draw = False
        # if self.type == 'DIAL':
        self.is_draw = True


class FRIENDLY_axis_widget:
    '''Axis gizmo group.'''
    
    # TODO Widget for 3D Cursor
    # TODO Snap to grid

    def __init__(self, matrix=None):
        self.widget_set = {}
        self.executed = None # Currently executed widget

        self.init_mat = None # Initial matrix when gizmo starts executing
        self.accumulated_mat = None # Accumulating offsets matrix
        self.current_mat = None # Renewed matrix(after every action) current gizmo transformation

        self.round_alt = 0
        self.direction = 0

        self.is_init_mat = False

        self.prev_angle = 0.0
        self.clockwise = None

        self.modifier = 0
        self.prev_modifier = 0
        self.prev_move_step = 0
        self.prev_loc = None
        self.gizmo_move = False

        self.ui_scale = bpy.context.preferences.system.ui_scale
        self.ui_addon_scale = get_pivot_prefs().pivot_gizmo_scale

        matrix_world = matrix if matrix else Matrix()

        # Scale
        matrix_world = matrix_world.copy() @ self.matrix_viewscale(matrix_world.copy()) 

        # Widgets
        x_t_widget = FRIENDLY_widget_arrow('x', matrix_world)
        y_t_widget = FRIENDLY_widget_arrow('y', matrix_world)
        z_t_widget = FRIENDLY_widget_arrow('z', matrix_world)
        x_r_widget = FRIENDLY_widget_dial('x', matrix_world)
        y_r_widget = FRIENDLY_widget_dial('y', matrix_world)
        z_r_widget = FRIENDLY_widget_dial('z', matrix_world)
        center = FRIENDLY_widget_dot(0, matrix_world, 3 * self.ui_scale * self.ui_addon_scale, Vector((1,1,1,1)), 'circle', 'corner', True, True, False)


        self.widget_set.update({x_t_widget.axel+'_t' : x_t_widget})
        self.widget_set.update({y_t_widget.axel+'_t' : y_t_widget})
        self.widget_set.update({z_t_widget.axel+'_t' : z_t_widget})
        self.widget_set.update({x_r_widget.axel+'_r' : x_r_widget})
        self.widget_set.update({y_r_widget.axel+'_r' : y_r_widget})
        self.widget_set.update({z_r_widget.axel+'_r' : z_r_widget})
        self.widget_set.update({center.index : center})

        self.increm_widget = FRIENDLY_increment_widget()
        self.distance_widget = FRIENDLY_distance_widget()

    def refresh(self, event, mouse_action, matrix):
        # Scale widget
        scale_offset = self.matrix_viewscale(matrix.copy())
        
        # Check for active widget
        if not self.executed: 
            # Get active widget
            for widget in self.widget_set.values():
                widget.isActive(event, matrix.copy() @ scale_offset)

                if widget.is_current:
                    self.executed = widget
                    self.gizmo_move = True
                    break
                else:
                    self.gizmo_move = False

        if not mouse_action and self.executed:
            self.executed = None

        # Check for action on active widget
        if mouse_action and self.executed:
            if mouse_action[0] == 'LEFTMOUSE': # TODO Get RMB/LMB from prefs
                if mouse_action[1] == 'PRESS':
                    if not self.init_mat:
                        self.init_mat = matrix.copy() # Save initial matrix when 
                        self.current_mat = self.init_mat.copy() # For alt
                        self.round_alt = 0
                    
                    # Get movement offset
                    offset = self.executed.execute(event, self.current_mat)
                     
                    # Modifiers' block
                    if offset:
                        loc_mat = Matrix.Translation(self.current_mat.to_translation()) # First location matrix
                        rot_mat = self.current_mat.copy().to_3x3()
                        settings = bpy.context.scene.unit_settings

                        # Round block
                        if event.alt: 
                            # Round initial matrix mode
                            # Count rounds
                            if offset != Matrix():
                                self.round_alt += 1
                            
                            if self.executed.type == 'DIAL':
                                eu_rot_base = rot_mat.to_euler('XYZ')
                                rad = getattr(eu_rot_base, self.executed.axel)

                                value = degrees(rad)
                                new_value = round(value)

                                if self.round_alt == 4: # Filter iteration before execute
                                    eu_rot_base.rotate_axis(self.executed.axel.upper(), radians(new_value - value))
                                    new_rot = eu_rot_base.to_matrix()
                                else:
                                    offset = Matrix() # Hold gizmo
                            else:
                                mult = 0.1 if event.shift else 1 # event.shift to increment transform
                                compare_current_mat = self.current_mat.copy() @ offset.copy().to_4x4() @ rot_mat.copy().to_4x4()
                                
                                if compare_current_mat.to_translation() < self.current_mat.to_translation():
                                    self.direction = -1
                                if compare_current_mat.to_translation() > self.current_mat.to_translation():
                                    self.direction = 1

                                # TODO Add temp gizmo global orientation when alt

                                new_value = loc_mat.to_translation().copy()
                                value = getattr(new_value, self.executed.axel)

                                if settings.system == 'IMPERIAL':
                                    value = value * (1/0.3048)

                                # Remove negativity to make right floor/ceil with negative numbers
                                zero_side = 1
                                if value < 0:
                                    value = abs(value)
                                    zero_side = -1

                                if self.direction == -1:
                                    value = floor(value / mult) * mult
                                if self.direction == 1:
                                    value = ceil(value / mult) * mult
                                
                                # Return original positive/negative to number
                                value = value * zero_side

                                if settings.system == 'IMPERIAL':
                                    value = value / (1/0.3048)

                                if self.round_alt == 4: # Filter iteration before execute
                                    setattr(new_value, self.executed.axel, value)
                                    offset = Matrix.Translation(new_value - loc_mat.to_translation())
                                else:
                                    offset = Matrix() # Hold gizmo

                        # Incremental block
                        if event.ctrl or event.shift and not event.alt:
                            # Incremental mode
                            self.round_alt = 0 # Reset Alt mode
                            move_step, step = 0, 0

                            # Set accumulated matrix to get whole mouse movement
                            if not self.accumulated_mat:
                                self.accumulated_mat = offset
                            else:
                                self.accumulated_mat = self.accumulated_mat @ offset

                            # Rotation increment
                            if self.executed.type == 'DIAL': 

                                plane_n = self.accumulated_mat.to_quaternion().to_axis_angle()[0]
                                rad = self.accumulated_mat.to_quaternion().angle

                                # Get key modifier to increment
                                if event.ctrl:
                                    step = 5
                                    deg = step * round(degrees(rad)/step)
                                    self.modifier = 1
                                if event.shift:
                                    step = 10
                                    deg = round(degrees(rad), -1)
                                    self.modifier = 2
                                if event.shift and event.ctrl:
                                    step = 1
                                    deg = round(degrees(rad))
                                    self.modifier = 3

                                # Add visual increment widget
                                self.increm_widget.type = 'DIAL'
                                self.increm_widget.axis = self.executed.axel
                                self.increm_widget.refresh(self.current_mat, step, scale_offset.decompose()[2][0])

                                if self.prev_modifier != self.modifier:
                                    self.prev_modifier = self.modifier
                                    step = 0
                                
                                # Floor or ceiling offset
                                if self.prev_move_step != deg :
                                    if step != 0:
                                        mult = abs((deg - self.prev_move_step) / step)
                                        step = -step if self.prev_move_step >= deg else step
                                    else:
                                        mult = 1

                                    offset = mathutils.Quaternion(plane_n, radians(step * mult)).to_matrix()
                                    self.prev_move_step = deg
                                else: # This hold rotation 
                                    offset = mathutils.Quaternion(plane_n, radians(0)).to_matrix()
                            else: # Transform increment
                                loc_offset = self.accumulated_mat.to_translation()

                                unitscale = settings.scale_length
                                view_scale = scale_offset.decompose()[2][0]
                                grid_scale = bpy.context.space_data.overlay.grid_scale

                                # Set additional scale according view distance
                                if 0.0 < view_scale < 0.005:
                                    add_scale = 0.001 if settings.system == 'IMPERIAL' else 0.1
                                elif 0.005 < view_scale < 0.05:
                                    add_scale = 1 if settings.system == 'IMPERIAL' else 1
                                elif 0.05 < view_scale < 0.5:
                                    add_scale = 1 if settings.system == 'IMPERIAL' else 1
                                elif 0.5 < view_scale < 5:
                                    add_scale = 12 if settings.system == 'IMPERIAL' else 10
                                elif 5 < view_scale < 25:
                                    add_scale = 36 if settings.system == 'IMPERIAL' else 100
                                elif 25 < view_scale < 450:
                                    add_scale = 792 if settings.system == 'IMPERIAL' else 1000
                                elif view_scale > 450:
                                    add_scale = 7920 if settings.system == 'IMPERIAL' else 10000
                                else:
                                    add_scale = 1.0

                                subunits = 12 * unitscale * (1/0.3048) if settings.system == 'IMPERIAL' else 100 * unitscale
                                subunits = (subunits / add_scale) / grid_scale # Scale increment according view and grid scale
                                distance = loc_offset.length * subunits

                                # Get key modifier
                                if event.ctrl: # 5 cm or 6 inches step increment 
                                    step = 6 if settings.system == 'IMPERIAL' else 5
                                    move_step = step * round(distance / step)
                                    self.modifier = 1

                                if event.shift: # 1 cm or 1 inch step increment 
                                    step = 1
                                    move_step = round(distance)
                                    self.modifier = 2

                                if event.shift and event.ctrl: # 1 mm or 1/8 inch step increment(smaller)
                                    step = 0.125 if settings.system == 'IMPERIAL' else 0.1
                                    move_step = step * round(distance / step)
                                    self.modifier = 3

                                # Add visual increment widget
                                self.increm_widget.type = 'LOC'
                                self.increm_widget.axis = self.executed.axel

                                if not self.is_init_mat or self.prev_modifier != self.modifier: # Refresh inc widget
                                    self.increm_widget.refresh(self.current_mat, step, subunits)
                                    self.is_init_mat = True
                                    step = 0 # if prev mod != cur mod skip round by zero offset
                                    self.prev_modifier = self.modifier
                                    
                                # Floor or ceiling offset
                                if self.prev_move_step != move_step:
                                    if step != 0:
                                        step = -abs(step) if self.prev_move_step > move_step else abs(step)
                                        mult = (move_step - self.prev_move_step) / step
                                    else:
                                        mult = 1

                                    tmp_vector = Vector()
                                    setattr(tmp_vector, self.executed.axel, 1.0)
                                    rot_dif = tmp_vector.rotation_difference(loc_offset) # Get diff from normalized vector
                                    setattr(tmp_vector, self.executed.axel, (step * mult)/subunits) # Set current offset
                                    tmp_vector = rot_dif @ tmp_vector 
                                    offset = Matrix.Translation(tmp_vector)
                                    
                                    self.prev_move_step = move_step
                                else: # This hold transformation
                                    offset = Matrix()

                        else: # Clear increment widget
                            if self.increm_widget: self.increm_widget.clear()
                            self.is_init_mat = False

                        # Set current matrix for widgets
                        if self.executed.type == 'DIAL' and self.round_alt == 4 and event.alt: 
                            # Replace original rotation by rounded one 
                            self.current_mat = loc_mat @ new_rot.to_4x4()
                        else:
                            self.current_mat = loc_mat @ offset.to_4x4() @ rot_mat.to_4x4() # add to current rot if need relative rot
                        self.gizmo_move = True

                        # Add distance's counter 
                        view_mode = 0
                        if event.alt:
                            # Show rounded value
                            cur_distance = new_value if self.executed.type == 'DIAL' else value
                            view_mode = 1
                        else:
                            if self.executed.type == 'DIAL':
                                rot_dif_qua = self.init_mat.to_quaternion().rotation_difference(self.current_mat.to_quaternion())
                                rot_dif = rot_dif_qua.to_swing_twist(self.executed.axel.upper())[1]
                                circle_rot = rot_dif % (2 * pi)
                               
                                if -pi/2 < rot_dif < pi/2:
                                    if not self.clockwise:
                                        self.clockwise = False if rot_dif < 0.0 else True
                                        self.clockwise = None if rot_dif == 0.0 else self.clockwise # Trim zero movement
                                        
                                    if rot_dif < 0.0 and self.prev_angle > 0.0:
                                        self.clockwise = False
                                    if rot_dif > 0.0 and self.prev_angle < 0.0:
                                        self.clockwise = True
                                    
                                if not self.clockwise:
                                    cur_distance = (degrees(circle_rot) - 360) 
                                else:
                                    cur_distance = degrees(circle_rot)
                                self.prev_angle = rot_dif
                            else:
                                cur_distance = (self.current_mat.to_translation() - self.init_mat.to_translation()).length
                                
                                # Find negative/positive direction
                                value_axis_cur = getattr(self.current_mat.copy().to_translation(), self.executed.axel)
                                value_axis_init = getattr(self.init_mat.copy().to_translation(), self.executed.axel)

                                if value_axis_cur < value_axis_init:
                                    cur_distance = -cur_distance

                        self.distance_widget.is_draw = True
                        self.distance_widget.refresh(str(round(cur_distance,2)), self.executed.axel, view_mode)

                # Release mouse
                if mouse_action[1] == 'RELEASE' and self.current_mat:
                    result = self.current_mat
                    mode = 0 if self.executed.type == 'DIAL'else 1 

                    self.executed.reset()
                    self.executed = None

                    self.init_mat = None
                    self.accumulated_mat = None
                    self.is_init_mat = False
                    self.current_mat = None

                    self.clockwise = None
                    self.prev_angle = 0.0

                    self.prev_step = 0
                    self.gizmo_move = False

                    self.increm_widget.is_draw = False
                    self.increm_widget.clear()

                    self.distance_widget.is_draw = False
                    self.distance_widget.clear()

                    return result, mode, self.gizmo_move, None#mouse_action

        # Refresh all widgets positions
        mat = matrix.copy() @ scale_offset if not self.init_mat else self.current_mat.copy() @ scale_offset
        for widget in self.widget_set.values():
            widget.refresh(mat)

        if not self.init_mat: # Clear action when no changes
            mouse_action = None

        return None, None, self.gizmo_move, mouse_action
        
    def matrix_viewscale(self, matrix):
        region, rv3d = bpy.context.region, bpy.context.region_data
        gizmo_size = bpy.context.preferences.view.gizmo_size

        origin_3d = matrix.to_translation()
        origin_2d = view3d_utils.location_3d_to_region_2d(region, rv3d, origin_3d)

        bar = 0.9
        if origin_2d:           
            view_point_2d = origin_2d + Vector((gizmo_size, gizmo_size))
            view_point = view3d_utils.region_2d_to_location_3d(region, rv3d, view_point_2d, origin_3d)
            
            view_dist = (view_point - origin_3d).length
        else:
            view_dist = 1

        coef = view_dist * bar * self.ui_scale * self.ui_addon_scale

        return mathutils.Matrix.Scale(coef, 4)

    def clear(self):
        if self.widget_set:
            for widget in self.widget_set.values():
                widget.clear()

        if self.increm_widget: self.increm_widget.clear()
        if self.distance_widget: self.distance_widget.clear()
        

class FRIENDLY_widget_ui:
    '''UI Widget container with property control.'''

    def __init__(self, co, color, radius, prop, patterns):
        # patterns = [pattern_on, pattern_off]

        self.name = None
        self.is_draw = True
        self.is_current = False
        self.id_visible = True

        self.ui_scale = bpy.context.preferences.system.ui_scale

        self.poperty = prop
        self.patterns = patterns
        self.radius = radius * self.ui_scale # f
        self.color = color # 4d
        self.co = co

        self._handler = None

        prop_bool = self.getProps(self.poperty)
        self.draw(prop_bool)

    def draw_prepare(self, prop_bool):
        button_color = Vector((0.35,0.35,0.35,0.75)) if self.is_current else Vector((0.15,0.15,0.15,0.75))
        button = self.circle_shape(self.co, self.radius, 32) 
        button_line_width = 1 * self.ui_scale
        scale = 0.55 * self.ui_scale

        if self.is_draw:
            if prop_bool:
                icon = [self.co + ((Vector(x) - Vector((20, 20))) * scale) for x in self.patterns[0]]
            else:
                icon = [self.co + ((Vector(x) - Vector((20, 20))) * scale) for x in self.patterns[1]] 

            icon_line_width = 1.5 * self.ui_scale
            draw_poly(button, button_color, 'TRI_FAN') # Draw button
            draw_edge(button, button_color, getIndices(button, 1), button_line_width) # Draw button contour
            draw_edge(icon, self.color, getIndices(icon, 1), icon_line_width) # Draw icon

    def getProps(self, property):
        return bpy.context.window_manager.FriendlyPivotProps[property]

    def setProp(self, prop_bool, property=None):
        if property:
            is_on = False if prop_bool else True
            setattr(bpy.context.window_manager.FriendlyPivotProps, property, is_on)

    def circle_shape(self, co, radius, segments):
        coords = []
        m = (1.0 / (segments - 1)) * (pi * 2)
        x, y = co[0], co[1]
        for p in range(segments):
            p1 = x + cos(m * p) * radius
            p2 = y + sin(m * p) * radius
            coords.append((p1, p2))
        return coords

    def isActive(self, event):
        cursor = event.mouse_region_x, event.mouse_region_y
        cursor_sqr = getPointSquare(cursor, self.co)

        if cursor_sqr < (self.radius**2):
            is_current = True
        else:
            is_current = False
        return is_current

    def refresh(self, event, mouse_action):
        # Draw active and action
        self.is_current = self.isActive(event)
        prop_bool = self.getProps(self.poperty)

        if mouse_action and self.is_current:
            if mouse_action[0] == 'LEFTMOUSE': # TODO Get RMB/LMB from prefs
                if mouse_action[1] == 'RELEASE':
                    self.setProp(prop_bool, self.poperty)
                    mouse_action = None

        self.clear()
        self.draw(prop_bool)
        return self.is_current, mouse_action

    def draw(self, prop_bool):
        self._handler = bpy.types.SpaceView3D.draw_handler_add(self.draw_prepare, (prop_bool,), 'WINDOW', 'POST_PIXEL') 

    def clear(self):
        bpy.types.SpaceView3D.draw_handler_remove(self._handler, 'WINDOW')
        self._handler = None


class FRIENDLY_widget_dot:
    '''Widget container.'''
    def __init__(self, index, co, radius, color, shape, p_type, id_visible, is_draw, fill=False):
        self.index = index
        self.hash = '' #'unique name' by hash
        self.is_current = False
        self.is_draw = is_draw
        self.is_conform = False
        self.id_visible = id_visible

        self.ui_scale = bpy.context.preferences.system.ui_scale

        if type(co) == type(Vector()):
            self.co = co
        if type(co) == type(Matrix()):
            self.co = co.to_translation()
        
        self.co_2d = self.get_2d()
        self.matrix = self.get_matrix()
        self.radius = radius # f
        self.color = color # 4d
        self.shape = shape # 'circle', 'square', rect', 'tris','X', 'diam'
        self.fill = fill
        self.type = p_type # 'corner', 'middle', 'center'

        self._handler = None

        if self.is_draw: self.draw()

    def get_matrix(self):
        return Matrix.Translation(self.co)

    def get_2d(self):
        context = bpy.context
        return view3d_utils.location_3d_to_region_2d(context.region, context.region_data, self.co)

    def draw_prepare(self):
        size_line = 3 * self.ui_scale if self.is_current else 2 * self.ui_scale # Selected point with big outline

        if self.get_2d():
            coord_2d = self.get_2d()
        else:
            coord_2d = Vector((-100,-100)) # Temp Draw TODO remove when rewrite

        if self.shape == 'circle':
            coords = self.circle_shape(coord_2d, self.radius, 16)
            indices = getIndices(coords, 1)
        if self.shape == 'X':
            coords = self.p4_shape(coord_2d, self.radius)
            indices = ((0,2),(1,3))
        if self.shape == 'square':
            coords = self.p4_shape(coord_2d, self.radius)
            indices = ((0,1),(1,2),(2,3),(3,0))
        if self.shape == 'diam':
            coords = self.circle_shape(coord_2d, self.radius, 5)
            indices = getIndices(coords, 1)
        if self.shape == 'tris':
            coords = self.circle_shape(coord_2d, self.radius, 4)
            indices = getIndices(coords, 1)
        
        if not self.id_visible: self.color.w = 0.05 # Fade opposite side point # TODO Get from prefs
        if self.is_current and not self.is_conform: # Highlight point
            self.color.xyzw = 1.0,1.0,1.0,1.0
        if self.is_current and self.is_conform: # Conform action on point
            self.color.xyzw = get_pivot_prefs().conform_color

        if self.is_draw: 
            if self.fill:
                draw_poly(coords, self.color, 'TRI_FAN')
            if self.shape != 'square': # No smooth lines for square             
                draw_edge(coords, self.color, indices, size_line)

    def draw(self):
        self._handler = bpy.types.SpaceView3D.draw_handler_add(self.draw_prepare, (), 'WINDOW', 'POST_PIXEL') 

    def clear(self):
        if self._handler:
            bpy.types.SpaceView3D.draw_handler_remove(self._handler, 'WINDOW')

    def refresh(self, matrix):
        self.clear()
        self.co = matrix.to_translation()
        self.draw()

    def p4_shape(self, co, radius):
        x, y, m = co[0], co[1], radius / 2
        return  [(x + m, y + m), (x + m, y - m), (x - m, y - m), (x - m, y + m)]

    def circle_shape(self, co, radius, segments):
        coords = []
        m = (1.0 / (segments - 1)) * (pi * 2)
        x, y = co[0], co[1]
        for p in range(segments):
            p1 = x + cos(m * p) * radius
            p2 = y + sin(m * p) * radius
            coords.append((p1, p2))
        return coords

    def isActive(self, event, matrix=None):
        if matrix: # TODO tmp solution
            self.is_current = False
            return

        cursor = event.mouse_region_x, event.mouse_region_y
        cursor_sqr = getPointSquare(cursor, self.get_2d())

        if cursor_sqr < (self.radius**2):
            self.is_current = True
            return self.co
        else:
            self.is_current = False
            return


class FRIENDLY_widget_line:
    '''Widget line container.'''
    def __init__(self, index, co_tuple, color, p_type, id_visible):
        self.index = index
        self.hash = '' #'unique name' by hash
        self.is_current = False
        self.is_draw = False
        self.is_conform = False
        self.id_visible = id_visible

        # self.matrix = matrix # TODO replace input co by matrix
        self.co = co_tuple # (p1_co, p2_co) # TODO get co from matrix
        self.co_2d = self.get_2d()
        self.color = color # 4d
        self.type = p_type # 'corner', 'middle', 'center'

        self._handler = None

    def get_2d(self):
        context, coords = bpy.context, []
        for co in self.co:
            coords.append(view3d_utils.location_3d_to_region_2d(context.region, context.region_data, co))  
        return coords

    def draw_prepare(self):
        self.co_2d = self.get_2d()
        distance = 17

        # Create corner line
        vector = (self.co_2d[1] - self.co_2d[0]).normalized()
        coords = [self.co_2d[0]]
        coords.append(self.co_2d[0] + (distance * vector))
        coords.append(self.co_2d[1])
        coords.append(self.co_2d[1] - (distance * vector))
        indices = ([0,1],[2,3],)

        if not self.id_visible: self.color.w = 0.03 # Fade opposite side point # TODO Get from prefs
        if self.is_draw: draw_edge(coords, self.color, indices, 2)

    def draw(self):
        self._handler = bpy.types.SpaceView3D.draw_handler_add(self.draw_prepare, (), 'WINDOW', 'POST_PIXEL') 

    def clear(self):
        bpy.types.SpaceView3D.draw_handler_remove(self._handler, 'WINDOW')


# ---------------------------------------------------------------------------
# Preferences access + preset operators.
# Friendly Pivot preferences live inside the HardSurface Tool add-on preferences.
# ---------------------------------------------------------------------------

_PREFS_EXEMPT = {'rna_type', 'name'}


def get_pivot_prefs():
    '''Friendly Pivot preferences (property group inside the HS add-on prefs).'''
    from ..utility.addon import get_prefs
    return get_prefs().pivot


class FRIENDLY_OT_writePrefs(bpy.types.Operator):
    """Write prefs to file."""

    bl_idname = "friendly.writetofile"
    bl_label = "Write prefs to file"
    bl_description = "Write prefs to file"

    def execute(self, context):
        #Make sure there is a directory for presets
        path = prepfolder()
        name = 'scpo_preset.py'

        addon_prefs = get_pivot_prefs()

        try:
            with open(os.path.join(path, name), "w") as file:
                for prop in addon_prefs.bl_rna.properties:
                    ident = prop.identifier
                    if ident in _PREFS_EXEMPT:
                        continue
                    attr = getattr(addon_prefs, ident)
                    if hasattr(attr, '__len__') and not isinstance(attr, str):
                        attr = [x for x in attr] # colors
                    file.write(str({ident : attr}) + '\n')
        except Exception as e:
            self.report({'ERROR'}, "Couldn't write the preset file: " + str(e))
            return {'CANCELLED'}

        return{'FINISHED'}


class FRIENDLY_OT_restorePrefs(bpy.types.Operator):
    """Restore prefs from file."""

    bl_idname = "friendly.restorefromfile"
    bl_label = "Restore prefs from file"
    bl_description = "Restore prefs from file"

    def execute(self, context):
        path = prepfolder()
        fullpath = os.path.join(path, 'scpo_preset.py')
        preferences = []

        if os.path.exists(fullpath):
            with open(fullpath, 'r') as file:
                for line in file.readlines():
                    try:
                        preferences.append(ast.literal_eval(line))
                    except Exception:
                        pass # skip unreadable lines (e.g. presets written by older versions)

            setPreferences(context, preferences)
        else:
            self.report({'WARNING'}, 'No preset file to restore')

        return{'FINISHED'}


class FRIENDLY_OT_defaultPrefs(bpy.types.Operator):
    """Default prefs."""

    bl_idname = "friendly.defaultprefs"
    bl_label = "Default prefs"
    bl_description = "Default prefs"

    def execute(self, context):
        prefs = get_pivot_prefs()
        for prop in prefs.bl_rna.properties:
            if prop.identifier not in _PREFS_EXEMPT:
                prefs.property_unset(prop.identifier)

        return{'FINISHED'}


class FRIENDLY_OT_Pivot2D(bpy.types.Operator):
    """Set 3D Cursor in 2D Operator"""

    bl_idname = "friendly.pivot2d"
    bl_label = "Friendly: SCPO2D"
    bl_options = {'REGISTER', 'UNDO'}

    # TODO Add support of poly
    # TODO Use barycentric calc of poly center
    # TODO Refresh screen while MMB 
    # TODO Check hang up when MMB press out off kd_tiles

    def modal(self, context, event):
        # View action
        coord = event.mouse_region_x, event.mouse_region_y
        view2d = context.region.view2d
        coord_view = view2d.region_to_view(coord[0],coord[1])
        active_tile = getActiveTile(coord_view)

        # Draw helpline
        context.area.header_text_set(self.help) 

        if self.mmb_mode:
            events = {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}
        else:
            events = {'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'MIDDLEMOUSE'}

        if event.type in events:
            # Allow navigation
            context.region.tag_redraw() 
            return {'PASS_THROUGH'}

        # Check and insert tiles to KD
        if active_tile not in self.map_tiles and active_tile in self.uv_tiles.tolist():
            # t0 = time.time()

            current_idx = np.logical_and(self.kd_coords > active_tile[:-2], self.kd_coords < active_tile[2:])
            idx_range = np.where(current_idx.all(axis=-1))[0]
            current = self.kd_coords[idx_range]

            for i, v in zip(idx_range, current):
                self.kd.insert(Vector(tuple(v)).to_3d(), i)          
            self.kd.balance()

            self.map_tiles.append(active_tile)

        elif event.value == 'PRESS' and event.type == 'SPACE':
            # Force vieport rotate on
            self.rotate = True
            return {'RUNNING_MODAL'}

        elif event.value == 'RELEASE' and event.type == 'SPACE':
            # Force vieport rotate off
            self.rotate = False
            return {'RUNNING_MODAL'}

        elif event.value == 'PRESS' and event.type == 'C':
            # Set center tile mode on
            self.center_mode = True
            return {'RUNNING_MODAL'}

        elif event.value == 'RELEASE' and event.type == 'C':
            # Set center tile mode off
            self.center_mode = False
            return {'RUNNING_MODAL'}

        elif event.value == 'PRESS' and event.type == self.prefs.multi_select_mode_shortcut:
            # Set multi selection
            self.multi = True
            return {'RUNNING_MODAL'} 

        elif event.value == 'PRESS' and event.type == self.prefs.cursor_mode_shortcut:
            # Block execution for screen manipulation
            if event.type == 'MIDDLEMOUSE':
                if event.alt or event.ctrl or event.shift or self.rotate or not self.args:
                    return {'PASS_THROUGH'}

            if self.multi and self.args and not self.center_mode:
                class component():
                    '''Custom element class.'''
                    def __init__(self):
                        self.vertices = None
                        self.hashtag = None
                        self.center = None

                element = component()
                element.vertices = self.args 
                element.center = self.kd_coords[self.index]
                element.hashtag = hash(str(self.args) + str(self.index))
                c_key = element.hashtag

                add = secondSelectFilter(self, self._highlightHandles, self.selected, c_key, element)

                v_coords = []
                if add:
                    self.sel_centers.append(element)
                    for point in self.args:
                        x,y = point[0], point[1]
                        v_coords.append(Vector(view2d.view_to_region(x, y, clip=False)))

                    # Draw component
                    colorElem, indices = getColor(self, v_coords), getIndices(v_coords, 1)
                    attrs = (self, v_coords, colorElem, indices)
                    self._highlightHandles.update({c_key : bpy.types.SpaceImageEditor.draw_handler_add(drawH, attrs, 'WINDOW', 'POST_PIXEL')})

                context.region.tag_redraw()
                return {'RUNNING_MODAL'}

            handlers(self, 'clear')

            if self.args and not self.center_mode:

                bpy.ops.uv.cursor_set(location=self.kd_coords[self.index])
                self.args = None # Reset target

            if self.args and self.center_mode:
                bpy.ops.uv.cursor_set(location=self.args)
                self.args = None # Reset target

            context.region.tag_redraw()
            return {'RUNNING_MODAL'}

        elif event.type == 'MOUSEMOVE':
            handlers(self, 'clear')
            self.index = None
            self.args = None
            v_coords = []

            if self.center_mode:
                v01 = Vector((active_tile[0], active_tile[1]))
                v02 = Vector((active_tile[2], active_tile[3]))
                self.args = v02.lerp(v01, 0.5)
                v_coords.append(view2d.view_to_region(self.args[0], self.args[1]))
            else:
                if active_tile in self.uv_tiles.tolist():
                    co, self.index, dist = self.kd.find(Vector(coord_view).to_3d())
                if self.index:
                    self.args = self.uvs_list[self.index]
                    # Get Draw points
                    for point in self.args:
                        x,y = point[0], point[1]
                        region_point = Vector(view2d.view_to_region(x, y, clip=False))
                        v_coords.append(region_point)

            if len(v_coords) > 0:
                colorElem, indices = getColor(self, v_coords), getIndices(v_coords, 1)
                self.width = self.prefs.highlight_vertex_size
                attrs = (self, v_coords, colorElem, indices)

                self._highlightHandle = bpy.types.SpaceImageEditor.draw_handler_add(drawH, attrs, 'WINDOW', 'POST_PIXEL')          

            context.region.tag_redraw() 
            return {'RUNNING_MODAL'}

        if event.value == 'RELEASE' and event.type == self.prefs.multi_select_mode_shortcut:
            handlers(self, 'clear multi')

            self.multi = False
            length = len(self.selected)

            if length > 0:
                coord_list = []
                for c in self.selected:
                    coord_list.append(c.center)

                coord_list = np.array(coord_list)
                coord = np.average(coord_list, axis = 0)

                bpy.ops.uv.cursor_set(location=coord)
                context.view_layer.update() # Force viewport redraw   
            else:
                return {'RUNNING_MODAL'}

            self.matrices = []
            self.sel_centers = []

            return {'RUNNING_MODAL'}

        elif event.type == self.mainKey and event.value == 'RELEASE':
            handlers(self, 'clear')
            adInit(self, context)
            
            context.area.header_text_set(None)
            context.region.tag_redraw()  
            return {'FINISHED'}

        elif event.type == "ESC" and event.value == 'RELEASE':
            # Additional exit if addon goes wild:)
            handlers(self, 'clear')
            adInit(self, context)

            context.area.header_text_set(None)
            context.region.tag_redraw()  
            return {'FINISHED'}

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        if context.space_data.type in {'IMAGE_EDITOR'} and context.mode == 'EDIT_MESH':
            # Init
            adInit(self, context)
            self.mode = 10 # # Mode for clear handler
            self.map_tiles = [] # Mapping uv tiles
            self.cached_uvs = []
            self.center_mode = False

            handlers(self, 'reset')
            self.prefs = get_pivot_prefs()
            ku = context.window_manager.keyconfigs.user 
            self.mainKey = ku.keymaps.get('Image').keymap_items.find_from_operator('friendly.pivot2d').type # Get initiate shortcut
            
            # t0 = time.time()
            
            # UV action
            sel = context.selected_objects

            # Get from lists
            bpy.ops.object.mode_set(mode='OBJECT')

            count = 0
            idx_ranges = []
            uvs = []

            for obj in sel:
                # Filter meshes only
                if obj.type != 'MESH': 
                    self.report({'WARNING'}, "Select only meshes")
                    return {'CANCELLED'}

                # Init np lists
                uvx = np.zeros((len(obj.data.loops))*2, dtype=float) # uvs coords
                loops_p_idx = np.zeros(len(obj.data.polygons), dtype=int) # uv indices for poly
            
                obj.data.uv_layers.active.data.foreach_get("uv", uvx)
                obj.data.polygons.foreach_get("loop_start", loops_p_idx)

                loops_idx_range = np.column_stack((loops_p_idx[:-1], loops_p_idx[1:])) # poly verts indexing
                idx_add = np.add(loops_idx_range, count, dtype=int)
                
                # Rearrange lists
                reshaped = np.reshape(uvx, (-1, 2))

                if len(uvs) == 0:  
                    uvs = reshaped
                    idx_ranges = idx_add
                else:
                    uvs = np.append(uvs, reshaped, axis=0)
                    idx_ranges = np.append(idx_ranges, idx_add, axis=0)

                if len(uvs) > 50000:
                    self.report({'WARNING'}, "More than 50K uv points, so the addon could not handle this amount!")
               
                count = len(uvs)

            bpy.ops.object.mode_set(mode='EDIT')

            self.uvs = np.unique(uvs, axis=0)

            # Get UV tiles from uv coords
            floor_ar = np.floor(self.uvs)
            ceil_ar = np.ceil(self.uvs)
            self.uv_tiles = np.concatenate((floor_ar, ceil_ar), axis=1)      

            poly_idx = [np.append(np.arange(n[0], n[1]), n[0]) for n in idx_ranges]
            edge_idx = np.unique(np.concatenate([np.column_stack((n[:-1], n[1:])) for n in poly_idx], axis=0),axis=0)

            # Reformat points
            verts_points = self.uvs.reshape(-1,1,2)

            # Get edge and its center
            edges_points = np.take(uvs, edge_idx, axis=0)
            edge_centers = np.average(edges_points, axis=1)

            # Get poly and its center # TODO
            # poly_points = np.take(uvs, poly_idx, axis=0)
            # poly_centers = np.average(poly_points, axis=1)

            # Combine lists
            self.uvs_list = verts_points.tolist() + edges_points.tolist() #+ poly_points.tolist()
            self.kd_coords = np.vstack((self.uvs, edge_centers))#, poly_centers))

            # This is for MMB check
            if self.prefs.cursor_mode_shortcut == 'MIDDLEMOUSE':
                self.mmb_mode = True 
            
            # # KDTree uv tiles
            self.kd = KDTree(len(self.kd_coords))

            # init Addon help block
            if self.prefs.cursor_mode_shortcut == 'LEFTMOUSE': but = 'LMB'
            if self.prefs.cursor_mode_shortcut == 'MIDDLEMOUSE':
                but = 'MMB'
                self.mmb_mode = True 
            if self.prefs.cursor_mode_shortcut == 'RIGHTMOUSE': but = 'RMB'

            h_conform = '  ' + but + ' : Set Cursor'

            # Helpline block
            h_center= ' Hold C : Set Cursor To Tile Center'
            escape_text = ' Esc : Escape'
            rotate_text = ' Space : Force View For Grabbing/Panning'
            multi_text = ' Hold ' + self.prefs.multi_select_mode_shortcut + ' : Multi Select'

            if self.mmb_mode:
                self.help = h_conform + ';' + multi_text + ';' + h_center + ';' + rotate_text + ';' + escape_text + ';'
            else:
                self.help = h_conform + ';' + multi_text + ';' + h_center + ';' + escape_text + ';'

            context.window_manager.modal_handler_add(self)
            context.region.tag_redraw()
            return {'RUNNING_MODAL'}

        else:
            self.report({'WARNING'}, "Activate Edit Mesh Mode")
            return {'CANCELLED'}


class FRIENDLY_OT_Origin(bpy.types.Operator):
    """Set Object's Origin Operator"""

    bl_idname = "friendly.origin"
    bl_label = "Friendly: Set Object's Origin"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if context.space_data.type == 'VIEW_3D':
            if context.mode == 'OBJECT':
                sel = context.selected_objects

                if len(sel) == 1:
                    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center='MEDIAN')

                if len(sel) > 1:
                    storeCursor = context.scene.cursor.matrix.copy()

                    bpy.ops.view3d.snap_cursor_to_selected()
                    bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='BOUNDS')

                    context.scene.cursor.matrix = storeCursor

                    for ob in sel:
                        ob.select_set(state=True)

                    context.region.tag_redraw() 
                    return {'FINISHED'}

                else: return {'CANCELLED'}
            else:
                self.report({'WARNING'}, "In Object mode only")
                return {'CANCELLED'}
        else:
            self.report({'WARNING'}, "Active space must be a View3d")
            return {'CANCELLED'}


class FRIENDLY_OT_Pivot(bpy.types.Operator):
    """Set Custom Pivot Orientation And Origin Operator"""

    bl_idname = "friendly.pivot"
    bl_label = "Friendly: SCPO"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING'}

    def modal(self, context, event):
        # Property store/exchanger
        data = context.window_manager.FriendlyPivotProps
        ui_scale = bpy.context.preferences.system.ui_scale

        # Viewport boundary
        vb_start = Vector((context.region.x, context.region.y))
        vb_end = Vector((context.region.x + context.region.width, context.region.y + context.region.height))

        bake_to_local_text = '  ' + self.prefs.bake_to_local_shortcut + ' : Bake To Local'
        h_autoPtoC_text = '  ' + self.prefs.autoset_cursor_shortcut + ' : Pivot To Cursor'
        orientAT_text = '  ' + self.prefs.autoset_orientAT_shortcut + ' : SCPO To Active Tool'

        # Set Addon Help
        check1_text = context.window_manager.FriendlyPivotProps.set_to_3Dcursor_store
        status1_text = ' (ON)' if check1_text else ' (OFF)'

        check2_text = context.window_manager.FriendlyPivotProps.orient_active_tool
        status2_text = ' (ON)' if check2_text else ' (OFF)'

        check3_text = context.window_manager.FriendlyPivotProps.set_bake_to_local_store
        status3_text = ' (ON)' if check3_text else ' (OFF)'

        escape_text = ' Esc : Escape'
        multi_text = ' Hold ' + self.prefs.multi_select_mode_shortcut + ' : Multi Select'
        bone_text = ' Hold ' + self.prefs.force_kdtree_bones_shortcut + ' : Force Bones'
        curve_text = ' Hold ' + self.prefs.force_kdtree_curves_shortcut + ' : Force Curves'
        axis_text = ' Hold ' + self.prefs.x_axis_shortcut + '/' + self.prefs.y_axis_shortcut + '/' + self.prefs.z_axis_shortcut + ' : Set To One Axis'

        rotate_text = ' Space : Force View Rotation'

        # Filter MMB button
        if self.mmb_mode:
            events = {'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}
            helpline = self.help + bake_to_local_text + status3_text + ';' + h_autoPtoC_text + status1_text + ';' + orientAT_text + status2_text + ';' + multi_text + ';' + bone_text + ';' + curve_text + ';' + axis_text + ';' + rotate_text + ';' + escape_text + ';'
        else:
            events = {'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'MIDDLEMOUSE'}
            helpline = self.help + bake_to_local_text + status3_text + ';' + h_autoPtoC_text + status1_text + ';' + orientAT_text + status2_text + ';' + multi_text + ';' + bone_text + ';' + curve_text + ';' + axis_text + ';' + escape_text + ';'
       
        # Draw helpline
        context.area.header_text_set(helpline) 

        if event.type in events:
            # Allow navigation
            context.region.tag_redraw() 
            return {'PASS_THROUGH'}

        ###################################### MAIN BUTTONS ##################################  #########

        elif event.value == 'PRESS' and event.type == self.prefs.force_kdtree_bones_shortcut:
            # Raycast for non face objects: Bones
            self.kdt = True

            # TODO Make better representation of highlighted elements
            # TODO Make more room for points

            if len(self.force_list) == 0:
                # Get armatures and its 3d points
                class component():
                    '''Custom element class.'''
                    def __init__(self):
                        self.center = None
                        self.matrix_world = None
                        self.points = []

                objects = [ob for ob in context.scene.objects if ob.type=='ARMATURE' and ob.visible_get() == True]

                if len(objects) > 0:
                    for ob in objects:  
                        mw = ob.matrix_world
                        for bone in ob.data.bones:
                            mr = bone.matrix_local.to_3x3()
                            head = component()
                            tail = component()
                            center = component()

                            head.center = mw @ bone.head_local
                            head.matrix_world = Matrix.Translation(head.center) @ mr.to_4x4()
                            head.points = [head.center,]

                            tail.center = mw @ bone.tail_local
                            tail.matrix_world = Matrix.Translation(tail.center) @ mr.to_4x4()
                            tail.points = [tail.center,]

                            center.center = head.center.lerp(tail.center, 0.5)
                            center.matrix_world = Matrix.Translation(center.center) @ mr.to_4x4()
                            center.points = [head.center, tail.center] # Only 2 points treat

                            self.force_list.append(head)
                            self.force_list.append(tail)
                            self.force_list.append(center)

            if len(self.force_list) > 0:
                self.force_2d_coords = {}
                for count, bn in zip(range(len(self.force_list)), self.force_list):
                    if len(bn.points) == 2:
                        point_0_2d = view3d_utils.location_3d_to_region_2d(context.region, context.region_data, bn.points[0])
                        point_1_2d = view3d_utils.location_3d_to_region_2d(context.region, context.region_data, bn.points[1])
                        
                        # Check visibility
                        if vb_start < point_0_2d < vb_end and vb_start < point_1_2d < vb_end:
                            vectorEdge = point_1_2d - point_0_2d
                            distance = vectorEdge.length
                            dist_perc = DIST_MAX/distance

                            # Filter distance equal 2 max dist
                            if distance <= DIST_MAX * 2:
                                p_coord_2d = view3d_utils.location_3d_to_region_2d(context.region, context.region_data, bn.center)
                                self.force_2d_coords[p_coord_2d.to_tuple()] = count
                            else:
                                offset_point_0_2d = point_0_2d + (vectorEdge*dist_perc)
                                offset_point_1_2d = point_1_2d + (vectorEdge*dist_perc)
                                distance2 = (offset_point_1_2d - offset_point_0_2d).length

                                # Make distance shorter for better head&tail selection
                                amount = round((distance2 - DIST_MAX*2) / DIST_MAX)
                                for am in range(amount):
                                    p_coord_2d = offset_point_0_2d.lerp(offset_point_1_2d, am/amount)
                                    self.force_2d_coords[p_coord_2d.to_tuple()] = count
                    else:
                        p_coord_2d = view3d_utils.location_3d_to_region_2d(context.region, context.region_data, bn.points[0])
                        if p_coord_2d:
                            self.force_2d_coords[p_coord_2d.to_tuple()] = count

                if len(self.force_2d_coords) > 0:
                    self.kd = KDTree(len(self.force_2d_coords))
                    for i, v in enumerate(self.force_2d_coords):
                        self.kd.insert(Vector(v).to_3d(), i)

                    self.kd.balance()

            return {'RUNNING_MODAL'}

        elif event.value == 'PRESS' and event.type == self.prefs.force_kdtree_curves_shortcut:
            # Raycast for non face objects: Curves
            self.kdt = True

            if len(self.force_list) == 0:
                # Get curves and its 3d points
                class component():
                    '''Custom element class.'''
                    def __init__(self):
                        self.center = None
                        self.matrix_world = None
                        self.points = []

                dg = context.evaluated_depsgraph_get()
                objects = [dg.id_eval_get(ob) for ob in context.scene.objects if ob.type=='CURVE' and ob.visible_get() == True]
                # TODO Add support modifiers
                
                for obj in objects:
                    mat = obj.matrix_world
                    for ob in obj.data.splines:
                        # TODO Get by np
                        points = ob.points.values() + ob.bezier_points.values()
                        for pt in points:
                            c_point = component()
                            c_point.center = mat @ pt.co.to_3d() # Remove 4d for Nurbs
                            c_point.points = [c_point.center,]
                            c_point.matrix_world = Matrix.Translation(c_point.center)
                            self.force_list.append(c_point)
                
                # Draw curve's points
                if self.prefs.enable_curve_preview:
                    coords = [pt.points[0] for pt in self.force_list]
                    colorElem = self.prefs.curve_points_preview_color
                    size = self.prefs.preview_curve_points_size
                    self._pointsHandle = bpy.types.SpaceView3D.draw_handler_add(draw_vertex, (coords, colorElem, size), 'WINDOW', 'POST_VIEW')
            
            self.force_2d_coords = {}
            for count, bn in zip(range(len(self.force_list)), self.force_list):
                p_coord_2d = view3d_utils.location_3d_to_region_2d(context.region, context.region_data, bn.points[0])
                if p_coord_2d:
                    self.force_2d_coords[p_coord_2d.to_tuple()] = count

            self.kd = KDTree(len(self.force_2d_coords))
            for i, v in enumerate(self.force_2d_coords):
                self.kd.insert(Vector(v).to_3d(), i)

            self.kd.balance()
        
            return {'RUNNING_MODAL'}

        elif event.value == 'RELEASE' and event.type == self.prefs.force_kdtree_curves_shortcut:
            # Reset force raycast var for non face objects
            handlers(self, 'clear_points')
            self.kdt = False
            self.force_list = []
            return {'RUNNING_MODAL'}

        elif event.value == 'RELEASE' and event.type == self.prefs.force_kdtree_bones_shortcut:
            # Reset force raycast var for non face objects
            self.kdt = False
            self.force_list = []
            return {'RUNNING_MODAL'}
        
        elif event.value == 'PRESS' and event.type == self.prefs.force_origin_shortcut:
            # Force transform Origin
            self.transform = True
            return {'RUNNING_MODAL'}
        
        elif event.value == 'RELEASE' and event.type == self.prefs.force_origin_shortcut:
            # Reset force transform Origin
            self.transform = False
            return {'RUNNING_MODAL'} 
             
        elif event.value == 'PRESS' and event.type == self.prefs.force_cursor_shortcut:
            # Force transform 3D Cursor
            self.cursor = True
            return {'RUNNING_MODAL'}
        
        elif event.value == 'RELEASE' and event.type == self.prefs.force_cursor_shortcut:
            # Reset force transform 3D Cursor
            self.cursor = False
            return {'RUNNING_MODAL'}

        elif event.value == 'PRESS' and event.type == self.prefs.reset_scpo_shortcut:
            # Set Orientation to Global and Origin - bounding box center
            bpy.context.scene.transform_orientation_slots[0].type = self.prefs.reset_orient_default
            bpy.context.scene.tool_settings.transform_pivot_point = self.prefs.reset_pivot_center_default

            return {'RUNNING_MODAL'}

        ###################################### AXIS BUTTONS ###########################################

        elif event.value == 'PRESS' and event.type == self.prefs.x_axis_shortcut:
            # Force transform 3D Cursor
            self.axel = 'X'
            return {'RUNNING_MODAL'}
        
        elif event.value == 'RELEASE' and event.type == self.prefs.x_axis_shortcut:
            # Reset force transform 3D Cursor
            self.axel = []
            return {'RUNNING_MODAL'}

        elif event.value == 'PRESS' and event.type == self.prefs.y_axis_shortcut:
            # Force transform 3D Cursor
            self.axel = 'Y'
            return {'RUNNING_MODAL'}
        
        elif event.value == 'RELEASE' and event.type == self.prefs.y_axis_shortcut:
            # Reset force transform 3D Cursor
            self.axel = []
            return {'RUNNING_MODAL'} 

        elif event.value == 'PRESS' and event.type == self.prefs.z_axis_shortcut:
            # Force transform 3D Cursor
            self.axel = 'Z'
            return {'RUNNING_MODAL'}
        
        elif event.value == 'RELEASE' and event.type == self.prefs.z_axis_shortcut:
            # Reset force transform 3D Cursor
            self.axel = []
            return {'RUNNING_MODAL'} 

        ########################################### Bbox ###############################################

        elif event.value == 'PRESS' and event.type == self.prefs.bbox_shortcut:
            # Switch on Bbox Gizmo
            self.is_bbox_gizmo = True

            if not data.object_data['bbox']:
                getBbox(self, context)

            bpy.context.region.tag_redraw()
            return {'RUNNING_MODAL'} 
            
        elif event.value == 'RELEASE' and event.type == self.prefs.bbox_shortcut:
            # Switch off Bbox Gizmo
            handlers(self, 'clear bbox')
            handlers(self, 'clear_ui')

            self.is_bbox_gizmo = False 
            bpy.context.window_manager.FriendlyPivotProps.object_data['bbox'] = None

            context.region.tag_redraw() 
            return {'RUNNING_MODAL'}       

        ###################################### Multi BUTTONS ###########################################

        elif event.value == 'PRESS' and event.type == self.prefs.multi_select_mode_shortcut:
            # Set multi selection
            self.multi = True
            return {'RUNNING_MODAL'} 

        ###################################### OPTIONS BUTTONS ###########################################

        elif event.value == 'PRESS' and event.type == 'SPACE':
            # Force vieport rotate on
            self.rotate = True
            return {'RUNNING_MODAL'}

        elif event.value == 'RELEASE' and event.type == 'SPACE':
            # Force vieport rotate off
            self.rotate = False
            return {'RUNNING_MODAL'}
    
        elif event.value == 'PRESS' and event.type == self.prefs.bake_to_local_shortcut:
            # Set On/Off Bake SCPO to Local
            check_bake_pref = bpy.context.window_manager.FriendlyPivotProps.set_bake_to_local_store
            bpy.context.window_manager.FriendlyPivotProps.set_bake_to_local_store = False if check_bake_pref else True

            return {'RUNNING_MODAL'}

        elif event.value == 'PRESS' and event.type == self.prefs.autoset_cursor_shortcut:  
            # Set switch Pivot Center to 3D Cursor
            check = bpy.context.window_manager.FriendlyPivotProps.set_to_3Dcursor_store
            bpy.context.window_manager.FriendlyPivotProps.set_to_3Dcursor_store = False if check else True

            if bpy.context.window_manager.FriendlyPivotProps.set_to_3Dcursor_store:
                # Store previous pivot center
                pivot_center = context.scene.tool_settings.transform_pivot_point
                bpy.context.window_manager.FriendlyPivotProps.store_previous_pivot_center = pivot_center

                context.scene.tool_settings.transform_pivot_point = 'CURSOR'

            if not bpy.context.window_manager.FriendlyPivotProps.set_to_3Dcursor_store:
                previous_pivot_center = bpy.context.window_manager.FriendlyPivotProps.store_previous_pivot_center

                if previous_pivot_center != "OFF":
                    context.scene.tool_settings.transform_pivot_point = previous_pivot_center
                else:
                    context.scene.tool_settings.transform_pivot_point = 'MEDIAN_POINT' 

            context.region.tag_redraw()
            return {'RUNNING_MODAL'}

        elif event.value == 'PRESS' and event.type == self.prefs.autoset_orientAT_shortcut:  
            # Set switch SCPO to  Active tools
            check = context.window_manager.FriendlyPivotProps.orient_active_tool
            bpy.context.window_manager.FriendlyPivotProps.orient_active_tool = False if check else True

            if not bpy.context.window_manager.FriendlyPivotProps.orient_active_tool:
                for n in range(4):
                    if n != 0:
                        slot = context.window_manager.FriendlyPivotProps.orient_slot['slot'+ str(n)]
                        bpy.context.scene.transform_orientation_slots[n].type = slot

            context.region.tag_redraw()
            return {'RUNNING_MODAL'}

        ###################################### UI INTERACTION BLOCK #######################################
        
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            # Special mouse action for widgets
            self.mouse_action = (event.type, event.value)

            if self.is_widget: # Block LMB action and return modal when cursor under widget
                return {'RUNNING_MODAL'}
            if data.is_origin_gizmo and self.gizmo_move: # Block conform and return modal when gizmo
                return {'RUNNING_MODAL'}
            if event.alt: # For industry keys support
                return {'PASS_THROUGH'} 

            # Bbox set current object
            if self.is_bbox_gizmo: # TODO optimize
                current = None
                for k,v in self._bboxHandle.items(): # TODO Remove loop, add current component to FRIENDLY_props and read here
                    if v.is_current:
                        current = v
                        break
                if not current: 
                    index, object = intersectSurface(self, context, event)
                    if object:
                        bpy.context.window_manager.FriendlyPivotProps.current_obj = object
                    return {'RUNNING_MODAL'}

            # if no conditions the main LMB action will be executed

        elif event.type == 'MIDDLEMOUSE' and event.value == 'PRESS': # TODO INPROGRESS
            # Block when cursor under widget
            if self.gizmo_move or self.is_widget: 
                return {'RUNNING_MODAL'}

            elif self.is_bbox_gizmo: # TODO optimize
                current = None
                for k,v in self._bboxHandle.items(): # TODO Remove loop, add current component to FRIENDLY_props and read here
                    if v.is_current:
                        current = v
                        break
                if not current: 
                    return {'PASS_THROUGH'} 
                    
            elif self._highlightHandle:
                if event.alt or event.ctrl or event.shift or self.rotate:
                    return {'PASS_THROUGH'}
        
                # if no condition the main MMB action will be executed
            else:
                return {'PASS_THROUGH'} 

        elif event.type == 'RIGHTMOUSE' and event.value == 'PRESS':
            # Block when cursor under widget
            if self.gizmo_move or self.is_widget: 
                return {'RUNNING_MODAL'}
            if event.alt: # For industry keys support
                return {'PASS_THROUGH'} 
            # if no condition and loop modal the main RMB action will be executed

        elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            # Special mouse action for widgets
            if self.gizmo_move or self.is_widget:
                self.mouse_action = (event.type, event.value)

            context.region.tag_redraw() 
            return {'RUNNING_MODAL'}

        ###################################### TIMER BLOCK ###########################################

        if event.type == 'TIMER':
            # Timer for UI and gizmo
            if not self.is_bbox_gizmo:
                # 40x40 pix pattern
                P = [(7,0),(7,40),(33,40),(33,15),(14,15),(14,20),(28,20),(28,35),(12,35),(12,0)]
                cross = [(0,5), (15,20), (0,35), (5,40), (20,25), (35,40), (40,35), (25,20), (40,5), (35,0),(20,15),(5,0)]
                patterns = [P,cross]
                widget_pos = Vector((100,75))
                widget_rad = 20
                pix_color = Vector((0.85,0.85,0.85,1.0))
                prop = 'is_origin_gizmo'

                if self._ui_widget:
                    if self.gizmo_move:# Filter widgets: axis - first when moving.
                        pass
                    else:
                        self.is_widget, self.mouse_action = self._ui_widget[prop].refresh(event, self.mouse_action)
                else:
                    ui_widget = FRIENDLY_widget_ui(widget_pos, pix_color, widget_rad, prop, patterns)
                    self._ui_widget.update({ui_widget.poperty : ui_widget})

                if data.is_origin_gizmo:
                    # Timer for axis gizmos
                    matrix = getMatrix(self, context)
        
                    try:
                        # Get origin location
                        region, rv3d = bpy.context.region, bpy.context.region_data
                        origin_coord_2d = view3d_utils.location_3d_to_region_2d(region, rv3d, matrix.decompose()[0])

                        if origin_coord_2d:
                            # Filter offside origin location
                            if 0.0 < origin_coord_2d.x < (region.width) and 0.0 < origin_coord_2d.y < (region.height):
                                if self._AxisWidget:
                                    if self.is_widget and not self.gizmo_move: # Filter widgets: UI - first.
                                        pass
                                    else:
                                        new_mat, action_mode, self.gizmo_move, self.mouse_action = self._AxisWidget['origin'].refresh(event, self.mouse_action, matrix)
                                        if new_mat:
                                            if action_mode == 0:
                                                setOrientation(self, new_mat.to_3x3())
                                            if action_mode == 1:
                                                adOrigin(self, context, new_mat)

                                                # TODO tmp solution to force renew self.result and args after set Origin
                                                index, object = intersectSurface(self, context, event)
                                                if self.result:
                                                    self.args = getComponents(self, event, context, index, object)

                                            context.region.tag_redraw()
                                else:
                                    ui_widget = FRIENDLY_axis_widget(matrix)

                                    if 'origin' in self._AxisWidget: # Clear to prevent repeating
                                        self._AxisWidget['origin'].clear()
                                        del self._AxisWidget['origin']

                                    self._AxisWidget.update({'origin' : ui_widget})

                            else:
                                if 'origin' in self._AxisWidget: # Clear to prevent repeating
                                    self._AxisWidget['origin'].clear()
                                    del self._AxisWidget['origin']

                    except: print('ERROR in pivot module')
                else:
                    handlers(self, 'clear_widget') # Remove axis widget   

                context.region.tag_redraw()
                return {'RUNNING_MODAL'}

            # Timer for bbox mode
            if self.is_bbox_gizmo:
                handlers(self, 'clear_widget') # Remove axis widget   
                handlers(self, 'clear bbox')

                try:
                    # 40x40 pix pattern
                    L = [(10,0), (10,40), (14,40), (14,4), (30,4), (30,0)]
                    W = [(0,40), (4,40), (11,12), (20,38), (29,12), (36,40), (40,40), (30,0), (20,29), (10,0)]
                    patterns = [L,W]
                    widget_pos = Vector((100,75))
                    widget_rad = 20
                    pix_color = Vector((0.85,0.85,0.85,1.0))
                    prop = 'bbox_local'

                    if prop not in self._ui_widget.keys():
                        handlers(self, 'clear_ui') # Remove axis widget ui  

                    # Draw ui widgets
                    if self.prefs.use_world:
                        if self._ui_widget:
                            # Force refresh bbox
                            refresh = False
                            if self.mouse_action: # TODO tmp
                                if self.mouse_action[0] == 'LEFTMOUSE' and self.mouse_action[1] == 'RELEASE': # TODO Get RMB/LMB from prefs
                                    refresh = True

                            self.is_widget, self.mouse_action = self._ui_widget[prop].refresh(event, self.mouse_action)
                            
                            if refresh: getBbox(self, context)
                        else:
                            ui_widget = FRIENDLY_widget_ui(widget_pos, pix_color, widget_rad, prop, patterns)
                            self._ui_widget.update({ui_widget.poperty : ui_widget})

                    # Get object and it's bbox from props
                    object = data.current_obj
                    points_co_list = data.object_data['bbox']

                    alpha = 0.8
                    points_3d = []
                    dots_scale = self.prefs.dots_scale

                    # Bbox indices
                    idx_line = ((0,1),(1,2),(2,3),(3,0),(0,4),(3,7),(7,6),(6,5),(5,4),(7,4),(1,5),(2,6))
                    idx_face = ((0,1,2,3),(7,6,5,4),(0,3,7,4),(4,5,1,0),(3,2,6,7),(1,5,6,2))

                    # Get face visibility
                    vis_points_idx, vis_face_idx = [], []
                    b_region, b_rv3d = context.region, context.region_data
                    
                    # TODO Refresh when bbox is renew this will reduce this calculations
                    for ix in idx_face:
                        vectors = [points_co_list[ix[0]], points_co_list[ix[1]], points_co_list[ix[2]], points_co_list[ix[3]]]
                        co_c = sum(vectors, Vector()) / len(vectors)
                        
                        f_origin_3d = object.matrix_world @ co_c if data.bbox_local else co_c
                        if data.bbox_local:
                            glob_n_vector = object.matrix_world.transposed().inverted() @ mathutils.geometry.normal(vectors)
                        else:
                            glob_n_vector = mathutils.geometry.normal(vectors)

                        f_origin_2d = view3d_utils.location_3d_to_region_2d(b_region, b_rv3d, f_origin_3d)
                        view_vector = view3d_utils.region_2d_to_vector_3d(b_region, b_rv3d, f_origin_2d)

                        if glob_n_vector.dot(view_vector) < 0 :
                            vis_face_idx.append(ix)
                            for i in ix: vis_points_idx.append(i)
                    
                    vis_points_idx = set(vis_points_idx) # Remove doubles

                    # Get corner points
                    for count, co in zip(range(len(points_co_list)), points_co_list):
                        viz = False if count not in vis_points_idx or count not in vis_points_idx else True # Fade opposite side points
                        points_3d.append(FRIENDLY_widget_dot(count, Vector(co), 7.0 * ui_scale * dots_scale, Vector((0.8, 0.3, 0.0, alpha)), 'circle', 'corner', viz, False, True)) # TODO Add color from prefs

                    # Get centers
                    num = len(points_3d)
                    for count, ix in zip(range(len(idx_face)), idx_face):
                        vectors = [points_3d[ix[0]].co, points_3d[ix[1]].co, points_3d[ix[2]].co, points_3d[ix[3]].co]
                        co_c = sum(vectors, Vector()) / len(vectors)

                        n_vector = mathutils.geometry.normal(vectors)
                        c_color = Vector((0.5, 0.8, 0.5, alpha)) # Just in case:)

                        ax_data = bpy.context.preferences.themes[0].user_interface
                        if n_vector.x != 0.0: c_color = Vector(tuple(ax_data.axis_x) + (alpha,))
                        if n_vector.y != 0.0: c_color = Vector(tuple(ax_data.axis_y) + (alpha,))
                        if n_vector.z != 0.0: c_color = Vector(tuple(ax_data.axis_z) + (alpha,)) 
                        
                        viz = False if ix not in vis_face_idx or ix not in vis_face_idx else True # Fade opposite side points
                        points_3d.append(FRIENDLY_widget_dot(count+num, Vector(co_c), 21.0 * ui_scale * dots_scale, c_color, 'square', 'center', viz, False, True))

                    # Get middle points
                    num = len(points_3d)
                    bbox_lines = []
                    for count, idx in zip(range(len(idx_line)), idx_line):
                        co_m = points_3d[idx[1]].co.lerp(points_3d[idx[0]].co, 0.5)
                        viz = False if idx[0] not in vis_points_idx or idx[1] not in vis_points_idx else True # Fade opposite side points
                        points_3d.append(FRIENDLY_widget_dot(count+num, Vector(co_m), 8 * ui_scale * dots_scale, Vector((0.0, 0.7, 0.6, alpha)), 'diam', 'middle', viz, False, True)) # TODO Add color from prefs 
                        # Endlines
                        bbox_lines.append(FRIENDLY_widget_line(count, (points_3d[idx[0]].co, points_3d[idx[1]].co), Vector((0.8, 0.2, 0.0, alpha)), 'middle', viz))

                    # Fraw corner angels
                    for line in bbox_lines:
                        if data.bbox_local:
                            line.co = [object.matrix_world @ x for x in line.co]
            
                        line.hash = hash(object.name + str(count))
                        line.is_draw = True 

                        if str(line.index) in self._bboxHandle_lines: # Clear to prevent repeating
                            self._bboxHandle_lines[str(line.index)].clear()
                            del self._bboxHandle_lines[str(line.index)]

                        line.draw()
                        self._bboxHandle_lines.update({str(line.index) : line})

                    # Final setup points and draw
                    for count, widget in zip(range(len(points_3d)), points_3d):
                        if data.bbox_local:
                            widget.co = object.matrix_world @ widget.co
                            widget.matrix = object.matrix_world @ widget.matrix

                        widget.hash = hash(object.name + str(count))
                        widget.is_draw = True 

                        if str(widget.index) in self._bboxHandle: # Clear to prevent repeating
                            self._bboxHandle[str(widget.index)].clear()
                            del self._bboxHandle[str(widget.index)]

                        widget.draw()
                        self._bboxHandle.update({str(widget.index) : widget})

                    # Draw active
                    if not self.is_widget: # Block if cursor under UI
                        for v in self._bboxHandle.values():
                            v.isActive(event)

                except: print('ERROR in Bbox module')

            context.region.tag_redraw()
            return {'RUNNING_MODAL'}

        ###################################### EXECUTE BLOCK ###########################################

        if event.type == self.prefs.orient_mode_shortcut and event.value == 'PRESS':
            handlers(self, 'clear')

            # Set orient mode
            if self.kdt and self.args:
                setOrientation(self, self.args[0].matrix_world.to_3x3())
                
            if self.result: 
                self.mouse_action = None # Clear mouse action for widgets

                try:
                    # Draw conform
                    coords = getDrawPoints(self.args)
                    colorConform, indices = self.prefs.conform_color, getIndices(coords)
                    self._conformMarker = bpy.types.SpaceView3D.draw_handler_add(drawH, (self, coords, colorConform, indices), 'WINDOW', 'POST_VIEW')
                    bpy.context.window_manager.FriendlyPivotProps.conform['draw'] = self._conformMarker

                    if self.multi:
                        self.mode = 0

                        component = getCompMult(self)
                        c_key = component.hashtag

                        add = secondSelectFilter(self, self._highlightHandles, self.selected, c_key, component)

                        if add:
                            # Draw component
                            coords = getDrawPoints(self.args)
                            colorElem, indices = getColor(self, coords), getIndices(coords) # TODO use special color?
                            self._highlightHandles.update({c_key : bpy.types.SpaceView3D.draw_handler_add(drawH, (self, coords, colorElem, indices) , 'WINDOW', 'POST_VIEW')})

                        context.region.tag_redraw()
                        return {'RUNNING_MODAL'}
                    else:
                        # For single selection
                        matrix = self.matrix
                        setOrientation(self, matrix)

                        if context.window_manager.FriendlyPivotProps.set_bake_to_local_store:
                            # TODO tmp solution to force renew self.result and args after set Origin
                            index, object = intersectSurface(self, context, event)

                            if self.result:
                                self.transformed = True 
                                self.args = getComponents(self, event, context, index, object)

                        if self.transform:
                            adOrigin(self, context, self.center)

                            self.transformed = True

                        context.region.tag_redraw()
                        return {'RUNNING_MODAL'}

                except:pass

            context.region.tag_redraw() 
            return {'RUNNING_MODAL'}
     
        elif event.value == 'PRESS' and event.type == self.prefs.cursor_mode_shortcut:
            handlers(self, 'clear')

            if self.is_bbox_gizmo: # Bbox execution mode
                current = None
                for k,v in self._bboxHandle.items(): # TODO Remove loop, add current component to FRIENDLY_props and read here
                    if v.is_current: current = v

                v.is_conform = True
                adCursor(self, context, current.matrix)
                context.view_layer.update() # Force viewport redraw

                return {'RUNNING_MODAL'}

            data.set_3Dcursor = True

            if self.multi:
                self.mode = 1 

                component = getCompMult(self)
                c_key = component.hashtag

                add = secondSelectFilter(self, self._highlightHandles, self.selected, c_key, component)

                if add:
                    self.sel_centers.append(self.args[0])

                    # Draw component
                    coords = getDrawPoints(self.args)
                    colorElem, indices = getColor(self, coords), getIndices(coords) # TODO use special color?
                    self._highlightHandles.update({c_key : bpy.types.SpaceView3D.draw_handler_add(drawH, (self, coords, colorElem, indices) , 'WINDOW', 'POST_VIEW')})

                context.region.tag_redraw()
                return {'RUNNING_MODAL'}
            else:
                if self.kdt:
                    adCursor(self, context, self.args[0].matrix_world)
                else:
                    # Draw conform
                    coords = getDrawPoints(self.args)
                    colorConform, indices = self.prefs.conform_color, getIndices(coords)
                    self._conformMarker = bpy.types.SpaceView3D.draw_handler_add(drawH, (self, coords, colorConform, indices), 'WINDOW', 'POST_VIEW')
                    bpy.context.window_manager.FriendlyPivotProps.conform['draw'] = self._conformMarker 

                    adCursor(self, context)

                    if self.transform:
                        matrix = self.matrix
                        setOrientation(self, matrix)

                        if context.window_manager.FriendlyPivotProps.set_bake_to_local_store:
                            # TODO tmp solution to force renew self.result and args after set Origin
                            index, object = intersectSurface(self, context, event)
                            
                            if self.result:
                                self.transformed = True 
                                self.args = getComponents(self, event, context, index, object)

                context.view_layer.update() # Force viewport redraw

            context.region.tag_redraw() 
            return {'RUNNING_MODAL'}

        elif event.type == self.prefs.origin_mode_shortcut and event.value == 'PRESS':
            handlers(self, 'clear')

            if self.is_bbox_gizmo: # Bbox execution mode
                # TODO Remove loop, add current point to FRIENDLY_props and read here

                for k,v in self._bboxHandle.items(): 
                    if v.is_current:
                        v.is_conform = True
                        adOrigin(self, context, v.matrix)
                        getBbox(self, context)

                context.region.tag_redraw() 
                return {'RUNNING_MODAL'}

            if self.kdt and self.args:
                # TODO Conform ?
                adOrigin(self, context, self.args[0].matrix_world)

            if self.result:
                data.set_Origin = True
                
                # Draw conform
                coords = getDrawPoints(self.args)
                colorConform, indices = self.prefs.conform_color, getIndices(coords)
                self._conformMarker = bpy.types.SpaceView3D.draw_handler_add(drawH, (self, coords, colorConform, indices), 'WINDOW', 'POST_VIEW')
                bpy.context.window_manager.FriendlyPivotProps.conform['draw'] = self._conformMarker

                if self.axel:
                    setattr(data, self.axel.lower()+'_axis', True)

                    # set self.axis(this indicator helps to filter active axel later)
                    for key in self.axis:
                        if self.axel == key:
                            self.axis[key] = True
                        else:
                            self.axis[key] = False
                else:
                    data.x_axis, data.y_axis, data.z_axis = True, True, True

                if self.cursor:
                    adCursor(self, context)
                else:
                    if self.multi:
                        self.mode = 2

                        component = getCompMult(self)
                        c_key = component.hashtag

                        add = secondSelectFilter(self, self._highlightHandles, self.selected, c_key, component)

                        if add:
                            # Draw component
                            coords = getDrawPoints(self.args)
                            colorElem, indices = getColor(self, coords), getIndices(coords) # TODO use special color?
                            self._highlightHandles.update({c_key : bpy.types.SpaceView3D.draw_handler_add(drawH, (self, coords, colorElem, indices) , 'WINDOW', 'POST_VIEW')})

                        context.region.tag_redraw()
                        return {'RUNNING_MODAL'}

                    else:
                        # For single selection
                        adOrigin(self, context, self.center)

                        # TODO tmp solution to force renew self.result and args after set Origin
                        index, object = intersectSurface(self, context, event)
                        if self.result:
                            self.args = getComponents(self, event, context, index, object)
                                                
                        if self.transform:
                            matrix = self.matrix
                            setOrientation(self, matrix)

                        context.region.tag_redraw()

                self.transformed = True

            context.region.tag_redraw() 
            return {'RUNNING_MODAL'}

        elif event.type == 'MOUSEMOVE':
            handlers(self, 'clear')

            # # Block draw when UI
            if self.gizmo_move or self.is_widget or self.is_bbox_gizmo: 
                return {'RUNNING_MODAL'}
           
            # Get current object and component
            index, object = intersectSurface(self, context, event)

            if self.kdt and index:
                coords = object.points
                self.args = index, object

                if self.prefs.enable_preview:
                    # Draw preview axis
                    axCoords = axisDrawPoints(self)
                    colorAxis = self.axisColor
                    size = self.prefs.preview_line_width
                    drawData02 = (axCoords, colorAxis, size) 
                    self._normalHandle = bpy.types.SpaceView3D.draw_handler_add(drawAxis, drawData02, 'WINDOW', 'POST_VIEW')
                
                self.width = self.prefs.highlight_vertex_size
                colorElem, indices = getColor(self, coords), getIndices(coords)
                self._highlightHandle = bpy.types.SpaceView3D.draw_handler_add(drawH, (self, coords, colorElem, indices) , 'WINDOW', 'POST_VIEW')          
            
            # Component mode
            elif self.result:
                #### WIREFRAME section ####
                # Restore wireframe for prev object
                if data.current_obj_orient:
                    if data.current_obj_orient != object:
                        context.window_manager.FriendlyPivotProps.current_obj_orient.show_wire = data.current_obj_wire_backup

                        # Save current object wireframe show state to props
                        context.window_manager.FriendlyPivotProps.current_obj_wire_backup = object.show_wire
                
                # Set current object to props and set Wireframe show ON
                context.window_manager.FriendlyPivotProps.current_obj_orient = object
                object.show_wire = True
                #### WIREFRAME section end ####

                self.args = getComponents(self, event, context, index, object) # Get current object and component
                
                # Break action if there is an error with index out of range in mesh
                if self.args == None:
                    self.report({'WARNING'}, "Poly index is out of range - can't draw the component.")
                    return {'RUNNING_MODAL'}

                elem = self.args[0]
                mx = self.args[1].matrix_world

                self.matrix = getCompMatrix(self, elem, mx) # While moving share matrix to other operators

                if self.prefs.enable_preview:
                    # Draw preview axis
                    axCoords = axisDrawPoints(self)
                    colorAxis = self.axisColor
                    size = self.prefs.preview_line_width
                    drawData02 = (axCoords, colorAxis, size) 
                    self._normalHandle = bpy.types.SpaceView3D.draw_handler_add(drawAxis, drawData02, 'WINDOW', 'POST_VIEW')
                
                # Draw component
                coords = getDrawPoints(self.args)
                colorElem, indices = getColor(self, coords), getIndices(coords)
                self._highlightHandle = bpy.types.SpaceView3D.draw_handler_add(drawH, (self, coords, colorElem, indices) , 'WINDOW', 'POST_VIEW')          
            
            else:
                handlers(self, 'reset')
                   
            context.region.tag_redraw() 
            return {'RUNNING_MODAL'}
        
        ###################################### RELEASE BLOCK ###########################################

        if event.value == 'RELEASE' and event.type == self.prefs.multi_select_mode_shortcut:
            handlers(self, 'clear multi')

            self.multi = False
            length = len(self.selected)

            if self.mode == 0 and length > 0: 
                # TODO switch on later
                # avrgOrient = getMatrixMulti(self, self.selected)
                # setOrientation(self, avrgOrient)
                return {'RUNNING_MODAL'}

            elif self.mode == 1 and length > 0:
                matrices, idx = [],[]
                for c in self.selected:
                    for v in c.vertices:
                        if v.hashtag not in idx: # Filter doubles in verts list
                            matrices.append(v.center)
                            idx.append(v.hashtag)

                avrgCenter = averageFunction(matrices)
                avrgOrient = getMatrixMulti(self, self.selected)
                
                matrix = avrgCenter #@ avrgOrient.to_4x4() # TODO switch on later
                adCursor(self, context, matrix)
                context.view_layer.update() # Force viewport redraw

            elif self.mode == 2 and length > 0:
                matrices, idx = [],[]
                for c in self.selected:
                    for v in c.vertices:
                        if v.hashtag not in idx: # Filter doubles in verts list
                            matrices.append(v.center)
                            idx.append(v.hashtag)

                avrgCenter = averageFunction(matrices)
                adOrigin(self, context, avrgCenter)

                self.transformed = True 

                context.region.tag_redraw()      
            else:
                return {'RUNNING_MODAL'}

            # TODO Add hilghlight comform for all components

            self.matrices = []
            self.sel_centers = []

            return {'RUNNING_MODAL'}

        elif event.type == self.mainKey and event.value == 'RELEASE':
            handlers(self, 'clear')
            handlers(self, 'clear_points')
            handlers(self, 'clear multi')
            handlers(self, 'clear bbox')
            handlers(self, 'clear_ui')
            handlers(self, 'clear_widget')

            # Restore wireframe show
            if data.current_obj_orient:
                context.window_manager.FriendlyPivotProps.current_obj_orient.show_wire = data.current_obj_wire_backup

            if self._timer: context.window_manager.event_timer_remove(self._timer)

            self._timer = None

            del self.bm # Del var to clear memory(good for heavy mesh)\
            adInit(self, context)
            context.area.header_text_set(None)
            
            # Restore selection
            storeSelection(self, context, 'restore')
            context.region.tag_redraw()
            return {'FINISHED'}

        elif event.type == "ESC" and event.value == 'PRESS':
            # Additional exit if addon goes wild:)
            # TODO Tmp solution, to remove
            handlers(self, 'clear')
            handlers(self, 'clear multi')
            handlers(self, 'clear bbox')
            handlers(self, 'clear_ui')
            handlers(self, 'clear_widget')

            # Restore wireframe show
            if data.current_obj_orient:
                context.window_manager.FriendlyPivotProps.current_obj_orient.show_wire = data.current_obj_wire_backup
            
            if self._timer: context.window_manager.event_timer_remove(self._timer)
            
            del self.bm # Del var to clear memory(good for heavy mesh)
            adInit(self, context)
            context.area.header_text_set(None)

            # Restore selection
            storeSelection(self, context, 'restore')
            context.region.tag_redraw()  
            return {'FINISHED'}

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        if context.space_data.type == 'VIEW_3D':
            # init marker
            bpy.context.window_manager.FriendlyPivotProps.is_init = True

            data = context.window_manager.FriendlyPivotProps
            # Get current selection
            self.selection = storeSelection(self, context, 'store')

            if self.selection == None:
                self.report({'WARNING'}, "Must be at least one selected object")
                return {'CANCELLED'}
            
            # Check for emulate MMB
            if context.preferences.inputs.use_mouse_emulate_3_button:
                pass
                # self.report({'WARNING'}, "The 3 button emulate mode is ON but you still need 3 button mouse.")
            
            # init
            adInit(self, context)
            self.prefs = get_pivot_prefs()
            ku = context.window_manager.keyconfigs.user 
            self.mainKey = ku.keymaps.get('3D View').keymap_items.find_from_operator('friendly.pivot').type # Get initiate shortcut
            handlers(self, 'reset')

            # Set Object mode
            if self.selection['mode'] == 'EDIT_MESH' and not self.prefs.is_edit_mode: # TODO Temp solution cause of raycast hangups in edit mode and Origin is being set up in Object mode
                bpy.ops.object.mode_set(mode='OBJECT')

           # # Init current object in friendly props
            if not self.prefs.use_world:
                bpy.context.window_manager.FriendlyPivotProps.bbox_local = True

            if not self.prefs.pivot_gizmo_on:
                bpy.context.window_manager.FriendlyPivotProps.is_origin_gizmo = False

            # TODO fix init offset of bbox when RMB execute before bbox init
            bpy.context.window_manager.FriendlyPivotProps.is_origin_gizmo = True if data.is_origin_gizmo else False
            bpy.context.window_manager.FriendlyPivotProps.bbox_local = True if data.bbox_local else False
            bpy.context.window_manager.FriendlyPivotProps.current_obj = self.selection['data'][-1] # TODO Waiting for world object.bound_box API for multiobjects bbox    

            if data.init1 == False:
                bpy.context.window_manager.FriendlyPivotProps.set_to_3Dcursor_store = self.prefs.set_to_3Dcursor
                bpy.context.window_manager.FriendlyPivotProps.init1 = True
            
            if data.init2 == False:
                bpy.context.window_manager.FriendlyPivotProps.orient_active_tool = self.prefs.set_in_Activetool
                bpy.context.window_manager.FriendlyPivotProps.init2 = True

            if data.init3 == False:
                bpy.context.window_manager.FriendlyPivotProps.set_bake_to_local_store = self.prefs.set_bake_to_local
                bpy.context.window_manager.FriendlyPivotProps.init3 = True
            
            length = len(data.orient_slot.values())
            for n in range(4):
                if n != 0:
                    if bpy.context.scene.transform_orientation_slots[n].type != "SCPO":
                        context.window_manager.FriendlyPivotProps.orient_slot['slot'+ str(n)] = bpy.context.scene.transform_orientation_slots[n].type
                    if length == 0:
                        context.window_manager.FriendlyPivotProps.orient_slot['slot'+ str(n)] = "DEFAULT"

            # init Addon help block
            button_list = [self.prefs.orient_mode_shortcut, self.prefs.cursor_mode_shortcut, self.prefs.origin_mode_shortcut]
            cnt = 0
            for b in button_list:
                if b == 'LEFTMOUSE': but = 'LMB'
                if b == 'MIDDLEMOUSE':
                    but = 'MMB'
                    self.mmb_mode = True # This is for MMB check # TODO ?
                if b == 'RIGHTMOUSE': but = 'RMB'
                # if b == 'BUTTON4MOUSE': but = '4MB'
                # if b == 'BUTTON5MOUSE': but = '5MB'
                # if b == 'BUTTON6MOUSE': but = '6MB'
                # if b == 'BUTTON7MOUSE': but = '7MB'
                if cnt == 0: or_mode = but
                if cnt == 1: c_mode = but
                if cnt == 2: o_mode = but
                cnt += 1
             
            h_conform1 = '  ' + or_mode + ' : Set Orient;'
            h_conform2 = '  ' + c_mode + ' : Set Cursor;'
            h_conform3 = '  ' + o_mode + ' : Set Origin;'
            h_orient = '  Hold ' + self.prefs.force_origin_shortcut + ' : Set Orient & Origin;'
            
            self.help = h_conform1 + h_conform2 + h_conform3 + h_orient

            # Init timer for ui and gizmo and curve preview
            if self._timer: context.window_manager.event_timer_remove(self._timer) # Prevent doubles
            self._timer = context.window_manager.event_timer_add(0.01, window=context.window)

            # Stop init marker
            bpy.context.window_manager.FriendlyPivotProps.is_init = False

            context.window_manager.modal_handler_add(self)
            context.region.tag_redraw()             
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "Active space must be a View3d")
            return {'CANCELLED'}


class Friendly_PivotProps(bpy.types.PropertyGroup):
    '''Friendly Pivot addon properties.'''

    # TODO Set all prefs invisible?

    # Var for conform haldle
    conform = {
        "draw": None,
    }

    # Store orietation slot(for Active Tool)
    orient_slot = {}

    # Var for conform haldle
    object_data = {
        "bbox": None,
    }

    # Store current orient and transform matrices
    # current_orient_mat : bpy.props.FloatVectorProperty(
    #     name="Current Orient Matrix",
    #     size=16,
    #     subtype="MATRIX"
    # )
    # current_trans_mat : bpy.props.FloatVectorProperty(
    #     name="Current Transform Matrix",
    #     size=16,
    #     subtype="MATRIX"
    # )

    # Store previous orient, origin, cursor matrices
    # prev_orient_mat : bpy.props.FloatVectorProperty(
    #     name="Old Orient Matrix",
    #     size=16,
    #     subtype="MATRIX"
    # )

    # TODO Need to change this property to list because it could  be several origins
    # prev_origin_mat : bpy.props.FloatVectorProperty(
    #     name="Old Origin Matrix",
    #     size=16,
    #     subtype="MATRIX"
    # )
    # prev_cursor_mat : bpy.props.FloatVectorProperty(
    #     name="Old Cursor Matrix",
    #     size=16,
    #     subtype="MATRIX"
    # )

    # For replace self.axis INDEV
    # modes : bpy.props.BoolVectorProperty(    
    #     name="modes",
    #     description="Property with action modes",
    #     default=(False, False, False)
    # )

    current_obj_wire_backup : bpy.props.BoolProperty(
        name="Current object wireframe",
        description="Backup current object wireframe bool to restore",
        default=False,
    )
    # Store current object TODO combine these props to one in future
    current_obj_orient : bpy.props.PointerProperty(
        name="Current object Orient mode",
        type=bpy.types.Object,
    )

    current_obj : bpy.props.PointerProperty(
        name="Current object Bbox mode",
        type=bpy.types.Object,
        update=getBbox
    )

    is_init : bpy.props.BoolProperty(
        name="Addon init status",
        description="Addon init status",
        default=False,
    )

    is_origin_gizmo : bpy.props.BoolProperty(
        name="Axis Gizmo",
        description="Switch On orient/origin gizmo",
        default=True,
    )

    bbox_local : bpy.props.BoolProperty(
        name="Local Bbox",
        description="On local bbox orientation",
        default=True,
    )

    # Temp savings for blender session
    init1 : bpy.props.BoolProperty(
        name="init1",
        description="Init Prop For Set 3Dcursor action",
        default=False
    )

    init2 : bpy.props.BoolProperty(
        name="init2",
        description="Init Prop For Set Orient to active tool",
        default=False
    )

    init3 : bpy.props.BoolProperty(
        name="init3",
        description="Init prop For Bake To Local Store",
        default=False
    )

    set_to_3Dcursor_store : bpy.props.BoolProperty(
        name="Set Pivot center to 3D Cursor",
        description="When True Pivot Center moves to 3D Cursor",
        default=True
    )

    store_previous_pivot_center : bpy.props.StringProperty(
        name="Store previous Pivot center",
        description="Store previous Pivot center",
        default="OFF"
    )

    set_bake_to_local_store : bpy.props.BoolProperty(
        name="Bake Orientation Directly to Local Store",
        description="When True this bakes Pivot Orientation directly to LOCAL Store",
        default=False
    )

    orient_active_tool : bpy.props.BoolProperty(
        name="Set Orient to Move/Rotate/Scale/Transfom tool",
        description="When True this sets Pivot Orientation to Move/Rotate/Scale/Transfom tools",
        default=False
    )

    set_3Dcursor : bpy.props.BoolProperty(
        name="3D Cursor",
        description="Set 3D Cursor as additional action when True",
        default=False
    )

    set_Origin : bpy.props.BoolProperty(
        name="Origin",
        description="Set Origin as additional action when True",
        default=False
    )

    set_Orient : bpy.props.BoolProperty(
        name="Orient",
        description="Set Pivot Orientation as additional action when True",
        default=False
    )

    x_axis : bpy.props.BoolProperty(
        name="X axis",
        description="Set Origin to X axis",
        default=False
    )
    y_axis : bpy.props.BoolProperty(
        name="Y axis",
        description="Set Origin to Y axis",
        default=False
    )

    z_axis : bpy.props.BoolProperty(
        name="Z axis",
        description="Set Origin to Z axis",
        default=False
    )

    local_axis : bpy.props.BoolProperty(
        name="local axis",
        description="Set Origin axis in local(Object transforms)",
        default=False
    )

classes = (
    FRIENDLY_OT_Pivot,
    FRIENDLY_OT_Pivot2D,
    FRIENDLY_OT_Origin,
    FRIENDLY_OT_writePrefs,
    FRIENDLY_OT_restorePrefs,
    FRIENDLY_OT_defaultPrefs,
    Friendly_PivotProps,
    )


def register_friendly_pivot():
    for cls in classes:
        register_class(cls)

    bpy.types.WindowManager.FriendlyPivotProps = bpy.props.PointerProperty(type=Friendly_PivotProps)


def unregister_friendly_pivot():
    try:
        del bpy.types.WindowManager.FriendlyPivotProps
    except Exception:
        pass

    for cls in reversed(classes):
        unregister_class(cls)
