"""
   A short description of what this check do
"""

import os, sys, logging
from argparse import ArgumentParser
from argparse import RawTextHelpFormatter

epilog = """
Example)
   python {} -s 3
___________________________________________________________
Infra @ Nordax
""".format(
    sys.argv[0]
)

## Argument parser setup
parser = ArgumentParser(
    formatter_class=RawTextHelpFormatter,
    description=__doc__,
    epilog=epilog,
    prog=os.path.basename(sys.argv[0]),
)

parser.add_argument(
    "-v", "--verbose", action="count", default=0, help="increase log level"
)
parser.add_argument(
    "-q", "--quiet", action="count", default=0, help="decrease log level"
)

""" Example of your script arguments, please adjust """
parser.add_argument(
    "-d",
    "--dest",
    dest="dest",
    metavar="ip",
    default="127.0.01",
    help="Destination (Default: 127.0.0.1)",
)

""" Example of required arguemnts """
required = parser.add_argument_group(title="required arguments")
required.add_argument(
    "-w",
    "--warning",
    dest="warning",
    metavar="N",
    type=int,
    required=True,
    help="WARNING threshold",
)

required.add_argument(
    "-c",
    "--critical",
    dest="critical",
    metavar="N",
    type=int,
    required=True,
    help="CRITICAL threshold",
)

"""Logging setup"""


def setLogging(args):
    log_adjust = max(min(args.quiet - args.verbose, 2), -2)
    logging.basicConfig(
        level=logging.INFO + log_adjust * 10,
        format="%(asctime)s [%(levelname)s]\t[%(module)s]\t%(message)s",
    )


EXIT = {
    "OK": 0,  	   # Service is OK
    "WARNING": 1,  # Service has a WARNING
    "CRITICAL": 2, # Service is in a CRITICAL status
    "UNKNOWN": 3,  # Service status is UNKNOWN
}

""" The main function for your script """


def main(args):
    ## Here you start fiddle with your check code
    logging.debug("This is a skeleton, your arguments => {}".format(args))

    my_result = 5

    # Sanitycheck
    if args.warning >= args.critical:
	print("\n\n!Warning threshold needs to be less than critical threshold\n\n___________________________________________________________\n")
	parser.print_help(sys.stderr)
	sys.exit(0)

    # let's check if critical
    if my_result >= args.critical:
	print("CRITICAL - {} is greater than critical threshold ({})".format(my_result,args.critical))
	sys.exit(EXIT["CRITICAL"])

    # let's check if warning
    if my_result >= args.warning:
	print("WARNING - {}, is above or equal to warning threshold ({})".format(my_result,args.warning))
	sys.exit(EXIT["WARNING"])

    # Default exit everything is OK
    print("All OK!")
    sys.exit(EXIT["OK"])


if __name__ == "__main__":
    # Parse arguments
    args = parser.parse_args()
    # Set loglevel
    setLogging(args)
    # Run your check
    main(args)

# Jon Svendsen 2020
