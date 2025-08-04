import bpy, traceback

from ..utility.mouse import mouse_warp
from ..utility.draw import draw_quad, draw_text, get_blf_text_dims
from ..utility.addon import get_prefs

from ..ui import controller

class TMC_OP_Bevel(bpy.types.Operator):
    bl_idname = "tmc.bevel"
    bl_label = "Bevel"
    bl_description = "Bevel Modal"
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
        self.limit_method_list = ["ANGLE", "WEIGHT", "VGROUP"]
        self.limit_method = 0
        self.original_width = 0
        self.original_segments = 2
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
            if mod.type == 'BEVEL':
                self.modifier = mod
                break
        
        if self.modifier == None:
            self.modifier = self.obj.modifiers.new('Bevel', 'BEVEL')

        self.width = self.modifier.width
        self.segments = self.modifier.segments
        self.limit_method = self.limit_method_list.index(self.modifier.limit_method)        
   
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
            self.modifier.width = self.original_width
            if self.created_modifier == True:
                self.obj.modifiers.remove(self.modifier)
            self.remove_shaders(context)
            return {'CANCELLED'}
        

        elif event.type == 'R' and event.value == 'PRESS':
            self.limit_method += 1
            if self.limit_method > 2:
                self.limit_method = 0
            self.modifier.limit_method = self.limit_method_list[self.limit_method]
            if self.limit_method == 0:
                self.modifier.angle_limit = 1.0471975512
            elif self.limit_method == 1:
                mode = bpy.context.active_object.mode
                if mode != 'OBJECT':
                    # we need to switch from Edit mode to Object mode so the selection gets updated
                    bpy.ops.object.mode_set(mode='OBJECT')
                    obj = bpy.context.active_object
                    obj_data = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
                    # create bevel weight edge data
                    if 'bevel_weight_edge' not in obj_data.attributes:
                        obj.data.attributes.new(
                            name='bevel_weight_edge',
                            type='FLOAT',
                            domain='EDGE'
                        )
                    for index, edge in enumerate(obj.data.edges):
                        if edge.select:
                            obj.data.attributes['bevel_weight_edge'].data[index].value = 1.0
                    # back to whatever mode we were in
                    bpy.ops.object.mode_set(mode=mode)
            elif self.limit_method == 2:
                if self.obj.vertex_groups.active_index == -1:
                    self.obj.vertex_groups.new(name="Bevel")
                self.modifier.vertex_group = self.obj.vertex_groups.active.name

        # Adjust Width
        elif event.type == 'MOUSEMOVE':
            delta = event.mouse_x - event.mouse_prev_x
            delta = delta / self.divisor
            self.modifier.width += delta
        
        # Adjust Segments
        elif event.type == 'WHEELUPMOUSE':
            self.modifier.segments += 1
        elif event.type == 'WHEELDOWNMOUSE':
            if self.modifier.segments > 1:
                self.modifier.segments -= 1


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
            print("2D Shader Failed in Bevel Modal")
            traceback.print_exc()
            self.remove_shaders(context)

    def draw_shaders_2d(self, context):

        prefs = get_prefs()

        # Props
        width_text = "Width: {:.2f}".format(self.modifier.width)
        segments_text = "Segments: {}".format(self.modifier.segments)
        limit_method_text = "Type: {}".format(self.limit_method_list[self.limit_method])

        font_size = prefs.settings.font_size
        dims = get_blf_text_dims(width_text, font_size)
        area_width = context.area.width
        padding = 8

        over_all_width = dims[0] + padding * 2
        over_all_height = dims[1] + padding * 2

        left_offset = abs((area_width - over_all_width) * 0.5)
        bottom_offset = 100

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
        # Draw Width Text
        draw_text(text=width_text, x=x, y=y, size=font_size, color=prefs.color.font_color)
        # Draw Segments Text
        draw_text(text=segments_text, x=x, y=y - 20, size=font_size, color=prefs.color.font_color)
        # Draw Limit Method Text
        draw_text(text=limit_method_text, x=x, y=y - 40, size=font_size, color=prefs.color.font_color)


