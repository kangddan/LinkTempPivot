from maya     import cmds
from maya.api import OpenMaya as om2
from        . import nodes, manager, utils


class TempPivot(object):
    
    def __cacheLocalMatrix(self):
        #for node in self.transformNodes:
            #manager.TempPivotManager.cacheLocalMatrix(self.masterGroup, node)
        manager.TempPivotManager.cacheLocalMatrix(self.masterGroup, self.transformNodes[-1])
    
    def __restoreSelection(self):
        sel = om2.MSelectionList()
        for transformNode in self.transformNodes:
            if transformNode.exists:
                sel.add(transformNode.fullPathName)
        if sel.length() > 0:
            om2.MGlobal.setActiveSelectionList(sel)
        
        
    def __deleteMasterGroup(self):
        if self.masterGroup is not None and self.masterGroup.exists:
            dagMod = om2.MDagModifier()
            self.masterGroup.depFn.isLocked = False
            dagMod.deleteNode(self.masterGroup.mobject)
            dagMod.doIt()
            
            
    def __removeAllCallbacks(self):
        utils.removeScriptJobCallbacks([self.timeChangedCallbackId, self.endUndoCallbackId])                            
        utils.removeApiEventCallbacks([self.selectionChangedCallbackId, self.updateLocalMatrixCallbackId])
    
    
    def __init__(self):
        self.masterGroup        = None
        self.transformNodesData = {}
        self.transformNodes     = []
        self.maxIterations      = 0
        
        self.undoStarted = True
        
        # Callbacks
        self.selectionChangedCallbackId  = -1
        self.updateLocalMatrixCallbackId = -1
        
        self.timeChangedCallbackId       = -1
        self.endUndoCallbackId           = -1
        
    
    def _initialize(self):
        self.transformNodes = utils.getTransformNodesSorted()
        if not self.transformNodes or utils.hasMasterGroup(self.transformNodes):
            return False
            
        self.masterGroup = manager.TempPivotManager.createMasterGroup(self.transformNodes[-1])
        for node in self.transformNodes:
            offsetMatrix = node.worldMatrix * self.masterGroup.worldInverseMatrix
            self.transformNodesData[node] = offsetMatrix
        self.maxIterations  = max(node.dagPath.length() for node in self.transformNodes)
        return True
        
        
    def addUndo(self):
        if self.undoStarted:
            cmds.undoInfo(openChunk=True)
            self.undoStarted = False
        
        
    def endUndo(self, *args):
        if not self.undoStarted:
            self.undoStarted = True
            cmds.undoInfo(closeChunk=True)
            
    
    def setup(self):
        result = self._initialize()
        if not result:
            return  
        # 0 set Timeline Focus
        utils.showKeyframesFor([node.fullPathName for node in self.transformNodes])
            
        # 1 selected masterGroup
        om2.MGlobal.clearSelectionList()
        om2.MGlobal.selectByName(self.masterGroup.fullPathName)
        cmds.EnterEditModePress()
        
        # 2 add callbacks 
        self.selectionChangedCallbackId  = om2.MEventMessage.addEventCallback('SelectionChanged', self.clear, None)
        self.updateLocalMatrixCallbackId = om2.MDagMessage.addMatrixModifiedCallback(self.masterGroup.dagPath, self.update, None)
        
        self.timeChangedCallbackId = cmds.scriptJob(event=['timeChanged', self.updateMasterGroupTransform], protected=True)
        self.endUndoCallbackId     = cmds.scriptJob(attributeChange=['{0}.matrix'.format(self.masterGroup.dagPath.fullPathName()), self.endUndo], protected=True)

        
    def updateMasterGroupTransform(self, *args):
        def _updateMasterGroupTransform():
            om2.MEventMessage.removeCallback(self.updateLocalMatrixCallbackId)
            manager.TempPivotManager.setTransform(self.masterGroup, self.transformNodes[-1])
            self.updateLocalMatrixCallbackId = om2.MDagMessage.addMatrixModifiedCallback(self.masterGroup.dagPath, self.update, None)
            for node in self.transformNodes:
                offsetMatrix = node.worldMatrix * self.masterGroup.worldInverseMatrix
                self.transformNodesData[node] = offsetMatrix
                
        if self.masterGroup is not None and self.masterGroup.exists:
            cmds.evalDeferred(_updateMasterGroupTransform)
 
 
    def update(self, mobject, flags, clientData):
        # update transformNodes worldMatrix
        if flags & (om2.MDagMessage.kScale | om2.MDagMessage.kRotation | om2.MDagMessage.kTranslation):
            self.addUndo()
            masterMatrix = self.masterGroup.worldMatrix  
            for _ in range(self.maxIterations):
                nextQueue = []
                for node in self.transformNodes:
                    newWorldMatrix = self.transformNodesData[node] * masterMatrix   
                    if not node.worldMatrix.isEquivalent(newWorldMatrix, 1e-5):
                        cmds.xform(node.fullPathName, m=list(newWorldMatrix), ws=True)
                        nextQueue.append(node) 
                if not nextQueue:
                    break
                    
        # cache localMatrix            
        elif flags & (om2.MDagMessage.kScalePivot | om2.MDagMessage.kRotatePivot):
            self.__cacheLocalMatrix()
                

    def clear(self, *args):
        def _clear():
            self.__removeAllCallbacks()
            self.__deleteMasterGroup()
            self.__restoreSelection()
            
        utils.showKeyframesForSelection()
        cmds.evalDeferred(_clear)
        