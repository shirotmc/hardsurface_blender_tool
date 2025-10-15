import bpy
import blf
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Vector, Matrix, Quaternion
from math import sin, cos, pi
import os

# NOTE: These helpers are Blender 4.x safe and avoid deprecated bgl state.
# They provide commonly needed draw operations in both 3D (POST_VIEW) and 2D (POST_PIXEL).

def draw_quad(vertices=[], color=(1,1,1,1)):
    '''Vertices = Top Left, Bottom Left, Top Right, Bottom Right'''
    indices = [(0, 1, 2), (1, 2, 3)]
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'TRIS', {"pos": vertices}, indices=indices)
    shader.bind()
    shader.uniform_float("color", color)
    gpu.state.blend_set("ALPHA")
    batch.draw(shader)
    gpu.state.blend_set("NONE")
    
    del shader
    del batch

def draw_text(text, x, y, size=12, color=(1,1,1,1)):

    font = 0
    blf.size(font, size)
    blf.color(font, *color)
    blf.position(font, x, y, 0)
    blf.draw(font, text)

def get_blf_text_dims(text, size):
    '''Return the total width of the string'''

    blf.size(0, size)
    return blf.dimensions(0, str(text))

# ----------------------
# New Drawing Utilities
# ----------------------

def _polyline_shader():
    # In 4.x, polyline shaders are 'POLYLINE_UNIFORM_COLOR' and 'POLYLINE_SMOOTH_COLOR'
    return gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR')

def _polyline_smooth_shader():
    return gpu.shader.from_builtin('POLYLINE_SMOOTH_COLOR')

def _uniform_shader(mode='3D'):
    # mode is ignored in Blender 4.x, kept for compatibility
    return gpu.shader.from_builtin('UNIFORM_COLOR')

def draw_point(co, mx=Matrix(), color=(1,1,1,1), size=6, xray=True):
    shader = _uniform_shader()
    shader.bind()
    shader.uniform_float('color', color)
    gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
    gpu.state.blend_set('ALPHA' if color[-1] < 1 else 'NONE')
    gpu.state.point_size_set(size)
    batch = batch_for_shader(shader, 'POINTS', {"pos": [mx @ co]})
    batch.draw(shader)

def draw_points(coords, mx=Matrix(), color=(1,1,1,1), size=4, xray=True, indices=None):
    shader = _uniform_shader()
    shader.bind()
    shader.uniform_float('color', color)
    gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
    gpu.state.blend_set('ALPHA' if color[-1] < 1 else 'NONE')
    gpu.state.point_size_set(size)
    pos = [mx @ c for c in coords] if mx != Matrix() else coords
    batch = batch_for_shader(shader, 'POINTS', {"pos": pos}, indices=indices)
    batch.draw(shader)

def draw_line(coords, mx=Matrix(), color=(1,1,1,1), width=1.0, xray=True, indices=None):
    # Connect consecutive points if indices not provided
    if indices is None and coords:
        indices = [(i, i+1) for i in range(len(coords)-1)]
    gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
    gpu.state.blend_set('ALPHA')
    shader = _polyline_shader()
    shader.bind()
    shader.uniform_float('color', color)
    shader.uniform_float('lineWidth', float(width))
    shader.uniform_float('viewportSize', gpu.state.scissor_get()[2:])
    pos = [mx @ c for c in coords] if mx != Matrix() else coords
    batch = batch_for_shader(shader, 'LINES', {"pos": pos}, indices=indices)
    batch.draw(shader)

def draw_lines(coords, mx=Matrix(), color=(1,1,1,1), width=1.0, xray=True, indices=None):
    # Treat coords as pairs; generate indices if not provided
    if indices is None:
        indices = [(i, i+1) for i in range(0, len(coords), 2) if i+1 < len(coords)]
    gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
    gpu.state.blend_set('ALPHA')
    shader = _polyline_shader()
    shader.bind()
    shader.uniform_float('color', color)
    shader.uniform_float('lineWidth', float(width))
    shader.uniform_float('viewportSize', gpu.state.scissor_get()[2:])
    pos = [mx @ c for c in coords] if mx != Matrix() else coords
    batch = batch_for_shader(shader, 'LINES', {"pos": pos}, indices=indices)
    batch.draw(shader)

