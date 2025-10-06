import bpy
import bmesh
from bpy.props import EnumProperty, BoolProperty, IntProperty
from bpy_extras.view3d_utils import (
    region_2d_to_origin_3d,
    region_2d_to_vector_3d,
    location_3d_to_region_2d,
)
from bpy_extras.view3d_utils import region_2d_to_location_3d, location_3d_to_region_2d

try:
    from bl_ui.space_statusbar import STATUSBAR_HT_header as _STATUSBAR
except Exception:
    _STATUSBAR = None
from mathutils import Vector, Matrix, Quaternion
from mathutils.geometry import (
    intersect_line_plane,
    intersect_point_line,
    intersect_line_line,
    distance_point_to_plane,
)
from math import radians, degrees
from ..utility.draw import (
    draw_line,
    draw_lines,
    draw_point,
    draw_points,
    draw_vector,
    draw_label,
)

# ===== UI constants / helpers =====
axis_color = {
    'X': (1.0, 0.3, 0.3),
    'Y': (0.3, 1.0, 0.4),
    'Z': (0.35, 0.6, 1.0),
}
WHITE = (1.0, 1.0, 1.0, 1.0)
YELLOW = (1.0, 0.9, 0.3, 1.0)

axis_mapping_dict = {'X': 0, 'Y': 1, 'Z': 2}
_SHIFT_KEYS = {'LEFT_SHIFT', 'RIGHT_SHIFT'}
_CTRL_KEYS = {'LEFT_CTRL', 'RIGHT_CTRL'}
_ALT_KEYS = {'LEFT_ALT', 'RIGHT_ALT'}

# drawing handled via shared utility/draw.py helpers imported above

def _avg(vecs):
    if not vecs:
        return Vector((0,0,0))
    s = Vector((0,0,0))
    for v in vecs:
        s += v
    return s / len(vecs)

def _face_center(face):
    try:
        return face.calc_center_median()
    except Exception:
        return _avg([v.co for v in face.verts])

def get_zoom_factor(context, depth_location, scale=10, ignore_obj_scale=False):
    center = Vector((context.region.width / 2, context.region.height / 2))
    offset = center + Vector((scale, 0))

    try:
        center_3d = region_2d_to_location_3d(context.region, context.region_data, center, depth_location)
        offset_3d = region_2d_to_location_3d(context.region, context.region_data, offset, depth_location)
    except:
        print("exception!")
        return 1

    if not ignore_obj_scale and context.active_object:
        mx = context.active_object.matrix_world.to_3x3()
        zoom_vector = mx.inverted_safe() @ Vector(((center_3d - offset_3d).length, 0, 0))
        return zoom_vector.length
    return (center_3d - offset_3d).length

def _create_rot_mx_from_vec(vec, mx=None):
    n = (mx.to_3x3() @ vec) if mx else vec
    b = n.orthogonal()
    t = n.cross(b)
    m = Matrix()
    m.col[0].xyz = t
    m.col[1].xyz = b
    m.col[2].xyz = n
    return m

def _get_selected_vert_sequences(verts, ensure_seq_len=True):
    # Ordered walk using selected edges only, matching MACHIN3tools behavior
    sequences = []
    verts = list(verts)
    if not verts:
        return sequences
    end_verts = [v for v in verts if len([e for e in v.link_edges if e.select]) == 1]
    v = end_verts[0] if end_verts else verts[0]
    seq = []
    while verts:
        seq.append(v)
        if v in verts:
            verts.remove(v)
        if v in end_verts:
            end_verts.remove(v)
        nextv = [e.other_vert(v) for e in v.link_edges if e.select and e.other_vert(v) not in seq]
        if nextv:
            v = nextv[0]
        else:
            cyclic = (len([e for e in v.link_edges if e.select]) == 2)
            if not ensure_seq_len or len(seq) > 1:
                sequences.append((seq, cyclic))
            if verts:
                v = end_verts[0] if end_verts else verts[0]
                seq = []
    return sequences


# ===== Operator =====
transform_mode_items = [('ROTATE', 'Rotate', ''), ('SCALE', 'Scale', '')]
transform_axis_items = [('VIEW', 'View', ''), ('X', 'X', ''), ('Y', 'Y', ''), ('Z', 'Z', '')]
constrain_mode_items = [
    ('DIRECT', 'Direct', ''),
    ('PROXIMITY', 'Proximity', ''),
    ('INTERSECTION', 'Intersection', ''),
    ('PLANE_INTERSECTION', 'Plane Intersection', ''),
    ('PROJECTED_PLANE_INTERSECTION', 'Projected Plane Intersection', ''),
    ('DIRECT_PLANE_INTERSECTION', 'Direct Plane Intersection', ''),
    ('MOUSEDIR_PLANE_INTERSECTION', 'MouseDir Plane Intersection', ''),
]


