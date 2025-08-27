import maya.cmds as cmds
import maya.api.OpenMaya as om2
from collections import defaultdict, deque
from . import nodes, manager


class TempPivot(object):
    
    def __init__(self):
        
        self.callbackIndices    = []
        self.masterGroup        = None
        self.transformNodesData = {}
        self.transformNodes     = []
        self.undoStarted        = True
        self.scriptJobIndex     = -1
        self.maxIter            = 0
           
           
    @staticmethod
    def getTransformNodes():
        transformNodes = []
        sel = om2.MGlobal.getActiveSelectionList()
        for i in range(sel.length()):
            mobj = sel.getDependNode(i)
            if not mobj.hasFn(om2.MFn.kTransform):
                continue
            transformNodes.append(nodes.TransformNode(mobj))
        return transformNodes
        
        
    @staticmethod
    def getTransformNodesSorted():
        sel = om2.MGlobal.getActiveSelectionList()
        transformNodes = []
        for i in range(sel.length()):
            mobj = sel.getDependNode(i)
            if mobj.hasFn(om2.MFn.kTransform):
                transformNodes.append(mobj)
        
        dagNodes = {}
        hashMap  = {} 
        for node in transformNodes:
            handle = om2.MObjectHandle(node)
            hcode  = handle.hashCode()
            dagNodes[hcode] = om2.MFnDagNode(node)
            hashMap[hcode]  = node
            
        graph    = defaultdict(list)
        indegree = defaultdict(int)

        for h1 in dagNodes:
            dagNode = dagNodes[h1]
            for h2 in dagNodes:
                if h1 == h2:
                    continue
                if dagNode.isParentOf(hashMap[h2]):
                    graph[h1].append(h2)
                    indegree[h2] += 1
        
        queue = deque([h for h in dagNodes if indegree[h] == 0])
        sortedList = []
        
        while queue:
            current = queue.popleft()
            sortedList.append(hashMap[current])
            for child in graph[current]:
                indegree[child] -= 1
                if indegree[child] == 0:
                    queue.append(child)

        return [nodes.TransformNode(node) for node in sortedList]
        
        
    @staticmethod
    def hasMasterGroup(nodes):
        '''
        Check whether the node list contains a masterGroup
        '''
        return any(node.depFn.hasAttribute(manager.MASTER_GROUP_ATTR_NAME) for node in nodes)
        
            
    def _initialize(self):
        transformNodes = TempPivot.getTransformNodesSorted()
        if not transformNodes or TempPivot.hasMasterGroup(transformNodes):
            return False

        self.masterGroup = manager.TempPivotManager.createMasterGroup(transformNodes)
        
        for node in transformNodes:
            offsetMatrix = node.worldMatrix * self.masterGroup.worldInverseMatrix
            self.transformNodesData[node] = offsetMatrix
        self.transformNodes = list(self.transformNodesData.keys()) 
        self.maxIter        = max(node.dagPath.length() for node in self.transformNodes)
        return True
        
        
    def setup(self):
        result = self._initialize()
        if not result:
            return 
            
        # 1 selected masterGroup
        om2.MGlobal.clearSelectionList()
        om2.MGlobal.selectByName(self.masterGroup.fullPathName)
        cmds.EnterEditModePress()
        
        # 2 add callbacks 
        self.scriptJobIndex = cmds.scriptJob(attributeChange=[f'{self.masterGroup.dagPath.fullPathName()}.matrix', self.endUndo], protected=True)
        self.callbackIndices.append(om2.MDagMessage.addMatrixModifiedCallback(self.masterGroup.dagPath, self.update, None))
        self.callbackIndices.append(om2.MEventMessage.addEventCallback('SelectionChanged', self.clear, None))


    def addUndo(self):
        if self.undoStarted:
            cmds.undoInfo(openChunk=True)
            self.undoStarted = False
        
        
    def endUndo(self, *args):
        self.undoStarted = True
        cmds.undoInfo(closeChunk=True)


    def update(self, *args):
        self.addUndo()
        masterMatrix = self.masterGroup.worldMatrix  
         
        for _ in range(self.maxIter):
            nextQueue = []
            for node in self.transformNodes:
                newWorldMatrix = self.transformNodesData[node] * masterMatrix   
                if not node.worldMatrix.isEquivalent(newWorldMatrix, 1e-5):
                    cmds.xform(node.fullPathName, m=list(newWorldMatrix), ws=True)
                    nextQueue.append(node) 
            if not nextQueue:
                break
                
            
    def clear(self, *args):
        
        def _clear():
            if len(self.transformNodes) == 1 and self.masterGroup is not None and self.masterGroup.exists:
                manager.TempPivotManager.cacheLocalMatrix(self.masterGroup, self.transformNodes[0])
                
            try: om2.MEventMessage.removeCallbacks(self.callbackIndices)
            except: pass
            if cmds.scriptJob(exists=self.scriptJobIndex):
                cmds.scriptJob(kill=self.scriptJobIndex, force=True)
                
            if self.masterGroup is not None and self.masterGroup.exists:
                dagMod = om2.MDagModifier()
                self.masterGroup.depFn.isLocked = False
                dagMod.deleteNode(self.masterGroup.mobject)
                dagMod.doIt()

        cmds.evalDeferred(_clear)
