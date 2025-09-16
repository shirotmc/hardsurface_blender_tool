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

# class TMC_OP_Boolean(bpy.types.Operator):
#     bl_idname = "tmc.boolean"
#     bl_label = "Boolean"
#     bl_description = "Boolean Modal"
#     bl_options = {"REGISTER", "UNDO", "BLOCKING"}

#     @classmethod
#     def poll(cls, context):
#         sel = list(context.selected_objects)
#         if context.active_object != None:
#             if context.active_object.type == 'MESH':
#                 if sel:
#                     active = context.view_layer.objects.active
#                     if active in sel and len(sel) == 2:
#                         return True
#         return False


#     def invoke(self, context, event):
#         sel = list(context.selected_objects)
#         active = context.view_layer.objects.active

#         # Props
#         self.boolean_method_list = ["UNION", "INTERSECT", "DIFFERENCE"]
#         self.boolean_method = 2
#         self.boolean_obj = [o for o in sel if o is not active][0] 
#         self.obj = context.active_object

#         # Initialize
#         self.setup(context)
#         self.draw_handle = bpy.types.SpaceView3D.draw_handler_add(self.draw_shaders_2d, (context,), 'WINDOW', 'POST_PIXEL')
#         context.window_manager.modal_handler_add(self)
#         return {"RUNNING_MODAL"}

#     def remove_shaders(self, context):
#         '''Remove shader handle'''

#         if self.draw_handle != None:
#             self.draw_handle = bpy.types.SpaceView3D.draw_handler_remove(self.draw_handle, "WINDOW")
#             context.area.tag_redraw()

#     def safe_draw_shader_2d(self, context):
#         try:
#             self.draw_shaders_2d(context)
#         except Exception:
#             print("2D Shader Failed in Bevel Modal")
#             traceback.print_exc()
#             self.remove_shaders(context)

#     def draw_shaders_2d(self, context):

#         # Props
#         boolean_method_text = "Type: {}".format(self.boolean_method_list[self.boolean_method])

#         font_size = 16
#         dims = get_blf_text_dims(boolean_method_text, font_size)
#         area_width = context.area.width
#         padding = 8

#         over_all_width = dims[0] + padding * 2
#         over_all_height = dims[1] + padding * 2

#         left_offset = abs((area_width - over_all_width) * 0.5)
#         bottom_offset = 100

#         top_left = (area_width, bottom_offset + over_all_height)
#         bot_left = (area_width, bottom_offset)
#         top_right = (area_width + over_all_width, bottom_offset + over_all_height)
#         bot_right = ( area_width + over_all_width, bottom_offset)
        
#         # Draw Quad
#         verts = [top_left, bot_left, top_right, bot_right]
#         draw_quad(vertices=verts, color=(0, 0, 0, 0.75))

#         # Draw Text
#         x = left_offset + padding
#         y = bottom_offset + padding
#         # Draw Boolean Method Text
#         draw_text(text=boolean_method_text, x=x, y=y, size=font_size, color=(1, 1, 1, 1))

#     def setup(self, context):
#         self.modifier = self.obj.modifiers.new('Boolean', 'BOOLEAN')
#         self.boolean_method = self.boolean_method_list.index(self.modifier.operation)
#         self.modifier.object = self.boolean_obj
#         self.boolean_obj.hide_set(True)

#     def modal(self, context, event):

#         # Free navigation
#         if event.type == 'MIDDLEMOUSE':
#             return {'PASS_THROUGH'}
        
