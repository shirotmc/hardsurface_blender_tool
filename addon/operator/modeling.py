import bpy
import bmesh
from mathutils import *
from mathutils import Vector, Matrix
from math import *

from ..ui import controller
from ..utility import variable

#region MAIN FUNCTION

#region set edge length
class TMC_OP_SetEdgeLength(bpy.types.Operator):
	bl_idname = "tmc.set_edge_length"
	bl_label = "Set Edge Length"
	bl_description = 'set current length to selected edge'

	def execute(self, context):
		current_object = bmesh.from_edit_mesh(bpy.context.active_object.data)
		selected_edges = [e for e in current_object.edges if e.select]
		lock_vertex_list = [v for v in current_object.verts if v.index in variable.LOCK_VERTEX_INDEX_LIST]
		bmesh.update_edit_mesh(bpy.context.active_object.data)
		new_length = context.scene.edge_length_value
		for edge in selected_edges:
			current_length = edge.calc_length()
			bpy.ops.mesh.select_all(action = 'DESELECT')
			edge.select = True
			scale = new_length / current_length
			two_vertices = [v for v in edge.verts]
			lock_vertex_current_edge = list(set(two_vertices) & set(lock_vertex_list))
			if len(lock_vertex_current_edge) == 1:
				bpy.ops.transform.resize(value=(scale, scale, scale), center_override = context.active_object.matrix_world @ lock_vertex_current_edge[0].co)
			else:
				bpy.ops.transform.resize(value=(scale, scale, scale))
		return {'FINISHED'}

class TMC_OP_GetEdgeLength(bpy.types.Operator):
	bl_idname = "tmc.get_edge_length"
	bl_label = "Get Edge Length"
	bl_description = 'Get length of current edge'

	def execute(self, context):
		selected_edges = [e for e in bmesh.from_edit_mesh(bpy.context.active_object.data).edges if e.select]
		if len(selected_edges) != 0:
			length_list = []
			for edge in selected_edges:
				length_list.append(edge.calc_length())
			average_length = sum(length_list) / len(length_list)

			controller.update_edge_length_value_ui(context, average_length)
		else:
			controller.show_message(context, "ERROR", "Please select edge!")
		return {'FINISHED'}

class TMC_OP_AddLockVertex(bpy.types.Operator):
	bl_idname = "tmc.add_lock_vertex"
	bl_label = "Add Lock Vertex"
	bl_description = 'Add lock vertex(s) when we set new edge length for them'

	def execute(self, context):
		variable.LOCK_VERTEX_INDEX_LIST = [v.index for v in bmesh.from_edit_mesh(bpy.context.active_object.data).verts if v.select]
		return {'FINISHED'}

class TMC_OP_ClearLockVertex(bpy.types.Operator):
	bl_idname = "tmc.clear_lock_vertex"
	bl_label = "Clear Lock Vertex"
	bl_description = 'Clear lock vertex(s) when we set new edge length for them'

	def execute(self, context):
		variable.LOCK_VERTEX_INDEX_LIST = []
		return {'FINISHED'}

#endregion

#region circle edge
class TMC_OP_CircleEdge(bpy.types.Operator):
	bl_idname = "tmc.circle_edge"
	bl_label = "Circle Edge"
	bl_description = 'make selected edges become arc'

	def execute(self, context):
		CircleVertex_GO(context, 0, context.scene.circle_diameter_toggle, context.scene.circle_angle_toggle, context.scene.circle_diameter_value, context.scene.circle_angle_value)
		return {'FINISHED'}

class TMC_OP_AddPriorityVertex(bpy.types.Operator):
	bl_idname = "tmc.add_priority_vertex"
	bl_label = "add priority vertex"
	bl_description = 'add priority vertex in circle edge'

	def execute(self, context):
		variable.PRIORITY_CIRCLE_VERTEX_INDEX_LIST = [v.index for v in bmesh.from_edit_mesh(bpy.context.active_object.data).verts if v.select]
		return {'FINISHED'}

class TMC_OP_ClearPriorityVertex(bpy.types.Operator):
	bl_idname = "tmc.clear_priority_vertex"
	bl_label = "clear priority vertex"
	bl_description = 'clear priority vertex in circle edge'

	def execute(self, context):
		variable.PRIORITY_CIRCLE_VERTEX_INDEX_LIST = []
		return {'FINISHED'}
	
class TMC_OP_GetCircleDiameter(bpy.types.Operator):
	bl_idname = "tmc.get_circle_diameter"
	bl_label = "get circle diameter"
	bl_description = 'get circle diameter of selected edges'

	def execute(self, context):
		CircleVertex_GO(context, 1, context.scene.circle_diameter_toggle, context.scene.circle_angle_toggle, context.scene.circle_diameter_value, context.scene.circle_angle_value)
		return {'FINISHED'}
	
class TMC_OP_GetCircleAngle(bpy.types.Operator):
	bl_idname = "tmc.get_circle_angle"
	bl_label = "get circle angle"
	bl_description = 'get circle angle of selected edges'

	def execute(self, context):
		CircleVertex_GO(context, 2, context.scene.circle_diameter_toggle, context.scene.circle_angle_toggle, context.scene.circle_diameter_value, context.scene.circle_angle_value)
		return {'FINISHED'}
#endregion

#region straight edge
class TMC_OP_StraightEdge(bpy.types.Operator):
	bl_idname = "tmc.straight_edge"
	bl_label = "straight edge"
	bl_description = 'make the selected edges become straight'

	def execute(self, context):
		axis = context.scene.straight_axis_radiobox
		even_mode = context.scene.even_straight_toggle
		result = StraightLine_GO(context, axis, even_mode)
		if result == 'Loop':
			controller.show_message(context, "ERROR", "Please don't select edge loop!")
		elif result == '<2':
			controller.show_message(context, "ERROR", "Please select more than 1 edge!")
		return {'FINISHED'}
