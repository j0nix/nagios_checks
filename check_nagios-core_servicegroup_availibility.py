#! /usr/bin/python
# j0nix 2017

#import modules
import sys
import datetime
import time
from optparse import OptionParser
import urllib2
import requests
try:
    import json
except ImportError:
    import simplejson as json
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
"""
          "host_name": "lib-dns-anyres-1.comhem.com",
          "description": "DNS IMR IPv4 Resolver",
          "time_ok": 86400,
          "time_warning": 0,
          "time_critical": 0,
          "time_unknown": 0,
          "scheduled_time_ok": 0,
          "scheduled_time_warning": 0,
          "scheduled_time_critical": 0,
          "scheduled_time_unknown": 0,
          "time_indeterminate_nodata": 0,
          "time_indeterminate_notrunning": 0
"""
#NAGIOS return codes
RETURN_CODE = { "UNKNOWN":3,"OK":0,"WARNING":1,"CRITICAL":2}

# Parse options
def build_parser():
    parser = OptionParser()
    parser.add_option("-b", "--base_url", dest="base_url", help="Base url to your nagios json api", type="string")
    parser.add_option("-s", "--servicegroup", dest="servicegroup", help="Servicegroup to query", type="string")
    parser.add_option("-u", "--user", dest="username", help="Username for nagios", type="string", default=None)
    parser.add_option("-p", "--password", dest="password", help="Password for nagios", type="string",default=None)
    parser.add_option("-d", "--days", dest="days", help="Archived days to check avaylibility", type="int")
    parser.add_option("-w", "--warn", dest="warning", help="Alert when below or equal to float between 0 and 1, default 0.9999", type="float", default=0.9999)
    parser.add_option("-c", "--crit", dest="critical", help="Alert when below or equal to float 0 and 1, default 0.9990", type="float",default=0.9990)
    parser.add_option("--debug", dest="debug", help="Enable debug", action="store_true")
    return parser

def validate_args(p,o):

    if not o.base_url:
        p.error("-b/--base_url is required")
        sys.exit(RETURN_CODE['UNKNOWN'])

    if not o.servicegroup:
        p.error("-s/--servicegroup is required")
        sys.exit(RETURN_CODE['UNKNOWN'])


    o.warning = round(o.warning,4)
    o.critical = round(o.critical,4)

    if o.warning == o.critical:
	p.error("warning & critical can't be the same value. Note that limit is set to 4")
        sys.exit(RETURN_CODE['UNKNOWN'])

    if o.warning < o.critical:
	p.error("warning can't be less than critical. Note that limit is set to 4")
        sys.exit(RETURN_CODE['UNKNOWN'])

    return o.warning,o.critical

# Your magic check funktion
def check(options):

	SSL_VERIFY = False
  	dpattern = '%Y-%m-%d %H:%M:%S'
	now = datetime.datetime.now()
  	endtime = int(time.mktime(time.strptime(now.strftime(dpattern), dpattern)))
  	starttime = endtime - (86400*int(options.days))

	uri = "{0}/cgi-bin/archivejson.cgi?query=availability&availabilityobjecttype=servicegroups&statetypes=hard&servicegroup={1}&assumeinitialstate=true&assumestateretention=true&assumestatesduringnagiosdowntime=true&assumedinitialhoststate=up&assumedinitialservicestate=ok&starttime={2}&endtime={3}".format(options.base_url,options.servicegroup,starttime,endtime)

	if options.debug:
		print "\r\nDEBUG::check:uri:\n\r%s" % uri

	if options.username == None:
        	response = requests.get(uri, verify=SSL_VERIFY)
	else:
        	response = requests.get(uri, auth=(options.username, options.password), verify=SSL_VERIFY)

        try:
            result  = response.json()
        except ValueError:
            print "status unknown, could not parse JSON.\n\rstatus_code: %s\n\r%s" % (response.status_code,response.text)
            sys.exit(RETURN_CODE['UNKNOWN'])

        if options.debug:
                print "\n\rDEBUG::check:result:\n\r%s" % result

        return result


# Validate your check result against thresholds
def validate_and_notify(data, options):

    container = {}

    pm = []

    exit_msg = []

    exit = "OK"


    if options.debug:
        print "\n\rDEBUG::validate_and_notify:data:\n\r"
	print json.dumps(data, sort_keys=True,indent=4, separators=(',', ': '))

    for services in data['data']['servicegroup']['services']:

	# Name of service check
	name = services['description'].replace(" ", "_")

   	try:
		container[name]['ok'] += int(services['time_ok'])  
		container[name]['hosts'] += 1 
   	except KeyError:
		# create if not exists
		container[name] = {"ok": 0 , "hosts":0}
		container[name]['ok'] += int(services['time_ok'])
		container[name]['hosts'] += 1 

	#container['j0nix'] = {'hosts': 20, 'ok': 1724400}

    for k, v in container.iteritems():
	val1 = int(v['ok']) 
	val2 = (int(options.days)*86400*int(v['hosts']))

	# NAGIOS PM |'label'=value[UOM];[warn];[crit];[min];

	msg = "%s=%.4f" % (k, (float(val1) / float(val2)))
	perf = msg + ";%.4f;%.4f;0.0;1.0" % (options.warning, options.critical)

    	#Validate if we are below some threashholds...

	if (float(val1) / float(val2)) <= options.critical:
		exit = "CRITICAL"
		exit_msg.append(msg)
	
	elif (float(val1) / float(val2)) <= options.warning:
		if exit != "CRITICAL":
			exit = "WARNING"
		exit_msg.append(msg)

    	if options.debug:
		print "\n\rDEBUG::validate_and_notify:perf: %s" % perf

	pm.append(perf)
 	
     
    if options.debug:
	print "\n\rDEBUG::validate_and_notify:exit_code: %s %s\n\r" % (exit,RETURN_CODE[exit])
	sys.exit(RETURN_CODE['UNKNOWN'])
    else:
   	print "%s %s %s|%s" % (exit,options.servicegroup,",".join(exit_msg)," ".join(pm))
    	sys.exit(RETURN_CODE[exit])


def main():


  # Get, parse and validate args
  parser = build_parser()
  options, _args = parser.parse_args()
  options.warning,options.critical = validate_args(parser,options)


  if options.debug:
        print "\n\rDEBUG::options:\n\r%s" % (options)

  result = check(options) # check stuff
  validate_and_notify(result,options)

if __name__ == '__main__':
  main()
