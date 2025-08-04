import bmesh
import bpy
import collections
import mathutils
import math
from bpy_extras import view3d_utils
from bpy.types import (
        Operator,
        Menu,
        Panel,
        PropertyGroup,
        AddonPreferences,
        )
from bpy.props import (
        BoolProperty,
        EnumProperty,
        FloatProperty,
        IntProperty,
        PointerProperty,
        StringProperty,
        )

# ########################################
# ##### General functions ################
# ########################################

# used by all tools to improve speed on reruns Unlink
looptools_cache = {}

# force a full recalculation next time
def cache_delete(tool):
    if tool in looptools_cache:
        del looptools_cache[tool]


# check cache for stored information
def cache_read(tool, object, bm, input_method, boundaries):
    # current tool not cached yet
    if tool not in looptools_cache:
        return(False, False, False, False, False)
    # check if selected object didn't change
    if object.name != looptools_cache[tool]["object"]:
        return(False, False, False, False, False)
    # check if input didn't change
    if input_method != looptools_cache[tool]["input_method"]:
        return(False, False, False, False, False)
    if boundaries != looptools_cache[tool]["boundaries"]:
        return(False, False, False, False, False)
    modifiers = [mod.name for mod in object.modifiers if mod.show_viewport and
                 mod.type == 'MIRROR']
    if modifiers != looptools_cache[tool]["modifiers"]:
        return(False, False, False, False, False)
    input = [v.index for v in bm.verts if v.select and not v.hide]
    if input != looptools_cache[tool]["input"]:
        return(False, False, False, False, False)
    # reading values
    single_loops = looptools_cache[tool]["single_loops"]
    loops = looptools_cache[tool]["loops"]
    derived = looptools_cache[tool]["derived"]
    mapping = looptools_cache[tool]["mapping"]

    return(True, single_loops, loops, derived, mapping)


# store information in the cache
def cache_write(tool, object, bm, input_method, boundaries, single_loops,
loops, derived, mapping):
    # clear cache of current tool
    if tool in looptools_cache:
        del looptools_cache[tool]
    # prepare values to be saved to cache
    input = [v.index for v in bm.verts if v.select and not v.hide]
    modifiers = [mod.name for mod in object.modifiers if mod.show_viewport
    and mod.type == 'MIRROR']
    # update cache
    looptools_cache[tool] = {
        "input": input, "object": object.name,
        "input_method": input_method, "boundaries": boundaries,
        "single_loops": single_loops, "loops": loops,
        "derived": derived, "mapping": mapping, "modifiers": modifiers}


# calculates natural cubic splines through all given knots
def calculate_cubic_splines(bm_mod, tknots, knots):
    # hack for circular loops
    if knots[0] == knots[-1] and len(knots) > 1:
        circular = True
        k_new1 = []
        for k in range(-1, -5, -1):
            if k - 1 < -len(knots):
                k += len(knots)
            k_new1.append(knots[k - 1])
        k_new2 = []
        for k in range(4):
            if k + 1 > len(knots) - 1:
                k -= len(knots)
            k_new2.append(knots[k + 1])
        for k in k_new1:
            knots.insert(0, k)
        for k in k_new2:
            knots.append(k)
        t_new1 = []
        total1 = 0
        for t in range(-1, -5, -1):
            if t - 1 < -len(tknots):
                t += len(tknots)
            total1 += tknots[t] - tknots[t - 1]
            t_new1.append(tknots[0] - total1)
        t_new2 = []
        total2 = 0
        for t in range(4):
            if t + 1 > len(tknots) - 1:
                t -= len(tknots)
            total2 += tknots[t + 1] - tknots[t]
            t_new2.append(tknots[-1] + total2)
        for t in t_new1:
            tknots.insert(0, t)
        for t in t_new2:
            tknots.append(t)
    else:
        circular = False
    # end of hack

    n = len(knots)
    if n < 2:
        return False
    x = tknots[:]
    locs = [bm_mod.verts[k].co[:] for k in knots]
    result = []
    for j in range(3):
        a = []
        for i in locs:
            a.append(i[j])
        h = []
        for i in range(n - 1):
            if x[i + 1] - x[i] == 0:
                h.append(1e-8)
            else:
                h.append(x[i + 1] - x[i])
        q = [False]
        for i in range(1, n - 1):
            q.append(3 / h[i] * (a[i + 1] - a[i]) - 3 / h[i - 1] * (a[i] - a[i - 1]))
        l = [1.0]
        u = [0.0]
        z = [0.0]
        for i in range(1, n - 1):
            l.append(2 * (x[i + 1] - x[i - 1]) - h[i - 1] * u[i - 1])
            if l[i] == 0:
                l[i] = 1e-8
            u.append(h[i] / l[i])
            z.append((q[i] - h[i - 1] * z[i - 1]) / l[i])
        l.append(1.0)
        z.append(0.0)
        b = [False for i in range(n - 1)]
        c = [False for i in range(n)]
        d = [False for i in range(n - 1)]
        c[n - 1] = 0.0
        for i in range(n - 2, -1, -1):
            c[i] = z[i] - u[i] * c[i + 1]
            b[i] = (a[i + 1] - a[i]) / h[i] - h[i] * (c[i + 1] + 2 * c[i]) / 3
            d[i] = (c[i + 1] - c[i]) / (3 * h[i])
        for i in range(n - 1):
            result.append([a[i], b[i], c[i], d[i], x[i]])
    splines = []
    for i in range(len(knots) - 1):
        splines.append([result[i], result[i + n - 1], result[i + (n - 1) * 2]])
    if circular:  # cleaning up after hack
        knots = knots[4:-4]
        tknots = tknots[4:-4]

    return(splines)


# calculates linear splines through all given knots
def calculate_linear_splines(bm_mod, tknots, knots):
    splines = []
    for i in range(len(knots) - 1):
        a = bm_mod.verts[knots[i]].co
        b = bm_mod.verts[knots[i + 1]].co
        d = b - a
        t = tknots[i]
        u = tknots[i + 1] - t
        splines.append([a, d, t, u])  # [locStart, locDif, tStart, tDif]

    return(splines)


# calculate a best-fit plane to the given vertices
def calculate_plane(bm_mod, loop, method="best_fit", object=False):
    # getting the vertex locations
    locs = [bm_mod.verts[v].co.copy() for v in loop[0]]

    # calculating the center of masss
    com = mathutils.Vector()
    for loc in locs:
        com += loc
    com /= len(locs)
    x, y, z = com

    if method == 'best_fit':
        # creating the covariance matrix
        mat = mathutils.Matrix(((0.0, 0.0, 0.0),
                                (0.0, 0.0, 0.0),
                                (0.0, 0.0, 0.0),
                                ))
        for loc in locs:
            mat[0][0] += (loc[0] - x) ** 2
            mat[1][0] += (loc[0] - x) * (loc[1] - y)
            mat[2][0] += (loc[0] - x) * (loc[2] - z)
            mat[0][1] += (loc[1] - y) * (loc[0] - x)
            mat[1][1] += (loc[1] - y) ** 2
            mat[2][1] += (loc[1] - y) * (loc[2] - z)
            mat[0][2] += (loc[2] - z) * (loc[0] - x)
            mat[1][2] += (loc[2] - z) * (loc[1] - y)
            mat[2][2] += (loc[2] - z) ** 2

        # calculating the normal to the plane
        normal = False
        try:
            mat = matrix_invert(mat)
        except:
            ax = 2
            if math.fabs(sum(mat[0])) < math.fabs(sum(mat[1])):
                if math.fabs(sum(mat[0])) < math.fabs(sum(mat[2])):
                    ax = 0
            elif math.fabs(sum(mat[1])) < math.fabs(sum(mat[2])):
                ax = 1
            if ax == 0:
                normal = mathutils.Vector((1.0, 0.0, 0.0))
            elif ax == 1:
                normal = mathutils.Vector((0.0, 1.0, 0.0))
            else:
                normal = mathutils.Vector((0.0, 0.0, 1.0))
        if not normal:
            # warning! this is different from .normalize()
            itermax = 500
            vec2 = mathutils.Vector((1.0, 1.0, 1.0))
            for i in range(itermax):
                vec = vec2
                vec2 = mat @ vec
                # Calculate length with double precision to avoid problems with `inf`
                vec2_length = math.sqrt(vec2[0] ** 2 + vec2[1] ** 2 + vec2[2] ** 2)
                if vec2_length != 0:
                    vec2 /= vec2_length
                if vec2 == vec:
                    break
            if vec2.length == 0:
                vec2 = mathutils.Vector((1.0, 1.0, 1.0))
            normal = vec2

    elif method == 'normal':
        # averaging the vertex normals
        v_normals = [bm_mod.verts[v].normal for v in loop[0]]
        normal = mathutils.Vector()
        for v_normal in v_normals:
            normal += v_normal
        normal /= len(v_normals)
        normal.normalize()

    elif method == 'view':
        # calculate view normal
        rotation = bpy.context.space_data.region_3d.view_matrix.to_3x3().\
            inverted()
        normal = rotation @ mathutils.Vector((0.0, 0.0, 1.0))
        if object:
            normal = object.matrix_world.inverted().to_euler().to_matrix() @ \
                     normal

    return(com, normal)


# calculate splines based on given interpolation method (controller function)
def calculate_splines(interpolation, bm_mod, tknots, knots):
    if interpolation == 'cubic':
        splines = calculate_cubic_splines(bm_mod, tknots, knots[:])
    else:  # interpolations == 'linear'
        splines = calculate_linear_splines(bm_mod, tknots, knots[:])

    return(splines)


# check loops and only return valid ones
def check_loops(loops, mapping, bm_mod):
    valid_loops = []
    for loop, circular in loops:
        # loop needs to have at least 3 vertices
        if len(loop) < 3:
            continue
        # loop needs at least 1 vertex in the original, non-mirrored mesh
        if mapping:
            all_virtual = True
            for vert in loop:
                if mapping[vert] > -1:
                    all_virtual = False
                    break
            if all_virtual:
                continue
        # vertices can not all be at the same location
        stacked = True
        for i in range(len(loop) - 1):
            if (bm_mod.verts[loop[i]].co - bm_mod.verts[loop[i + 1]].co).length > 1e-6:
                stacked = False
                break
        if stacked:
            continue
        # passed all tests, loop is valid
        valid_loops.append([loop, circular])

    return(valid_loops)


# input: bmesh, output: dict with the edge-key as key and face-index as value
def dict_edge_faces(bm):
    edge_faces = dict([[edgekey(edge), []] for edge in bm.edges if not edge.hide])
    for face in bm.faces:
        if face.hide:
            continue
        for key in face_edgekeys(face):
            edge_faces[key].append(face.index)

    return(edge_faces)


# input: bmesh (edge-faces optional), output: dict with face-face connections
def dict_face_faces(bm, edge_faces=False):
    if not edge_faces:
        edge_faces = dict_edge_faces(bm)

    connected_faces = dict([[face.index, []] for face in bm.faces if not face.hide])
    for face in bm.faces:
        if face.hide:
            continue
        for edge_key in face_edgekeys(face):
            for connected_face in edge_faces[edge_key]:
                if connected_face == face.index:
                    continue
                connected_faces[face.index].append(connected_face)

    return(connected_faces)


# input: bmesh, output: dict with the vert index as key and edge-keys as value
def dict_vert_edges(bm):
    vert_edges = dict([[v.index, []] for v in bm.verts if not v.hide])
    for edge in bm.edges:
        if edge.hide:
            continue
        ek = edgekey(edge)
        for vert in ek:
            vert_edges[vert].append(ek)

    return(vert_edges)


# input: bmesh, output: dict with the vert index as key and face index as value
def dict_vert_faces(bm):
    vert_faces = dict([[v.index, []] for v in bm.verts if not v.hide])
    for face in bm.faces:
        if not face.hide:
            for vert in face.verts:
                vert_faces[vert.index].append(face.index)

    return(vert_faces)


# input: list of edge-keys, output: dictionary with vertex-vertex connections
def dict_vert_verts(edge_keys):
    # create connection data
    vert_verts = {}
    for ek in edge_keys:
        for i in range(2):
            if ek[i] in vert_verts:
                vert_verts[ek[i]].append(ek[1 - i])
            else:
                vert_verts[ek[i]] = [ek[1 - i]]

    return(vert_verts)


# return the edgekey ([v1.index, v2.index]) of a bmesh edge
def edgekey(edge):
    return(tuple(sorted([edge.verts[0].index, edge.verts[1].index])))


# returns the edgekeys of a bmesh face
def face_edgekeys(face):
    return([tuple(sorted([edge.verts[0].index, edge.verts[1].index])) for edge in face.edges])