#endregion

#region relax edge
class TMC_OP_RelaxEdge(bpy.types.Operator):
	bl_idname = "tmc.relax_edge"
	bl_label = "relax edge"
	bl_description = 'make the selected edges become relax xD'

	def execute(self, context):
		# initialise
		object, bm = initialise()
		# check cache to see if we can save time
		cached, single_loops, loops, derived, mapping = cache_read("Relax",object, bm, context.scene.relax_input, False)
		if cached:
			derived, bm_mod = get_derived_bmesh(object, bm, False)
		else:
			# find loops
			derived, bm_mod, loops = get_connected_input(object, bm, False, context.scene.relax_input)
			mapping = get_mapping(derived, bm, bm_mod, False, False, loops)
			loops = check_loops(loops, mapping, bm_mod)
		knots, points = relax_calculate_knots(loops)

		# saving cache for faster execution next time
		if not cached:
			cache_write("Relax", object, bm, context.scene.relax_input, False, False, loops, derived, mapping)

		for iteration in range(int(context.scene.relax_iterations)):
			# calculate splines and new positions
			tknots, tpoints = relax_calculate_t(bm_mod, knots, points, context.scene.relax_regular)
			splines = []
			for i in range(len(knots)):
				splines.append(calculate_splines(context.scene.relax_interpolation, bm_mod, tknots[i], knots[i]))
			move = [relax_calculate_verts(bm_mod, context.scene.relax_interpolation, tknots, knots, tpoints, points, splines)]
			move_verts(object, bm, mapping, move, False, context.scene.relax_influence)

		# cleaning up
		if derived:
			bm_mod.free()
		terminate()
		return {'FINISHED'}
#endregion

#region space edge
class TMC_OP_SpaceEdge(bpy.types.Operator):
	bl_idname = "tmc.space_edge"
	bl_label = "space edge"
	bl_description = 'spacing selected edges'

	def execute(self, context):
		# initialise
		object, bm = initialise()
		# check cache to see if we can save time
		cached, single_loops, loops, derived, mapping = cache_read("Space",
			object, bm, context.scene.space_input, False)
		if cached:
			derived, bm_mod = get_derived_bmesh(object, bm, True)
		else:
			# find loops
			derived, bm_mod, loops = get_connected_input(object, bm, True, context.scene.space_input)
			mapping = get_mapping(derived, bm, bm_mod, False, False, loops)
			loops = check_loops(loops, mapping, bm_mod)

		# saving cache for faster execution next time
		if not cached:
			cache_write("Space", object, bm, context.scene.space_input, False, False, loops, derived, mapping)

		move = []
		for loop in loops:
			# calculate splines and new positions
			if loop[1]:  # circular
				loop[0].append(loop[0][0])
			tknots, tpoints = space_calculate_t(bm_mod, loop[0][:])
			splines = calculate_splines(context.scene.space_interpolation, bm_mod, tknots, loop[0][:])
			move.append(space_calculate_verts(bm_mod, context.scene.space_interpolation, tknots, tpoints, loop[0][:-1], splines))
		# move vertices to new locations
		if context.scene.space_lock_x or context.scene.space_lock_y or context.scene.space_lock_z:
			lock = [context.scene.space_lock_x, context.scene.space_lock_y, context.scene.space_lock_z]
		else:
			lock = False
		move_verts(object, bm, mapping, move, lock, context.scene.space_influence)

		# cleaning up
		if derived:
			bm_mod.free()
		terminate()

		cache_delete("Space")
		return {'FINISHED'}
#endregion

#region flatten face
class TMC_OP_FlattenFace(bpy.types.Operator):
	bl_idname = "tmc.flatten_face"
	bl_label = "flatten face"
	bl_description = 'flatten selected face'

	def execute(self, context):
		# initialise
		object, bm = initialise()
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
			com, normal = calculate_plane(bm, loop, method=context.scene.flatten_plane,
				object=object)
			to_move = flatten_project(bm, loop, com, normal)
			if context.scene.flatten_restriction == 'none':
				move.append(to_move)
			else:
				move.append(to_move)

		# move vertices to new locations
		if context.scene.flatten_lock_x or context.scene.flatten_lock_y or context.scene.flatten_lock_z:
			lock = [context.scene.flatten_lock_x, context.scene.flatten_lock_y, context.scene.flatten_lock_z]
		else:
			lock = False
		move_verts(object, bm, False, move, lock, context.scene.flatten_influence)

		# cleaning up
		terminate()
		return {'FINISHED'}
#endregion

