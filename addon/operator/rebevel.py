# ***** BEGIN GPL LICENSE BLOCK *****
#
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.    See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ***** END GPL LICENCE BLOCK *****

from math import sin, cos, pi, pow
from mathutils import Vector
import mathutils
from math import *
import bpy
import bmesh
import re
import numpy as np
from copy import deepcopy


points_to_remove = {} #helper [spl_id]=[pts_to_remove_ids]
def spline_remove_points(obj, spl_id=None, points_ids=None, multi_spl=False):
    ''' remov points froom obj while mantaining selection state'''
    backup_mode = obj.mode
    # remove points from points_ids by selecting them and dissolve
    if multi_spl:
        splines_ids = points_to_remove.keys()
        pts_idss = points_to_remove.values()
    else:
        splines_ids = [spl_id]
        pts_idss = [points_ids]
    # for sp_id, pt_ids in zip(splines_ids, pts_idss):
    #     spline = obj.data.splines[spl_id]
    for spl in obj.data.splines:
        if spl.type == 'BEZIER':
            for p in spl.bezier_points:
                p.select_control_point = False
                p.select_left_handle = False
                p.select_right_handle = False
        else:
            for p in spl.points:
                p.select = False

    for sp_id, pts_ids in zip(splines_ids,pts_idss):
        spline = obj.data.splines[sp_id]
        if spline.type == 'BEZIER':
            for p_id in pts_ids:
                spline.bezier_points[p_id].select_control_point = True
        else:
            for p_id in pts_ids:
                spline.points[p_id].select = True

    if obj.mode != 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.curve.delete(type='VERT')  # context override dosent work no matter what
    if backup_mode != 'EDIT':  # we loose spline after going in and out of edit mode
        bpy.ops.object.mode_set(mode=backup_mode)

    #? spline.bezier_points.update()

#* Bezier bezer_point.co  = Vector((x,y,z))  ; select_control_point; select_left_handle; select_left_handle
#* polyline point.co  = Vector((x,y,z, 1)); select
#* Nurb point.co  = Vector((x,y,z, 1)); select
class BezierPoint(object):  # do we even need it...
    def __init__(self, co, handle_left_type='AUTO', handle_left=Vector((0, 0, 0)), handle_right_type='AUTO', handle_right=Vector((0, 0, 0)), select = False, lh_select = False, rh_select = False, radius=1, tilt=0, idx=-1):
        ''' ‘FREE’, ‘VECTOR’, ‘ALIGNED’, ‘AUTO’ '''
        self.co = co.xyz.copy()
        self.handle_left = handle_left.xyz.copy()
        self.handle_left_type = handle_left_type
        self.select_left_handle = lh_select
        self.handle_right = handle_right.xyz.copy()
        self.handle_right_type = handle_right_type
        self.select_right_handle = rh_select

        self.select = select
        self.tag = False #helper
        self.radius = radius
        self.tilt = tilt
        self.orig_idx = idx

    @classmethod
    def from_point(cls, b_pt, idx=-1):
        return cls(b_pt.co, b_pt.handle_left_type, b_pt.handle_left, b_pt.handle_right_type, b_pt.handle_right,
             select=b_pt.select_control_point, lh_select=b_pt.select_left_handle, rh_select=b_pt.select_right_handle, radius=b_pt.radius, tilt=b_pt.tilt, idx=idx)

    def copy_to_target(self, b_pt):
        b_pt.co = self.co.xyz.copy()

        b_pt.handle_left = self.handle_left
        b_pt.handle_right = self.handle_right

        b_pt.handle_left_type = self.handle_left_type
        b_pt.handle_right_type = self.handle_right_type

        b_pt.select_left_handle = self.select_left_handle
        b_pt.select_right_handle = self.select_right_handle
        b_pt.select_control_point = self.select
        b_pt.radius = self.radius
        b_pt.tilt = self.tilt


class Point(object):  # do we even need it...
    def __init__(self, co, select=False, radius=1, tilt=0, idx=-1):
        self.co = co.xyz.copy()
        self.select = select
        self.radius = radius
        self.tilt = tilt
        self.orig_idx = idx

    @classmethod
    def from_point(cls, pt, idx=-1):
        sel = pt.select if hasattr(pt, 'select') else pt.select_control_point
        return cls(pt.co, sel, radius=pt.radius, tilt=pt.tilt, idx=idx)

    def copy_to_target(self, nurb_point):
        nurb_point.co.xyz = self.co
        nurb_point.radius = self.radius
        nurb_point.select = self.select
        nurb_point.tilt = self.tilt
        # nurb_point.co.w = 1

    # def copy_to_btarget(self, nurb_point):
    #     nurb_point.co.xyz = self.co
    #     nurb_point.radius = self.radius
    #     nurb_point.select_control_point = self.select
    #     nurb_point.tilt = self.tilt
        # nurb_point.co.w = 1


class SplineCommon(object):
    def __init__(self, in_spl):
        self.skip_pts_remove = False
        self.orig_spl_props = {}
        if in_spl:
            self.backup_spl_props(in_spl)

    def backup_spl_props(self, spl):
        ''' copy blender spline settings like resu, res_v etc'''
        for k, v in spl.bl_rna.properties.items():
            if not v.is_readonly:  # value may be eg. <bpy_struct, EnumProperty("type")>; use: path_resolve(k) instead
                self.orig_spl_props[k] = spl.path_resolve(k)
                # setattr(new_spl, k, spl.path_resolve(k))

    def write_spl_props(self, spl):
        for k, v in self.orig_spl_props.items():
            setattr(spl, k, v)

    def write_common(self, obj, spl_id=None):
        write_spl_id = spl_id if spl_id != None else self.orig_spl_id
        if write_spl_id is None:
            print('cant write spline. No targest splined index given')
            return
        obj_spl_count = len(obj.data.splines)
        if write_spl_id == -1:
            write_spl_id = obj_spl_count-1
        if write_spl_id > obj_spl_count-1:  # create new spline
            spl_type = self.orig_spl_type if self.orig_spl_type else 'NURBS'
            polyline = obj.data.splines.new(spl_type)  # by default use Nurbs
            write_spl_id = obj_spl_count
            if spl_type == 'BEZIER':
                polyline.bezier_points.add(count=self.length-1)
                # for pt in polyline.bezier_points:
                #     pt.handle_left_type = 'AUTO'
                #     pt.handle_right_type = 'AUTO'
            else:
                polyline.points.add(count=self.length-1)
        else:
            self.set_blender_spl_p_count(obj, write_spl_id)
        polyline = obj.data.splines[write_spl_id]
        self.write_spl_props(polyline)
        return polyline

    def set_blender_spl_p_count(self, obj, spl_id):
        blender_spline = obj.data.splines[spl_id]
        pts = blender_spline.bezier_points if blender_spline.type == "BEZIER" else blender_spline.points
        pts_cnt = self.length
        new_points = pts_cnt - len(pts)
        if new_points > 0:  # orig spline has not enough
            pts.add(count=new_points)
        if new_points < 0:  # orig spline have too many points
            #* since its is very slow, add delayed opiton to remove exesive poitns once at finish
            pts_ids = [pts_cnt + i for i in range(abs(new_points))]
            if not self.skip_pts_remove:
                spline_remove_points(obj, spl_id, pts_ids)


