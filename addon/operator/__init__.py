import bpy
from bpy.props import PointerProperty
# Menu
from .bevel import *
from .boolean import *
## Panel
from .check import *
from .modifier import *
from .material import *
from .modeling import *
from .looptools import  LoopToolsProps, Circle, Curve, Flatten, Relax, Space
from .normal import *
from .vertex_group import *
from .geometry_data import *
from .bridge import *
from .screenshot import *
from .mirror import *
from .collection import *
from .uv import *
from .bakeset import *
from .auto_delete import *
from .edge_constraint import *
from .rebevel import TMC_OP_Unbevel, TMC_OP_BevelCurve, TMC_OP_reBevelCurve, TMC_OT_RebevelSmart


classes = [
	# Menu
	TMC_OP_Boolean,

	# Panel
	## Check
	TMC_OP_CheckAll,
	TMC_OP_CheckMeshNoTris,
	TMC_OP_CheckNgonsFace,
	TMC_OP_CheckNonManifold,
	TMC_OP_CheckIntersectFace,
	TMC_OP_CheckZeroEdgeLength,
	TMC_OP_CheckZeroFaceArea,
	TMC_OP_CheckIsolatedVertex,
	TMC_OP_CheckZeroUVSet,
	TMC_OP_CheckSilhouette,
	## Modifier
	TMC_OP_ToggleModifier,
	TMC_OP_ApplyModifier,
	TMC_OP_BevelCustomSetting,
	TMC_OP_GetBevelModifiersFromVertex,
	TMC_OP_SelectObjectFromCurrentMirror,
	TMC_OP_SetCurrentMirrorToTargetMirror,
	## Collection
	TMC_OP_CollapseAllCollections,
	TMC_OP_ToggleCurrentHideGroup,
	## Material
	TMC_OP_DeleteDuplicateMaterials,
	TMC_OP_CleanMaterialSlots,
	TMC_OP_DeleteAllMaterials,
	TMC_OP_AddMaterial,
	TMC_OP_SelectObjectsByMaterial,
	TMC_OP_SelectFacesOnActiveByMaterial,
	TMC_OP_AssignMaterialToSelection,
	## UV
	TMC_OP_UVBySharpEdge,
	TMC_OP_RenameUV1,
	TMC_OP_DeleteRedundantUV,
	## Bakeset
	TMC_OP_RenameHighpoly,
	TMC_OP_CreateBakeSet,
	TMC_OP_AutoCreateBakeSet,
	TMC_OP_ExportBakeSet,
	TMC_OP_ExportSelectedHighLow,

	## Modeling
	### Edge Length
	TMC_OP_SetEdgeLength,
	TMC_OP_GetEdgeLength,
	TMC_OP_AddLockVertex,
	TMC_OP_ClearLockVertex,
	### Circle Edge
	TMC_OP_CircleEdge,
	TMC_OP_AddPriorityVertex,
	TMC_OP_ClearPriorityVertex,
	TMC_OP_GetCircleDiameter,
	TMC_OP_GetCircleAngle,
	### Straight Edge
	TMC_OP_StraightEdge,
	### Relax Edge
	TMC_OP_RelaxEdge,
	### Space Edge
	TMC_OP_SpaceEdge,
	### Smooth Edge
	TMC_OP_SmoothEdge,
	### Flatten Face
	TMC_OP_FlattenFace,
	### Edge Constraints (Rotate/Scale along edge direction)
	TMC_OP_EdgeConstraints,
	### ReBevel (Mesh/Curve)
	TMC_OP_Unbevel,
	TMC_OP_BevelCurve,
	TMC_OP_reBevelCurve,
	TMC_OT_RebevelSmart,
	### Loop Tools
	LoopToolsProps,
	Circle,
	Curve,
	Flatten,
	Relax,
	Space,

	### Detach Element
	TMC_OP_DetachElement,

	### Clone Element
	TMC_OP_CloneElement,

	## Bridge
	TMC_OP_ExportToMaya,
	TMC_OP_ImportFromMaya,

	## Screenshot
	TMC_OP_AutoScreenshot,
	TMC_OP_CustomScreenshot,

	### Vertex Group
	TMC_OP_CleanVertexGroup,
	### Vertex Normal
	TMC_OP_Set_Normal_With_Active_Face,

	### Geometry Data
	TMC_OP_ClearCustomNormalsData,

	# Utilities
	TMC_OP_AutoDelete,
]

def menu_func(self, context):
	self.layout.menu("VIEW3D_MT_edit_mesh_looptools")
	self.layout.separator()

def register_operators():
	from bpy.utils import register_class
	for cls in classes:
		register_class(cls)
	bpy.types.VIEW3D_MT_edit_mesh_context_menu.prepend(menu_func)
	bpy.types.WindowManager.looptools = PointerProperty(type=LoopToolsProps)
	
def unregister_operators():
	from bpy.utils import unregister_class
	for cls in reversed(classes):
		unregister_class(cls)
			
	bpy.types.VIEW3D_MT_edit_mesh_context_menu.remove(menu_func)
	try:
		del bpy.types.WindowManager.looptools
	except Exception as e:
		print('unregister fail:\n', e)
		pass
