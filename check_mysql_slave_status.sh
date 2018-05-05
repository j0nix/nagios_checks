#!/bin/sh
# Quick & dirty MySQL slave check by j0nix
# Om db monitored you first need to execute: 
# mysql> GRANT REPLICATION CLIENT ON *.* to 'nagios'@'localhost';
# mysql> flush privileges;

#Default shit
WARNING=30
DB_USER="nagios"

#Exitcodes
E_OK=0
E_WARNING=1
E_CRITICAL=2
E_UNKNOWN=3

show_help() {
    echo 
    echo "$0 -w seconds_behind -c seconds_behind [ -h ] "
    echo "Checks if slave is working by checking that Slave_IO_Running & Slave_SQL_Running equals Yes"
    echo "Also checks Seconds_Behind_Master, here you can set a warning threshold"
    echo 
    echo "  -w SECONDS  	 Seconds behind master"
    echo "  -u db_username	 mysql user that have grants = GRANT REPLICATION CLIENT ON *.* to '<user_name>'@'localhost'; "
    echo
    echo "Example:"
    echo "    $0 -u nagios -w 300"
    echo
}

# process args
while [ ! -z "$1" ]; do
    case $1 in
        -w) shift; WARNING=$1 ;;
        -u) shift; DB_USER=$1 ;;
        -h) show_help; exit 1 ;;
    esac
    shift
done

client=$(which mysql);

CHECK=$($client -u $DB_USER -e "SHOW SLAVE STATUS\G" 2>/dev/null)

if [ $? -eq 0 ]
then 
	repl_IO=`printf "$CHECK"|grep "Slave_IO_Running:"|cut -f2 -d:`

	repl_SQL=`printf "$CHECK"|grep "Slave_SQL_Running:"|cut -f2 -d:`

	repl_BEHIND=`printf "$CHECK"|grep "Seconds_Behind_Master"|cut -f2 -d:`

	if [ "$repl_IO" != " Yes" -o "$repl_SQL" != " Yes" ] ; then
		printf "THIS SLAVE IS NOT WORKING!\n"
		exit $E_CRITICAL;
	fi

	if [ $repl_BEHIND -ge $WARNING ] ; then
		printf "SLAVE IS FALLING BEHIND, Seconds_Behind_Master = $repl_BEHIND\n"
		exit $E_WARNING;
	fi

	printf "THIS SLAVE IS WORKING\n"
	exit $E_OK;
else
	printf "CAN'T EXEUTE SLAVE CHECK"
	exit $E_WARNING; 
fi
