import os
import bpy
import bmesh
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
        # iterate over a copy since we'll be removing materials
        for mat in list(mats):
            (original, _, ext) = mat.name.rpartition(".")
            if ext.isnumeric() and mats.find(original) != -1:
                mat.user_remap(mats[original])
                try:
                    mats.remove(mat)
                except Exception:
                    # ignore removal errors
                    pass

        # After remapping/removing duplicates, ensure each object's material slots
        # do not contain repeated references to the same material. If duplicates
        # exist, collapse them to a single slot and remap polygon material indices.
        for obj in list(bpy.data.objects):
            if obj.type != 'MESH':
                continue
            mesh = obj.data
            try:
                old_slots = list(mesh.materials)
                if not old_slots:
                    continue
                unique_slots = []
                index_map = {}
                for i, m in enumerate(old_slots):
                    if m in unique_slots:
                        index_map[i] = unique_slots.index(m)
                    else:
                        index_map[i] = len(unique_slots)
                        unique_slots.append(m)

                # If slots were already unique, nothing to do
                if len(unique_slots) == len(old_slots):
                    continue

                # Rebuild material slots to only the unique list
                try:
                    mesh.materials.clear()
                except Exception:
                    # older Blender versions may not support clear(); fallback
                    try:
                        for i in range(len(mesh.materials)-1, -1, -1):
                            mesh.materials.pop(i)
                    except Exception:
                        pass
                for m in unique_slots:
                    try:
                        mesh.materials.append(m)
                    except Exception:
                        pass

                # Remap polygon material indices from old -> new
                try:
                    for p in mesh.polygons:
                        old_index = p.material_index
                        p.material_index = index_map.get(old_index, old_index)
                    mesh.update()
                except Exception:
                    pass
            except Exception:
                pass
        # controller.show_message(context, "INFO", "Delete Duplicate Materials: Done!")
        return {'FINISHED'}

class TMC_OP_ClearMaterialSearch(bpy.types.Operator):
    bl_idname = "tmc.clear_material_search"
    bl_label = "Reset Material Search"
    bl_description = "Reset material search filter (show all materials)"

    def execute(self, context):
        context.scene.material_search = ""
        # Force a UI redraw so the filtered list refreshes immediately
        try:
            for area in context.screen.areas:
                try:
                    area.tag_redraw()
                except Exception:
                    pass
        except Exception:
            try:
                context.area.tag_redraw()
            except Exception:
                pass

        return {'FINISHED'}


class TMC_OP_SelectMaterial(bpy.types.Operator):
    bl_idname = "tmc.select_material"
    bl_label = "Select Material"
    bl_description = "Select a material in the UI list"

    index = bpy.props.IntProperty()

    def execute(self, context):
        try:
            context.scene.material_index = int(self.index)
        except Exception:
            context.scene.material_index = 0
        return {'FINISHED'}


class TMC_OP_AddMaterial(bpy.types.Operator):
    bl_idname = "tmc.add_material"
    bl_label = "Add Material"
    bl_description = "Create a new material"

    def execute(self, context):
        # Create a new material with a unique name
        base = "Material"
        name = base
        i = 1
        mats = bpy.data.materials
        while name in mats:
            i += 1
            name = f"{base}.{i}"
        mat = bpy.data.materials.new(name=name)
        # Apply scene color to the new material (try Principled BSDF if nodes are used)
        try:
            col = tuple(getattr(context.scene, 'material_add_color', (0.8, 0.8, 0.8)))
            # ensure nodes are enabled for the material so we can set principled color
            try:
                if not getattr(mat, 'use_nodes', False):
                    mat.use_nodes = True
            except Exception:
                pass
            try:
                if getattr(mat, 'use_nodes', False) and mat.node_tree:
                    nodes = mat.node_tree.nodes
                    bsdf = None
                    for n in nodes:
                        if getattr(n, 'type', '') == 'BSDF_PRINCIPLED' or n.name.lower().find('principled') != -1:
                            bsdf = n
                            break
                    if bsdf is None:
                        # create a principled node and connect to output
                        try:
                            bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
                            output = None
                            for n in nodes:
                                if getattr(n, 'type', '') == 'OUTPUT_MATERIAL':
                                    output = n
                                    break
                            if output is not None:
                                try:
                                    mat.node_tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
                                except Exception:
                                    pass
                        except Exception:
                            bsdf = None
                    if bsdf is not None and 'Base Color' in bsdf.inputs:
                        bsdf.inputs['Base Color'].default_value = (col[0], col[1], col[2], 1.0)
                    else:
                        # fallback to diffuse_color
                        if hasattr(mat, 'diffuse_color'):
                            if len(mat.diffuse_color) == 4:
                                mat.diffuse_color = (col[0], col[1], col[2], mat.diffuse_color[3])
                            else:
                                mat.diffuse_color = (col[0], col[1], col[2])
            except Exception:
                # Fallback to diffuse_color if nodes fail
                try:
                    if hasattr(mat, 'diffuse_color'):
                        if len(mat.diffuse_color) == 4:
                            mat.diffuse_color = (col[0], col[1], col[2], mat.diffuse_color[3])
                        else:
                            mat.diffuse_color = (col[0], col[1], col[2])
                except Exception:
                    pass
        except Exception:
            pass
        # Select the new material in the UI
        try:
            context.scene.material_index = list(bpy.data.materials).index(mat)
        except Exception:
            context.scene.material_index = 0
        # Add to stored rows if collection exists
        try:
            scene = context.scene
            if hasattr(scene, 'tmc_material_rows'):
                item = scene.tmc_material_rows.add()
                item.material = mat
                item.visible = True
                scene.tmc_material_rows_index = len(scene.tmc_material_rows) - 1
        except Exception:
            pass
        return {'FINISHED'}


