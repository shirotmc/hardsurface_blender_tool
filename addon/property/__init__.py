import bpy

from .preferences import TMC_Preferences
from .updater import TMC_Updater
from .color import TMC_Color
from .settings import TMC_Settings
from .ui import TMC_UIProperty

classes = [
	TMC_Updater,
	TMC_Color,
	TMC_Settings,
	TMC_Preferences,
	TMC_UIProperty
]

def register_properties():
	from bpy.utils import register_class
	for cls in classes:
		register_class(cls)
	
def unregister_properties():
	from bpy.utils import unregister_class
	for cls in reversed(classes):
		unregister_class(cls)