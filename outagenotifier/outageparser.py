#!/usr/bin/env python

from bs4 import BeautifulSoup
from termcolor import colored
import ConfigParser
import datetime
import hmdclogger
import os
import time

__author__ = "Harvard-MIT Data Center DevOps"
__copyright__ = "Copyright 2015, HMDC"
__credits__ = ["Bradley Frank"]
__license__ = "GPLv2"
__maintainer__ = "HMDC"
__email__ = "linux@lists.hmdc.harvard.edu"
__status__ = "Production"


class OutageParser:
  """

  Example:
    notifier = OutageNotifier()
    # TODO

  Private Functions:
    _get_settings: Parses the conf file for settings.
    _get_update_time: Returns the mtime of the notification feed.

  Public Functions:
    create_outages_output:
    get_notifications:
    parse_xml:
    sort_outages_by_status:

  Class Variables:
    CONFIG_FILE (string): Location of conf file to import self.settings.
  """

  CONFIG_FILE = "/etc/outagenotifier.conf"

  def __init__(self, logger=None, debug_level=None, log_to_console=False, log_to_file=False):
    """Sets up module settings and a logging instance.

    Arguments:
      debug_level (string): Optionally override the debugging level.
      log_to_console (boolean): Optionally log to console.
      log_to_file (boolean): Optionally log to a file (defined in CONFIG_FILE).

    Attributes:
      hmdclog (instance): Instance of HMDCLogger for logging.
    """

    self.settings = self._get_settings()

    if logger is None:
      self.hmdclog = self._set_logger(debug_level, log_to_console, log_to_file)
    else:
      self.hmdclog = logger

  def _get_settings(self):
    """Parses the conf file for settings."""

    config = ConfigParser.ConfigParser()
    config.read(self.CONFIG_FILE)

    settings = {
      # Debugging
      'debug_level': config.get('Debugging', 'debug_level'),
      'log_file': config.get('Debugging', 'log_file'),
      # Parsing
      'scope_ahead': config.getint('Parsing', 'scope_ahead'),
      'scope_past': config.getint('Parsing', 'scope_past'),
      # States
      'states': {},
      # WorkingFiles
      'working_directory': config.get('WorkingFiles', 'working_directory'),
      # Widget
      'icon_path': config.get('Widget', 'icon_path'),
      'update_interval': config.getint('Widget', 'update_interval'),
    }

    for state in ('active', 'completed', 'default', 'error', 'none', 'scheduled'):
      icon, timeout, urgency = config.get('States', state).split(':')
      settings['states'][state] = {
        'icon': icon,
        'timeout': int(timeout),
        'urgency': urgency
      }

    return settings

  def _set_logger(self, debug_level, log_to_console, log_to_file):
    """Creates an instance of HMDCLogger with appropriate handlers."""

    config_name = self.__class__.__name__

    if debug_level is None:
      hmdclog = hmdclogger.HMDCLogger(config_name, self.settings['debug_level'])
      hmdclog.log_to_file(self.settings['log_file'])
    else:
      hmdclog = hmdclogger.HMDCLogger(config_name, debug_level)

      # There must be at least one handler.
      if log_to_console is False and log_to_file is False:
        raise Exception("You must set a logging handler (console or file).")

      # Log to console and/or file.
      if log_to_console:
        hmdclog.log_to_console()
      if log_to_file:
        hmdclog.log_to_file(self.settings['log_file'])

    return hmdclog

  def create_outages_output(self, sorted_outages):
    """Returns GUI and console output sorted into groups of "completed",
       "active", and "scheduled".

    Arguments:
      sorted_outages (dictionary): Outages sorted into groups.

    Attributes:
      cns_text (string): Link header text for printing to console.
      counter (int): Counts interations for debugging text.
      gui_text (string): Link header text for displaying to the widget.
      icon (string): Icon to use with associated outage status.
      link_color (string): Shared text color for URLs.
      message (string): Formatted text to display on the widget or console.
      timeout (int): Time to keep the widget displayed (milliseconds).
      title (string): Name of the outage.
      urgency (string): Urgency level used by NOTIFY_SEND.

    Returns:
      output (dictionary): GUI and console output sorted into lists.
    """

    cns_text = "Please see the following URL for more information:"
    gui_text = "Right click the outages toolbar icon for more information."
    link_color = 'blue'
    output = {'gui': [], 'console': []}

    #
    # Create output for all completed outages.
    #
    counter = 1
    for completed in sorted_outages['completed']:
      self.hmdclog.log('debug', "")
      self.hmdclog.log('info', "Begin creating output for completed outage #" + str(counter) + ".")
      #
      # Completed outages without a specific end time won't display
      # at all; see sort_outages_by_status() for more information.
      #
      title = completed['title']
      complete_text = title + " is now complete."

      # GUI output
      icon = self.settings['states']['completed']['icon']
      message = complete_text + "\n" + gui_text
      timeout = self.settings['states']['completed']['timeout']
      urgency = self.settings['states']['completed']['urgency']

      output['gui'].append({'icon': icon, 'message': message, 'timeout': timeout,
                  'title': title, 'urgency': urgency})

      self.hmdclog.log('debug', "GUI settings:")
      self.hmdclog.log('debug', "\tTitle: " + title)
      self.hmdclog.log('debug', "\tIcon: " + str(icon))
      self.hmdclog.log('debug', "\tTimeout: " + str(timeout))
      self.hmdclog.log('debug', "\tUrgency: " + str(urgency))

      # Console output
      link = colored(completed['link'], link_color)
      text = colored(complete_text, 'yellow', attrs=['bold'])
      message = text + "\n" + cns_text + "\n\t" + link + "\n"
      output['console'].append(message)

      self.hmdclog.log('debug', "Console output:")
      self.hmdclog.log('debug', "\tText: " + str(complete_text))

      self.hmdclog.log('info', "Finished creating output for completed outage #" +
               str(counter) + ".")
      counter += 1

    #
    # Create output for upcoming outages.
    #
    counter = 1
    for scheduled in sorted_outages['scheduled']:
      self.hmdclog.log('debug', "")
      self.hmdclog.log('info', "Begin creating output for scheduled outage #" +
               str(counter) + ".")

      start_time = self.format_date(scheduled['start_time'], 'start_time')
      title = scheduled['title']
      scheduled_text = title + " is scheduled to start on " + start_time

      # GUI output
      icon = self.settings['states']['scheduled']['icon']
      message = scheduled_text + "\n" + scheduled['link'] + "\n" + gui_text
      timeout = self.settings['states']['scheduled']['timeout']
      urgency = self.settings['states']['scheduled']['urgency']

      output['gui'].append({'icon': icon, 'message': message, 'timeout': timeout,
                  'title': title, 'urgency': urgency})

      self.hmdclog.log('debug', "GUI settings:")
      self.hmdclog.log('debug', "\tTitle: " + title)
      self.hmdclog.log('debug', "\tIcon: " + str(icon))
      self.hmdclog.log('debug', "\tTimeout: " + str(timeout))
      self.hmdclog.log('debug', "\tUrgency: " + str(urgency))

      # Console output
      link = colored(scheduled['link'], link_color)
      text = colored(scheduled['title'], attrs=['bold']) + \
        " is scheduled to start on " + colored(start_time, 'green') + "."
      message = text + "\n" + cns_text + "\n\t" + link + "\n"
      output['console'].append(message)

      self.hmdclog.log('debug', "Console output:")
      self.hmdclog.log('debug', "\tText: " + str(scheduled_text))

      self.hmdclog.log('info', "Finished creating output for scheduled outage #" +
               str(counter) + ".")
      counter += 1

    #
    # Create output for all outages currently in progress.
    #
    counter = 1
    for active in sorted_outages['active']:
      self.hmdclog.log('debug', "")
      self.hmdclog.log('info', "Begin creating output for active outage #" + str(counter) + ".")

      # If end_time exists, add it to the output.
      if active['end_time'] != 0:
        end_time = " until " + self.format_date(active['end_time'], 'end_time')
      else:
        end_time = ""

      title = active['title']
      active_text = title + " is in progress" + end_time

      # GUI output
      icon = self.settings['states']['active']['icon']
      timeout = self.settings['states']['active']['timeout']
      urgency = self.settings['states']['active']['urgency']
      message = active_text + "." + "\n" + gui_text

      output['gui'].append({'icon': icon, 'message': message, 'timeout': timeout,
                  'title': title, 'urgency': urgency})

      self.hmdclog.log('debug', "GUI settings:")
      self.hmdclog.log('debug', "\tTitle: " + title)
      self.hmdclog.log('debug', "\tIcon: " + str(icon))
      self.hmdclog.log('debug', "\tTimeout: " + str(timeout))
      self.hmdclog.log('debug', "\tUrgency: " + str(urgency))

      # Console output
      link = colored(active['link'], link_color)
      text = colored(active['title'], attrs=['bold']) + \
        colored(" is in progress" + end_time + ".", 'red', attrs=['bold'])
      message = text + "\n" + cns_text + "\n\t" + link + "\n"
      output['console'].append(message)

      self.hmdclog.log('debug', "Console output:")
      self.hmdclog.log('debug', "\tText: " + str(active_text))

      self.hmdclog.log('info', "Done creating output for active outage #" + str(counter) + ".")
      counter += 1

    self.hmdclog.log('debug', "")
    self.hmdclog.log('debug', "Created " + str(counter) + " outage(s).")
    return output

  def format_date(self, unixtime, name):
    """Formats a unix timestamp into a readable date and time."""

    datetime_obj = datetime.datetime.fromtimestamp(unixtime)
    timestamp = datetime_obj.strftime("%B %d at %I:%M") + datetime_obj.strftime("%p").lower()
    self.hmdclog.log('debug', "" + name + ": " + str(unixtime) + " converted to " + str(timestamp))

    return timestamp

  def get_notifications(self):
    """
    """

    source = self.settings['working_directory'] + "/outages.xml"
    outages = self.parse_xml(source)
    sorted_outages = self.sort_outages_by_status(outages)
    output = self.create_outages_output(sorted_outages)

    return output

  def parse_xml(self, source):
    """Parses a notification feed into a dictionary.

    Attributes:
      counter (int): Counts interations for debugging text.
      desc (string): The 'description' from the calendar feed.
      end_time (int): The 'end time' in unix format from the calendar feed.
      items (BeautifulSoup element): ResultSet from the notification feed.
      link (string): The 'URL' from the calendar feed.
      mod_time (int): The 'modified time' in unix format from the calendar feed.
      resolved (boolean): If the outage is marked resolved is the description.
      start_time (int): The 'start time' in unix format from the calendar feed.
      title (string): The event 'title' from the calendar feed.

    Returns:
      outages (dictionary): Outages parsed from the notification feed.
    """

    counter = 1
    outages = []

    if os.path.isfile(source):
      with open(source, "r") as file:
        xml_file = BeautifulSoup(file, "xml")
      file.close()
      self.hmdclog.log('debug', "Read in file: " + source)
    else:
      raise Exception("Notifications file not found!")

    # Each outage in the feed is in an <item>...</item>
    items = xml_file.find_all("item")

    for item in items:
      self.hmdclog.log('debug', "")
      self.hmdclog.log('debug', "Begin parsing entry #" + str(counter) + ".")

      dates = {"start_time": int(item.start_time.text),
               "end_time": int(item.end_time.text)}
      self.hmdclog.log('debug', "start time: " + str(dates['start_time']))
      self.hmdclog.log('debug', "end time: " + str(dates['end_time']))

      link = str(item.link.text)
      self.hmdclog.log('debug', "link: " + link)

      mod_time = int(item.mod_time.text)
      self.hmdclog.log('debug', "modified time: " + str(mod_time))

      resolved = True if item.resolved.text == "True" else False
      self.hmdclog.log('debug', "resolved: " + str(resolved))

      title = str(item.title.text)
      self.hmdclog.log('debug', "title: " + title)

      self.hmdclog.log('debug', "Done parsing outage #" + str(counter) + ".")
      counter += 1

      outages.append({"end_time": dates["end_time"],
                      "link": link,
                      "mod_time": mod_time,
                      "resolved": resolved,
                      "start_time": dates["start_time"],
                      "title": title})

    self.hmdclog.log('debug', "")
    self.hmdclog.log('debug', "Parsed " + str(counter) + " outage(s).")

    return outages

  def sort_outages_by_status(self, outages):
    """Sorts outages into one of three categories based on status.

    Arguments:
      outages (dictionary): A list of outages from the ICAL feed.

    Attributes:
      counter (int): Counts interations for debugging text.
      has_ended (boolean):
      has_end_time (boolean):
      has_started (boolean):
      now (int): current date and time as a unix timestamp.
      seconds_until_end (int):
      seconds_until_start (int):
      within_future_scope (boolean):
      within_past_scope (boolean):

    Returns:
      sorted_outages (dictionary): Outages sorted into buckets of
        "completed", "active", and "scheduled".
    """

    sorted_outages = {"completed": [], "scheduled": [], "active": []}
    now = int(time.time())

    #
    # Iterate over each outage and sort it based on several factors.
    #
    counter = 1
    for outage in outages:
      self.hmdclog.log('debug', "")
      self.hmdclog.log('info', "Begin sorting outage #" +
               str(counter) + ": " + outage["title"])

      #
      # Calculates how many seconds until the start and end time.
      #
      seconds_until_start = outage["start_time"] - now
      seconds_until_end = outage["end_time"] - now

      self.hmdclog.log('debug', "seconds until start: " + str(seconds_until_start))
      self.hmdclog.log('debug', "seconds until end: " + str(seconds_until_end))

      #
      # Determines if the outage has started and ended.
      #
      has_started = seconds_until_start <= 0
      has_ended = seconds_until_end <= 0

      self.hmdclog.log('debug', "has started: " + str(has_started))
      self.hmdclog.log('debug', "has ended: " + str(has_ended))

      #
      # Some outages may not have a defined end time.
      #
      has_end_time = outage["end_time"] != 0

      self.hmdclog.log('debug', "has end time: " + str(has_end_time))

      #
      # This should never happen, so attempt to capture it.
      #
      if has_end_time and (has_ended and not has_started):
        raise Exception("Event can't end without starting!")

      #
      # Determines if the outage fits into the defined scopes.
      #
      within_future_scope = seconds_until_start < self.settings['scope_ahead']
      within_past_scope = abs(seconds_until_end) < self.settings['scope_past']

      self.hmdclog.log('debug', "within future scope: " + str(within_future_scope))
      self.hmdclog.log('debug', "within past scope: " + str(within_past_scope))

      #
      # Was previously cast as boolean.
      #
      resolved = outage["resolved"]

      self.hmdclog.log('debug', "resolved: " + str(resolved))

      #
      # Outage is in progress if it:
      #   o has already started
      #   o has not ended or doesn't have an end time
      #   o is not resolved yet
      #
      if (has_started and (not has_ended or not has_end_time)) and not resolved:
        sorted_outages["active"].append(outage)
        self.hmdclog.log('debug', "Added outage to \"active\" queue.")

      #
      # Outage is complete if it:
      #   o has started and ended
      #   o is resolved
      # ...but only display the completed outage if it falls in the
      # scope. NOTE: within_past_scope doesn't work for outages that
      # are missing a defined end time, so those events will not
      # display once they are marked "resolved" in the calendar.
      #
      elif ((has_started and has_ended) or resolved) and within_past_scope:
        sorted_outages["completed"].append(outage)
        self.hmdclog.log('debug', "Added outage to \"completed\" queue.")

      #
      # Outage is upcoming if it:
      #   o has not started
      #   o is not resolved
      # ...but only display the outage if it falls in the scope.
      #
      elif (not has_started and not resolved) and within_future_scope:
        sorted_outages["scheduled"].append(outage)
        self.hmdclog.log('debug', "Added outage to \"scheduled\" queue.")

      #
      # Outage does not meet any of the above three criteria.
      #
      else:
        self.hmdclog.log('debug', "Outage not added to any queue.")

      self.hmdclog.log('debug', "Done sorting outage #" + str(counter) + ".")
      counter += 1

    self.hmdclog.log('debug', "")
    self.hmdclog.log('debug', "Sorted " + str(counter) + " outage(s).")
    return sorted_outages

if __name__ == '__main__':
  pass
