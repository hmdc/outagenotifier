#!/usr/bin/env python

"""
Script for printing outage information to the console.
"""

from bs4 import BeautifulSoup
import argparse
import ConfigParser
import hmdclogger
import os

__author__ = "Harvard-MIT Data Center DevOps"
__copyright__ = "Copyright 2015, HMDC"
__credits__ = ["Bradley Frank"]
__license__ = "GPLv2"
__maintainer__ = "HMDC"
__email__ = "linux@lists.hmdc.harvard.edu"
__status__ = "Production"

CONFIG_FILE = "/etc/outagenotifier.conf"
NOTIFICATIONS_FILE = "notifications.xml"


def get_settings(config_file):
  config = ConfigParser.ConfigParser()
  config.read(config_file)

  settings = {
    # WorkingFiles
    'working_directory': config.get('WorkingFiles', 'working_directory'),
  }

  return settings

def set_logger(debug_level):
  """Creates an instance of HMDCLogger with appropriate handlers."""

  hmdclog = hmdclogger.HMDCLogger("outages", debug_level)
  hmdclog.log_to_console()

  return hmdclog

def parse_xml(source, hmdclog):
  """Reads in messages from notifications XML file."""

  hmdclog.log('debug', "Source file: " + source)

  if os.path.isfile(source):
    with open(source, "r") as file:
      xml_file = BeautifulSoup(file, "xml")
    file.close()
    hmdclog.log('debug', "Read in file: " + source)
  else:
    raise Exception("Notifications file not found!")

  counter = 0
  outages = []
  messages = xml_file.find_all("message")

  for message in messages:
    counter += 1
    hmdclog.log('debug', "Parsing message #" + str(counter) + ".")
    raw_text = str(message.text)
    text = raw_text.decode("unicode_escape")
    outages.append(text)

  return outages

#
# Setup argument parsing with the argparse module.
#
parser = argparse.ArgumentParser(description="Display RCE outages.")
parser.add_argument('-d', '--debug', action='store_true',
                    help="Enables verbose output.")
args = parser.parse_args()

#
# Import conf file settings.
#
settings = get_settings(CONFIG_FILE)

#
# Set logging level based on the debug argument.
#
debug_level = 'DEBUG' if args.debug else 'NOTSET'
hmdclog = set_logger(debug_level)

#
# Parse the noifications file for outage messages to display.
#
source = settings['working_directory'] + "/" + NOTIFICATIONS_FILE
messages = parse_xml(source, hmdclog)

#
# Print the messages to console.
#
for message in messages:
  print message