# calculate input loops
def get_connected_input(object, bm, not_use_mirror, input):
    # get mesh with modifiers applied
    derived, bm_mod = get_derived_bmesh(object, bm, not_use_mirror)

    # calculate selected loops
    edge_keys = [edgekey(edge) for edge in bm_mod.edges if edge.select and not edge.hide]
    loops = get_connected_selections(edge_keys)

    # if only selected loops are needed, we're done
    if input == 'selected':
        return(derived, bm_mod, loops)
    # elif input == 'all':
    loops = get_parallel_loops(bm_mod, loops)

    return(derived, bm_mod, loops)


# sorts all edge-keys into a list of loops
def get_connected_selections(edge_keys):
    # create connection data
    vert_verts = dict_vert_verts(edge_keys)

    # find loops consisting of connected selected edges
    loops = []
    while len(vert_verts) > 0:
        loop = [iter(vert_verts.keys()).__next__()]
        growing = True
        flipped = False

        # extend loop
        while growing:
            # no more connection data for current vertex
            if loop[-1] not in vert_verts:
                if not flipped:
                    loop.reverse()
                    flipped = True
                else:
                    growing = False
            else:
                extended = False
                for i, next_vert in enumerate(vert_verts[loop[-1]]):
                    if next_vert not in loop:
                        vert_verts[loop[-1]].pop(i)
                        if len(vert_verts[loop[-1]]) == 0:
                            del vert_verts[loop[-1]]
                        # remove connection both ways
                        if next_vert in vert_verts:
                            if len(vert_verts[next_vert]) == 1:
                                del vert_verts[next_vert]
                            else:
                                vert_verts[next_vert].remove(loop[-1])
                        loop.append(next_vert)
                        extended = True
                        break
                if not extended:
                    # found one end of the loop, continue with next
                    if not flipped:
                        loop.reverse()
                        flipped = True
                    # found both ends of the loop, stop growing
                    else:
                        growing = False

        # check if loop is circular
        if loop[0] in vert_verts:
            if loop[-1] in vert_verts[loop[0]]:
                # is circular
                if len(vert_verts[loop[0]]) == 1:
                    del vert_verts[loop[0]]
                else:
                    vert_verts[loop[0]].remove(loop[-1])
                if len(vert_verts[loop[-1]]) == 1:
                    del vert_verts[loop[-1]]
                else:
                    vert_verts[loop[-1]].remove(loop[0])
                loop = [loop, True]
            else:
                # not circular
                loop = [loop, False]
        else:
            # not circular
            loop = [loop, False]

        loops.append(loop)

    return(loops)


# get the derived mesh data, if there is a mirror modifier
def get_derived_bmesh(object, bm, not_use_mirror):
    # check for mirror modifiers
    if 'MIRROR' in [mod.type for mod in object.modifiers if mod.show_viewport]:
        derived = True
        # disable other modifiers
        show_viewport = [mod.name for mod in object.modifiers if mod.show_viewport]
        merge = []
        for mod in object.modifiers:
            if mod.type != 'MIRROR':
                mod.show_viewport = False
            #leave the merge points untouched
            if mod.type == 'MIRROR':
                merge.append(mod.use_mirror_merge)
                if not_use_mirror:
                    mod.use_mirror_merge = False
        # get derived mesh
        bm_mod = bmesh.new()
        depsgraph = bpy.context.evaluated_depsgraph_get()
        object_eval = object.evaluated_get(depsgraph)
        mesh_mod = object_eval.to_mesh()
        bm_mod.from_mesh(mesh_mod)
        object_eval.to_mesh_clear()
        # re-enable other modifiers
        for mod_name in show_viewport:
            object.modifiers[mod_name].show_viewport = True
        merge.reverse()
        for mod in object.modifiers:
            if mod.type == 'MIRROR':
                mod.use_mirror_merge = merge.pop()
    # no mirror modifiers, so no derived mesh necessary
    else:
        derived = False
        bm_mod = bm

    bm_mod.verts.ensure_lookup_table()
    bm_mod.edges.ensure_lookup_table()
    bm_mod.faces.ensure_lookup_table()

    return(derived, bm_mod)


# return a mapping of derived indices to indices
def get_mapping(derived, bm, bm_mod, single_vertices, full_search, loops):
    if not derived:
        return(False)

    if full_search:
        verts = [v for v in bm.verts if not v.hide]
    else:
        verts = [v for v in bm.verts if v.select and not v.hide]

    # non-selected vertices around single vertices also need to be mapped
    if single_vertices:
        mapping = dict([[vert, -1] for vert in single_vertices])
        verts_mod = [bm_mod.verts[vert] for vert in single_vertices]
        for v in verts:
            for v_mod in verts_mod:
                if (v.co - v_mod.co).length < 1e-6:
                    mapping[v_mod.index] = v.index
                    break
        real_singles = [v_real for v_real in mapping.values() if v_real > -1]

        verts_indices = [vert.index for vert in verts]
        for face in [face for face in bm.faces if not face.select and not face.hide]:
            for vert in face.verts:
                if vert.index in real_singles:
                    for v in face.verts:
                        if v.index not in verts_indices:
                            if v not in verts:
                                verts.append(v)
                    break

    # create mapping of derived indices to indices
    mapping = dict([[vert, -1] for loop in loops for vert in loop[0]])
    if single_vertices:
        for single in single_vertices:
            mapping[single] = -1
    verts_mod = [bm_mod.verts[i] for i in mapping.keys()]
    for v in verts:
        for v_mod in verts_mod:
            if (v.co - v_mod.co).length < 1e-6:
                mapping[v_mod.index] = v.index
                verts_mod.remove(v_mod)
                break

    return(mapping)


# calculate the determinant of a matrix
def matrix_determinant(m):
    determinant = m[0][0] * m[1][1] * m[2][2] + m[0][1] * m[1][2] * m[2][0] \
        + m[0][2] * m[1][0] * m[2][1] - m[0][2] * m[1][1] * m[2][0] \
        - m[0][1] * m[1][0] * m[2][2] - m[0][0] * m[1][2] * m[2][1]

    return(determinant)


# custom matrix inversion, to provide higher precision than the built-in one
def matrix_invert(m):
    r = mathutils.Matrix((
        (m[1][1] * m[2][2] - m[1][2] * m[2][1], m[0][2] * m[2][1] - m[0][1] * m[2][2],
         m[0][1] * m[1][2] - m[0][2] * m[1][1]),
        (m[1][2] * m[2][0] - m[1][0] * m[2][2], m[0][0] * m[2][2] - m[0][2] * m[2][0],
         m[0][2] * m[1][0] - m[0][0] * m[1][2]),
        (m[1][0] * m[2][1] - m[1][1] * m[2][0], m[0][1] * m[2][0] - m[0][0] * m[2][1],
         m[0][0] * m[1][1] - m[0][1] * m[1][0])))

    return (r * (1 / matrix_determinant(m)))


# returns a list of all loops parallel to the input, input included
def get_parallel_loops(bm_mod, loops):
    # get required dictionaries
    edge_faces = dict_edge_faces(bm_mod)
    connected_faces = dict_face_faces(bm_mod, edge_faces)
    # turn vertex loops into edge loops
    edgeloops = []
    for loop in loops:
        edgeloop = [[sorted([loop[0][i], loop[0][i + 1]]) for i in
                    range(len(loop[0]) - 1)], loop[1]]
        if loop[1]:  # circular
            edgeloop[0].append(sorted([loop[0][-1], loop[0][0]]))
        edgeloops.append(edgeloop[:])
    # variables to keep track while iterating
    all_edgeloops = []
    has_branches = False

    for loop in edgeloops:
        # initialise with original loop
        all_edgeloops.append(loop[0])
        newloops = [loop[0]]
        verts_used = []
        for edge in loop[0]:
            if edge[0] not in verts_used:
                verts_used.append(edge[0])
            if edge[1] not in verts_used:
                verts_used.append(edge[1])

        # find parallel loops
        while len(newloops) > 0:
            side_a = []
            side_b = []
            for i in newloops[-1]:
                i = tuple(i)
                forbidden_side = False
                if i not in edge_faces:
                    # weird input with branches
                    has_branches = True
                    break
                for face in edge_faces[i]:
                    if len(side_a) == 0 and forbidden_side != "a":
                        side_a.append(face)
                        if forbidden_side:
                            break
                        forbidden_side = "a"
                        continue
                    elif side_a[-1] in connected_faces[face] and \
                    forbidden_side != "a":
                        side_a.append(face)
                        if forbidden_side:
                            break
                        forbidden_side = "a"
                        continue
                    if len(side_b) == 0 and forbidden_side != "b":
                        side_b.append(face)
                        if forbidden_side:
                            break
                        forbidden_side = "b"
                        continue
                    elif side_b[-1] in connected_faces[face] and \
                    forbidden_side != "b":
                        side_b.append(face)
                        if forbidden_side:
                            break
                        forbidden_side = "b"
                        continue

            if has_branches:
                # weird input with branches
                break

            newloops.pop(-1)
            sides = []
            if side_a:
                sides.append(side_a)
            if side_b:
                sides.append(side_b)

            for side in sides:
                extraloop = []
                for fi in side:
                    for key in face_edgekeys(bm_mod.faces[fi]):
                        if key[0] not in verts_used and key[1] not in \
                        verts_used:
                            extraloop.append(key)
                            break
                if extraloop:
                    for key in extraloop:
                        for new_vert in key:
                            if new_vert not in verts_used:
                                verts_used.append(new_vert)
                    newloops.append(extraloop)
                    all_edgeloops.append(extraloop)

    # input contains branches, only return selected loop
    if has_branches:
        return(loops)

    # change edgeloops into normal loops
    loops = []
    for edgeloop in all_edgeloops:
        loop = []
        # grow loop by comparing vertices between consecutive edge-keys
        for i in range(len(edgeloop) - 1):
            for vert in range(2):
                if edgeloop[i][vert] in edgeloop[i + 1]:
                    loop.append(edgeloop[i][vert])
                    break
        if loop:
            # add starting vertex
            for vert in range(2):
                if edgeloop[0][vert] != loop[0]:
                    loop = [edgeloop[0][vert]] + loop
                    break
            # add ending vertex
            for vert in range(2):
                if edgeloop[-1][vert] != loop[-1]:
                    loop.append(edgeloop[-1][vert])
                    break
            # check if loop is circular
            if loop[0] == loop[-1]:
                circular = True
                loop = loop[:-1]
            else:
                circular = False
        loops.append([loop, circular])

    return(loops)


# gather initial data
def initialise():
    object = bpy.context.active_object
    if 'MIRROR' in [mod.type for mod in object.modifiers if mod.show_viewport]:
        # ensure that selection is synced for the derived mesh
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(object.data)

    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    return(object, bm)


# move the vertices to their new locations
def move_verts(object, bm, mapping, move, lock, influence):
    if lock:
        lock_x, lock_y, lock_z = lock
        orient_slot = bpy.context.scene.transform_orientation_slots[0]
        custom = orient_slot.custom_orientation
        if custom:
            mat = custom.matrix.to_4x4().inverted() @ object.matrix_world.copy()
        elif orient_slot.type == 'LOCAL':
            mat = mathutils.Matrix.Identity(4)
        elif orient_slot.type == 'VIEW':
            mat = bpy.context.region_data.view_matrix.copy() @ \
                object.matrix_world.copy()
        else:  # orientation == 'GLOBAL'
            mat = object.matrix_world.copy()
        mat_inv = mat.inverted()

    # get all mirror vectors
    mirror_Vectors = []
    if object.data.use_mirror_x:
        mirror_Vectors.append(mathutils.Vector((-1, 1, 1)))
    if object.data.use_mirror_y:
        mirror_Vectors.append(mathutils.Vector((1, -1, 1)))
    if object.data.use_mirror_x and object.data.use_mirror_y:
        mirror_Vectors.append(mathutils.Vector((-1, -1, 1)))
    z_mirror_Vectors = []
    if object.data.use_mirror_z:
        for v in mirror_Vectors:
            z_mirror_Vectors.append(mathutils.Vector((1, 1, -1)) * v)
        mirror_Vectors.extend(z_mirror_Vectors)
        mirror_Vectors.append(mathutils.Vector((1, 1, -1)))

    for loop in move:
        for index, loc in loop:
            if mapping:
                if mapping[index] == -1:
                    continue
                else:
                    index = mapping[index]
            if lock:
                delta = (loc - bm.verts[index].co) @ mat_inv
                if lock_x:
                    delta[0] = 0
                if lock_y:
                    delta[1] = 0
                if lock_z:
                    delta[2] = 0
                delta = delta @ mat
                loc = bm.verts[index].co + delta
            if influence < 0:
                new_loc = loc
            else:
                new_loc = loc * (influence / 100) + \
                                 bm.verts[index].co * ((100 - influence) / 100)

            for mirror_Vector in mirror_Vectors:
                for vert in bm.verts:
                    if vert.co == mirror_Vector * bm.verts[index].co:
                        vert.co = mirror_Vector * new_loc

            bm.verts[index].co = new_loc

    bm.normal_update()
    object.data.update()

    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()


