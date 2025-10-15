import bpy
import bmesh
import weakref
import math
from math import pi
from ..utility.draw import draw_tris, draw_line, draw_circle, draw_label
import os
from ..utility.draw import draw_image_2d
import types
import traceback

ICONS_DIR = os.path.join(os.path.dirname(__file__), 'icons')
_ICON_CACHE = {}
_OP_CLASS_CACHE = None  # lazy-built mapping of bl_idname -> operator class

# -----------------------------
# Easy theme / tuning parameters (user-adjustable at top of file)
PIE_CONFIG = {
    'RADIUS': 180,                 # base outer radius (was 120)
    'INNER_RADIUS_FACTOR': 0.45,   # inner ring = RADIUS * factor
    'CENTER_RADIUS_FACTOR': 0.50,  # center disk = inner * factor
    'BORDER_COLOR': (1, 1, 1, 0.18),
    'SPOKE_COLOR': (1, 1, 1, 0.15),
    'HOVER_SLICE_FILL': (1.0, 0.9, 0.2, 0.28),  # hover slice overlay
    'HOVER_SLICE_OUTLINE': (1.0, 0.9, 0.2, 0.9),
    'ICON_SIZE': 36,
    'SLICE_SCALE_HOVER': 1.0,       # how much the hovered slice inflates (1.0 = no scale)
    'PIE_RADIUS_HOVER_SCALE': 1.0,  # overall pie grows when hovering a slice (1.0 = no scale)
    'HOVER_OUTER_EXTRUDE': 14.0,    # px to push the hovered wedge's OUTER arc outward (inner stays)
    'HOVER_ICON_SCALE': 1.3,       # scale for hovered icon only
    'CENTER_TEXT_SIZE': 14,
    'CENTER_SUBTEXT_SIZE': 12,
    'SIDE_LABEL_SIZE': 14,
    'CENTER_SUBTEXT_COLOR': (0.85,0.85,0.85,0.85),
    'SIDE_LABEL_COLOR': (1,1,1,0.9),
    'CANCEL_HINT': False,          # we keep cancel by center hover but hide visuals
    'HOVER_GUIDE': False,
}

def _load_icon_image(name):
    """Load an image from addon/ui/icons by file name. Cached by absolute path."""
    path = os.path.join(ICONS_DIR, name)
    if not os.path.exists(path):
        return None
    abspath = os.path.abspath(path)
    # If we have a cached image object, ensure it's still valid in bpy.data.images
    if abspath in _ICON_CACHE:
        cached = _ICON_CACHE[abspath]
        try:
            if cached and cached in bpy.data.images:
                return cached
        except Exception:
            pass
        # stale cache entry, remove and attempt to reload
        _ICON_CACHE.pop(abspath, None)
    # try find an already loaded image with same filepath
    for im in bpy.data.images:
        try:
            if im.filepath and os.path.abspath(bpy.path.abspath(im.filepath)) == abspath:
                _ICON_CACHE[abspath] = im
                return im
        except Exception:
            pass
    try:
        im = bpy.data.images.load(abspath, check_existing=True)
        _ICON_CACHE[abspath] = im
        return im
    except Exception:
        return None


def _hud_draw(op_id):
    """Module-level draw handler. Looks up the weakref for the operator and calls its _draw.
    This prevents the draw handler from keeping the operator RNA alive and avoids
    "StructRNA ... has been removed" errors when the operator is cancelled elsewhere.
    """
    try:
        mod = globals()
        ops = mod.get('_HUD_OPS')
        if not ops:
            return
        ref = ops.get(op_id)
        if not ref:
            return
        op = ref()
        if not op:
            # operator was GC'd or removed; clean up handler
            
            handlers = mod.get('_HUD_HANDLERS') or {}
            h = handlers.pop(op_id, None)
            if h:
                try:
                    bpy.types.SpaceView3D.draw_handler_remove(h, 'WINDOW')
                except Exception:
                    pass
            ops.pop(op_id, None)
            return
        # call operator draw
        try:
            op._draw(bpy.context)
        except Exception:
            pass
    except Exception:
        pass

