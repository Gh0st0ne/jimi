import json
import  uuid

from flask import Flask, request, render_template, make_response, redirect

from core import api, model, db

from core.models import trigger, action, conduct, webui

@api.webServer.route("/conductEditor/", methods=["GET"])
def editConduct():
    return render_template("conductEditor.html")

@api.webServer.route("/conductEditor/<conductID>/", methods=["POST"])
def conductFlowchartPoll(conductID):
    conductObj = conduct._conduct().query(api.g["sessionData"],id=conductID)["results"]
    if len(conductObj) == 1:
        conductObj = conductObj[0]
    else:
        return {},404
    data = json.loads(api.request.data)

    lastPollTime = data["lastPollTime"]
    flowchartOperators = data["operators"]
    flowchartLinks = data["links"]

    flowchartResponse = { "operators" : { "delete" : {}, "create" : {}, "update" : {} }, "links" : { "delete" : {}, "create" : {}, "update" : {} } }

    # Getting all UI flow details for flows in this conduct
    flows = [ x for x in conductObj["flow"] ]
    flowsList = [ x["flowID"] for x in flows ]
    linksList = []
    flowsUI = webui._modelUI().getAsClass(api.g["sessionData"],query={ "flowID" : { "$in" :flowsList }, "conductID" : conductID, "lastUpdateTime" : { "$gt" : lastPollTime } })

    objectsToLoad = { "trigger" : {}, "action" : {} }
    for flow in flows:
        if "type" in flow:
            flowType = flow["type"]
            if "subtype" in flow:
                flowSubtype = flow["subtype"]
            else:
                flowSubtype = ""
            if "{0}{1}".format(flowType,"ID") in flow:
                objectID = "{0}{1}".format(flowType,"ID")
                flowID = flow["flowID"]
                # Default to create
                flowchartResponseType = "create"
                if flowID in flowchartOperators:
                    # If it already exits then its an update
                    flowchartResponseType = "update"
                # Setting position if it has changed since last pollTime
                foundFlowUI = False
                for flowUI in flowsUI:
                    if flow["flowID"] == flowUI.flowID:
                        flowchartResponse["operators"][flowchartResponseType][flowID] = { "_id" : flow[objectID], "flowID" : flowID, "flowType" : flowType, "flowSubtype" : flowSubtype, "title" : flowUI.title, "x" : flowUI.x, "y" : flowUI.y }
                        foundFlowUI = True
                        break
                if flowchartResponseType == "create":
                    if not foundFlowUI:
                        tempFlowUI = webui._modelUI().getAsClass(api.g["sessionData"],query={ "flowID" : flowID, "conductID" : conductID })
                        if len(tempFlowUI) == 1:
                            tempFlowUI = tempFlowUI[0]
                            flowchartResponse["operators"][flowchartResponseType][flowID] = { "_id" : flow[objectID], "flowID" : flowID, "flowType" : flowType, "flowSubtype" : flowSubtype, "title" : tempFlowUI.title, "x" : tempFlowUI.x, "y" : tempFlowUI.y }
                # Do any links need to be created
                for nextFlow in flow["next"]:
                    linkName = "{0}->{1}".format(flowID,nextFlow["flowID"])
                    linksList.append(linkName)
                    if linkName not in flowchartLinks:
                        flowchartResponse["links"]["create"][linkName] = { "from" : flowID, "to" : nextFlow["flowID"], "logic" : nextFlow["logic"] }
                    #Updates (for logic for now)
                    flowchartResponse["links"]["update"][linkName] = { "from" : flowID, "to" : nextFlow["flowID"], "logic" : nextFlow["logic"] }


    # Checking for deleted operators
    for flowchartOperator in flowchartOperators:
        if flowchartOperator not in flowsList:
            flowchartResponse["operators"]["delete"][flowchartOperator] = { "flowID" : flowchartOperator }
    # Checking for deleted links
    for flowchartLink in flowchartLinks:
        if flowchartLink not in linksList:
            flowchartResponse["links"]["delete"][flowchartLink] = { "linkName" : flowchartLink }

    return flowchartResponse, 200

