import os
import shutil
import maya.api.OpenMaya as om2
from importlib import reload


def deletePycache(directory):
    for root, dirs, _ in os.walk(directory):
        for dir in dirs:
            if dir == '__pycache__':
                shutil.rmtree(os.path.join(root, dir))

def findPythonModules(directory):
    moduleNames = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py') and file != '__init__.py': 
                relativePath = os.path.relpath(os.path.join(root, file), start=os.path.dirname(directory))
                modulePath = relativePath.replace(os.sep, '.').rsplit('.', 1)[0]
                moduleNames.append(modulePath)
    return moduleNames


def reloadIt():
    directory = os.path.dirname(os.path.abspath(__file__))
    
    modulesToReload = findPythonModules(directory)
    for moduleName in modulesToReload:
        try:
            module = __import__(moduleName, fromlist=[''])
            reload(module)
            print('{} reloaded successfully'.format(moduleName))
        except Exception as e:
            print('Error reloading {}: {}'.format(moduleName, e))
    om2.MGlobal.displayInfo('-------------------- ALL RELOAD : OK')


if __name__ == '__main__':
    reloadIt()
