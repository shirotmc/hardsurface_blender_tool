# SimpleLattice (benjamin.sauder, Eugene Dudavkin) integrated into HardSurface Tool.
# Original: https://github.com/BenjaminSauder/SimpleLattice  (GPL-3.0-or-later)
import bpy
from bpy.props import FloatProperty
from bpy.types import PropertyGroup

from . import op_LatticeCreate
from . import op_LatticeApply
from . import op_LatticeRemove


def _active_lattice_data():
    obj = bpy.context.active_object
    if obj is not None and obj.type == 'LATTICE':
        return obj.data
    return None


def _make_uvw(attr):
    def getter(self):
        data = _active_lattice_data()
        return getattr(data, attr) if data else 2

    def setter(self, value):
        data = _active_lattice_data()
        if data:
            setattr(data, attr, value)
    return getter, setter


get_u, set_u = _make_uvw("points_u")
get_v, set_v = _make_uvw("points_v")
get_w, set_w = _make_uvw("points_w")


class MODIFIERSTRENGTH_PG_main(PropertyGroup):

    def update_modifierstrength(self, context):
        lattice = context.active_object
        for o in bpy.data.objects:
            for modifier in o.modifiers:
                if modifier.type == 'LATTICE' and "SimpleLattice" in modifier.name:
                    if modifier.object == lattice:
                        modifier.strength = self.str_obj

    str_obj: bpy.props.FloatProperty(
        description="Change strength for Lattice modifier in objects affected by lattice",
        name="Strength",
        min=0.0,
        max=1.0,
        step=1,
        default=1,
        update=update_modifierstrength
    )


class RESOLUTIONUVW_PG_main(PropertyGroup):

    change_u: bpy.props.IntProperty(min=2, max=20, get=get_u, set=set_u)
    change_v: bpy.props.IntProperty(min=2, max=20, get=get_v, set=set_v)
    change_w: bpy.props.IntProperty(min=2, max=20, get=get_w, set=set_w)


classes = [
    op_LatticeCreate.Op_LatticeCreateOperator,
    op_LatticeApply.Op_LatticeApplyOperator,
    op_LatticeRemove.Op_LatticeRemoveOperator,
    MODIFIERSTRENGTH_PG_main,
    RESOLUTIONUVW_PG_main,
]


def _lattice_is_simple_in_edit(context):
    obj = context.active_object
    return (obj is not None and obj.type == 'LATTICE'
            and "SimpleLattice" in obj.name and obj.mode == 'EDIT')


def draw_lattice_ops(layout, context):
    """Create / Apply / Remove entries (used by menus and the HS panel)."""
    show_apply_op = op_LatticeApply.Op_LatticeApplyOperator.poll(context)
    show_remove_op = op_LatticeRemove.Op_LatticeRemoveOperator.poll(context)
    show_create_op = op_LatticeCreate.Op_LatticeCreateOperator.poll(context)

    if show_apply_op:
        layout.operator("object.op_lattice_apply")
    if show_remove_op:
        layout.operator("object.op_lattice_remove")
    if show_create_op and not show_apply_op:
        layout.operator("object.op_lattice_create")


def draw_lattice_settings(layout, context):
    """Resolution + strength of the active SimpleLattice (edit mode)."""
    if not _lattice_is_simple_in_edit(context):
        return
    layout.label(text="Simple Lattice Resolution:")
    sub = layout.column(align=True)
    res = context.scene.RESOLUTIONUVW_PG_main
    sub.prop(res, "change_u", text="U")
    sub.prop(res, "change_v", text="V")
    sub.prop(res, "change_w", text="W")
    layout.prop(context.scene.MODIFIERSTRENGTH_PG_main, "str_obj", text="Strength")


def context_menu(self, context):
    layout = self.layout
    layout.separator()
    draw_lattice_ops(layout, context)
    layout.separator()
    if _lattice_is_simple_in_edit(context):
        draw_lattice_settings(layout, context)
        layout.separator()


def object_mesh_menu(self, context):
    layout = self.layout
    show = (op_LatticeApply.Op_LatticeApplyOperator.poll(context)
            or op_LatticeCreate.Op_LatticeCreateOperator.poll(context))
    if show:
        layout.separator()
    draw_lattice_ops(layout, context)


_prepend_menus = ("VIEW3D_MT_object_context_menu",
                  "VIEW3D_MT_edit_mesh_context_menu",
                  "VIEW3D_MT_edit_lattice_context_menu",
                  "VIEW3D_MT_edit_lattice")
_append_menus = ("VIEW3D_MT_edit_mesh", "VIEW3D_MT_object")


def _menus(names):
    return [getattr(bpy.types, n) for n in names if hasattr(bpy.types, n)]


def register_simple_lattice():
    for c in classes:
        bpy.utils.register_class(c)
    for menu in _menus(_prepend_menus):
        menu.prepend(context_menu)
    for menu in _menus(_append_menus):
        menu.append(object_mesh_menu)

    bpy.types.Scene.MODIFIERSTRENGTH_PG_main = bpy.props.PointerProperty(type=MODIFIERSTRENGTH_PG_main)
    bpy.types.Scene.RESOLUTIONUVW_PG_main = bpy.props.PointerProperty(type=RESOLUTIONUVW_PG_main)


def unregister_simple_lattice():
    for menu in _menus(_prepend_menus):
        try:
            menu.remove(context_menu)
        except Exception:
            pass
    for menu in _menus(_append_menus):
        try:
            menu.remove(object_mesh_menu)
        except Exception:
            pass
    for c in reversed(classes):
        try:
            bpy.utils.unregister_class(c)
        except Exception:
            pass
    for attr in ("MODIFIERSTRENGTH_PG_main", "RESOLUTIONUVW_PG_main"):
        try:
            delattr(bpy.types.Scene, attr)
        except Exception:
            pass
