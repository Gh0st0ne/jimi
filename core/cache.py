import time

from core import helpers, logging

class _cache():
    objects = dict()

    def newCache(self,cacheName,maxSize=10485760,cacheExpiry=60,sessionData=None):
        userID = None
        if sessionData:
            if "_id" in sessionData:
                userID = sessionData["_id"]
                cacheName = "{0},-,{1}".format(userID,cacheName)
        if cacheName not in self.objects:
            self.objects[cacheName] = { "objects" : {}, "maxSize" : maxSize, "cacheExpiry" : cacheExpiry, "userID" : userID }
            logging.debug("New cache store created, name={0}, maxSize={1}, cacheExpry={2}, userID={3}".format(cacheName,maxSize,cacheExpiry,userID),20)

    def clearCache(self,cacheName,sessionData=None):
        authedCacheName = self.checkSessionData(cacheName,sessionData)
        if authedCacheName == None:
            return
        if cacheName == "ALL":
            for cacheName, cacheValue in self.objects.items():
                self.objects[cacheName]["objects"].clear()
        elif authedCacheName in self.objects:
            self.objects[authedCacheName]["objects"].clear()
            logging.debug("Cache store cleared, name={0}".format(authedCacheName),20)

    def get(self,cacheName,uid,setFunction,*args,sessionData=None,extendCacheTime=False,forceUpdate=False):
        authedCacheName = self.checkSessionData(cacheName,sessionData)
        if authedCacheName == None:
            return
        now = time.time()
        if ((uid in self.objects[authedCacheName]["objects"]) and (not forceUpdate)):
            if ((self.objects[authedCacheName]["objects"][uid]["cacheExpiry"] > now) or (extendCacheTime)):
                self.objects[authedCacheName]["objects"][uid]["accessCount"] += 1
                if extendCacheTime:
                    self.objects[authedCacheName]["objects"][uid]["cacheFor"] =  ( now + self.objects[authedCacheName]["cacheExpiry"] )
                return self.objects[authedCacheName]["objects"][uid]["objectValue"]
        cache, objectValue = self.getObjectValue(cacheName,uid,setFunction,*args,sessionData=sessionData)
        if cache and objectValue:
            if uid in self.objects[authedCacheName]["objects"]:
                self.objects[authedCacheName]["objects"][uid]["objectValue"] = objectValue
                self.objects[authedCacheName]["objects"][uid]["cacheExpiry"] = (now + self.objects[authedCacheName]["cacheExpiry"])
                self.objects[authedCacheName]["objects"][uid]["accessCount"] += 1
            else:
                self.objects[authedCacheName]["objects"][uid] = { "objectValue" : objectValue, "accessCount" : 0, "cacheExpiry" : (now + self.objects[authedCacheName]["cacheExpiry"]) }
        if objectValue:
            return objectValue
        else:
            return None

    def getObjectValue(self,cacheName,uid,setFunction,*args,sessionData=None):
        authedCacheName = self.checkSessionData(cacheName,sessionData)
        if cacheName == None:
            return
        if len(args) > 0:
            newObject = setFunction(uid,sessionData,*args)
        else:
            newObject = setFunction(uid,sessionData)
        newObjectSize = helpers.getObjectMemoryUsage(newObject)
        currentCacheSzie = helpers.getObjectMemoryUsage(self.objects[authedCacheName]["objects"])
        memoryNeeded = (currentCacheSzie + newObjectSize) - self.objects[authedCacheName]["maxSize"]
        if memoryNeeded > 0:
            if not self.reduceSize(cacheName,memoryNeeded,sessionData=sessionData):
                logging.debug("ERROR - Cache store full and unable to free enough space for new object, name={0}".format(authedCacheName),5)
                return (False, newObject)
        return (True, newObject)

    def reduceSize(self,cacheName,amountToFree,sessionData=None):
        authedCacheName = self.checkSessionData(cacheName,sessionData)
        if authedCacheName == None:
            return
        logging.debug("Cache store attempting to reduce memory, name={0}, amount={1}".format(authedCacheName,amountToFree),20)
        # No objects to clear
        if len(self.objects[authedCacheName]["objects"]) == 0:
            return False
        
        now = time.time()
        amountReduced = 0
        poplist = []
        accessCount = {}
        for cacheObjectKey, cacheObjectValue in self.objects[authedCacheName]["objects"].items():
            if cacheObjectValue["cacheExpiry"] < now:
                amountReduced += helpers.getObjectMemoryUsage(cacheObjectValue)
                poplist.append(cacheObjectKey)
            else:
                if cacheObjectValue["accessCount"] not in accessCount:
                    accessCount[cacheObjectValue["accessCount"]] = []
                accessCount[cacheObjectValue["accessCount"]].append(cacheObjectKey)
            if amountReduced >= amountToFree:
                break
        if amountReduced < amountToFree:
            for count in accessCount.keys():
                for item in accessCount[count]:
                    amountReduced += helpers.getObjectMemoryUsage(self.objects[authedCacheName]["objects"][item])
                    poplist.append(item)
                    if amountReduced >= amountToFree:
                        break
                if amountReduced >= amountToFree:
                    break

        for item in poplist:
            del self.objects[authedCacheName]["objects"][item]

        if amountReduced >= amountToFree:
            return True

        return False

    def checkSessionData(self,cacheName,sessionData):
        if sessionData:
            authedCacheName = "{0},-,{1}".format(sessionData["_id"],cacheName)
            if sessionData["_id"] == self.objects[authedCacheName]["userID"]:
                return authedCacheName
            else:
                logging.debug("ERROR - Cache store access denied due to mismatched ID, name={0}, userID={1}".format(cacheName,sessionData["_id"]),5)
                return None
        else:
            return cacheName
        return None

    def getSummary(self):
        result = ""
        totalSize = 0
        for cacheName, cacheValue in self.objects.items():
            cacheSzie = helpers.getObjectMemoryUsage(cacheValue)
            totalSize+=cacheSzie
            result+="name='{0}', size='{1}'\r\n".format(cacheName,cacheSzie)
        result+="\r\n\r\nTotal Size='{0}'".format(totalSize)
        return result

globalCache = _cache()