class TMC_OP_DuplicateMaterial(bpy.types.Operator):
    bl_idname = "tmc.duplicate_material"
    bl_label = "Duplicate Material"
    bl_description = "Duplicate the selected material"

    def execute(self, context):
        idx = getattr(context.scene, 'material_index', 0)
        mats = bpy.data.materials
        if idx < 0 or idx >= len(mats):
            return {'CANCELLED'}
        src = mats[idx]
        try:
            new = src.copy()
            # give unique name
            base = src.name
            name = base
            i = 1
            while name in mats:
                i += 1
                name = f"{base}.{i}"
            new.name = name
            context.scene.material_index = list(mats).index(new)
            # Add duplicated material to stored rows
            try:
                scene = context.scene
                if hasattr(scene, 'tmc_material_rows'):
                    item = scene.tmc_material_rows.add()
                    item.material = new
                    item.visible = True
                    scene.tmc_material_rows_index = len(scene.tmc_material_rows) - 1
            except Exception:
                pass
        except Exception:
            return {'CANCELLED'}
        return {'FINISHED'}


class TMC_OP_RemoveMaterial(bpy.types.Operator):
    bl_idname = "tmc.remove_material"
    bl_label = "Remove Material"
    bl_description = "Remove the selected material from the file (user_clear first)"

    def execute(self, context):
        idx = getattr(context.scene, 'material_index', 0)
        mats = bpy.data.materials
        if idx < 0 or idx >= len(mats):
            return {'CANCELLED'}
        mat = mats[idx]
        try:
            # Remove matching rows first
            try:
                scene = context.scene
                if hasattr(scene, 'tmc_material_rows'):
                    # remove all rows that reference this material
                    to_remove = [i for i, r in enumerate(scene.tmc_material_rows) if getattr(r, 'material', None) == mat]
                    for i in reversed(to_remove):
                        scene.tmc_material_rows.remove(i)
                    # clamp stored index
                    scene.tmc_material_rows_index = max(0, min(getattr(scene, 'tmc_material_rows_index', 0), max(0, len(scene.tmc_material_rows)-1)))
            except Exception:
                pass
            mat.user_clear()
            bpy.data.materials.remove(mat)
            # clamp index for data materials
            context.scene.material_index = max(0, min(idx, max(0, len(bpy.data.materials)-1)))
        except Exception:
            return {'CANCELLED'}
        return {'FINISHED'}


class TMC_OP_SyncMaterialRows(bpy.types.Operator):
    bl_idname = "tmc.sync_material_rows"
    bl_label = "Sync Material Rows"
    bl_description = "Populate saved material rows from bpy.data.materials"

    def execute(self, context):
        scene = context.scene
        # Clear existing collection
        scene.tmc_material_rows.clear()
        for mat in bpy.data.materials:
            item = scene.tmc_material_rows.add()
            item.material = mat
            item.visible = True
        scene.tmc_material_rows_index = 0
        return {'FINISHED'}


