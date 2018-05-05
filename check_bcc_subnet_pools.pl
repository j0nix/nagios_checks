#!/usr/bin/perl -w
# Incognito BCC api & scope utilization check. 
# Author: Jon Svendsen 2016
# License: Free As In Beer
#
# Note: Make sure that nrpe generates file in /tmp. 
# Otherwise you probably get an error
use strict;
use warnings;
use XML::Simple;
use LWP::UserAgent;
use Getopt::Std;
use Net::SNMP qw(:asn1 :snmp DEBUG_ALL);
use Time::HiRes;
use Switch;
use Sys::Syslog;
#Syslog credentials
openlog("NAGIOSDEBUG", "nofatal,pid", "local0");
#use Math::Round qw/nearest/;

# Some default variables
my $username = $ENV{LOGNAME} || $ENV{USER} || getpwuid($<);
my $VER="1.0.0";
my %ERRORS=('OK'=>0,'WARNING'=>1,'CRITICAL'=>2,'UNKNOWN'=>3,'DEPENDENT'=>4);
my $WARN = undef;
my $CRIT = undef;
my $HOST = undef;
my $PORT = 8181;
my $TIMEOUT = 5;
my $POOLSUB = '^(.*)\d+$';
my %STATUS;
my @EXCLUDE;
my $PERF = 0; 
my $DEBUG = 0;
my $SENDTRAP=0;

my $TRAPDEST = undef;
my $TRAPCOMM='public';
my $TRAPPORT=162;
my @TRAPPOOLS;
my $TRAPFILE;
$TRAPFILE = "/tmp/bcc_subnet_pools";
$TRAPFILE .= $username if defined $username;
my $TRAPERROR = 0;
 
