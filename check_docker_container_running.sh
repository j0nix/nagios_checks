#!/bin/bash
# j0nix


CONTAINER=""
RESTART=0
verbose=0
LOGGER=0

function show_help {
printf "$0 -i container_id
	
	-i 	container_id
	-v 	verbose
	-r 	restart container if not running
	-h|? 	show this help
	-s	redirect output 2 syslog

"
}

OPTIND=1
while getopts "h?svri:" opt; do
    case "$opt" in
    h|\?)
        show_help
        exit 0
        ;;
    v)  verbose=1
        ;;
    r)  RESTART=1
        ;;
    i)  CONTAINER=$OPTARG
        ;;
    s)  LOGGER=1
    esac
done
shift $((OPTIND-1))
[ "$1" = "--" ] && shift

if [[ $LOGGER == 1 ]]; then
	exec 1> >(/bin/logger -s -t $(basename $0)) 2>&1
fi

if [ "x${CONTAINER}" == "x" ]; then
  echo "UNKNOWN - Container ID or Friendly Name Required"
  exit 3
fi

if [ "x$(which docker)" == "x" ]; then
  echo "UNKNOWN - Missing docker binary"
  exit 3
fi

docker info > /dev/null 2>&1
if [ $? -ne 0 ]; then
  echo "UNKNOWN - Unable to talk to the docker daemon"
  exit 3
fi

RUNNING=$(docker inspect --format="{{.State.Running}}" $CONTAINER 2> /dev/null)

if [ $? -eq 1 ]; then
  echo "UNKNOWN - $CONTAINER does not exist."
  exit 3
fi

if [ "$RUNNING" == "false" ]; then
  echo "CRITICAL - $CONTAINER is not running."
  if [[ $RESTART == 1 ]]
  then
	echo "docker restart $CONTAINER"
	docker restart $CONTAINER
  fi
  exit 2
fi

RESTARTING=$(docker inspect --format="{{.State.Restarting}}" $CONTAINER)

if [ "$RESTARTING" == "true" ]; then
  echo "WARNING - $CONTAINER state is restarting."
  exit 1
fi

STARTED=$(docker inspect --format="{{.State.StartedAt}}" $CONTAINER)
NETWORK=$(docker inspect --format="{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}" $CONTAINER)

echo "OK - $CONTAINER is running. IP: $NETWORK, StartedAt: $STARTED"
