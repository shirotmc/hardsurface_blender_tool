bl_info = {
	"name": "HardSurface Tool",
	"description": "This add-on provides a set of custom tools for working efficiently in Blender.",
	"author": "Canh Tran",
	"version": (1, 2, 1),
	"blender": (2, 80, 0),
	"location": "View3D",
	"category": "3D View"
}

import sys
sys.dont_write_bytecode = True
import bpy
from . import addon_updater_ops
from .addon.register import register_addon, unregister_addon
from bpy.app.handlers import persistent


@persistent
def _tmc_on_load(dummy):
	try:
		from .addon.ui import handlers as _ui_handlers
		_ui_handlers.register()
	except Exception:
		pass


@addon_updater_ops.make_annotations
class HS_PieItem(bpy.types.PropertyGroup):
	# legacy assignment style; decorator converts them to annotations on 2.8+
	name = bpy.props.StringProperty(name="Label", default="")  # visible label
	op = bpy.props.StringProperty(name="Operator", default="")  # e.g. 'tmc.boolean'
	icon = bpy.props.StringProperty(name="Icon", default="")  # optional icon file name within icons folder


@addon_updater_ops.make_annotations
class HS_OT_PieItemAdd(bpy.types.Operator):
	bl_idname = "tmc.pie_item_add"
	bl_label = "Add Pie Item"
	bl_description = "Add current operator entry to the pie menu list"

	# Mode: 'DIALOG' opens fields, 'PICKER' shows a simple default list to choose from
	mode = 'PICKER'
	# Fields for dialog (kept for advanced/manual add if we switch mode)
	label = bpy.props.StringProperty(name="Label", default="")
	operator = bpy.props.StringProperty(name="Operator", default="")
	icon_name = bpy.props.StringProperty(name="Icon (optional)", default="")

	# internal flag to know an item was added from picker
	_added_from_picker = False

	def draw(self, context):
		layout = self.layout
		if self.mode == 'DIALOG':
			col = layout.column(align=True)
			col.prop(self, "label", text="Label")
			col.prop(self, "operator", text="Operator idname")
			col.prop(self, "icon_name", text="Icon file (icons/)")
		else:
			# Picker list from fallback defaults
			try:
				from .addon.ui.menu import get_default_pie_items
			except Exception:
				get_default_pie_items = lambda: []
			items = get_default_pie_items()
			col = layout.column(align=True)
			col.label(text="Choose an item to add")
			for idx, entry in enumerate(items):
				label = entry[0] if len(entry) > 0 else ""
				op = entry[1] if len(entry) > 1 else ""
				icon = entry[2] if len(entry) > 2 else ""
				row = col.row(align=True)
				btn = row.operator(HS_OT_PieItemAddConfirm.bl_idname, text=label or op)
				btn.label = label or op
				btn.operator = op
				btn.icon_name = icon if isinstance(icon, str) else (icon.get('icon','') if isinstance(icon, dict) else "")
				# Set a flag so invoke() can auto-close the dialog on execute
				self._added_from_picker = True

	def execute(self, context):
		prefs = context.preferences.addons[__package__].preferences
		item = prefs.pie_items.add()
		item.name = self.label or self.operator
		item.op = self.operator
		item.icon = self.icon_name
		prefs.pie_items_index = len(prefs.pie_items) - 1
		return {'FINISHED'}

	def invoke(self, context, event):
		# Always open as picker by default for your workflow
		self.mode = 'PICKER'
		wm = context.window_manager
		ret = wm.invoke_props_dialog(self, width=320)
		# If an item was clicked, close immediately by returning FINISHED from execute; Blender will close dialog after operator finishes.
		return ret


@addon_updater_ops.make_annotations
class HS_OT_PieItemAddConfirm(bpy.types.Operator):
	bl_idname = "tmc.pie_item_add_confirm"
	bl_label = "Add Item (Confirm)"
	bl_description = "Confirm add from picker list"

	label = bpy.props.StringProperty(default="")
	operator = bpy.props.StringProperty(default="")
	icon_name = bpy.props.StringProperty(default="")

	def execute(self, context):
		prefs = context.preferences.addons[__package__].preferences
		item = prefs.pie_items.add()
		item.name = self.label or self.operator
		item.op = self.operator
		item.icon = self.icon_name
		prefs.pie_items_index = len(prefs.pie_items) - 1
		return {'FINISHED'}