class TMC_OP_EdgeConstraints(bpy.types.Operator):
    bl_idname = "tmc.edge_constraints"
    bl_label = "Edge Constraints"
    bl_description = "Rotate/Scale constrained along selected edge direction"
    bl_options = {"REGISTER", "UNDO"}

    # optional: object mode injection by index
    objmode: BoolProperty(default=False)  # type: ignore
    edgeindex: IntProperty(default=-1)  # type: ignore
    faceindex: IntProperty(default=-1)  # type: ignore

    transform_mode: EnumProperty(name='Transform Mode', items=transform_mode_items, default='ROTATE')  # type: ignore
    transform_axis: EnumProperty(name='Transform Axis', items=transform_axis_items, default='VIEW')  # type: ignore
    constrain_mode: EnumProperty(name='Constrain Mode', items=constrain_mode_items, default='DIRECT_PLANE_INTERSECTION')  # type: ignore
    end_align: BoolProperty(name="Align Ends to Face Edge", default=True)  # type: ignore
    draw_end_align: BoolProperty(name="Draw Align Ends Option", default=False)  # type: ignore
    face_align: BoolProperty(name="Face Align", default=False)  # type: ignore
    draw_face_align: BoolProperty(name="Draw Face Align Option", default=False)  # type: ignore

    # runtime state
    def _reset_runtime(self):
        self.is_snapping = False
        self.is_zero_scaling = False
        self.is_axis_locking = False
        self.is_direction_locking = False
        self.is_mmb = False
        self.individual_origins = False
        self.angle = 0.0
        self.amount = 1.0
        self.rotation = Quaternion()
        self.scale = Vector()
        self.locked_intersection = None
        self.mousepos = Vector((0,0))
        self.slide_coords = []
        self.original_edge_coords = []
        self.draw_end_align = False
        self.draw_face_align = False

    @classmethod
    def poll(cls, context):
        if context.mode == 'EDIT_MESH':
            obj = context.active_object
            return obj and obj.type == 'MESH'
        if context.mode == 'OBJECT':
            return True
        return False

    # ---------- HUD / VIEW3D ----------
    def _draw_statusbar(self):
        if not _STATUSBAR:
            return
        def draw(self_ui, context):
            layout = self_ui.layout
            row = layout.row(align=True)
            text = 'Zero Scaling' if self.is_zero_scaling else ('Scaling' if self.transform_mode=='SCALE' else 'Rotation')
            row.label(text=f"Edge Constrained {text}")
            for ico, label in [('MOUSE_LMB','Confirm'),('MOUSE_RMB','Cancel')]:
                row.label(text="", icon=ico); row.label(text=label)
            row.separator(factor=10)
            if not self.is_axis_locking:
                for k in ['EVENT_X','EVENT_Y','EVENT_Z']:
                    row.label(text="", icon=k)
                row.label(text="", icon='MOUSE_MMB'); row.label(text="Axis")
            else:
                row.label(text="", icon='EVENT_C'); row.label(text="Clear Axis")
            if not self.is_zero_scaling:
                if self.transform_mode=='SCALE':
                    row.label(text="", icon='EVENT_R'); row.label(text="Rotate")
                else:
                    row.label(text="", icon='EVENT_S'); row.label(text="Scale")
                row.label(text="", icon='EVENT_SHIFT'); row.label(text="Zero Scale")
            if self.transform_mode=='ROTATE' and not self.is_zero_scaling:
                row.label(text="", icon='MOUSE_MMB'); row.label(text="Constrain Mode")
                row.label(text="", icon='EVENT_CTRL'); 
                row.separator(factor=2)
                row.label(text="Angle Snap")
            elif not self.is_direction_locking and not self.is_axis_locking and not self.is_zero_scaling:
                row.label(text="", icon='EVENT_ALT'); 
                row.separator(factor=2)
                row.label(text="Direction Lock")
            if self.draw_end_align:
                row.label(text="", icon='EVENT_E'); row.label(text=f"Align Ends: {'Face' if self.end_align else 'Cross'}")
            if self.draw_face_align:
                row.label(text="", icon='EVENT_F'); row.label(text=f"Face Alignment: {'True' if self.face_align else 'False'}")
            if len(self.data) > 1:
                row.label(text="", icon='EVENT_Q'); row.label(text=f"Individual Origins: {self.individual_origins}")
        self._bar_draw = _STATUSBAR.draw
        _STATUSBAR.draw = draw

    def _restore_statusbar(self):
        if _STATUSBAR and hasattr(self, '_bar_draw'):
            _STATUSBAR.draw = self._bar_draw

    def draw_HUD(self, args):
        context, event = args
        scale = context.preferences.system.ui_scale
        height = 10 * scale
        if self.is_zero_scaling:
            draw_label(context, title=f"ZERO SCALE", coords=self.mousepos + Vector((20, height)), center=False, color=WHITE)
        elif self.transform_mode == 'SCALE':
            col = YELLOW if self.is_snapping else WHITE
            draw_label(context, title=f"SCALE {self.amount:.2f}", coords=self.mousepos + Vector((20, height)), center=False, color=col)
            if self.is_direction_locking:
                draw_label(context, title=f"Direction Locked", coords=self.mousepos + Vector((20, height-20*scale)), center=False, color=(1,1,1,0.5))
        elif self.transform_mode == 'ROTATE':
            col = YELLOW if self.is_snapping else WHITE
            draw_label(context, title=f"ROTATE {self.angle:.1f}", coords=self.mousepos + Vector((20, height)), center=False, color=col)
            draw_label(context, title=f"{self.constrain_mode.title().replace('_',' ')}", coords=self.mousepos + Vector((20, height-20*scale)), center=False, color=(1,1,1,0.6))
        if self.is_axis_locking:
            axis = self.transform_axis[-1]
            draw_label(context, title=f"LOCAL {self.transform_axis}", coords=self.mousepos + Vector((20, height-40*scale)), center=False, color=axis_color[axis])
        if self.individual_origins:
            draw_label(context, title=f"Individual Origins", coords=self.mousepos + Vector((20, height-60*scale)), center=False, color=YELLOW)

    def draw_VIEW3D(self):
        # Full debug overlays
        draw_point(self.origin, color=(1,1,0,0.5), size=6)
        if self.individual_origins:
            inds = [seq['origin'] for seq in self.data.values()]
            draw_points(inds, color=(1,1,0,0.5), size=4)
        if self.is_axis_locking:
            axis = self.transform_axis[-1]
            v = self.mx.col[axis_mapping_dict[axis]].xyz.normalized()
            draw_line([self.origin - v*1000, self.origin, self.origin + v*1000], width=1.0, color=(*axis_color[axis], 0.5), xray=0.75)
        for ax in ['X','Y','Z']:
            v = self.mx.col[axis_mapping_dict[ax]].xyz.normalized()
            zf = self.zoom_factor
            draw_line([self.origin + v*0.3*zf, self.origin + v*zf], width=1.0, color=(*axis_color[ax], 0.75))
        if self.is_direction_locking or (self.transform_mode=='SCALE' and self.is_axis_locking):
            draw_vector(self.scale, origin=self.origin, color=(1,1,1,0.6))
        elif not (self.is_zero_scaling and self.is_axis_locking):
            draw_line([self.origin, self.intersection], width=1.0, color=(0,0,0,0.5))
        # Old/previous lines are intentionally hidden unless debugging

    # ---------- modal ----------
    def modal(self, context, event):
        context.area.tag_redraw()
        self.is_snapping = event.ctrl
        self.is_zero_scaling = event.shift
        if event.type in _SHIFT_KEYS:
            self.update_transform_plane(context, init=True)
        self.is_direction_locking = event.alt and self.transform_mode=='SCALE' and not self.is_zero_scaling and not self.is_axis_locking
        self._update_scale_direction_lock()

        events = ['MOUSEMOVE','ONE','TWO','WHEELUPMOUSE','WHEELDOWNMOUSE','E','R','S','X','Y','Z','C','MIDDLEMOUSE','F','Q','D']
        if event.type in events or event.type in _CTRL_KEYS or event.type in _ALT_KEYS or event.type in _SHIFT_KEYS:
            if event.type == 'MOUSEMOVE':
                self.mousepos = Vector((event.mouse_region_x, event.mouse_region_y))
                self.update_transform_plane(context, init=False)

            if (event.type in {'X','Y','Z','C'} and event.value == 'PRESS') or event.type == 'MIDDLEMOUSE':
                self._update_transform_axis(context, event)

            elif event.type == 'R' and event.value == 'PRESS':
                self.transform_mode = 'ROTATE'
                self.update_transform_plane(context, init=True)
            elif event.type == 'S' and event.value == 'PRESS':
                self.transform_mode = 'SCALE'
                self.update_transform_plane(context, init=True)
            elif event.type in {'ONE','WHEELUPMOUSE'} and event.value=='PRESS' and self.transform_mode=='ROTATE' and not self.is_zero_scaling:
                self.constrain_mode = self._step_enum(self.constrain_mode, constrain_mode_items, -1)
            elif event.type in {'TWO','WHEELDOWNMOUSE'} and event.value=='PRESS' and self.transform_mode=='ROTATE' and not self.is_zero_scaling:
                self.constrain_mode = self._step_enum(self.constrain_mode, constrain_mode_items, +1)
            elif event.type == 'E' and event.value=='PRESS':
                self.end_align = not self.end_align
            elif event.type == 'F' and event.value=='PRESS':
                self.face_align = not self.face_align
            elif len(self.data)>1 and event.type=='Q' and event.value=='PRESS':
                self.individual_origins = not self.individual_origins

            self._transform(context)

        if event.type in {'LEFTMOUSE','SPACE'} and event.value=='PRESS':
            self._finish()
            return {'FINISHED'}
        elif event.type in {'RIGHTMOUSE','ESC'}:
            self._reset_mesh()
            self._finish()
            return {'CANCELLED'}
        return {'RUNNING_MODAL'}

    def _finish(self):
        try: bpy.types.SpaceView3D.draw_handler_remove(self.HUD, 'WINDOW')
        except Exception: pass
        try: bpy.types.SpaceView3D.draw_handler_remove(self.VIEW3D, 'WINDOW')
        except Exception: pass
        self._restore_statusbar()
        if self.objmode:
            bpy.ops.object.mode_set(mode='OBJECT')

    def invoke(self, context, event):
        self.active = context.active_object
        self.mx = self.active.matrix_world
        # Optional object mode pick by index
        if self.objmode and (self.edgeindex!=-1 or self.faceindex!=-1):
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='DESELECT')
            bm = bmesh.from_edit_mesh(self.active.data)
            if self.faceindex!=-1:
                bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='FACE')
                bm.faces.ensure_lookup_table()
                if 0 <= self.faceindex < len(bm.faces):
                    bm.faces[self.faceindex].select_set(True)
                else:
                    self.report({'WARNING'}, 'faceindex out of range'); return {'CANCELLED'}
            elif self.edgeindex!=-1:
                bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='EDGE')
                bm.edges.ensure_lookup_table()
                if 0 <= self.edgeindex < len(bm.edges):
                    bm.edges[self.edgeindex].select_set(True)
                else:
                    self.report({'WARNING'}, 'edgeindex out of range'); return {'CANCELLED'}
            bmesh.update_edit_mesh(self.active.data)
        elif self.objmode:
            return {'CANCELLED'}

        # Build data
        self._reset_runtime()
        self.bm = bmesh.from_edit_mesh(self.active.data)
        self.bm.normal_update(); self.bm.verts.ensure_lookup_table()
        verts = [v for v in self.bm.verts if v.select]
        sequences = _get_selected_vert_sequences(verts, ensure_seq_len=True)
        if not sequences:
            self.report({'ERROR'}, 'Select an edge chain or loop')
            return {'CANCELLED'}
        self.data = self._build_selection_data(sequences)
        self.transform_axis = 'VIEW'

        pivot = context.scene.tool_settings.transform_pivot_point
        self.individual_origins = len(self.data)>1 and pivot not in {'CURSOR','ACTIVE_ELEMENT'}
        self.mousepos = Vector((event.mouse_region_x, event.mouse_region_y))
        self._update_view_plane(context, init=True)
        self.zoom_factor = get_zoom_factor(context, self.origin, scale=30)

        if _STATUSBAR:
            self._draw_statusbar()
        args = (context, event)
        self.VIEW3D = bpy.types.SpaceView3D.draw_handler_add(self.draw_VIEW3D, (), 'WINDOW', 'POST_VIEW')
        self.HUD = bpy.types.SpaceView3D.draw_handler_add(self.draw_HUD, (args,), 'WINDOW', 'POST_PIXEL')
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    # ---------- helpers ----------
    def _update_scale_direction_lock(self):
        if self.is_direction_locking and not self.locked_intersection:
            self.locked_intersection = self.intersection
        elif not self.is_direction_locking and self.locked_intersection:
            self.locked_intersection = None

    def _build_selection_data(self, sequences):
        data = {}
        self.draw_face_align = False
        self.original_edge_coords = []
        for sidx, (seq, cyclic) in enumerate(sequences):
            d = {'cyclic': cyclic, 'verts': seq, 'edges': [], 'origin': self.mx @ _avg([v.co for v in seq])}
            data[sidx] = d
            for vidx, v in enumerate(seq):
                prev_v = seq[(vidx-1) % len(seq)]
                next_v = seq[(vidx+1) % len(seq)]
                d[v] = {
                    'co': v.co.copy(), 'no': v.normal.copy(), 'dir': None, 'cross': None,
                    'prev_vert': prev_v if cyclic or vidx>0 else None,
                    'next_vert': next_v if cyclic or vidx < len(seq)-1 else None,
                    'prev_edge': None, 'next_edge': None,
                    'loop': None, 'left_face': None, 'right_face': None,
                    'left_edge': None, 'left_edge_dir': None, 'left_edge_coords': None,
                    'right_edge': None, 'right_edge_dir': None, 'right_edge_coords': None,
                    'left_face_edge': None, 'left_face_edge_dir': None, 'left_face_edge_coords': None,
                    'right_face_edge': None, 'right_face_edge_dir': None, 'right_face_edge_coords': None,
                    'left_face_dir': None, 'left_face_coords': None,
                    'right_face_dir': None, 'right_face_coords': None,
                }
            # edges, dirs, faces, side edges
            for v in seq:
                vdata = d[v]
                if vdata['next_vert']:
                    e = self.bm.edges.get([v, vdata['next_vert']])
                    vdata['next_edge'] = e; d['edges'].append(e)
                if vdata['prev_vert']:
                    e = self.bm.edges.get([v, vdata['prev_vert']])
                    vdata['prev_edge'] = e; d['edges'].append(e)
                # dir & cross
                if vdata['prev_vert'] and vdata['next_vert']:
                    vdir = ((vdata['next_vert'].co - vdata['co']).normalized() + (vdata['co'] - vdata['prev_vert'].co).normalized()).normalized()
                elif vdata['next_vert']:
                    vdir = (vdata['next_vert'].co - vdata['co']).normalized()
                else:
                    vdir = (vdata['co'] - vdata['prev_vert'].co).normalized()
                vdata['dir'] = vdir
                vdata['cross'] = vdata['no'].cross(vdir).normalized()
                # loop & faces (best-effort)
                e = vdata['next_edge'] or vdata['prev_edge']
                if e:
                    loops = [l for l in e.link_loops if l.vert == v]
                    if loops:
                        left_face = loops[0].face
                        right_face = loops[0].link_loop_radial_next.face
                        vdata['loop'] = loops[0]
                        vdata['left_face'] = left_face
                        if right_face != left_face:
                            vdata['right_face'] = right_face
                    elif e.link_loops:
                        vdata['right_face'] = e.link_loops[0].face
                # side edges: choose connected edges not in path leaning to cross direction
                connected = [e for e in v.link_edges if e not in d['edges']]
                for side in ('left','right'):
                    if connected:
                        options = []
                        for e in connected:
                            edir = (e.other_vert(v).co - vdata['co']).normalized()
                            dot = edir.dot(vdata['cross'])
                            if (side=='left' and dot>0.2) or (side=='right' and dot<-0.2):
                                options.append((e, abs(dot)))
                        if options:
                            e_best = max(options, key=lambda x: x[1])[0]
                            vdata[f'{side}_edge'] = e_best
                            vdata[f'{side}_edge_dir'] = (e_best.other_vert(v).co - v.co).normalized()
                            vdata[f'{side}_edge_coords'] = [v.co.copy() for v in e_best.verts]
                    # fallback via face normal to find projected dir on face
                    if vdata.get(f'{side}_face') and not vdata.get(f'{side}_edge'):
                        cross = vdata['cross'] if side=='left' else -vdata['cross']
                        i = intersect_line_plane(vdata['co'] + cross, vdata['co'] + cross - vdata[f'{side}_face'].normal, vdata['co'], vdata[f'{side}_face'].normal)
                        if i:
                            fdir = (i - vdata['co']).normalized()
                            vdata[f'{side}_face_dir'] = fdir
                            vdata[f'{side}_face_coords'] = [vdata['co'], vdata['co'] + fdir]
                            self.draw_face_align = True
            # flip to ensure both sides present
            for v in seq:
                vd = d[v]
                if vd['left_edge'] and not vd['right_edge']:
                    vd['right_edge'] = vd['left_edge']; vd['right_edge_dir'] = -vd['left_edge_dir']; vd['right_edge_coords'] = vd['left_edge_coords']
                elif vd['right_edge'] and not vd['left_edge']:
                    vd['left_edge'] = vd['right_edge']; vd['left_edge_dir'] = -vd['right_edge_dir']; vd['left_edge_coords'] = vd['right_edge_coords']
                if vd['left_face_edge'] and not vd['right_face_edge']:
                    vd['right_face_edge'] = vd['left_face_edge']; vd['right_face_edge_dir'] = -vd['left_face_edge_dir']; vd['right_face_edge_coords'] = vd['left_face_edge_coords']
                elif vd['right_face_edge'] and not vd['left_face_edge']:
                    vd['left_face_edge'] = vd['right_face_edge']; vd['left_face_edge_dir'] = -vd['right_face_edge_dir']; vd['left_face_edge_coords'] = vd['right_face_edge_coords']
                if vd['left_face_dir'] and not vd['right_face_dir']:
                    vd['right_face_dir'] = -vd['left_face_dir']
                elif vd['right_face_dir'] and not vd['left_face_dir']:
                    vd['left_face_dir'] = -vd['right_face_dir']
                if vd.get('next_vert'):
                    self.original_edge_coords.extend([vd['co'], d[vd['next_vert']]['co']])
        return data

    def _update_transform_axis(self, context, event):
        if event.type == 'X':
            self.transform_axis = 'X'; self.is_axis_locking = True
        elif event.type == 'Y':
            self.transform_axis = 'Y'; self.is_axis_locking = True
        elif event.type == 'Z':
            self.transform_axis = 'Z'; self.is_axis_locking = True
        elif event.type == 'C':
            self.transform_axis = 'VIEW'; self.is_axis_locking = False
        elif event.type == 'MIDDLEMOUSE':
            if event.value == 'PRESS':
                origin_2d = location_3d_to_region_2d(context.region, context.region_data, self.origin)
                if not origin_2d:
                    return
                mouse_vector = (origin_2d - self.mousepos).normalized()
                axes_2d = []
                for ax in ['X','Y','Z']:
                    v = self.mx.col[axis_mapping_dict[ax]].xyz.normalized()*self.zoom_factor
                    axis_2d = origin_2d - location_3d_to_region_2d(context.region, context.region_data, self.origin + v)
                    if round(axis_2d.length):
                        axes_2d.append((ax, mouse_vector.dot(axis_2d.normalized())))
                axis = max(axes_2d, key=lambda x: abs(x[1]))[0] if axes_2d else 'X'
                self.transform_axis = axis; self.is_axis_locking = True; self.is_mmb = True
            elif event.value == 'RELEASE':
                self.transform_axis = 'VIEW'; self.is_axis_locking = False; self.is_mmb = False
        self._update_view_plane(context, init=True)

    def _update_view_plane(self, context, init=False):
        def get_origin():
            pivot = context.scene.tool_settings.transform_pivot_point
            if pivot == 'CURSOR':
                return context.scene.cursor.location
            elif pivot == 'ACTIVE_ELEMENT':
                sel_mode = tuple(bpy.context.scene.tool_settings.mesh_select_mode)
                if self.bm.select_history and sel_mode == (True, False, False):
                    v = self.bm.select_history[-1]; return self.mx @ v.co
                elif self.bm.select_history and sel_mode == (False, True, False):
                    e = self.bm.select_history[-1]
                    # if active edge is sequence end, use end-point; else average
                    for seq in self.data.values():
                        if not seq['cyclic'] and e in seq['edges'] and len(seq['edges'])>1:
                            verts = seq['verts']
                            if e == seq['edges'][0]: return self.mx @ verts[0].co
                            if e == seq['edges'][-1]: return self.mx @ verts[-1].co
                    return self.mx @ _avg([v.co for v in e.verts])
                elif self.bm.faces.active and sel_mode == (False, False, True):
                    f = self.bm.faces.active; return self.mx @ _face_center(f)
            # default: average of all selection verts
            verts_all = [v for seq in self.data.values() for v in seq['verts']]
            return self.mx @ _avg([v.co for v in verts_all])

        def get_origin_dir():
            if self.transform_axis == 'VIEW':
                return - region_2d_to_vector_3d(context.region, context.region_data, (context.region.width/2, context.region.height/2))
            elif self.transform_mode == 'SCALE' or self.is_zero_scaling:
                axis = self.transform_axis
                axis_v = self.mx.col[axis_mapping_dict[axis]].xyz
                cross_v = axis_v.cross(view_dir)
                return axis_v.cross(cross_v)
            else:  # ROTATE
                axis = self.transform_axis[-1]
                return self.mx.col[axis_mapping_dict[axis]].xyz

        view_origin = region_2d_to_origin_3d(context.region, context.region_data, self.mousepos)
        view_dir = region_2d_to_vector_3d(context.region, context.region_data, self.mousepos)
        if init:
            self._reset_mesh()
            self.origin = get_origin()
            self.origin_dir = get_origin_dir()
        i = intersect_line_plane(view_origin, view_origin + view_dir, self.origin, self.origin_dir)
        if not i or round(self.origin_dir.dot(view_dir), 5) == 0:
            self.transform_axis = 'VIEW'; self.is_axis_locking = False
            self.origin_dir = - region_2d_to_vector_3d(context.region, context.region_data, (context.region.width/2, context.region.height/2))
            i = intersect_line_plane(view_origin, view_origin + view_dir, self.origin, self.origin_dir)
        if init:
            self.init_intersection = i
        self.intersection = i

    # Backward/compat alias used by modal handlers and key events
    def update_transform_plane(self, context, init=False):
        return self._update_view_plane(context, init=init)

    def _reset_mesh(self):
        for sel in self.data.values():
            for v in sel['verts']:
                v.co = sel[v]['co']
        self.bm.normal_update(); bmesh.update_edit_mesh(self.active.data)

    def _transform(self, context):
        def get_rotation():
            rot = (self.init_intersection - self.origin).rotation_difference(self.intersection - self.origin)
            if self.is_snapping:
                dangle = degrees(rot.angle); mod = dangle % 5
                angle = radians(dangle + (5-mod)) if mod >= 2.5 else radians(dangle - mod)
                rot = Quaternion(rot.axis, angle)
            self.angle = degrees(rot.angle); return rot
        def get_scale(per_sequence_origin=None):
            def lock_dir():
                i = intersect_point_line(self.intersection, self.origin, self.locked_intersection)
                if i:
                    cur = i[0] - self.origin
                    dot = cur.normalized().dot((self.locked_intersection - self.origin).normalized())
                    if dot < 0:
                        amt = 0; cur = cur*0.001
                    else:
                        amt = cur.length / init_scale.length
                    return amt, cur
                return amount, current_scale
            def lock_axis():
                axis = self.transform_axis
                axis_v = self.mx.col[axis_mapping_dict[axis]].xyz
                i = intersect_point_line(self.intersection, self.origin, self.origin + axis_v)
                if i:
                    cur = i[0] - self.origin
                    init_i = intersect_point_line(self.init_intersection, self.origin, self.origin + axis_v)
                    init_s = init_i[0] - self.origin
                    amt = cur.length / init_s.length
                    return amt, cur
                return amount, current_scale
            init_scale = self.init_intersection - self.origin
            current_scale = self.intersection - self.origin
            amount = current_scale.length / max(init_scale.length, 1e-9)
            if self.is_axis_locking:
                amount, current_scale = lock_axis()
            elif self.is_direction_locking:
                amount, current_scale = lock_dir()
            origin_local = (self.mx.inverted_safe() @ per_sequence_origin) if per_sequence_origin else (self.mx.inverted_safe() @ self.origin)
            rmx = _create_rot_mx_from_vec(current_scale.normalized(), mx=self.mx.inverted_safe())
            space = rmx.inverted_safe() @ Matrix.Translation(origin_local).inverted_safe()
            if self.is_zero_scaling:
                amount = 0
            vec = Vector((1,1,amount)); self.amount = amount
            return vec, space, current_scale

        self._reset_mesh()
        all_verts = [v for sel in self.data.values() for v in sel['verts']]
        if self.transform_mode=='SCALE' or self.is_zero_scaling:
            vec, space, self.scale = get_scale()
            if self.individual_origins:
                for sel in self.data.values():
                    origin = sel['origin']; verts = sel['verts']
                    _, space, _ = get_scale(per_sequence_origin=origin)
                    bmesh.ops.scale(self.bm, vec=vec, space=space, verts=verts)
            else:
                bmesh.ops.scale(self.bm, vec=vec, space=space, verts=all_verts)
        else:
            self.rotation = get_rotation()
            if self.individual_origins:
                for sel in self.data.values():
                    origin = sel['origin']; verts = sel['verts']
                    bmesh.ops.rotate(self.bm, cent=origin, matrix=self.rotation.to_matrix(), verts=verts, space=self.mx)
            else:
                bmesh.ops.rotate(self.bm, cent=self.origin, matrix=self.rotation.to_matrix(), verts=all_verts, space=self.mx)

        self.tdata = self._get_transformed_data()
        self._constrain_verts_to_edges()
        self.bm.normal_update(); bmesh.update_edit_mesh(self.active.data)

    def _constrain_verts_to_edges(self):
        for sidx, sel in self.tdata.items():
            for v in sel['verts']:
                tv = self.tdata[sidx][v]
                if not tv['edge_dir']:
                    continue
                if self.transform_mode=='SCALE' or self.is_zero_scaling:
                    if tv['scale_plane_intersection_co']:
                        v.co = tv['scale_plane_intersection_co']
                else:
                    cm = self.constrain_mode
                    if cm=='DIRECT' and tv['direct_co']:
                        v.co = tv['direct_co']
                    elif cm=='PROXIMITY' and tv['proximity_co']:
                        v.co = tv['proximity_co']
                    elif cm=='INTERSECTION' and tv['intersection_co']:
                        v.co = tv['intersection_co']
                    elif cm=='PLANE_INTERSECTION' and tv['plane_intersection_co']:
                        v.co = tv['plane_intersection_co']
                    elif cm=='PROJECTED_PLANE_INTERSECTION':
                        if tv['projected_plane_intersection_co']:
                            v.co = tv['projected_plane_intersection_co']
                        elif tv['direct_co']:
                            v.co = tv['direct_co']
                        elif tv['proximity_co']:
                            v.co = tv['proximity_co']
                    elif cm=='DIRECT_PLANE_INTERSECTION':
                        if tv['direct_plane_intersection_co']:
                            v.co = tv['direct_plane_intersection_co']
                        elif tv['projected_plane_intersection_co']:
                            v.co = tv['projected_plane_intersection_co']
                        elif tv['direct_co']:
                            v.co = tv['direct_co']
                        elif tv['proximity_co']:
                            v.co = tv['proximity_co']
                    elif cm=='MOUSEDIR_PLANE_INTERSECTION' and tv['mousedir_plane_intersection_co']:
                        v.co = tv['mousedir_plane_intersection_co']

    def _get_transformed_data(self):
        def check_flat():
            if len(verts) >= 3:
                plane_co = tdata[sidx][verts[1]]['init_co']
                plane_no = tdata[sidx][verts[1]]['init_no']
                for vv in [vv for vv in verts if vv != verts[1]]:
                    d = distance_point_to_plane(tdata[sidx][vv]['init_co'], plane_co, plane_no)
                    if abs(round(d, 6)) > 0:
                        return False
            return True
        def get_rotated_dir():
            if tv['prev_vert'] and tv['next_vert']:
                rv = ((tv['next_vert'].co - v.co).normalized() + (v.co - tv['prev_vert'].co).normalized()).normalized()
            elif tv['next_vert']:
                rv = (tv['next_vert'].co - v.co).normalized()
            else:
                rv = (v.co - tv['prev_vert'].co).normalized()
            tv['dir'] = rv; return rv
        def get_rotated_no_cross():
            rmx = self.mx.inverted_safe().to_quaternion() @ self.rotation @ self.mx.to_quaternion()
            tv['no'] = rmx @ init_no
            tv['cross'] = rvdir.cross(tv['no'])
        def pick_edge_dir():
            def align_face(edge_dir, slide_coords):
                if self.face_align and vdata['left_face_dir']:
                    dirs = [
                        ('edge_dir', moved.dot(edge_dir)),
                        ('left_face_dir', moved.dot(vdata['left_face_dir'])),
                        ('right_face_dir', moved.dot(vdata['right_face_dir'])),
                    ]
                    md = max(dirs, key=lambda x: abs(x[1]))
                    if md[0] != 'edge_dir':
                        edge_dir = vdata[md[0]]; slide_coords = vdata[md[0].replace('dir','coords')]
                return edge_dir, slide_coords
            edge_dir = None; slide_coords = []
            moved = (v.co - vdata['co']).normalized()
            side = 'left' if moved.dot(cross) > 0 else 'right'
            endvert = (v == verts[0] or v == verts[-1])
            if self.end_align and not cyclic and endvert and vdata.get(f'{side}_face_edge_dir'):
                edge_dir = vdata[f'{side}_face_edge_dir']; slide_coords = vdata[f'{side}_face_edge_coords']
            elif vdata.get(f'{side}_edge_dir'):
                edge_dir = vdata[f'{side}_edge_dir']; slide_coords = vdata[f'{side}_edge_coords']
                edge_dir, slide_coords = align_face(edge_dir, slide_coords)
            elif vdata.get(f'{side}_face_edge_dir'):
                edge_dir = vdata[f'{side}_face_edge_dir']; slide_coords = vdata[f'{side}_face_edge_coords']
                edge_dir, slide_coords = align_face(edge_dir, slide_coords)
            elif vdata.get(f'{side}_face_dir'):
                edge_dir = vdata[f'{side}_face_dir']; slide_coords = vdata[f'{side}_face_coords']
                edge_dir, slide_coords = align_face(edge_dir, slide_coords)
            tv['edge_dir'] = edge_dir
            edges_differ = bool(vdata.get(f'{side}_edge') and vdata.get(f'{side}_face_edge') and vdata[f'{side}_edge'] != vdata[f'{side}_face_edge'])
            if not cyclic and slide_coords and endvert and edges_differ:
                self.slide_coords.extend(slide_coords); self.draw_end_align = True
            return edge_dir
        def get_projected_co():
            i = intersect_line_plane(co, co + origin_dir_local, individual_origin_local if self.individual_origins else origin_local, origin_dir_local)
            if i:
                tv['projected_co'] = i; tv['projected_dir'] = i - co
        def get_direct_co():
            i = intersect_line_line(individual_origin_local if self.individual_origins else origin_local, co, init_co, init_co + edge_dir)
            if i:
                tv['direct_co'] = i[1]
        def get_proximity_co():
            i, _ = intersect_point_line(co, init_co, init_co + edge_dir); tv['proximity_co'] = i
        def get_intersection_co():
            i = intersect_line_line(co, co + rvdir, init_co, init_co + edge_dir)[1]
            if i: tv['intersection_co'] = i
        def get_plane_intersection_co():
            i = intersect_line_plane(init_co, init_co + edge_dir, co, tv['cross'])
            if i: tv['plane_intersection_co'] = i
        def get_projected_plane_intersection_co():
            projected_cross = rvdir.cross(tv['projected_dir']) if tv.get('projected_dir') else None
            if projected_cross:
                i = intersect_line_plane(init_co, init_co + edge_dir, co, projected_cross)
                if i: tv['projected_plane_intersection_co'] = i
        def get_direct_plane_intersection_co():
            if is_flat:
                tv['direct_plane_intersection_co'] = tv.get('projected_plane_intersection_co'); return
            direct_dir = (co - (individual_origin_local if self.individual_origins else origin_local)).normalized()
            direct_cross = rvdir.cross(direct_dir)
            i = intersect_line_plane(init_co, init_co + edge_dir, co, direct_cross)
            if i: tv['direct_plane_intersection_co'] = i
        def get_mousedir_plane_intersection_co():
            i = intersect_line_plane(init_co, init_co + edge_dir, co, init_mousedir_local)
            if i: tv['mousedir_plane_intersection_co'] = i
        def get_scale_plane_intersection_co():
            i = intersect_line_plane(init_co, init_co + edge_dir, co, current_scale_local)
            if i: tv['scale_plane_intersection_co'] = i

        tdata = {}; self.slide_coords = []
        origin_local = self.mx.inverted_safe() @ self.origin
        origin_dir_local = self.mx.inverted_safe().to_quaternion() @ self.origin_dir
        current_scale_local = self.mx.inverted_safe().to_quaternion() @ self.scale
        init_mousedir_local = self.mx.to_quaternion() @ (self.origin - self.init_intersection)

        for sidx, sel in self.data.items():
            verts = sel['verts']; cyclic = sel['cyclic']
            individual_origin_local = self.mx.inverted_safe() @ sel['origin']
            tdata[sidx] = {'verts': verts, 'cyclic': cyclic}
            for v in verts:
                vdata = sel[v]
                co = v.co.copy(); init_co = vdata['co']; init_no = vdata['no']
                tdata[sidx][v] = {
                    'co': co, 'init_co': init_co, 'dir': None,
                    'no': None, 'init_no': init_no, 'cross': None,
                    'prev_vert': vdata['prev_vert'], 'next_vert': vdata['next_vert'],
                    'edge_dir': None,
                    'projected_co': None, 'projected_dir': None,
                    'direct_co': None, 'proximity_co': None, 'intersection_co': None,
                    'plane_intersection_co': None, 'projected_plane_intersection_co': None,
                    'direct_plane_intersection_co': None,
                    'scale_plane_intersection_co': None, 'mousedir_plane_intersection_co': None,
                }
            is_flat = check_flat()
            for v in verts:
                vdata = self.data[sidx][v]; tv = tdata[sidx][v]
                co = tv['co']; init_co = tv['init_co']; init_no = vdata['no']; cross = vdata['cross']
                rvdir = get_rotated_dir(); get_rotated_no_cross(); edge_dir = pick_edge_dir()
                if self.transform_mode=='SCALE' or self.is_zero_scaling:
                    get_scale_plane_intersection_co()
                else:
                    get_projected_co(); get_direct_co(); get_proximity_co(); get_intersection_co(); get_plane_intersection_co();
                    get_projected_plane_intersection_co(); get_direct_plane_intersection_co(); get_mousedir_plane_intersection_co()
        return tdata

    @staticmethod
    def _step_enum(value, items, step):
        keys = [k for k,_,_ in items]
        if value not in keys:
            return keys[0]
        idx = (keys.index(value) + step) % len(keys)
        return keys[idx]