class SplineSimple(SplineCommon):
    ''' Spline with Points() list '''
    def __init__(self, in_spl, orig_spl_id):
        super().__init__(in_spl)
        self.points = []
        self.orig_spl_id = orig_spl_id
        self.orig_spl_type = in_spl.type
        if in_spl.type == 'BEZIER':
            self.points = [BezierPoint.from_point(p, i) for i,p in enumerate(in_spl.bezier_points)]
        else:
            self.points = [Point.from_point(p, i) for i,p in enumerate(in_spl.points)]


    @property
    def length(self): return len(self.points)

    def append(self, point):
        self.points.append(deepcopy(point))

    def insert(self, index, points):
        if isinstance(points, list):
            self.points[index:index] = points[:]
        else:
            self.points.insert(index, points)

    def __delitem__(self, idx): del self.points[idx]

    def __getitem__(self, idx): return self.points[idx] # overload [] get

    def __setitem__(self, idx, point):
        ''' point can be blender bezier, or Point '''
        self.points[idx] = deepcopy(point)


    def write_to_blender_spl(self, obj, spl_id=None):
        polyline = self.write_common(obj, spl_id)
        if polyline.type == "BEZIER":
            for blender_pt, p in zip(polyline.bezier_points, self.points):
                p.copy_to_target(blender_pt)
                # blender_pt.handle_left_type = 'AUTO'
                # blender_pt.handle_right_type = 'AUTO'
        else:
            # polyline.order_u = 3
            # polyline.use_endpoint_u = True
            for blender_pt, p in zip(polyline.points, self.points):
                p.copy_to_target(blender_pt)
                blender_pt.co.w = 1 #pt tension


class Splines(object):
    '''Seens like almost no differerence in time for splFlat vs Simple (simple seems faster tiny bit...) '''
    def __init__(self, curveObj, onlySelection, with_clear = False):
        self.splines = []
        selectedSplines = [] #to clear if with clear....
        offset_idx = 999 if with_clear else 0
        if onlySelection:
            for spl_id, spl in enumerate(curveObj.data.splines):
                pts = spl.points if spl.type in {'NURBS', 'POLY'} else spl.bezier_points
                any_pt_selected = any([p.select for p in pts]) if spl.type in {'NURBS', 'POLY'} else any([p.select_control_point for p in pts])
                if any_pt_selected and len(pts)>1:
                    spl_id += offset_idx  # move far back, so we wont override exisitng non selected spl
                    self.splines.append(SplineSimple(spl, spl_id))
                    selectedSplines.append(spl)
        else:
            all_valid_splines = [spl for spl in curveObj.data.splines if len(spl.points) > 1 or len(spl.bezier_points) > 1]
            selectedSplines.extend(all_valid_splines)
            self.splines = [SplineSimple(spl, spl_id) for spl_id, spl in enumerate(all_valid_splines)]
        if curveObj.data.splines.active:
            id_str = curveObj.data.splines.active.path_from_id()
            numbs_str = re.findall(r'\d+', id_str)
            self.active_spl_idx = int(numbs_str[0])
        else:
            self.active_spl_idx = -1
        for spl in self.splines:
            spl.skip_pts_remove = True
        if with_clear: #remove splines after reading data from them?
            if onlySelection:
                for spline in selectedSplines:
                    curveObj.data.splines.remove(spline)
            else:
                curveObj.data.splines.clear()

    @property
    def length(self): return len(self.splines)

    def write_splines_to_blender(self, obj):
        for spl in self.splines: #*check if we write less pts, to obj.spline. If so remove pts from curve
            write_spl_id = spl.orig_spl_id
            if write_spl_id is None:
                continue
            obj_spl_count = len(obj.data.splines)
            if write_spl_id == -1:
                write_spl_id = obj_spl_count-1
            if write_spl_id < obj_spl_count:
                pts_cnt = spl.length
                blender_spl = obj.data.splines[write_spl_id]
                pts = blender_spl.bezier_points if blender_spl.type == 'BEZIER' else blender_spl.points
                new_points = pts_cnt - len(pts)
                if new_points < 0:  # orig spline have too many points
                    pts_ids = [pts_cnt + i for i in range(abs(new_points))]
                    points_to_remove[write_spl_id] = pts_ids
        if points_to_remove: #* pts removal is slow, so do it only once for all removed pts
            spline_remove_points(obj, multi_spl=True)
            points_to_remove.clear()
        [sp.write_to_blender_spl(obj) for sp in self.splines]
        if self.active_spl_idx > -1:
            obj.data.splines.active = obj.data.splines[self.active_spl_idx]

class TMC_OP_BevelCurve(bpy.types.Operator):
    bl_idname = "tmc.curve_bevel"
    bl_label = "Bevel Curve"
    bl_description = "Bevel selected curve vertices (ctrl+B)"
    bl_options = {'REGISTER', 'UNDO'}

    bevel_size: bpy.props.FloatProperty(name="ReBevel size", description="ReBevel size", default=0.0, min=0.0)  # type: ignore
    segments: bpy.props.IntProperty(name="Segments", description="Segments count", default=0, min=0)  # type: ignore
    tension: bpy.props.FloatProperty(name="Shape", description="re-bevel shape. Default 0.5", default=0.5, min=-1.0, max=1.0)  # type: ignore
    resize_mode: bpy.props.EnumProperty(name='Resize mode', description='Bevel resizing mode',  # type: ignore
                                        items=[
                                            ('UNIFORM', 'Uniform', 'Uniform radius change'),
                                            ('PROP', 'Proportional', 'Radius change proportional to adjacent edges length')
                                        ], default='UNIFORM')


    def curve_bevel(self, context):
        sel_splines = deepcopy(self.orig_splines)
        if self.bevel_size > 0:
            normalized_bevel_pts = super_elipse2(self.tension, self.segments+2) #in (0,1) range
            for spl in sel_splines.splines:
                pts_cnt = spl.length
                idx_offset = 0
                orig_pts_co = [p.co.copy() for p in spl.points]
                for p_idx in range(pts_cnt):
                    new_p_idx = p_idx+idx_offset
                    pt = spl.points[new_p_idx] # skip ahead of newly added bevel pts
                    if pt.select:
                        bevel_target = pt.co.copy()
                        prev_co = orig_pts_co[(p_idx-1)%pts_cnt]
                        next_co = orig_pts_co[(p_idx+1)%pts_cnt]
                        dir_pt_prev = prev_co - pt.co
                        dir_pt_next = next_co - pt.co
                        dir_pt_prev_cp = dir_pt_prev.copy()
                        dir_pt_next_cp = dir_pt_next.copy()

                        #* remember we have dupli of pt now in bevel_pts
                        #TODO: make it  auto scale depending on curve bbxo?
                        if self.resize_mode == 'UNIFORM':
                            # self.bevel_size = min(self.bevel_size, 1) #clamp
                            off_to_prev = dir_pt_prev.normalized() * self.bevel_size * self.diagonal
                            off_to_next = dir_pt_next.normalized() * self.bevel_size * self.diagonal
                        else:
                            off_to_prev = self.bevel_size*dir_pt_prev
                            off_to_next = self.bevel_size*dir_pt_next
                        off_to_prev = off_to_prev if off_to_prev.length < dir_pt_prev_cp.length else dir_pt_prev_cp #basically clamp
                        off_to_next = off_to_next if off_to_next.length < dir_pt_next_cp.length else dir_pt_next_cp  #basically clamp

                        offset_v1 = bevel_target + off_to_prev
                        offset_v2 = bevel_target + off_to_next
                        bevel_target_coords = barycentric_transform(normalized_bevel_pts, bevel_target, offset_v1, offset_v2, self.tension)

                        bevel_pts = [deepcopy(pt) for i in range(self.segments+1)] + [pt, ]
                        if spl.orig_spl_type == 'BEZIER':
                            for p in bevel_pts:
                                p.handle_left_type = 'AUTO'
                                p.handle_right_type = 'AUTO'
                        for bevel_pt, target_co in zip(bevel_pts, bevel_target_coords):
                            bevel_pt.co = target_co
                        spl.insert(new_p_idx, bevel_pts[:-1])  # skip last pt (which is same as pt)
                        idx_offset += self.segments+1

        sel_splines.write_splines_to_blender(context.active_object)
        return

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'CURVE' and obj.mode == 'EDIT'

    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'bevel_size')
        layout.prop(self, 'resize_mode')
        layout.prop(self, 'segments')
        if self.segments > 0:
            layout.prop(self, 'tension')

    def invoke(self, context, event):
        bpy.ops.ed.undo_push()
        self.orig_splines = Splines(context.active_object, True)
        if not self.orig_splines.splines:
            self.report({'ERROR'}, 'No points selected on any spline. Cancelling!')
            return {'CANCELLED'}
        self.diagonal = context.active_object.dimensions.length / 4
        self.segments = 0
        self.bevel_size = 0
        self.prev_settings = (self.bevel_size, self.segments, self.tension)
        self.run_exec = False
        self.start_x = event.mouse_region_x
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        self.run_exec = True
        self.curve_bevel(context)
        return {'FINISHED'}

    def check(self, context):
        return True

    def do_update(self, context):
        if self.prev_settings == (self.bevel_size, self.segments, self.tension):
            return {"RUNNING_MODAL"}
        else:
            self.curve_bevel(context)
            self.prev_settings = (self.bevel_size, self.segments, self.tension)

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':
            diff = (event.mouse_region_x - self.start_x)/200
            if event.ctrl:
                margin = 35 / 200
                if abs(diff) < margin:  # snap to (1 + 0)
                    diff = 0.0
                if abs(diff + 0.5) < margin:  # snap for bevel size (1 - 0.5)
                    diff = - 0.5
                if abs(diff - 1.0) < margin:  # snap for bevel (1 + 1)
                    diff = 1.0
                if abs(diff - 3.0) < margin:  # snap for bevel (1 + 3)
                    diff = 3.0

            self.bevel_size = max(0.0, diff)
            resize_mode = 'Proportional' if self.resize_mode == 'PROP' else 'Uniform'
            context.workspace.status_text_set(
                f'Beves size: {self.bevel_size:.2f}      [MMB] Segments: {self.segments}     [Ctrl] Snap: {event.ctrl}     [Shift] Shape: {self.tension:.2f}      [M] Resize Mode: {resize_mode}')
            self.do_update(context)

        elif event.type == 'M' and event.value == 'PRESS':
            self.resize_mode = 'UNIFORM' if self.resize_mode == 'PROP' else 'PROP'

        elif event.type == 'WHEELUPMOUSE' or (event.type == 'TWO' and event.value == 'PRESS'):
            if event.shift:
                self.tension += 0.1
            else:
                self.segments += 1
            self.do_update(context)
        elif event.type == 'WHEELDOWNMOUSE' or (event.type == 'ONE' and event.value == 'PRESS'):
            if event.shift:
                self.tension -= 0.1
            else:
                self.segments = max(self.segments - 1, 0)
            self.do_update(context)

        elif event.type == "LEFTMOUSE":
            context.workspace.status_text_set(None)
            return {"FINISHED"}

        elif event.type in {"RIGHTMOUSE", "ESC"}:
            context.workspace.status_text_set(None)
            bpy.ops.ed.undo()
            return {"CANCELLED"}

        return {"RUNNING_MODAL"}