#         # Confirm
#         elif event.type == 'LEFTMOUSE' and event.value == 'PRESS':
#             # create a collection for booleans if it doesn't exist
#             boolean_collection_name = "HS_Boolean"
#             if boolean_collection_name not in bpy.data.collections:
#                 boolean_collection = bpy.data.collections.new(boolean_collection_name)
#                 context.scene.collection.children.link(boolean_collection)
#             # else get the collection
#             else:
#                 boolean_collection = bpy.data.collections[boolean_collection_name]
#             # move the boolean object to the boolean collection, i mean move the object to the collection correct the code
#             boolean_collection.objects.link(self.boolean_obj)
#             self.boolean_obj.users_collection[0].objects.unlink(self.boolean_obj)
#             # parent boolean object to main object but keep transform, show me code
#             self.boolean_obj.parent = self.obj
#             self.boolean_obj.matrix_parent_inverse = self.obj.matrix_world.inverted()
#             # set the active object to the main object
#             bpy.context.view_layer.objects.active = self.obj
#             self.boolean_obj.hide_set(False)
#             # hide the collection in viewport, i mean the eye icon, ignore the render icon
#             bpy.context.view_layer.layer_collection.children.get(boolean_collection_name).hide_viewport = True
#             self.remove_shaders(context)
#             return {'FINISHED'}

#         # Cancel
#         elif event.type == 'RIGHTMOUSE' and event.value == 'PRESS':
#             self.obj.modifiers.remove(self.modifier)
#             self.boolean_obj.hide_set(False)
#             self.remove_shaders(context)
#             return {'CANCELLED'}
        
#         # Change Boolean Method
#         elif event.type == 'WHEELUPMOUSE':
#             if self.modifier.operation == 'UNION':
#                 self.modifier.operation = 'INTERSECT'
#                 self.boolean_method = 1
#             elif self.modifier.operation == 'DIFFERENCE':
#                 self.modifier.operation = 'UNION'
#                 self.boolean_method = 0
#             elif self.modifier.operation == 'INTERSECT':
#                 self.modifier.operation = 'DIFFERENCE'
#                 self.boolean_method = 2
#         elif event.type == 'WHEELDOWNMOUSE':
#             if self.modifier.operation == 'UNION':
#                 self.modifier.operation = 'DIFFERENCE'
#                 self.boolean_method = 2
#             elif self.modifier.operation == 'DIFFERENCE':
#                 self.modifier.operation = 'INTERSECT'
#                 self.boolean_method = 1
#             elif self.modifier.operation == 'INTERSECT':
#                 self.modifier.operation = 'UNION'
#                 self.boolean_method = 0


#         return {"RUNNING_MODAL"}
    
#     def remove_shaders(self, context):
#         '''Remove shader handle'''

#         if self.draw_handle != None:
#             self.draw_handle = bpy.types.SpaceView3D.draw_handler_remove(self.draw_handle, "WINDOW")
#             context.area.tag_redraw()

#     def safe_draw_shader_2d(self, context):
#         try:
#             self.draw_shaders_2d(context)
#         except Exception:
#             print("2D Shader Failed in Bevel Modal")
#             traceback.print_exc()
#             self.remove_shaders(context)

#     def draw_shaders_2d(self, context):

#         # Props
#         boolean_method_text = "Type: {}".format(self.boolean_method_list[self.boolean_method])

#         font_size = 16
#         dims = get_blf_text_dims(boolean_method_text, font_size)
#         area_width = context.area.width
#         padding = 8

#         over_all_width = dims[0] + padding * 2
#         over_all_height = dims[1] + padding * 2

#         left_offset = abs((area_width - over_all_width) * 0.5)
#         bottom_offset = 100

#         top_left = (area_width, bottom_offset + over_all_height)
#         bot_left = (area_width, bottom_offset)
#         top_right = (area_width + over_all_width, bottom_offset + over_all_height)
#         bot_right = ( area_width + over_all_width, bottom_offset)
        
#         # Draw Quad
#         verts = [top_left, bot_left, top_right, bot_right]
#         draw_quad(vertices=verts, color=(0, 0, 0, 0.75))

#         # Draw Text
#         x = left_offset + padding
#         y = bottom_offset + padding
#         # Draw Boolean Method Text
#         draw_text(text=boolean_method_text, x=x, y=y - 40, size=font_size, color=(1, 1, 1, 1))