def draw_vector(vector, origin=Vector((0,0,0)), mx=Matrix(), color=(1,1,1,1), width=1.0, fade=False, xray=True):
    # Optionally fade the vector tail
    gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
    gpu.state.blend_set('ALPHA')
    if fade:
        shader = _polyline_smooth_shader()
        coords = [mx @ origin, mx @ origin + (mx.to_3x3() @ vector)]
        cols = (color, (*color[:3], color[3] * 0.1))
        shader.bind()
        shader.uniform_float('lineWidth', float(width))
        shader.uniform_float('viewportSize', gpu.state.scissor_get()[2:])
        batch = batch_for_shader(shader, 'LINES', {"pos": coords, "color": cols})
        batch.draw(shader)
    else:
        draw_line([origin, origin + vector], mx=mx, color=color, width=width, xray=xray)

def draw_vectors(vectors, origins, mx=Matrix(), color=(1,1,1,1), width=1.0, fade=False, xray=True):
    coords = []
    if fade:
        cols = []
    for v, o in zip(vectors, origins):
        a = mx @ o
        b = a + (mx.to_3x3() @ v)
        coords.extend([a, b])
        if fade:
            cols.extend([color, (*color[:3], color[3]*0.1)])
    gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
    gpu.state.blend_set('ALPHA')
    if fade:
        shader = _polyline_smooth_shader()
        shader.bind()
        shader.uniform_float('lineWidth', float(width))
        shader.uniform_float('viewportSize', gpu.state.scissor_get()[2:])
        indices = [(i, i+1) for i in range(0, len(coords), 2)]
        batch = batch_for_shader(shader, 'LINES', {"pos": coords, "color": cols}, indices=indices)
        batch.draw(shader)
    else:
        draw_lines(coords, color=color, width=width, xray=xray)

def draw_tris(coords, mx=Matrix(), color=(1,1,1,1), indices=None, xray=True):
    shader = _uniform_shader()
    shader.bind()
    shader.uniform_float('color', color)
    gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
    gpu.state.blend_set('ALPHA' if color[-1] < 1 else 'NONE')
    pos = [mx @ c for c in coords] if mx != Matrix() else coords
    batch = batch_for_shader(shader, 'TRIS', {"pos": pos}, indices=indices)
    batch.draw(shader)

def draw_image_2d(image, x, y, w, h, color=(1,1,1,1), src_rect=None):
    """Draw a Blender image in 2D screen space (POST_PIXEL).
    src_rect: optional (sx, sy, sw, sh) in pixels to sample from the image (origin top-left of image).
    """
    if image is None:
        return
    try:
        tex = gpu.texture.from_image(image)
    except Exception:
        return
    shader = gpu.shader.from_builtin('IMAGE')
    # positions in screen space
    pos = [(x, y, 0), (x+w, y, 0), (x+w, y+h, 0), (x, y+h, 0)]
    if src_rect is None:
        uv = [(0, 0), (1, 0), (1, 1), (0, 1)]
    else:
        sx, sy, sw, sh = src_rect
        iw = image.size[0] if hasattr(image, 'size') else tex.width
        ih = image.size[1] if hasattr(image, 'size') else tex.height
        # Blender image origin is bottom-left; src_rect uses top-left origin, convert Y
        sy_bl = ih - (sy + sh)
        u0 = sx / iw; v0 = sy_bl / ih
        u1 = (sx + sw) / iw; v1 = (sy_bl + sh) / ih
        uv = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
    idx = [(0,1,2), (0,2,3)]
    gpu.state.blend_set('ALPHA')
    shader.bind()
    shader.uniform_sampler('image', tex)
    batch = batch_for_shader(shader, 'TRIS', {"pos": pos, "texCoord": uv}, indices=idx)
    batch.draw(shader)

def draw_mesh_wire(data, color=(1,1,1,1), width=1.0, xray=True):
    # data can be (coords, indices) or a GPU batch tuple
    if isinstance(data, tuple) and len(data) == 2 and isinstance(data[0], list):
        coords, indices = data
    else:
        # Assume it's already in coords,indices form
        coords, indices = data
    gpu.state.depth_test_set('NONE' if xray else 'LESS_EQUAL')
    gpu.state.blend_set('ALPHA')
    shader = _polyline_shader()
    shader.bind()
    shader.uniform_float('color', color)
    shader.uniform_float('lineWidth', float(width))
    shader.uniform_float('viewportSize', gpu.state.scissor_get()[2:])
    batch = batch_for_shader(shader, 'LINES', {"pos": coords}, indices=indices)
    batch.draw(shader)

