import bpy

keys = []

def register_keymaps():

    wm = bpy.context.window_manager
    addon_keyconfig = wm.keyconfigs.addon
    kc = addon_keyconfig

    km = kc.keymaps.new(name="3D View", space_type="VIEW_3D")
    kmi = km.keymap_items.new("wm.call_menu_pie", "Q", "PRESS", shift=True)
    kmi.properties.name = "TMC_MT_Main_Menu"
    keys.append((km, kmi))
	
def unregister_keymaps():

    for km, kmi in keys:
        km.keymap_items.remove(kmi)

    keys.clear()