sub init() {

	# File for store pools where we sent traps, this to be able to send clear traps
		
    	#Create the file if it doesn't exist
	unless(-e $TRAPFILE) {
    		open my $fc, ">", $TRAPFILE;
    		close $fc;
    	}
	#Read file info array
	open TRAPFILE, "<", $TRAPFILE or die $!;
		chomp(@TRAPPOOLS = <TRAPFILE>);
	close(TRAPFILE);
	#Open & truncate file
	open TRAPFILE, ">", $TRAPFILE or die $!;

	#use Data::Dumper;
	#print Dumper(@TRAPPOOLS);

	## Fetch all these options
	my %options;
	getopts("VvhPt:w:c:H:p:E:r:T:", \%options);

	## Some extra sanity check
	if ($ARGV[0]) {
		print "Invalid argument:" ;
		foreach (@ARGV) { print "$_\n"; }
		&help();
	}

	# Do we include any of these print & die flags?
	&help() if defined $options{h};
	&version() if defined $options{V};

	# Required options
	if (defined($options{H}) && defined($options{c}) && defined($options{w})) {
		$HOST = $options{H};
		$WARN = $options{w};
		$CRIT = $options{c};	
	} else {
        	print "\nMissing REQIRED options\n";
		&help();
	}
	# If provided... set other shit
	$PORT=$options{p} if defined($options{p});
	$POOLSUB=$options{r} if defined($options{r});
	$PERF = 1 if defined($options{P});
	@EXCLUDE = split(',',$options{E}) if defined($options{E});
	$DEBUG = 1 if defined($options{v});
	if(defined($options{T})) {
		$TRAPDEST = $options{T};
		$SENDTRAP=1;
	}

	#Some helpful debug output
	if ($DEBUG) {
	printf "
	TIMEOUT: %s
	PORT: %s 
	POOLREGEXP: %s
	HOST: %s
	WARNING: %s
	CRITICAL: %s
	PERFORMANCE: %s
	EXCLUDE_PATTERN: %s
	SENDTRAP: %s
	TRAPDEST: %s

	\n",$TIMEOUT,$PORT,$POOLSUB,$HOST,$WARN,$CRIT,$PERF,join(",",@EXCLUDE),$SENDTRAP,$TRAPDEST;
	}

	# Prepare for that API call
	my $server_endpoint = "http://$HOST:$PORT/rangeinfo";
	my $ua = LWP::UserAgent->new;
	$ua->timeout($TIMEOUT);
	my $req = HTTP::Request->new(GET => $server_endpoint);
	$req->header('content-type' => 'application/xml');
	# API CALL
	my $resp = $ua->request($req);
	# Success?
	if ($resp->is_success) {

		# Local variables;
		my ($msg,$usage,$status,$poolname);
		my @performance;
		my %pools;
		my $EXITSTATUS = "OK";
		my $ALARMTRAPS = 0;
		my $CLEARTRAPS = 0;

		# Decode xml
		my $xml = $resp->decoded_content;
		my $tree = XMLin($xml);

		# Loop & define pools
		foreach my $key ( keys %{ $tree->{'dhcpv4Ranges'}->{'range'} } ) {

			# Only add subnet with ipaddresses
			if($tree->{'dhcpv4Ranges'}->{'range'}->{$key}->{'usage'}->{'totalips'} > 0) {
			
				# Set poolname	
				$poolname=$key;
				$poolname =~ s/$POOLSUB/$1/; 
				
				# If exclude search if poolname should be excluded
				# Note: this means that we also exclude performance data for that pool
				my $x=0;
				if(@EXCLUDE) {	
					foreach (@EXCLUDE) { $x=1 if $poolname =~ /$_/; }
				}

				#Some helpful debug output
				if ($DEBUG) {
					my $tmp = $key;
                                        if ($tmp =~ /$POOLSUB/) {
						$tmp =~ s/$POOLSUB/$1/;
                                                printf "%s match %s, POOLNAME=%s\n",$key,$POOLSUB,$tmp;
                                        } else{
                                                printf "%s DONT match %s, POOLNAME=%s\n",$key,$POOLSUB,$tmp;
                                        }
                                }
				# If not to exclude
				if (!$x) { 
					# If pool already defined, update (add) data to pool, otherwise define new...
					if($pools{$poolname}) {
						$pools{$poolname}{'total'} += $tree->{'dhcpv4Ranges'}->{'range'}->{$key}->{'usage'}->{'totalips'};
						$pools{$poolname}{'used'} += $tree->{'dhcpv4Ranges'}->{'range'}->{$key}->{'usage'}->{'usedips'};
					} else {
						$pools{$poolname}{'total'} = $tree->{'dhcpv4Ranges'}->{'range'}->{$key}->{'usage'}->{'totalips'};
						$pools{$poolname}{'used'} = $tree->{'dhcpv4Ranges'}->{'range'}->{$key}->{'usage'}->{'usedips'};
					}
				} else {
					# If someone thinks its important you could define a variable to hold excluded pools & its data, for like merging when printing performance data.
					

					printf("\nExcluding $poolname\n") if $DEBUG;
				}
			}
		}

		# Validate pool usage & also exclude, if defined, pools
		foreach my $p ( keys %pools ) {

    				$usage = sprintf "%0.1f",(($pools{$p}{'used'}/$pools{$p}{'total'}) * 100);
				$status = validate($usage,$WARN,$CRIT);
				
				if ($status ne "OK") {

					$STATUS{$status} .= " $p=$usage% ";
					# If traps are requested...
					if ($SENDTRAP) {
						if(send_trap($status,$pools{$p}{'total'},$pools{$p}{'used'},$p)) {
							print TRAPFILE "$p|$status\n";	
							$ALARMTRAPS++;
							printf("\nTrap sent for pool $p\n") if $DEBUG;
						} else {
							$TRAPERROR++;
        						printf("\nError sending trap for $p\n") if $DEBUG;
						}
					}

				} else {

					if($SENDTRAP) {
						# Do we need to send any cleartraps?
						if (my @hits = grep(/^$p\|[WARNING|CRITICAL]/, @TRAPPOOLS)) {
							print "\n>> Found ",join(";",@hits)," in $TRAPFILE\n" if $DEBUG;
							foreach my $x (@hits) {
								my @y = split('\|',$x);
								if(send_trap("CLEAR$y[1]",$pools{$p}{'total'},$pools{$p}{'used'},$p)) {
									$CLEARTRAPS++;
                                                        		printf("\nClearTrap sent for pool $p\n") if $DEBUG;
                                                		} else {
                                                        		printf("\nError sending cleartrap for $p\n") if $DEBUG;
									$TRAPERROR++;
                                                		}
							}
						}
					}
				}

				if ($PERF) {
					# make % in actual numbers in performance data
					my $w = sprintf "%i",(($pools{$p}{'total'}*$WARN )/100);
					my $c = sprintf "%i",(($pools{$p}{'total'}*$CRIT )/100);
					push(@performance, "$p=$pools{$p}{'used'};$w;$c;0;$pools{$p}{'total'}");
				}

		}

		if ($STATUS{'CRITICAL'}) {
			$msg .= "CRITICAL:". $STATUS{'CRITICAL'};
			$EXITSTATUS = "CRITICAL";
		}
		
		if ($STATUS{'WARNING'}) {
			$msg .= "; " if ($STATUS{'CRITICAL'});
			$msg .= "WARNING:". $STATUS{'WARNING'};
			$EXITSTATUS = "WARNING" unless $STATUS{'CRITICAL'};
		}
		
		if (!%STATUS) {
			$msg = "OK: No subnets violate thresholds" #Thresholds are set to warning when equal or above $WARN%, critical equal or above $CRIT%"; 
		}

		if ($SENDTRAP) { # Define exitstatus & msg when using traps
			$EXITSTATUS = "OK";
			$msg .= " (TRAPS: $ALARMTRAPS, CLEARTRAPS: $CLEARTRAPS)" unless ($TRAPERROR > 0);
			$msg .= " ! SCRIPTERROR SENDING SNMPTRAPS" if ($TRAPERROR > 0);
			$EXITSTATUS = "WARNING" if ($TRAPERROR > 0);
		}

		# Performance data ?
		$msg .= " | " . join(',', @performance) if ($PERF);

		# print & exit
		print "$msg\n";
		exit $ERRORS{$EXITSTATUS};
	}
	else {
		print "CRITICAL: ERROR QUERY HTTP-API : ". $resp->content();
	        exit $ERRORS{'CRITICAL'};
	}

	close(TRAPFILE);

}

