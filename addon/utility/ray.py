import bpy, mathutils

from bpy_extras import view3d_utils
from mathutils import Vector

def mouse_raycast_to_plane(mouse_pos, context, point, normal):

    # Get the context arguments
    region = context.region
    rv3d = context.region_data
    intersection = Vector((0, 0, 0))
    try:
        # Camera Origin
        origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, mouse_pos)
        # Mouse Origin
        mouse = view3d_utils.region_2d_to_vector_3d(region, rv3d, mouse_pos)
        # Camera Origin + Mouse
        ray_origin = origin + mouse
        # From the mouse to the viewport
        loc = view3d_utils.region_2d_to_location_3d(region, rv3d, mouse_pos, ray_origin - origin)
        # Ray to plane
        intersection = mathutils.geometry.intersect_line_plane(ray_origin, loc, point, normal)
    
    except:
        intersection = Vector((0, 0, 0))

    if intersection ==  None:
        intersection = Vector((0, 0, 0))
    
    return intersection

def mouse_raycast_to_scene(context, event):

    mouse_pos = (event.mouse_region_x, event.mouse_region_y)

    origin = view3d_utils.region_2d_to_origin_3d(bpy.context.region, bpy.context.region_data, mouse_pos)
    direction = view3d_utils.region_2d_to_vector_3d(bpy.context.region, bpy.context.region_data, mouse_pos)

    hit, location, normal, index, object, matrix = context.scene.ray_cast(context.view_layer.depsgraph, origin, direction)
    return hit, location, normal, index, object, matrix