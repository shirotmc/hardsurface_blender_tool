import bpy


class FriendlyPivotPrefs(bpy.types.PropertyGroup):
    """Friendly Pivot (SCPO) preferences, stored inside the HardSurface Tool add-on preferences."""
    ################## UI VARIABLES #####################
    buttons =(("LEFTMOUSE", "LEFTMOUSE", "LEFTMOUSE"),
        ("MIDDLEMOUSE", "MIDDLEMOUSE", "MIDDLEMOUSE"),
        ("RIGHTMOUSE", "RIGHTMOUSE", "RIGHTMOUSE"),
    )

    keys = (("A", "A", "A"),
        ("B", "B", "B"),
        ("C", "C", "C"),
        ("D", "D", "D"),
        ("E", "E", "E"),
        ("F", "F", "F"),
        ("G", "G", "G"),
        ("H", "H", "H"),
        ("I", "I", "I"),
        ("J", "J", "J"),
        ("K", "K", "K"),
        ("L", "L", "L"),
        ("M", "M", "M"),
        ("N", "N", "N"),
        ("O", "O", "O"),
        ("P", "P", "P"),
        ("Q", "Q", "Q"),
        ("R", "R", "R"),
        ("S", "S", "S"),
        ("T", "T", "T"),
        ("U", "U", "U"),
        ("V", "V", "V"),
        ("W", "W", "W"),
        ("X", "X", "X"),
        ("Y", "Y", "Y"),
        ("Z", "Z", "Z"),
        ("ZERO", "ZERO", "ZERO"),
        ("ONE", "ONE", "ONE"),
        ("TWO", "TWO", "TWO"),
        ("THREE", "THREE", "THREE"),
        ("FOUR", "FOUR", "FOUR"),
        ("FIVE", "FIVE", "FIVE"),
        ("SIX", "SIX", "SIX"),
        ("SEVEN", "SEVEN", "SEVEN"),
        ("EIGHT", "EIGHT", "EIGHT"),
        ("NINE", "NINE", "NINE"),
        ("LEFT_CTRL", "LEFT_CTRL", "LEFT_CTRL"),
        ("LEFT_ALT", "LEFT_ALT", "LEFT_ALT"),
        ("LEFT_SHIFT", "LEFT_SHIFT", "LEFT_SHIFT"),
        ("RIGHT_ALT", "RIGHT_ALT", "RIGHT_ALT"),
        ("RIGHT_CTRL", "RIGHT_CTRL", "RIGHT_CTRL"),
        ("RIGHT_SHIFT", "RIGHT_SHIFT", "RIGHT_SHIFT"),
        ("OSKEY", "OSKEY", "OSKEY"),
        ("ESC", "ESC", "ESC"),
        ("TAB", "TAB", "TAB"),
        ("RET", "RET", "RET"),
        ("SPACE", "SPACE", "SPACE"),
        ("LINE_FEED", "LINE_FEED", "LINE_FEED"),
        ("BACK_SPACE", "BACK_SPACE", "BACK_SPACE"),
        ("DEL", "DEL", "DEL"),
        ("SEMI_COLON", "SEMI_COLON", "SEMI_COLON"),
        ("PERIOD", "PERIOD", "PERIOD"),
        ("COMMA", "COMMA", "COMMA"),
        ("QUOTE", "QUOTE", "QUOTE"),
        ("ACCENT_GRAVE", "ACCENT_GRAVE", "ACCENT_GRAVE"),
        ("MINUS", "MINUS", "MINUS"),
        ("PLUS", "PLUS", "PLUS"),
        ("SLASH", "SLASH", "SLASH"),
        ("BACK_SLASH", "BACK_SLASH", "BACK_SLASH"),
        ("EQUAL", "EQUAL", "EQUAL"),
        ("LEFT_BRACKET", "LEFT_BRACKET", "LEFT_BRACKET"),
        ("RIGHT_BRACKET", "RIGHT_BRACKET", "RIGHT_BRACKET"),
        ("LEFT_ARROW", "LEFT_ARROW", "LEFT_ARROW"),
        ("DOWN_ARROW", "DOWN_ARROW", "DOWN_ARROW"),
        ("RIGHT_ARROW", "RIGHT_ARROW", "RIGHT_ARROW"),
        ("UP_ARROW", "UP_ARROW", "UP_ARROW"),
        ("NUMPAD_2", "NUMPAD_2", "NUMPAD_2"),
        ("NUMPAD_4", "NUMPAD_4", "NUMPAD_4"),
        ("NUMPAD_6", "NUMPAD_6", "NUMPAD_6"),
        ("NUMPAD_8", "NUMPAD_8", "NUMPAD_8"),
        ("NUMPAD_1", "NUMPAD_1", "NUMPAD_1"),
        ("NUMPAD_3", "NUMPAD_3", "NUMPAD_3"),
        ("NUMPAD_5", "NUMPAD_5", "NUMPAD_5"),
        ("NUMPAD_7", "NUMPAD_7", "NUMPAD_7"),
        ("NUMPAD_9", "NUMPAD_9", "NUMPAD_9"),
        ("NUMPAD_PERIOD", "NUMPAD_PERIOD", "NUMPAD_PERIOD"),
        ("NUMPAD_SLASH", "NUMPAD_SLASH", "NUMPAD_SLASH"),
        ("NUMPAD_ASTERIX", "NUMPAD_ASTERIX", "NUMPAD_ASTERIX"),
        ("NUMPAD_0", "NUMPAD_0", "NUMPAD_0"),
        ("NUMPAD_MINUS", "NUMPAD_MINUS", "NUMPAD_MINUS"),
        ("NUMPAD_ENTER", "NUMPAD_ENTER", "NUMPAD_ENTER"),
        ("NUMPAD_PLUS", "NUMPAD_PLUS", "NUMPAD_PLUS"),
        ("F1", "F1", "F1"),
        ("F2", "F2", "F2"),
        ("F3", "F3", "F3"),
        ("F4", "F4", "F4"),
        ("F5", "F5", "F5"),
        ("F6", "F6", "F6"),
        ("F7", "F7", "F7"),
        ("F8", "F8", "F8"),
        ("F9", "F9", "F9"),
        ("F10", "F10", "F10"),
        ("F11", "F11", "F11"),
        ("F12", "F12", "F12"),
        ("PAUSE", "PAUSE", "PAUSE"),
        ("INSERT", "INSERT", "INSERT"),
        ("HOME", "HOME", "HOME"),
        ("PAGE_UP", "PAGE_UP", "PAGE_UP"),
        ("PAGE_DOWN", "PAGE_DOWN", "PAGE_DOWN"),
        ("END", "END", "END"),
        ("PAGE_DOWN", "PAGE_DOWN", "PAGE_DOWN"),
        )

    # Get current orientation keys
    orient_keys = ()
    for it in  bpy.types.TransformOrientationSlot.bl_rna.properties['type'].enum_items:
        orient_keys += ((it.identifier, it.identifier, it.identifier),)
    
    # Get current pivot center keys
    pivot_center_keys = ()
    for it in bpy.types.ToolSettings.bl_rna.properties['transform_pivot_point'].enum_items:
        pivot_center_keys += ((it.identifier, it.identifier, it.identifier),)

    highlight_vert_color : bpy.props.FloatVectorProperty(
        name="HighlightVertColor",
        description="Highlight vert color",
        default=(1.0, 0.5, 0.0, 0.75),
        min=0.0,
        max=1.0,
        size=4,
        subtype='COLOR'
    )

    highlight_edge_color : bpy.props.FloatVectorProperty(
        name="HighlightEdgeColor",
        description="Highlight edge color",
        default=(0.9, 0.9, 0.0, 0.75),
        min=0.0,
        max=1.0,
        size=4,
        subtype='COLOR'
    )

    highlight_face_color : bpy.props.FloatVectorProperty(
        name="HighlightFaceColor",
        description="Highlight face color",
        default=[0.5, 0.9, 0.0, 0.75],
        min=0.0,
        max=1.0,
        size=4,
        subtype='COLOR'
    )

    conform_color : bpy.props.FloatVectorProperty(
        name="ConformColor",
        description="Conform color",
        default=(0.0,1.0,1.0,1.0),
        min=0.0,
        max=1.0,
        size=4,
        subtype='COLOR'
    )

    curve_points_preview_color : bpy.props.FloatVectorProperty(
        name="curve_points_preview_color",
        description="Curve points preview color",
        default=(0.1, 0.6, 0.0, 0.4),
        min=0.0,
        max=1.0,
        size=4,
        subtype='COLOR'
    )

    highlight_vertex_size : bpy.props.FloatProperty(
        name="Highlight Vertex Size",
        description="Highlight vertex size",
        default=5.0,
        min=0.5,
        max=10.0)

    highlight_line_width : bpy.props.FloatProperty(
        name="Highlight Line Width",
        description="Highlight line width",
        default=2.5,
        min=0.5,
        max=10.0
    )

    highlight_lineface_width : bpy.props.FloatProperty(
        name="Highlight Face Lines Width",
        description="Highlight face lines width",
        default=2.5,
        min=0.5,
        max=10.0
    )

    preview_line_width : bpy.props.FloatProperty(
        name="Preview Line Width",
        description="Preview axis lines width",
        default=1.5,
        min=0.5,
        max=10.0
    )

    preview_size : bpy.props.FloatProperty(
        name="Preview Size",
        description="Preview axis size",
        default= 0.75,
        min=0.01,
        max=10.0
    )

    preview_curve_points_size : bpy.props.FloatProperty(
        name="Preview Curve Points Size",
        description="Preview curve points size in px",
        default=6.0,
        min=0.5,
        max=20.0)

    pivot_gizmo_scale : bpy.props.FloatProperty(
        name="Pivot Gizmo's Scale",
        description="Set Pivot gizmo size",
        default= 1,
        min=0.01,
        max=10
    )

    dots_scale : bpy.props.FloatProperty(
        name="Bbox Dots' Scale",
        description="Set Bbox gizmo size",
        default= 1,
        min=0.01,
        max=10
    )

    force_kdtree_meshes_shortcut : bpy.props.EnumProperty(
        items=keys,
        description = "(!!!IN DEVELOPMENT!!!)Force addon to treat verts and edges of active object(mesh) without faces",
        default='F'
    )

    force_kdtree_curves_shortcut : bpy.props.EnumProperty(
        items=keys,
        description = "Force raycast to get curves in scene",
        default='G'
    )

    force_kdtree_bones_shortcut : bpy.props.EnumProperty(
        items=keys,
        description = "Force raycast to get bones in scene",
        default='V'
    )

    force_origin_shortcut : bpy.props.EnumProperty(
        items=keys,
        description = "Set Origin or 3D Cursor position at the same time with Pivot Orientation",
        default='S'
    )

    force_cursor_shortcut : bpy.props.EnumProperty(
        items=keys,
        description = "This key emulates MMB (by default Set 3D Cursor) action for 2 button mouse",
        default='C'
    )

    autoset_cursor_shortcut : bpy.props.EnumProperty(
        items=keys,
        description = "Set pivot center to 3D Cursor and back",
        default='O'
    )
    
    autoset_orientAT_shortcut : bpy.props.EnumProperty(
        items=keys,
        description = "AutoSet Orientation to active tools",
        default='P'
    )

    orient_mode_shortcut : bpy.props.EnumProperty(
        items=buttons,
        description = "Set pivot orientation",
        default='LEFTMOUSE'
    )

    cursor_mode_shortcut : bpy.props.EnumProperty(
        items=buttons,
        description = "Set 3DCursor position",
        default='MIDDLEMOUSE'
    )

    origin_mode_shortcut : bpy.props.EnumProperty(
        items=buttons,
        description = "Set Origin position",
        default='RIGHTMOUSE'
    )

    x_axis_shortcut : bpy.props.EnumProperty(
        items=keys,
        description = "Set to world X axis",
        default='X'
    )

    y_axis_shortcut : bpy.props.EnumProperty(
        items=keys,
        description = "Set to world Y axis",
        default='Y'
    )

    z_axis_shortcut : bpy.props.EnumProperty(
        items=keys,
        description = "Set to world Z axis",
        default='Z'
    )

    multi_select_mode_shortcut : bpy.props.EnumProperty(
        items=keys,
        description = "Activate Multi Selection mode",
        default='A'
    )

    bbox_shortcut : bpy.props.EnumProperty(
        items=keys,
        description = "Activate Bbox Selection mode",
        default='B'
    )

    bake_to_local_shortcut : bpy.props.EnumProperty(
        items=keys,
        description = "Bake Orientation directly to LOCAL",
        default='L'
    )

    reset_scpo_shortcut : bpy.props.EnumProperty(
        items=keys,
        description = "Reset/Set Orientation and Pivot center",
        default='R'
    )

    reset_orient_default : bpy.props.EnumProperty(
        items=orient_keys,
        description = "Set default Orientation",
        default=orient_keys[0][0]
    )

    reset_pivot_center_default : bpy.props.EnumProperty(
        items=pivot_center_keys,
        description = "Set default Pivot center",
        default=pivot_center_keys[0][0]
    )

    set_bake_to_local : bpy.props.BoolProperty(
        name="Bake to Local On",
        description="Switch ON to bake orientation directly to LOCAL by default",
        default=False
    )

    set_to_3Dcursor : bpy.props.BoolProperty(
        name="Pivot to 3D Cursor On",
        description="If ON this default action moves Pivot Center to 3D Cursor when it's conformed",
        default=True
    )

    set_in_Activetool : bpy.props.BoolProperty(
        name="SCPO in Active Tools On",
        description="Set Pivot Orientation in Move/Rotate/Scale/Transform Active Tool to ON or OFF by default",
        default=False
    )

    restore_prefs : bpy.props.BoolProperty(
        name="Restore prefs from file",
        description="Restore preferences from file",
        default=True
    )

    use_world : bpy.props.BoolProperty(
        name="Bbox World Orient On",
        description="This setting makes available world orientation in Bbox mode",
        default=True
    )

    pivot_gizmo_on : bpy.props.BoolProperty(
        name="Pivot Gizmo On",
        description="This setting switch addon's axis gizmo on/off",
        default=True
    )

    is_edit_mode : bpy.props.BoolProperty(
        name="Edit Mode On",
        description="WARNING! Proper work is not guarantee with some modifiers! This setting remains Edit Mode active when addon is being invoked",
        default=False
    )

    extra_setting : bpy.props.BoolProperty(
        name="Extra Settings Expand",
        description="Expand extra settings",
        default=True
    )

    enable_preview : bpy.props.BoolProperty(
        name="Preview Enable",
        description="Enable axis preview",
        default=True
    )

    enable_curve_preview : bpy.props.BoolProperty(
        name="Preview Curve Enable",
        description="Enable curve points preview",
        default=True
    )



