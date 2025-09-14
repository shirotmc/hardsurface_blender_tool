import bpy

from .ui import TMC_UIProperty

classes = [
	TMC_UIProperty
]

def register_properties():
	from bpy.utils import register_class
	for cls in classes:
		register_class(cls)
	# material row types/collections removed for rework

def unregister_properties():
	from bpy.utils import unregister_class
	# unregister material row and remove scene props
	# material row types/collections removed for rework
	for cls in reversed(classes):
		unregister_class(cls)
	# TMC_MaterialRow removed during rework; nothing else to unregister here
    