# load custom tool settings
def settings_load(self):
    lt = bpy.context.window_manager.looptools
    tool = self.name.split()[0].lower()
    keys = self.as_keywords().keys()
    for key in keys:
        setattr(self, key, getattr(lt, tool + "_" + key))


# store custom tool settings
def settings_write(self):
    lt = bpy.context.window_manager.looptools
    tool = self.name.split()[0].lower()
    keys = self.as_keywords().keys()
    for key in keys:
        setattr(lt, tool + "_" + key, getattr(self, key))


# clean up and set settings back to original state
def terminate():
    # update editmesh cached data
    obj = bpy.context.active_object
    if obj.mode == 'EDIT':
        bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=True)


# ########################################
# ##### Circle functions #################
# ########################################

# convert 3d coordinates to 2d coordinates on plane
def circle_3d_to_2d(bm_mod, loop, com, normal):
    # project vertices onto the plane
    verts = [bm_mod.verts[v] for v in loop[0]]
    verts_projected = [[v.co - (v.co - com).dot(normal) * normal, v.index]
                       for v in verts]

    # calculate two vectors (p and q) along the plane
    m = mathutils.Vector((normal[0] + 1.0, normal[1], normal[2]))
    p = m - (m.dot(normal) * normal)
    if p.dot(p) < 1e-6:
        m = mathutils.Vector((normal[0], normal[1] + 1.0, normal[2]))
        p = m - (m.dot(normal) * normal)
    q = p.cross(normal)

    # change to 2d coordinates using perpendicular projection
    locs_2d = []
    for loc, vert in verts_projected:
        vloc = loc - com
        x = p.dot(vloc) / p.dot(p)
        y = q.dot(vloc) / q.dot(q)
        locs_2d.append([x, y, vert])

    return(locs_2d, p, q)


# calculate a best-fit circle to the 2d locations on the plane
def circle_calculate_best_fit(locs_2d):
    # initial guess
    x0 = 0.0
    y0 = 0.0
    r = 1.0

    # calculate center and radius (non-linear least squares solution)
    for iter in range(500):
        jmat = []
        k = []
        for v in locs_2d:
            d = (v[0] ** 2 - 2.0 * x0 * v[0] + v[1] ** 2 - 2.0 * y0 * v[1] + x0 ** 2 + y0 ** 2) ** 0.5
            jmat.append([(x0 - v[0]) / d, (y0 - v[1]) / d, -1.0])
            k.append(-(((v[0] - x0) ** 2 + (v[1] - y0) ** 2) ** 0.5 - r))
        jmat2 = mathutils.Matrix(((0.0, 0.0, 0.0),
                                  (0.0, 0.0, 0.0),
                                  (0.0, 0.0, 0.0),
                                  ))
        k2 = mathutils.Vector((0.0, 0.0, 0.0))
        for i in range(len(jmat)):
            k2 += mathutils.Vector(jmat[i]) * k[i]
            jmat2[0][0] += jmat[i][0] ** 2
            jmat2[1][0] += jmat[i][0] * jmat[i][1]
            jmat2[2][0] += jmat[i][0] * jmat[i][2]
            jmat2[1][1] += jmat[i][1] ** 2
            jmat2[2][1] += jmat[i][1] * jmat[i][2]
            jmat2[2][2] += jmat[i][2] ** 2
        jmat2[0][1] = jmat2[1][0]
        jmat2[0][2] = jmat2[2][0]
        jmat2[1][2] = jmat2[2][1]
        try:
            jmat2.invert()
        except:
            pass
        dx0, dy0, dr = jmat2 @ k2
        x0 += dx0
        y0 += dy0
        r += dr
        # stop iterating if we're close enough to optimal solution
        if abs(dx0) < 1e-6 and abs(dy0) < 1e-6 and abs(dr) < 1e-6:
            break

    # return center of circle and radius
    return(x0, y0, r)


# calculate circle so no vertices have to be moved away from the center
def circle_calculate_min_fit(locs_2d):
    # center of circle
    x0 = (min([i[0] for i in locs_2d]) + max([i[0] for i in locs_2d])) / 2.0
    y0 = (min([i[1] for i in locs_2d]) + max([i[1] for i in locs_2d])) / 2.0
    center = mathutils.Vector([x0, y0])
    # radius of circle
    r = min([(mathutils.Vector([i[0], i[1]]) - center).length for i in locs_2d])

    # return center of circle and radius
    return(x0, y0, r)


# calculate the new locations of the vertices that need to be moved
def circle_calculate_verts(flatten, bm_mod, locs_2d, com, p, q, normal):
    # changing 2d coordinates back to 3d coordinates
    locs_3d = []
    for loc in locs_2d:
        locs_3d.append([loc[2], loc[0] * p + loc[1] * q + com])

    if flatten:  # flat circle
        return(locs_3d)

    else:  # project the locations on the existing mesh
        vert_edges = dict_vert_edges(bm_mod)
        vert_faces = dict_vert_faces(bm_mod)
        faces = [f for f in bm_mod.faces if not f.hide]
        rays = [normal, -normal]
        new_locs = []
        for loc in locs_3d:
            projection = False
            if bm_mod.verts[loc[0]].co == loc[1]:  # vertex hasn't moved
                projection = loc[1]
            else:
                dif = normal.angle(loc[1] - bm_mod.verts[loc[0]].co)
                if -1e-6 < dif < 1e-6 or math.pi - 1e-6 < dif < math.pi + 1e-6:
                    # original location is already along projection normal
                    projection = bm_mod.verts[loc[0]].co
                else:
                    # quick search through adjacent faces
                    for face in vert_faces[loc[0]]:
                        verts = [v.co for v in bm_mod.faces[face].verts]
                        if len(verts) == 3:  # triangle
                            v1, v2, v3 = verts
                            v4 = False
                        else:  # assume quad
                            v1, v2, v3, v4 = verts[:4]
                        for ray in rays:
                            intersect = mathutils.geometry.\
                            intersect_ray_tri(v1, v2, v3, ray, loc[1])
                            if intersect:
                                projection = intersect
                                break
                            elif v4:
                                intersect = mathutils.geometry.\
                                intersect_ray_tri(v1, v3, v4, ray, loc[1])
                                if intersect:
                                    projection = intersect
                                    break
                        if projection:
                            break
            if not projection:
                # check if projection is on adjacent edges
                for edgekey in vert_edges[loc[0]]:
                    line1 = bm_mod.verts[edgekey[0]].co
                    line2 = bm_mod.verts[edgekey[1]].co
                    intersect, dist = mathutils.geometry.intersect_point_line(
                        loc[1], line1, line2
                        )
                    if 1e-6 < dist < 1 - 1e-6:
                        projection = intersect
                        break
            if not projection:
                # full search through the entire mesh
                hits = []
                for face in faces:
                    verts = [v.co for v in face.verts]
                    if len(verts) == 3:  # triangle
                        v1, v2, v3 = verts
                        v4 = False
                    else:  # assume quad
                        v1, v2, v3, v4 = verts[:4]
                    for ray in rays:
                        intersect = mathutils.geometry.intersect_ray_tri(
                            v1, v2, v3, ray, loc[1]
                            )
                        if intersect:
                            hits.append([(loc[1] - intersect).length,
                                intersect])
                            break
                        elif v4:
                            intersect = mathutils.geometry.intersect_ray_tri(
                                v1, v3, v4, ray, loc[1]
                                )
                            if intersect:
                                hits.append([(loc[1] - intersect).length,
                                    intersect])
                                break
                if len(hits) >= 1:
                    # if more than 1 hit with mesh, closest hit is new loc
                    hits.sort()
                    projection = hits[0][1]
            if not projection:
                # nothing to project on, remain at flat location
                projection = loc[1]
            new_locs.append([loc[0], projection])

        # return new positions of projected circle
        return(new_locs)


# check loops and only return valid ones
def circle_check_loops(single_loops, loops, mapping, bm_mod):
    valid_single_loops = {}
    valid_loops = []
    for i, [loop, circular] in enumerate(loops):
        # loop needs to have at least 3 vertices
        if len(loop) < 3:
            continue
        # loop needs at least 1 vertex in the original, non-mirrored mesh
        if mapping:
            all_virtual = True
            for vert in loop:
                if mapping[vert] > -1:
                    all_virtual = False
                    break
            if all_virtual:
                continue
        # loop has to be non-collinear
        collinear = True
        loc0 = mathutils.Vector(bm_mod.verts[loop[0]].co[:])
        loc1 = mathutils.Vector(bm_mod.verts[loop[1]].co[:])
        for v in loop[2:]:
            locn = mathutils.Vector(bm_mod.verts[v].co[:])
            if loc0 == loc1 or loc1 == locn:
                loc0 = loc1
                loc1 = locn
                continue
            d1 = loc1 - loc0
            d2 = locn - loc1
            if -1e-6 < d1.angle(d2, 0) < 1e-6:
                loc0 = loc1
                loc1 = locn
                continue
            collinear = False
            break
        if collinear:
            continue
        # passed all tests, loop is valid
        valid_loops.append([loop, circular])
        valid_single_loops[len(valid_loops) - 1] = single_loops[i]

    return(valid_single_loops, valid_loops)


# calculate the location of single input vertices that need to be flattened
def circle_flatten_singles(bm_mod, com, p, q, normal, single_loop):
    new_locs = []
    for vert in single_loop:
        loc = mathutils.Vector(bm_mod.verts[vert].co[:])
        new_locs.append([vert, loc - (loc - com).dot(normal) * normal])

    return(new_locs)


# calculate input loops
def circle_get_input(object, bm):
    # get mesh with modifiers applied
    derived, bm_mod = get_derived_bmesh(object, bm, False)

    # create list of edge-keys based on selection state
    faces = False
    for face in bm.faces:
        if face.select and not face.hide:
            faces = True
            break
    if faces:
        # get selected, non-hidden , non-internal edge-keys
        eks_selected = [
            key for keys in [face_edgekeys(face) for face in
            bm_mod.faces if face.select and not face.hide] for key in keys
            ]
        edge_count = {}
        for ek in eks_selected:
            if ek in edge_count:
                edge_count[ek] += 1
            else:
                edge_count[ek] = 1
        edge_keys = [
            edgekey(edge) for edge in bm_mod.edges if edge.select and
            not edge.hide and edge_count.get(edgekey(edge), 1) == 1
            ]
    else:
        # no faces, so no internal edges either
        edge_keys = [
            edgekey(edge) for edge in bm_mod.edges if edge.select and not edge.hide
            ]

    # add edge-keys around single vertices
    verts_connected = dict(
        [[vert, 1] for edge in [edge for edge in
        bm_mod.edges if edge.select and not edge.hide] for vert in
        edgekey(edge)]
        )
    single_vertices = [
        vert.index for vert in bm_mod.verts if
        vert.select and not vert.hide and
        not verts_connected.get(vert.index, False)
        ]

    if single_vertices and len(bm.faces) > 0:
        vert_to_single = dict(
            [[v.index, []] for v in bm_mod.verts if not v.hide]
            )
        for face in [face for face in bm_mod.faces if not face.select and not face.hide]:
            for vert in face.verts:
                vert = vert.index
                if vert in single_vertices:
                    for ek in face_edgekeys(face):
                        if vert not in ek:
                            edge_keys.append(ek)
                            if vert not in vert_to_single[ek[0]]:
                                vert_to_single[ek[0]].append(vert)
                            if vert not in vert_to_single[ek[1]]:
                                vert_to_single[ek[1]].append(vert)
                    break

    # sort edge-keys into loops
    loops = get_connected_selections(edge_keys)

    # find out to which loops the single vertices belong
    single_loops = dict([[i, []] for i in range(len(loops))])
    if single_vertices and len(bm.faces) > 0:
        for i, [loop, circular] in enumerate(loops):
            for vert in loop:
                if vert_to_single[vert]:
                    for single in vert_to_single[vert]:
                        if single not in single_loops[i]:
                            single_loops[i].append(single)

    return(derived, bm_mod, single_vertices, single_loops, loops)


# recalculate positions based on the influence of the circle shape
def circle_influence_locs(locs_2d, new_locs_2d, influence):
    for i in range(len(locs_2d)):
        oldx, oldy, j = locs_2d[i]
        newx, newy, k = new_locs_2d[i]
        altx = newx * (influence / 100) + oldx * ((100 - influence) / 100)
        alty = newy * (influence / 100) + oldy * ((100 - influence) / 100)
        locs_2d[i] = [altx, alty, j]

    return(locs_2d)