#region curve edge
class TMC_OP_CurveEdge(bpy.types.Operator):
	bl_idname = "tmc.curve_edge"
	bl_label = "curve edge"
	bl_description = 'make selected edges become smooth'

	def execute(self, context):
		# initialise
		object, bm = initialise()
		# check cache to see if we can save time
		cached, single_loops, loops, derived, mapping = cache_read("Curve",
			object, bm, False, context.scene.curve_boundaries)
		if cached:
			derived, bm_mod = get_derived_bmesh(object, bm, False)
		else:
			# find loops
			derived, bm_mod, loops = curve_get_input(object, bm, context.scene.curve_boundaries)
			mapping = get_mapping(derived, bm, bm_mod, False, True, loops)
			loops = check_loops(loops, mapping, bm_mod)
		verts_selected = [
			v.index for v in bm_mod.verts if v.select and not v.hide
			]

		# saving cache for faster execution next time
		if not cached:
			cache_write("Curve", object, bm, False, context.scene.curve_boundaries, False,
				loops, derived, mapping)

		move = []
		for loop in loops:
			knots, points = curve_calculate_knots(loop, verts_selected)
			pknots = curve_project_knots(bm_mod, verts_selected, knots,
				points, loop[1])
			tknots, tpoints = curve_calculate_t(bm_mod, knots, points,
				pknots, context.scene.curve_regular, loop[1])
			splines = calculate_splines(context.scene.curve_interpolation, bm_mod,
				tknots, knots)
			move.append(curve_calculate_vertices(bm_mod, knots, tknots,
				points, tpoints, splines, context.scene.curve_interpolation,
				context.scene.curve_restriction))

		# move vertices to new locations
		if context.scene.curve_lock_x or context.scene.curve_lock_y or context.scene.curve_lock_z:
			lock = [context.scene.curve_lock_x, context.scene.curve_lock_y, context.scene.curve_lock_z]
		else:
			lock = False
		move_verts(object, bm, mapping, move, lock, context.scene.curve_influence)

		# cleaning up
		if derived:
			bm_mod.free()
		terminate()

		return {'FINISHED'}

#endregion

#region smooth edge
class TMC_OP_SmoothEdge(bpy.types.Operator):
	bl_idname = "tmc.smooth_edge"
	bl_label = "smooth edge"
	bl_description = 'make selected edges become so smooth'

	def execute(self, context):
		# initialise
		object, bm = initialise()
		# check cache to see if we can save time
		curve_cached, single_loops, loops, derived, mapping = cache_read("Curve",
			object, bm, False, context.scene.curve_boundaries)
		if curve_cached:
			derived, bm_mod = get_derived_bmesh(object, bm, False)
		else:
			# find loops
			derived, bm_mod, loops = curve_get_input(object, bm, context.scene.curve_boundaries)
			mapping = get_mapping(derived, bm, bm_mod, False, True, loops)
			loops = check_loops(loops, mapping, bm_mod)
		verts_selected = [
			v.index for v in bm_mod.verts if v.select and not v.hide
			]

		# saving cache for faster execution next time
		if not curve_cached:
			cache_write("Curve", object, bm, False, context.scene.curve_boundaries, False,
				loops, derived, mapping)

		# Curve Movement
		move = []
		for loop in loops:
			knots, points = curve_calculate_knots(loop, verts_selected)
			pknots = curve_project_knots(bm_mod, verts_selected, knots,
				points, loop[1])
			tknots, tpoints = curve_calculate_t(bm_mod, knots, points,
				pknots, context.scene.curve_regular, loop[1])
			splines = calculate_splines(context.scene.curve_interpolation, bm_mod,
				tknots, knots)
			move.append(curve_calculate_vertices(bm_mod, knots, tknots,
				points, tpoints, splines, context.scene.curve_interpolation,
				context.scene.curve_restriction))

		# move vertices to new locations
		if context.scene.curve_lock_x or context.scene.curve_lock_y or context.scene.curve_lock_z:
			lock = [context.scene.curve_lock_x, context.scene.curve_lock_y, context.scene.curve_lock_z]
		else:
			lock = False
		move_verts(object, bm, mapping, move, lock, context.scene.curve_influence)

		# cleaning up
		if derived:
			bm_mod.free()
		terminate()

		return {'FINISHED'}
#endregion


#region detach element
class TMC_OP_DetachElement(bpy.types.Operator):
	bl_idname = "tmc.detach_element"
	bl_label = "detach element"
	bl_description = 'detach selected element'

	@classmethod
	def poll(cls, context):
		obj = getattr(context, 'active_object', None)
		if not obj or obj.type != 'MESH':
			return False
		# Require Edit Mesh mode
		if getattr(context, 'mode', '') != 'EDIT_MESH':
			return False
		# Require any component selection (vert/edge/face)
		try:
			bm = bmesh.from_edit_mesh(obj.data)
			if any(v.select for v in bm.verts):
				return True
			if any(e.select for e in bm.edges):
				return True
			if any(f.select for f in bm.faces):
				return True
		except Exception:
			# Fallback to mesh data flags in rare cases
			try:
				if any(p.select for p in obj.data.polygons):
					return True
				if any(e.select for e in obj.data.edges):
					return True
				if any(v.select for v in obj.data.vertices):
					return True
			except Exception:
				pass
		return False

	def execute(self, context):
		bpy.ops.mesh.separate(type='SELECTED')
		bpy.ops.object.editmode_toggle()

		new_object = bpy.context.selected_objects[-1]
		bpy.context.active_object.select_set(False)
		bpy.data.objects[new_object.name].select_set(True)
		bpy.data.objects[new_object.name].select_get()
		bpy.context.view_layer.objects.active = bpy.data.objects[new_object.name]
		return {'FINISHED'}
#endregion

#region clone element
class TMC_OP_CloneElement(bpy.types.Operator):
	bl_idname = "tmc.clone_element"
	bl_label = "clone element"
	bl_description = 'clone selected element'

	@classmethod
	def poll(cls, context):
		obj = getattr(context, 'active_object', None)
		if not obj or obj.type != 'MESH':
			return False
		# Require Edit Mesh mode
		if getattr(context, 'mode', '') != 'EDIT_MESH':
			return False
		# Require any component selection (vert/edge/face)
		try:
			bm = bmesh.from_edit_mesh(obj.data)
			if any(v.select for v in bm.verts):
				return True
			if any(e.select for e in bm.edges):
				return True
			if any(f.select for f in bm.faces):
				return True
		except Exception:
			# Fallback to mesh data flags in rare cases
			try:
				if any(p.select for p in obj.data.polygons):
					return True
				if any(e.select for e in obj.data.edges):
					return True
				if any(v.select for v in obj.data.vertices):
					return True
			except Exception:
				pass
		return False

	def execute(self, context):
		bpy.ops.mesh.duplicate()
		bpy.ops.mesh.separate(type='SELECTED')
		bpy.ops.object.editmode_toggle()

		new_object = bpy.context.selected_objects[-1]
		bpy.context.active_object.select_set(False)
		bpy.data.objects[new_object.name].select_set(True)
		bpy.data.objects[new_object.name].select_get()
		bpy.context.view_layer.objects.active = bpy.data.objects[new_object.name]
		return {'FINISHED'}