class TMC_OP_SelectObjectsByMaterial(bpy.types.Operator):
    """Select all objects that use the active material in the list"""
    bl_idname = "tmc.select_objects_by_material"
    bl_label = "Select Objects by Material"
    bl_description = "Select all objects that use the active material"

    def execute(self, context):
        idx = getattr(context.scene, 'material_index', 0)
        mats = bpy.data.materials
        if idx < 0 or idx >= len(mats):
            return {'CANCELLED'}
        mat = mats[idx]
        scene = context.scene
        # Remember current mode so we can restore it
        prev_mode = None
        try:
            prev_mode = context.mode
        except Exception:
            try:
                prev_mode = bpy.context.mode
            except Exception:
                prev_mode = None

        # If we're in Edit Mode, switch to Object Mode to safely change object selections and edit meshes
        if prev_mode and prev_mode.startswith('EDIT'):
            try:
                bpy.ops.object.mode_set(mode='OBJECT')
            except Exception:
                pass

        # Deselect everything first
        bpy.ops.object.select_all(action='DESELECT')

        last_obj_with_faces = None

        for obj in list(scene.objects):
            if obj.type != 'MESH':
                continue
            # find material slot index(es) that reference the material
            slot_indices = [i for i, m in enumerate(obj.data.materials) if m == mat]
            if not slot_indices:
                continue

            # mark that this object will be selected
            try:
                obj.select_set(True)
            except Exception:
                pass

            # ensure object is in object mode so we can update mesh via bmesh
            prev_active = context.view_layer.objects.active
            try:
                context.view_layer.objects.active = obj
            except Exception:
                pass

            # Use bmesh to set face selection by material index
            try:
                mesh = obj.data
                bm = bmesh.new()
                bm.from_mesh(mesh)
                bm.faces.ensure_lookup_table()
                any_selected = False
                for f in bm.faces:
                    if f.material_index in slot_indices:
                        f.select = True
                        any_selected = True
                    else:
                        f.select = False
                if any_selected:
                    last_obj_with_faces = obj
                bm.to_mesh(mesh)
                mesh.update()
                bm.free()
            except Exception:
                try:
                    bm.free()
                except Exception:
                    pass

        # If we found at least one object with selected faces, make the last one active and enter Edit mode
        try:
            if last_obj_with_faces is not None:
                context.view_layer.objects.active = last_obj_with_faces
                # enter edit mode to show face selection for the active object
                try:
                    bpy.ops.object.mode_set(mode='EDIT')
                except Exception:
                    pass
                # ensure face select mode
                try:
                    bpy.ops.mesh.select_mode(type='FACE')
                except Exception:
                    pass
            else:
                # If no faces found, at least keep any objects that use the material selected and stay in Object mode
                try:
                    bpy.ops.object.mode_set(mode='OBJECT')
                except Exception:
                    pass
        except Exception:
            pass

        # Restore previous mode if different
        try:
            if prev_mode and prev_mode.startswith('EDIT') and prev_mode != context.mode:
                # We already entered EDIT on last_obj_with_faces; if prev_mode was EDIT_MESH and we ended in OBJECT, try to restore
                try:
                    bpy.ops.object.mode_set(mode=prev_mode.split('_', 1)[1])
                except Exception:
                    # fallback to EDIT
                    try:
                        bpy.ops.object.mode_set(mode='EDIT')
                    except Exception:
                        pass
        except Exception:
            pass

        return {'FINISHED'}


class TMC_OP_AssignMaterialToSelection(bpy.types.Operator):
    """Assign active material from the list to selected objects or selected faces"""
    bl_idname = "tmc.assign_material_to_selection"
    bl_label = "Assign Material"
    bl_description = "Assign the selected material to current selected objects or faces"

    def execute(self, context):
        idx = getattr(context.scene, 'material_index', 0)
        mats = bpy.data.materials
        if idx < 0 or idx >= len(mats):
            return {'CANCELLED'}
        mat = mats[idx]

        # If in edit mode on a mesh, assign material slot to selected faces
        mode = getattr(context, 'mode', None)
        if mode and str(mode).upper().startswith('EDIT'):
            active_obj = context.active_object
            if active_obj and active_obj.type == 'MESH':
                # Ensure material exists in object's material slots
                mesh = active_obj.data
                try:
                    # find or add the material slot index
                    slot_index = None
                    for i, m in enumerate(mesh.materials):
                        if m == mat:
                            slot_index = i
                            break
                    if slot_index is None:
                        mesh.materials.append(mat)
                        slot_index = len(mesh.materials) - 1

                    # Use bmesh from edit mesh to assign material indices to selected faces
                    bm = bmesh.from_edit_mesh(mesh)
                    bm.faces.ensure_lookup_table()
                    any_assigned = False
                    for f in bm.faces:
                        if f.select:
                            f.material_index = slot_index
                            any_assigned = True
                    if any_assigned:
                        bmesh.update_edit_mesh(mesh, loop_triangles=False)
                except Exception:
                    try:
                        bmesh.update_edit_mesh(mesh, loop_triangles=False)
                    except Exception:
                        pass
                return {'FINISHED'}

        # Otherwise, assign material to selected objects (object-level)
        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue
            try:
                mesh = obj.data
                # Replace object's material slots so it has only the selected material
                try:
                    mesh.materials.clear()
                except Exception:
                    # Fallback: remove by index if clear not available
                    try:
                        for i in range(len(mesh.materials)-1, -1, -1):
                            mesh.materials.pop(i)
                    except Exception:
                        pass

                try:
                    mesh.materials.append(mat)
                except Exception:
                    # if append fails, try assigning first slot
                    try:
                        if len(mesh.materials) > 0:
                            mesh.materials[0] = mat
                    except Exception:
                        pass

                # Set all polygons to use the single slot (index 0)
                try:
                    for p in mesh.polygons:
                        p.material_index = 0
                    mesh.update()
                except Exception:
                    pass
            except Exception:
                pass

        return {'FINISHED'}