# project 2d locations on circle, respecting distance relations between verts
def circle_project_non_regular(locs_2d, x0, y0, r, angle):
    for i in range(len(locs_2d)):
        x, y, j = locs_2d[i]
        loc = mathutils.Vector([x - x0, y - y0])
        mat_rot = mathutils.Matrix.Rotation(angle, 2, 'X')
        loc.rotate(mat_rot)
        loc.length = r
        locs_2d[i] = [loc[0], loc[1], j]

    return(locs_2d)


# project 2d locations on circle, with equal distance between all vertices
def circle_project_regular(locs_2d, x0, y0, r, angle):
    # find offset angle and circling direction
    x, y, i = locs_2d[0]
    loc = mathutils.Vector([x - x0, y - y0])
    loc.length = r
    offset_angle = loc.angle(mathutils.Vector([1.0, 0.0]), 0.0)
    loca = mathutils.Vector([x - x0, y - y0, 0.0])
    if loc[1] < -1e-6:
        offset_angle *= -1
    x, y, j = locs_2d[1]
    locb = mathutils.Vector([x - x0, y - y0, 0.0])
    if loca.cross(locb)[2] >= 0:
        ccw = 1
    else:
        ccw = -1
    # distribute vertices along the circle
    for i in range(len(locs_2d)):
        t = offset_angle + ccw * (i / len(locs_2d) * 2 * math.pi)
        x = math.cos(t + angle) * r
        y = math.sin(t + angle) * r
        locs_2d[i] = [x, y, locs_2d[i][2]]

    return(locs_2d)


# shift loop, so the first vertex is closest to the center
def circle_shift_loop(bm_mod, loop, com):
    verts, circular = loop
    distances = [
             [(bm_mod.verts[vert].co - com).length, i] for i, vert in enumerate(verts)
            ]
    distances.sort()
    shift = distances[0][1]
    loop = [verts[shift:] + verts[:shift], circular]

    return(loop)


# ########################################
# ##### Curve functions ##################
# ########################################

# create lists with knots and points, all correctly sorted
def curve_calculate_knots(loop, verts_selected):
    knots = [v for v in loop[0] if v in verts_selected]
    points = loop[0][:]
    # circular loop, potential for weird splines
    if loop[1]:
        offset = int(len(loop[0]) / 4)
        kpos = []
        for k in knots:
            kpos.append(loop[0].index(k))
        kdif = []
        for i in range(len(kpos) - 1):
            kdif.append(kpos[i + 1] - kpos[i])
        kdif.append(len(loop[0]) - kpos[-1] + kpos[0])
        kadd = []
        for k in kdif:
            if k > 2 * offset:
                kadd.append([kdif.index(k), True])
            # next 2 lines are optional, they insert
            # an extra control point in small gaps
            # elif k > offset:
            #   kadd.append([kdif.index(k), False])
        kins = []
        krot = False
        for k in kadd:  # extra knots to be added
            if k[1]:  # big gap (break circular spline)
                kpos = loop[0].index(knots[k[0]]) + offset
                if kpos > len(loop[0]) - 1:
                    kpos -= len(loop[0])
                kins.append([knots[k[0]], loop[0][kpos]])
                kpos2 = k[0] + 1
                if kpos2 > len(knots) - 1:
                    kpos2 -= len(knots)
                kpos2 = loop[0].index(knots[kpos2]) - offset
                if kpos2 < 0:
                    kpos2 += len(loop[0])
                kins.append([loop[0][kpos], loop[0][kpos2]])
                krot = loop[0][kpos2]
            else:  # small gap (keep circular spline)
                k1 = loop[0].index(knots[k[0]])
                k2 = k[0] + 1
                if k2 > len(knots) - 1:
                    k2 -= len(knots)
                k2 = loop[0].index(knots[k2])
                if k2 < k1:
                    dif = len(loop[0]) - 1 - k1 + k2
                else:
                    dif = k2 - k1
                kn = k1 + int(dif / 2)
                if kn > len(loop[0]) - 1:
                    kn -= len(loop[0])
                kins.append([loop[0][k1], loop[0][kn]])
        for j in kins:  # insert new knots
            knots.insert(knots.index(j[0]) + 1, j[1])
        if not krot:  # circular loop
            knots.append(knots[0])
            points = loop[0][loop[0].index(knots[0]):]
            points += loop[0][0:loop[0].index(knots[0]) + 1]
        else:  # non-circular loop (broken by script)
            krot = knots.index(krot)
            knots = knots[krot:] + knots[0:krot]
            if loop[0].index(knots[0]) > loop[0].index(knots[-1]):
                points = loop[0][loop[0].index(knots[0]):]
                points += loop[0][0:loop[0].index(knots[-1]) + 1]
            else:
                points = loop[0][loop[0].index(knots[0]):loop[0].index(knots[-1]) + 1]
    # non-circular loop, add first and last point as knots
    else:
        if loop[0][0] not in knots:
            knots.insert(0, loop[0][0])
        if loop[0][-1] not in knots:
            knots.append(loop[0][-1])

    return(knots, points)


# calculate relative positions compared to first knot
def curve_calculate_t(bm_mod, knots, points, pknots, regular, circular):
    tpoints = []
    loc_prev = False
    len_total = 0

    for p in points:
        if p in knots:
            loc = pknots[knots.index(p)]  # use projected knot location
        else:
            loc = mathutils.Vector(bm_mod.verts[p].co[:])
        if not loc_prev:
            loc_prev = loc
        len_total += (loc - loc_prev).length
        tpoints.append(len_total)
        loc_prev = loc
    tknots = []
    for p in points:
        if p in knots:
            tknots.append(tpoints[points.index(p)])
    if circular:
        tknots[-1] = tpoints[-1]

    # regular option
    if regular:
        tpoints_average = tpoints[-1] / (len(tpoints) - 1)
        for i in range(1, len(tpoints) - 1):
            tpoints[i] = i * tpoints_average
        for i in range(len(knots)):
            tknots[i] = tpoints[points.index(knots[i])]
        if circular:
            tknots[-1] = tpoints[-1]

    return(tknots, tpoints)


# change the location of non-selected points to their place on the spline
def curve_calculate_vertices(bm_mod, knots, tknots, points, tpoints, splines,
interpolation, restriction):
    newlocs = {}
    move = []

    for p in points:
        if p in knots:
            continue
        m = tpoints[points.index(p)]
        if m in tknots:
            n = tknots.index(m)
        else:
            t = tknots[:]
            t.append(m)
            t.sort()
            n = t.index(m) - 1
        if n > len(splines) - 1:
            n = len(splines) - 1
        elif n < 0:
            n = 0

        if interpolation == 'cubic':
            ax, bx, cx, dx, tx = splines[n][0]
            x = ax + bx * (m - tx) + cx * (m - tx) ** 2 + dx * (m - tx) ** 3
            ay, by, cy, dy, ty = splines[n][1]
            y = ay + by * (m - ty) + cy * (m - ty) ** 2 + dy * (m - ty) ** 3
            az, bz, cz, dz, tz = splines[n][2]
            z = az + bz * (m - tz) + cz * (m - tz) ** 2 + dz * (m - tz) ** 3
            newloc = mathutils.Vector([x, y, z])
        else:  # interpolation == 'linear'
            a, d, t, u = splines[n]
            newloc = ((m - t) / u) * d + a

        if restriction != 'none':  # vertex movement is restricted
            newlocs[p] = newloc
        else:  # set the vertex to its new location
            move.append([p, newloc])

    if restriction != 'none':  # vertex movement is restricted
        for p in points:
            if p in newlocs:
                newloc = newlocs[p]
            else:
                move.append([p, bm_mod.verts[p].co])
                continue
            oldloc = bm_mod.verts[p].co
            normal = bm_mod.verts[p].normal
            dloc = newloc - oldloc
            if dloc.length < 1e-6:
                move.append([p, newloc])
            elif restriction == 'extrude':  # only extrusions
                if dloc.angle(normal, 0) < 0.5 * math.pi + 1e-6:
                    move.append([p, newloc])
            else:  # restriction == 'indent' only indentations
                if dloc.angle(normal) > 0.5 * math.pi - 1e-6:
                    move.append([p, newloc])

    return(move)


# trim loops to part between first and last selected vertices (including)
def curve_cut_boundaries(bm_mod, loops):
    cut_loops = []
    for loop, circular in loops:
        if circular:
            selected = [bm_mod.verts[v].select for v in loop]
            first = selected.index(True)
            selected.reverse()
            last = -selected.index(True)
            if last == 0:
                if len(loop[first:]) < len(loop)/2:
                    cut_loops.append([loop[first:], False])
            else:
                if len(loop[first:last]) < len(loop)/2:
                    cut_loops.append([loop[first:last], False])
            continue
        selected = [bm_mod.verts[v].select for v in loop]
        first = selected.index(True)
        selected.reverse()
        last = -selected.index(True)
        if last == 0:
            cut_loops.append([loop[first:], circular])
        else:
            cut_loops.append([loop[first:last], circular])

    return(cut_loops)


# calculate input loops
def curve_get_input(object, bm, boundaries):
    # get mesh with modifiers applied
    derived, bm_mod = get_derived_bmesh(object, bm, False)

    # vertices that still need a loop to run through it
    verts_unsorted = [
        v.index for v in bm_mod.verts if v.select and not v.hide
        ]
    # necessary dictionaries
    vert_edges = dict_vert_edges(bm_mod)
    edge_faces = dict_edge_faces(bm_mod)
    correct_loops = []
    # find loops through each selected vertex
    while len(verts_unsorted) > 0:
        loops = curve_vertex_loops(bm_mod, verts_unsorted[0], vert_edges,
            edge_faces)
        verts_unsorted.pop(0)

        # check if loop is fully selected
        search_perpendicular = False
        i = -1
        for loop, circular in loops:
            i += 1
            selected = [v for v in loop if bm_mod.verts[v].select]
            if len(selected) < 2:
                # only one selected vertex on loop, don't use
                loops.pop(i)
                continue
            elif len(selected) == len(loop):
                search_perpendicular = loop
                break
        # entire loop is selected, find perpendicular loops
        if search_perpendicular:
            for vert in loop:
                if vert in verts_unsorted:
                    verts_unsorted.remove(vert)
            perp_loops = curve_perpendicular_loops(bm_mod, loop,
                vert_edges, edge_faces)
            for perp_loop in perp_loops:
                correct_loops.append(perp_loop)
        # normal input
        else:
            for loop, circular in loops:
                correct_loops.append([loop, circular])

    # boundaries option
    if boundaries:
        correct_loops = curve_cut_boundaries(bm_mod, correct_loops)

    return(derived, bm_mod, correct_loops)


# return all loops that are perpendicular to the given one
def curve_perpendicular_loops(bm_mod, start_loop, vert_edges, edge_faces):
    # find perpendicular loops
    perp_loops = []
    for start_vert in start_loop:
        loops = curve_vertex_loops(bm_mod, start_vert, vert_edges,
            edge_faces)
        for loop, circular in loops:
            selected = [v for v in loop if bm_mod.verts[v].select]
            if len(selected) == len(loop):
                continue
            else:
                perp_loops.append([loop, circular, loop.index(start_vert)])

    # trim loops to same lengths
    shortest = [
        [len(loop[0]), i] for i, loop in enumerate(perp_loops) if not loop[1]
        ]
    if not shortest:
        # all loops are circular, not trimming
        return([[loop[0], loop[1]] for loop in perp_loops])
    else:
        shortest = min(shortest)
    shortest_start = perp_loops[shortest[1]][2]
    before_start = shortest_start
    after_start = shortest[0] - shortest_start - 1
    bigger_before = before_start > after_start
    trimmed_loops = []
    for loop in perp_loops:
        # have the loop face the same direction as the shortest one
        if bigger_before:
            if loop[2] < len(loop[0]) / 2:
                loop[0].reverse()
                loop[2] = len(loop[0]) - loop[2] - 1
        else:
            if loop[2] > len(loop[0]) / 2:
                loop[0].reverse()
                loop[2] = len(loop[0]) - loop[2] - 1
        # circular loops can shift, to prevent wrong trimming
        if loop[1]:
            shift = shortest_start - loop[2]
            if loop[2] + shift > 0 and loop[2] + shift < len(loop[0]):
                loop[0] = loop[0][-shift:] + loop[0][:-shift]
            loop[2] += shift
            if loop[2] < 0:
                loop[2] += len(loop[0])
            elif loop[2] > len(loop[0]) - 1:
                loop[2] -= len(loop[0])
        # trim
        start = max(0, loop[2] - before_start)
        end = min(len(loop[0]), loop[2] + after_start + 1)
        trimmed_loops.append([loop[0][start:end], False])

    return(trimmed_loops)