class TMC_OP_BevelCustomSetting(bpy.types.Operator):
    bl_idname = "tmc.bevel_with_custom_setting"
    bl_label = "Custom Bevel"
    bl_description = "Bevel with custom setting"

    def execute(self, context):
        # Get the custom bevel settings from the scene properties
        is_exists = False
        obj = context.active_object
        for mod in obj.modifiers:
            if mod.type == "BEVEL":
                if mod.name == context.scene.bevel_modifier_name:
                    is_exists = True
                    break
        if not is_exists:
            # Create Bevel Vertex Group Modifier
            mod = obj.modifiers.new(context.scene.bevel_modifier_name, 'BEVEL')
            mod.offset_type = 'OFFSET'
            mod.width = context.scene.bevel_unit_value
            mod.segments = context.scene.bevel_segment_value
            mod.limit_method = context.scene.bevel_type
            mod.miter_outer = 'MITER_ARC'
            mod.miter_inner = 'MITER_SHARP'
            mod.use_clamp_overlap = False
            mod.loop_slide = True
            if context.scene.bevel_type == "VGROUP":
                # Create Vertex Group
                new_vertex_group = bpy.context.object.vertex_groups.new(name=context.scene.bevel_modifier_name)
                bpy.ops.object.vertex_group_assign()
                mod.vertex_group = new_vertex_group.name
            elif context.scene.bevel_type == "WEIGHT":
                mode = bpy.context.active_object.mode
                if mode != 'OBJECT':
                    # we need to switch from Edit mode to Object mode so the selection gets updated
                    bpy.ops.object.mode_set(mode='OBJECT')
                    obj = bpy.context.active_object
                    obj_data = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
                    # create bevel weight edge data
                    if 'bevel_weight_edge' not in obj_data.attributes:
                        obj.data.attributes.new(
                            name='bevel_weight_edge',
                            type='FLOAT',
                            domain='EDGE'
                        )
                    for index, edge in enumerate(obj.data.edges):
                        if edge.select:
                            obj.data.attributes['bevel_weight_edge'].data[index].value = 1.0
                    # back to whatever mode we were in
                    bpy.ops.object.mode_set(mode=mode)
            elif context.scene.bevel_type == "ANGLE":
                mod.angle_limit = 1.0471975512 # 60 Degrees
        else:
            controller.show_message(context, "ERROR", "This name already exists. Please enter another name!")
        return {'FINISHED'}

class TMC_OP_GetBevelModifiersFromVertex(bpy.types.Operator):
    bl_idname = "tmc.get_bevel_modifiers_from_vertex"
    bl_label = "Get Bevel Modifiers From Vertex"
    bl_description = "Get bevel modifiers from vertex"

    def execute(self, context):
        vtg_list = []
        have_vertex_group_bevel = False
        obj = bpy.context.selected_objects[0]
        # Get selected verties
        edit_mode = bpy.context.active_object.mode
        bpy.ops.object.mode_set(mode='OBJECT')
        selected_vertices = [v.index for v in bpy.context.active_object.data.vertices if v.select]
        bpy.ops.object.mode_set(mode=edit_mode)
    
        for vert in selected_vertices:
            for group in obj.vertex_groups:
                vert_in_group = [vert.index for vert in obj.data.vertices if group.index in [i.group for i in vert.groups]]
                if vert in vert_in_group and group.name not in vtg_list:
                    vtg_list.append(group.name)

        modifier_list = obj.modifiers
        for mod in modifier_list:
            if mod.type == "BEVEL":
                if mod.limit_method == "VGROUP":
                    if mod.vertex_group in vtg_list:
                        mod.show_expanded = True
                        have_vertex_group_bevel = True
                    else:
                        mod.show_expanded = False
                else:
                    mod.show_expanded = False
            else:
                mod.show_expanded = False
        if not have_vertex_group_bevel:
            controller.show_message(context, "ERROR", "Object doesn't have bevel vertex group modifier!")
        return {'FINISHED'}