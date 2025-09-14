import bpy
import bmesh
from .controller import *
from ..utility import variable


# Material UI and UIList classes removed for rework per user request


class TMC_UL_MaterialList(bpy.types.UIList):
	"""Simple UIList to display materials from bpy.data.materials"""

	def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
		# data is bpy.data, item is a Material
		mat = item
		if self.layout_type in {'DEFAULT', 'COMPACT'}:
			# Compute whether this material is assigned to the current selection
			assigned = False
			try:
				selected_mats = set()
				mode = getattr(context, 'mode', None)
				if mode and str(mode).upper().startswith('EDIT'):
					# In Edit Mode: check active object's selected faces
					active_obj = context.active_object
					if active_obj and active_obj.type == 'MESH':
						try:
							bm = bmesh.from_edit_mesh(active_obj.data)
							for f in bm.faces:
								if f.select:
									mi = f.material_index
									if 0 <= mi < len(active_obj.data.materials):
										m = active_obj.data.materials[mi]
										if m:
											selected_mats.add(m)
						except Exception:
							# Fallback to polygons if bmesh fails
							for p in active_obj.data.polygons:
								if p.select:
									mi = p.material_index
									if 0 <= mi < len(active_obj.data.materials):
										m = active_obj.data.materials[mi]
										if m:
											selected_mats.add(m)
				else:
					# Object mode or other: collect materials from selected objects
					for obj in context.selected_objects:
						if obj.type != 'MESH':
							continue
						for m in obj.data.materials:
							if m:
								selected_mats.add(m)
				assigned = (mat in selected_mats)
			except Exception:
				assigned = False

			# Use same column splits as header so preview, checkbox and name line up
			row = layout.row(align=True)
			# Left: read-only checkbox indicating assignment to current selection
			col = row.split(factor=0.05, align=True)
			try:
				if assigned:
					col.label(text="", icon='CHECKBOX_HLT')
				else:
					col.label(text="", icon='CHECKBOX_DEHLT')
			except Exception:
				col.label(text="")
			# Next: preview swatch (narrow)
			col = row.split(factor=0.08, align=True)
			try:
				icon = getattr(mat.preview, 'icon_id', None)
				if icon:
					col.label(text="", icon_value=icon)
				else:
					# fallback: small color block
					col.prop(mat, "diffuse_color", text="")
			except Exception:
				col.label(text="")
			# Name column (wide). Draw editable input with no emboss when active so it blends with the row highlight
			col = row.split(factor=0.87, align=True)
			if index == getattr(context.scene, 'material_index', 0):
				col.prop(mat, "name", text="", emboss=False)
			else:
				col.label(text=mat.name)
		elif self.layout_type in {'GRID'}:
			layout.alignment = 'CENTER'
			layout.label(text="")


