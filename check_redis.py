#! /usr/bin/python
# j0nix 2017

#import modules
import socket
import sys
from optparse import OptionParser

#NAGIOS return codes
RETURN_CODE = { "UNKNOWN":0,"OK":0,"WARNING":1,"CRITICAL":2}

# Parse options
def build_parser():
    parser = OptionParser()
    parser.add_option("-H", "--host", dest="host", help="Host to connect to", default="127.0.0.1")
    parser.add_option("-w", "--warn", dest="warning", help="Alert if memory usage in MB is greater than value", type="int")
    parser.add_option("-c", "--crit", dest="critical", help="Alert if memory usage in MB is greater than value", type="int")
    parser.add_option("-p", "--port", dest="port", help="Redis port to connect to.", type="int", default=6379)
    parser.add_option("-t", "--timeout", dest="timeout", help="Number of seconds to wait before considering redis down", type="int", default=2)
    parser.add_option("-d", "--debug", dest="debug", help="Enable debug", action="store_true")
    return parser

# Check if we have required args and makes sense
def validate_args(p,o):

    if not o.warning:
        p.error("Warning value in MB required")
        sys.exit(RETURN_CODE['UNKNOWN'])
	
    if not o.critical:
        p.error("Critical value in MB required")
        sys.exit(RETURN_CODE['UNKNOWN'])

    if o.warning == o.critical:
	p.error("Warning and Critical cant be the same value")
        sys.exit(RETURN_CODE['UNKNOWN'])

    if o.warning > o.critical:
	p.error("Warning can't be larger than Critical")
        sys.exit(RETURN_CODE['UNKNOWN'])
	
# Your magic check funktion
def check(options):

    try:
    	socket.setdefaulttimeout(options.timeout or None)
    	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    	s.connect((options.host, options.port))
    	s.send("*1\r\n$4\r\ninfo memory\r\n")
    	buf = ""
    	while '\r\n\r\n' not in buf:
    	    buf += s.recv(1024)
    	s.close()

    	if options.debug:
    		print "\n\rDEBUG::check:\n\r{}".format(buf) 

	return dict(x.split(':', 1) for x in buf.split('\r\n') if ':' in x)

    except socket.error, exc:
        print "CRITICAL: Error connecting or getting INFO from redis %s:%s: %s" % (options.host, options.port, exc)
        sys.exit(RETURN_CODE['CRITICAL'])
 
# Validate your check result against thresholds
def validate_and_notify(result, options):

    if options.debug:
    	print "\n\rDEBUG::validate_and_notify:\n\r{}".format(result) 

    try: 
    	memory = int(result.get("used_memory_rss") or result["used_memory"]) / (1024*1024)
    except:
	print "Could not fetch memory data"
        sys.exit(RETURN_CODE['UNKNOWN'])

    if options.debug:
    	print "\n\rDEBUG::validate_and_notify:memory:\n\r{}".format(memory) 

    if memory > options.critical:
        print "CRITICAL: Redis memory usage is %dMB (threshold %dMB)" % (memory, options.critical)
        sys.exit(RETURN_CODE['CRITICAL'])
 
    elif memory > options.warning:
        print "WARN: Redis memory usage is %dMB (threshold %dMB)" % (memory, options.warning)
        sys.exit(RETURN_CODE['WARNING'])
    else:
    	print "OK: Redis memory usage is %dMB" % memory
        sys.exit(RETURN_CODE['OK'])

# logical script flow
def main():
    
  # Get, parse and validate args
  parser = build_parser()
  options, _args = parser.parse_args()

  if options.debug:
	print "\n\rDEBUG::options:\n\r{}".format(options)
 
  validate_args(parser,options)
  result = check(options) # check stuff
  validate_and_notify(result,options)
 
if __name__ == '__main__':
  main()