sub validate() {
        my ($res,$warn,$crit) = @_;
        return 'CRITICAL' if ($res >= $crit);
        return 'WARNING' if ($res >= $warn);
        return 'OK';
}

sub send_trap() {

	my ($severity,$total,$used,$poolname) = @_;

        printf("Preparing sending trap: $poolname = total: $total, used: $used, severity: $severity\n") if $DEBUG;
	
	my $result = 0;

	my $oid = 0;

	switch ($severity) {

		case "WARNING"	{ $oid='.1.3.6.1.4.1.3606.7.1.99.0.6' }
		case "CRITICAL"	{ $oid='.1.3.6.1.4.1.3606.7.1.99.0.7' }
		case "CLEARWARNING" { $oid='.1.3.6.1.4.1.3606.7.1.99.0.42' }
		case "CLEARCRITICAL" { $oid='.1.3.6.1.4.1.3606.7.1.99.0.43';}
		else { 
			printf("\nERROR: WRONG SEVERITY: $severity\n") if $DEBUG;
			return 1;
		}
	}

	my ($session, $error) = Net::SNMP->session(
		
		-hostname  => $TRAPDEST || 'localhost',
		-community => 'public',
		-port      => 162,     
		-version   => 'snmpv2c',
		#-debug	   => DEBUG_ALL

	);

	if (!defined($session)) {
		printf("\nError createing NETSNMP session: %s\n",$error ) if $DEBUG;
        	return 0;
	}

	$result = $session->snmpv2_trap(
                -varbindlist => [
                  '1.3.6.1.2.1.1.3.0', TIMETICKS, time,
                  '1.3.6.1.6.3.1.1.4.1.0', OBJECT_IDENTIFIER, $oid,
                  '1.3.6.1.4.1.3606.7.1.2.99.1.2', UNSIGNED32, $total,
                  '1.3.6.1.4.1.3606.7.1.2.99.1.4', UNSIGNED32, ($total-$used),
                  '1.3.6.1.4.1.3606.7.1.2.99.1.5', INTEGER, 1 ,
                  '1.3.6.1.4.1.3606.7.1.2.99.1.6', OCTET_STRING, '000 000 000 000 000 000 000 000 000 000 000 000 000 000 000 000 ',
                  '1.3.6.1.4.1.3606.7.1.2.99.1.7', OCTET_STRING, $poolname
                ]);



	if (!defined($result)) {

		printf("\nERROR when snmptrap: %s.\n", $session->error()) if $DEBUG;
		return  0;

	} else {
		return 1;
	}

	$session->close();
}

sub help() {
	print "

        check_bcc_subnet -H <ipaddress/fqdn> -w <warning threshold> -c <critical threshold> [-h] [-V] [-P] [-D] [-t <timeout>] [-p <port>] [-E <exclude_pattern>] [-r <pool_regexp_pattern> ]

          Options:

          -H    ipaddress/fqdn to http-api		| REQUIRED
	  -p	api port				| Default: $PORT
          -w    warning threshold			| REQUIRED
          -c    critical threshold			| REQUIRED
          -h    Print help & exit
          -V    Print version & exit
          -t    timeout in sec				| Default: $TIMEOUT s
	  -E	Exclude patterns, comma separated	| Ex) -E Unprov,TEST
	  -P	Include Performance data
	  -r	Regexp substitute pattern for pools	| Default ^(.*)\\d+\$    (capture 1 = pool)
	  -T    Ipaddress to trapdestination		| If not set no traps will be sent 
	  -v	Show debug output

	
";
        # Exit as unknown error
        exit $ERRORS{'UNKNOWN'};
}
sub version() {
	print "
        	$0 $VER  - j0nix\@zweet.net
	";
        # Exit as unknown error
        exit $ERRORS{'UNKNOWN'};
}
init(); # Do tha thingie
#j0nix
