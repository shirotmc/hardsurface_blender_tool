import bpy

class TMC_MT_Main_Menu(bpy.types.Menu):
    bl_idname = "TMC_MT_Main_Menu"
    bl_label = "HS - Menu Pie"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()

        # Modifier
        box = pie.column(align=True)
        line = box.row(align=True)
        line.scale_x = 1.2
        line.scale_y = 1.5
        line.operator("tmc.toggle_modifier", text="Modifier: Toggle", icon="RESTRICT_VIEW_ON")
        line = box.row(align=True)
        line.scale_x = 1.2
        line.scale_y = 1.5
        line.operator("tmc.apply_modifier", text="Modifier: Apply", icon="CHECKMARK")

        # Boolean
        box = pie.column(align=True)
        line = box.row(align=True)
        line.scale_x = 1.2
        line.scale_y = 1.5
        line.operator("tmc.boolean", text="Boolean", icon="MOD_BOOLEAN")
    