import bpy

class TMC_MT_Main_Menu(bpy.types.Menu):
    bl_idname = "TMC_MT_Main_Menu"
    bl_label = "HardSurface Tool"

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
        
        # box = pie.box().column(align=True)
        # box.scale_x = 1.2
        # box.scale_y = 1.5
        # box.menu("TMC_MT_Modifier_Menu", text="Modifier", icon="MODIFIER")


        # layout.operator("tmc.bevel", text="Bevel", icon="MOD_BEVEL")
        # layout.operator("tmc.solidify", text="Solidify", icon="MOD_SOLIDIFY")
        # layout.operator("tmc.ray_caster", text="Ray Caster", icon="TRACKING_BACKWARDS_SINGLE")

# class TMC_MT_Modifier_Menu(bpy.types.Menu):
#     bl_idname = "TMC_MT_Modifier_Menu"
#     bl_label = "Modifier Menu"

#     def draw(self, context):
#         scene = context.scene
#         layout = self.layout
#         box = layout.column(align=True)
#         line = box.row(align=True)
#         line.scale_x = 1.2
#         line.scale_y = 1.5
#         line.operator("tmc.toggle_modifier", text="Toggle Modifier", icon="RESTRICT_VIEW_ON")
#         line = box.row(align=True)
#         line.scale_x = 1.2
#         line.scale_y = 1.5
#         line.operator("tmc.apply_modifier", text="Apply Modifier", icon="CHECKMARK")

# class TMC_MT_Material_Menu(bpy.types.Menu):
#     bl_idname = "TMC_MT_Material_Menu"
#     bl_label = "Material Menu"

#     def draw(self, context):
#         scene = context.scene
#         layout = self.layout
#         box = layout.column(align=True)
#         line = box.row(align=True)
#         line.scale_x = 1.2
#         line.scale_y = 1.5
#         line.operator("tmc.delete_duplicate_materials", text="Delete Duplicate Materials", icon="MATERIAL_DATA")
#         line = box.row(align=True)
#         line.scale_x = 1.2
#         line.scale_y = 1.5
#         line.operator("tmc.clean_material_slots", text="Clean Material Slots", icon="NODE_MATERIAL")
#         line = box.row(align=True)
#         line.scale_x = 1.2
#         line.scale_y = 1.5
#         line.operator("tmc.delete_all_materials", text="Delete All Materials", icon="CANCEL")