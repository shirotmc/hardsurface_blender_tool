# Auto Highlight in Outliner (Amandeep) integrated into HardSurface Tool.
# Selected objects in the 3D viewport are automatically revealed in the Outliner.
# Original licence: GPL-3.0-or-later.
import functools
import time

import bpy

from ..utility.addon import get_prefs


def preferences():
    return get_prefs().highlight


def draw_highlight_prefs(layout, prefs, context):
    col = layout.column(align=True)
    col.prop(prefs, 'default_state')
    col.prop(prefs, 'expand_all_selected')
    col.prop(prefs, 'max_objects_to_expand')
    col.prop(prefs, 'show_actual_object_for_parented_objects')
    col.prop(prefs, 'expand_bones')
    col.prop(prefs, 'collapse_fix')


class HighlightPrefs(bpy.types.PropertyGroup):
    expand_all_selected: bpy.props.BoolProperty(default=True, name="Keep all selected objects expanded when using 'Collapse other collections'", description='Enabling this option will expand all selected objects in the outliner. Disabling it will only expand the active object.')
    expand_bones: bpy.props.BoolProperty(default=False, name='Expand to show selected bones in Pose mode')
    ex: bpy.props.BoolProperty(name='Experimental', default=False)
    show_actual_object_for_parented_objects: bpy.props.BoolProperty(default=False, name='Show actual object for parented objects', description='When disabled, the addon will expand to show the grayed out version of children objects (the ones shown under the parent object) instead of the actual object, which may be located in another collection. Enabling this option will display the actual object from the other collection instead.')
    default_state: bpy.props.BoolProperty(default=True, name='Enable by default in all new scenes', description='This option allows you to set the starting state for new scenes. When enabled, auto highlight will be turned on by default for every new Blender scene you open.')
    collapse_fix: bpy.props.BoolProperty(default=False, name="Enable if performance is slow when using 'Collapse other collections'")
    max_objects_to_expand: bpy.props.IntProperty(default=10, min=1, max=999999, name="Objects limit")


new_selection = []
prev_selection = []
prev_collections = set()
new_collections = set()
def enable_filter_children(area,filter_children,filter_content):
    area.spaces.active.use_filter_children=filter_children
    area.spaces.active.use_filter_object_content=filter_content
    return None
def show_active_again(active,override):
    if bpy.context.mode=='OBJECT':
        if True or not(active and active.parent and set(active.parent.users_collection)==set(active.users_collection)):
            if bpy.context.view_layer.objects.active!=active:
                bpy.context.view_layer.objects.active=active
            with bpy.context.temp_override(**override):
                bpy.ops.outliner.show_active()
        bpy.context.view_layer.objects.active=active
def collapse_outliner(override):
    if not preferences().collapse_fix:
        for i in range(15):
            with bpy.context.temp_override(**override):
                bpy.ops.outliner.show_one_level(open=False)
    else:
        with bpy.context.temp_override(**override):
            bpy.ops.outliner.expanded_toggle()
            bpy.ops.outliner.expanded_toggle()
def show_active(active_bone, active, override,area,filter_children,filter_content):

    
    if preferences().expand_all_selected:
        count=1
        if bpy.context.mode=='OBJECT':
            for a in bpy.context.selected_objects:
                count+=1
                if a!=active and not(a.parent and set(a.parent.users_collection)==set(a.users_collection)):
                    bpy.context.view_layer.objects.active=a
                    with bpy.context.temp_override(**override):
                        bpy.ops.outliner.show_active()
                if count>preferences().max_objects_to_expand:
                    break
        if preferences().expand_bones:
            if bpy.context.mode=='POSE':
                for a in bpy.context.selected_pose_bones:
                    if a!=active_bone and active:
                        bpy.context.view_layer.objects.active=a.id_data
                        a.id_data.data.bones.active=a.bone
                        with bpy.context.temp_override(**override):
                            bpy.ops.outliner.show_active()
    expanded_active=False
    if bpy.context.mode=='OBJECT':
        if active.parent and set(active.parent.users_collection)!=set(active.users_collection):
            expanded_active=True
            if bpy.context.view_layer.objects.active!=active:
                bpy.context.view_layer.objects.active=active
            with bpy.context.temp_override(**override):
                bpy.ops.outliner.show_active()
        bpy.context.view_layer.objects.active=active
    if preferences().expand_bones:
        if bpy.context.mode=='POSE' and active and active_bone:
            bpy.context.view_layer.objects.active=active_bone.id_data
            active_bone.id_data.data.bones.active=active_bone.bone
            with bpy.context.temp_override(**override):
                bpy.ops.outliner.show_active()
    
    area.spaces.active.use_filter_children=filter_children
    area.spaces.active.use_filter_object_content=filter_content
    if not expanded_active:
        bpy.app.timers.register(functools.partial(show_active_again, active, override),first_interval=0.01)
    return None
