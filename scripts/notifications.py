#!/usr/bin/env python

"""
Script for printing outage information to a Gnome widget.
"""

import argparse
import outagenotifier

__author__ = "Harvard-MIT Data Center DevOps"
__copyright__ = "Copyright 2015, HMDC"
__credits__ = ["Bradley Frank"]
__license__ = "GPLv2"
__maintainer__ = "HMDC"
__email__ = "linux@lists.hmdc.harvard.edu"
__status__ = "Production"

#
# Setup argument parsing with the argparse module.
#
parser = argparse.ArgumentParser(description="Display RCE outages.")
parser.add_argument('-d', '--debug', action='store_true',
                    help="Enables verbose output.")
parser.add_argument('-l', '--log',
                    help="Full path to log file.")
args = parser.parse_args()

#
# Set logging variables.
#
debug_level = 'DEBUG' if args.debug else 'NOTSET'
log_to_console = True if args.debug else False
log_to_file = True if args.log else False

#
# Print the outages to the widget.
#
notifier = outagenotifier.OutageNotifier(None, debug_level, log_to_console,
                                         log_to_file, args.log)
notifier.widget_init()
