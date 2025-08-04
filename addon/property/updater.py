import bpy
from ..operator.updater import *

class TMC_Updater(bpy.types.PropertyGroup):

    auto_check_update: bpy.props.BoolProperty(
		name="Auto-check for Update",
		description="If enabled, auto-check for updates using an interval",
		default=False)

    updater_interval_months: bpy.props.IntProperty(
		name='Months',
		description="Number of months between checking for updates",
		default=0,
		min=0)

    updater_interval_days: bpy.props.IntProperty(
		name='Days',
		description="Number of days between checking for updates",
		default=7,
		min=0,
		max=31)

    updater_interval_hours: bpy.props.IntProperty(
		name='Hours',
		description="Number of hours between checking for updates",
		default=0,
		min=0,
		max=23)

    updater_interval_minutes: bpy.props.IntProperty(
		name='Minutes',
		description="Number of minutes between checking for updates",
		default=0,
		min=0,
		max=59)

def draw_updater(prefs, layout):
	box = layout
	if updater.invalid_updater:
			box.label(text="Error initializing updater code:")
			box.label(text=updater.error_msg)
			return
	# auto-update settings
	box.label(text="Updater Settings")
	row = box.row()

	# special case to tell user to restart blender, if set that way
	if not updater.auto_reload_post_update:
		saved_state = updater.json
		if "just_updated" in saved_state and saved_state["just_updated"]:
			row.alert = True
			row.operator("wm.quit_blender",
						text="Restart blender to complete update",
						icon="ERROR")
			return

	split = layout_split(row, factor=0.4)
	sub_col = split.column()
	sub_col.prop(prefs.updater, "auto_check_update")
	sub_col = split.column()

	if not prefs.updater.auto_check_update:
		sub_col.enabled = False
	sub_row = sub_col.row()
	sub_row.label(text="Interval between checks")
	sub_row = sub_col.row(align=True)
	check_col = sub_row.column(align=True)
	check_col.prop(prefs.updater, "updater_interval_months")
	check_col = sub_row.column(align=True)
	check_col.prop(prefs.updater, "updater_interval_days")
	check_col = sub_row.column(align=True)

	# Consider un-commenting for local dev (e.g. to set shorter intervals)
	# check_col.prop(settings,"updater_interval_hours")
	# check_col = sub_row.column(align=True)
	# check_col.prop(settings,"updater_interval_minutes")

	# Checking / managing updates.
	row = box.row()
	col = row.column()
	if updater.error is not None:
		sub_col = col.row(align=True)
		sub_col.scale_y = 1
		split = sub_col.split(align=True)
		split.scale_y = 2
		if "ssl" in updater.error_msg.lower():
			split.enabled = True
			split.operator(AddonUpdaterInstallManually.bl_idname,
						text=updater.error)
		else:
			split.enabled = False
			split.operator(AddonUpdaterCheckNow.bl_idname,
						text=updater.error)
		split = sub_col.split(align=True)
		split.scale_y = 2
		split.operator(AddonUpdaterCheckNow.bl_idname,
					text="", icon="FILE_REFRESH")

	elif updater.update_ready is None and not updater.async_checking:
		col.scale_y = 2
		col.operator(AddonUpdaterCheckNow.bl_idname)
	elif updater.update_ready is None:  # async is running
		sub_col = col.row(align=True)
		sub_col.scale_y = 1
		split = sub_col.split(align=True)
		split.enabled = False
		split.scale_y = 2
		split.operator(AddonUpdaterCheckNow.bl_idname, text="Checking...")
		split = sub_col.split(align=True)
		split.scale_y = 2
		split.operator(AddonUpdaterEndBackground.bl_idname, text="", icon="X")

	elif updater.include_branches and \
			len(updater.tags) == len(updater.include_branch_list) and not \
			updater.manual_only:
		# No releases found, but still show the appropriate branch.
		sub_col = col.row(align=True)
		sub_col.scale_y = 1
		split = sub_col.split(align=True)
		split.scale_y = 2
		update_now_txt = "Update directly to {}".format(
			updater.include_branch_list[0])
		split.operator(AddonUpdaterUpdateNow.bl_idname, text=update_now_txt)
		split = sub_col.split(align=True)
		split.scale_y = 2
		split.operator(AddonUpdaterCheckNow.bl_idname,
					text="", icon="FILE_REFRESH")

	elif updater.update_ready and not updater.manual_only:
		sub_col = col.row(align=True)
		sub_col.scale_y = 1
		split = sub_col.split(align=True)
		split.scale_y = 2
		split.operator(AddonUpdaterUpdateNow.bl_idname,
					text="Update now to " + str(updater.update_version))
		split = sub_col.split(align=True)
		split.scale_y = 2
		split.operator(AddonUpdaterCheckNow.bl_idname,
					text="", icon="FILE_REFRESH")

	elif updater.update_ready and updater.manual_only:
		col.scale_y = 2
		dl_now_txt = "Download " + str(updater.update_version)
		col.operator("wm.url_open",
					text=dl_now_txt).url = updater.website
	else:  # i.e. that updater.update_ready == False.
		sub_col = col.row(align=True)
		sub_col.scale_y = 1
		split = sub_col.split(align=True)
		split.enabled = False
		split.scale_y = 2
		split.operator(AddonUpdaterCheckNow.bl_idname,
					text="Addon is up to date")
		split = sub_col.split(align=True)
		split.scale_y = 2
		split.operator(AddonUpdaterCheckNow.bl_idname,
					text="", icon="FILE_REFRESH")

	if not updater.manual_only:
		col = row.column(align=True)
		if updater.include_branches and len(updater.include_branch_list) > 0:
			branch = updater.include_branch_list[0]
			col.operator(AddonUpdaterUpdateTarget.bl_idname,
						text="Install {} / old version".format(branch))
		else:
			col.operator(AddonUpdaterUpdateTarget.bl_idname,
						text="(Re)install addon version")
		last_date = "none found"
		backup_path = os.path.join(updater.stage_path, "backup")
		if "backup_date" in updater.json and os.path.isdir(backup_path):
			if updater.json["backup_date"] == "":
				last_date = "Date not found"
			else:
				last_date = updater.json["backup_date"]
		backup_text = "Restore addon backup ({})".format(last_date)
		col.operator(AddonUpdaterRestoreBackup.bl_idname, text=backup_text)

	row = box.row()
	row.scale_y = 0.7
	last_check = updater.json["last_check"]
	if updater.error is not None and updater.error_msg is not None:
		row.label(text=updater.error_msg)
	elif last_check:
		last_check = last_check[0: last_check.index(".")]
		row.label(text="Last update check: " + last_check)
	else:
		row.label(text="Last update check: Never")