import functools
import time
def highlight_in_outliner():
    st=time.time()
    if bpy.context.scene.auto_highlight_in_outliner and not bpy.context.scene.auto_highlight_temp_disable:
        global new_selection,prev_selection,prev_collections,new_collections
        new_selection=set(bpy.context.selected_objects[:])
        has_parent=any([a.parent!=None for a in new_selection])
        new_selection=set([a.name for a in new_selection])
        
        active_bone=None
        if bpy.context.mode=='POSE':
            new_selection.update([a.name for a in bpy.context.selected_pose_bones])
            active_bone=bpy.context.active_pose_bone if bpy.context.active_pose_bone in bpy.context.selected_pose_bones else None
        active=bpy.context.active_object
        if bpy.context.selected_objects and active not in bpy.context.selected_objects:
            active=bpy.context.selected_objects[0]
        if new_selection!=prev_selection:
            # new_collection_set=False
            prev_selection=new_selection
            # if prev_collections!=new_collections :
            #     prev_collections=new_collections
            #     new_collection_set=True
            override = None
            for win in bpy.context.window_manager.windows:
            
                for area in win.screen.areas:
                    if 'OUTLINER' in area.type:
                        if area.spaces and area.spaces.active and area.spaces.active.display_mode in ['VIEW_LAYER','SCENES','LIBRARIES']:
                            for region in area.regions:
                                if 'WINDOW' in region.type:
                                    override = {'window':win,'area': area, 'region': region}

                                    if bpy.context.scene.collapse_other_collections and bpy.context.selected_objects[:]:
                                        if True or not preferences().show_actual_object_for_parented_objects:
                                            collapse_outliner(override)
                                            if area.spaces.active.display_mode=='LIBRARIES':
                                                with bpy.context.temp_override(**override):
                                                    bpy.ops.outliner.show_one_level(open=True)
                                    filter_children=area.spaces.active.use_filter_children
                                    filter_content=area.spaces.active.use_filter_object_content
                                    if has_parent and preferences().show_actual_object_for_parented_objects:
                                        count=1
                                        if bpy.context.mode=='OBJECT':
                                            for a in bpy.context.selected_objects:
                                                if a!=active and a.parent and set(a.parent.users_collection)==set(a.users_collection):
                                                    count+=1
                                                    bpy.context.view_layer.objects.active=a
                                                    with bpy.context.temp_override(**override):
                                                        bpy.ops.outliner.show_active()
                                                    if count>preferences().max_objects_to_expand:
                                                        break
                                        if bpy.context.mode=='OBJECT':
                                            if active and active.parent and set(active.parent.users_collection)==set(active.users_collection):
                                                if bpy.context.view_layer.objects.active!=active:
                                                    bpy.context.view_layer.objects.active=active
                                                with bpy.context.temp_override(**override):
                                                    bpy.ops.outliner.show_active()
                                        area.spaces.active.use_filter_children=False
                                        area.spaces.active.use_filter_object_content=False
                                        collapse_outliner(override)
                                        bpy.app.timers.register(functools.partial(show_active,active_bone, active, override,area,filter_children,filter_content),first_interval=0.002)
                                        
                                    else:
                                        if preferences().expand_all_selected:
                                            count=1
                                            if bpy.context.mode=='OBJECT':
                                                for a in bpy.context.selected_objects:
                                                    if a!=active:
                                                        count+=1
                                                        bpy.context.view_layer.objects.active=a
                                                        with bpy.context.temp_override(**override):
                                                            bpy.ops.outliner.show_active()
                                                            # if preferences().show_actual_object_for_parented_objects:
                                                            #     area.spaces.active.use_filter_children=False
                                                            #     area.spaces.active.use_filter_object_content=False
                                                            #     collapse_outliner(override)
                                                            #     bpy.app.timers.register(functools.partial(show_active,active_bone, active, override,area,filter_children,filter_content),first_interval=0.0002)
                                                            # else:
                                                            #     bpy.ops.outliner.show_active()
                                                        if count>preferences().max_objects_to_expand:
                                                            break
                                            if preferences().expand_bones:
                                                if bpy.context.mode=='POSE':
                                                    for a in bpy.context.selected_pose_bones:
                                                        if a!=active_bone and active:
                                                            bpy.context.view_layer.objects.active=a.id_data
                                                            a.id_data.data.bones.active=a.bone
                                                            with bpy.context.temp_override(**override):
                                                                if preferences().show_actual_object_for_parented_objects:
                                                                    area.spaces.active.use_filter_children=False
                                                                    area.spaces.active.use_filter_object_content=False
                                                                    collapse_outliner(override)
                                                                    bpy.app.timers.register(functools.partial(show_active,active_bone, active, override,area,filter_children,filter_content),first_interval=0.002)
                                                                else:
                                                                    bpy.ops.outliner.show_active()
                                                                            
                                        if bpy.context.mode=='OBJECT':
                                            if bpy.context.view_layer.objects.active!=active:
                                                bpy.context.view_layer.objects.active=active
                                            with bpy.context.temp_override(**override):
                                                bpy.ops.outliner.show_active()
                                                # if preferences().show_actual_object_for_parented_objects:
                                                #     area.spaces.active.use_filter_children=False
                                                #     area.spaces.active.use_filter_object_content=False
                                                #     collapse_outliner(override)
                                                #     bpy.app.timers.register(functools.partial(show_active,active_bone, active, override,area,filter_children,filter_content),first_interval=0.0002)
                                                # else:
                                                #     bpy.ops.outliner.show_active()
                                        if preferences().expand_bones:
                                            if bpy.context.mode=='POSE' and active and active_bone:
                                                bpy.context.view_layer.objects.active=active_bone.id_data
                                                active_bone.id_data.data.bones.active=active_bone.bone
                                                with bpy.context.temp_override(**override):
                                                    if preferences().show_actual_object_for_parented_objects:
                                                        area.spaces.active.use_filter_children=False
                                                        area.spaces.active.use_filter_object_content=False
                                                        collapse_outliner(override)
                                                        bpy.app.timers.register(functools.partial(show_active,active_bone, active, override,area,filter_children,filter_content),first_interval=0.002)
                                                    else:
                                                        bpy.ops.outliner.show_active()
                                        # area.spaces.active.use_filter_children=filter_children
                                        # area.spaces.active.use_filter_object_content=filter_content
                                    # else:
                                    #     bpy.app.timers.register(functools.partial(show_active,active_bone, active, override,area,filter_children),first_interval=0.002)
                                
                        # break
                # if override is not None:
                #     if bpy.context.scene.collapse_other_collections:
                #         bpy.ops.outliner.expanded_toggle(override)
                #         bpy.ops.outliner.expanded_toggle(override)
            # print(time.time()-st)            
    return 0.1