def draw_bbox(bbox, mx=Matrix(), color=(1,1,1,1), width=1.0, corners=0.0, xray=True):
    if corners and corners > 0:
        # Draw corner ticks instead of full edges
        coords = []
        for i in range(8):
            base = bbox[i]
            # Each corner connects to 3 edges; approximate by directions to other points sharing axis
            # Use neighboring points: We map the standard cube corners across connected points
        # Build a standard set using bbox indexing
        b = bbox
        c = corners
        coords = [
            b[0], b[0] + (b[1]-b[0])*c, b[0], b[0] + (b[3]-b[0])*c, b[0], b[0] + (b[4]-b[0])*c,
            b[1], b[1] + (b[0]-b[1])*c, b[1], b[1] + (b[2]-b[1])*c, b[1], b[1] + (b[5]-b[1])*c,
            b[2], b[2] + (b[1]-b[2])*c, b[2], b[2] + (b[3]-b[2])*c, b[2], b[2] + (b[6]-b[2])*c,
            b[3], b[3] + (b[0]-b[3])*c, b[3], b[3] + (b[2]-b[3])*c, b[3], b[3] + (b[7]-b[3])*c,
            b[4], b[4] + (b[0]-b[4])*c, b[4], b[4] + (b[5]-b[4])*c, b[4], b[4] + (b[7]-b[4])*c,
            b[5], b[5] + (b[1]-b[5])*c, b[5], b[5] + (b[4]-b[5])*c, b[5], b[5] + (b[6]-b[5])*c,
            b[6], b[6] + (b[2]-b[6])*c, b[6], b[6] + (b[5]-b[6])*c, b[6], b[6] + (b[7]-b[6])*c,
            b[7], b[7] + (b[3]-b[7])*c, b[7], b[7] + (b[4]-b[7])*c, b[7], b[7] + (b[6]-b[7])*c,
        ]
        draw_lines([mx @ p for p in coords], color=color, width=width, xray=xray)
        return
    # Full wireframe bbox
    indices = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),(0,4),(1,5),(2,6),(3,7)]
    draw_line([mx @ p for p in bbox], color=color, width=width, xray=xray, indices=indices)

def draw_circle(loc=Vector(), rot=Quaternion(), radius=1.0, segments=64, color=(1,1,1,1), width=1.0, xray=True):
    segs = max(16, int(radius*segments) if segments == 'AUTO' else int(segments))
    coords = []
    for i in range(segs):
        theta = 2*pi*i/segs
        coords.append(Vector((cos(theta)*radius, sin(theta)*radius, 0)))
    # close the loop by repeating the first vertex so polyline drawing connects end->start
    if coords:
        coords.append(coords[0])
    # transform into place
    mx = Matrix.LocRotScale(loc, rot, Vector((1,1,1))) if len(loc) == 3 else Matrix()
    draw_line([mx @ p for p in coords], color=color, width=width, xray=xray)

def draw_cross_3d(co, mx=Matrix(), color=(1,1,1,1), width=1.0, length=1.0, xray=True):
    x = Vector((1,0,0)); y = Vector((0,1,0)); z = Vector((0,0,1))
    coords = [co - x*length, co + x*length, co - y*length, co + y*length, co - z*length, co + z*length]
    draw_lines([mx @ p for p in coords], color=color, width=width, xray=xray)

def draw_label(context, title='', coords=None, center=True, size=12, color=(1,1,1,1)):
    # Simple label draw; when center=True, centers horizontally around coords.x
    font = 0
    scale = context.preferences.system.ui_scale
    fontsize = int(size * scale)
    blf.size(font, fontsize)
    # Ensure color has 4 components (r,g,b,a)
    if color is None:
        color = (1.0, 1.0, 1.0, 1.0)
    elif len(color) == 3:
        color = (color[0], color[1], color[2], 1.0)
    elif len(color) >= 4:
        color = (color[0], color[1], color[2], color[3])
    blf.color(font, *color)

    # Resolve coords (accept Vector or (x,y))
    if coords is None:
        x = context.region.width / 2
        y = context.region.height / 2
    else:
        try:
            x, y = coords
        except Exception:
            # If coords is a Vector-like with x/y attributes
            x = getattr(coords, 'x', 0)
            y = getattr(coords, 'y', 0)

    if center:
        dims = blf.dimensions(font, title)
        blf.position(font, x - dims[0] / 2, y, 0)
    else:
        blf.position(font, x, y, 0)
    blf.draw(font, title)

def get_text_dimensions(context, text='', size=12):
    font = 0
    scale = context.preferences.system.ui_scale
    blf.size(font, int(size*scale))
    return blf.dimensions(font, text)
