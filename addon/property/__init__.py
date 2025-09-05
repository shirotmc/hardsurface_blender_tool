import bpy

from .ui import TMC_UIProperty

classes = [
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