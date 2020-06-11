import os
import requests
from pathlib import Path
import re
import functools
import types
import traceback
import base64
import sys
from types import ModuleType, FunctionType
from gc import get_referents
import json
import ast

from bson.objectid import ObjectId 
from core import settings, function

functionSafeList = function.systemFunctions

regexEvalString = re.compile("(\%\%([^%]*)\%\%)")
regexDict = re.compile("^([a-zA-Z]*)\[.*\]")
regexDictKeys = re.compile("(\[\"?([^\]\"]*)\"?\])")
regexFunction = re.compile("^([a-zA-Z0-9]*)\(.*\)")
regexFunctionOpen = re.compile("^([a-zA-Z0-9]*)\(.*")
regexCommor = re.compile(",(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)")
regexInt = re.compile("^[0-9]*$")
regexFloat = re.compile("^[0-9]*\.[0-9]*$")

# Return evaluated dictionary of list seperated varibles ['test','this is a test %data["event"]["tick"]%']
def defineVars(varDefinitions,dicts={},functionSafeList=functionSafeList):
    result = {}
    for varDefinition in varDefinitions:
        result[varDefinition[0]] = evalString(str(varDefinition[1]),dicts,functionSafeList)
    return result

def evalString(varString,dicts={},functionSafeList=functionSafeList):
    results = varString
    evalMatches = regexEvalString.findall(varString)
    for evalMatch in evalMatches:
        if results is not None:
            results = typeCast(results.replace(evalMatch[0],str(typeCast(evalMatch[1],dicts,functionSafeList))))
    return results

def evalDict(varDict,dicts={},functionSafeList=functionSafeList):
    result = {}
    for key, value in varDict.items():
        if type(value) is str:
            result[key] = evalString(varDict[key],dicts,functionSafeList)
        elif type(value) is dict:
            if key not in result:
                result[key] = evalDict(value,dicts,functionSafeList)
            else:
                result[key].update(evalDict(value,dicts,functionSafeList))
        else:
            result[key] = varDict[key]
    return result

def evalList(varList,dicts={},functionSafeList=functionSafeList):
    result = []
    for item in varList:
        if type(item) is str:
            result.append(evalString(item,dicts,functionSafeList))
        elif type(item) is dict:
            result.append(evalDict(item,dicts,functionSafeList))
        else:
            result.append(item)
    return result

# Get dict values from string dict
def getDictValue(varString,dicts={}):
    def nested_dict_get(dictionary, keys):
        try:
            return functools.reduce(lambda d, key: d.get(key) if d else None, keys, dictionary)
        # Unable to convert from dictionary to value
        except AttributeError:
            return None

    if regexDict.search(varString):
        dictName = varString.split("[")[0]
        if dictName in dicts:
            dictKeys = []
            for key in regexDictKeys.findall(varString):
                dictKeys.append(typeCast(key[1]))
            return typeCast(nested_dict_get(dicts[dictName],dictKeys))
    return None

# Type cast string into varible types, includes dict and function calls
def typeCast(varString,dicts={},functionSafeList=functionSafeList):
    if type(varString) == str:
        # String defined
        if varString.startswith("\"") and varString.endswith("\""):
            return str(varString[1:-1])
        # Attempt to cast
        try:
            return ast.literal_eval(varString)
        except Exception as e:
            pass
        # dict
        if regexDict.search(varString):
            return getDictValue(varString,dicts)
        # Function
        elif regexFunction.search(varString):
            functionName = varString.split("(")[0]
            if functionName in functionSafeList:
                functionArgs = []
                # Cast type from string for function arguments
                functionFound = None
                for functionArg in regexCommor.split(varString[(len(functionName)+1):-1]):
                    if not functionFound:
                        if regexFunctionOpen.search(functionArg):
                            functionFound = functionArg
                            if functionFound.endswith(")"):
                                functionArg = functionFound
                                functionFound = None
                    else:
                        functionFound+=",{0}".format(functionArg)
                        if functionFound.endswith(")"):
                            functionArg = functionFound
                            functionFound = None
                    if not functionFound:
                        value = typeCast(functionArg.strip(),dicts,functionSafeList)
                        functionArgs.append(value)
                if functionFound:
                    value = typeCast(functionArg.strip(),dicts,functionSafeList)
                    functionArgs.append(value)
                # Catch any execution errors within functions
                try:
                    if len(functionArgs) > 0:
                        a = functionSafeList[functionName](*functionArgs)
                        return a
                    else:
                        return functionSafeList[functionName]()
                except Exception as e:
                    from system.models import trigger as systemTrigger
                    systemTrigger.failedTrigger(None, "FunctionCrash", "Function functionName='{0}' crashed with msg='{1}'".format(functionName,''.join(traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__))))
    # Default to exsiting
    return varString

def handelTypes(_object):
        # Handle none native json types
    if type(_object) is ObjectId:
        return str(_object)
    else:
        return _object

