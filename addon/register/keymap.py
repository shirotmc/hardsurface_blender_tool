import bpy

addon_keymaps = []

def register_keymaps():
    wm = bpy.context.window_manager
    # Use addon keyconfig when available; fall back to user keyconfig if not
    kc = wm.keyconfigs.addon or wm.keyconfigs.user
    if not kc:
        return

    # Keymap: 3D View -> Ctrl + Right Mouse opens the custom HUD circle menu (Maya-style)
    km = kc.keymaps.new(name='3D View', space_type='VIEW_3D')
    kmi = km.keymap_items.new('tmc.hud_pie', 'RIGHTMOUSE', 'PRESS', ctrl=True)
    addon_keymaps.append((km, kmi))

    # Keymap: Edit Mesh -> Backspace triggers context-aware auto delete
    km_mesh = kc.keymaps.new(name='Mesh', space_type='EMPTY', region_type='WINDOW')
    kmi_mesh = km_mesh.keymap_items.new('view3d.auto_delete', 'BACK_SPACE', 'PRESS')
    addon_keymaps.append((km_mesh, kmi_mesh))

    # Keymap: Edit Mesh -> Alt+R launches Edge Constraints
    kmi_edge = km_mesh.keymap_items.new('tmc.edge_constraints', 'R', 'PRESS', alt=True)
    addon_keymaps.append((km_mesh, kmi_edge))

    # ReBevel (Mesh) Alt+B
    kmi_rebevel_mesh = km_mesh.keymap_items.new('tmc.re_bevel', 'B', 'PRESS', alt=True)
    addon_keymaps.append((km_mesh, kmi_rebevel_mesh))

    # Curve keymaps
    km_curve = kc.keymaps.new(name='Curve', space_type='EMPTY', region_type='WINDOW')

    # Ctrl+B Bevel Curve
    kmi_curve_bevel = km_curve.keymap_items.new('tmc.curve_bevel', 'B', 'PRESS', ctrl=True)
    addon_keymaps.append((km_curve, kmi_curve_bevel))

    # Alt+B ReBevel Curve
    kmi_curve_rebevel = km_curve.keymap_items.new('tmc.curve_re_bevel', 'B', 'PRESS', alt=True)
    addon_keymaps.append((km_curve, kmi_curve_rebevel))


def unregister_keymaps():
    # Remove all keymap items we added
    try:
        for km, kmi in addon_keymaps:
            try:
                if kmi in km.keymap_items:
                    km.keymap_items.remove(kmi)
            except Exception:
                # Keymap might have been cleared or already removed
                pass
        addon_keymaps.clear()
    except Exception:
        # Be resilient during F8 reloads or partial teardown
        addon_keymaps.clear()