class HS_OT_PieItemClear(bpy.types.Operator):
	bl_idname = "tmc.pie_items_clear"
	bl_label = "Clear Pie Items"
	bl_description = "Remove all custom pie items"

	def execute(self, context):
		prefs = context.preferences.addons[__package__].preferences
		prefs.pie_items.clear()
		prefs.pie_items_index = 0
		return {'FINISHED'}


@addon_updater_ops.make_annotations
class HS_OT_PieItemsSeedDefaults(bpy.types.Operator):
	bl_idname = "tmc.pie_items_seed_defaults"
	bl_label = "Load Defaults"
	bl_description = "Fill the Pie Menu Items list with the add-on's default items"

	def execute(self, context):
		prefs = context.preferences.addons[__package__].preferences
		# import lazily to avoid circulars
		try:
			from .addon.ui.menu import get_pie_items
		except Exception:
			return {'CANCELLED'}
		# clear existing
		prefs.pie_items.clear()
		# add defaults
		try:
			defaults = get_pie_items(None)
		except Exception:
			defaults = []
		for entry in defaults:
			try:
				label = entry[0] if len(entry) >= 1 else ""
				op = entry[1] if len(entry) >= 2 else ""
				icon = ""
				if len(entry) >= 3:
					p = entry[2]
					if isinstance(p, str):
						icon = p
					elif isinstance(p, dict):
						icon = p.get('icon', "")
				item = prefs.pie_items.add()
				item.name = label or op
				item.op = op
				item.icon = icon
			except Exception:
				continue
		prefs.pie_items_index = max(0, len(prefs.pie_items) - 1)
		return {'FINISHED'}

@addon_updater_ops.make_annotations
class HS_OT_PieItemAddSearch(bpy.types.Operator):
	bl_idname = "tmc.pie_item_add_search"
	bl_label = "Add Pie Item"
	bl_description = "Search and add a default pie item"
	bl_property = 'pick'

	def _enum_items(self, context):
		try:
			from .addon.ui.menu import get_default_pie_items
		except Exception:
			return []
		items = []
		for idx, entry in enumerate(get_default_pie_items(), start=1):
			label = entry[0] if len(entry) > 0 else ""
			op = entry[1] if len(entry) > 1 else ""
			identifier = op or label or f"item_{idx}"
			name = label or op or identifier
			items.append((identifier, name, "", idx))
		return items

	pick = bpy.props.EnumProperty(name='Choose Pie Item', description='', options={'SKIP_SAVE'}, items=_enum_items)

	def execute(self, context):
		chosen = getattr(self, 'pick', None)
		if not chosen or chosen == 'SELECT/SEARCH ITEM':
			return {'CANCELLED'}
		try:
			from .addon.ui.menu import get_default_pie_items
		except Exception:
			return {'CANCELLED'}
		match = None
		for entry in get_default_pie_items():
			label = entry[0] if len(entry) > 0 else ""
			op = entry[1] if len(entry) > 1 else ""
			if op == chosen or label == chosen:
				match = entry
				break
		if not match:
			return {'CANCELLED'}
		label = match[0] if len(match) > 0 else chosen
		op = match[1] if len(match) > 1 else chosen
		icon_name = ""
		if len(match) > 2:
			third = match[2]
			if isinstance(third, str):
				icon_name = third
			elif isinstance(third, dict):
				icon_name = third.get('icon', '')
		prefs = context.preferences.addons[__package__].preferences
		item = prefs.pie_items.add()
		item.name = label or op
		item.op = op
		item.icon = icon_name
		prefs.pie_items_index = len(prefs.pie_items) - 1
		return {'FINISHED'}

	def invoke(self, context, event):
		context.window_manager.invoke_search_popup(self)
		return self.execute(context)

