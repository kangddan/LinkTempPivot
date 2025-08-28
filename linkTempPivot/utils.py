import numbers
from maya        import cmds
from maya.api    import OpenMaya as om2
from collections import defaultdict, deque
from           . import nodes, manager


def getTransformNodes():
    transformNodes = []
    sel = om2.MGlobal.getActiveSelectionList()
    for i in range(sel.length()):
        mobj = sel.getDependNode(i)
        if not mobj.hasFn(om2.MFn.kTransform):
            continue
        transformNodes.append(nodes.TransformNode(mobj))
    return transformNodes
    
    
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
    
    
def hasMasterGroup(nodes):
    '''
    Check whether the node list contains a masterGroup
    '''
    return any(node.depFn.hasAttribute(manager.MASTER_GROUP_ATTR_NAME) for node in nodes)
    
    
def removeScriptJobCallbacks(indices):
    if isinstance(indices, numbers.Number):
        indices = [indices]
    for index in indices:
        if not cmds.scriptJob(exists=index):
            continue
        cmds.scriptJob(kill=index, force=True)
        
        
def removeApiEventCallbacks(indices):
    try:
        if isinstance(indices, numbers.Number):
            om2.MEventMessage.removeCallback(indices)
        else:
            om2.MEventMessage.removeCallbacks(indices)
    except:
        om2.MGlobal.displayInfo('Callback ID is not valid')
        
        
def showKeyframesFor(objects):
    connection = cmds.selectionConnection()
    for obj in objects:
        cmds.selectionConnection(connection, edit=True, select=obj)
    cmds.timeControl(cmds.lsUI(type='timeControl')[0], edit=True, mainListConnection=connection)
    
    
def showKeyframesForSelection():
    defaultConnection = cmds.selectionConnection(activeList=True)
    cmds.timeControl(cmds.lsUI(type='timeControl')[0], edit=True, mainListConnection=defaultConnection)
    
    
    

