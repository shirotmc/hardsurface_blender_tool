import bpy, traceback

from ..utility.mouse import mouse_warp
from ..utility.draw import draw_quad, draw_text, get_blf_text_dims
from ..ui import controller

class TMC_OP_Boolean(bpy.types.Operator):
    bl_idname = "tmc.boolean"
    bl_label = "Boolean"
    bl_description = "Fast Boolean Union"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        sel = list(context.selected_objects)
        if context.active_object != None:
            if context.active_object.type == 'MESH':
                if sel:
                    active = context.view_layer.objects.active
                    if active in sel and len(sel) == 2:
                        return True
        return False

    def execute(self, context):
        sel = list(context.selected_objects)
        active = context.view_layer.objects.active
        boolean_obj = [o for o in sel if o is not active][0] 

        # set "Display as" of boolean object to "Wire"
        boolean_obj.display_type = 'WIRE'

        # create a collection for booleans if it doesn't exist
        boolean_collection_name = "HS_Boolean"
        if boolean_collection_name not in bpy.data.collections:
            boolean_collection = bpy.data.collections.new(boolean_collection_name)
            context.scene.collection.children.link(boolean_collection)
        # else get the collection
        else:
            boolean_collection = bpy.data.collections[boolean_collection_name]

        # add boolean modifier
        modifier = active.modifiers.new('Boolean', 'BOOLEAN')
        modifier.operation = 'DIFFERENCE'
        modifier.object = boolean_obj

        # move the boolean object to the boolean collection
        # Safely move the boolean object into the boolean collection.
        # Capture original collections first, then link to the target
        # and unlink from the originals (but don't unlink the target).
        try:
            orig_cols = list(boolean_obj.users_collection)
        except Exception:
            orig_cols = []
        try:
            if boolean_collection not in boolean_obj.users_collection:
                boolean_collection.objects.link(boolean_obj)
        except Exception:
            pass
        # Unlink from original collections except the boolean collection
        for col in orig_cols:
            try:
                if col is boolean_collection:
                    continue
                if boolean_obj.name in col.objects:
                    col.objects.unlink(boolean_obj)
            except Exception:
                pass

        # parent boolean object to main object but keep transform
        boolean_obj.parent = active
        boolean_obj.matrix_parent_inverse = active.matrix_world.inverted()

        # deselect all, set active object to active
        bpy.ops.object.select_all(action='DESELECT')
        active.select_set(True)

        # hide the collection in viewport
        context.view_layer.layer_collection.children.get(boolean_collection_name).hide_viewport = True

        return {'FINISHED'}