import bpy, blf, gpu
from bgl import *
from gpu_extras.batch import batch_for_shader

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