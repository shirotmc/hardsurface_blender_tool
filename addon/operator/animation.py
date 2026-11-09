import bpy


class TMC_OP_ClearDrivers(bpy.types.Operator):
    bl_idname = "tmc.clear_drivers"
    bl_label = "Clear Drivers"
    bl_description = "Remove all drivers (object, mesh data and shape keys) from selected objects"

    @classmethod
    def poll(cls, context):
        return len(context.selected_objects) > 0

    def execute(self, context):
        removed = 0
        for obj in context.selected_objects:
            targets = [obj]
            if obj.data is not None:
                targets.append(obj.data)
                shape_keys = getattr(obj.data, "shape_keys", None)
                if shape_keys is not None:
                    targets.append(shape_keys)
            for target in targets:
                anim = target.animation_data
                if anim is None:
                    continue
                for fcurve in list(anim.drivers):
                    anim.drivers.remove(fcurve)
                    removed += 1
        self.report({'INFO'}, f"Removed {removed} driver(s)")
        return {'FINISHED'}
