import bpy, traceback

from ..utility.mouse import mouse_warp
from ..utility.draw import draw_quad, draw_text, get_blf_text_dims
from ..utility.addon import get_prefs

from ..ui import controller
from ..utility import variable

class TMC_OP_ToggleCurrentHideGroup(bpy.types.Operator):
    bl_idname = "tmc.toggle_current_hide_group"
    bl_label = "Toggle Current Hide Group"
    bl_description = "Toggle Current Hide Group"

    def getChildrenCollectionRecursion(self, result_list, collection_list):
        for children_collection in collection_list:
            result_list.append(children_collection)
            self.getChildrenCollectionRecursion(result_list, children_collection.children)

    def execute(self, context):
        # Fetch the area
        outliner = next(a for a in bpy.context.screen.areas if a.type == "OUTLINER") 
        outliner.spaces[0].show_restrict_column_viewport = True

        #Get all Layer Collection
        result_list = []
        children_list = bpy.context.view_layer.layer_collection.children
        self.getChildrenCollectionRecursion(result_list, children_list)
        if variable.UNHIDE_COLLECTION_BOOL == True:
            variable.HIDE_COLLECTION_LIST = []
            for collection in result_list:
                if collection.hide_viewport == True or bpy.data.collections[collection.name].hide_viewport == True:
                    collection.hide_viewport = False
                    bpy.data.collections[collection.name].hide_viewport = False
                    variable.HIDE_COLLECTION_LIST.append(collection)
                collection.exclude = False
                bpy.data.collections[collection.name].hide_select = False
                bpy.data.collections[collection.name].hide_render = False
        else:
            for collection in variable.HIDE_COLLECTION_LIST:
                collection.hide_viewport = True
                bpy.data.collections[collection.name].hide_viewport = True
                collection.exclude = False
                bpy.data.collections[collection.name].hide_select = False
                bpy.data.collections[collection.name].hide_render = False
        variable.UNHIDE_COLLECTION_BOOL = not variable.UNHIDE_COLLECTION_BOOL
        return {'FINISHED'}