# project knots on non-selected geometry
def curve_project_knots(bm_mod, verts_selected, knots, points, circular):
    # function to project vertex on edge
    def project(v1, v2, v3):
        # v1 and v2 are part of a line
        # v3 is projected onto it
        v2 -= v1
        v3 -= v1
        p = v3.project(v2)
        return(p + v1)

    if circular:  # project all knots
        start = 0
        end = len(knots)
        pknots = []
    else:  # first and last knot shouldn't be projected
        start = 1
        end = -1
        pknots = [mathutils.Vector(bm_mod.verts[knots[0]].co[:])]
    for knot in knots[start:end]:
        if knot in verts_selected:
            knot_left = knot_right = False
            for i in range(points.index(knot) - 1, -1 * len(points), -1):
                if points[i] not in knots:
                    knot_left = points[i]
                    break
            for i in range(points.index(knot) + 1, 2 * len(points)):
                if i > len(points) - 1:
                    i -= len(points)
                if points[i] not in knots:
                    knot_right = points[i]
                    break
            if knot_left and knot_right and knot_left != knot_right:
                knot_left = mathutils.Vector(bm_mod.verts[knot_left].co[:])
                knot_right = mathutils.Vector(bm_mod.verts[knot_right].co[:])
                knot = mathutils.Vector(bm_mod.verts[knot].co[:])
                pknots.append(project(knot_left, knot_right, knot))
            else:
                pknots.append(mathutils.Vector(bm_mod.verts[knot].co[:]))
        else:  # knot isn't selected, so shouldn't be changed
            pknots.append(mathutils.Vector(bm_mod.verts[knot].co[:]))
    if not circular:
        pknots.append(mathutils.Vector(bm_mod.verts[knots[-1]].co[:]))

    return(pknots)


# find all loops through a given vertex
def curve_vertex_loops(bm_mod, start_vert, vert_edges, edge_faces):
    edges_used = []
    loops = []

    for edge in vert_edges[start_vert]:
        if edge in edges_used:
            continue
        loop = []
        circular = False
        for vert in edge:
            active_faces = edge_faces[edge]
            new_vert = vert
            growing = True
            while growing:
                growing = False
                new_edges = vert_edges[new_vert]
                loop.append(new_vert)
                if len(loop) > 1:
                    edges_used.append(tuple(sorted([loop[-1], loop[-2]])))
                if len(new_edges) < 3 or len(new_edges) > 4:
                    # pole
                    break
                else:
                    # find next edge
                    for new_edge in new_edges:
                        if new_edge in edges_used:
                            continue
                        eliminate = False
                        for new_face in edge_faces[new_edge]:
                            if new_face in active_faces:
                                eliminate = True
                                break
                        if eliminate:
                            continue
                        # found correct new edge
                        active_faces = edge_faces[new_edge]
                        v1, v2 = new_edge
                        if v1 != new_vert:
                            new_vert = v1
                        else:
                            new_vert = v2
                        if new_vert == loop[0]:
                            circular = True
                        else:
                            growing = True
                        break
            if circular:
                break
            loop.reverse()
        loops.append([loop, circular])

    return(loops)


# ########################################
# ##### Flatten functions ################
# ########################################

# sort input into loops
def flatten_get_input(bm):
    vert_verts = dict_vert_verts(
            [edgekey(edge) for edge in bm.edges if edge.select and not edge.hide]
            )
    verts = [v.index for v in bm.verts if v.select and not v.hide]

    # no connected verts, consider all selected verts as a single input
    if not vert_verts:
        return([[verts, False]])

    loops = []
    while len(verts) > 0:
        # start of loop
        loop = [verts[0]]
        verts.pop(0)
        if loop[-1] in vert_verts:
            to_grow = vert_verts[loop[-1]]
        else:
            to_grow = []
        # grow loop
        while len(to_grow) > 0:
            new_vert = to_grow[0]
            to_grow.pop(0)
            if new_vert in loop:
                continue
            loop.append(new_vert)
            verts.remove(new_vert)
            to_grow += vert_verts[new_vert]
        # add loop to loops
        loops.append([loop, False])

    return(loops)


# calculate position of vertex projections on plane
def flatten_project(bm, loop, com, normal):
    verts = [bm.verts[v] for v in loop[0]]
    verts_projected = [
        [v.index, mathutils.Vector(v.co[:]) -
        (mathutils.Vector(v.co[:]) - com).dot(normal) * normal] for v in verts
        ]

    return(verts_projected)

# ########################################
# ##### Relax functions ##################
# ########################################

# create lists with knots and points, all correctly sorted
def relax_calculate_knots(loops):
    all_knots = []
    all_points = []
    for loop, circular in loops:
        knots = [[], []]
        points = [[], []]
        if circular:
            if len(loop) % 2 == 1:  # odd
                extend = [False, True, 0, 1, 0, 1]
            else:  # even
                extend = [True, False, 0, 1, 1, 2]
        else:
            if len(loop) % 2 == 1:  # odd
                extend = [False, False, 0, 1, 1, 2]
            else:  # even
                extend = [False, False, 0, 1, 1, 2]
        for j in range(2):
            if extend[j]:
                loop = [loop[-1]] + loop + [loop[0]]
            for i in range(extend[2 + 2 * j], len(loop), 2):
                knots[j].append(loop[i])
            for i in range(extend[3 + 2 * j], len(loop), 2):
                if loop[i] == loop[-1] and not circular:
                    continue
                if len(points[j]) == 0:
                    points[j].append(loop[i])
                elif loop[i] != points[j][0]:
                    points[j].append(loop[i])
            if circular:
                if knots[j][0] != knots[j][-1]:
                    knots[j].append(knots[j][0])
        if len(points[1]) == 0:
            knots.pop(1)
            points.pop(1)
        for k in knots:
            all_knots.append(k)
        for p in points:
            all_points.append(p)

    return(all_knots, all_points)


# calculate relative positions compared to first knot
def relax_calculate_t(bm_mod, knots, points, regular):
    all_tknots = []
    all_tpoints = []
    for i in range(len(knots)):
        amount = len(knots[i]) + len(points[i])
        mix = []
        for j in range(amount):
            if j % 2 == 0:
                mix.append([True, knots[i][round(j / 2)]])
            elif j == amount - 1:
                mix.append([True, knots[i][-1]])
            else:
                mix.append([False, points[i][int(j / 2)]])
        len_total = 0
        loc_prev = False
        tknots = []
        tpoints = []
        for m in mix:
            loc = mathutils.Vector(bm_mod.verts[m[1]].co[:])
            if not loc_prev:
                loc_prev = loc
            len_total += (loc - loc_prev).length
            if m[0]:
                tknots.append(len_total)
            else:
                tpoints.append(len_total)
            loc_prev = loc
        if regular:
            tpoints = []
            for p in range(len(points[i])):
                tpoints.append((tknots[p] + tknots[p + 1]) / 2)
        all_tknots.append(tknots)
        all_tpoints.append(tpoints)

    return(all_tknots, all_tpoints)


# change the location of the points to their place on the spline
def relax_calculate_verts(bm_mod, interpolation, tknots, knots, tpoints,
points, splines):
    change = []
    move = []
    for i in range(len(knots)):
        for p in points[i]:
            m = tpoints[i][points[i].index(p)]
            if m in tknots[i]:
                n = tknots[i].index(m)
            else:
                t = tknots[i][:]
                t.append(m)
                t.sort()
                n = t.index(m) - 1
            if n > len(splines[i]) - 1:
                n = len(splines[i]) - 1
            elif n < 0:
                n = 0

            if interpolation == 'cubic':
                ax, bx, cx, dx, tx = splines[i][n][0]
                x = ax + bx * (m - tx) + cx * (m - tx) ** 2 + dx * (m - tx) ** 3
                ay, by, cy, dy, ty = splines[i][n][1]
                y = ay + by * (m - ty) + cy * (m - ty) ** 2 + dy * (m - ty) ** 3
                az, bz, cz, dz, tz = splines[i][n][2]
                z = az + bz * (m - tz) + cz * (m - tz) ** 2 + dz * (m - tz) ** 3
                change.append([p, mathutils.Vector([x, y, z])])
            else:  # interpolation == 'linear'
                a, d, t, u = splines[i][n]
                if u == 0:
                    u = 1e-8
                change.append([p, ((m - t) / u) * d + a])
    for c in change:
        move.append([c[0], (bm_mod.verts[c[0]].co + c[1]) / 2])

    return(move)


# ########################################
# ##### Space functions ##################
# ########################################

# calculate relative positions compared to first knot
def space_calculate_t(bm_mod, knots):
    tknots = []
    loc_prev = False
    len_total = 0
    for k in knots:
        loc = mathutils.Vector(bm_mod.verts[k].co[:])
        if not loc_prev:
            loc_prev = loc
        len_total += (loc - loc_prev).length
        tknots.append(len_total)
        loc_prev = loc
    amount = len(knots)
    t_per_segment = len_total / (amount - 1)
    tpoints = [i * t_per_segment for i in range(amount)]

    return(tknots, tpoints)


# change the location of the points to their place on the spline
def space_calculate_verts(bm_mod, interpolation, tknots, tpoints, points,
splines):
    move = []
    for p in points:
        m = tpoints[points.index(p)]
        if m in tknots:
            n = tknots.index(m)
        else:
            t = tknots[:]
            t.append(m)
            t.sort()
            n = t.index(m) - 1
        if n > len(splines) - 1:
            n = len(splines) - 1
        elif n < 0:
            n = 0

        if interpolation == 'cubic':
            ax, bx, cx, dx, tx = splines[n][0]
            x = ax + bx * (m - tx) + cx * (m - tx) ** 2 + dx * (m - tx) ** 3
            ay, by, cy, dy, ty = splines[n][1]
            y = ay + by * (m - ty) + cy * (m - ty) ** 2 + dy * (m - ty) ** 3
            az, bz, cz, dz, tz = splines[n][2]
            z = az + bz * (m - tz) + cz * (m - tz) ** 2 + dz * (m - tz) ** 3
            move.append([p, mathutils.Vector([x, y, z])])
        else:  # interpolation == 'linear'
            a, d, t, u = splines[n]
            move.append([p, ((m - t) / u) * d + a])

    return(move)


# ########################################
# ##### Operators ########################
# ########################################

