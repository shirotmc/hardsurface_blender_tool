import os
import bpy
from bpy.utils import previews
from ..utility import variable
from .menu import *
from .panel import *

classes = [
	TMC_MT_Main_Menu,
	TMC_MT_Main_Panel,
]

def register_menus():
	from bpy.utils import register_class
	for cls in classes:
		register_class(cls)
	
	# Register Icons
	pcoll = previews.new()
	my_icons_dir = os.path.join(os.path.dirname(__file__), "icons")
	pcoll.load("false_icon", os.path.join(my_icons_dir, "false.png"), 'IMAGE')
	pcoll.load("true_icon", os.path.join(my_icons_dir, "true.png"), 'IMAGE')
	variable.PREVIEW_COLLECTIONS["main"] = pcoll

def unregister_menus():
	from bpy.utils import unregister_class
	for cls in reversed(classes):
		unregister_class(cls)

	# Unregister Icons
	for pcoll in variable.PREVIEW_COLLECTIONS.values():
		bpy.utils.previews.remove(pcoll)
	variable.PREVIEW_COLLECTIONS.clear()