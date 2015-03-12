#!/usr/bin/env python

from termcolor import colored
import datetime
import os
import time
import webbrowser

__author__ = "Harvard-MIT Data Center DevOps"
__copyright__ = "Copyright 2015, HMDC"
__credits__ = ["Bradley Frank"]
__license__ = "GPLv2"
__maintainer__ = "HMDC"
__email__ = "linux@lists.hmdc.harvard.edu"
__status__ = "Production"

class OutageNotifier:
  """Formats and displays notifications to console or Gnome panel widget.

  Example:
    notifier = OutageNotifier()
    # TODO

  Private Functions:
    _get_settings: Parses the conf file for settings.
    _buttonPressEvent: Captures mouse clicks on the icon widget.
    _getRSSupdateTime: Returns the mtime of the clean RSS feed.

  Public Functions:
    checkForUpdates: Checks for RSS updates by using the clean RSS mtime.
    displayOutages: Prints outages to stdout or widget notifications.
    printToCLI: Calls appropropriate methods to print Outages to CLI.
    sortOutagesByStatus: Groups outages by their status.
    updateWidget: Updates widget icons and handles notification pop-ups.
    widgetInit: Initializes a toolbar icon and handles first check.

  Class Variables:
    CONFIG_FILE (string): Location of conf file to import self.settings.
  """

  CONFIG_FILE = "/etc/outagenotifier.conf"

  def __init__( self ):
    """
    Instance Variables:
      lastUpdate (int): The mtime of the XML file.
    """

    #
    # Set to 0 so the initial run will immediately poll for outages.
    #
    self.lastUpdate = 0

  def _get_settings(self):
    """Parses the conf file for settings."""

    config = ConfigParser.ConfigParser()
    config.read(self.CONFIG_FILE)

    settings = {
      # Debugging
      'debug_level': config.get('Debugging', 'debug_level'),
      'log_file': config.get('Debugging', 'log_file'),
      # Parsing
      'resolved_pattern': config.get('Parsing', 'resolved_pattern'),
      # Sources
      'feed_url': config.get('Sources', 'feed_url'),
      'website_url': config.get('Sources', 'website_url'),
      # WorkingFiles
      'notifications': config.get('WorkingFiles', 'notifications'),
      'preserve_versions': config.getboolean('WorkingFiles', 'preserve_versions'),
      'working_directory': config.get('WorkingFiles', 'working_directory'),
    }

    return settings

  def _getRSSupdateTime( self ):
    """Returns the mtime of the notifications feed."""
    return os.path.getmtime(self.XML_FILE)

  def create_outages_output(self, sorted_outages):
    """Returns GUI and console output based on outage status.

    Arguments:
      sorted_outages (dictionary): Outages sorted into buckets of
        "completed", "active", and "scheduled".

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
      self.hmdclog.log('info', "Begin creating output for active outage #" + \
               str(counter) + ".")

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

      self.hmdclog.log('info', "Finished creating output for active outage #" + \
               str(counter) + ".")
      counter += 1

    self.hmdclog.log('debug', "")
    return output

  def create_outages_output(self, sorted_outages):
    """Returns GUI and console output based on outage status.

    Arguments:
      sorted_outages (dictionary): Outages sorted into buckets of
        "completed", "active", and "scheduled".

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
      self.hmdclog.log('info', "Begin creating output for active outage #" + \
               str(counter) + ".")

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

      self.hmdclog.log('info', "Finished creating output for active outage #" + \
               str(counter) + ".")
      counter += 1

    self.hmdclog.log('debug', "")
    return output

  def sort_outages_by_status(self, outages):
    """Sorts outages into one of three categories based on status.

    Arguments:
      outages (dictionary): Calendar events from the XML notifications feed.

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

      self.hmdclog.log('info', "Completed sorting outage #" + str(counter) + ".")
      counter += 1

    self.hmdclog.log('debug', "")
    return sorted_outages

if __name__ == '__main__':
    pass