#endregion

#endregion

#region SUPPORT FUNCTION

#region Circle & Straight functions
###################################

def magnitude(vector): 
	return sqrt(sum(pow(element, 2) for element in vector))

def GetVectorFromPointAndPlane(a, nm, P):
	d = -a.x*nm.x-a.y*nm.y-a.z*nm.z
	lmn = (nm.x*nm.x + nm.y*nm.y + nm.z*nm.z)
	x1 = (P.x*(nm.y*nm.y + nm.z*nm.z)-(P.y*nm.y + P.z*nm.z+d)*nm.x) / lmn
	y1 = (P.y*(nm.z*nm.z + nm.x*nm.x)-(P.z*nm.z + P.x*nm.x+d)*nm.y) / lmn
	z1 = (P.z*(nm.x*nm.x + nm.y*nm.y)-(P.x*nm.x + P.y*nm.y+d)*nm.z) / lmn
	Q = Vector((x1, y1, z1))
	return Q

def GetVertexPosOnStraightLine(a1, a2, b1):
	a3 = Vector((a2.x - a1.x , a2.y - a1.y , a2.z - a1.z))
	t = (-1*(a1.x - b1.x) * a3.x - (a1.y - b1.y) * a3.y - (a1.z - b1.z) * a3.z ) / (a3.x * a3.x + a3.y * a3.y + a3.z * a3.z)
	c1 = Vector(((a3.x * t + a1.x), (a3.y * t + a1.y),(a3.z*t + a1.z)))
	return c1

def GetEvenVertexPosOnStraightLine(a1, a2, ver_num, ver_index):
	a3 = Vector((a2.x - a1.x , a2.y - a1.y , a2.z - a1.z))
	d = magnitude(a3) * ver_index / (float)(ver_num - 1)
	t = d / sqrt(a3.x * a3.x + a3.y * a3.y + a3.z * a3.z)
	c1 = a1 + a3 * t
	return c1	

def GetVectorFromPoints(a, b, c, P):
	ab = b-a
	ac = c-a
	nm = ab.cross(ac)
	d = -a.x*nm.x-a.y*nm.y-a.z*nm.z
	lmn = (nm.x*nm.x + nm.y*nm.y + nm.z*nm.z)
	x1 = (P.x*(nm.y*nm.y + nm.z*nm.z)-(P.y*nm.y + P.z*nm.z+d)*nm.x) / lmn
	y1 = (P.y*(nm.z*nm.z + nm.x*nm.x)-(P.z*nm.z + P.x*nm.x+d)*nm.y) / lmn
	z1 = (P.z*(nm.x*nm.x + nm.y*nm.y)-(P.x*nm.x + P.y*nm.y+d)*nm.z) / lmn
	Q = Vector((x1, y1, z1))
	return Q

def GetRotPosition(pos, rotRad, mode):
	if (mode==0): 
		rotPos = Vector((pos.x, pos.y*cos(rotRad) - pos.z*sin(rotRad), pos.y*sin(rotRad) + pos.z*cos(rotRad)))
	if (mode==1): 
		rotPos = Vector((pos.z*sin(rotRad) + pos.x*cos(rotRad), pos.y, pos.z*cos(rotRad) - pos.x*sin(rotRad)))
	if (mode==2): 
		rotPos = Vector((pos.x*cos(rotRad) - pos.y*sin(rotRad), pos.x*sin(rotRad) + pos.y*cos(rotRad), pos.z))
	return rotPos

def QuaternionMultiplication(Q, R):
	quater = [0,0,0,0]
	t1 = Q[0]
	V1 = Vector((Q[1],Q[2],Q[3]))
	t2 = R[0]
	V2 = Vector((R[1],R[2],R[3]))
	quater[0] = t1 * t2 - V1.dot(V2)
	vec = (t1 * V2) + (t2 * V1) + V1.cross(V2)
	quater[1] = vec.x
	quater[2] = vec.y
	quater[3] = vec.z
	return quater

def QuaternionRotate(p, v, rad):
	P = [0, p.x, p.y, p.z]
	Q = [cos(rad/2), (v.x)*sin(rad/2), (v.y)*sin(rad/2), (v.z)*sin(rad/2)]
	R = [cos(rad/2), -(v.x)*sin(rad/2), -(v.y)*sin(rad/2), -(v.z)*sin(rad/2)]
	PQR = QuaternionMultiplication(R, P)
	PQR = QuaternionMultiplication(PQR, Q)
	moveP = Vector((PQR[1],PQR[2],PQR[3]))
	return moveP

def QuaternionRotateArray(pList, v, rad):
	afterPos = []
	for i in range(0, len(pList)):
		afterPos.append(QuaternionRotate(pList[i], v, rad))
	return afterPos

def DistancePos(pos0, pos1):
	dis = ((pos1.x)-(pos0.x))*((pos1.x)-(pos0.x)) + ((pos1.y)-(pos0.y))*((pos1.y)-(pos0.y)) + ((pos1.z)-(pos0.z))*((pos1.z)-(pos0.z))
	dis = sqrt(dis)
	return dis

