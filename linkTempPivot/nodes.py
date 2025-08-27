import maya.api.OpenMaya as om2

class BaseNode(object):
    def __hash__(self):
        return self.handle.hashCode()
    
    
    def __eq__(self, other):
        if self is other:
            return True
        if not isinstance(other, self.__class__):
            return False
        return self.handle == other.handle
        
        
    def __repr__(self):
        return '<{} at {} {}>'.format(self.__class__.__name__, hex(id(self)), self.name)
            
                       
    def __str__(self):
        return self.name
        
        
    def __init__(self, node):
        if isinstance(node, str):
            node = om2.MGlobal.getSelectionListByName(node).getDependNode(0) 
        self._initialize(node)
        
        
    def _initialize(self, node):
        self._mobject = node
        self._handle  = om2.MObjectHandle(node)
        self._depFn   = om2.MFnDependencyNode(node)
        
        
    @property
    def exists(self):
        return self.handle.isValid()
        
        
    @property
    def mobject(self):
        return self._mobject
        
        
    @property
    def handle(self):
        return self._handle
        
        
    @property
    def depFn(self):
        return self._depFn
        
        
    @property
    def name(self):
        return self.depFn.name() if self.exists else ''
        
        
    @property
    def uuid(self):
        return self.depFn.uuid().asString()
    

class TransformNode(BaseNode):
        
        
    def _initialize(self, node):
        super(TransformNode, self)._initialize(node)
        
        self._dagPath     = om2.MDagPath.getAPathTo(node)
        self._transformFn = om2.MFnTransform(self._dagPath)      
        
        
    @property
    def dagPath(self):
        return self._dagPath
        
        
    @property
    def transformFn(self):
        return self._transformFn
        
        
    @property
    def fullPathName(self):
        return self.dagPath.fullPathName() if self.exists else ''
        
        
    @property
    def parentInverseMatrix(self):
        return self.dagPath.exclusiveMatrixInverse()
        
        
    @property
    def parentMatrix(self):
        return self.dagPath.exclusiveMatrix()
        
        
    @property
    def worldMatrix2(self):
        worldMatrix = self.worldMatrix
        rotatePivot = self.transformFn.rotatePivot(om2.MSpace.kTransform)
        offset      = rotatePivot * worldMatrix
        worldMatrix[12], worldMatrix[13], worldMatrix[14], _ = offset
        return worldMatrix
        
        
    @property
    def worldMatrix(self):
        return self.dagPath.inclusiveMatrix()
    
    
    @worldMatrix.setter
    def worldMatrix(self, newMatrix):
        localMatrix = newMatrix * self.parentInverseMatrix
        self.transformFn.setTransformation(om2.MTransformationMatrix(localMatrix))
         
         
    @property
    def matrix(self):
        return self.worldMatrix * self.parentInverseMatrix
        
        
    @matrix.setter
    def matrix(self, newMatrix):
        self.transformFn.setTransformation(om2.MTransformationMatrix(newMatrix))
        
        
    @property
    def worldInverseMatrix(self):
        return self.dagPath.inclusiveMatrixInverse()
        
        
    @property
    def inverseMatrix(self):
        return self.matrix.inverse()
        
        
    @property      
    def globalPosition(self):
        return self.transformFn.translation(om2.MSpace.kWorld)
        
        
    @globalPosition.setter
    def globalPosition(self, newPosition):
        self.transformFn.setTranslation(newPosition, om2.MSpace.kWorld)
          
          
    @property      
    def localPosition(self):
        return self.transformFn.translation(om2.MSpace.kTransform)
        
        
    @localPosition.setter
    def localPosition(self, newPosition):
        self.transformFn.setTranslation(newPosition, om2.MSpace.kTransform)