class AH_OT_Click_Bypass(bpy.types.Operator):
    bl_idname = "ah.clickbypass"
    bl_label = "Select in Outliner"
    bl_description = "Used to detect clicks in outliner to temporarily disable auto hightlight while you are in outliner."
    bl_options = {"REGISTER", "UNDO"}

    def invoke(self, context,event):
        context.scene.auto_highlight_temp_disable=True
        return {'PASS_THROUGH'}
class AH_OT_Click_Bypass_View3d(bpy.types.Operator):
    bl_idname = "ah.clickbypassview"
    bl_label = "Select in Viewport"
    bl_description = "Used to detect clicks in viewport to reenable auto hightlight after it was temporarily disabled when you clicked in outliner."
    bl_options = {"REGISTER", "UNDO"}

    def invoke(self, context,event):
        context.scene.auto_highlight_temp_disable=False
        # if the user clicked in the 3D view and the addon is configured to
        # collapse collections when deselecting by clicking empty space,
        # schedule a short timer to check the selection and collapse outliner
        if context.scene.collapse_on_deselect:
            bpy.app.timers.register(collapse_on_deselect_timer, first_interval=0.05)
        return {'PASS_THROUGH'}
classes = (AH_OT_Click_Bypass, AH_OT_Click_Bypass_View3d)

addon_keymaps = []


def drawIntoOutliner(self, context):
    layout = self.layout
    layout.separator(factor=1)
    layout.prop(context.scene, 'auto_highlight_in_outliner')
    if context.scene.auto_highlight_in_outliner:
        layout.prop(context.scene, 'collapse_other_collections')
        layout.prop(context.scene, 'collapse_on_deselect')
        if context.scene.collapse_other_collections and preferences().collapse_fix:
            layout.label(text='Make sure you collapse all', icon='ERROR')
            layout.label(text='collections once using SHIFT+A')
            layout.label(text='before using this.Press again if')
            layout.label(text='collections expand instead of collapsing!')


