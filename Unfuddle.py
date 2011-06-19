import simplejson as json
import os
import sys
import urllib
import urllib2
from datetime import datetime, timedelta

account  = ''
username = ''
password = ''
base     = ''

class UnfuddleError(Exception):
	def __init__(self, value):
		self.value = value
	def __repr__(self):
		return repr(self.value)
	def __str__(self):
		return str(self.value)

class Account(dict):
	def __init__(self, acct, user, passwd):
		global account
		global username
		global password
		global base
		account  = acct
		username = user
		password = passwd
		base     = "http://%s.unfuddle.com/api/v1/" % account
		response = get('initializer')
		self['projects'] = dict([(p['title'   ], Project(p)) for p in response['projects']])
		self['people'  ] = dict([(p['username'], Person(p) ) for p in response['people'  ]])
		self.update(response['account'])
	
	def activity(self, start = datetime.now(), end = (datetime.now() - timedelta(weeks=2)), limit = 20):
		return get("account/activity", {'request':{'start-date':start, 'end-date':end, 'limit':limit}})
	
	def formatter(self, text, markup):
		return post("account/formatter", {'request':{'text':text, 'markup':markup}})
	
	def reset_access_keys(self):
		return put("account/reset_access_keys")
	
	def search(self, query, start = 0, end = 10, limit = 10, flt = 'changesets,comments,messages,milestones,notebooks,tickets'):
		return get("account/search/", {'request' : {'query':query, 'start-index':start, 'end-index':end, 'limit':limit, 'filter':flt}})
	
	def projects(self):
		self['projects'] = [Project(p) for p in get('projects/')]
		return self['projects']
	
	def people(self):
		self['people'] = [Person(p) for p in get('people/')]
		return self['people']
	
	def currentPerson(self):
		return Person(get('people/current/'))
	
	def milestones(self):
		self['milestones'] = [Milestone(m) for m in get('milestones/')]
		return self['milestones']
	
class Project(dict):
	def __init__(self, d):
		self.update(d)
		self.base = "projects/%i/" % d['id']
	
	def activity(self, start = datetime.now(), end = (datetime.now() - timedelta(weeks=2)), limit = 20):
		return get(self.base + "activity", {'request':{'start-date':start, 'end-date':end, 'limit':limit}})
	
	def search(self, query, start = 0, end = 10, limit = 10, flt = 'changesets,comments,messages,milestones,notebooks,tickets'):
		return get(self.base + "search/", {'request' : {'query':query, 'start-index':start, 'end-index':end, 'limit':limit, 'filter':flt}})
	
	def dump(self):
		# Doesn't work -- only return XML
		return get(self.base + "dump/")
	
	def versions(self):
		return get(self.base + "versions/")

class Person(dict):
	def __init__(self, d):
		self.update(d)
		self.base = "people/%i/" % d['id']

class Milestone(dict):
	@staticmethod
	def upcoming():
		return [Milestone(m) for m in get('milestones/upcoming')]
	
	@staticmethod
	def late():
		return [Milestone(m) for m in get('milestones/late')]
	
	@staticmethod
	def completed():
		return [Milestone(m) for m in get('milestones/completed')]
	
	@staticmethod
	def archived():
		return [Milestone(m) for m in get('milestones/archived')]
	
	def __init__(self, d):
		self.update(d)
		self.base = "projects/%i/milestones/%i/" % (d['project_id'], d['id'])
	
def toXML(d):
	if isinstance(d, dict):
		output = ''
		for key, value in d.items():
			output += "<%(key)s>%(value)s</%(key)s>" % ({'key':key, 'value':toXML(value)})
		return output
	elif isinstance(d, datetime):
		return d.strftime("%Y/%m/%d")
	else:
		return d

def get(apiEndPoint, data = None):
	# From the Unfuddle API documentation
	if (data == None):
		return post(apiEndPoint)
	else:
		data = toXML(data)
		return post(apiEndPoint + "?" + urllib.quote(data))

def post(apiEndPoint, data = None):
	url = base + apiEndPoint
	
	manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
	manager.add_password(None, url, username, password)
	handler = urllib2.HTTPBasicAuthHandler(manager)
	
	opener = urllib2.build_opener()
	opener.add_handler(handler)
	
	req = urllib2.Request(url, toXML(data), headers = {'Content-Type': 'application/xml', 'Accept' : 'application/json'})
	
	try:
		res = opener.open(req).read().strip()
		if len(res):
			obj = json.loads(res)
			if ('error' in obj):
				raise UnfuddleError(obj['error'])
			return obj
		else:
			return None
	except (IOError, KeyError, TypeError, json.decoder.JSONDecodeError) as err:
		raise UnfuddleError(str(err))

def put(apiEndPoint, data=None):
	url = base + apiEndPoint
	opener = urllib2.build_opener(urllib2.HTTPHandler)
	request = urllib2.Request(url, data=toXML(data))
	request.add_header('Content-Type', 'application/xml')
	request.add_header('Accept', 'application/json')
	request.get_method = lambda: 'PUT'
	url = opener.open(request)

def getTickets(project):
	return get('projects/%s/tickets/' % project)

def makeTicket(project, description, title, priority=1):
	ticket  = "<ticket>"
	ticket += "<summary>%s</summary>" % title
	ticket += "<description>%s</description>" % description
	ticket += "<priority>%i</priority>" % priority
	ticket += "</ticket>"
	return post('projects/%s/tickets' % project, ticket)
	
	# <ticket>
	#   <assignee-id type="integer"> </assignee-id>
	#   <component-id type="integer"> </component-id>
	#   <created-at type="datetime"> </created-at>
	#   <description> </description>
	#   <description-format> [markdown, textile, plain] </description-format>
	#   <description-formatted> <!-- only available if formatted=true --> </description-formatted>
	#   <due-on type="date"> </due-on>
	#   <due-on-formatted> </due-on-formatted>
	#   <field1-value-id="integer"> </field1-value-id>
	#   <field2-value-id="integer"> </field2-value-id>
	#   <field3-value-id="integer"> </field3-value-id>
	#   <hours-estimate-current type="float"> </hours-estimate-current>
	#   <hours-estimate-initial type="float"> </hours-estimate-initial>
	#   <id type="integer"> </id>
	#   <milestone-id type="integer"> </milestone-id>
	#   <number type="integer"> </number>
	#   <priority> [1, 2, 3, 4, 5] </priority>
	#   <project-id type="integer"> </project-id>
	#   <reporter-id type="integer"> </reporter-id>
	#   <resolution> [fixed, works_for_me, postponed, duplicate, will_not_fix, invalid] </resolution>
	#   <resolution-description> </resolution-description>
	#   <resolution-description-format> [markdown, textile, plain] </resolution-description-format>
	#   <resolution-description-formatted> <!-- only available if formatted=true --> </resolution-description-formatted>
	#   <severity-id type="integer"> </severity-id>
	#   <status> [new, unaccepted, reassigned, reopened, accepted, resolved, closed] </status>
	#   <summary> </summary>
	#   <updated-at type="datetime"> </updated-at>
	#   <version-id type="integer"> </version-id>
	# 
	# </ticket>