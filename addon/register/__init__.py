

def register_addon():

    # Properties
    from ..property import register_properties
    register_properties()

    # Menus
    from ..ui import register_menus
    register_menus()

    # Operators
    from ..operator import register_operators
    register_operators()

    # Keymaps
    from .keymap import register_keymaps
    register_keymaps()

def unregister_addon():

    # Properties
    from ..property import unregister_properties
    unregister_properties()

    # Menus
    from ..ui import unregister_menus
    unregister_menus()

    # Operators
    from ..operator import unregister_operators
    unregister_operators()

    # Keymaps
    from .keymap import unregister_keymaps
    unregister_keymaps()
    