class TMC_OP_reBevelCurve(bpy.types.Operator):
    bl_idname = "tmc.curve_re_bevel"
    bl_label = "reBevel Curve"
    bl_description = "reBevel selected curve vertices (alt+B)"
    bl_options = {'REGISTER', 'UNDO'}

    rebevel_size: bpy.props.FloatProperty(name="ReBevel size", description="ReBevel size", default=0.0, min=0.0)  # type: ignore
    segments: bpy.props.IntProperty(name="Segments", description="Segments count", default=0, min=0)  # type: ignore
    tension: bpy.props.FloatProperty(name="Shape", description="re-bevel shape. Default 0.5", default=0.5, min=-1.0, max=1.0)  # type: ignore
    resize_mode: bpy.props.EnumProperty(name='Resize mode', description='Bevel resizing mode',  # type: ignore
                                        items=[
                                            ('UNIFORM', 'Uniform', 'Uniform radius change'),
                                            ('PROP', 'Proportional', 'Radius change proportional to adjacent edges length')
                                        ], default='UNIFORM')

    @staticmethod
    def get_sel_ver_chain(spl, ignored_ids):
        ''' for now only get one chain of sel verts
        returns list of [(pt, idx), ...]
        '''
        pts_cnt = spl.length
        prev_sel = spl.points[-1].select
        chain = []
        pre_loop_appended = False
        for idx, pt in enumerate(spl.points):
            if pt.select and pt.orig_idx not in ignored_ids:
                chain.append(pt)
                pre_loop_appended = True
            else:
                if pre_loop_appended:
                    break
        if len(chain) == pts_cnt or len(chain)==1: #cant work on whole spl selected... wtf would happen.
            return []
        if chain and chain[0].orig_idx == 0: #go back to see if we have sel pts in negative dir...
            for idx, pt in reversed(list(enumerate(spl.points))):
                if pt.select and pt.orig_idx not in ignored_ids:
                    chain.insert(0, pt)
                else:
                    break
        return chain


    def curve_rebevel(self, context):
        sel_splines = deepcopy(self.orig_splines)
        target_bevel_vcount = self.segments+2 #including boundary verts
        normalized_bevel_pts = super_elipse2(self.tension, target_bevel_vcount)  # in (0,1) range
        for spl in sel_splines.splines:
            ignored_chain_ids = [] #ignore those pt.ids when searching for n-th time for sel_vert_chain
            while True: #while we find new chains of sel verts strip
                pts_cnt = spl.length
                orig_pts_co = [p.co.copy() for p in spl.points]
                sel_strip = self.get_sel_ver_chain(spl, ignored_chain_ids)  # list of [(pt, idx), ...]
                if not sel_strip:
                    break
                chain_len = len(sel_strip)

                first_pt_idx = sel_strip[0].orig_idx  # (pt, idx)
                last_pt_idx = sel_strip[-1].orig_idx  # (pt, idx)

                v_1_co = sel_strip[0].co.copy()
                v_n_co = sel_strip[-1].co.copy()

                prev_co = orig_pts_co[(first_pt_idx-1) % pts_cnt]
                next_co = orig_pts_co[(last_pt_idx+1) % pts_cnt]

                intersect = mathutils.geometry.intersect_line_line(prev_co, v_1_co, next_co, v_n_co) # ret pair of p1,p2  - closest p to line_x
                if intersect:
                    (bevel_target_pt, bevel_target_pt2) = intersect
                    bevel_target_pt = (bevel_target_pt+bevel_target_pt2)/2
                else: #? if parallel lines
                    normal_dir = (v_1_co-prev_co).normalized()
                    v1n_dist = (v_1_co - v_n_co).length
                    bevel_target_pt = (v_1_co+v_n_co)/2 + normal_dir*v1n_dist/2

                #* delete selected verts first from spl (added later from sel_strip)
                for pt in reversed(sel_strip):
                    del spl.points[pt.orig_idx]

                if self.rebevel_size < 0.001: #* collapse into one
                    sel_strip[0].co = bevel_target_pt
                    spl.insert(first_pt_idx, sel_strip[0])  # we removed orign sel_strip few lines above
                    ignored_chain_ids.append(first_pt_idx)
                else: #* or reBevel
                    #* first shorten or lengthen the sel_strip.., depending on target segments+2
                    spare_vcount = chain_len - target_bevel_vcount
                    if spare_vcount > 0:
                        for i in range(spare_vcount):
                            sel_strip.pop()
                    elif spare_vcount < 0:
                        for i in range(-1*spare_vcount):
                            sel_strip.append(deepcopy(sel_strip[-1]))

                    offset_v1 = bevel_target_pt.lerp(v_1_co, self.rebevel_size)
                    offset_v2 = bevel_target_pt.lerp(v_n_co, self.rebevel_size)
                    bevel_target_coords = barycentric_transform(normalized_bevel_pts, bevel_target_pt, offset_v1, offset_v2, self.tension)

                    for bevel_pt, target_co in zip(sel_strip, bevel_target_coords):
                        bevel_pt.co = target_co
                    spl.insert(first_pt_idx, sel_strip)  # we removed orign sel_strip few lines above
                    ignored_chain_ids.extend([first_pt_idx+i for i in range(target_bevel_vcount)])

                for i,p in enumerate(spl.points):
                    p.orig_idx = i


        sel_splines.write_splines_to_blender(context.active_object)


    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.type == 'CURVE' and obj.mode == 'EDIT'

    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'rebevel_size')
        layout.prop(self, 'resize_mode')
        layout.prop(self, 'segments')
        if self.segments > 0:
            layout.prop(self, 'tension')

    def invoke(self, context, event):
        bpy.ops.ed.undo_push()
        self.orig_splines = Splines(context.active_object, True)
        if not self.orig_splines.splines:
            self.report({'ERROR'}, 'No points selected on any spline. Cancelling!')
            return {'CANCELLED'}

        #sample for segments
        sel_strip = self.get_sel_ver_chain(self.orig_splines.splines[0],[])  # list of [(pt, idx), ...]

        self.segments = len(sel_strip) - 2
        # self.init_segments = self.segments
        self.rebevel_size = 0
        self.prev_settings = (self.rebevel_size, self.segments, self.tension)
        self.run_exec = False
        self.start_x = event.mouse_region_x
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        self.run_exec = True
        self.curve_rebevel(context)
        return {'FINISHED'}

    def check(self, context):
        return True

    def do_update(self, context):
        if self.prev_settings == (self.rebevel_size, self.segments, self.tension):
            return {"RUNNING_MODAL"}
        else:
            self.curve_rebevel(context)
            self.prev_settings = (self.rebevel_size, self.segments, self.tension)

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':
            diff = (event.mouse_region_x - self.start_x)/200
            if event.ctrl:
                margin = 35 / 200
                if abs(diff) < margin:  # snap to (1 + 0)
                    diff = 0.0
                if abs(diff + 0.5) < margin:  # snap for bevel size (1 - 0.5)
                    diff = - 0.5
                if abs(diff - 1.0) < margin:  # snap for bevel (1 + 1)
                    diff = 1.0
                if abs(diff - 3.0) < margin:  # snap for bevel (1 + 3)
                    diff = 3.0

            self.rebevel_size = max(0.0, diff+1)
            resize_mode = 'Proportional' if self.resize_mode == 'PROP' else 'Uniform'
            context.workspace.status_text_set(
                f'Beves size: {self.rebevel_size:.2f}      [MMB] Segments: {self.segments}     [Ctrl] Snap: {event.ctrl}     [Shift] Shape: {self.tension:.2f}      [M] Resize Mode: {resize_mode}')
            self.do_update(context)

        elif event.type == 'M' and event.value == 'PRESS':
            self.resize_mode = 'UNIFORM' if self.resize_mode == 'PROP' else 'PROP'

        elif event.type == 'WHEELUPMOUSE' or (event.type == 'TWO' and event.value == 'PRESS'):
            if event.shift:
                self.tension += 0.1
            else:
                self.segments += 1
            self.do_update(context)
        elif event.type == 'WHEELDOWNMOUSE' or (event.type == 'ONE' and event.value == 'PRESS'):
            if event.shift:
                self.tension -= 0.1
            else:
                self.segments = max(self.segments - 1, 0)
            self.do_update(context)

        elif event.type == "LEFTMOUSE":
            context.workspace.status_text_set(None)
            return {"FINISHED"}

        elif event.type in {"RIGHTMOUSE", "ESC"}:
            context.workspace.status_text_set(None)
            return {"CANCELLED"}

        return {"RUNNING_MODAL"}


