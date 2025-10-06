import bpy

addon_keymaps = []

def register_keymaps():
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if not kc:
        return

    # Keymap: 3D View -> Shift+Q opens the TMC pie menu
    km = kc.keymaps.new(name='3D View', space_type='VIEW_3D')
    kmi = km.keymap_items.new('wm.call_menu_pie', 'Q', 'PRESS', shift=True)
    kmi.properties.name = 'TMC_MT_Main_Menu'
    addon_keymaps.append((km, kmi))

    # Keymap: Edit Mesh -> Backspace triggers context-aware auto delete
    km_mesh = kc.keymaps.new(name='Mesh', space_type='EMPTY', region_type='WINDOW')
    kmi_mesh = km_mesh.keymap_items.new('view3d.auto_delete', 'BACK_SPACE', 'PRESS')
    addon_keymaps.append((km_mesh, kmi_mesh))

    # Keymap: Edit Mesh -> Alt+R launches Edge Constraints
    kmi_edge = km_mesh.keymap_items.new('tmc.edge_constraints', 'R', 'PRESS', alt=True)
    addon_keymaps.append((km_mesh, kmi_edge))