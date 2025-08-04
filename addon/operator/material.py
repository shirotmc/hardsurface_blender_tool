import os
import bpy
from ..ui import controller
from ..utility import variable

class TMC_OP_CleanMaterialSlots(bpy.types.Operator):
    bl_idname = "tmc.clean_material_slots"
    bl_label = "Clean Material Slots"
    bl_description = "Clean Material Slots"

    def execute(self, context):
        for obj in bpy.context.selected_objects:
            if obj.type == 'MESH':
                obj.data.materials.clear()
        # controller.show_message(context, "INFO", "Clean Material Slots: Done!")
        return {'FINISHED'}
    
class TMC_OP_DeleteAllMaterials(bpy.types.Operator):
    bl_idname = "tmc.delete_all_materials"
    bl_label = "Delete All Materials"
    bl_description = "Delete All Materials"

    def execute(self, context):
        for obj in context.scene.objects:
            if obj.type == 'MESH':
                obj.data.materials.clear()
        for material in bpy.data.materials:
            material.user_clear()
            bpy.data.materials.remove(material)
        # controller.show_message(context, "INFO", "Delete All Materials: Done!")
        return {'FINISHED'}
    
class TMC_OP_DeleteDuplicateMaterials(bpy.types.Operator):  
    bl_idname = "tmc.delete_duplicate_materials"
    bl_label = "Delete Duplicate Materials"
    bl_description = "Delete Duplicate Materials"

    def execute(self, context):
        mats = bpy.data.materials
        for mat in mats:
            (original, _, ext) = mat.name.rpartition(".")
            if ext.isnumeric() and mats.find(original) != -1:
                mat.user_remap(mats[original])
                mats.remove(mat)
        # controller.show_message(context, "INFO", "Delete Duplicate Materials: Done!")
        return {'FINISHED'}