@api.webServer.route("/conductEditor/<conductID>/", methods=["GET"])
def getConduct(conductID):
    conductObj = conduct._conduct().query(api.g["sessionData"],id=conductID)["results"]
    if len(conductObj) == 1:
        conductObj = conductObj[0]
    else:
        return {},404

    # Getting all UI flow details for flows in this conduct
    flows = [ x["flowID"] for x in conductObj["flow"] ]
    flowsUI = webui._modelUI().getAsClass(api.g["sessionData"],query={ "flowID" : { "$in" :flows }, "conductID" : conductID })

    objectsToLoad = { "trigger" : [], "action" : [] }
    objects = {}
    for flow in conductObj["flow"]:
        if "type" in flow:
            flowType = flow["type"]
            if "{0}{1}".format(flowType,"ID") in flow:
                # Creating array of tigger and action so we can do one massive DB query
                objectsToLoad[flowType].append(db.ObjectId(flow["{0}{1}".format(flowType,"ID")]))
                # Creating objects dict
                objects[flow["{0}{1}".format(flowType,"ID")]] = {}
                objects[flow["{0}{1}".format(flowType,"ID")]]["_id"] = flow["{0}{1}".format(flowType,"ID")]
                objects[flow["{0}{1}".format(flowType,"ID")]]["flowType"] = flowType
                objects[flow["{0}{1}".format(flowType,"ID")]]["flowID"] = flow["flowID"]
                objects[flow["{0}{1}".format(flowType,"ID")]]["next"] = flow["next"]
                # Setting default name encase no name is set
                objects[flow["{0}{1}".format(flowType,"ID")]]["name"] = flow["flowID"]
                # Checking if we have a flowUI for the current flowID if so add to objects array, or keep as default
                objects[flow["{0}{1}".format(flowType,"ID")]]["ui"] = { "x" : 0, "y" : 0, "title" : "" }
                for flowUI in flowsUI:
                    if flowUI.flowID == flow["flowID"]:
                        # Overriding defaults with values loaded from the database
                        objects[flow["{0}{1}".format(flowType,"ID")]]["ui"]["x"] = flowUI.x
                        objects[flow["{0}{1}".format(flowType,"ID")]]["ui"]["y"] = flowUI.y
                        objects[flow["{0}{1}".format(flowType,"ID")]]["ui"]["title"] = flowUI.title
                        if objects[flow["{0}{1}".format(flowType,"ID")]]["ui"]["title"] == "":
                            if flowType == "trigger":
                                modelObject = trigger._trigger().getAsClass(api.g["sessionData"],id=objects[flow["{0}{1}".format(flowType,"ID")]]["_id"])[0]
                            elif flowType == "action":
                                modelObject = action._action().getAsClass(api.g["sessionData"],id=objects[flow["{0}{1}".format(flowType,"ID")]]["_id"])[0]
                            flowUI.title = modelObject.name
                            objects[flow["{0}{1}".format(flowType,"ID")]]["ui"]["title"] = modelObject.name
                            flowUI.update(["title"])
                        break

    return objects, 200

@api.webServer.route("/conductEditor/<conductID>/flow/<flowID>/", methods=["DELETE"])
def deleteFlow(conductID,flowID):
    conductObj = conduct._conduct().getAsClass(api.g["sessionData"],id=conductID)
    if len(conductObj) == 1:
        conductObj = conductObj[0]
    else:
        return { }, 404
    flow = [ x for x in conductObj.flow if x["flowID"] ==  flowID]
    if len(flow) == 1:
        flow = flow[0]
        for flowItemsValue in conductObj.flow:
            for nextflowValue in flowItemsValue["next"]:
                if nextflowValue["flowID"] == flowID:
                    conductObj.flow[conductObj.flow.index(flowItemsValue)]["next"].remove(nextflowValue)
        conductObj.flow.remove(flow)
        conductObj.update(["flow"])
        return { }, 200
    else:
        return { }, 404

