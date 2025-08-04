import bpy

from ..operator import updater

from ..utility.addon import addon_name, get_prefs
from bpy.props import PointerProperty

from .updater import TMC_Updater, draw_updater
from .color import TMC_Color, draw_color
from .settings import TMC_Settings, draw_settings

class TMC_Preferences(bpy.types.AddonPreferences):
    bl_idname = addon_name

    # Properties Groups
    updater: PointerProperty(type=TMC_Updater)
    color: PointerProperty(type=TMC_Color)
    settings: PointerProperty(type=TMC_Settings)

    def draw(self, context):

        prefs = get_prefs()
        layout = self.layout

        # Addon updater settings 
        box = layout.box()
        draw_updater(prefs, box)

        # Color settings
        box = layout.box()
        draw_color(prefs, box)

        # Drawing settings
        box = layout.box()
        draw_settings(prefs, box)
