import json
import maya.cmds as cmds
import maya.api.OpenMaya as om2
from . import nodes


CONTAINER_ATTR_NAME    = 'tempPivotData'
MASTER_GROUP_ATTR_NAME = 'isMasterGroup'


class ContainerNode(nodes.BaseNode):
    
    
    def __init__(self, node):
        super().__init__(node)
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
    def getCenterPosition(cls, transformNodes:list):
        total = om2.MVector()
        for node in transformNodes:
            globalPosition = node.globalPosition
            total.x += globalPosition.x
            total.y += globalPosition.y
            total.z += globalPosition.z  
        count = len(transformNodes)
        return total / (count if count > 0 else 1)
    
    
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
    def createMasterGroup(cls, transformNodes=None):
        dagMod = om2.MDagModifier()
        mobj   = dagMod.createNode('transform')
        dagMod.renameNode(mobj, 'master_group')
        dagMod.doIt()
        masterGroup = nodes.TransformNode(mobj)

        # add Attr
        attrFn   = om2.MFnNumericAttribute()
        boolAttr = attrFn.create(MASTER_GROUP_ATTR_NAME, 
                                 MASTER_GROUP_ATTR_NAME, 
                                 om2.MFnNumericData.kBoolean, 
                                 True)
        masterGroup.depFn.addAttribute(boolAttr)
        cls.connectAsset(masterGroup, cls.getAsset())
        
        # Prevent manual deletion of masterGroup
        masterGroup.depFn.isLocked = True

        # set transform
        if len(transformNodes) > 1:
            centerPosition = cls.getCenterPosition(transformNodes)
            masterGroup.globalPosition = centerPosition  
        else:
            cls.setTransform(masterGroup, transformNodes[0])
        return masterGroup


    @classmethod
    def connectAsset(cls, masterGroup, container):
        cmds.container(container.name, edit=True, addNode=masterGroup.fullPathName, includeHierarchyBelow=True)
        cmds.container(container.name, edit=True, publishAsRoot=[masterGroup.fullPathName, True])
             
             
    @classmethod
    def cacheLocalMatrix(cls, masterGroup, transformNode):
        container = cls.getAsset()
        oldData = container.getData()
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
