from flask import Flask, request, make_response, redirect, g
import _thread

from core import settings

base = "/api/1.0/"
webServer = None

def createServer(name, **kwargs):
	global webServer
	webServer = Flask(name,**kwargs)

def startServer(**kwargs):
	global webServer
	_thread.start_new_thread(webServer.run, (), kwargs)


