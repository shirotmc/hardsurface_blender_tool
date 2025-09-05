import bpy
from ..ui.controller import *

class TMC_UIProperty(bpy.types.PropertyGroup):

	bpy.types.Scene.menu_tab = bpy.props.EnumProperty(
		name="Tool Tab",
		description="menu tab for specific function",
		items=(("MODEL", "Model", "Model Function", "MESH_CUBE", 0),
				("MODIFIER", "Modifier", "Modifier Function", "MODIFIER", 1),
				("MISC", "Misc", "Misc Function", "SCENE_DATA", 2),		
				("CHECK", "Check", "Check Function", "CHECKMARK", 3),	
				("BRIDGE", "Bridge", "Software Bridge", "UV_SYNC_SELECT", 4),
				("CAPTURE", "Capture", "Capture Function", "RESTRICT_RENDER_OFF", 5)))

	## Modifier
	bpy.types.Scene.toggle_apply_modifier_ui = bpy.props.BoolProperty(
		name="Enable Toggle & Apply Modifier UI",
		default=False
	)

	bpy.types.Scene.toggle_subdivision_modifier_ui = bpy.props.BoolProperty(
		name="Enable Subdivision Modifier UI",
		default=False
	)

	bpy.types.Scene.toggle_bevel_modifier_ui = bpy.props.BoolProperty(
		name="Enable Bevel Modifier UI",
		default=False
	)

	bpy.types.Scene.toggle_mirror_modifier_ui = bpy.props.BoolProperty(
		name="Enable Mirror Modifier UI",
		default=False
	)


	## Model
	bpy.types.Scene.toggle_edge_length_ui = bpy.props.BoolProperty(
		name="Enable Edge Length UI",
		default=False
	)

	bpy.types.Scene.toggle_circle_edge_ui = bpy.props.BoolProperty(
		name="Enable Circle Edge UI",
		default=False
	)

	bpy.types.Scene.toggle_straight_edge_ui = bpy.props.BoolProperty(
		name="Enable Circle Edge UI",
		default=False
	)

	bpy.types.Scene.toggle_relax_edge_ui = bpy.props.BoolProperty(
		name="Enable Relax Edge UI",
		default=False
	)

	bpy.types.Scene.toggle_space_edge_ui = bpy.props.BoolProperty(
		name="Enable Space Edge UI",
		default=False
	)

	bpy.types.Scene.toggle_flatten_face_ui = bpy.props.BoolProperty(
		name="Enable Flatten Face UI",
		default=False
	)

	bpy.types.Scene.toggle_collection_area_ui = bpy.props.BoolProperty(
		name="Enable Collection UI",
		default=False
	)

	bpy.types.Scene.toggle_normal_area_ui = bpy.props.BoolProperty(
		name="Enable Normal UI",
		default=False
	)

	bpy.types.Scene.toggle_vertex_group_area_ui = bpy.props.BoolProperty(
		name="Enable Vertex Group UI",
		default=False
	)

	bpy.types.Scene.toggle_material_area_ui = bpy.props.BoolProperty(
		name="Enable Material UI",
		default=False
	)

	bpy.types.Scene.toggle_uv_area_ui = bpy.props.BoolProperty(
		name="Enable UV UI",
		default=False
	)

	bpy.types.Scene.toggle_bakeset_area_ui = bpy.props.BoolProperty(
		name="Enable Bake Set UI",
		default=False
	)

	bpy.types.Scene.toggle_coalition_area_ui = bpy.props.BoolProperty(
		name="Enable Coalition UI",
		default=False
	)

	# --- UI Element Props --- #

	#region File
	bpy.types.Scene.blender_maya_normal_radiobox = bpy.props.EnumProperty(
	name="Normal",
	items=(("Lock", "Lock", "Lock", "", 0),
	("Unlock", "Unlock", "Unlock", "", 1))
	)

	bpy.types.Scene.rizom_path = bpy.props.StringProperty(
	name="",
	description="Rizom path",
	subtype='FILE_PATH',
	update=update_rizom_path_ui)
	#endregion

	#region Bevel
	bpy.types.Scene.bevel_unit_value = bpy.props.FloatProperty(
		name="Bevel Unit Value",
		description=":",
		precision=3,
		min=0.001,
		step=0.001,
		default=0.001,
		update=bevel_value_ui_change)
	
	bpy.types.Scene.bevel_segment_value = bpy.props.IntProperty(
		name="Bevel Segment Value",
		description=":",
		min=1,
		max=100,
		default=1,
		update=bevel_segment_ui_change)

	bpy.types.Scene.bevel_type = bpy.props.EnumProperty(name="Type",
		items=(("VGROUP", "Vertex Group", "Use bevel weights to determine how much bevel is applied in edge mode."),
				("WEIGHT", "Weight", "Use vertex group weights to select whether vertex or edge is beveled."),
				("ANGLE", "Angle", "Only bevel edges with sharp enough angles between faces.")),
		description="Select bevel type",
		update=update_bevel_modifier_name_ui
	)
	#endregion

	#region UVset
	bpy.types.Scene.uvset1_name = bpy.props.StringProperty(
		name="UVSet1 Name",
		description=":",
		default="map1",
		maxlen=1024)
	#endregion
	
	#region Mirror
	bpy.types.Scene.current_mirror_object_name = bpy.props.StringProperty(
		name="Current Mirror Object Name",
		description=":",
		default="",
		maxlen=1024)
	
	bpy.types.Scene.target_mirror_object_name = bpy.props.StringProperty(
		name="Target Mirror Object Name",
		description=":",
		default="",
		maxlen=1024)
	#endregion

	#region Vertex group
	bpy.types.Scene.bevel_modifier_name = bpy.props.StringProperty(
		name="Bevel Modifier Name",
		description=":",
		default="BevelV",
		maxlen=1024)
	#endregion

	#region Check
	bpy.types.Scene.check_ngons_face = bpy.props.BoolProperty(
		name="Check N-gons Face Result",
		description="Show n-gons face checking result",
		default = True
		)

	bpy.types.Scene.check_intersect_face = bpy.props.BoolProperty(
		name="Check Intersect Face Result",
		description="Show intersect face checking result",
		default = True
		)

	bpy.types.Scene.check_non_manifold = bpy.props.BoolProperty(
		name="Check Non-Manifold Result",
		description="Show non-manifold checking result",
		default = True
		)

	bpy.types.Scene.check_zero_edge_length = bpy.props.BoolProperty(
		name="Check Zero Edge Length Result",
		description="Show zero edge length checking result",
		default = True
		)

	bpy.types.Scene.check_zero_face_area = bpy.props.BoolProperty(
		name="Check Tiny Edge Leg Result",
		description="Show zero face area checking result",
		default = True
		)

	bpy.types.Scene.check_isolated_vertex = bpy.props.BoolProperty(
		name="Check Isolated Vertex Result",
		description="Show isolated vertex checking result",
		default = True
		)

	bpy.types.Scene.viewport_background_color = bpy.props.FloatVectorProperty(
		name="Colour",
		subtype='COLOR',
		default=(0.188, 0.188, 0.188))
	#endregion

	#region Bake set
	bpy.types.Scene.export_bakeset_unlock_normal = bpy.props.BoolProperty(
		name="Unlock Normal Checkbox",
		description="On/Off Unlock Normal",
		default = False
		)

	bpy.types.Scene.export_bakeset_mode = bpy.props.EnumProperty(
		name="Export Mode",
		items=[
		('Single', 'Single File', 'Single', '', 0),
		('Multiple', 'Multiple Files', 'Multiple', '', 1),
		],
		default='Multiple')


	bpy.types.Scene.bakeset_name = bpy.props.StringProperty(
		name="BakeSet Name",
		description=":",
		default="BakeSet",
		maxlen=1024)
	
	bpy.types.Scene.threshold_value = bpy.props.FloatProperty(
		name="High/Low Threshold Value",
		description=":",
		default=0.01)
	
	bpy.types.Scene.bakeset_export_path = bpy.props.StringProperty(
		name="Path",
		description="Export FBX Path",
		default="D:/",
		subtype='FILE_PATH',
		update=update_bakeset_export_path_ui)
	#endregion


	#region check properties
	bpy.types.Scene.min_edge_length_value = bpy.props.FloatProperty(
		name="Min Edge Length Value",
		description=":",
		precision=4,
		default=0.001)

	bpy.types.Scene.min_face_area_value = bpy.props.FloatProperty(
		name="Min Face Area Value",
		description=":",
		precision=7,
		default=0.00001)
	#endregion

	#region edge length properties
	bpy.types.Scene.edge_length_value = bpy.props.FloatProperty(
		name="Edge Length Value",
		description=":",
		default=0.0)
	#endregion

	#region circle properties

	bpy.types.Scene.circle_diameter_toggle = bpy.props.BoolProperty(
		name="Diameter Checkbox",
		description="On/Off Diameter Input",
		default = False
		)

	bpy.types.Scene.circle_angle_toggle = bpy.props.BoolProperty(
		name="Angle Checkbox",
		description="On/Off Angle Input",
		default = False
		)

	bpy.types.Scene.circle_diameter_value = bpy.props.FloatProperty(
		name="Diameter Value",
		description="Diameter Value",
		default=1
		)
		
	bpy.types.Scene.circle_angle_value = bpy.props.FloatProperty(
		name="Angle Value",
		description="Angle Value",
		default=180)
	#endregion

	#region straight properties

	bpy.types.Scene.even_straight_toggle = bpy.props.BoolProperty(
		name="Even Straight Checkbox",
		description="On/Off Even Straight",
		default = False
		)

	bpy.types.Scene.straight_axis_radiobox = bpy.props.EnumProperty(
		name="Axis",
		items=[
		('X', 'X', 'X', '', 0),
		('Y', 'Y', 'Y', '', 1),
		('Z', 'Z', 'Z', '', 2),
		('All', 'All', 'All', '', 3),
		],
		default='All')
	#endregion
	
	#region relax properties

	bpy.types.Scene.relax_input = bpy.props.EnumProperty(name="Input",
		items=(("all", "Parallel (all)", "Also use non-selected "
										"parallel loops as input"),
				("selected", "Selection", "Only use selected vertices as input")),
		description="Loops that are relaxed",
		default='selected'
	)

	bpy.types.Scene.relax_interpolation = bpy.props.EnumProperty(
		name="Interpolation",
		items=(("cubic", "Cubic", "Natural cubic spline, smooth results"),
				("linear", "Linear", "Simple and fast linear algorithm")),
		description="Algorithm used for interpolation",
		default='cubic'
	)

	bpy.types.Scene.relax_iterations = bpy.props.EnumProperty(name="Iterations",
		items=(("1", "1", "One"),
				("3", "3", "Three"),
				("5", "5", "Five"),
				("10", "10", "Ten"),
				("25", "25", "Twenty-five")),
		description="Number of times the loop is relaxed",
		default="1"
	)

	bpy.types.Scene.relax_regular = bpy.props.BoolProperty(
		name="Regular",
		description="Distribute vertices at constant distances along the loop",
		default=True
	)
	#endregion

	#region space properties

	bpy.types.Scene.space_influence = bpy.props.FloatProperty(
		name="Influence",
		description="Force of the tool",
		default=100.0,
		min=0.0,
		max=100.0,
		precision=1,
		subtype='PERCENTAGE'
	)

	bpy.types.Scene.space_input = bpy.props.EnumProperty(
		name="Input",
		items=(("all", "Parallel (all)", "Also use non-selected "
				"parallel loops as input"),
			("selected", "Selection", "Only use selected vertices as input")),
		description="Loops that are spaced",
		default='selected'
	)

	bpy.types.Scene.space_interpolation = bpy.props.EnumProperty(
		name="Interpolation",
		items=(("cubic", "Cubic", "Natural cubic spline, smooth results"),
			("linear", "Linear", "Vertices are projected on existing edges")),
		description="Algorithm used for interpolation",
		default='cubic'
		)

	bpy.types.Scene.space_lock_x = bpy.props.BoolProperty(
		name="Lock X",
		description="Lock editing of the x-coordinate",
		default=False
		)

	bpy.types.Scene.space_lock_y = bpy.props.BoolProperty(
		name="Lock Y",
		description="Lock editing of the y-coordinate",
		default=False
		)

	bpy.types.Scene.space_lock_z = bpy.props.BoolProperty(
		name="Lock Z",
		description="Lock editing of the z-coordinate",
		default=False
		)
	#endregion

	#region flatten properties

	bpy.types.Scene.flatten_influence = bpy.props.FloatProperty(
		name="Influence",
		description="Force of the tool",
		default=100.0,
		min=0.0,
		max=100.0,
		precision=1,
		subtype='PERCENTAGE'
		)

	bpy.types.Scene.flatten_lock_x = bpy.props.BoolProperty(
		name="Lock X",
		description="Lock editing of the x-coordinate",
		default=False
		)
	bpy.types.Scene.flatten_lock_y = bpy.props.BoolProperty(
		name="Lock Y",
		description="Lock editing of the y-coordinate",
		default=False
		)
	
	bpy.types.Scene.flatten_lock_z = bpy.props.BoolProperty(name="Lock Z",
		description="Lock editing of the z-coordinate",
		default=False
		)
	
	bpy.types.Scene.flatten_plane = bpy.props.EnumProperty(
		name="Plane",
		items=(("best_fit", "Best fit", "Calculate a best fitting plane"),
			  ("normal", "Normal", "Derive plane from averaging vertex normals"),
			  ("view", "View", "Flatten on a plane perpendicular to the viewing angle")),
		description="Plane on which vertices are flattened",
		default='best_fit'
		)
	
	bpy.types.Scene.flatten_restriction = bpy.props.EnumProperty(
		name="Restriction",
		items=(("none", "None", "No restrictions on vertex movement"),
			   ("bounding_box", "Bounding box", "Vertices are restricted to "
			   "movement inside the bounding box of the selection")),
		description="Restrictions on how the vertices can be moved",
		default='none'
		)

	#endregion

	#region screenshot properties
	bpy.types.Scene.camera_zoom_value = bpy.props.IntProperty(
		name="Zoom (%)",
		description="Camera zoom value",
		default=100,
		min=10,
		max=200,
		step=10,
		update=camera_zoom_value_ui_change)


	bpy.types.Scene.screenshot_path = bpy.props.StringProperty(
		name="",
		description="Screenshot path",
		default="D:/",
		subtype='DIR_PATH',
		update=update_screenshot_path_ui)

	#endregion

	#region material properties
	# coalition_stage = bpy.props.EnumProperty(name="Stage",
	# 	items=(("VIS0", "VIS0", ""),
	# 			("VIS1", "VIS1", "")),
	# 	description="Select Coalition stage")

	# udim_number = bpy.props.IntProperty(
	# 	name="",
	# 	description=":",
	# 	default=1,
	# 	min=1,
	# 	max=5,
	# 	step=1)
	#endregion

