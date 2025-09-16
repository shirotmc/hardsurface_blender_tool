import bpy
import bmesh


def _get_selected_material_from_active_mesh(context):
    try:
        mode = getattr(context, 'mode', None)
        if not (mode and str(mode).upper().startswith('EDIT')):
            return None
        active_obj = context.active_object
        if not active_obj or active_obj.type != 'MESH':
            return None
        try:
            bm = bmesh.from_edit_mesh(active_obj.data)
            for f in bm.faces:
                if f.select:
                    mi = f.material_index
                    if 0 <= mi < len(active_obj.data.materials):
                        m = active_obj.data.materials[mi]
                        if m:
                            return m
        except Exception:
            for p in active_obj.data.polygons:
                if p.select:
                    mi = p.material_index
                    if 0 <= mi < len(active_obj.data.materials):
                        m = active_obj.data.materials[mi]
                        if m:
                            return m
    except Exception:
        return None
    return None


def depsgraph_handler(depsgraph):
    try:
        ctx = bpy.context
        mat = _get_selected_material_from_active_mesh(ctx)
        if mat is None:
            return
        mats_list = list(bpy.data.materials)
        if mat in mats_list:
            new_idx = mats_list.index(mat)
            last = getattr(ctx.scene, '_tmc_last_material_idx', None)
            if last == new_idx:
                return
            if getattr(ctx.scene, 'material_index', None) != new_idx:
                try:
                    ctx.scene.material_index = new_idx
                    try:
                        ctx.scene['_tmc_last_material_idx'] = new_idx
                    except Exception:
                        pass
                    # Force a UI redraw so the material list highlight updates
                    try:
                        for screen in bpy.data.screens:
                            for area in screen.areas:
                                try:
                                    area.tag_redraw()
                                except Exception:
                                    pass
                    except Exception:
                        pass
                except Exception:
                    pass
    except Exception:
        pass


def register():
    handlers = bpy.app.handlers.depsgraph_update_post
    if depsgraph_handler not in handlers:
        handlers.append(depsgraph_handler)


def unregister():
    handlers = bpy.app.handlers.depsgraph_update_post
    if depsgraph_handler in handlers:
        handlers.remove(depsgraph_handler)
