import bpy

#region Function
global message_content

def draw_message(self, context):
    self.layout.label(text=message_content)

def show_message(context, icon, content):
    global message_content
    message_content = content
    context.window_manager.popup_menu(draw_message, icon=icon)


def camera_zoom_value_ui_change(self, context):
    for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for region in area.regions:
                    if region.type == 'WINDOW':
                        ctx = context.copy()
                        ctx['area'] = area
                        ctx['region'] = region
                        with context.temp_override(**ctx):
                            # Set Camera
                            if len(bpy.context.selected_objects) > 0:
                                bpy.ops.view3d.view_selected()
                                bpy.ops.object.select_all(action='DESELECT')
                            else:
                                bpy.ops.view3d.view_all(center=False)
                            # Calculating
                            zoom_value = int((context.scene.camera_zoom_value - 100) / 10)
                            for _ in range(abs(zoom_value)):
                                if zoom_value > 0:
                                    bpy.ops.view3d.zoom(delta=1)
                                else:
                                    bpy.ops.view3d.zoom(delta=-1)
                            for o in bpy.context.selected_objects:
                                o.select_set(True)
                        break
                break

def bevel_value_ui_change(self, context):
    max_segment = 16
    segment_list = [(0.001, 1), (0.003, 2), (0.006, 4), (0.012, 5)]
    # unit: meter
    bevel_value = context.scene.bevel_unit_value

    for i in range(0, len(segment_list)):
        if bevel_value < segment_list[0][0]:
            segment = segment_list[0][1]
            break
        if bevel_value > segment_list[-1][0]:
            segment = int(bevel_value / segment_list[-1][0] * 5) 
            if segment > max_segment:
                segment = max_segment
            break
        if bevel_value == segment_list[i][0]:
            segment = segment_list[i][1]
            break
        if i < len(segment_list) - 1:
            if bevel_value < segment_list[i+1][0] and bevel_value > segment_list[i][0]:
                segment = segment_list[i][1] if (bevel_value - segment_list[i][0] < ((segment_list[i+1][0] - segment_list[i][0]) / 2)) else segment_list[i+1][1]
                break
    
    context.scene.bevel_segment_value = segment

    # If bevel modifier exists
    obj = context.active_object
    for mod in obj.modifiers:
        if mod.type == "BEVEL":
            if mod.name == context.scene.bevel_modifier_name:
                mod.width = context.scene.bevel_unit_value
                mod.segments = context.scene.bevel_segment_value
                break

def bevel_segment_ui_change(self, context):
    # If bevel modifier exists
    obj = context.active_object
    for mod in obj.modifiers:
        if mod.type == "BEVEL":
            if mod.name == context.scene.bevel_modifier_name:
                mod.segments = context.scene.bevel_segment_value
                break

def update_bevel_modifier_name_ui(self, context):
    if context.scene.bevel_type == "VGROUP":
        context.scene.bevel_modifier_name = "BevelV"
    elif context.scene.bevel_type == "WEIGHT":
        context.scene.bevel_modifier_name = "BevelW"
    elif context.scene.bevel_type == "ANGLE":
        context.scene.bevel_modifier_name = "BevelA"

def update_screenshot_path_ui(self, context):
    context.scene.screenshot_path = context.scene.screenshot_path.replace('\\', '/')
    return True

def update_bakeset_export_path_ui(self, context):
    context.scene.bakeset_export_path = context.scene.bakeset_export_path.replace('\\', '/')
    return None

def update_rizom_path_ui(self, context):
    context.scene.rizom_path = context.scene.rizom_path.replace('\\', '/')
    return True

def update_edge_length_value_ui(context, value):
    context.scene.edge_length_value = value
    return True

def update_circle_diameter_value_ui(context, value):
    context.scene.circle_diameter_value = value
    return True

def update_circle_angle_value_ui(context, value):
    context.scene.circle_angle_value = value
    return True