# Preferences helper -----------------------------------------------------------
def _get_addon_prefs():
    try:
        # The add-on root package is two levels up: hardsurface_blender_tool
        addon_key = __name__.split('.')[0]
        return bpy.context.preferences.addons.get(addon_key, None).preferences if addon_key in bpy.context.preferences.addons else None
    except Exception:
        return None

# -----------------------------
# Simple, user-editable pie items
# Edit this function to customize your pie menu entries.
# Return a list of tuples: (label, operator_idname, props_dict)
# - label: displayed text for the slice
# - operator_idname: e.g. 'wm.search' or 'view3d.view_persportho'. Use None for a disabled/placeholder slice.
# - props_dict: optional dict of operator properties, e.g. {'use_global': True}
#   You can also pass an explicit icon filename as the third item either as a
#   string ("apply.png") or as a props dict: ("Apply", "tmc.op", {"icon":"apply.png"})
def get_default_pie_items():
    """Hardcoded fallback defaults for the HUD pie."""
    return [
        ("Clone Element", "tmc.clone_element", "clone.png"),
        ("Detach Element", "tmc.detach_element", "detach.png"),
        ("Toggle Modifier", "tmc.toggle_modifier", "toggle.png"),
        ("Apply Modifier", "tmc.apply_modifier", "apply.png"),
        ("ReBevel", "tmc.rebevel_smart", "rebevel.png"),
        ("Boolean", "tmc.boolean", "boolean.png"),
        ("Delete", "tmc.auto_delete", "delete.png"),
        ("Clear Vertex Group", "tmc.clean_vertex_group", "vertex_group.png"),
        ("Set Normal to Active", "tmc.set_normal_with_active_face", "normal_face.png"),
        ("Clear Custom Normals", "tmc.clear_custom_normals_data", "custom_normal.png"),
    ]

# Map operator idname -> default icon file (string) for convenient fallback in prefs
DEFAULT_ICON_MAP = {entry[1]: (entry[2] if len(entry) > 2 and isinstance(entry[2], str) else "") for entry in get_default_pie_items()}

def get_pie_items(context=None):
    """Return current pie items, pref-driven if available, else defaults."""
    prefs = _get_addon_prefs()
    items = []
    try:
        if prefs and getattr(prefs, 'pie_items', None) and len(prefs.pie_items) > 0:
            for it in prefs.pie_items:
                label = it.name or it.op
                op = it.op
                # Prefer explicit icon from prefs; else fall back to default mapping by operator
                icon = it.icon if getattr(it, 'icon', None) else None
                if (not icon) and op:
                    icon = DEFAULT_ICON_MAP.get(op, None)
                # Always pass icon as a plain string so execute() doesn't treat it as op kwargs
                if icon:
                    items.append((label, op, icon))
                else:
                    # let icon auto-resolve from label/op later by passing string
                    items.append((label, op, label.lower().replace(' ', '_') + '.png'))
            return items
    except Exception:
        pass
    # Fallback defaults
    return get_default_pie_items()

# --------------------------------------
# Enable/Disable conditions for pie items (optional overrides)
def _cond_mesh_edit_component_selected(context):
    obj = context.active_object
    if not obj or obj.type != 'MESH' or context.mode != 'EDIT_MESH':
        return False
    try:
        bm = bmesh.from_edit_mesh(obj.data)
        if any(v.select for v in bm.verts):
            return True
        if any(e.select for e in bm.edges):
            return True
        if any(f.select for f in bm.faces):
            return True
    except Exception:
        # fallback to mesh data if bmesh not available
        try:
            if any(p.select for p in obj.data.polygons):
                return True
        except Exception:
            pass
    return False

# Map operator idnames to default enable conditions (rarely needed if poll is correct)
OP_ENABLE_RULES = {
    'tmc.clone_element': 'mesh_edit_component_selected',
}

CONDITIONS = {
    'mesh_edit_component_selected': _cond_mesh_edit_component_selected,
}