def jsonToClass(_class,json):
    members = [attr for attr in dir(_class) if not callable(getattr(_class, attr)) and not "__" in attr and attr ]
    for key, value in json.items():
        for member in members:
            if key == member:
                valueObject = handelTypes(value)
                if type(getattr(_class,member)) == type(valueObject):
                    setattr(_class,member,valueObject)
                    break
                elif type(getattr(_class,member)) == str:
                    setattr(_class,member,str(valueObject))
                    break
                elif type(getattr(_class,member)) == float and type(valueObject) == int:
                    setattr(_class,member,float(valueObject))
                    break
                elif type(getattr(_class,member)) == int and type(valueObject) == float:
                    setattr(_class,member,int(valueObject))
                    break
    return _class

def classToJson(_class,hidden=False):
    members = [attr for attr in dir(_class) if not callable(getattr(_class, attr)) and not "__" in attr and attr ]
    result = {}
    for member in members:
        # Skips hidden values
        if not hidden:
            if member[0] != "_":
                result[member] = handelTypes(getattr(_class,member))
        else:
            result[member] = handelTypes(getattr(_class,member))
    return result

def unicodeEscapeDict(dictVar):
    resultItem = {}
    for key, value in dictVar.items():
        newKey = key.replace(".","\\u002E").replace("$","\\u0024")
        if type(value) is dict:
            resultItem[newKey] = unicodeEscapeDict(value)
        else:
            resultItem[newKey] = value
    return resultItem

def unicodeUnescapeDict(dictVar):
    resultItem = {}
    for key, value in dictVar.items():
        newKey = key.replace("\\u002E",".").replace("\\u0024","$")
        if type(value) is dict:
            resultItem[newKey] = unicodeUnescapeDict(value)
        else:
            resultItem[newKey] = value
    return resultItem

def unicodeUnescape(var):
    return var.replace("\\u002E",".").replace("\\u0024","$")

def locateModel(classType,modelType):
    # Check Core Model First
    try:
        mod = __import__("core.models.{0}".format(classType), fromlist=["_{0}".format(classType)])
        class_ = getattr(mod, "_{0}".format(classType))
        if class_ in modelType:
            return class_
    except ModuleNotFoundError:
        pass
    # Check Plugins Second
    plugins = os.listdir("plugins")
    # Look in all plugin folders
    for plugin in plugins:
        models = os.listdir(Path("plugins/{0}/models".format(plugin)))
        # Looking in all .py files within models dir
        for model in models:
            if len(model) > 3:
                if model[-3:] == ".py":
                    # Bruteforce attempt to load classType within model file
                    try:
                        mod = __import__("plugins.{0}.models.{1}".format(plugin,model[:-3]), fromlist=["_{0}".format(classType)])
                        class_ = getattr(mod, "_{0}".format(classType))
                        # Check that loaded class base ( parent class ) is within supplied ( expected ) modelType
                        if class_.__bases__[0] in modelType:
                            return class_
                    except ModuleNotFoundError:
                        pass
                    except AttributeError:
                        pass
    return None

# Reloads all loaded moduels - NOT WORKING!
def reload():
    import sys
    import importlib
    for moduleItem in sys.modules["__main__"].__dict__.items():
        if len(moduleItem) == 2:
            if type(moduleItem[1]) is types.ModuleType:
                importlib.reload(moduleItem[1])

apiURL = "http://{0}:{1}/{2}".format(settings.config["api"]["core"]["bind"],settings.config["api"]["core"]["port"],settings.config["api"]["core"]["base"])
def apiCall(methord,apiEndpoint,jsonData=None):
    url = "{0}/{1}".format(apiURL,apiEndpoint)
    if methord == "GET":
        response = requests.get(url,proxies=settings.config["api"]["proxy"])
    elif methord == "POST":
        response = requests.post(url,json=jsonData,proxies=settings.config["api"]["proxy"])
    elif methord == "DELETE":
        response = requests.delete(url,proxies=settings.config["api"]["proxy"])
    return response

def isBase64(s):
    if len(s) == 88 and s[-2:] == "==":
        try:
            enc = base64.b64encode(base64.b64decode(s)).decode()
            return enc == s
        except base64.binascii.Error:
            pass
    return False


def getObjectMemoryUsage(obj):
    BLACKLIST = type, ModuleType, FunctionType
    """sum size of object & members."""
    if isinstance(obj, BLACKLIST):
        raise TypeError('getsize() does not take argument of type: '+ str(type(obj)))
    seen_ids = set()
    size = 0
    objects = [obj]
    while objects:
        need_referents = []
        for obj in objects:
            if not isinstance(obj, BLACKLIST) and id(obj) not in seen_ids:
                seen_ids.add(id(obj))
                size += sys.getsizeof(obj)
                need_referents.append(obj)
        objects = get_referents(*need_referents)
    return size