import bpy
import gpu
from gpu_extras.batch import batch_for_shader


_DRAW_HANDLE = None


def _tag_viewports_for_redraw():
	window_manager = getattr(bpy.context, "window_manager", None)
	if window_manager is None:
		return

	for window in window_manager.windows:
		for area in window.screen.areas:
			if area.type == 'VIEW_3D':
				area.tag_redraw()


def _polygon_boundary_edges(mesh):
	edges = set()
	for polygon in mesh.polygons:
		loop_indices = polygon.loop_indices
		for index, loop_index in enumerate(loop_indices):
			next_loop_index = loop_indices[(index + 1) % len(loop_indices)]
			vertex_a = mesh.loops[loop_index].vertex_index
			vertex_b = mesh.loops[next_loop_index].vertex_index
			edges.add(tuple(sorted((vertex_a, vertex_b))))
	return edges


def _triangulation_edges(obj, depsgraph):
	evaluated_obj = obj.evaluated_get(depsgraph)
	mesh = evaluated_obj.to_mesh()
	try:
		mesh.calc_loop_triangles()
		boundary_edges = _polygon_boundary_edges(mesh)
		hidden_edges = set()

		for triangle in mesh.loop_triangles:
			vertices = triangle.vertices
			for index, vertex_a in enumerate(vertices):
				vertex_b = vertices[(index + 1) % 3]
				edge = tuple(sorted((vertex_a, vertex_b)))
				if edge not in boundary_edges:
					hidden_edges.add(edge)

		positions = []
		for vertex_a, vertex_b in hidden_edges:
			positions.extend((
				obj.matrix_world @ mesh.vertices[vertex_a].co,
				obj.matrix_world @ mesh.vertices[vertex_b].co,
			))
		return positions
	finally:
		evaluated_obj.to_mesh_clear()


def _dashed_positions(positions, dash_length, gap_length):
	dashed_positions = []
	for index in range(0, len(positions), 2):
		start = positions[index]
		end = positions[index + 1]
		direction = end - start
		length = direction.length
		if length == 0.0:
			continue

		unit_direction = direction / length
		distance = 0.0
		while distance < length:
			dash_end = min(distance + dash_length, length)
			dashed_positions.extend((
				start + unit_direction * distance,
				start + unit_direction * dash_end,
			))
			distance += dash_length + gap_length
	return dashed_positions


def _draw_hidden_triangulation():
	context = bpy.context
	scene = getattr(context, "scene", None)
	if scene is None or not getattr(scene, "hidden_triangulation_enabled", False):
		return

	depsgraph = context.evaluated_depsgraph_get()
	if getattr(scene, "hidden_triangulation_selected_only", True):
		objects = context.selected_objects
	else:
		objects = scene.objects

	positions = []
	for obj in objects:
		if obj.type == 'MESH' and obj.visible_get():
			positions.extend(_triangulation_edges(obj, depsgraph))

	if not positions:
		return

	positions = _dashed_positions(
		positions,
		scene.hidden_triangulation_dash_length,
		scene.hidden_triangulation_gap_length,
	)
	shader = gpu.shader.from_builtin('UNIFORM_COLOR')
	batch = batch_for_shader(shader, 'LINES', {"pos": positions})
	gpu.state.blend_set('ALPHA')
	gpu.state.depth_test_set('LESS_EQUAL')
	gpu.state.line_width_set(scene.hidden_triangulation_line_width)
	shader.bind()
	shader.uniform_float("color", scene.hidden_triangulation_color)
	batch.draw(shader)
	gpu.state.line_width_set(1.0)
	gpu.state.depth_test_set('NONE')
	gpu.state.blend_set('NONE')


def _set_overlay_enabled(enabled):
	global _DRAW_HANDLE

	if enabled and _DRAW_HANDLE is None:
		_DRAW_HANDLE = bpy.types.SpaceView3D.draw_handler_add(
			_draw_hidden_triangulation, (), 'WINDOW', 'POST_VIEW'
		)
	elif not enabled and _DRAW_HANDLE is not None:
		bpy.types.SpaceView3D.draw_handler_remove(_DRAW_HANDLE, 'WINDOW')
		_DRAW_HANDLE = None

	_tag_viewports_for_redraw()


def hidden_triangulation_enabled_update(self, context):
	_set_overlay_enabled(self.hidden_triangulation_enabled)


def hidden_triangulation_display_update(self, context):
	_tag_viewports_for_redraw()


def sync_hidden_triangulation_overlay():
	scene = getattr(bpy.context, "scene", None)
	_set_overlay_enabled(bool(scene and getattr(scene, "hidden_triangulation_enabled", False)))


def unregister_hidden_triangulation_overlay():
	_set_overlay_enabled(False)


class TMC_OP_ToggleHiddenTriangulation(bpy.types.Operator):
	bl_idname = "tmc.toggle_hidden_triangulation"
	bl_label = "Toggle Hidden Triangulation"
	bl_description = "Show or hide implicit triangulation diagonals in the viewport"

	def execute(self, context):
		context.scene.hidden_triangulation_enabled = not context.scene.hidden_triangulation_enabled
		return {'FINISHED'}