def GetEdgeList(getList_edges, verMode):
	getList_vertex = []
	for i in range(0, len(getList_edges)):
		selected_vertices = [v for v in getList_edges[i].verts]
		getList_vertex += selected_vertices

	sort_edgeList = []
	sort_vertexList = []
	for i in range(0, len(getList_edges)):
		if getList_edges[i] in sort_edgeList:
			continue

		workEdgeList = []
		workVertexList = []
		loopTrue = False

		for k in range(0, 2):
			nowEdge = getList_edges[i]
			nowVertex = getList_vertex[i*2+k]
			n = 0
			if nowVertex not in sort_vertexList:
				if len(workVertexList) == 0:
					workVertexList.append(nowVertex)
				else:
					workVertexList[0] = nowVertex
				beforeEdge = nowVertex
				while (n < 100000):
					for j in range(0, len(getList_edges)):
						if getList_edges[j] == nowEdge:
							continue
						if getList_edges[j] in workEdgeList:
							continue
						if getList_edges[j] in sort_edgeList:
							continue
						verNum2=j*2
						if nowVertex == getList_vertex[verNum2]:
							nowEdge = getList_edges[j]
							nowVertex = getList_vertex[verNum2+1]
							if nowVertex not in workVertexList:
								workEdgeList.append(nowEdge)
								workVertexList.append(nowVertex)
							else:
								loopTrue = True
							break
						if nowVertex == getList_vertex[verNum2+1]:
							nowEdge = getList_edges[j]
							nowVertex = getList_vertex[verNum2]
							if nowVertex not in workVertexList:
								workEdgeList.append(nowEdge)
								workVertexList.append(nowVertex)

							else:
								loopTrue = True
							break

					if beforeEdge == nowVertex:
						break
					beforeEdge = nowVertex
					n += 1

			plusEdge_Work = workEdgeList
			plusVertex_Work = workVertexList

			if k==0:
				plusEdge_Work.reverse()
				plusVertex_Work.reverse()

			sort_edgeList = sort_edgeList + plusEdge_Work
			sort_vertexList = sort_vertexList + plusVertex_Work
			if k==0:
				if len(plusEdge_Work) != 0:
					if plusEdge_Work[0] != getList_edges[i]:
						sort_edgeList.append(getList_edges[i])
					else:
						loopTrue = True
				else:
					sort_edgeList.append(getList_edges[i])
			else:
				sepaString = "--"
				if loopTrue:
					sepaString = "--Loop"
				sort_edgeList.append(sepaString)
				sort_vertexList.append(sepaString)

			workEdgeList = []
			workVertexList = []

	if (verMode):
		return sort_vertexList
	else:
		return sort_edgeList
	
def VectorAve(vectorList):
	totalVal= Vector((0,0,0))
	for vec in vectorList:
		totalVal = totalVal+vec
	aveVal = totalVal/len(vectorList)
	return aveVal

def VectorMaxMinAve(vectorList):
	firstPos = vectorList[0]
	maxX = firstPos.x
	maxY = firstPos.y
	maxZ = firstPos.z
	minX = firstPos.x
	minY = firstPos.y
	minZ = firstPos.z
	for vec in vectorList:
		if (maxX < vec.x):
			maxX = vec.x
		if (maxY < vec.y):
			maxY = vec.y
		if (maxZ < vec.z):
			maxZ = vec.z
		if (minX > vec.x):
			minX = vec.x
		if (minY > vec.y):
			minY = vec.y
		if (minZ > vec.z):
			minZ = vec.z
	aveVal = Vector((((minX+maxX)/2.0),((minY+maxY)/2.0),((minZ+maxZ)/2.0)))
	return aveVal

