#!/usr/bin/python
# j0nix 2017
 
# import modules
import sys
from optparse import OptionParser
 
#NAGIOS return codes
RETURN_CODE = { "OK":0,"WARNING":1,"CRITICAL":2,"UNKNOWN":3 }
 
# Parse options
def build_parser():
    parser = OptionParser()
    parser.add_option("-H", "--host", dest="host", help="Host to connect to.", default="127.0.0.1")
    parser.add_option("-w", "--warn", dest="warning", help="Warning threshold", type="int")
    parser.add_option("-c", "--crit", dest="critical", help="Critical threshold", type="int")
    parser.add_option("-d", "--debug", dest="debug", help="Enable debug", action="store_true")
    return parser
 
# Check if we have required args and makes sense
def validate_args(p,o):
 
    if not o.warning:
        p.error("Warning level required")
        sys.exit(RETURN_CODE['UNKNOWN'])
 
    if not o.critical:
        p.error("Critical level required")
        sys.exit(RETURN_CODE['UNKNOWN'])
 
    if o.warning == o.critical:
        p.error("Warning and Critical cant be the same value")
        sys.exit(RETURN_CODE['UNKNOWN'])
 
    if o.warning > o.critical:
        p.error("Warning can't be larger than Critical")
        sys.exit(RETURN_CODE['UNKNOWN'])
 
# Your magic check funktion
def check(options):
 
    host = options.host
    if options.debug:
        print "{}".format(host)
 
    return 5
 
# Validate your check result against thresholds
def validate_and_notify(result, options):
 
        if result >= options.critical:
            print 'CRITICAL'
            sys.exit(RETURN_CODE['CRITICAL'])
        elif result >= options.warning:
            print 'WARNING'
            sys.exit(RETURN_CODE['WARNING'])
        elif result < options.warning:
            print 'OK'
            sys.exit(RETURN_CODE['OK'])
        else
            print "UNKNOWN ({})".format(result)
            sys.exit(RETURN_CODE['UNKNOWN'])
 
 # logical script flow
def main():
 
  # Get, parse and validate args
  parser = build_parser()
  options, _args = parser.parse_args()
  validate_args(parser,options)
  result = check(options) # check stuff
  validate_and_notify(result,options)
 
if __name__ == '__main__':
  main()
