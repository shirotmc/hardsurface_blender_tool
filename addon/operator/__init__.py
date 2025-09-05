import bpy
# Menu
from .bevel import *
from .solidify import TMC_OP_Solidify
from .ray_caster import TMC_OP_Ray
## Panel
from .check import *
from .modifier import *
from .material import *
from .modeling import *
from .normal import *
from .vertex_group import *
from .bridge import *
from .screenshot import *
from .mirror import *
from .collection import *
from .uv import *
from .bakeset import *

classes = [
	# Menu
	TMC_OP_Bevel,
	TMC_OP_Solidify,
	TMC_OP_Ray,
	
	# Panel
	## Check
	TMC_OP_CheckAll,
	TMC_OP_CheckNgonsFace,
	TMC_OP_CheckNonManifold,
	TMC_OP_CheckIntersectFace,
	TMC_OP_CheckZeroEdgeLength,
	TMC_OP_CheckZeroFaceArea,
	TMC_OP_CheckIsolatedVertex,
	TMC_OP_CheckSilhouette,
	## Modifier
	TMC_OP_ToggleModifier,
	TMC_OP_ApplyModifier,
	TMC_OP_BevelCustomSetting,
	TMC_OP_GetBevelModifiersFromVertex,
	TMC_OP_SelectObjectFromCurrentMirror,
	TMC_OP_SetCurrentMirrorToTargetMirror,
	## Collection
	TMC_OP_ToggleCurrentHideGroup,
	## Material
	TMC_OP_DeleteDuplicateMaterials,
	TMC_OP_CleanMaterialSlots,
	TMC_OP_DeleteAllMaterials,
	## UV
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
	### Flatten Face
	TMC_OP_FlattenFace,
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
	TMC_OP_Set_Normal_With_Active_Face
]

def register_operators():
	from bpy.utils import register_class
	for cls in classes:
		register_class(cls)
	
def unregister_operators():
	from bpy.utils import unregister_class
	for cls in reversed(classes):
		unregister_class(cls)