@api.webServer.route("/conductEditor/<conductID>/flow/", methods=["PUT"])
def newFlow(conductID):
    conductObj = conduct._conduct().getAsClass(api.g["sessionData"],id=conductID)
    if len(conductObj) == 1:
        conductObj = conductObj[0]
    else:
        return { }, 404

    access, accessIDs, adminBypass = db.ACLAccess(api.g["sessionData"],conductObj.acl,"write")
    if access:
        data = json.loads(api.request.data)
        # Get new UUID store within current conduct flow and return UUID
        newFlowID = str(uuid.uuid4())
        flow = {
            "flowID" : newFlowID, 
            "next" : []
        }
        # Creating new object of model type
        _class = model._model().getAsClass(api.g["sessionData"],id=data["classID"])
        if _class:
            subtype = _class[0].name
            _class = _class[0].classObject()
            newFlowObjectID = _class().new(flow["flowID"]).inserted_id
            # Working out by bruteforce which type this is ( try and load it by parent class and check for error) - get on trigger if it does not exist will return None
            modelFlowObjectType = "action"
            if len(trigger._trigger().getAsClass(api.g["sessionData"],id=newFlowObjectID)) > 0:
                modelFlowObjectType = "trigger"
            modelFlowObject = _class().getAsClass(api.g["sessionData"],id=newFlowObjectID)
            if len(modelFlowObject) == 1:
                modelFlowObject = modelFlowObject[0]
            else:
                return { }, 404
            modelFlowObject.acl = { "ids" : [ { "accessID" : api.g["sessionData"]["primaryGroup"], "read" : True, "write" : True, "delete" : True } ] }
            modelFlowObject.update(["acl"])
            flow["type"] = modelFlowObjectType
            if subtype != "action" and subtype != "trigger":
                flow["subtype"] = subtype
            flow["{0}{1}".format(modelFlowObjectType,"ID")] = str(newFlowObjectID)
            # Adding UI position for cloned object
            webui._modelUI().new(conductID,conductObj.acl,flow["flowID"],data["x"],data["y"],modelFlowObject.name)
            # Appending new object to conduct
            conductObj.flow.append(flow)
            conductObj.update(["flow"])
            return { }, 201
    else:
        return { }, 403

    return { }, 404
    
@api.webServer.route("/conductEditor/<conductID>/flow/", methods=["POST"])
def dropExistingObject(conductID):
    conductObj = conduct._conduct().getAsClass(api.g["sessionData"],id=conductID)
    if len(conductObj) == 1:
        conductObj = conductObj[0]
    else:
        return { }, 404
    access, accessIDs, adminBypass = db.ACLAccess(api.g["sessionData"],conductObj.acl,"write")
    if access:
        data = json.loads(api.request.data)
        if data["action"] == "drop":
            newFlowID = str(uuid.uuid4())
            flow = {
                "flowID" : newFlowID, 
                "type" : data["flowType"],
                "{0}{1}".format(data["flowType"],"ID") : data["_id"],
                "next" : []
            }
            modelFlowObject = None
            if data["flowType"] == "trigger":
                modelFlowObject = trigger._trigger().getAsClass(api.g["sessionData"],id=data["_id"])[0]
            elif data["flowType"] == "action":
                modelFlowObject = action._action().getAsClass(api.g["sessionData"],id=data["_id"])[0]
            if modelFlowObject:
                name = modelFlowObject.name
            else:
                name = flow["flowID"]

            webui._modelUI().new(conductID,conductObj.acl,flow["flowID"],data["x"],data["y"],name)
            conductObj.flow.append(flow)
            conductObj.update(["flow"])
            return { }, 201
    return { }, 404

