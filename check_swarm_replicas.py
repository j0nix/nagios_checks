#! /usr/bin/python

# QuickFix haxx by j0nix
# ToDo:
# - Add debug
# - Add options for remote api link, like port and hostname ...

#import modules
import sys, getopt, requests
import simplejson as json

#NAGIOS return codes
RETURN_CODE = { "UNKNOWN":3,"OK":0,"WARNING":1,"CRITICAL":2}

# Remote api defaults
RA_HOST = "localhost"
RA_PORT = 2375

usage = """

    Check if status for this node is 'ready'
    
    - IF OK	=> Check number of replicas for defined service
    - ELSE	=> Alert with Warning

    
    usage: """ + __file__ + """ -w/--warn <integer> -c/--crit <integer> -s service_name
	
      -w Warning if nr of replicas is below this value		(REQUIRED)
      -c Critical if nr of replicas is below this value		(REQUIRED)
      -s service name						(REQUIRED)

      -H Remote API host					(OPTIONAL), DEFAULT: localhost
      -P Remote API port					(OPTIONAL), DEFAULT: 2375
      -x include PM data					(OPTIONAL), DEFAULT: False
	

"""

def node_status(host,port):

   import socket
   hostname = socket.gethostname()

   data = None

   status = "?"

   location = "http://{}:{}/nodes/{}".format(host,port,hostname)

   try:
	r = requests.get(location)
	data = r.json()
	#data = json.dumps(r.json(),indent=4, sort_keys=True)
	#print data
   except:
   	print 'UNKNOWN - Some communication error with docker remote api @ {}'.format(location)
   	sys.exit(RETURN_CODE['UNKNOWN'])
	
   try:
 	status = data["Status"]["State"]
   except KeyError:
	print 'UNKNOWN - Key error for status in json reply from remote api @ {}'.format(location)
   	sys.exit(RETURN_CODE['UNKNOWN'])

   #if status != "ready":
   #	print "WARNING - node '{}' is in status state '{}'".format(hostname,status)
   # 	sys.exit(RETURN_CODE['WARNING'])
   return status

def service_replicas(host,port,service):

   data = None

   location = "http://{}:{}/services/{}".format(host,port,service)

   try:
	r = requests.get(location)
	data = r.json()
	#data = json.dumps(r.json(),indent=4, sort_keys=True)
	#print data
   except:
   	print 'UNKNOWN - Some communication error with docker remote api @ {}'.format(location)
   	sys.exit(RETURN_CODE['UNKNOWN'])
	
   try:
 	replicas = data["Spec"]["Mode"]["Replicated"]["Replicas"]
   except KeyError:
	print 'UNKNOWN - Key error for replicas in json reply from remote api @ {}'.format(location)
   	sys.exit(RETURN_CODE['UNKNOWN'])

   return replicas


def performance_data(service):
  performance_data = "| 'label'=value[UOM];[warn];[crit];[min];[max]"
  return performance_data

def command_line_validate(argv):

  # Defaults
  host = RA_HOST
  port = RA_PORT
  pm = False

  try:
    opts, args = getopt.getopt(argv, 'w:c:s:H:P:x', ['warn=' ,'crit=','service=','host=','port=','pm'])
  except getopt.GetoptError:
    print usage

  try:

    for opt, arg in opts:

      if opt in ('-w', '--warn'):

        try:
        	warn = int(arg)
        except:
        	print '***warn value must be an integer***'
        	sys.exit(RETURN_CODE['CRITICAL'])

      elif opt in ('-c', '--crit'):

        try:
        	crit = int(arg)
        except:
        	print '***crit value must be an integer***'
        	sys.exit(RETURN_CODE['UNKNOWN'])

      elif opt in ('-s','--service'):

        try:
      		service = str(arg)
        except:
       		print '***service value must be a string***'
      		sys.exit(RETURN_CODE['UNKNOWN'])

      elif opt in ('-H','--host'):

        try:
      		host = str(arg)
        except:
       		print '***service value must be a string***'
      		sys.exit(RETURN_CODE['UNKNOWN'])

      elif opt in ('-P','--port'):

        try:
      		port = int(arg)
        except:
       		print '***service value must be a integer***'
      		sys.exit(RETURN_CODE['UNKNOWN'])

      elif opt in ('-x','--pm'):

	pm = True

      else:
      	print usage

    try:
      isinstance(warn, int)
    except:
      print '\n***warn level is required***\n'
      print usage
      sys.exit(RETURN_CODE['UNKNOWN'])
    try:
      isinstance(crit, int)
    except:
      print '\n***crit level is required***\n'
      print usage
      sys.exit(RETURN_CODE['UNKNOWN'])
    try:
      isinstance(service, basestring)
    except:
      print '\n***service name is required***\n'
      print usage
      sys.exit(RETURN_CODE['UNKNOWN'])

  except:
    sys.exit(RETURN_CODE['UNKNOWN'])

  if warn < crit:
    print '***warning level must be higher than critical level***'
    sys.exit(RETURN_CODE['UNKNOWN'])
  if warn == crit:
    print '***warning & critical cant be set to same value***'
    sys.exit(RETURN_CODE['UNKNOWN'])
  
  return warn, crit, service, host, port, pm
  
def validate_and_notify(node_status, total_replicas, warn, crit, service, perf_data):

  if node_status == 'ready':
  
  	if total_replicas < crit:
		print 'CRITICAL - replicas for',service,'=', total_replicas, perf_data
		sys.exit(RETURN_CODE['CRITICAL'])
	elif total_replicas < warn:
		print 'WARNING - replicas for',service,'=',total_replicas,perf_data
		sys.exit(RETURN_CODE['WARNING'])
	else:
		print 'OK - Status:',node_status,' Replicas:',total_replicas,perf_data
		sys.exit(RETURN_CODE['OK'])
  else:
	print 'WARNING - Node is not in expected state! Status => state =>',node_status
	sys.exit(RETURN_CODE['WARNING'])

# main function
def main():
	
  argv = sys.argv[1:]
  
  warn, crit, service, host, port, get_pm = command_line_validate(argv)

  status = node_status(host,port)
  
  replicas = service_replicas(host,port,service)

  if(get_pm): 
  	perf_data = performance_data(service)
  else:
	perf_data = ""

  validate_and_notify(status, replicas, warn, crit, service, perf_data)

if __name__ == '__main__':
  main()