def enabled(self, context):
    self.ah_state_set = True
    if self.auto_highlight_in_outliner:
        if not bpy.app.timers.is_registered(highlight_in_outliner):
            bpy.app.timers.register(highlight_in_outliner, persistent=True)
    else:
        if bpy.app.timers.is_registered(highlight_in_outliner):
            bpy.app.timers.unregister(highlight_in_outliner)


def collapse_on_deselect_timer():
    """Timer called shortly after a 3D-view click. If the scene has no selected objects
    and the option is enabled, collapse other collections in any Outliner areas."""
    try:
        if not bpy.context.scene.collapse_on_deselect:
            return None
    except Exception:
        return None

    # If there are no selected objects, treat this as a deselect: collapse outliner
    if not bpy.context.selected_objects:
        for win in bpy.context.window_manager.windows:
            for area in win.screen.areas:
                if area.type == 'OUTLINER' and area.spaces.active.display_mode in ['VIEW_LAYER', 'SCENES', 'LIBRARIES']:
                    for region in area.regions:
                        if region.type == 'WINDOW':
                            override = {'window': win, 'area': area, 'region': region}
                            if bpy.context.scene.collapse_other_collections:
                                collapse_outliner(override)
    return None


from bpy.app.handlers import persistent


@persistent
def start_ah(dummy):
    try:
        for scene in bpy.data.scenes:
            if scene.ah_state_set:
                scene.auto_highlight_in_outliner = scene.auto_highlight_in_outliner
            else:
                scene.auto_highlight_in_outliner = preferences().default_state
    except Exception:
        pass


def register_auto_highlight():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name="3D View", space_type="VIEW_3D")
        kmi = km.keymap_items.new("ah.clickbypassview", type='LEFTMOUSE', value="PRESS", any=True)
        addon_keymaps.append((km, kmi))
        km = kc.keymaps.new(name='Outliner', space_type='OUTLINER')
        kmi = km.keymap_items.new("ah.clickbypass", type='LEFTMOUSE', value="PRESS", any=True)
        addon_keymaps.append((km, kmi))

    bpy.types.OUTLINER_PT_filter.append(drawIntoOutliner)
    bpy.types.Scene.auto_highlight_in_outliner = bpy.props.BoolProperty(default=True, name="Auto Highlight", update=enabled)
    bpy.types.Scene.collapse_other_collections = bpy.props.BoolProperty(default=True, name="Collapse Other Collections")
    bpy.types.Scene.auto_highlight_temp_disable = bpy.props.BoolProperty(default=False, name="Auto Highlight Temp Disable")
    bpy.types.Scene.ah_state_set = bpy.props.BoolProperty(default=False, name="Auto Highlight State Set")
    bpy.types.Scene.collapse_on_deselect = bpy.props.BoolProperty(default=True, name="Collapse On Deselect", description="When enabled, clicking empty space in the 3D View (deselect) will collapse other collections in the outliner")
    bpy.app.handlers.load_post.append(start_ah)
    # Scene property updates only fire on change, and bpy.context is restricted while add-ons load,
    # so apply the saved/default state shortly after registration (also covers enabling mid-session).
    bpy.app.timers.register(_deferred_start, first_interval=0.5)


def _deferred_start():
    start_ah(None)
    return None


def unregister_auto_highlight():
    if bpy.app.timers.is_registered(_deferred_start):
        bpy.app.timers.unregister(_deferred_start)
    if bpy.app.timers.is_registered(highlight_in_outliner):
        bpy.app.timers.unregister(highlight_in_outliner)
    from bpy.utils import unregister_class

    for (km, kmi) in addon_keymaps:
        try:
            km.keymap_items.remove(kmi)
        except Exception:
            pass
    addon_keymaps.clear()
    try:
        bpy.types.OUTLINER_PT_filter.remove(drawIntoOutliner)
    except Exception:
        pass
    try:
        bpy.app.handlers.load_post.remove(start_ah)
    except Exception:
        pass
    for cls in reversed(classes):
        try:
            unregister_class(cls)
        except Exception:
            pass
    for attr in ("auto_highlight_in_outliner", "collapse_other_collections", "auto_highlight_temp_disable", "ah_state_set", "collapse_on_deselect"):
        try:
            delattr(bpy.types.Scene, attr)
        except Exception:
            pass