class TMC_MT_Main_Panel(bpy.types.Panel):
	bl_idname = "TMC_MT_Main_Panel"
	bl_label = "HardSurface Tool"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "HS Tool"

	def draw(self, context):

		# Scene
		scene = context.scene

		# Main layout
		layout = self.layout

		# Tool Tab UI
		box = layout.box()
		row = box.row(align=True)
		row.scale_y = 1.5
		for index, item in enumerate(context.scene.bl_rna.properties["menu_tab"].enum_items):   
				row.prop_enum(context.scene, "menu_tab", item.identifier)
				if index == 2: # new line after third item
					row = box.row(align=True) 
					row.scale_y = 1.5
		
		# Modifier Tab UI
		if scene.menu_tab == "MODIFIER":
						
			## Toggle & Apply
			main_box = layout.box()
			row = main_box.row()
			split = row.split(factor=0.15, align=True)
			if context.scene.toggle_apply_modifier_ui:
				split.prop(scene, "toggle_apply_modifier_ui", text="", icon="DOWNARROW_HLT")
				
			else:
				split.prop(scene, "toggle_apply_modifier_ui", text="", icon="RIGHTARROW")
			split.label(text="Toggle & Apply")
			if scene.toggle_apply_modifier_ui:
				child_box = main_box.box()
				row = child_box.row(align=True)
				row.operator("tmc.toggle_modifier", text = "Toggle Modifiers")
				row.scale_y = 2.0
				row = child_box.row(align=True)
				row.operator("tmc.apply_modifier", text = "Apply Modifier")
				row.scale_y = 1.5

			## Bevel
			main_box = layout.box()
			row = main_box.row()
			split = row.split(factor=0.15, align=True)
			if context.scene.toggle_bevel_modifier_ui:
				split.prop(scene, "toggle_bevel_modifier_ui", text="", icon="DOWNARROW_HLT")
				
			else:
				split.prop(scene, "toggle_bevel_modifier_ui", text="", icon="RIGHTARROW")
			split.label(text="Bevel")
			if scene.toggle_bevel_modifier_ui:
				child_box = main_box.box()
				row = child_box.row(align=True)
				row.prop(scene, "bevel_modifier_name", text="")
				row.prop(scene, "bevel_type", text="")
				row = child_box.row(align=True)
				row.prop(scene, "bevel_unit_value", text="Value")
				row = child_box.row(align=True)
				row.prop(scene, "bevel_segment_value", text="Segment")
				row = child_box.row(align=True)
				row.operator("tmc.bevel_with_custom_setting", text = "Create Bevel")
				row.scale_y = 2.0
				row = child_box.row(align=True)
				row.operator("tmc.get_bevel_modifiers_from_vertex", text = "Get Bevel Modifiers (Vertex)")
				row.scale_y = 1.5

			## Boolean
			main_box = layout.box()
			row = main_box.row()
			split = row.split(factor=0.15, align=True)
			if context.scene.toggle_boolean_modifier_ui:
				split.prop(scene, "toggle_boolean_modifier_ui", text="", icon="DOWNARROW_HLT")

			else:
				split.prop(scene, "toggle_boolean_modifier_ui", text="", icon="RIGHTARROW")
			split.label(text="Boolean")
			if scene.toggle_boolean_modifier_ui:
				child_box = main_box.box()
				row = child_box.row(align=True)
				row.operator("tmc.boolean", text = "Simple Boolean")
				row.scale_y = 2.0

			## Mirror
			main_box = layout.box()
			row = main_box.row()
			split = row.split(factor=0.15, align=True)
			if context.scene.toggle_mirror_modifier_ui:
				split.prop(scene, "toggle_mirror_modifier_ui", text="", icon="DOWNARROW_HLT")
				
			else:
				split.prop(scene, "toggle_mirror_modifier_ui", text="", icon="RIGHTARROW")
			split.label(text="Mirror")
			if scene.toggle_mirror_modifier_ui:
				child_box = main_box.box()
				row = child_box.row(align=True)
				row.prop(scene, "current_mirror_object_name", text="Source")

				row = child_box.row(align=True)
				row.prop(scene, "target_mirror_object_name", text="Target")

				row = child_box.row(align=True)
				row.operator("tmc.select_object_from_current_mirror", text = "Select Object From Source")
				row.scale_y = 1.5

				row = child_box.row(align=True)
				row.operator("tmc.set_current_mirror_to_target_mirror", text = "Set Mirror To Target")
				row.scale_y = 1.5

		# Model Tab UI
		if scene.menu_tab == "MODEL":

			## Edge Length
			main_box = layout.box()
			row = main_box.row(align=True)
			split = row.split(factor=0.15, align=True)
			if context.scene.toggle_edge_length_ui:
				split.prop(scene, "toggle_edge_length_ui", text="", icon="DOWNARROW_HLT")
				
			else:
				split.prop(scene, "toggle_edge_length_ui", text="", icon="RIGHTARROW")
			split.prop(scene, "edge_length_value", text="")
			split.operator("tmc.set_edge_length", text = "Set Edge")
			row.scale_y = 2.0
			if scene.toggle_edge_length_ui:
				child_box = main_box.box()
				row = child_box.row(align=True)
				col = row.column(align=True)
				col.operator("tmc.get_edge_length", text = "Get Length")
				col.scale_y = 2.0
				col = row.column(align=True)
				child_row = col.row(align=True)
				child_row.operator("tmc.add_lock_vertex", text = "Add Lock Vertex")
				child_row = col.row(align=True)
				child_row.operator("tmc.clear_lock_vertex", text = "Clear")
				if variable.LOCK_VERTEX_INDEX_LIST == []:
					child_row.enabled = False
			
			## Circle Edge
			main_box = layout.box()
			row = main_box.row()
			split = row.split(factor=0.15, align=True)
			if context.scene.toggle_circle_edge_ui:
				split.prop(scene, "toggle_circle_edge_ui", text="", icon="DOWNARROW_HLT")
				
			else:
				split.prop(scene, "toggle_circle_edge_ui", text="", icon="RIGHTARROW")
			split.operator("tmc.circle_edge", text = "Circle Edge")
			row.scale_y = 2.0
			if scene.toggle_circle_edge_ui:
				# Line 1
				child_box = main_box.box()
				row = child_box.row(align=True)
				row.scale_y = 1.2
				col = row.column(align=True)
				col.prop(scene, "circle_diameter_toggle", text="Diameter")
				col = row.column(align=True)
				col.prop(scene, "circle_diameter_value", text="")
				if context.scene.circle_diameter_toggle == False:
					col.enabled = False 
				col = row.column(align=True)
				col.operator("tmc.get_circle_diameter", text = "Get")
				# Line 2
				row = child_box.row(align=True)
				row.scale_y = 1.2
				col = row.column(align=True)
				col.prop(scene, "circle_angle_toggle", text="Angle")
				col = row.column(align=True)
				col.prop(scene, "circle_angle_value", text="")
				if context.scene.circle_angle_toggle == False:
					col.enabled = False 
				col = row.column(align=True)
				col.operator("tmc.get_circle_angle", text = "Get")
				# Line 3
				row = child_box.row(align=True)
				row.scale_y = 1.5
				col = row.column(align=True)
				col.operator("tmc.add_priority_vertex", text = "Add Lock Vertex")
				col = row.column(align=True)
				col.operator("tmc.clear_priority_vertex", text = "Clear")
				if variable.PRIORITY_CIRCLE_VERTEX_INDEX_LIST == []:
					col.enabled = False

			## Straight Edge
			main_box = layout.box()
			row = main_box.row()
			split = row.split(factor=0.15, align=True)
			if context.scene.toggle_straight_edge_ui:
				split.prop(scene, "toggle_straight_edge_ui", text="", icon="DOWNARROW_HLT")
				
			else:
				split.prop(scene, "toggle_straight_edge_ui", text="", icon="RIGHTARROW")
			split.operator("tmc.straight_edge", text = "Straight Edge")
			row.scale_y = 2.0
			if scene.toggle_straight_edge_ui:
				child_box = main_box.box()
				row = child_box.row(align=True)
				row.prop(scene, "straight_axis_radiobox", expand = True)
				row = child_box.row(align=True)
				row.prop(scene, "even_straight_toggle", text="Even")
				if context.scene.straight_axis_radiobox != "All":
					row.enabled = False

			## Relax Edge
			main_box = layout.box()
			row = main_box.row()
			split = row.split(factor=0.15, align=True)
			if context.scene.toggle_relax_edge_ui:
				split.prop(scene, "toggle_relax_edge_ui", text="", icon="DOWNARROW_HLT")
				
			else:
				split.prop(scene, "toggle_relax_edge_ui", text="", icon="RIGHTARROW")
			split.operator("tmc.relax_edge", text = "Relax Edge")
			row.scale_y = 2.0
			if scene.toggle_relax_edge_ui:
				child_box = main_box.box()
				row = child_box.row(align=True)
				row.prop(scene, "relax_interpolation")
				row = child_box.row(align=True)
				row.prop(scene, "relax_input")
				row = child_box.row(align=True)
				row.prop(scene, "relax_iterations")
				row = child_box.row(align=True)
				row.prop(scene, "relax_regular")


			## Space Edge
			main_box = layout.box()
			row = main_box.row()
			split = row.split(factor=0.15, align=True)
			if context.scene.toggle_space_edge_ui:
				split.prop(scene, "toggle_space_edge_ui", text="", icon="DOWNARROW_HLT")
				
			else:
				split.prop(scene, "toggle_space_edge_ui", text="", icon="RIGHTARROW")
			split.operator("tmc.space_edge", text = "Space Edge")
			row.scale_y = 2.0
			if scene.toggle_space_edge_ui:
				child_box = main_box.box()
				row = child_box.row(align=True)
				row.prop(scene, "space_interpolation")
				row = child_box.row(align=True)
				row.prop(scene, "space_input")
				row = child_box.row(align=True)
				if scene.space_lock_x:
					row.prop(scene, "space_lock_x", text="X", icon="LOCKED")
				else:
					row.prop(scene, "space_lock_x", text="X", icon="UNLOCKED")
				if scene.space_lock_y:
					row.prop(scene, "space_lock_y", text="Y", icon="LOCKED")
				else:
					row.prop(scene, "space_lock_y", text="Y", icon="UNLOCKED")
				if scene.space_lock_z:
					row.prop(scene, "space_lock_z", text="Z", icon="LOCKED")
				else:
					row.prop(scene, "space_lock_z", text="Z", icon="UNLOCKED")
				row = child_box.row(align=True)
				row.prop(scene, "space_influence")

			## Flatten Face
			main_box = layout.box()
			row = main_box.row()
			split = row.split(factor=0.15, align=True)
			if context.scene.toggle_flatten_face_ui:
				split.prop(scene, "toggle_flatten_face_ui", text="", icon="DOWNARROW_HLT")
				
			else:
				split.prop(scene, "toggle_flatten_face_ui", text="", icon="RIGHTARROW")
			split.operator("tmc.flatten_face", text = "Flatten Face")
			row.scale_y = 2.0
			if scene.toggle_flatten_face_ui:
				child_box = main_box.box()
				row = child_box.row(align=True)
				row.prop(scene, "flatten_plane")
				row = child_box.row(align=True)
				row.prop(scene, "flatten_restriction")
				row = child_box.row(align=True)
				if scene.flatten_lock_x:
					row.prop(scene, "flatten_lock_x", text="X", icon='LOCKED')
				else:
					row.prop(scene, "flatten_lock_x", text="X", icon='UNLOCKED')
				if scene.flatten_lock_y:
					row.prop(scene, "flatten_lock_y", text="Y", icon='LOCKED')
				else:
					row.prop(scene, "flatten_lock_y", text="Y", icon='UNLOCKED')
				if scene.flatten_lock_z:
					row.prop(scene, "flatten_lock_z", text="Z", icon='LOCKED')
				else:
					row.prop(scene, "flatten_lock_z", text="Z", icon='UNLOCKED')
				row = child_box.row(align=True)
				row.prop(scene, "flatten_influence")

			## Smooth Edge
			main_box = layout.box()
			row = main_box.row()
			split = row.split(factor=0.15, align=True)
			if context.scene.toggle_smooth_edge_ui:
				split.prop(scene, "toggle_smooth_edge_ui", text="", icon="DOWNARROW_HLT")
				
			else:
				split.prop(scene, "toggle_smooth_edge_ui", text="", icon="RIGHTARROW")
			split.operator("tmc.smooth_edge", text = "Smooth Edge")
			row.scale_y = 2.0
			if scene.toggle_smooth_edge_ui:
				child_box = layout.box()
				row = child_box.row()
				row.prop(scene, "curve_influence", text="Curve")
				row = child_box.row()
				row.prop(scene, "space_influence", text="Space")
				row = child_box.row()
				row.prop(scene, "relax_influence",  text="Relax")
				row = child_box.row()
				split = row.split(factor=0.4, align=True)
				split.label(text="Loop Input:")
				split.prop(scene, "smooth_input", text="")
				
				### Curve Settings
				row = child_box.row()
				curve_box = row.box()
				row = curve_box.row()
				row.label(text="Curve Settings:")
				row = curve_box.row()
				split = row.split(factor=0.4, align=True)
				split.label(text="Interpolation:")
				split.prop(scene, "curve_interpolation", text="")
				row = curve_box.row()
				row.prop(scene, "curve_boundaries", text="Boundaries")
				row = curve_box.row()
				row.prop(scene, "curve_regular", text="Regular Distribution")
				row = curve_box.row()
				split = row.split(factor=0.4, align=True)
				split.label(text="Restriction:")
				split.prop(scene, "curve_restriction", text="")

				### Relax Settings
				row = child_box.row()
				relax_box = row.box()
				row = relax_box.row()
				row.label(text="Relax Settings:")
				row = relax_box.row()
				split = row.split(factor=0.4, align=True)
				split.label(text="Restriction:")
				split.prop(scene, "relax_iterations", text="")
				row = relax_box.row()
				row.prop(scene, "relax_regular", text="Regular Distribution")


			## Clone element
			main_box = layout.box()
			row = main_box.row()
			row.operator("tmc.clone_element", text = "Clone Element")
			row.scale_y = 2.0


		# Misc Tab UI
		if scene.menu_tab == "MISC":
			## Collection
			main_box = layout.box()
			row = main_box.row()
			split = row.split(factor=0.15, align=True)
			if context.scene.toggle_collection_area_ui:
				split.prop(scene, "toggle_collection_area_ui", text="", icon="DOWNARROW_HLT")
				
			else:
				split.prop(scene, "toggle_collection_area_ui", text="", icon="RIGHTARROW")
			split.label(text="Collection")
			if scene.toggle_collection_area_ui:
				child_box = main_box.box()
				row = child_box.row(align=True)
				row.operator("tmc.collapse_all_collections", text = "Collapse All Collections")
				row.scale_y = 1.5
				child_box = main_box.box()
				row = child_box.row(align=True)
				row.operator("tmc.toggle_current_hide_group", text = "Toggle Hide Collections")
				row.scale_y = 1.5

			## Normal
			main_box = layout.box()
			row = main_box.row()
			split = row.split(factor=0.15, align=True)
			if context.scene.toggle_normal_area_ui:
				split.prop(scene, "toggle_normal_area_ui", text="", icon="DOWNARROW_HLT")
				
			else:
				split.prop(scene, "toggle_normal_area_ui", text="", icon="RIGHTARROW")
			split.label(text="Normal")
			if scene.toggle_normal_area_ui:
				child_box = main_box.box()
				row = child_box.row(align=True)
				row.operator("tmc.set_normal_with_active_face", text = "Set Normal From Last Face")
				row.scale_y = 1.5

			#region Vertex Group
			main_box = layout.box()
			row = main_box.row()
			split = row.split(factor=0.15, align=True)
			if context.scene.toggle_vertex_group_area_ui:
				split.prop(scene, "toggle_vertex_group_area_ui", text="", icon="DOWNARROW_HLT")
				
			else:
				split.prop(scene, "toggle_vertex_group_area_ui", text="", icon="RIGHTARROW")
			split.label(text="Vertex Group")
			if scene.toggle_vertex_group_area_ui:
				child_box = main_box.box()
				row = child_box.row(align=True)
				row.operator("tmc.clean_vertex_group", text = "Clean Vertex Group")
				row.scale_y = 1.5
			#endregion

			## UV
			main_box = layout.box()
			row = main_box.row()
			split = row.split(factor=0.15, align=True)
			if context.scene.toggle_uv_area_ui:
				split.prop(scene, "toggle_uv_area_ui", text="", icon="DOWNARROW_HLT")
				
			else:
				split.prop(scene, "toggle_uv_area_ui", text="", icon="RIGHTARROW")
			split.label(text="UV")
			if scene.toggle_uv_area_ui:
				child_box = main_box.box()
				row = child_box.row()
				row.operator("tmc.uv_by_sharp_edge", text = "UV by Sharp Edge")
				row.scale_y = 1.5
				child_box = main_box.box()
				row = child_box.row()
				row.prop(scene, "uvset1_name", text="UV1")
				row.operator("tmc.rename_uv1", text = "Rename")
				row.scale_y = 1.5
				row = child_box.row(align=True)
				row.operator("tmc.delete_redundant_uv", text = "Delete Redundant UVSet")
				row.scale_y = 1.5

			## Capture
			main_box = layout.box()
			row = main_box.row()
			split = row.split(factor=0.15, align=True)
			if context.scene.toggle_capture_area_ui:
				split.prop(scene, "toggle_capture_area_ui", text="", icon="DOWNARROW_HLT")

			else:
				split.prop(scene, "toggle_capture_area_ui", text="", icon="RIGHTARROW")
			split.label(text="Capture")
			if scene.toggle_capture_area_ui:
				# Line 1
				row = main_box.row()
				row.prop(scene, "screenshot_path")
				row.scale_y = 1.5
				# Line 2
				row = main_box.row(align=True)
				row.prop(scene, "camera_zoom_value", text = "Zoom ")
				row.scale_y = 1.5
				# Line 3
				row = main_box.row()
				row.scale_y = 2.0
				row.operator("tmc.auto_screenshot", text="Auto", icon="SCENE")
				row.operator("tmc.custom_screenshot", text="Custom", icon="RESTRICT_RENDER_OFF")


			# ## Bake Set
			# main_box = layout.box()
			# row = main_box.row()
			# split = row.split(factor=0.15, align=True)
			# if context.scene.toggle_bakeset_area_ui:
			# 	split.prop(scene, "toggle_bakeset_area_ui", text="", icon="DOWNARROW_HLT")
				
			# else:
			# 	split.prop(scene, "toggle_bakeset_area_ui", text="", icon="RIGHTARROW")
			# split.label(text="Bake Set")
			# if scene.toggle_bakeset_area_ui:
			# 	child_box = main_box.box()
			# 	row = child_box.row()
			# 	row.prop(scene, "bakeset_name", text="Name")
			# 	row.scale_y = 1.5
				
			# 	row = child_box.row()
			# 	row.prop(scene, "threshold_value", text="Threshold")
			# 	row.scale_y = 1.5

			# 	row = child_box.row()
			# 	row.operator("tmc.rename_highpoly", text = "Rename Highpoly")
			# 	row.scale_y = 1.5
			# 	row = child_box.row()
			# 	row.operator("tmc.create_bakeset", text = "Create Bake Set")
			# 	row.scale_y = 1.5
			# 	row = child_box.row()
			# 	row.operator("tmc.auto_create_bakeset", text = "Auto Create Bake Set")
			# 	row.scale_y = 1.5

			# 	row = child_box.row()
			# 	row.prop(scene, "bakeset_export_path", text="Path")
			# 	row.scale_y = 1.5

			# 	row = child_box.row()
			# 	row.prop(scene, "export_bakeset_mode", text="Mode")
			# 	row.scale_y = 1.5

			# 	row = child_box.row()
			# 	row.prop(scene, "export_bakeset_unlock_normal", text="Unlock Normal")
			# 	row.scale_y = 1.5

			# 	row = child_box.row()
			# 	row.operator("tmc.export_bakeset", text = "Export Selected High/Low Objects")
			# 	row.scale_y = 1.5
				
			# 	row = child_box.row()
			# 	row.operator("tmc.export_selected_highlow", text = "Export All Bake Set")
			# 	row.scale_y = 1.5

		# Check Tab UI
		if scene.menu_tab == "CHECK":
			## Check Model
			pcoll = variable.PREVIEW_COLLECTIONS['main']
			true_icon = pcoll['true_icon']
			false_icon = pcoll['false_icon']

			main_box = layout.box()
			row = main_box.row(align=True)
			row.label(text="Model")
			child_box = main_box.box()
			row = child_box.row(align=True)
			row.operator("tmc.check_all", text = "Check All")
			row.scale_y = 1.5
			row = child_box.row(align=True)
			split = row.split(factor=0.85, align=True)
			split.operator("tmc.check_ngons_face", text = "N-gons Face")
			if scene.check_ngons_face:
				split.operator("tmc.check_ngons_face", text = "", icon_value = true_icon.icon_id)
			else:
				split.operator("tmc.check_ngons_face", text = "", icon_value = false_icon.icon_id)
			row.scale_y = 1.5
			
			row = child_box.row(align=True)
			split = row.split(factor=0.85, align=True)
			split.operator("tmc.check_non_manifold", text = "Non-manifold")
			if scene.check_non_manifold:
				split.operator("tmc.check_non_manifold", text = "", icon_value = true_icon.icon_id)
			else:
				split.operator("tmc.check_non_manifold", text = "", icon_value = false_icon.icon_id)
			row.scale_y = 1.5

			row = child_box.row(align=True)
			split = row.split(factor=0.85, align=True)
			split.operator("tmc.check_isolated_vertex", text = "Isolated Vertex")
			if scene.check_isolated_vertex:
				split.operator("tmc.check_isolated_vertex", text = "", icon_value = true_icon.icon_id)
			else:
				split.operator("tmc.check_isolated_vertex", text = "", icon_value = false_icon.icon_id)
			row.scale_y = 1.5

			row = child_box.row(align=True)
			split = row.split(factor=0.85, align=True)
			split.operator("tmc.check_intersect_face", text = "Intersect Face")
			if scene.check_intersect_face:
				split.operator("tmc.check_intersect_face", text = "", icon_value = true_icon.icon_id)
			else:
				split.operator("tmc.check_intersect_face", text = "", icon_value = false_icon.icon_id)
			row.scale_y = 1.5

			row = child_box.row(align=True)
			split = row.split(factor=0.85, align=True)
			small_split = split.split(factor=0.65, align=True)
			small_split.operator("tmc.check_zero_edge_length", text = "Zero Edge Length")
			small_split.prop(scene, "min_edge_length_value", text="")
			if scene.check_zero_edge_length:
				split.operator("tmc.check_zero_edge_length", text = "", icon_value = true_icon.icon_id)
			else:
				split.operator("tmc.check_zero_edge_length", text = "", icon_value = false_icon.icon_id)
			row.scale_y = 1.5

			row = child_box.row(align=True)
			split = row.split(factor=0.85, align=True)
			small_split = split.split(factor=0.65, align=True)
			small_split.operator("tmc.check_zero_face_area", text = "Zero Face Area")
			small_split.prop(scene, "min_face_area_value", text="")
			if scene.check_zero_face_area:
				split.operator("tmc.check_zero_face_area", text = "", icon_value = true_icon.icon_id)
			else:
				split.operator("tmc.check_zero_face_area", text = "", icon_value = false_icon.icon_id)
			row.scale_y = 1.5

			child_box = main_box.box()
			row = child_box.row()
			split = row.split(factor=0.7)
			split.operator("tmc.check_silhouette", text = "Check Silhouette")
			split.prop(scene, "viewport_background_color", text="")
			split.scale_y = 1.5

		# Bridge Tab UI
		if scene.menu_tab == "BRIDGE":
			## Maya - Blender
			main_box = layout.box()
			row = main_box.row(align=True)
			row.label(text="Blender - Maya - Max")
			child_box = main_box.box()

			# row = child_box.row(align=True)
			# split = row.split(factor=0.2, align=True)
			# row.label(text = "Forward:", icon="AXIS_FRONT")
			# row.prop(scene, "blender_maya_axis_forward_combobox")
	
			# row = child_box.row(align=True)
			# split = row.split(factor=0.2, align=True)
			# row.label(text = "Up:", icon="AXIS_TOP")
			# row.prop(scene, "blender_maya_axis_up_combobox")

			row = child_box.row(align=True)
			split = row.split(factor=0.2, align=True)
			row.label(text = "Normal:", icon="NORMALS_VERTEX_FACE")
			row.prop(scene, "blender_maya_normal_radiobox", expand = True)
			row = child_box.row(align=True)
			row.operator("tmc.import_from_maya", text = "Import", icon="IMPORT")
			row.operator("tmc.export_to_maya", text = "Export", icon="EXPORT")
			row.scale_y = 1.5

		# Material Tab UI
		if scene.menu_tab == "MATERIAL":
			# Material list: show all materials in the file (scene-wide)
			main_box = layout.box()
			child_box = main_box.box()
			# Use a template_list over bpy.data.materials via a shortcut:
			# We provide a dummy pointer to the window manager to host the index
			# but we'll simply draw items using the UIList class below.
			# Draw header with same row style/alignment as items for better theme parity
			header = child_box.row(align=True)
			header.scale_y = 1.0
			# Left preview swatch column (narrow)
			#col = header.split(factor=0.3, align=True)
			header.label(text="Material List", icon='MATERIAL')
			# Material list with right-side Select button
			row = child_box.row(align=True)
			row.scale_y = 1.5
			# Left: material list (wide)
			col = row.split(factor=0.65)
			col.template_list("TMC_UL_MaterialList", "", bpy.data, "materials", context.scene, "material_index")
			# Right: small column for action buttons (stacked)
			col_buttons = col.column(align=True)
			col_buttons.operator("tmc.select_objects_by_material", text="Select Objects")
			col_buttons.operator("tmc.assign_material_to_selection", text="Assign Selected")

			col_buttons.separator()
			col_buttons.operator("tmc.add_material", text="Add Material")
			# Color picker for new material base color (also edits selected material)
			try:
				col_buttons.prop(scene, "material_add_color", text="")
			except Exception:
				pass
			
			col_buttons.separator()
			col_buttons.operator("tmc.clean_material_slots", text="Clean Slots")
			col_buttons.operator("tmc.delete_duplicate_materials", text="Delete Duplicates")
			col_buttons.operator("tmc.delete_all_materials", text="Delete All")