def AlignmentCircle(vertexList, distanceInput, moveMode, priority_vertex_list):
	vertexPosList = [vert.co for vert in vertexList] 
	
	centerPos = VectorMaxMinAve(vertexPosList)

	vectorList = []
	triangleNormal = []
	for i in range(0, len(vertexPosList)):
		vec1 = vertexPosList[i]-centerPos
		vectorList.append(vec1)
		if (i+1<len(vertexPosList)):
			vec2 = vertexPosList[i+1] - centerPos
		else:
			vec2 = vertexPosList[0] - centerPos
		triangleNormal.append(vec1.cross(vec2))
		triangleNormal[i] = triangleNormal[i].normalized()
	
	centerNormal = VectorAve(triangleNormal)
	centerNormal = centerNormal.normalized()
	if (distanceInput == 0 or moveMode == 1):
		distanceTotal = 0
		for i in range(0, len(vertexPosList)):
			distanceTotal = distanceTotal + DistancePos(centerPos,vertexPosList[i])
		distance = distanceTotal/len(vertexPosList)
	else:
		distance = distanceInput

	if (moveMode==1):
		return distance
	if(moveMode==0):
		fixVerNumber = 0
		priorityVerTrue = False
		priorityVer = None

		for i in range(0, len(vertexList)):
			if vertexList[i] in priority_vertex_list:
				priorityVerTrue = True
				priorityVer = vertexList[i]
				fixVerNumber = i
	
		if priorityVer != None:
			pass
		
		minAngle = 3.15
		minVerNum = 0
		axisX = Vector((1,0,0))
		axisY = Vector((0,1,0))
		axisZ = Vector((0,0,-1))
		axisAngle = 0
		axis = axisY
		for i in range(0, len(vectorList)):
			axisAngle = axis.angle(vectorList[i])
			if (minAngle > axisAngle):
				minVerNum = i
				minAngle  = axisAngle

		horizTrue = 0
		angleAbout = 0.01
		inextNum = 0
		if not priorityVerTrue:
			nextNum = minVerNum - 1
			if (nextNum<0):
				nextNum = len(vectorList)-1
			axisAngle = axis.angle(vectorList[nextNum])
			if (minAngle < axisAngle + angleAbout and minAngle > axisAngle - angleAbout):
				horizTrue = 1	
			nextNum = minVerNum + 1
			
			if (len(vectorList) <= nextNum):
				nextNum = 0
			axisAngle = axis.angle(vectorList[nextNum])
			if (minAngle < axisAngle + angleAbout and minAngle > axisAngle - angleAbout):
				horizTrue = 2
			fixVerNumber = minVerNum

		verListSort_num = []
		verListSort_pos = []
		sortCounter = 0
		i=0
		while (sortCounter < len(vertexList)):
			if (vertexList[i]==vertexList[fixVerNumber] or sortCounter != 0):
				verListSort_num.append(vertexList[i])
				verListSort_pos.append(vertexPosList[i])
				sortCounter += 1
			i+=1
			if (i >= len(vertexList)):
				i = i - len(vertexList)

		movePosList = []
		basePosList = []
		verTotal = len(verListSort_num)
		rot = 360.0 / verTotal
		for i in range(0, verTotal):	
			rad = radians(rot*i)
			x = distance * sin(rad)
			y = distance * cos(rad)
			basePosList.append(Vector((x, y, 0)))
		
		baseNormal = Vector((0, 0 ,-1))
		movePosList = basePosList
		normalCross = baseNormal.cross(centerNormal)
		normalAngle = baseNormal.angle(centerNormal)
		normalCross = normalCross.normalized()
		if (normalCross.x==0 and normalCross.y==0 and normalCross.z==0):
			normalCross = Vector((1,0,0))
		
		fixPosLocal  = verListSort_pos[0] - centerPos
		reMovefixPos = QuaternionRotate(fixPosLocal, normalCross, normalAngle)
		fixPosFrontVector = Vector(((reMovefixPos.x), (reMovefixPos.y) ,0))
		fixCross =  basePosList[0].cross(fixPosFrontVector)
		fixAngle = basePosList[0].angle(fixPosFrontVector)
		if (fixCross.z < 0):
			fixAngle = fixAngle * -1
		for i in range(0, len(movePosList)):
			movePosList[i] = GetRotPosition(movePosList[i], fixAngle, 2)
		
		movePosList = QuaternionRotateArray(movePosList, normalCross, -normalAngle)
		for i in range(0, len(verListSort_num)):
			movePos = movePosList[i]
			movePos = movePos + centerPos
			verListSort_num[i].co = movePos

	if(moveMode==4):
		for i in range(0, len(vertexList)):
			vertexPosList[i] = vertexList[i].co
			planePos = GetVectorFromPointAndPlane(centerPos, centerNormal, vertexPosList[i])
			pointNormal = planePos - centerPos
			pointNormal = pointNormal.normalized()
			movePos = (pointNormal * distance) + centerPos
			vertexList[i].co = movePos

	bmesh.update_edit_mesh(bpy.context.active_object.data)
	return distance

def AlignmentSemicircle(vertexList, inputAngle, moveMode):
	if len(vertexList) <= 2:
		return 0
	vertexPosList = [vert.co for vert in vertexList]

	target_first_pos = vertexPosList[0]
	target_end_pos   = vertexPosList[len(vertexPosList)-1]
	target_vector    = target_end_pos - target_first_pos
	centerPos = VectorMaxMinAve(vertexPosList)
	vectorList = []
	triangleNormal = []

	for i in range(0, len(vertexPosList)):
		vec1 = vertexPosList[i] - centerPos
		vectorList.append(vec1)
		if (i+1 < len(vertexPosList)):
			vec2 = vertexPosList[i+1] - centerPos
		else:
			vec2 = vertexPosList[0] - centerPos

		triangleNormal.append(vec1.cross(vec2))

	centerNormal = VectorAve(triangleNormal)

	if (inputAngle == 0 or moveMode == 2):
		angleTotal_rad = 0
		for i in range(1, len(vertexPosList)-1):
			angleTotal_rad = angleTotal_rad + (vertexPosList[i] - target_first_pos).angle(vertexPosList[i] - target_end_pos)
		
		angleAbe_rad = angleTotal_rad / (len(vertexPosList)-2)
		angleAbe_deg = degrees(angleAbe_rad)
		angleAbe_deg = 360 - (angleAbe_deg * 2)
		inputAngle = angleAbe_deg

	distance = 1
	radAngle = radians((360-inputAngle) / 2.0)
	firstEndPosDistance = DistancePos(target_first_pos, target_end_pos)
	distance = (firstEndPosDistance/2) / sin(radAngle)
	if (moveMode == 1): 
		return distance
	if (moveMode == 2):
		return inputAngle
	basePosList = []
	movePosList = []
	verTotal = len(vertexList)
	rot = 0
	rot = inputAngle / (verTotal-1)
	for i in range(0, verTotal):
		rad = radians(rot*i + 180-(inputAngle/2.0))
		x = distance * sin(rad)
		y = distance * cos(rad)
		current_vector = Vector((x, y, 0))
		basePosList.append(current_vector)
	

	baseNormal = Vector((0, 0 , -1))
	base_vector = Vector((-1, 0 , 0))
	movePosList = basePosList
	vector_cross = base_vector.cross(target_vector)
	vector_angle = base_vector.angle(target_vector)
	vector_cross = vector_cross.normalized()

	if (vector_cross.x == 0 and vector_cross.y == 0 and vector_cross.z==0):
		vector_cross = Vector((0, 0, 1))

	rotTargetVec = QuaternionRotate(centerNormal, vector_cross, vector_angle)

	rotTargetFrontVec = Vector((0, (rotTargetVec.y) ,(rotTargetVec.z)))
	first_cross =  baseNormal.cross(rotTargetFrontVec)
	first_angle = baseNormal.angle(rotTargetFrontVec)
	if (first_cross.x<0):
		first_angle = first_angle * -1
	for i in range(0, len(movePosList)):
		movePosList[i] = GetRotPosition(movePosList[i], first_angle, 0)

	movePosList = QuaternionRotateArray(movePosList, vector_cross, -vector_angle)

	translateVal = target_first_pos - movePosList[0]
	for i in range(0, len(vertexList)):
		movePosList[i] = movePosList[i] + translateVal
	
	for i in range(0, len(vertexList)):
		vertexList[i].co = movePosList[i]

	bmesh.update_edit_mesh(bpy.context.active_object.data)
	return distance