# circle operator
class Circle(Operator):
    bl_idname = "mesh.looptools_circle"
    bl_label = "Circle"
    bl_description = "Move selected vertices into a circle shape"
    bl_options = {'REGISTER', 'UNDO'}

    custom_radius: BoolProperty(
        name="Radius",
        description="Force a custom radius",
        default=False
        )
    fit: EnumProperty(
        name="Method",
        items=(("best", "Best fit", "Non-linear least squares"),
               ("inside", "Fit inside", "Only move vertices towards the center")),
        description="Method used for fitting a circle to the vertices",
        default='best'
        )
    flatten: BoolProperty(
        name="Flatten",
        description="Flatten the circle, instead of projecting it on the mesh",
        default=True
        )
    influence: FloatProperty(
        name="Influence",
        description="Force of the tool",
        default=100.0,
        min=0.0,
        max=100.0,
        precision=1,
        subtype='PERCENTAGE'
        )
    lock_x: BoolProperty(
        name="Lock X",
        description="Lock editing of the x-coordinate",
        default=False
        )
    lock_y: BoolProperty(
        name="Lock Y",
        description="Lock editing of the y-coordinate",
        default=False
        )
    lock_z: BoolProperty(name="Lock Z",
        description="Lock editing of the z-coordinate",
        default=False
        )
    radius: FloatProperty(
        name="Radius",
        description="Custom radius for circle",
        default=1.0,
        min=0.0,
        soft_max=1000.0
        )
    angle: FloatProperty(
        name="Angle",
        description="Rotate a circle by an angle",
        unit='ROTATION',
        default=math.radians(0.0),
        soft_min=math.radians(-360.0),
        soft_max=math.radians(360.0)
        )
    regular: BoolProperty(
        name="Regular",
        description="Distribute vertices at constant distances along the circle",
        default=True
        )

    @classmethod
    def poll(cls, context):
        ob = context.active_object
        return(ob and ob.type == 'MESH' and context.mode == 'EDIT_MESH')

    def draw(self, context):
        layout = self.layout
        col = layout.column()

        col.prop(self, "fit")
        col.separator()

        col.prop(self, "flatten")
        row = col.row(align=True)
        row.prop(self, "custom_radius")
        row_right = row.row(align=True)
        row_right.active = self.custom_radius
        row_right.prop(self, "radius", text="")
        col.prop(self, "regular")
        col.prop(self, "angle")
        col.separator()

        col_move = col.column(align=True)
        row = col_move.row(align=True)
        if self.lock_x:
            row.prop(self, "lock_x", text="X", icon='LOCKED')
        else:
            row.prop(self, "lock_x", text="X", icon='UNLOCKED')
        if self.lock_y:
            row.prop(self, "lock_y", text="Y", icon='LOCKED')
        else:
            row.prop(self, "lock_y", text="Y", icon='UNLOCKED')
        if self.lock_z:
            row.prop(self, "lock_z", text="Z", icon='LOCKED')
        else:
            row.prop(self, "lock_z", text="Z", icon='UNLOCKED')
        col_move.prop(self, "influence")

    def invoke(self, context, event):
        # load custom settings
        settings_load(self)
        return self.execute(context)

    def execute(self, context):
        # initialise
        object, bm = initialise()
        settings_write(self)
        # check cache to see if we can save time
        cached, single_loops, loops, derived, mapping = cache_read("Circle",
            object, bm, False, False)
        if cached:
            derived, bm_mod = get_derived_bmesh(object, bm, False)
        else:
            # find loops
            derived, bm_mod, single_vertices, single_loops, loops = \
                circle_get_input(object, bm)
            mapping = get_mapping(derived, bm, bm_mod, single_vertices,
                False, loops)
            single_loops, loops = circle_check_loops(single_loops, loops,
                mapping, bm_mod)

        # saving cache for faster execution next time
        if not cached:
            cache_write("Circle", object, bm, False, False, single_loops,
                loops, derived, mapping)

        move = []
        for i, loop in enumerate(loops):
            # best fitting flat plane
            com, normal = calculate_plane(bm_mod, loop)
            # if circular, shift loop so we get a good starting vertex
            if loop[1]:
                loop = circle_shift_loop(bm_mod, loop, com)
            # flatten vertices on plane
            locs_2d, p, q = circle_3d_to_2d(bm_mod, loop, com, normal)
            # calculate circle
            if self.fit == 'best':
                x0, y0, r = circle_calculate_best_fit(locs_2d)
            else:  # self.fit == 'inside'
                x0, y0, r = circle_calculate_min_fit(locs_2d)
            # radius override
            if self.custom_radius:
                r = self.radius / p.length
            # calculate positions on circle
            if self.regular:
                new_locs_2d = circle_project_regular(locs_2d[:], x0, y0, r, self.angle)
            else:
                new_locs_2d = circle_project_non_regular(locs_2d[:], x0, y0, r, self.angle)
            # take influence into account
            locs_2d = circle_influence_locs(locs_2d, new_locs_2d,
                self.influence)
            # calculate 3d positions of the created 2d input
            move.append(circle_calculate_verts(self.flatten, bm_mod,
                locs_2d, com, p, q, normal))
            # flatten single input vertices on plane defined by loop
            if self.flatten and single_loops:
                move.append(circle_flatten_singles(bm_mod, com, p, q,
                    normal, single_loops[i]))

        # move vertices to new locations
        if self.lock_x or self.lock_y or self.lock_z:
            lock = [self.lock_x, self.lock_y, self.lock_z]
        else:
            lock = False
        move_verts(object, bm, mapping, move, lock, -1)

        # cleaning up
        if derived:
            bm_mod.free()
        terminate()

        return{'FINISHED'}


# curve operator
class Curve(Operator):
    bl_idname = "mesh.looptools_curve"
    bl_label = "Curve"
    bl_description = "Turn a loop into a smooth curve"
    bl_options = {'REGISTER', 'UNDO'}

    boundaries: BoolProperty(
        name="Boundaries",
        description="Limit the tool to work within the boundaries of the selected vertices",
        default=False
        )
    influence: FloatProperty(
        name="Influence",
        description="Force of the tool",
        default=100.0,
        min=0.0,
        max=100.0,
        precision=1,
        subtype='PERCENTAGE'
        )
    interpolation: EnumProperty(
        name="Interpolation",
        items=(("cubic", "Cubic", "Natural cubic spline, smooth results"),
              ("linear", "Linear", "Simple and fast linear algorithm")),
        description="Algorithm used for interpolation",
        default='cubic'
        )
    lock_x: BoolProperty(
        name="Lock X",
        description="Lock editing of the x-coordinate",
        default=False
        )
    lock_y: BoolProperty(
        name="Lock Y",
        description="Lock editing of the y-coordinate",
        default=False
        )
    lock_z: BoolProperty(
        name="Lock Z",
        description="Lock editing of the z-coordinate",
        default=False
        )
    regular: BoolProperty(
        name="Regular",
        description="Distribute vertices at constant distances along the curve",
        default=True
        )
    restriction: EnumProperty(
        name="Restriction",
        items=(("none", "None", "No restrictions on vertex movement"),
              ("extrude", "Extrude only", "Only allow extrusions (no indentations)"),
              ("indent", "Indent only", "Only allow indentation (no extrusions)")),
        description="Restrictions on how the vertices can be moved",
        default='none'
        )

    @classmethod
    def poll(cls, context):
        ob = context.active_object
        return(ob and ob.type == 'MESH' and context.mode == 'EDIT_MESH')

    def draw(self, context):
        layout = self.layout
        col = layout.column()

        col.prop(self, "interpolation")
        col.prop(self, "restriction")
        col.prop(self, "boundaries")
        col.prop(self, "regular")
        col.separator()

        col_move = col.column(align=True)
        row = col_move.row(align=True)
        if self.lock_x:
            row.prop(self, "lock_x", text="X", icon='LOCKED')
        else:
            row.prop(self, "lock_x", text="X", icon='UNLOCKED')
        if self.lock_y:
            row.prop(self, "lock_y", text="Y", icon='LOCKED')
        else:
            row.prop(self, "lock_y", text="Y", icon='UNLOCKED')
        if self.lock_z:
            row.prop(self, "lock_z", text="Z", icon='LOCKED')
        else:
            row.prop(self, "lock_z", text="Z", icon='UNLOCKED')
        col_move.prop(self, "influence")

    def invoke(self, context, event):
        # load custom settings
        settings_load(self)
        return self.execute(context)

    def execute(self, context):
        # initialise
        object, bm = initialise()
        settings_write(self)
        # check cache to see if we can save time
        cached, single_loops, loops, derived, mapping = cache_read("Curve",
            object, bm, False, self.boundaries)
        if cached:
            derived, bm_mod = get_derived_bmesh(object, bm, False)
        else:
            # find loops
            derived, bm_mod, loops = curve_get_input(object, bm, self.boundaries)
            mapping = get_mapping(derived, bm, bm_mod, False, True, loops)
            loops = check_loops(loops, mapping, bm_mod)
        verts_selected = [
            v.index for v in bm_mod.verts if v.select and not v.hide
            ]

        # saving cache for faster execution next time
        if not cached:
            cache_write("Curve", object, bm, False, self.boundaries, False,
                loops, derived, mapping)

        move = []
        for loop in loops:
            knots, points = curve_calculate_knots(loop, verts_selected)
            pknots = curve_project_knots(bm_mod, verts_selected, knots,
                points, loop[1])
            tknots, tpoints = curve_calculate_t(bm_mod, knots, points,
                pknots, self.regular, loop[1])
            splines = calculate_splines(self.interpolation, bm_mod,
                tknots, knots)
            move.append(curve_calculate_vertices(bm_mod, knots, tknots,
                points, tpoints, splines, self.interpolation,
                self.restriction))

        # move vertices to new locations
        if self.lock_x or self.lock_y or self.lock_z:
            lock = [self.lock_x, self.lock_y, self.lock_z]
        else:
            lock = False
        move_verts(object, bm, mapping, move, lock, self.influence)

        # cleaning up
        if derived:
            bm_mod.free()
        terminate()

        return{'FINISHED'}


# flatten operator
class Flatten(Operator):
    bl_idname = "mesh.looptools_flatten"
    bl_label = "Flatten"
    bl_description = "Flatten vertices on a best-fitting plane"
    bl_options = {'REGISTER', 'UNDO'}

    influence: FloatProperty(
        name="Influence",
        description="Force of the tool",
        default=100.0,
        min=0.0,
        max=100.0,
        precision=1,
        subtype='PERCENTAGE'
        )
    lock_x: BoolProperty(
        name="Lock X",
        description="Lock editing of the x-coordinate",
        default=False
        )
    lock_y: BoolProperty(
        name="Lock Y",
        description="Lock editing of the y-coordinate",
        default=False
        )
    lock_z: BoolProperty(name="Lock Z",
        description="Lock editing of the z-coordinate",
        default=False
        )
    plane: EnumProperty(
        name="Plane",
        items=(("best_fit", "Best fit", "Calculate a best fitting plane"),
              ("normal", "Normal", "Derive plane from averaging vertex normals"),
              ("view", "View", "Flatten on a plane perpendicular to the viewing angle")),
        description="Plane on which vertices are flattened",
        default='best_fit'
        )
    restriction: EnumProperty(
        name="Restriction",
        items=(("none", "None", "No restrictions on vertex movement"),
               ("bounding_box", "Bounding box", "Vertices are restricted to "
               "movement inside the bounding box of the selection")),
        description="Restrictions on how the vertices can be moved",
        default='none'
        )

    @classmethod
    def poll(cls, context):
        ob = context.active_object
        return(ob and ob.type == 'MESH' and context.mode == 'EDIT_MESH')

    def draw(self, context):
        layout = self.layout
        col = layout.column()

        col.prop(self, "plane")
        # col.prop(self, "restriction")
        col.separator()

        col_move = col.column(align=True)
        row = col_move.row(align=True)
        if self.lock_x:
            row.prop(self, "lock_x", text="X", icon='LOCKED')
        else:
            row.prop(self, "lock_x", text="X", icon='UNLOCKED')
        if self.lock_y:
            row.prop(self, "lock_y", text="Y", icon='LOCKED')
        else:
            row.prop(self, "lock_y", text="Y", icon='UNLOCKED')
        if self.lock_z:
            row.prop(self, "lock_z", text="Z", icon='LOCKED')
        else:
            row.prop(self, "lock_z", text="Z", icon='UNLOCKED')
        col_move.prop(self, "influence")

    def invoke(self, context, event):
        # load custom settings
        settings_load(self)
        return self.execute(context)

    def execute(self, context):
        # initialise
        object, bm = initialise()
        settings_write(self)
        # check cache to see if we can save time
        cached, single_loops, loops, derived, mapping = cache_read("Flatten",
            object, bm, False, False)
        if not cached:
            # order input into virtual loops
            loops = flatten_get_input(bm)
            loops = check_loops(loops, mapping, bm)

        # saving cache for faster execution next time
        if not cached:
            cache_write("Flatten", object, bm, False, False, False, loops,
                False, False)

        move = []
        for loop in loops:
            # calculate plane and position of vertices on them
            com, normal = calculate_plane(bm, loop, method=self.plane,
                object=object)
            to_move = flatten_project(bm, loop, com, normal)
            if self.restriction == 'none':
                move.append(to_move)
            else:
                move.append(to_move)

        # move vertices to new locations
        if self.lock_x or self.lock_y or self.lock_z:
            lock = [self.lock_x, self.lock_y, self.lock_z]
        else:
            lock = False
        move_verts(object, bm, False, move, lock, self.influence)

        # cleaning up
        terminate()

        return{'FINISHED'}

