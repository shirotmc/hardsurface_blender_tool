import bpy, traceback
from mathutils import Vector

from ..utility.draw import draw_quad, draw_text, get_blf_text_dims
from ..utility.addon import get_prefs
from ..utility.ray import mouse_raycast_to_plane, mouse_raycast_to_scene


class TMC_OP_Ray(bpy.types.Operator):
    bl_idname = "tmc.ray_caster"
    bl_label = "Raycaster"
    bl_description = "Raycaster Modal"
    bl_options = {"REGISTER", "UNDO", "BLOCKING"}

    @classmethod
    def poll(cls, context):

        if context.active_object != None:
            if context.active_object.type == 'MESH':
                return True
        return False


    def invoke(self, context, event):
    
        self.obj = context.active_object
        self.scene_cast = True 
        self.intersection = Vector((0, 0, 0))
        self.draw_handle = bpy.types.SpaceView3D.draw_handler_add(self.draw_shaders_2d, (context,), 'WINDOW', 'POST_PIXEL')
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}
   
    def modal(self, context, event):

        # Free navigation
        if event.type == 'MIDDLEMOUSE':
            return {'PASS_THROUGH'}
        
        # Exit
        elif event.type in {'LEFTMOUSE', 'RIGHTMOUSE'} and event.value == 'PRESS':
            self.remove_shaders(context)
            return {'FINISHED'}
        
        # Change ray cast method
        elif event.type == 'R' and event.value == 'PRESS':
            self.scene_cast = not self.scene_cast

        # Adjust
        elif event.type == 'MOUSEMOVE':

            # Scene raycast
            if self.scene_cast == True:
                hit, location, normal, index, object, matrix = mouse_raycast_to_scene(context, event)
                if hit:
                    self.intersection = location
                
            # Line plane raycast
            else:
                mouse = (event.mouse_region_x, event.mouse_region_y)
                point = Vector((0, 0, 0))
                normal = Vector((0, 0, 1))
                self.intersection = mouse_raycast_to_plane(mouse, context, point, normal)
                self.obj.location = self.intersection
        
        context.area.tag_redraw()
        return {"RUNNING_MODAL"}

    def remove_shaders(self, context):
        '''Remove shader handle'''

        if self.draw_handle != None:
            self.draw_handle = bpy.types.SpaceView3D.draw_handler_remove(self.draw_handle, "WINDOW")
            context.area.tag_redraw()

    def safe_draw_shader_2d(self, context):
        try:
            self.draw_shaders_2d(context)
        except Exception:
            print("2D Shader Failed in Ray-Caster")
            traceback.print_exc()
            self.remove_shaders(context)

    def draw_shaders_2d(self, context):

        prefs = get_prefs()

        # Props
        text = "X: {:.3f}, Y: {:.3f}, Z: {:.3f}".format(self.intersection.x, self.intersection.y, self.intersection.z)
        font_size = prefs.settings.font_size
        dims = get_blf_text_dims(text, font_size)
        area_width = context.area.width
        padding = 8

        over_all_width = dims[0] + padding * 2
        over_all_height = dims[1] + padding * 2

        left_offset = abs((area_width - over_all_width) * 0.5)
        bottom_offset = 20

        top_left = (area_width, bottom_offset + over_all_height)
        bot_left = (area_width, bottom_offset)
        top_right = (area_width + over_all_width, bottom_offset + over_all_height)
        bot_right = ( area_width + over_all_width, bottom_offset)
        
        # Draw Quad
        verts = [top_left, bot_left, top_right, bot_right]
        draw_quad(vertices=verts, color=prefs.color.bg_color)

        # Draw Text
        x = left_offset + padding
        y = bottom_offset + padding
        draw_text(text=text, x=x, y=y, size=font_size, color=prefs.color.font_color)

        # Draw ray type
        text = "SCENE" if self.scene_cast else "PLANE"
        draw_text(text=text, x=x, y=y + over_all_height + padding, size=font_size, color=prefs.color.font_color)

    