@addon_updater_ops.make_annotations
class HS_OT_PieItemRemove(bpy.types.Operator):
	bl_idname = "tmc.pie_item_remove"
	bl_label = "Remove Pie Item"
	index = bpy.props.IntProperty(default=-1)

	def execute(self, context):
		prefs = context.preferences.addons[__package__].preferences
		idx = self.index if self.index >= 0 else prefs.pie_items_index
		if 0 <= idx < len(prefs.pie_items):
			prefs.pie_items.remove(idx)
			prefs.pie_items_index = min(idx, len(prefs.pie_items)-1)
		return {'FINISHED'}


@addon_updater_ops.make_annotations
class AddonPreferences(bpy.types.AddonPreferences):
	bl_idname = __package__

	# Updater options
	auto_check_update = bpy.props.BoolProperty(name="Auto-check for Update", default=False)
	updater_interval_months = bpy.props.IntProperty(name='Months', default=0, min=0)
	updater_interval_days = bpy.props.IntProperty(name='Days', default=7, min=0, max=31)
	updater_interval_hours = bpy.props.IntProperty(name='Hours', default=0, min=0, max=23)
	updater_interval_minutes = bpy.props.IntProperty(name='Minutes', default=0, min=0, max=59)

	# Pie menu configuration
	pie_items = bpy.props.CollectionProperty(type=HS_PieItem)
	pie_items_index = bpy.props.IntProperty(default=0)

	def draw(self, context):
		layout = self.layout
		# Updater block
		addon_updater_ops.update_settings_ui(self, context)

		box = layout.box()
		row = box.row(align=True)
		row.label(text="Pie Menu Items")
		row.operator("tmc.pie_item_add_search", text="Add", icon="ADD")
		row.operator("tmc.pie_items_clear", text="Clear", icon="TRASH")
		row.operator("tmc.pie_items_seed_defaults", text="Load Defaults", icon="FILE_REFRESH")

		# List header
		col = box.column(align=True)
		for i, it in enumerate(self.pie_items):
			r = col.row(align=True)
			r.label(text=f"{i+1}", icon='DOT')
			# Robust property access (older Blender reloads can lose RNA defs temporarily)
			try:
				r.prop(it, "name", text="")
			except Exception:
				r.label(text=getattr(it, 'name', ''))
			try:
				r.prop(it, "op", text="")
			except Exception:
				r.label(text=getattr(it, 'op', ''))
			op_rm = r.operator("tmc.pie_item_remove", text="", icon="X")
			try:
				op_rm.index = i
			except Exception:
				pass


def register():
	# Update add-ons
	addon_updater_ops.register(bl_info)
	bpy.utils.register_class(HS_PieItem)
	bpy.utils.register_class(HS_OT_PieItemAdd)
	bpy.utils.register_class(HS_OT_PieItemAddSearch)
	bpy.utils.register_class(HS_OT_PieItemAddConfirm)
	bpy.utils.register_class(HS_OT_PieItemClear)
	bpy.utils.register_class(HS_OT_PieItemsSeedDefaults)
	bpy.utils.register_class(HS_OT_PieItemRemove)
	bpy.utils.register_class(AddonPreferences)
	# Ensure our load handler is attached so runtime handlers re-register
	try:
		if _tmc_on_load not in bpy.app.handlers.load_post:
			bpy.app.handlers.load_post.append(_tmc_on_load)
	except Exception:
		pass
	# Unregister add-ons
	register_addon()

def unregister():
	# Update add-ons
	addon_updater_ops.unregister()
	bpy.utils.unregister_class(AddonPreferences)
	bpy.utils.unregister_class(HS_OT_PieItemRemove)
	bpy.utils.unregister_class(HS_OT_PieItemClear)
	bpy.utils.unregister_class(HS_OT_PieItemsSeedDefaults)
	bpy.utils.unregister_class(HS_OT_PieItemAddSearch)
	bpy.utils.unregister_class(HS_OT_PieItemAdd)
	bpy.utils.unregister_class(HS_OT_PieItemAddConfirm)
	bpy.utils.unregister_class(HS_PieItem)
	# Remove our load handler
	try:
		if _tmc_on_load in bpy.app.handlers.load_post:
			bpy.app.handlers.load_post.remove(_tmc_on_load)
	except Exception:
		pass
	# Unregister add-ons
	unregister_addon()