bl_info = {
	"name": "HardSurface Tool",
	"description": "This add-on provides a set of custom tools for working efficiently in Blender.",
	"author": "Canh Tran",
	"version": (1, 0, 6),
	"blender": (2, 80, 0),
	"location": "View3D",
	"category": "3D View"
}

import sys
sys.dont_write_bytecode = True
from .addon.operator import updater
from .addon.register import register_addon, unregister_addon

def register():
    # Update add-ons
    updater.register(bl_info)
    # Unregister add-ons
    register_addon()

def unregister():
    # Update add-ons
    updater.unregister()
    # Unregister add-ons
    unregister_addon()