def _find_operator_class(op_idname):
    global _OP_CLASS_CACHE
    # Build cache once to avoid scanning bpy.types every draw
    if _OP_CLASS_CACHE is None:
        mapping = {}
        try:
            for name in dir(bpy.types):
                cls = getattr(bpy.types, name, None)
                if not isinstance(cls, type):
                    continue
                try:
                    if issubclass(cls, bpy.types.Operator):
                        bid = getattr(cls, 'bl_idname', None)
                        if bid:
                            mapping[bid] = cls
                except Exception:
                    continue
        except Exception:
            mapping = {}
        _OP_CLASS_CACHE = mapping
    # Return from cache; if not present, best-effort fallback
    cls = _OP_CLASS_CACHE.get(op_idname)
    if cls:
        return cls
    # One-off slow path to find and cache
    try:
        for name in dir(bpy.types):
            cls2 = getattr(bpy.types, name, None)
            if not isinstance(cls2, type):
                continue
            try:
                if issubclass(cls2, bpy.types.Operator):
                    if getattr(cls2, 'bl_idname', None) == op_idname:
                        _OP_CLASS_CACHE[op_idname] = cls2
                        return cls2
            except Exception:
                continue
    except Exception:
        pass
    return None

def _is_item_enabled(context, entry):
    try:
        op = entry[1] if len(entry) >= 2 else None
        # If no operator, disabled
        if not op:
            return False
        # Explicit per-item condition via props.enable_if
        cond_key = None
        if len(entry) >= 3 and isinstance(entry[2], dict):
            cond_key = entry[2].get('enable_if')
        if cond_key:
            fn = CONDITIONS.get(cond_key)
            return True if not fn else bool(fn(context))
        # Prefer operator class's poll
        try:
            op_cls = _find_operator_class(op)
            if op_cls and hasattr(op_cls, 'poll'):
                return bool(op_cls.poll(context))
        except Exception:
            pass
        # Fallback to mapping
        cond_key = OP_ENABLE_RULES.get(op)
        if cond_key:
            fn = CONDITIONS.get(cond_key)
            return True if not fn else bool(fn(context))
        # Default enabled
        return True
    except Exception:
        return True

