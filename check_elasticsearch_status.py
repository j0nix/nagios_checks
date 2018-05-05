#! /usr/bin/python
# j0nix 2018
# Check elasticsearch cluster status

#import modules
import sys
try:
  import json
except ImportError:
  import simplejson as json
try:
  import requests
except:
  print "\n\r\t[MISSING module 'python-requests']\n\r"
  exit(3)

from optparse import OptionParser, TitledHelpFormatter

from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

SSL_VERIFY = False

# ES CREDENTIALS
usr = '''elastic'''
pwd = '''changeme'''

#NAGIOS return codes
RETURN_CODE = { "UNKNOWN":3,"OK":0,"WARNING":1,"CRITICAL":2}

# Parse options
def build_parser():
    parser = OptionParser()
    parser.add_option("-H", "--host", dest="host", help="Host to connect to", default="127.0.0.1")
    parser.add_option("-p", "--port", dest="port", help="Port where http API is published", type="int", default=9200)
    parser.add_option("-n", "--nr_of_nodes", dest="nr_of_nodes", help="Number of cluster nodes this cluster have", type="int")
    parser.add_option("-d", dest="debug", help="Enable debug", action="store_true")
    parser.add_option("-s", dest="ssl", help="Enable ssl", action="store_true")
    parser.add_option("-x", dest="auth", help="Use auth credentials, defined in script code", action="store_true")
    return parser

def validate_args(p,o):

    if not o.nr_of_nodes:
        p.error("Number of nodes in cluster is required")
        sys.exit(RETURN_CODE['UNKNOWN'])

# Magic check funktion
def check(options):

	if options.ssl:
		location = 'https://%s:%d/_cluster/health' % (options.host, options.port)
	else:
		location = 'http://%s:%d/_cluster/health' % (options.host, options.port)

	if options.auth:

	  try:
	    r = requests.get(location, auth=(usr, pwd), verify=SSL_VERIFY)
	  except requests.exceptions.ConnectionError as e:
	    print "{} => {}".format(location,e)
            sys.exit(RETURN_CODE['UNKNOWN'])

        else:

	  try:
	    r = requests.get(location, verify=SSL_VERIFY)
	  except requests.exceptions.ConnectionError as e:
	    print "{} => {}".format(location,e)
            sys.exit(RETURN_CODE['UNKNOWN'])

        try:

	  if r.status_code != requests.codes.ok:
            r.raise_for_status()

        except requests.exceptions.HTTPError as e:
	  print "[{}] {} => {}".format(r.status_code,location,e)
          sys.exit(RETURN_CODE['UNKNOWN'])


        if options.debug:
                print "\n\rDEBUG::check:\n\r{}".format(r.text)

        try:
            es_cluster_health = r.json()

        except ValueError:
            print "JSON_PARSE_ERROR => {}".format(r.text)
            sys.exit(RETURN_CODE['UNKNOWN'])

        return es_cluster_health

# Validate check result against thresholds
def validate_and_notify(cluster_health, options):

    if options.debug:
        print "\n\rDEBUG::validate_and_notify:\n\r{}".format(cluster_health)

    if cluster_health['status'].lower() == 'red':
        print "Status red, number_of_nodes: {}, relocating_shards: {}, initializing_shards {}, unassigned_shards: {}, active_shards_percent_as_number: {}".format(cluster_health['number_of_nodes'],cluster_health['relocating_shards'] ,cluster_health['initializing_shards'],cluster_health['unassigned_shards'],cluster_health['active_shards_percent_as_number'] )
        sys.exit(RETURN_CODE['CRITICAL'])
    elif cluster_health['status'].lower() == 'yellow' and cluster_health['number_of_nodes'] < int(options.nr_of_nodes):
        print "STATUS == YELLOW and missing cluster nodes. Have {}, expecting {}".format(cluster_health['number_of_nodes'],options.nr_of_nodes)
        sys.exit(RETURN_CODE['WARNING'])
    else:
        print "All OK, status: {}, number_of_nodes: {}, relocating_shards: {}, initializing_shards {}, unassigned_shards: {}, active_shards_percent_as_number: {}".format(cluster_health['status'],cluster_health['number_of_nodes'],cluster_health['relocating_shards'] ,cluster_health['initializing_shards'],cluster_health['unassigned_shards'],cluster_health['active_shards_percent_as_number'] )
        sys.exit(RETURN_CODE['OK'])


# logical script flow
def main():

  # Get, parse and validate args
  parser = build_parser()
  options, _args = parser.parse_args()
  validate_args(parser,options)

  if options.debug:
        print "\n\rDEBUG::options:\n\r{}".format(options)

  result = check(options) # check stuff
  validate_and_notify(result,options)

if __name__ == '__main__':
  main()