class TMC_OT_RebevelSmart(bpy.types.Operator):
    bl_idname = "tmc.rebevel_smart"
    bl_label = "ReBevel (Smart)"
    bl_description = "ReBevel for mesh edges or curve points based on current context"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = getattr(context, 'active_object', None)
        if not obj:
            return False
        # Curve edit mode supported by curve re-bevel
        if obj.type == 'CURVE' and obj.mode == 'EDIT':
            return True
        # Mesh rebevel only in Edit Mesh with edge select mode
        if obj.type == 'MESH' and context.mode == 'EDIT_MESH':
            try:
                sel_mode = context.scene.tool_settings.mesh_select_mode[:]
            except Exception:
                try:
                    sel_mode = context.tool_settings.mesh_select_mode[:]
                except Exception:
                    sel_mode = (False, True, False)
            return sel_mode == (False, True, False)
        return False

    def execute(self, context):
        obj = context.active_object
        if obj and obj.type == 'CURVE' and obj.mode == 'EDIT':
            try:
                bpy.ops.tmc.curve_re_bevel('INVOKE_DEFAULT')
                return {'FINISHED'}
            except Exception as e:
                self.report({'ERROR'}, f'Curve ReBevel failed: {e}')
                return {'CANCELLED'}
        if obj and obj.type == 'MESH' and context.mode == 'EDIT_MESH':
            try:
                bpy.ops.tmc.re_bevel('INVOKE_DEFAULT')
                return {'FINISHED'}
            except Exception as e:
                self.report({'ERROR'}, f'Mesh ReBevel failed: {e}')
                return {'CANCELLED'}
        self.report({'WARNING'}, 'ReBevel is only available in Edit Mesh (edge select) or Edit Curve modes')
        return {'CANCELLED'}


#!################################## END OF SPLINES  ###########################################################
#!##############################################################################################################


def remap(old_value, old_min, old_max, new_min, new_max):
    old_range = (old_max - old_min)
    new_range = (new_max - new_min)
    return (((old_value - old_min) * new_range) / old_range) + new_min

def super_elipse(t, n, v1, v2, bevel_target):
    t_rad = pi/2 * t # map (0,1) to (0, pi/2)
    eli_point = Vector((pow(cos(t_rad), 2/n), pow(sin(t_rad), 2/n), 0))
    return mathutils.geometry.barycentric_transform(eli_point, Vector((1, 0, 0)), Vector((1, 1, 0)), Vector((0, 1, 0)), v1, bevel_target, v2)

def reflect_point(v1, v2, pt):
    v1_v2 = (v2 - v1).normalized()
    v1_pt = (pt - v1)
    parallel_comp = v1_v2.dot(v1_pt) * v1_v2
    perp_comp = v1_pt - parallel_comp
    return parallel_comp - perp_comp + v1

a10 = Vector((1, 0, 0))
a11 = Vector((1, 1, 0))
a01 = Vector((0, 1, 0))


def barycentric_transform(normalized_bevel_pts, bevel_target, v1, v2, tension):
    bevel_t = reflect_point(v1, v2, bevel_target) if tension < 0 else bevel_target
    return [mathutils.geometry.barycentric_transform(elips_point, a10, a11, a01, v1, bevel_t, v2) for elips_point in normalized_bevel_pts]

def super_elipse2(tension, segments):
    # n_pow = tension*10 + 1  #now tension of 0.113 gives same result as default blender bevel....
    normalized_bevel_pts = []  # bevel for a10, a11, a01 pts
    if tension < 0:
        tension *= -1

    if tension == 1.0:
        for i in range(segments):
            t = i/(segments-1)  # t in (0,1)
            if t < 0.5:  # sample (v1, bevel_target) line
                corner_sample = a10.lerp(a11, t*2)  # remap t (0, 0.5) to (0,1)
            else:  # sample (bevel_target, v2) line
                corner_sample = a11.lerp(a01, (t-0.5)*2)  # remap t(0.5, 1) to (0,1)
            normalized_bevel_pts.append(corner_sample)

    elif tension < 0.5: #use lerp of circle to linear v1, v2 blend
        flat_bevel_pts = [a10.lerp(a01, i/(segments-1)) for i in range(segments)]
        circle_points = [Vector((cos(pi/2 * i/(segments-1)), sin(pi/2 * i/(segments-1)), 0)) for i in range(segments)]
        normalized_bevel_pts = [flat_p.lerp(circle_p, tension*2) for circle_p, flat_p in zip(circle_points, flat_bevel_pts)]

    else: #* Use super elipse bevel pts
        max_range = pi/4
        n_pow = 2*tension + 1 + pow(2, (tension - 0.5) * 10)-1  # (0.5, 1) to (2, inf)
        first_pass_elipse_pts = []

        #calc superellipse for only 0 =- 45 deg - later mirror around y=x to get (45,90) range
        for i in range(segments):
            t = i/(segments-1)
            t_remapped = max_range * pow(t, n_pow/2)  # map (0,1) to (0, pi/2)
            first_pass_elipse_pts.append(Vector((pow(cos(t_remapped), 2/n_pow), pow(sin(t_remapped), 2/n_pow), 0)))
        #Mirrorin to full from (0,45) to (0,90) deg range - excluding last pt - alrady on y=x line
        for i in reversed(range(segments-1)): # -1 to exclude last pt
            first_pass_elipse_pts.append(first_pass_elipse_pts[i].yxz)
        #first_pass_elipse_pts has now 2*segments-1 pts.
        #Resample to target pt count using np.interp(2.5, xp, fp)
        in_xp = np.linspace(0, 1, segments) #defines output pts cnt
        xp = np.linspace(0, 1, 2*segments-1)
        fp = np.array(first_pass_elipse_pts, 'f')
        # out_fp = np.interp(in_xp, xp, fp)

        elips_resampled_np = np.transpose([np.interp(in_xp, xp, fp[:, i]) for i in range(fp.shape[1])])
        normalized_bevel_pts = [Vector(x.tolist()) for x in elips_resampled_np]

    return normalized_bevel_pts