class TMC_OT_HUDPieMenu(bpy.types.Operator):
    bl_idname = "tmc.hud_pie"
    bl_label = "HS - Circle Menu"
    bl_description = "Circle (GTA-style) radial menu"
    bl_options = {"REGISTER", "BLOCKING"}

    # Items source: user-editable function, easy to modify
    def _items(self, context):
        return get_pie_items(context)

    def _fallback_items(self):
        return [
            ("Toggle Modifiers", "tmc.toggle_modifier"),
        ]

    def _sector_tris(self, cx, cy, r0, r1, a0, a1, steps=24):
        tris = []
        da = (a1 - a0) / steps
        for i in range(steps):
            a = a0 + i * da
            b = a + da
            p0 = (cx + r0 * math.cos(a), cy + r0 * math.sin(a))
            p1 = (cx + r1 * math.cos(a), cy + r1 * math.sin(a))
            p2 = (cx + r1 * math.cos(b), cy + r1 * math.sin(b))
            p3 = (cx + r0 * math.cos(b), cy + r0 * math.sin(b))
            tris.extend([p0, p1, p2])
            tris.extend([p0, p2, p3])
        return tris

    def _disk_tris(self, cx, cy, r, steps=24):
        tris = []
        da = 2*pi / steps
        for i in range(steps):
            a = i * da
            b = a + da
            p0 = (cx, cy)
            p1 = (cx + r * math.cos(a), cy + r * math.sin(a))
            p2 = (cx + r * math.cos(b), cy + r * math.sin(b))
            tris.extend([p0, p1, p2])
        return tris

    def _angle_to_index(self, ang):
        # determine slice count from cached value or cached items; fallback to 8
        n = getattr(self, '_slice_count', None)
        if not n:
            items_cached = getattr(self, '_slice_items', None)
            try:
                n = len(items_cached) if items_cached is not None else 0
            except Exception:
                n = 0
        try:
            n = int(n) if n and n > 0 else 8
        except Exception:
            n = 8
        ang = (ang - (-pi/2)) % (2*pi)
        idx = int((ang / (2*pi)) * n) % n
        # clamp to valid range
        try:
            if hasattr(self, '_slice_items') and idx >= len(self._slice_items):
                idx = len(self._slice_items) - 1
        except Exception:
            pass
        return idx

    def _draw(self, context):
        # Hovering color & config
        cfg = PIE_CONFIG
        hi = cfg['HOVER_SLICE_OUTLINE']
        cx, cy = self.center
        # use precomputed radii for consistency and performance
        R_outer = getattr(self, '_R_outer', self.radius)
        R_inner = getattr(self, '_R_inner', int(self.radius * PIE_CONFIG['INNER_RADIUS_FACTOR']))
        R_center = getattr(self, '_R_center', int(R_inner * PIE_CONFIG['CENTER_RADIUS_FACTOR']))

        # Determine hover state early to decide ring drawing
        items = getattr(self, '_slice_items', None) or (self._items(context) or self._fallback_items())
        n = max(1, len(items))
        hovering_center_early = False
        if hasattr(self, 'mouse'):
            mx, my = self.mouse
            dx, dy = mx - cx, my - cy
            hovering_center_early = dx*dx + dy*dy <= (R_center * R_center)
        hover_index_early = self.index if (0 <= getattr(self, 'index', -1) < n and not hovering_center_early) else -1

        # base ring and spokes
        # Draw inner ring globally; outer border will be drawn per-slice (allows only hovered slice to expand)
        draw_circle(loc=(cx, cy, 0), radius=R_inner, segments=48, color=cfg['BORDER_COLOR'], width=2.0)
        # Precompute hover state so we can skip spokes at hovered edges
        angles = getattr(self, '_angles', None)
        if not angles or len(angles) != n:
            angles = [-pi/2 + i * (2*pi / n) for i in range(n)]
        # Determine if cursor is in center and which slice index is hovered
        hovering_center = False
        if hasattr(self, 'mouse'):
            mx, my = self.mouse
            dx, dy = mx - cx, my - cy
            hovering_center = dx*dx + dy*dy <= (R_center * R_center)
        hover_index_for_spokes = self.index if (0 <= getattr(self, 'index', -1) < n and not hovering_center) else -1
        for j, a in enumerate(angles):
            # Skip spokes that coincide with hovered slice edges to hide the white seam
            if hover_index_for_spokes != -1 and (j == hover_index_for_spokes or j == ((hover_index_for_spokes + 1) % n)):
                continue
            x0 = cx + R_inner * math.cos(a)
            y0 = cy + R_inner * math.sin(a)
            x1 = cx + R_outer * math.cos(a)
            y1 = cy + R_outer * math.sin(a)
            draw_line([(x0, y0, 0), (x1, y1, 0)], color=cfg['SPOKE_COLOR'], width=1.5)

        # Draw outer arc border per slice; hovered slice uses extruded radius
        for i in range(n):
            a0_i = -pi/2 + i * (2*pi / n)
            a1_i = a0_i + (2*pi / n)
            r_out_line = R_outer + (PIE_CONFIG.get('HOVER_OUTER_EXTRUDE', 0.0) if (hover_index_early == i) else 0.0)
            arc_steps = 48
            arc_pts = []
            for k in range(arc_steps+1):
                t = k/arc_steps
                ang_k = a0_i*(1-t) + a1_i*t
                arc_pts.append((cx + r_out_line * math.cos(ang_k), cy + r_out_line * math.sin(ang_k), 0))
            draw_line(arc_pts, color=cfg['BORDER_COLOR'], width=2.0)

        # draw slice icons (use cached slice items/images if available)
        items = getattr(self, '_slice_items', None) or (self._items(context) or self._fallback_items())
        n = max(1, len(items))
        # compute enabled flags once per draw
        enabled_flags = []
        try:
            for entry in items:
                enabled_flags.append(_is_item_enabled(context, entry))
        except Exception:
            enabled_flags = [True] * n
        # determine hover center before deciding slice visuals
        hovering_center = False
        if hasattr(self, 'mouse'):
            mx, my = self.mouse
            dx, dy = mx - cx, my - cy
            hovering_center = dx*dx + dy*dy <= (R_center * R_center)

        hover_index = (self.index if (0 <= self.index < n and not hovering_center) else -1)

        # Apply global pie growth when hovering a slice
        scale_pie = PIE_CONFIG.get('PIE_RADIUS_HOVER_SCALE', 1.0) if hover_index != -1 else 1.0
        if scale_pie != 1.0:
            R_outer *= scale_pie
            R_inner *= scale_pie
            R_center = int(R_inner * PIE_CONFIG['CENTER_RADIUS_FACTOR'])
        for i in range(n):
            # Use precomputed slice images/labels when available (computed in invoke)
            # apply slice scale on hover
            slice_scale = (cfg['SLICE_SCALE_HOVER'] if i == hover_index else 1.0)
            am = -pi/2 + (i + 0.5) * (2*pi / n)
            r_mid = R_inner + 0.55 * (R_outer - R_inner) * slice_scale
            x = cx + r_mid * math.cos(am)
            y = cy + r_mid * math.sin(am)
            picked = None
            try:
                if hasattr(self, '_slice_images') and i < len(self._slice_images):
                    picked = self._slice_images[i]
            except Exception:
                picked = None

            if picked:
                try:
                    size = cfg['ICON_SIZE'] * (cfg['HOVER_ICON_SCALE'] if i == hover_index else 1.0)
                    draw_image_2d(picked, x - size/2, y - size/2, size, size)
                except Exception:
                    pass

            # Dim overlay if this slice is disabled
            if not enabled_flags[i]:
                try:
                    # use precomputed overlay tris when available
                    tris_i = None
                    if hasattr(self, '_slice_sector_tris') and i < len(self._slice_sector_tris):
                        tris_i = self._slice_sector_tris[i]
                    if not tris_i:
                        a0_i = -pi/2 + i * (2*pi / n)
                        a1_i = a0_i + (2*pi / n)
                        tris_i = self._sector_tris(cx, cy, R_inner + 1.0, R_outer - 1.0, a0_i + 0.01, a1_i - 0.01, steps=40)
                    draw_tris([(xx, yy, 0) for (xx, yy) in tris_i], color=(0.0, 0.0, 0.0, 0.4))
                except Exception:
                    pass

        # highlight selected sector with overdraw (or center if hovering center)

        # sector angular extents depend on current slice count
        n = getattr(self, '_slice_count', None)
        if not n:
            n = max(1, len(getattr(self, '_slice_items', []) or self._items(context) or []))
        try:
            n = int(n) if n and n > 0 else 8
        except Exception:
            n = 8
        a0 = -pi/2 + self.index * (2*pi / n)
        a1 = a0 + (2*pi / n)
        pad_r_inner = 2.0
        pad_r_outer = 2.0
        pad_ang = 0.006
        if not hovering_center and hover_index != -1:
            tris = self._sector_tris(cx, cy,
                                     R_inner - pad_r_inner,
                                     R_outer + pad_r_outer + PIE_CONFIG.get('HOVER_OUTER_EXTRUDE', 0.0),
                                     a0 - pad_ang,
                                     a1 + pad_ang,
                                     steps=64)
            draw_tris([(x, y, 0) for (x, y) in tris], color=cfg['HOVER_SLICE_FILL'])

        # bold outlines — align radial edges and arcs to the same padded radii so seams disappear
        if not hovering_center and hover_index != -1:
        # use the same padding as the filled sector so the outlines meet exactly
            r_in_edge = R_inner - pad_r_inner
            r_out_edge = R_outer + pad_r_outer + PIE_CONFIG.get('HOVER_OUTER_EXTRUDE', 0.0)
            rx0_in, ry0_in = cx + r_in_edge * math.cos(a0), cy + r_in_edge * math.sin(a0)
            rx0_out, ry0_out = cx + r_out_edge * math.cos(a0), cy + r_out_edge * math.sin(a0)
            rx1_in, ry1_in = cx + r_in_edge * math.cos(a1), cy + r_in_edge * math.sin(a1)
            rx1_out, ry1_out = cx + r_out_edge * math.cos(a1), cy + r_out_edge * math.sin(a1)
            draw_line([(rx0_in, ry0_in, 0), (rx0_out, ry0_out, 0)], color=hi, width=3.8)
            draw_line([(rx1_in, ry1_in, 0), (rx1_out, ry1_out, 0)], color=hi, width=3.8)

        # increase tessellation for smoother arc outlines (balanced)
        if not hovering_center and hover_index != -1:
            arc_steps = 72
            arc_pts = []
            for i in range(arc_steps+1):
                t = i/arc_steps
                a = a0*(1-t) + a1*t
                arc_pts.append((cx + r_out_edge * math.cos(a), cy + r_out_edge * math.sin(a), 0))
            draw_line(arc_pts, color=hi, width=3.8)

            inner_arc_pts = []
            for i in range(arc_steps+1):
                t = i/arc_steps
                a = a0*(1-t) + a1*t
                inner_arc_pts.append((cx + r_in_edge * math.cos(a), cy + r_in_edge * math.sin(a), 0))
            draw_line(inner_arc_pts, color=hi, width=3.8)

        # Hover guideline removed per request

        # side label or cancel hint
        # Center text + logo (always rendered) -------------------------------------------------
        # Show current slice label (or instruction) inside center ring with an icon if available
        center_label = ""  # assembled below
        center_sub = ""
        if items:
            idx = self.index if 0 <= self.index < len(items) else max(0, len(items)-1)
            entry = items[idx]
            label = entry[0] if entry else ""
            # add disabled hint using cached flags
            enabled = True
            try:
                enabled = enabled_flags[idx]
            except Exception:
                pass
            if not enabled and label and not hovering_center:
                # Show 'Disabled' as a second row in the center
                center_sub = "Disabled"
            center_label = label

        # Draw center icon (cancel when hovering center) and text stacked
        try:
            icon_img = None
            if hovering_center:
                # Prefer cancel.png; fallback to false.png or blender.png
                icon_img = _load_icon_image('cancel.png') or _load_icon_image('false.png') or _load_icon_image('blender.png')
                # Override label to make intent obvious
                center_label = "Cancel"
            elif items and hasattr(self, '_slice_images') and self.index < len(self._slice_images):
                icon_img = self._slice_images[self.index]
            else:
                icon_img = _load_icon_image('blender.png')
            if icon_img:
                icon_size = int(PIE_CONFIG['ICON_SIZE'] * 1.05)
                draw_image_2d(icon_img, cx - icon_size/2, cy - icon_size/2 + 8, icon_size, icon_size)
        except Exception:
            pass
        if center_label:
            cy_label = cy - PIE_CONFIG['ICON_SIZE'] * 0.55
            draw_label(context, title=center_label, coords=(cx, cy_label), center=True, size=cfg['CENTER_TEXT_SIZE'], color=cfg['SIDE_LABEL_COLOR'])
            if center_sub:
                draw_label(context, title=center_sub, coords=(cx, cy_label - cfg['CENTER_TEXT_SIZE'] - 2), center=True, size=cfg['CENTER_SUBTEXT_SIZE'], color=cfg['CENTER_SUBTEXT_COLOR'])
        # Side label removed (center now owns label). If needed, re-add later.

    def invoke(self, context, event):
        area = context.area
        if not area or area.type != 'VIEW_3D':
            return {'CANCELLED'}
        self.center = (event.mouse_region_x, event.mouse_region_y)
        self.mouse = (event.mouse_region_x, event.mouse_region_y)
        # Base radius from config
        self.radius = PIE_CONFIG['RADIUS']
        self.index = 0
        self.angle = -pi/2
        # register a safe module-level draw handler to avoid keeping operator RNA alive
        op_id = str(id(self))
        try:
            # store weakref and handler in module dicts
            from . import menu as _menu_mod
        except Exception:
            _menu_mod = globals()
        # ensure module-level registries exist
        if not hasattr(_menu_mod, '_HUD_OPS'):
            _menu_mod._HUD_OPS = {}
            _menu_mod._HUD_HANDLERS = {}

        _menu_mod._HUD_OPS[op_id] = weakref.ref(self)
        handler = bpy.types.SpaceView3D.draw_handler_add(_menu_mod._hud_draw, (op_id,), 'WINDOW', 'POST_PIXEL')
        _menu_mod._HUD_HANDLERS[op_id] = handler
        self._hud_id = op_id
        self._handle = handler
        context.window_manager.modal_handler_add(self)
        try:
            area.tag_redraw()
        except Exception:
            pass
        # Precompute slice images and labels to avoid expensive lookup in the draw loop
        try:
            items = self._items(context)
            if not items:
                items = self._fallback_items()
            # store up to 8 items
            self._slice_items = list(items[:8])
            self._slice_images = []
            self._slice_labels = []
            # precompute radii and angles
            self._R_outer = self.radius
            self._R_inner = int(self.radius * PIE_CONFIG['INNER_RADIUS_FACTOR'])
            self._R_center = int(self._R_inner * PIE_CONFIG['CENTER_RADIUS_FACTOR'])
            n_local = max(1, len(self._slice_items))
            self._angles = [-pi/2 + i * (2*pi / n_local) for i in range(n_local)]
            for entry in self._slice_items:
                try:
                    label = entry[0] if len(entry) >= 1 else ''
                    op = entry[1] if len(entry) >= 2 else None
                    raw_props = entry[2] if len(entry) >= 3 else {}
                except Exception:
                    label = ''
                    op = None
                    raw_props = {}

                # allow explicit icon provided either as a string third-element or
                # as props dict with key 'icon'
                explicit_icon = None
                try:
                    if isinstance(raw_props, str):
                        explicit_icon = raw_props
                    elif isinstance(raw_props, dict):
                        explicit_icon = raw_props.get('icon')
                except Exception:
                    explicit_icon = None

                base_fn = op.replace('.', '_') if op else None
                func = op.split('.')[-1] if op else None
                label_base = label.lower().replace(' ', '_') if label else ''

                candidates = []
                if explicit_icon:
                    # accept with or without .png
                    try:
                        if explicit_icon.lower().endswith('.png'):
                            candidates.append(explicit_icon)
                        else:
                            candidates.append(f"{explicit_icon}.png")
                    except Exception:
                        pass

                # fallback candidates derived from label/op names
                candidates.extend([
                    f"{label_base}.png" if label_base else None,
                    f"{base_fn}.png" if base_fn else None,
                    f"{func}.png" if func else None,
                ])
                picked = None
                for fname in [c for c in candidates if c]:
                    img = _load_icon_image(fname)
                    if img:
                        picked = img
                        break
                if not picked:
                    picked = _load_icon_image('blender.png')
                self._slice_images.append(picked)
                self._slice_labels.append(label)
                # update slice_count so _angle_to_index and drawing use the same value
                try:
                    self._slice_count = len(self._slice_items)
                except Exception:
                    self._slice_count = None

            # Precompute dim-overlay tris for each slice to avoid recomputation during draw
            try:
                cx, cy = self.center
                R_inner = self._R_inner
                R_outer = self._R_outer
                n = max(1, len(self._slice_items))
                tris_list = []
                for i in range(n):
                    a0_i = -pi/2 + i * (2*pi / n)
                    a1_i = a0_i + (2*pi / n)
                    tris_i = self._sector_tris(cx, cy, R_inner + 1.0, R_outer - 1.0, a0_i + 0.01, a1_i - 0.01, steps=36)
                    tris_list.append(tris_i)
                self._slice_sector_tris = tris_list
            except Exception:
                self._slice_sector_tris = []
        except Exception:
            try:
                self._slice_images = []
                self._slice_labels = []
            except Exception:
                pass
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        # Cancel on ESC
        if event.type in {'ESC'}:
            try:
                from . import menu as _menu_mod
            except Exception:
                _menu_mod = globals()
            # remove handler and cleanup module registries
            hid = getattr(self, '_hud_id', None)
            if hid and hasattr(_menu_mod, '_HUD_HANDLERS'):
                h = _menu_mod._HUD_HANDLERS.pop(hid, None)
                if h:
                    bpy.types.SpaceView3D.draw_handler_remove(h, 'WINDOW')
            if hid and hasattr(_menu_mod, '_HUD_OPS'):
                _menu_mod._HUD_OPS.pop(hid, None)
            try:
                context.area.tag_redraw()
            except Exception:
                pass
            return {'CANCELLED'}

        if event.type == 'MOUSEMOVE':
            dx = event.mouse_region_x - self.center[0]
            dy = event.mouse_region_y - self.center[1]
            ang = math.atan2(dy, dx)
            self.index = self._angle_to_index(ang)
            self.angle = ang
            self.mouse = (event.mouse_region_x, event.mouse_region_y)
            try:
                context.area.tag_redraw()
            except Exception:
                pass
            return {'RUNNING_MODAL'}

        # Confirm selection on mouse release
        # Accept both LEFTMOUSE (common Blender selection) and RIGHTMOUSE (marking menu style)
        if ((event.type in {'LEFTMOUSE', 'RIGHTMOUSE'} and event.value == 'RELEASE')
            or (event.type in {'RET', 'SPACE'} and event.value == 'PRESS')):
            try:
                # check hover center to cancel
                cx, cy = self.center
                R_inner = int(self.radius * PIE_CONFIG['INNER_RADIUS_FACTOR'])
                R_center = int(R_inner * PIE_CONFIG['CENTER_RADIUS_FACTOR'])
                mx, my = getattr(self, 'mouse', self.center)
                dx, dy = mx - cx, my - cy
                hovering_center = (dx*dx + dy*dy) <= (R_center * R_center)

                # If clicked in center, treat as cancel regardless of button
                if not hovering_center:
                    # Use cached slice items to match what is drawn
                    items = getattr(self, '_slice_items', None) or self._items(context) or self._fallback_items()
                    if items and 0 <= self.index < len(items):
                        entry = items[self.index]
                        # block execution when disabled
                        try:
                            if not _is_item_enabled(context, entry):
                                raise RuntimeError("Selected slice disabled in current context")
                        except Exception:
                            pass
                        # (label, op) or (label, op, props_or_icon)
                        op = entry[1] if len(entry) >= 2 else None
                        raw3 = entry[2] if len(entry) >= 3 else None
                        # Only pass through dict props that aren't just icon metadata
                        props = {}
                        if isinstance(raw3, dict):
                            props = {k: v for k, v in raw3.items() if k not in {"icon", "enable_if"}}
                        if op:
                            mod, fn = op.split('.', 1)
                            if isinstance(props, dict) and props:
                                getattr(getattr(bpy.ops, mod), fn)(**props)
                            else:
                                getattr(getattr(bpy.ops, mod), fn)()
                # else hovering center: do nothing (cancel)
            except Exception as e:
                print("HUDPie error:", e)
            try:
                from . import menu as _menu_mod
            except Exception:
                _menu_mod = globals()
            hid = getattr(self, '_hud_id', None)
            if hid and hasattr(_menu_mod, '_HUD_HANDLERS'):
                h = _menu_mod._HUD_HANDLERS.pop(hid, None)
                if h:
                    bpy.types.SpaceView3D.draw_handler_remove(h, 'WINDOW')
            if hid and hasattr(_menu_mod, '_HUD_OPS'):
                _menu_mod._HUD_OPS.pop(hid, None)
            try:
                context.area.tag_redraw()
            except Exception:
                pass
            return {'FINISHED'}

        return {'RUNNING_MODAL'}
