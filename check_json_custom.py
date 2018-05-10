#! /usr/bin/env python
# Hacked by j0nix 2017
# Custom check for OSS systems that can report status @ http://<osssystem>/_status
# Expects a json reply formated like below, otherwise you need to rehack this shit
#{
#  "status": "OK",
#  "message": "All is good",
#  "probes": [
#    {
#      "name": "runtime",
#      "message": "3708640144 bytes of total free (unused+unallocated) memory, max is 5726797824 bytes",
#      "status": "OK",
#      "details": {
#        "availableProcessors": 2,
#        "freeMemory": 894786448,
#        "maxMemory": 5726797824,
#        "totalMemory": 2912944128
#      }
#    }
#    ]
#}
import urllib2
import simplejson
import sys
from optparse import OptionParser

class nagios:
    ok       = (0, 'OK')
    warning  = (1, 'WARNING')
    critical = (2, 'CRITICAL')
    unknown  = (3, 'UNKNOWN')

def exit(status, message):
    print status[1] + ' - ' + message
    sys.exit(status[0])

usage = 'usage: %prog -f status_field -u https://status-url'
parser = OptionParser(description="Custom check-script for OSS status pages", usage=usage)
parser.add_option("-u", "--url", dest="uri", help="url to json status page", default=None)
parser.add_option("-f", "--field", dest="field", help="field holding status value", default="status")
parser.add_option("-p", "--probe", dest="probe", help="probe to check", default=None)
(options, args) = parser.parse_args()

if options.uri is None:
    parser.error('Missing status url')

field = options.field
uri = options.uri
probe = options.probe

try:
    j = simplejson.load(urllib2.urlopen(uri)) # Go get JSON data
except urllib2.HTTPError, ex:
    exit(nagios.unknown, 'invalid url ' + uri)
except urllib2.URLError:
    exit(nagios.unknown, 'invalid url ' + uri)

if probe:
	for p in j['probes']:
		if p['name'] == probe:
			if field not in p:
				exit(nagios.unknown, 'field "' + field + '" for probe ' + probe + ' is not present in json reply')
			# Validate field value
			if j[field] == "OK":
    				exit(nagios.ok, probe + ", " + j['message'])
			elif j[field] == 'WARNING':
    				exit(nagios.warning, probe + ", " + j['message'])
			elif j[field] == 'CRITICAL':
    				exit(nagios.critical, probe + ", " + j['message'])
			elif j[field] == 'ERROR':
				exit(nagios.critical, probe + ", " + j['message'])
			else:
    				exit(nagios.unknown, probe + ", " + j['message'])
	# We did not match included probe name for any probe reported from url
	exit(nagios.unknown, 'probe "' + probe + '" is not present in json reply')
			
else:
	if field not in j:
		exit(nagios.unknown, 'field "' + field + '" is not present in json reply')
	# Validate field value
	if j[field] == "OK":
	    exit(nagios.ok, j['message'])
	elif j[field] == 'WARNING':
	    exit(nagios.warning, j['message'])
	elif j[field] == 'CRITICAL':
	    exit(nagios.critical, j['message'])
	elif j[field] == 'ERROR':
	    exit(nagios.critical, j['message'])
	else:
	    exit(nagios.unknown, j['message'])
# j0nixRulez