@api.webServer.route("/conductEditor/<conductID>/flow/<flowID>/", methods=["POST"])
def updateFlow(conductID,flowID):
    conductObj = conduct._conduct().getAsClass(api.g["sessionData"],id=conductID)
    if len(conductObj) == 1:
        conductObj = conductObj[0]
    else:
        return { }, 404

    flow = [ x for x in conductObj.flow if x["flowID"] ==  flowID]
    if len(flow) == 1:
        flow = flow[0]
        data = json.loads(api.request.data)
        if data["action"] == "update":
            access, accessIDs, adminBypass = db.ACLAccess(api.g["sessionData"],conductObj.acl,"write")
            if access:
                if "x" in data and "y" in data:
                    try:
                        x = int(data["x"])
                        y = int(data["y"])
                    except:
                        return { }, 403
                flowUI = webui._modelUI().getAsClass(api.g["sessionData"],query={ "flowID" : flow["flowID"], "conductID" : conductID })
                if len(flowUI) == 1:
                    flowUI = flowUI[0]
                    if "x" in data and "y" in data:
                        flowUI.x = x
                        flowUI.y = y
                        flowUI.update(["x","y"])
                    if "title" in data:
                        flowUI.title = data["title"]
                        flowUI.update(["title"])
                    return { }, 200
                else:
                    webui._modelUI().new(conductID,conductObj.acl,flow["flowID"],x,y)
                    return { }, 201
        elif data["action"] == "copy":
            access, accessIDs, adminBypass = db.ACLAccess(api.g["sessionData"],conductObj.acl,"write")
            if access:
                flow = [ x for x in conductObj.flow if x["flowID"] ==  data["operatorId"]]
                if len(flow) == 1:
                    flow = flow[0]
                    newFlowID = str(uuid.uuid4())
                    newFlow = {
                        "flowID" : newFlowID, 
                        "type" : flow["type"],
                        "{0}{1}".format(flow["type"],"ID") : flow["{0}{1}".format(flow["type"],"ID")],
                        "next" : []
                    }
                    flowUI = webui._modelUI().getAsClass(api.g["sessionData"],query={ "flowID" : flow["flowID"], "conductID" : conductID })[0]
                    webui._modelUI().new(conductID,conductObj.acl,newFlow["flowID"],data["x"],data["y"],flowUI.title)
                    conductObj.flow.append(newFlow)
                    conductObj.update(["flow"])
                    return { }, 201
        elif data["action"] == "clone":
            access, accessIDs, adminBypass = db.ACLAccess(api.g["sessionData"],conductObj.acl,"write")
            if access:
                flow = [ x for x in conductObj.flow if x["flowID"] ==  data["operatorId"]]
                if len(flow) == 1:
                    flow = flow[0]
                    data = json.loads(api.request.data)
                    modelFlowObject = None
                    # Check if the modelType and object are unchanged
                    if "type" in flow:
                        if flow["type"] == "trigger":
                            modelFlowObject = trigger._trigger().getAsClass(api.g["sessionData"],id=flow["{0}{1}".format(flow["type"],"ID")])
                            if len(modelFlowObject) == 1:
                                modelFlowObject = modelFlowObject[0]
                            modelFlowObjectType = "trigger"
                        if flow["type"] == "action":
                            modelFlowObject = action._action().getAsClass(api.g["sessionData"],id=flow["{0}{1}".format(flow["type"],"ID")])
                            if len(modelFlowObject) == 1:
                                modelFlowObject = modelFlowObject[0]
                            modelFlowObjectType = "action"

                        # Was it possible to load an existing object
                        if modelFlowObject:
                            # Create new flowItem
                            newFlowID = str(uuid.uuid4())
                            flow = {
                                "flowID" : newFlowID, 
                                "type" : flow["type"],
                                "next" : []
                            }
                            # New object required
                            _class = model._model().getAsClass(api.g["sessionData"],id=modelFlowObject.classID)
                            if _class:
                                _class = _class[0].classObject()
                                # Bug exists as name value is not requried by db class but is for core models - this could result in an error if new model is added that does not accept name within new function override
                                newFlowObjectID = _class().new(flow["flowID"]).inserted_id

                                # Working out by bruteforce which type this is ( try and load it by parent class and check for error) - get on trigger if it does not exist will return None
                                modelFlowObjectClone = _class().getAsClass(api.g["sessionData"],id=newFlowObjectID)
                                if len(modelFlowObjectClone) == 1:
                                    modelFlowObjectClone = modelFlowObjectClone[0]
                                else:
                                    return { }, 404

                                # Setting values in cloned object
                                members = [attr for attr in dir(modelFlowObject) if not callable(getattr(modelFlowObject, attr)) and not "__" in attr and attr ]
                                dontCopy=["_id","name"]
                                updateList = []
                                for member in members:
                                    if member not in dontCopy:
                                        setattr(modelFlowObjectClone,member,getattr(modelFlowObject,member))
                                        updateList.append(member)
                                modelFlowObjectClone.update(updateList)

                                # Set conduct flow to correct type and objectID
                                flow["{0}{1}".format(flow["type"],"ID")] = str(newFlowObjectID)
                                conductObj.flow.append(flow)

                                # Adding UI position for cloned object
                                flowUI = webui._modelUI().getAsClass(api.g["sessionData"],query={ "flowID" : flowID, "conductID" : conductID })[0]
                                webui._modelUI().new(conductID,conductObj.acl,flow["flowID"],data["x"],data["y"],"Copy - {0}".format(flowUI.title))
                                conductObj.update(["flow"])
                                return { "result" : True}, 201
    return { }, 404