def other_edges(vert, edge):
    for ed in vert.link_edges:
        if ed != edge:
            yield ed


def edges_angle(edgeA, edgeB, adj_vert):
    vec_a = edgeA.other_vert(adj_vert).co - adj_vert.co   # from A -> Vert
    vec_b = edgeB.other_vert(adj_vert).co - adj_vert.co  # from vert  -> B
    return vec_a.angle(vec_b)


def get_counter_facing_edge(e, vert):
    ''' return best edge with atleast 110 deg angle to reference e '''
    min_angle = 2  # at least 110 deg, between 2 edges
    max_angle_edge = None
    for other_edge in other_edges(vert, e):
        ab_angle = edges_angle(e, other_edge, vert)
        if ab_angle > min_angle:
            max_angle_edge = other_edge
            min_angle = ab_angle
    if min_angle > 2:  # 2rad = 110 deg
        return max_angle_edge
    return None


def adj_ring_vert(v, old_vert):
    adj_verts = [l_e.other_vert(v) for l_e in v.link_edges if not l_e.select and l_e.other_vert(v).select and l_e.other_vert(v) != old_vert]
    return adj_verts[0] if adj_verts else None



def adj_ring_vert_better(v, v_edge):
    ''' Get adjacent verts in ring (sel) - using vert.loops - less error prone '''
    # sorted_e_strips[0][0].link_loops[0].link_loop_prev.vert
    adj_v = []
    for l in v_edge.link_loops:
        if l.vert == v:
            candidate = l.link_loop_prev.vert if len(l.link_loop_prev.face.verts)==4 else None
        else:
            candidate = l.link_loop_next.link_loop_next.vert if len(l.link_loop_next.link_loop_next.face.verts)==4 else None
        if candidate and candidate.select:
            adj_v.append(candidate)
    return adj_v

def adj_ring_vert_better_ignoring(v, v_edge, ignored_v):
    ''' Get adjacent verts in ring (sel)'''
    # sorted_e_strips[0][0].link_loops[0].link_loop_prev.vert
    adj_v = adj_ring_vert_better(v, v_edge)
    if ignored_v in adj_v:
        adj_v.remove(ignored_v)
    return adj_v[0] if adj_v else None