# relax operator
class Relax(Operator):
    bl_idname = "mesh.looptools_relax"
    bl_label = "Relax"
    bl_description = "Relax the loop, so it is smoother"
    bl_options = {'REGISTER', 'UNDO'}

    input: EnumProperty(
        name="Input",
        items=(("all", "Parallel (all)", "Also use non-selected "
               "parallel loops as input"),
               ("selected", "Selection", "Only use selected vertices as input")),
        description="Loops that are relaxed",
        default='selected'
        )
    interpolation: EnumProperty(
        name="Interpolation",
        items=(("cubic", "Cubic", "Natural cubic spline, smooth results"),
               ("linear", "Linear", "Simple and fast linear algorithm")),
        description="Algorithm used for interpolation",
        default='cubic'
        )
    iterations: EnumProperty(
        name="Iterations",
        items=(("1", "1", "One"),
               ("3", "3", "Three"),
               ("5", "5", "Five"),
               ("10", "10", "Ten"),
              ("25", "25", "Twenty-five")),
        description="Number of times the loop is relaxed",
        default="1"
        )
    regular: BoolProperty(
        name="Regular",
        description="Distribute vertices at constant distances along the loop",
        default=True
        )

    @classmethod
    def poll(cls, context):
        ob = context.active_object
        return(ob and ob.type == 'MESH' and context.mode == 'EDIT_MESH')

    def draw(self, context):
        layout = self.layout
        col = layout.column()

        col.prop(self, "interpolation")
        col.prop(self, "input")
        col.prop(self, "iterations")
        col.prop(self, "regular")

    def invoke(self, context, event):
        # load custom settings
        settings_load(self)
        return self.execute(context)

    def execute(self, context):
        # initialise
        object, bm = initialise()
        settings_write(self)
        # check cache to see if we can save time
        cached, single_loops, loops, derived, mapping = cache_read("Relax",
            object, bm, self.input, False)
        if cached:
            derived, bm_mod = get_derived_bmesh(object, bm, False)
        else:
            # find loops
            derived, bm_mod, loops = get_connected_input(object, bm, False, self.input)
            mapping = get_mapping(derived, bm, bm_mod, False, False, loops)
            loops = check_loops(loops, mapping, bm_mod)
        knots, points = relax_calculate_knots(loops)

        # saving cache for faster execution next time
        if not cached:
            cache_write("Relax", object, bm, self.input, False, False, loops,
                derived, mapping)

        for iteration in range(int(self.iterations)):
            # calculate splines and new positions
            tknots, tpoints = relax_calculate_t(bm_mod, knots, points,
                self.regular)
            splines = []
            for i in range(len(knots)):
                splines.append(calculate_splines(self.interpolation, bm_mod,
                    tknots[i], knots[i]))
            move = [relax_calculate_verts(bm_mod, self.interpolation,
                tknots, knots, tpoints, points, splines)]
            move_verts(object, bm, mapping, move, False, -1)

        # cleaning up
        if derived:
            bm_mod.free()
        terminate()

        return{'FINISHED'}


# space operator
class Space(Operator):
    bl_idname = "mesh.looptools_space"
    bl_label = "Space"
    bl_description = "Space the vertices in a regular distribution on the loop"
    bl_options = {'REGISTER', 'UNDO'}

    influence: FloatProperty(
        name="Influence",
        description="Force of the tool",
        default=100.0,
        min=0.0,
        max=100.0,
        precision=1,
        subtype='PERCENTAGE'
        )
    input: EnumProperty(
        name="Input",
        items=(("all", "Parallel (all)", "Also use non-selected "
                "parallel loops as input"),
              ("selected", "Selection", "Only use selected vertices as input")),
        description="Loops that are spaced",
        default='selected'
        )
    interpolation: EnumProperty(
        name="Interpolation",
        items=(("cubic", "Cubic", "Natural cubic spline, smooth results"),
              ("linear", "Linear", "Vertices are projected on existing edges")),
        description="Algorithm used for interpolation",
        default='cubic'
        )
    lock_x: BoolProperty(
        name="Lock X",
        description="Lock editing of the x-coordinate",
        default=False
        )
    lock_y: BoolProperty(
        name="Lock Y",
        description="Lock editing of the y-coordinate",
        default=False
        )
    lock_z: BoolProperty(
        name="Lock Z",
        description="Lock editing of the z-coordinate",
        default=False
        )

    @classmethod
    def poll(cls, context):
        ob = context.active_object
        return(ob and ob.type == 'MESH' and context.mode == 'EDIT_MESH')

    def draw(self, context):
        layout = self.layout
        col = layout.column()

        col.prop(self, "interpolation")
        col.prop(self, "input")
        col.separator()

        col_move = col.column(align=True)
        row = col_move.row(align=True)
        if self.lock_x:
            row.prop(self, "lock_x", text="X", icon='LOCKED')
        else:
            row.prop(self, "lock_x", text="X", icon='UNLOCKED')
        if self.lock_y:
            row.prop(self, "lock_y", text="Y", icon='LOCKED')
        else:
            row.prop(self, "lock_y", text="Y", icon='UNLOCKED')
        if self.lock_z:
            row.prop(self, "lock_z", text="Z", icon='LOCKED')
        else:
            row.prop(self, "lock_z", text="Z", icon='UNLOCKED')
        col_move.prop(self, "influence")

    def invoke(self, context, event):
        # load custom settings
        settings_load(self)
        return self.execute(context)

    def execute(self, context):
        # initialise
        object, bm = initialise()
        settings_write(self)
        # check cache to see if we can save time
        cached, single_loops, loops, derived, mapping = cache_read("Space",
            object, bm, self.input, False)
        if cached:
            derived, bm_mod = get_derived_bmesh(object, bm, True)
        else:
            # find loops
            derived, bm_mod, loops = get_connected_input(object, bm, True, self.input)
            mapping = get_mapping(derived, bm, bm_mod, False, False, loops)
            loops = check_loops(loops, mapping, bm_mod)

        # saving cache for faster execution next time
        if not cached:
            cache_write("Space", object, bm, self.input, False, False, loops,
                derived, mapping)

        move = []
        for loop in loops:
            # calculate splines and new positions
            if loop[1]:  # circular
                loop[0].append(loop[0][0])
            tknots, tpoints = space_calculate_t(bm_mod, loop[0][:])
            splines = calculate_splines(self.interpolation, bm_mod,
                tknots, loop[0][:])
            move.append(space_calculate_verts(bm_mod, self.interpolation,
                tknots, tpoints, loop[0][:-1], splines))
        # move vertices to new locations
        if self.lock_x or self.lock_y or self.lock_z:
            lock = [self.lock_x, self.lock_y, self.lock_z]
        else:
            lock = False
        move_verts(object, bm, mapping, move, lock, self.influence)

        # cleaning up
        if derived:
            bm_mod.free()
        terminate()

        cache_delete("Space")

        return{'FINISHED'}


# ########################################
# ##### GUI and registration #############
# ########################################

# menu containing all tools
class VIEW3D_MT_edit_mesh_looptools(Menu):
    bl_label = "LoopTools"

    def draw(self, context):
        layout = self.layout

        layout.operator("mesh.looptools_circle")
        layout.operator("mesh.looptools_curve")
        layout.operator("mesh.looptools_flatten")
        layout.operator("mesh.looptools_relax")
        layout.operator("mesh.looptools_space")