@api.webServer.route("/conductEditor/<conductID>/flowLink/<fromFlowID>/<toFlowID>/", methods=["PUT"])
def newFlowLink(conductID,fromFlowID,toFlowID):
    conductObj = conduct._conduct().getAsClass(api.g["sessionData"],id=conductID)
    if len(conductObj) == 1:
        conductObj = conductObj[0]
    else:
        return { }, 404
    access, accessIDs, adminBypass = db.ACLAccess(api.g["sessionData"],conductObj.acl,"write")
    if access:
        fromFlow = [ x for x in conductObj.flow if x["flowID"] ==  fromFlowID][0]
        toFlow = [ x for x in conductObj.flow if x["flowID"] ==  toFlowID][0]
        nextFlows = [ x for x in fromFlow["next"] if x["flowID"] ==  toFlowID]
        if len(nextFlows) == 0:
            if toFlow["type"] != "trigger":
                fromFlow["next"].append({ "flowID" : toFlowID, "logic": True })
                conductObj.update(["flow"])
                return { }, 201
            else:
                return { }, 403
        return { }, 200
    else:
        return { }, 403

@api.webServer.route("/conductEditor/<conductID>/flowLink/<fromFlowID>/<toFlowID>/", methods=["DELETE"])
def deleteFlowLink(conductID,fromFlowID,toFlowID):
    conductObj = conduct._conduct().getAsClass(api.g["sessionData"],id=conductID)
    if len(conductObj) == 1:
        conductObj = conductObj[0]
    else:
        return { }, 404
    access, accessIDs, adminBypass = db.ACLAccess(api.g["sessionData"],conductObj.acl,"write")
    if access:
        fromFlow = [ x for x in conductObj.flow if x["flowID"] ==  fromFlowID][0]
        for nextflow in fromFlow["next"]:
            if nextflow["flowID"] == toFlowID:
                conductObj.flow[conductObj.flow.index(fromFlow)]["next"].remove(nextflow)
                conductObj.update(["flow"])
                return { }, 200
        return { }, 404
    else:
        return {}, 403