class TMC_OP_Unbevel(bpy.types.Operator):
    bl_idname = "tmc.re_bevel"
    bl_label = "ReBevel"
    bl_description = "ReBevel by selecting bevel edges"
    bl_options = {'REGISTER', 'UNDO'}

    rebevel_size: bpy.props.FloatProperty(name="ReBevel size", description="ReBevel size", default=1.0, min=0.0)  # type: ignore
    segments: bpy.props.IntProperty(name="Segments", description="Segments count", default=2, min=0)  # type: ignore
    tension: bpy.props.FloatProperty(name="Shape", description="re-bevel shape. Default 0.5", default=0.5, min=-1.0, max=1.0)  # type: ignore
    use_profile: bpy.props.BoolProperty(name="Use Profile", description="Use Profile", default=False)  # type: ignore
    resize_mode: bpy.props.EnumProperty(name='Resize mode', description='Bevel resizing mode',  # type: ignore
        items=[
            ('UNIFORM', 'Uniform', 'Uniform radius change'),
            ('PROP', 'Proportional', 'Radius change proportional to bevel size (faster change on bigger bevels)')
        ], default='UNIFORM')


    def my_get_sorted_loops(self, bm):
        # adjacent rings may have flipped ver order from top to bottom. Need sorting
        remaining_edges_ids = [e.index for e in bm.edges if e.select]
        edge_strips = []
        vert_strips = []

        while remaining_edges_ids:
            current_edge_loop = []
            current_vert_loop = []
            current_edge = bm.edges[remaining_edges_ids.pop()]
            current_edge_loop.append(current_edge)

            def follow_edge_loop(curr_edge, old_vert, add_right):
                while True:  # go vert0 way, till no lined edges (line stops)
                    next_vert = curr_edge.other_vert(old_vert)
                    next_edges = [link_e for link_e in next_vert.link_edges if link_e.select and link_e != curr_edge]
                    if add_right:
                        current_vert_loop.append(next_vert)
                    else:
                        current_vert_loop.insert(0, next_vert)
                    if next_edges and next_edges[0] not in current_edge_loop:  # just ignore if there are more linked edges selected. Maybe give error - bad selection
                        if add_right:
                            current_edge_loop.append(next_edges[0])
                            # current_vert_loop.append(next_vert)
                        else:
                            current_edge_loop.insert(0, next_edges[0])
                            # current_vert_loop.insert(0,next_vert)
                        remaining_edges_ids.remove(next_edges[0].index)
                        curr_edge = next_edges[0]
                        old_vert = next_vert  # right vert becomes left
                    else:
                        break
            follow_edge_loop(current_edge, current_edge.verts[0], True)  # go in direction of vert 1
            follow_edge_loop(current_edge, current_edge.verts[1], False)  # go in direction of vert 0

            edge_strips.append(current_edge_loop)
            vert_strips.append(current_vert_loop)

        return vert_strips, edge_strips

    def sort_loops_by_first_vert(self, bm, vert_strips, edge_strips):
        #make parallel loops same direction by reversing if required
        sorted_v_strips = []
        sorted_e_strips = []
        while vert_strips:
            current_strip = vert_strips.pop()
            sorted_v_strips.append(current_strip)
            current_edge_strip = edge_strips.pop()
            sorted_e_strips.append(current_edge_strip)
            root_v1 = current_strip[0]
            # root_v2 = current_strip[-1]

            # rootv1_adj_ring_verts = [l_e.other_vert(root_v1) for l_e in root_v1.link_edges if not l_e.select and l_e.other_vert(root_v1).select]  # ring adj verts
            rootv1_adj_ring_verts = adj_ring_vert_better(root_v1, current_edge_strip[0])
            go_right = True
            for v1_linked_v in rootv1_adj_ring_verts:  # try going right from current_strip by searching for v1_linked_v
                current_vert = v1_linked_v
                old_vert = root_v1
                while vert_strips and current_vert:
                    for strip_id in range(len(vert_strips)):
                        sorted_strip = None
                        if current_vert == vert_strips[strip_id][0]:
                            sorted_strip = vert_strips.pop(strip_id)
                            sorted_e = edge_strips.pop(strip_id)
                        elif current_vert == vert_strips[strip_id][-1]:
                            sorted_strip = vert_strips.pop(strip_id)[::-1] #reversed
                            sorted_e = edge_strips.pop(strip_id)[::-1]  # reversed
                        if sorted_strip:
                            if go_right:
                                sorted_v_strips.append(sorted_strip)
                                sorted_e_strips.append(sorted_e)
                            else:
                                sorted_v_strips.insert(0, sorted_strip)
                                sorted_e_strips.insert(0, sorted_e)
                            # next_linked_vert = adj_ring_vert(current_vert, old_vert)
                            next_linked_vert = adj_ring_vert_better_ignoring(current_vert, sorted_e[0], old_vert) # curren_vert belongs to sorted_e_strip ... rihgt?
                            old_vert = current_vert
                            current_vert = next_linked_vert
                            break  # foor loop
                    if not sorted_strip:
                        current_vert = None
                    # current_vert = None #did not find next vert
                    # run_while = False
                go_right = False
        return sorted_v_strips, sorted_e_strips

    @staticmethod
    def calc_handles(bevel_target_pt, v1, v2, tension, segments):
        # lerp toward flat bevel  ==  low tension
        handle1 = bevel_target_pt.lerp(v1, 0.45) #* 0.45 - gives almost perfect circle bevel
        handle2 = bevel_target_pt.lerp(v2, 0.45)
        if tension <= 0.5: # toward flat bevel aka chamfer?
            flat_handle1 = v1.lerp(v2, 1/3)
            hand1_lerp = flat_handle1.lerp(handle1, tension*2)  # lerp toward flat_handle
            flat_handle2 = v2.lerp(v1, 1/3)
            hand2_lerp = flat_handle2.lerp(handle2, tension*2)  # lerp toward flat_handle
            resampled_pts = mathutils.geometry.interpolate_bezier(v1, hand1_lerp, hand2_lerp, v2, segments)  # (knot1, handle1, handle2, knot2, res)
        else: #toward sharp corner
            corner_pts = []
            for i in range(segments):
                t = i/(segments-1) # t in (0,1)
                if t < 0.5: #sample (v1, bevel_target) line
                    corner_sample = v1.lerp(bevel_target_pt, t*2)  #remap t (0, 0.5) to (0,1)
                else:  # sample (bevel_target, v2) line
                    corner_sample = bevel_target_pt.lerp(v2, (t-0.5)*2)  # remap t(0.5, 1) to (0,1)
                corner_pts.append(corner_sample)
            bezier_pts = mathutils.geometry.interpolate_bezier(v1, handle1, handle2, v2, segments)  # (knot1, handle1, handle2, knot2, res)
            resampled_pts = [bezier_p.lerp(corner_p, (tension-0.5)*2) for bezier_p, corner_p in zip(bezier_pts, corner_pts)]  # lerp to sharp corner for high tension

        return resampled_pts

    def rebevel(self, context, reb_size=None):
        active_obj = context.active_object
        if self.segments != self.start_segments or self.tension != self.start_tenison:
            self.only_resize = False

        bm = bmesh.from_edit_mesh(active_obj.data)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()

        if bpy.app.version < (4, 0, 0):
            bweight = bm.edges.layers.bevel_weight.verify()
            ecrease = bm.edges.layers.crease.verify()
        else:
            bweight = bm.edges.layers.float.get('bevel_weight_edge')
            # bweight = active_obj.data.attributes.get('bevel_weight_edge')
            # crease = active_obj.data.attributes.get('crease_edge')
            ecrease = bm.edges.layers.float.get('crease_edge')
            # TODO: how about all other attributes??

        verts_strips, edges_strips = self.my_get_sorted_loops(bm)
        verts_strips, edges_strips = self.sort_loops_by_first_vert(bm, verts_strips, edges_strips)

        if verts_strips:

            # clear faces between border edges. Bridge later
            if (self.segments != self.start_segments or self.use_profile) and len(verts_strips[0]) > 2:

                # cache edge data
                edge_cache = [{'bweight': e_loop[0][bweight] if bweight else 0, 'crease':e_loop[0][ecrease] if ecrease else 0, 'smooth':e_loop[0].smooth, 'seam':e_loop[0].seam} for e_loop in edges_strips]

                for i, verts_strip in enumerate(verts_strips):  # merge bever ring
                    bmesh.ops.dissolve_verts(bm, verts=verts_strip[1:-1], use_face_split=False, use_boundary_tear=False)
                    new_edges = bmesh.ops.connect_verts(bm, verts=[verts_strip[0], verts_strip[-1]])  # return dict
                    for edge in new_edges['edges']:  # only one it shoudl beee..
                        # use cache data
                        if bweight:
                            edge[bweight] = edge_cache[i]['bweight']
                        if ecrease:
                            edge[ecrease] = edge_cache[i]['crease']

                        edge.smooth = edge_cache[i]['smooth']
                        edge.seam = edge_cache[i]['seam']

                        edge.select = True
                        edges_strips[i] = [edge]

                bevel_faces = list(set([f for e in bm.edges if e.select for f in e.link_faces if all([v.select for v in f.verts])]))  # if all([v.select for v in f.verts]) - only inner bevel faces?
                # * copy face data (material and ? ) from adj geo
                for b_face in bevel_faces:
                    for e in b_face.edges:
                        if not e.select:  # cos if e.select -> then adj. face is bevel_face
                            for other_f in e.link_faces:
                                if other_f != b_face:
                                    b_face.copy_from(other_f)
                                    break
                            break

            bm.normal_update()

            # we have hole for bridge now. First we try to calculate bevel target for changing bevel width
            # Bevel target will lie on line calculated from -> intersect: v1.link_face.normal plane * v2.link_face.normal plane plane -> bevel_line_pt, bevel_line_dir;
            # * Calculate bevel_target_pts
            v1_v2_bevel_ring_edges = []
            bevel_target_pts = []
            for strip_id, verts_strip in enumerate(verts_strips):  # TODO: wont work if eg. script picks same faces for both verts.
                (v1, v2) = (verts_strip[0], verts_strip[-1])

                # * First get faces for  (plane X plane) intersections
                if self.start_segments != self.segments or self.use_profile:  # we merged bevel segments, so only v1 and v2 are left
                    v1_neibor = v2
                    v2_neibor = v1
                    connecting_edge = set(v1.link_edges) & (set(v2.link_edges))
                    e2 = e1 = connecting_edge.pop()
                    v1_v2_bevel_ring_edges.append(e1)
                else:
                    v1_neibor = verts_strip[1]
                    v2_neibor = verts_strip[-2]
                    e1 = edges_strips[strip_id][0]
                    e2 = edges_strips[strip_id][-1]

                # to define plane we need co, and normal  (vert, and face.normal)
                planes_v1 = [{'vert': v1, 'face': f} for f in v1.link_faces if f not in v1_neibor.link_faces]  # avoid picking bevel faces, and faces common to v1 and v2
                planes_v2 = [{'vert': v2, 'face': f} for f in v2.link_faces if f not in v2_neibor.link_faces]  # avoid picking bevel faces, and faces common to v1 and v2

                # we need 3 non cooplanar faces to get intersesction point if possible
                adj_cross_planes = []
                for candidate_plane in planes_v1+planes_v2:  # dot > 0.98 -> at least 12deg difference between plane normals
                    if not any([plane['face'].normal.dot(candidate_plane['face'].normal) > 0.98 for plane in adj_cross_planes]):  # exclude cooplanar  faces for intersect point
                        adj_cross_planes.append(candidate_plane)
                        if len(adj_cross_planes) >= 3:  # 3 are enough for 3x plane intersection
                            break
                cross_planes_count = len(adj_cross_planes)

                # ? what if none? then we cant recreate beevl anyway? O use fallback method...
                #* Get edges that are not belonging to bevel edges, but adjacent
                rail_edges = [get_counter_facing_edge(e1, v1), get_counter_facing_edge(e2, v2)]  # v1 and v2 rail edges if any

                def most_penperdicular_edge(reference_vec):
                    ''' pick most perpendicular rail edge to reference_vec '''
                    best_rail_v = None
                    r_vert = v1  # [(v1, rail_1), (v2, rail_2)]
                    max_dot = 0.99   # the smaller the dot, the more perpendicular rail is, the better
                    for rail_edge in rail_edges:  # max 2 edges #? maybe we should use one from  v1 rail and one from v2 rail
                        if not rail_edge:  # jump to second rail
                            r_vert = v2
                            continue
                        r_other_vert = rail_edge.other_vert(r_vert)
                        dot_result = abs(reference_vec.dot((r_vert.co - r_other_vert.co).normalized()))
                        if dot_result < max_dot:
                            max_dot = dot_result
                            best_rail_v = [r_vert, r_other_vert]
                        r_vert = v2
                    return best_rail_v

                if cross_planes_count == 0:  # no connected faces then just bridge #? maybe use railedges intersection if any(rail_edges)?
                    if None not in rail_edges:  # we got two rails. Use them
                        #should cross both on
                        (bevel_target_pt, bevel_target_pt2) = mathutils.geometry.intersect_line_line(v1.co, rail_edges[0].other_vert(v1).co, v2.co, rail_edges[1].other_vert(v2).co,)
                        bevel_target_pts.append(bevel_target_pt)
                    else: #worst case scenario
                        bevel_target_pts.append((v1.co+v2.co)/2)

                elif cross_planes_count == 1:
                    #? maybe use railedges intersection if any(rail_edges)?
                    if None not in rail_edges:# we got two rails. Use them
                        #should cross both on
                        (bevel_target_pt, bevel_target_pt2) = mathutils.geometry.intersect_line_line(v1.co, rail_edges[0].other_vert(v1).co, v2.co, rail_edges[1].other_vert(v2).co,)
                        bevel_target_pts.append(bevel_target_pt)
                    else: #we got jsut one rail one plane. No use
                        # project v1, v2 on plane to get bevel_target
                        avg_v12 = (v1.co+v2.co)/2
                        pt_distance = mathutils.geometry.distance_point_to_plane(avg_v12, adj_cross_planes[0]['vert'].co, adj_cross_planes[0]['face'].normal)  # negative == below plane norm
                        bevel_target_pt = avg_v12 + adj_cross_planes[0]['face'].normal * (-1) * pt_distance  # move avg_v12 toward surface
                        bevel_target_pts.append(bevel_target_pt)

                elif cross_planes_count >= 2:  # 2 planes intersection gives line. Cross with v1-v2 line gives target point
                    # intersect 2 faces from v1 and v2 - we get intersection line - bevel target will lay on it
                    bevel_line_pt, bevel_line_dir = mathutils.geometry.intersect_plane_plane(
                        adj_cross_planes[0]['vert'].co, adj_cross_planes[0]['face'].normal, adj_cross_planes[1]['vert'].co, adj_cross_planes[1]['face'].normal)

                    if cross_planes_count == 2:  # intersect 2planes with one of rail edges
                        # * pick best rail edge for intersection with p x p line
                        best_rail_v = most_penperdicular_edge(bevel_line_dir.normalized())
                        if best_rail_v:
                            (bevel_target_pt, v12_cross_point) = mathutils.geometry.intersect_line_line(bevel_line_pt, bevel_line_pt+bevel_line_dir, best_rail_v[0].co, best_rail_v[1].co)
                            bevel_target_pts.append(bevel_target_pt)
                        else:  # worst case: project v12 to plane x plane line
                            avg_v12 = (v1.co+v2.co)/2
                            bevel_target_pt, distance = mathutils.geometry.intersect_point_line(avg_v12, bevel_line_pt, bevel_line_pt+bevel_line_dir)
                            bevel_target_pts.append(bevel_target_pt)

                    if cross_planes_count == 3:  # best case scenario - for predicting bevel target - 3 planes intersections gives target point
                        bevel_target_pt = mathutils.geometry.intersect_line_plane(bevel_line_pt, bevel_line_pt+bevel_line_dir, adj_cross_planes[2]['vert'].co, adj_cross_planes[2]['face'].normal)
                        bevel_target_pts.append(bevel_target_pt)

            # * done calculating bevel_target_pts now

            #* calc bevel scale facter per loop - smaller loop - slower lerp in next step
            if self.resize_mode == 'PROP':
                scale_factor = [1]*len(verts_strips)
            else:
                scale_factor = []
                for verts_strip, bevel_target_pt in zip(verts_strips, bevel_target_pts):
                    if bevel_target_pt:
                        scale_factor.append((verts_strip[0].co - bevel_target_pt).length/2 + (verts_strip[-1].co - bevel_target_pt).length/2)
                    else:
                        scale_factor.append(scale_factor[-1])
                min_el = min(scale_factor) #! what if 0?
                scale_factor = [e/min_el for e in scale_factor]


            # * scale each verts_strip to bevel_target_pt
            for verts_strip, bevel_target_pt, sc_fac in zip(verts_strips, bevel_target_pts, scale_factor):
                if bevel_target_pt:
                    target_verts = [verts_strip[0], verts_strip[-1]] if self.start_segments != self.segments or self.use_profile else verts_strip  # veld remaining 2 points, or all verts_strip
                    if reb_size > 0:
                        for v in target_verts:
                            # v.co = bevel_target_pt.lerp(v.co, sc_fac*reb_size)
                            targt = v.co.lerp(bevel_target_pt, 1/sc_fac)  # move bevel_target_pt toward v.co, based on scale_fac
                            v.co = targt.lerp(v.co, reb_size)
                    elif reb_size == 0:  # make bevel into zero segments by dissolving segments points
                        bmesh.ops.pointmerge(bm, verts=target_verts, merge_co=bevel_target_pt)  # points will be merged into first
                else:
                    print('No bevel target found for scaling bevel width')

            # we did not change bevel segmetns or there are not segmetns, then finish
            if ((self.segments == self.start_segments and self.only_resize) or self.segments == 0) and not self.use_profile or reb_size == 0:
                bm.normal_update()
                bmesh.update_edit_mesh(active_obj.data)
                if not self.run_exec:
                    bpy.ops.ed.undo_push()
                return

            # * 'BEVEL' - subdivide bevel  type of re-bevel
            if self.segments == self.start_segments and not self.only_resize and not self.use_profile:  # smooth not rebeveled loops
                new_verts_strips = verts_strips
                normalized_bevel_pts = super_elipse2(self.tension, self.segments+2)
                for verts_strip, bevel_target_pt in zip(verts_strips, bevel_target_pts):
                    # resampled_pts = self.calc_handles(bevel_target_pt, verts_strip[0].co, verts_strip[-1].co, self.tension, self.segments+2)
                    bevel_pts = barycentric_transform(normalized_bevel_pts, bevel_target_pt, verts_strip[0].co, verts_strip[-1].co, self.tension)
                    for vert, target_co in zip(verts_strip, bevel_pts):
                        vert.co = target_co

            elif self.segments != self.start_segments or self.use_profile:
                # back_verts_strips = [[v.index for v in verts_strip if v.is_valid] for verts_strip in verts_strips] #?

                seg_count = self.segments if not self.use_profile else len(context.tool_settings.custom_bevel_profile_preset.points)-2
                #* subdivide each edge seg_count times (and reinitialize verts_strips to new_verts_strips)
                # gen_geo = bmesh.ops.subdivide_edges(bm, edges=v1_v2_bevel_ring_edges, smooth=0, smooth_falloff='SHARP', fractal=0, along_normal=0, cuts=seg_count)
                new_verts_strips = []
                new_edges_strips = []
                for idx, (verts_strip, bevel_e) in enumerate(zip(verts_strips, v1_v2_bevel_ring_edges)): #? maybe then connect the split edges cente
                    (v1, v2) = (verts_strip[0], verts_strip[-1])
                    new_verts_strips.append([v1]) # len is split_edges + 1
                    new_edges_strips.append([])

                    split_edge = bevel_e  # split it seg_count times
                    from_vert = v1
                    for i in range(seg_count):
                        (new_edge, new_vert) = bmesh.utils.edge_split(split_edge, from_vert, 1/(seg_count+1-i))
                        new_edges_strips[idx].append(new_edge)
                        new_verts_strips[idx].append(new_vert)
                        new_edge.select = True
                        new_vert.select = True
                        from_vert = new_vert
                    new_edges_strips[idx].append(split_edge) #it becomes last edge (adj to v2)
                    new_verts_strips[idx].append(v2)

                #* bridge adj rings verts accros with edges.
                if len(new_verts_strips) > 1:  # at least to bevel rings required for connection across
                    prev_vert_strip = new_verts_strips[0]
                    new_verts_strips.append(new_verts_strips[0]) # makes it cyclic - we bridge last and first vert strip. But below we check if vstrips are adjacent anyway
                    for vert_strip in new_verts_strips[1:]:
                        if len(prev_vert_strip) != len(vert_strip) or len(prev_vert_strip) < 3:  # each ring has to have at least 3 verts (first and last are already connected)
                            prev_vert_strip = vert_strip
                            continue # cant connect two ring if different vert count

                        # no common edge on first ring verts, and last ring verts - must be not adjacent
                        if not (set(prev_vert_strip[0].link_edges) & set(vert_strip[0].link_edges) and set(prev_vert_strip[-1].link_edges) & set(vert_strip[-1].link_edges)):
                            prev_vert_strip = vert_strip
                            continue  # then rings are not adjacent.

                        #two vert strips are adjacent (first verts pair is linked by one edge, and last verts in strip also are connected)
                        for v_ring1, v_ring2 in zip(prev_vert_strip[1:-1], vert_strip[1:-1]):
                            bmesh.ops.connect_vert_pair(bm, verts=[v_ring1, v_ring2])
                            # bmesh.ops.connect_verts(bm, [prev, ring_v])
                            # bm.edges.new([prev, ring_v])
                            prev_vert_strip = vert_strip
                    new_verts_strips.pop()  # remove last appended new_verts_strips[0] element

                #* finally put new bevel rings on spline
                src_tri = [Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((1, 1, 0))]
                if self.use_profile:
                    for new_verts_strip, bevel_target_pt in zip(new_verts_strips, bevel_target_pts):  # recover original strips bevel_target points
                        for vert, profile_pt in zip(new_verts_strip, context.tool_settings.custom_bevel_profile_preset.points):
                            out_pt = mathutils.geometry.barycentric_transform(profile_pt.location.to_3d(), src_tri[0], src_tri[1], src_tri[2],
                                                                              new_verts_strip[0].co, new_verts_strip[-1].co, bevel_target_pt)
                            vert.co = out_pt
                else:
                    normalized_bevel_pts = super_elipse2(self.tension, self.segments+2)
                    for new_verts_strip, bevel_target_pt in zip(new_verts_strips, bevel_target_pts):  # recover original strips bevel_target points
                        # resampled_pts = self.calc_handles(bevel_target_pt, new_verts_strip[0].co, new_verts_strip[-1].co, self.tension, self.segments+2)
                        bevel_pts = barycentric_transform(normalized_bevel_pts, bevel_target_pt, new_verts_strip[0].co, new_verts_strip[-1].co, self.tension)
                        for vert, target_co in zip(new_verts_strip, bevel_pts):
                            vert.co = target_co

            bm.normal_update()
            bmesh.update_edit_mesh(active_obj.data)
            if not self.run_exec:
                bpy.ops.ed.undo_push()
            return

        if not self.run_exec:
            bpy.ops.ed.undo_push()

        return

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.mode == 'EDIT'

    def draw(self, context):
        layout = self.layout
        layout.prop(self, 'rebevel_size')
        layout.prop(self, 'resize_mode')
        if not self.use_profile:
            layout.prop(self, 'segments')
            if not self.only_resize or self.segments != self.start_segments:
                layout.prop(self, 'tension')
        if bpy.app.version >= (2, 82, 0):
            layout.prop(self, 'use_profile')
            if self.use_profile:
                layout.template_curveprofile(context.tool_settings, "custom_bevel_profile_preset")

    def invoke(self, context, event):
        active_obj = context.active_object
        bpy.ops.ed.undo_push()
        bm = bmesh.from_edit_mesh(active_obj.data)
        sel_mode = context.scene.tool_settings.mesh_select_mode[:]
        if sel_mode != (False, True, False):
            self.report({'ERROR'}, 'Switch to edge mode and select bevel rings!')
            return {'CANCELLED'}
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        try:
            vert_loops, _ = self.my_get_sorted_loops(bm)
        except ValueError as ve:
            print('Error: in self.my_get_sorted_loops(bm)' + str(ve))
            self.report({'ERROR'}, 'Select correct bevel ring!')
            return {'CANCELLED'}
        self.start_segments = len(vert_loops[0])-2  # how much bevel segmetns there are at begining
        self.start_tenison = self.tension
        if self.use_profile:
            self.start_segments = -1
            self.segments = len(context.tool_settings.custom_bevel_profile_preset.points)
        else:
            self.segments = self.start_segments
        self.rebevel_size = 1
        self.prev_settings = (self.rebevel_size, self.segments, self.tension)
        self.use_profile = False
        self.only_resize = True #by default start rebevel as resize of bevel ring loops
        self.run_exec = False

        self.start_x = event.mouse_region_x
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}


    def execute(self, context):
        if self.last_modal_rebevel_size == 0:
            return {'FINISHED'}
        self.run_exec = True
        # remap current rebevel size to 1 if self.rebevel_size == self.last_modal_rebevel_size
        self.rebevel(context, self.rebevel_size / self.last_modal_rebevel_size)
        return {'FINISHED'}

    def check(self, context):
        return True

    def do_update(self, context):
        if self.prev_settings == (self.rebevel_size, self.segments, self.tension):
            return {"RUNNING_MODAL"}
        else:
            bpy.ops.ed.undo() # to restore default mesh state
            self.rebevel(context, self.rebevel_size)
            self.prev_settings = (self.rebevel_size, self.segments, self.tension)

    def modal(self, context, event):
        if event.type == 'MOUSEMOVE':
            diff = (event.mouse_region_x - self.start_x)/200
            if event.ctrl:
                margin = 35 / 200
                if abs(diff) < margin: #snap to (1 + 0)
                    diff = 0.0
                if abs(diff + 0.5) < margin:  # snap for bevel size (1 - 0.5)
                    diff = - 0.5
                if abs(diff - 1.0) < margin:  # snap for bevel (1 + 1)
                    diff = 1.0
                if abs(diff - 3.0) < margin:  # snap for bevel (1 + 3)
                    diff = 3.0

            self.rebevel_size = max(0.0, 1+diff)
            resize_mode = 'Proportional' if self.resize_mode == 'PROP' else 'Uniform'
            context.workspace.status_text_set(
                f'Beves size: {self.rebevel_size:.2f}      [MMB] Segments: {self.segments}     [Ctrl] Snap: {event.ctrl}     [Shift] Shape: {self.tension:.2f}      [M] Resize Mode: {resize_mode}')
            self.do_update(context)

        elif event.type == 'M' and event.value == 'PRESS':
            self.resize_mode = 'UNIFORM' if self.resize_mode == 'PROP' else 'PROP'

        elif event.type == 'WHEELUPMOUSE' or (event.type == 'TWO' and event.value == 'PRESS'):
            if event.shift:
                self.tension += 0.1
            else:
                self.segments += 1
            self.do_update(context)
        elif event.type == 'WHEELDOWNMOUSE' or (event.type == 'ONE' and event.value == 'PRESS'):
            if event.shift:
                self.tension -= 0.1
            else:
                self.segments = max(self.segments - 1, 0)
            self.do_update(context)

        elif event.type == "LEFTMOUSE":
            # context.window_manager.invoke_props_dialog(self)
            # hack cos edit bmesh now is != from begning one
            #so if seg count changed in modal, thing will go wrong without this
            context.workspace.status_text_set(None)
            self.last_modal_rebevel_size = self.rebevel_size
            self.start_segments = self.segments
            return {"FINISHED"}

        elif event.type in {"RIGHTMOUSE", "ESC"}:
            context.workspace.status_text_set(None)
            return {"CANCELLED"}

        return {"RUNNING_MODAL"}