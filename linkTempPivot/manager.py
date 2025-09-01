import math
import json
from maya          import cmds
from maya.api      import OpenMaya as om2
from linkTempPivot import nodes


CONTAINER_ATTR_NAME    = 'tempPivotData'
MASTER_GROUP_ATTR_NAME = 'isMasterGroup'


class ContainerNode(nodes.BaseNode):
    
    
    def __init__(self, node):
        super(ContainerNode, self).__init__(node)
        self.setBlackBox(True)
        
        
    def setBlackBox(self, value):
        self.depFn.findPlug('blackBox', False).setBool(value)


    @classmethod    
    def create(cls):
        dgMod = om2.MDGModifier()
        containerObj = dgMod.createNode('container')
        dgMod.renameNode(containerObj, 'TempPivotManager')
        dgMod.doIt()
        
        attrFn  = om2.MFnTypedAttribute()
        strAttr = attrFn.create(CONTAINER_ATTR_NAME, 
                                CONTAINER_ATTR_NAME, 
                                om2.MFnData.kString,
                                om2.MFnStringData().create('{}'))
        depFn = om2.MFnDependencyNode(containerObj)
        depFn.addAttribute(strAttr)
        depFn.findPlug(CONTAINER_ATTR_NAME, False).isLocked = True
        return cls(containerObj) 
        
        
    def getData(self):
        return json.loads(self.depFn.findPlug(CONTAINER_ATTR_NAME, False).asString())
        
        
    def setData(self, data):
        self.depFn.findPlug(CONTAINER_ATTR_NAME, False).isLocked = False
        self.depFn.findPlug(CONTAINER_ATTR_NAME, False).setString(json.dumps(data)) 
        self.depFn.findPlug(CONTAINER_ATTR_NAME, False).isLocked = True


class TempPivotManager(object):
    
    
    @classmethod
    def getAsset(cls):
        it    = om2.MItDependencyNodes(om2.MFn.kContainer) 
        depFn = om2.MFnDependencyNode() 
        while not it.isDone():
            mobj = it.thisNode()
            depFn.setObject(mobj) 
            if depFn.hasAttribute(CONTAINER_ATTR_NAME) and not depFn.isFromReferencedFile:
                return ContainerNode(mobj)
            it.next()
        return ContainerNode.create()

        
    @classmethod
    def createMasterGroup(cls, transformNode=None):
        cmds.undoInfo(stateWithoutFlush=False)
        
        group = cmds.createNode('transform', name='master_group')
        cmds.addAttr(group, ln=MASTER_GROUP_ATTR_NAME, at='bool', dv=True)
        for attr in ('t', 'r', 's'):
            for sub in ('x', 'y', 'z'):
                cmds.setAttr('{0}.{1}'.format(group, attr+sub), keyable=False, channelBox=True)
        cmds.setAttr('{0}.v'.format(group), keyable=False, channelBox=True)
        
        masterGroup = nodes.TransformNode(group)
        cls.connectAsset(masterGroup, cls.getAsset())
        masterGroup.depFn.isLocked = True

        # set transform
        cls.setTransform(masterGroup, transformNode)
            
        cmds.undoInfo(stateWithoutFlush=True)
        return masterGroup


    @classmethod
    def connectAsset(cls, masterGroup, container):
        cmds.container(container.name, edit=True, addNode=masterGroup.fullPathName, includeHierarchyBelow=True)
        cmds.container(container.name, edit=True, publishAsRoot=[masterGroup.fullPathName, True])
        
    @classmethod    
    def __getMasterGroupWorldMatrix(cls, masterGroup):
        dagPath     = masterGroup.dagPath
        transformFn = masterGroup.transformFn
        worldMatrix = masterGroup.worldMatrix
        
        globalPose = om2.MVector(om2.MFnTransform(dagPath).rotatePivot(om2.MSpace.kTransform) * worldMatrix)
        euler      = om2.MEulerRotation(*(math.radians(r) for r in cmds.manipPivot(q=True, o=True)[0]))
        euler.reorderIt(masterGroup.rotateOrder)
        
        transfromMatrix = om2.MTransformationMatrix()
        transfromMatrix.setTranslation(globalPose, om2.MSpace.kWorld)
        transfromMatrix.setRotation(euler)
        
        return transfromMatrix.asMatrix()
             
             
    @classmethod
    def cacheLocalMatrix(cls, masterGroup, transformNode):
        container = cls.getAsset()
        oldData   = container.getData()
        #offsetMatrix = cls.__getMasterGroupWorldMatrix(masterGroup) * transformNode.worldInverseMatrix
        offsetMatrix = masterGroup.worldMatrix2 * transformNode.worldInverseMatrix
        oldData[transformNode.uuid] = list(offsetMatrix)
        container.setData(oldData)

        
    @classmethod
    def setTransform(cls, masterGroup, transformNode):
        container = cls.getAsset()
        oldData   = container.getData()
        localMatrix = oldData.get(transformNode.uuid, None)
        if localMatrix is None:
            masterGroup.worldMatrix = transformNode.worldMatrix
        else:
            masterGroup.worldMatrix = om2.MMatrix(localMatrix) * transformNode.worldMatrix

