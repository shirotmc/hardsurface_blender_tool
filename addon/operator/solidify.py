import bpy, traceback
from ..utility.mouse import mouse_warp
from ..utility.draw import draw_quad, draw_text, get_blf_text_dims
from ..utility.addon import get_prefs

class TMC_OP_Solidify(bpy.types.Operator):
    bl_idname = "tmc.solidify"
    bl_label = "Solidify"
    bl_description = "Solidify Modal"
    bl_options = {"REGISTER", "UNDO", "BLOCKING"}

    @classmethod
    def poll(cls, context):

        if context.active_object != None:
            if context.active_object.type == 'MESH':
                return True
        return False


    def invoke(self, context, event):
        
        # Props
        self.created_modifier = False
        self.original_thickness = 0
        self.modifier = None
        self.obj = context.active_object
        self.divisor = 1000

        # Initialize
        self.setup(context)
        self.draw_handle = bpy.types.SpaceView3D.draw_handler_add(self.draw_shaders_2d, (context,), 'WINDOW', 'POST_PIXEL')
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def setup(self, context):
        for mod in self.obj.modifiers:
            if mod.type == 'SOLIDIFY':
                self.modifier = mod
                break
        
        if self.modifier == None:
            self.modifier = self.obj.modifiers.new('Solidify', 'SOLIDIFY')

        self.original_thickness = self.modifier.thickness
   
    def modal(self, context, event):

        # Utils
        mouse_warp(context, event)

        # Free navigation
        if event.type == 'MIDDLEMOUSE':
            return {'PASS_THROUGH'}
        
        # Confirm
        elif event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.remove_shaders(context)
            return {'FINISHED'}

        # Cancel
        elif event.type == 'RIGHTMOUSE' and event.value == 'PRESS':
            self.modifier.thickness = self.original_thickness
            if self.created_modifier == True:
                self.obj.modifiers.remove(self.modifier)
            self.remove_shaders(context)
            return {'CANCELLED'}
        
        # Adjust
        elif event.type == 'MOUSEMOVE':
            delta = event.mouse_x - event.mouse_prev_x
            delta = delta / self.divisor
            self.modifier.thickness += delta

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
            print("2D Shader Failed in Solidify")
            traceback.print_exc()
            self.remove_shaders(context)

    def draw_shaders_2d(self, context):

        prefs = get_prefs()

        # Props
        text = "Thickness: {:.2f}".format(self.modifier.thickness)
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