def draw_pivot_prefs(layout, self):
    '''Friendly Pivot: only settings that change how the tool behaves.'''
    col = layout.column(align=True)

    # Mouse buttons used while the tool is running
    row = col.row(align=True)
    row.prop(self, "orient_mode_shortcut", text="Orient")
    row.prop(self, "cursor_mode_shortcut", text="3D Cursor")
    row.prop(self, "origin_mode_shortcut", text="Origin")

    col.separator()
    col.label(text="Modifier keys:")
    row = col.row(align=True)
    row.prop(self, "x_axis_shortcut", text="X")
    row.prop(self, "y_axis_shortcut", text="Y")
    row.prop(self, "z_axis_shortcut", text="Z")
    row = col.row(align=True)
    row.prop(self, "multi_select_mode_shortcut", text="Multi Select")
    row.prop(self, "bbox_shortcut", text="Bbox")
    row = col.row(align=True)
    row.prop(self, "force_kdtree_meshes_shortcut", text="Force Mesh")
    row.prop(self, "force_kdtree_curves_shortcut", text="Curves")
    row.prop(self, "force_kdtree_bones_shortcut", text="Bones")
    row = col.row(align=True)
    row.prop(self, "force_origin_shortcut", text="Combo")
    row.prop(self, "force_cursor_shortcut", text="Force Cursor")
    row = col.row(align=True)
    row.prop(self, "bake_to_local_shortcut", text="Bake Local")
    row.prop(self, "autoset_cursor_shortcut", text="Pivot->Cursor")
    row.prop(self, "autoset_orientAT_shortcut", text="Active Tools")
    row = col.row(align=True)
    row.prop(self, "reset_scpo_shortcut", text="Reset")
    row.prop(self, "reset_orient_default", text="")
    row.prop(self, "reset_pivot_center_default", text="")

    col.separator()
    col.label(text="Defaults:")
    row = col.row()
    row.prop(self, "set_bake_to_local", toggle=0)
    row.prop(self, "set_to_3Dcursor", toggle=0)
    row = col.row()
    row.prop(self, "set_in_Activetool", toggle=0)
    row.prop(self, "pivot_gizmo_on", toggle=0)
    row = col.row()
    row.prop(self, "is_edit_mode", toggle=0)
    row.prop(self, "use_world", toggle=0)