def CircleVertex_GO(context, moveMode, averageDistanceModeTrue, averageDistanceAngleTrue, averageDistance, averageAngle):
	distance = 0
	angle = 0
	if averageDistanceModeTrue:
		distance = averageDistance
	else:
		distance = 0

	if averageDistanceAngleTrue:
		angle = averageAngle
	else:
		angle = 0
	
	distance = distance / 2.0
	current_object = bmesh.from_edit_mesh(bpy.context.active_object.data)
	selected_edges = [e for e in current_object.edges if e.select]
	priority_vertex_list = [v for v in current_object.verts if v.index in variable.PRIORITY_CIRCLE_VERTEX_INDEX_LIST]

	sortVerList = []
	if len(selected_edges) > 0:
		sortVerList = GetEdgeList(selected_edges, 1)

	vertexList = []
	distanceTotal = 0
	totalDisCounter = 0
	angleTotal = 0
	totalAngCounter = 0

	for ver in sortVerList:
		if (ver == "--Loop"):
			getDis = AlignmentCircle(vertexList, distance, moveMode, priority_vertex_list)
			vertexList = []
			distanceTotal = distanceTotal + getDis
			totalDisCounter += 1
			continue
		if (ver == "--"):
			getAng = AlignmentSemicircle(vertexList, angle, moveMode)
			vertexList = []
			angleTotal = angleTotal + getAng
			totalAngCounter += 1
			continue
		vertexList.append(ver)
	
	if (totalDisCounter != 0):
		distanceAve = distanceTotal / totalDisCounter * 2
		if (moveMode==1):
			controller.update_circle_diameter_value_ui(context, distanceAve)
	if (totalAngCounter != 0):
		angleAve = angleTotal / totalAngCounter
		if(moveMode==2):
			controller.update_circle_angle_value_ui(context, angleAve)

def StraightLine_GO(context, axis, even_mode):
	current_object = bmesh.from_edit_mesh(bpy.context.active_object.data)
	selected_edges = [e for e in current_object.edges if e.select]

	sortVerList = []
	if len(selected_edges) > 1:
		sortVerList = GetEdgeList(selected_edges, 1)
	else:
		return '<2'

	if "--Loop" in sortVerList:
		return 'Loop'

	vertexList = []
	counter = -1

	for i in range(0, len(sortVerList)):
		if sortVerList[i] == "--":
			continue
		if counter == -1:
			pos1 = sortVerList[i].co
			counter += 1
			continue
		if sortVerList[i+1] == "--":
			pos2 = sortVerList[i].co
			MakeStraightLine(vertexList, axis, even_mode, pos1, pos2)
			vertexList = []
			counter = -1
			continue
		vertexList.append(sortVerList[i])
		counter += 1

	return ''

def MakeStraightLine(vertex_list, axis, even_mode, pos1, pos2):
	if axis == 'All':
		save_ver_pos1 = pos1
		save_ver_pos2 = pos2
		ver_index = 1
		ver_num = len(vertex_list) + 2
		for ver in vertex_list:
			pos = ver.co
			loop_pos = pos
			if not even_mode:
				move_pos_vector=GetVertexPosOnStraightLine(save_ver_pos1, save_ver_pos2, loop_pos)
			else:
				move_pos_vector=GetEvenVertexPosOnStraightLine(save_ver_pos1, save_ver_pos2, ver_num, ver_index)
			ver.co = move_pos_vector
			ver_index += 1
	else:
		if axis == 'X':
			xx = 2
			yy = 1
		elif axis == 'Y':
			xx = 0
			yy = 2
		elif axis == 'Z':
			xx = 0
			yy = 1
		
		inclination = 1
		a = 0
		if pos1[xx] - pos2[xx] != 0:
			a = (pos1[yy] - pos2[yy]) / (pos1[xx] - pos2[xx])
			b = pos2[yy] - a * pos2[xx]
		else:
			move_pos1 = pos1[xx]
			inclination = 0
		
		for ver in vertex_list:
			pos = ver.co
			if a != 0:
				a2 = -1 / a
				b2 = pos[yy] - a2 * pos[xx]
				move_pos1 = (b2 - b) / (a - a2)
				move_pos2 = a * move_pos1 + b
			else:
				if inclination != 0:
					move_pos1 = pos[xx]
					move_pos2 = b
				else:
					move_pos2 = pos[yy]
			if xx == 0 and yy == 1:
				ver.co.x = move_pos1
				ver.co.y = move_pos2
			if xx == 0 and yy == 2:
				ver.co.x = move_pos1
				ver.co.z = move_pos2
			if xx == 2 and yy == 1:
				ver.co.z = move_pos1
				ver.co.y = move_pos2
	bmesh.update_edit_mesh(bpy.context.active_object.data)

#endregion

#region LoopTool functions
##########################

# gather initial data
looptools_cache = {}

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

