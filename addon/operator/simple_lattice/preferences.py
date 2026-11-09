import bpy


class LatticePrefs(bpy.types.PropertyGroup):
    """SimpleLattice defaults, stored inside the HardSurface Tool add-on preferences."""

    orientation_types = (('GLOBAL', 'Global', ''),
                         ('LOCAL', 'Local', ''),
                         ('CURSOR', 'Cursor', ''),
                         ('NORMAL', 'Normal', ''))

    interpolation_types = (('KEY_LINEAR', 'Linear', ''),
                           ('KEY_CARDINAL', 'Cardinal', ''),
                           ('KEY_CATMULL_ROM', 'Catmull-Rom', ''),
                           ('KEY_BSPLINE', 'BSpline', ''))

    default_orientation: bpy.props.EnumProperty(
        name="Default Orientation", items=orientation_types, default='GLOBAL')

    default_ignore_mods: bpy.props.BoolProperty(
        name="Ignore Modifiers", default=False,
        description="Ignore Modifiers for calculation BBOX for lattice")

    default_resolution_u: bpy.props.IntProperty(default=2, min=2)
    default_resolution_v: bpy.props.IntProperty(default=2, min=2)
    default_resolution_w: bpy.props.IntProperty(default=2, min=2)

    default_interpolation: bpy.props.EnumProperty(
        name="Default Interpolation", items=interpolation_types, default='KEY_LINEAR')

    default_scale: bpy.props.FloatProperty(
        name="Scale", default=1.0, min=0.001, soft_min=0.1, soft_max=2.0)


def draw_lattice_prefs(layout, prefs):
    col = layout.column(align=True)
    col.prop(prefs, "default_orientation", text="Orientation")
    col.prop(prefs, "default_interpolation", text="Interpolation")
    col.prop(prefs, "default_scale", text="Scale")
    row = col.row(align=True)
    row.prop(prefs, "default_resolution_u", text="U")
    row.prop(prefs, "default_resolution_v", text="V")
    row.prop(prefs, "default_resolution_w", text="W")
    col.prop(prefs, "default_ignore_mods")
