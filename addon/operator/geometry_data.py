import bpy

class TMC_OP_ClearCustomNormalsData(bpy.types.Operator):
    """Clear custom split normals data from selected mesh objects"""
    bl_idname = "tmc.clear_custom_normals_data"
    bl_label = "Clear Custom Normals Data"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.selected_objects is not None

    def execute(self, context):
        # Iterate through each selected object
        for obj in context.selected_objects:
            # Check if the object is a mesh and has custom split normals
            if obj.type == 'MESH' and obj.data.has_custom_normals:
                # Set the object as active in the scene context
                # This is necessary for some operators to function correctly
                bpy.context.view_layer.objects.active = obj
                
                # Clear the custom split normals data
                bpy.ops.mesh.customdata_custom_splitnormals_clear()
                print(f"Cleared custom split normals for: {obj.name}")
            elif obj.type == 'MESH':
                print(f"Object '{obj.name}' is a mesh but has no custom split normals to clear.")
            else:
                print(f"Object '{obj.name}' is not a mesh, skipping.")

        print("Custom split normal data clearing complete.")
        return {'FINISHED'}