# panel containing all tools
class VIEW3D_PT_tools_looptools(Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Edit'
    bl_context = "mesh_edit"
    bl_label = "LoopTools"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        lt = context.window_manager.looptools

        # bridge - first line
        split = col.split(factor=0.15, align=True)
        if lt.display_bridge:
            split.prop(lt, "display_bridge", text="", icon='DOWNARROW_HLT')
        else:
            split.prop(lt, "display_bridge", text="", icon='RIGHTARROW')
        split.operator("mesh.looptools_bridge", text="Bridge").loft = False
        # bridge - settings
        if lt.display_bridge:
            box = col.column(align=True).box().column()
            # box.prop(self, "mode")

            # top row
            col_top = box.column(align=True)
            row = col_top.row(align=True)
            col_left = row.column(align=True)
            col_right = row.column(align=True)
            col_right.active = lt.bridge_segments != 1
            col_left.prop(lt, "bridge_segments")
            col_right.prop(lt, "bridge_min_width", text="")
            # bottom row
            bottom_left = col_left.row()
            bottom_left.active = lt.bridge_segments != 1
            bottom_left.prop(lt, "bridge_interpolation", text="")
            bottom_right = col_right.row()
            bottom_right.active = lt.bridge_interpolation == 'cubic'
            bottom_right.prop(lt, "bridge_cubic_strength")
            # boolean properties
            col_top.prop(lt, "bridge_remove_faces")

            # override properties
            col_top.separator()
            row = box.row(align=True)
            row.prop(lt, "bridge_twist")
            row.prop(lt, "bridge_reverse")

        # circle - first line
        split = col.split(factor=0.15, align=True)
        if lt.display_circle:
            split.prop(lt, "display_circle", text="", icon='DOWNARROW_HLT')
        else:
            split.prop(lt, "display_circle", text="", icon='RIGHTARROW')
        split.operator("mesh.looptools_circle")
        # circle - settings
        if lt.display_circle:
            box = col.column(align=True).box().column()
            box.prop(lt, "circle_fit")
            box.separator()

            box.prop(lt, "circle_flatten")
            row = box.row(align=True)
            row.prop(lt, "circle_custom_radius")
            row_right = row.row(align=True)
            row_right.active = lt.circle_custom_radius
            row_right.prop(lt, "circle_radius", text="")
            box.prop(lt, "circle_regular")
            box.separator()

            col_move = box.column(align=True)
            row = col_move.row(align=True)
            if lt.circle_lock_x:
                row.prop(lt, "circle_lock_x", text="X", icon='LOCKED')
            else:
                row.prop(lt, "circle_lock_x", text="X", icon='UNLOCKED')
            if lt.circle_lock_y:
                row.prop(lt, "circle_lock_y", text="Y", icon='LOCKED')
            else:
                row.prop(lt, "circle_lock_y", text="Y", icon='UNLOCKED')
            if lt.circle_lock_z:
                row.prop(lt, "circle_lock_z", text="Z", icon='LOCKED')
            else:
                row.prop(lt, "circle_lock_z", text="Z", icon='UNLOCKED')
            col_move.prop(lt, "circle_influence")

        # curve - first line
        split = col.split(factor=0.15, align=True)
        if lt.display_curve:
            split.prop(lt, "display_curve", text="", icon='DOWNARROW_HLT')
        else:
            split.prop(lt, "display_curve", text="", icon='RIGHTARROW')
        split.operator("mesh.looptools_curve")
        # curve - settings
        if lt.display_curve:
            box = col.column(align=True).box().column()
            box.prop(lt, "curve_interpolation")
            box.prop(lt, "curve_restriction")
            box.prop(lt, "curve_boundaries")
            box.prop(lt, "curve_regular")
            box.separator()

            col_move = box.column(align=True)
            row = col_move.row(align=True)
            if lt.curve_lock_x:
                row.prop(lt, "curve_lock_x", text="X", icon='LOCKED')
            else:
                row.prop(lt, "curve_lock_x", text="X", icon='UNLOCKED')
            if lt.curve_lock_y:
                row.prop(lt, "curve_lock_y", text="Y", icon='LOCKED')
            else:
                row.prop(lt, "curve_lock_y", text="Y", icon='UNLOCKED')
            if lt.curve_lock_z:
                row.prop(lt, "curve_lock_z", text="Z", icon='LOCKED')
            else:
                row.prop(lt, "curve_lock_z", text="Z", icon='UNLOCKED')
            col_move.prop(lt, "curve_influence")

        # flatten - first line
        split = col.split(factor=0.15, align=True)
        if lt.display_flatten:
            split.prop(lt, "display_flatten", text="", icon='DOWNARROW_HLT')
        else:
            split.prop(lt, "display_flatten", text="", icon='RIGHTARROW')
        split.operator("mesh.looptools_flatten")
        # flatten - settings
        if lt.display_flatten:
            box = col.column(align=True).box().column()
            box.prop(lt, "flatten_plane")
            # box.prop(lt, "flatten_restriction")
            box.separator()

            col_move = box.column(align=True)
            row = col_move.row(align=True)
            if lt.flatten_lock_x:
                row.prop(lt, "flatten_lock_x", text="X", icon='LOCKED')
            else:
                row.prop(lt, "flatten_lock_x", text="X", icon='UNLOCKED')
            if lt.flatten_lock_y:
                row.prop(lt, "flatten_lock_y", text="Y", icon='LOCKED')
            else:
                row.prop(lt, "flatten_lock_y", text="Y", icon='UNLOCKED')
            if lt.flatten_lock_z:
                row.prop(lt, "flatten_lock_z", text="Z", icon='LOCKED')
            else:
                row.prop(lt, "flatten_lock_z", text="Z", icon='UNLOCKED')
            col_move.prop(lt, "flatten_influence")

        # gstretch - first line
        split = col.split(factor=0.15, align=True)
        if lt.display_gstretch:
            split.prop(lt, "display_gstretch", text="", icon='DOWNARROW_HLT')
        else:
            split.prop(lt, "display_gstretch", text="", icon='RIGHTARROW')
        split.operator("mesh.looptools_gstretch")
        # gstretch settings
        if lt.display_gstretch:
            box = col.column(align=True).box().column()
            box.prop(lt, "gstretch_use_guide")
            if lt.gstretch_use_guide == "GPencil":
                box.prop(lt, "gstretch_guide")
            box.prop(lt, "gstretch_method")

            col_conv = box.column(align=True)
            col_conv.prop(lt, "gstretch_conversion", text="")
            if lt.gstretch_conversion == 'distance':
                col_conv.prop(lt, "gstretch_conversion_distance")
            elif lt.gstretch_conversion == 'limit_vertices':
                row = col_conv.row(align=True)
                row.prop(lt, "gstretch_conversion_min", text="Min")
                row.prop(lt, "gstretch_conversion_max", text="Max")
            elif lt.gstretch_conversion == 'vertices':
                col_conv.prop(lt, "gstretch_conversion_vertices")
            box.separator()

            col_move = box.column(align=True)
            row = col_move.row(align=True)
            if lt.gstretch_lock_x:
                row.prop(lt, "gstretch_lock_x", text="X", icon='LOCKED')
            else:
                row.prop(lt, "gstretch_lock_x", text="X", icon='UNLOCKED')
            if lt.gstretch_lock_y:
                row.prop(lt, "gstretch_lock_y", text="Y", icon='LOCKED')
            else:
                row.prop(lt, "gstretch_lock_y", text="Y", icon='UNLOCKED')
            if lt.gstretch_lock_z:
                row.prop(lt, "gstretch_lock_z", text="Z", icon='LOCKED')
            else:
                row.prop(lt, "gstretch_lock_z", text="Z", icon='UNLOCKED')
            col_move.prop(lt, "gstretch_influence")
            if lt.gstretch_use_guide == "Annotation":
                box.operator("remove.annotation", text="Delete Annotation Strokes")
            if lt.gstretch_use_guide == "GPencil":
                box.operator("remove.gp", text="Delete GPencil Strokes")

        # loft - first line
        split = col.split(factor=0.15, align=True)
        if lt.display_loft:
            split.prop(lt, "display_loft", text="", icon='DOWNARROW_HLT')
        else:
            split.prop(lt, "display_loft", text="", icon='RIGHTARROW')
        split.operator("mesh.looptools_bridge", text="Loft").loft = True
        # loft - settings
        if lt.display_loft:
            box = col.column(align=True).box().column()
            # box.prop(self, "mode")

            # top row
            col_top = box.column(align=True)
            row = col_top.row(align=True)
            col_left = row.column(align=True)
            col_right = row.column(align=True)
            col_right.active = lt.bridge_segments != 1
            col_left.prop(lt, "bridge_segments")
            col_right.prop(lt, "bridge_min_width", text="")
            # bottom row
            bottom_left = col_left.row()
            bottom_left.active = lt.bridge_segments != 1
            bottom_left.prop(lt, "bridge_interpolation", text="")
            bottom_right = col_right.row()
            bottom_right.active = lt.bridge_interpolation == 'cubic'
            bottom_right.prop(lt, "bridge_cubic_strength")
            # boolean properties
            col_top.prop(lt, "bridge_remove_faces")
            col_top.prop(lt, "bridge_loft_loop")

            # override properties
            col_top.separator()
            row = box.row(align=True)
            row.prop(lt, "bridge_twist")
            row.prop(lt, "bridge_reverse")

        # relax - first line
        split = col.split(factor=0.15, align=True)
        if lt.display_relax:
            split.prop(lt, "display_relax", text="", icon='DOWNARROW_HLT')
        else:
            split.prop(lt, "display_relax", text="", icon='RIGHTARROW')
        split.operator("mesh.looptools_relax")
        # relax - settings
        if lt.display_relax:
            box = col.column(align=True).box().column()
            box.prop(lt, "relax_interpolation")
            box.prop(lt, "relax_input")
            box.prop(lt, "relax_iterations")
            box.prop(lt, "relax_regular")

        # space - first line
        split = col.split(factor=0.15, align=True)
        if lt.display_space:
            split.prop(lt, "display_space", text="", icon='DOWNARROW_HLT')
        else:
            split.prop(lt, "display_space", text="", icon='RIGHTARROW')
        split.operator("mesh.looptools_space")
        # space - settings
        if lt.display_space:
            box = col.column(align=True).box().column()
            box.prop(lt, "space_interpolation")
            box.prop(lt, "space_input")
            box.separator()

            col_move = box.column(align=True)
            row = col_move.row(align=True)
            if lt.space_lock_x:
                row.prop(lt, "space_lock_x", text="X", icon='LOCKED')
            else:
                row.prop(lt, "space_lock_x", text="X", icon='UNLOCKED')
            if lt.space_lock_y:
                row.prop(lt, "space_lock_y", text="Y", icon='LOCKED')
            else:
                row.prop(lt, "space_lock_y", text="Y", icon='UNLOCKED')
            if lt.space_lock_z:
                row.prop(lt, "space_lock_z", text="Z", icon='LOCKED')
            else:
                row.prop(lt, "space_lock_z", text="Z", icon='UNLOCKED')
            col_move.prop(lt, "space_influence")


# property group containing all properties for the gui in the panel
class LoopToolsProps(PropertyGroup):
    """
    Fake module like class
    bpy.context.window_manager.looptools
    """
    # general display properties
    display_circle: BoolProperty(
        name="Circle settings",
        description="Display settings of the Circle tool",
        default=False
        )
    display_curve: BoolProperty(
        name="Curve settings",
        description="Display settings of the Curve tool",
        default=False
        )
    display_flatten: BoolProperty(
        name="Flatten settings",
        description="Display settings of the Flatten tool",
        default=False
        )
    display_relax: BoolProperty(
        name="Relax settings",
        description="Display settings of the Relax tool",
        default=False
        )
    display_space: BoolProperty(
        name="Space settings",
        description="Display settings of the Space tool",
        default=False
        )

    # circle properties
    circle_custom_radius: BoolProperty(
        name="Radius",
        description="Force a custom radius",
        default=False
        )
    circle_fit: EnumProperty(
        name="Method",
        items=(("best", "Best fit", "Non-linear least squares"),
            ("inside", "Fit inside", "Only move vertices towards the center")),
        description="Method used for fitting a circle to the vertices",
        default='best'
        )
    circle_flatten: BoolProperty(
        name="Flatten",
        description="Flatten the circle, instead of projecting it on the mesh",
        default=True
        )
    circle_influence: FloatProperty(
        name="Influence",
        description="Force of the tool",
        default=100.0,
        min=0.0,
        max=100.0,
        precision=1,
        subtype='PERCENTAGE'
        )
    circle_lock_x: BoolProperty(
        name="Lock X",
        description="Lock editing of the x-coordinate",
        default=False
        )
    circle_lock_y: BoolProperty(
        name="Lock Y",
        description="Lock editing of the y-coordinate",
        default=False
        )
    circle_lock_z: BoolProperty(
        name="Lock Z",
        description="Lock editing of the z-coordinate",
        default=False
        )
    circle_radius: FloatProperty(
        name="Radius",
        description="Custom radius for circle",
        default=1.0,
        min=0.0,
        soft_max=1000.0
        )
    circle_regular: BoolProperty(
        name="Regular",
        description="Distribute vertices at constant distances along the circle",
        default=True
        )
    circle_angle: FloatProperty(
        name="Angle",
        description="Rotate a circle by an angle",
        unit='ROTATION',
        default=math.radians(0.0),
        soft_min=math.radians(-360.0),
        soft_max=math.radians(360.0)
        )
    # curve properties
    curve_boundaries: BoolProperty(
        name="Boundaries",
        description="Limit the tool to work within the boundaries of the "
                    "selected vertices",
        default=False
        )
    curve_influence: FloatProperty(
        name="Influence",
        description="Force of the tool",
        default=100.0,
        min=0.0,
        max=100.0,
        precision=1,
        subtype='PERCENTAGE'
        )
    curve_interpolation: EnumProperty(
        name="Interpolation",
        items=(("cubic", "Cubic", "Natural cubic spline, smooth results"),
            ("linear", "Linear", "Simple and fast linear algorithm")),
        description="Algorithm used for interpolation",
        default='cubic'
        )
    curve_lock_x: BoolProperty(
        name="Lock X",
        description="Lock editing of the x-coordinate",
        default=False
        )
    curve_lock_y: BoolProperty(
        name="Lock Y",
        description="Lock editing of the y-coordinate",
        default=False
        )
    curve_lock_z: BoolProperty(
        name="Lock Z",
        description="Lock editing of the z-coordinate",
        default=False
        )
    curve_regular: BoolProperty(
        name="Regular",
        description="Distribute vertices at constant distances along the curve",
        default=True
        )
    curve_restriction: EnumProperty(
        name="Restriction",
        items=(("none", "None", "No restrictions on vertex movement"),
            ("extrude", "Extrude only", "Only allow extrusions (no indentations)"),
            ("indent", "Indent only", "Only allow indentation (no extrusions)")),
        description="Restrictions on how the vertices can be moved",
        default='none'
        )

    # flatten properties
    flatten_influence: FloatProperty(
        name="Influence",
        description="Force of the tool",
        default=100.0,
        min=0.0,
        max=100.0,
        precision=1,
        subtype='PERCENTAGE'
        )
    flatten_lock_x: BoolProperty(
        name="Lock X",
        description="Lock editing of the x-coordinate",
        default=False)
    flatten_lock_y: BoolProperty(name="Lock Y",
        description="Lock editing of the y-coordinate",
        default=False
        )
    flatten_lock_z: BoolProperty(
        name="Lock Z",
        description="Lock editing of the z-coordinate",
        default=False
        )
    flatten_plane: EnumProperty(
        name="Plane",
        items=(("best_fit", "Best fit", "Calculate a best fitting plane"),
            ("normal", "Normal", "Derive plane from averaging vertex "
            "normals"),
            ("view", "View", "Flatten on a plane perpendicular to the "
            "viewing angle")),
        description="Plane on which vertices are flattened",
        default='best_fit'
        )
    flatten_restriction: EnumProperty(
        name="Restriction",
        items=(("none", "None", "No restrictions on vertex movement"),
            ("bounding_box", "Bounding box", "Vertices are restricted to "
            "movement inside the bounding box of the selection")),
        description="Restrictions on how the vertices can be moved",
        default='none'
        )

    # relax properties
    relax_input: EnumProperty(name="Input",
        items=(("all", "Parallel (all)", "Also use non-selected "
                                           "parallel loops as input"),
                ("selected", "Selection", "Only use selected vertices as input")),
        description="Loops that are relaxed",
        default='selected'
        )
    relax_interpolation: EnumProperty(
        name="Interpolation",
        items=(("cubic", "Cubic", "Natural cubic spline, smooth results"),
                ("linear", "Linear", "Simple and fast linear algorithm")),
        description="Algorithm used for interpolation",
        default='cubic'
        )
    relax_iterations: EnumProperty(name="Iterations",
        items=(("1", "1", "One"),
                ("3", "3", "Three"),
                ("5", "5", "Five"),
                ("10", "10", "Ten"),
                ("25", "25", "Twenty-five")),
        description="Number of times the loop is relaxed",
        default="1"
        )
    relax_regular: BoolProperty(
        name="Regular",
        description="Distribute vertices at constant distances along the loop",
        default=True
        )

    # space properties
    space_influence: FloatProperty(
        name="Influence",
        description="Force of the tool",
        default=100.0,
        min=0.0,
        max=100.0,
        precision=1,
        subtype='PERCENTAGE'
        )
    space_input: EnumProperty(
        name="Input",
        items=(("all", "Parallel (all)", "Also use non-selected "
                "parallel loops as input"),
            ("selected", "Selection", "Only use selected vertices as input")),
        description="Loops that are spaced",
        default='selected'
        )
    space_interpolation: EnumProperty(
        name="Interpolation",
        items=(("cubic", "Cubic", "Natural cubic spline, smooth results"),
            ("linear", "Linear", "Vertices are projected on existing edges")),
        description="Algorithm used for interpolation",
        default='cubic'
        )
    space_lock_x: BoolProperty(
        name="Lock X",
        description="Lock editing of the x-coordinate",
        default=False
        )
    space_lock_y: BoolProperty(
        name="Lock Y",
        description="Lock editing of the y-coordinate",
        default=False
        )
    space_lock_z: BoolProperty(
        name="Lock Z",
        description="Lock editing of the z-coordinate",
        default=False
        )

# draw function for integration in menus
def menu_func(self, context):
    self.layout.menu("VIEW3D_MT_edit_mesh_looptools")
    self.layout.separator()

# define classes for registration
# classes = (
#     VIEW3D_MT_edit_mesh_looptools,
#     VIEW3D_PT_tools_looptools,
#     LoopToolsProps,
#     Circle,
#     Curve,
#     Flatten,
#     Relax,
#     Space
# )


# registering and menu integration
# def register():
#     for cls in classes:
#         bpy.utils.register_class(cls)
#     bpy.types.VIEW3D_MT_edit_mesh_context_menu.prepend(menu_func)
#     bpy.types.WindowManager.looptools = PointerProperty(type=LoopToolsProps)


# # unregistering and removing menus
# def unregister():
#     for cls in reversed(classes):
#         bpy.utils.unregister_class(cls)
#     bpy.types.VIEW3D_MT_edit_mesh_context_menu.remove(menu_func)
#     try:
#         del bpy.types.WindowManager.looptools
#     except Exception as e:
#         print('unregister fail:\n', e)
#         pass