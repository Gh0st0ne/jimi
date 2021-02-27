import time

from core.models import action, conduct
from core import helpers, logging, cache, settings

import jimi

class _subFlow(jimi.action._action):
	triggerID = str()
	customEventsValue = False
	eventsValue = str()
	customEventsList = False
	eventsList = list()
	mergeFinalDataValue = False 

	def doAction(self,data):
		triggerID = jimi.helpers.evalString(self.triggerID,{"data" : data["flowData"]})

		events = [data["flowData"]["event"]]

		tempData = conduct.copyData(conduct.dataTemplate(data,keepEvent=True))
		tempData["flowData"]["callingTriggerID"] = data["flowData"]["trigger_id"]

		if self.customEventsValue:
			events = jimi.helpers.evalString(self.eventsValue,{"data" : data["flowData"]})
			if type(events) is not list:
				events = [events]
		if self.customEventsList:
			events = jimi.helpers.evalList(self.eventsList,{"data" : data["flowData"]})

		trigger = jimi.trigger._trigger().getAsClass(id=triggerID)
		if len(trigger) == 1:
			trigger = trigger[0]
			finalData = trigger.notify(events,tempData)
			if self.mergeFinalDataValue:
				data["flowData"]["event"] = finalData["flowData"]["event"]
				data["flowData"]["action"] = finalData["flowData"]["action"]
				data["flowData"]["var"] = finalData["flowData"]["var"]
				data["flowData"]["plugin"] = finalData["flowData"]["plugin"]
		else:
			return { "result" : False, "rc" : 5, "msg" : "Unable to find the specified triggerID={0}".format(triggerID) }

		return { "result" : True, "rc" : 0 }