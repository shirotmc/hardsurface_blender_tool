import bpy, traceback

from ..utility.mouse import mouse_warp
from ..utility.draw import draw_quad, draw_text, get_blf_text_dims
from ..utility.addon import get_prefs

from ..ui import controller

class TMC_OP_SelectObjectFromCurrentMirror(bpy.types.Operator):
    bl_idname = "tmc.select_object_from_current_mirror"
    bl_label = "Select Object From Current Mirror"
    bl_decription = "Select Object From Current Mirror"

    def execute(self, context):
        current_object = bpy.context.scene.objects.get(context.scene.current_mirror_object_name)
        if current_object:
            is_exists = True
        else:
            is_exists = False
        if is_exists or context.scene.current_mirror_object_name == '':
            mirror_object_list = []
            mesh_list = [obj for obj in bpy.context.scene.objects if obj.type=='MESH']
            for obj in mesh_list:
                bpy.context.view_layer.objects.active = obj
                for mod in obj.modifiers:
                    if mod.type == 'MIRROR':
                        if mod.mirror_object == None:
                            if context.scene.current_mirror_object_name == '':
                                mirror_object_list.append(obj)
                        else:
                            if mod.mirror_object.name == context.scene.current_mirror_object_name:
                                mirror_object_list.append(obj)
            if mirror_object_list == []:
                controller.show_message(context, "ERROR", "No object selected!")
            else:
                bpy.ops.object.mode_set(mode = 'OBJECT')
                for obj in mirror_object_list:
                    obj.select_set(True)
                controller.show_message(context, "INFO", "Select: Done!")
        else:
            controller.show_message(context, "ERROR", "Target Mirror isn't exists!")
        return {'FINISHED'}
    
class TMC_OP_SetCurrentMirrorToTargetMirror(bpy.types.Operator):
    bl_idname = "tmc.set_current_mirror_to_target_mirror"
    bl_label = "Set Current Mirror To Target Mirror"
    bl_description = "Set Current Mirror To Target Mirror"

    def execute(self, context):
        current_object = bpy.context.scene.objects.get(context.scene.current_mirror_object_name)
        if current_object:
            is_exists = True
        else:
            is_exists = False
        if is_exists or context.scene.current_mirror_object_name == '':
            mesh_list = [obj for obj in bpy.context.scene.objects if obj.type=='MESH']
            for obj in mesh_list:
                bpy.context.view_layer.objects.active = obj
                for mod in obj.modifiers:
                    if mod.type == 'MIRROR':
                        if mod.mirror_object != None:
                            if mod.mirror_object.name == context.scene.current_mirror_object_name:
                                if context.scene.target_mirror_object_name == '':
                                    mod.mirror_object = None
                                else:
                                    mod.mirror_object = bpy.data.objects[context.scene.target_mirror_object_name]
                        elif context.scene.current_mirror_object_name == '':
                            if context.scene.target_mirror_object_name == '':
                                    mod.mirror_object = None
                            else:
                                mod.mirror_object = bpy.data.objects[context.scene.target_mirror_object_name]
            empty_list = [obj for obj in bpy.context.scene.objects if obj.type=='EMPTY']
            for em in empty_list:
                if context.scene.current_mirror_object_name == em.name:
                    bpy.data.objects.remove(em, do_unlink=True)
            controller.show_message(context, "INFO", "Change: Done!")
        else:
            controller.show_message(context, "ERROR", "Target Mirror isn't exists!")
        return {'FINISHED'}