# clean up and set settings back to original state
def terminate():
	# update editmesh cached data
	obj = bpy.context.active_object
	if obj.mode == 'EDIT':
		bmesh.update_edit_mesh(obj.data, loop_triangles=True, destructive=True)

# store information in the cache
def cache_write(tool, object, bm, input_method, boundaries, single_loops, loops, derived, mapping):
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

# force a full recalculation next time
def cache_delete(tool):
	if tool in looptools_cache:
		del looptools_cache[tool]

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
		[v.index, Vector(v.co[:]) -
		(Vector(v.co[:]) - com).dot(normal) * normal] for v in verts
		]

	return(verts_projected)

# calculate a best-fit plane to the given vertices
def calculate_plane(bm_mod, loop, method="best_fit", object=False):
	# getting the vertex locations
	locs = [bm_mod.verts[v].co.copy() for v in loop[0]]
	# calculating the center of mass
	com = Vector()
	for loc in locs:
		com += loc
	com /= len(locs)

	if method == 'best_fit':
		# getting active face
		if bm_mod.select_history:
			elem = bm_mod.select_history[-1]
		face = [f for f in bm_mod.faces if f.index == elem.index][0]
		selected_locs = [bm_mod.verts[v.index].co.copy() for v in face.verts]
		com = Vector()
		for loc in selected_locs:
			com += loc
		com /= len(selected_locs)
		normal = face.normal

	elif method == 'normal':
		# averaging the vertex normals
		v_normals = [bm_mod.verts[v].normal for v in loop[0]]
		normal = Vector()
		for v_normal in v_normals:
			normal += v_normal
		normal /= len(v_normals)
		normal.normalize()

	elif method == 'view':
		# calculate view normal
		rotation = bpy.context.space_data.region_3d.view_matrix.to_3x3().\
			inverted()
		normal = rotation @ Vector((0.0, 0.0, 1.0))
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

# move the vertices to their new locations
def move_verts(object, bm, mapping, move, lock, influence):
	if lock:
		lock_x, lock_y, lock_z = lock
		orient_slot = bpy.context.scene.transform_orientation_slots[0]
		custom = orient_slot.custom_orientation
		if custom:
			mat = custom.matrix.to_4x4().inverted() @ object.matrix_world.copy()
		elif orient_slot.type == 'LOCAL':
			mat = Matrix.Identity(4)
		elif orient_slot.type == 'VIEW':
			mat = bpy.context.region_data.view_matrix.copy() @ \
				object.matrix_world.copy()
		else:  # orientation == 'GLOBAL'
			mat = object.matrix_world.copy()
		mat_inv = mat.inverted()

	# get all mirror vectors
	mirror_Vectors = []
	if object.data.use_mirror_x:
		mirror_Vectors.append(Vector((-1, 1, 1)))
	if object.data.use_mirror_y:
		mirror_Vectors.append(Vector((1, -1, 1)))
	if object.data.use_mirror_x and object.data.use_mirror_y:
		mirror_Vectors.append(Vector((-1, -1, 1)))
	z_mirror_Vectors = []
	if object.data.use_mirror_z:
		for v in mirror_Vectors:
			z_mirror_Vectors.append(Vector((1, 1, -1)) * v)
		mirror_Vectors.extend(z_mirror_Vectors)
		mirror_Vectors.append(Vector((1, 1, -1)))

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

# returns the edgekeys of a bmesh face
def face_edgekeys(face):
	return([tuple(sorted([edge.verts[0].index, edge.verts[1].index])) for edge in face.edges])

# return the edgekey ([v1.index, v2.index]) of a bmesh edge
def edgekey(edge):
	return(tuple(sorted([edge.verts[0].index, edge.verts[1].index])))

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

#endregion

#region Relax functions
########################

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
			loc = Vector(bm_mod.verts[m[1]].co[:])
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
				change.append([p, Vector([x, y, z])])
			else:  # interpolation == 'linear'
				a, d, t, u = splines[i][n]
				if u == 0:
					u = 1e-8
				change.append([p, ((m - t) / u) * d + a])
	for c in change:
		move.append([c[0], (bm_mod.verts[c[0]].co + c[1]) / 2])

	return(move)

#endregion

#region Space functions
#######################

# calculate relative positions compared to first knot
def space_calculate_t(bm_mod, knots):
	tknots = []
	loc_prev = False
	len_total = 0
	for k in knots:
		loc = Vector(bm_mod.verts[k].co[:])
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
			move.append([p, Vector([x, y, z])])
		else:  # interpolation == 'linear'
			a, d, t, u = splines[n]
			move.append([p, ((m - t) / u) * d + a])

	return(move)
#endregion

#region Curve functions
#######################
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
            loc = Vector(bm_mod.verts[p].co[:])
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
            newloc = Vector([x, y, z])
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
                if dloc.angle(normal, 0) < 0.5 * pi + 1e-6:
                    move.append([p, newloc])
            else:  # restriction == 'indent' only indentations
                if dloc.angle(normal) > 0.5 * pi - 1e-6:
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
        pknots = [Vector(bm_mod.verts[knots[0]].co[:])]
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
                knot_left = Vector(bm_mod.verts[knot_left].co[:])
                knot_right = Vector(bm_mod.verts[knot_right].co[:])
                knot = Vector(bm_mod.verts[knot].co[:])
                pknots.append(project(knot_left, knot_right, knot))
            else:
                pknots.append(Vector(bm_mod.verts[knot].co[:]))
        else:  # knot isn't selected, so shouldn't be changed
            pknots.append(Vector(bm_mod.verts[knot].co[:]))
    if not circular:
        pknots.append(Vector(bm_mod.verts[knots[-1]].co[:]))

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


#endregion

#endregion