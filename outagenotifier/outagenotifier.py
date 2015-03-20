#!/usr/bin/env python

from bs4 import BeautifulSoup
import ConfigParser
import hmdclogger
import gobject
import gtk
import os
import pygtk
import pynotify
import webbrowser

__author__ = "Harvard-MIT Data Center DevOps"
__copyright__ = "Copyright 2015, HMDC"
__credits__ = ["Bradley Frank"]
__license__ = "GPLv2"
__maintainer__ = "HMDC"
__email__ = "linux@lists.hmdc.harvard.edu"
__status__ = "Production"


class OutageNotifier():
  """Displays notifications to a Gnome panel widget.

  Example:
    import outagenotifier
    notifier = outagenotifier.OutageNotifier
    notifier.widget_init()

  Private Functions:
    _button_press_event: Handles mouse clicks on the toolbar icon.
    _get_settings: Parses the conf file for settings.
    _set_logger: Creates a logger.

  Public Functions:
    get_updates: Compares notification file mtime to check for updates.
    output_to_widget: Sets widget icon and displays notifications.
    parse_xml: Reads in widget data from notifications XML file.
    widget_init: Initializes the widget and does initial check for outages.

  Class Variables:
    CONFIG_FILE (string): Full path of the configuration (conf) file.
  """

  CONFIG_FILE = "/etc/outagenotifier.conf"

  def __init__(self, logger=None, debug_level=None,
               log_to_console=False, log_to_file=False, log_file=None):
    """Sets up module settings and a logging instance.

    Parameters:
      logger (instance): Previous instance of hmdclogger.
      debug_level (string): Optionally override the debugging level.
      log_to_console (boolean): Optionally log to console.
      log_to_file (boolean): Optionally log to a file.
      log_file (string): Full path to a log file.

    Attributes:
      settings (dictionary): Global module settings.
      hmdclog (instance): Instance of HMDCLogger for logging.
      last_updated (int): Last time an outages update was seen (unix timestamp).
    """

    self.settings = self._get_settings()
    if logger is not None:
      self.hmdclog = logger
    else:
      self.hmdclog = self._set_logger(debug_level, log_to_console, log_to_file, log_file)

    # Set to zero to force an initial check for outages.
    self.last_updated = 0
    # Set full path to notifications file.
    self.source = self.settings['working_directory'] + "/notifications.xml"

    self.hmdclog.log('debug', "Source file: " + self.source)
    self.hmdclog.log('debug', "Last updated: " + str(self.last_updated))

  def _button_press_event(self, widget, event):
    """Wrapper function for capturing mouse clicks on the widget."""

    if event.button == 1:  # left click
      self.get_updates(True)
    elif event.button == 3:  # right click
      webbrowser.open_new("http://projects.iq.harvard.edu/rce/calendar")

  def _get_settings(self):
    """Parses the conf file for settings."""

    config = ConfigParser.ConfigParser()
    config.read(self.CONFIG_FILE)

    settings = {
      # WorkingFiles
      'working_directory': config.get('WorkingFiles', 'working_directory'),
      # Widget
      'icon_path': config.get('Widget', 'icon_path'),
      'update_interval': config.getint('Widget', 'update_interval')
    }

    return settings

  def _set_logger(self, debug_level, log_to_console, log_to_file, log_file):
    """Creates an instance of HMDCLogger with appropriate handlers."""

    config_name = self.__class__.__name__

    if debug_level is None:
      hmdclog = hmdclogger.HMDCLogger(config_name, 'NOTSET')
      hmdclog.log_to_console()  # A blank handler.
      return hmdclog

    hmdclog = hmdclogger.HMDCLogger(config_name, debug_level)

    # There must be at least one handler.
    if log_to_console is False and log_to_file is False:
      raise Exception("You must set a logging handler (console or file).")

    # Log to console and/or file.
    if log_to_console:
      hmdclog.log_to_console()
    if log_to_file:
      log_file = os.path.expanduser('~') + "/outagenotifier.log"
      hmdclog.log_to_file(log_file)

    return hmdclog

  def get_updates(self, force_update=False):
    """Compares notification file mtime to check for updates.

    Parameters:
      force_update (boolean): Forces widgets to re-display.

    Attributes:
      mtime (int): Last modification time to notifications file.
    """

    mtime = int(os.path.getmtime(self.source))
    self.hmdclog.log('debug', "Notfications mtime: " + str(mtime))
    self.hmdclog.log('debug', "Last updated: " + str(self.last_updated))

    if mtime != self.last_updated:
      self.hmdclog.log('info', "Updates found to outage list.")
      self.last_updated = mtime
      outages = self.parse_xml()
      self.output_to_widget(outages)
    else:
      self.hmdclog.log('info', "No updates found to outage list.")

    gobject.timeout_add(self.settings['update_interval'], self.get_updates)

  def output_to_widget(self, outages):
    """Sets widget icon and displays notifications.

    Parameters:
      outages (dictionary): Widget data for each outage.

    Attributes:
      counter (int): Used for debugging outage parsing.
      default_urgency (instance): Urgency setting for pynotify module.
    """

    counter = 0
    default_urgency = self.notify_urgency['URGENCY_NORMAL']

    for outage in outages:
      counter += 1

      # Setup pop-up elements
      icon = self.settings['icon_path'] + "/" + outage['icon'] + ".svg"
      title = outage['title']
      tooltip = outage['tooltip']
      timeout = outage['timeout']
      urgency = self.notify_urgency.get(outage['urgency'], default_urgency)

      self.hmdclog.log('debug', "Creating widget output #" + str(counter))
      self.hmdclog.log('debug', "\tTitle: " + title)
      self.hmdclog.log('debug', "\tIcon: " + icon)
      self.hmdclog.log('debug', "\tUrgency: " + outage['urgency'])

      # Update the toolbar icon
      self.icon.set_from_file(icon)
      self.icon.set_tooltip(tooltip)

      # Create the actual pop-up
      notify_send = self.notify.Notification(title, tooltip, icon)
      notify_send.set_urgency(urgency)
      notify_send.set_timeout(timeout)
      notify_send.show()

      self.hmdclog.log('debug', "")

  def parse_xml(self):
    """Reads in widget data from notifications XML file."""

    if os.path.isfile(self.source):
      with open(self.source, 'r') as file:
        xml_file = BeautifulSoup(file, 'xml')
      self.hmdclog.log('debug', "Read in file: " + self.source)
    else:
      raise Exception("Notifications file not found!")

    counter = 0
    outages = []
    widgets = xml_file.find_all("widget")

    for widget in widgets:
      counter += 1
      self.hmdclog.log('debug', "Parsing widget #" + str(counter) + ".")

      title = widget.title.text
      icon = widget.icon.text
      timeout = widget.timeout.text
      urgency = widget.urgency.text
      tooltip = widget.tooltip.text

      self.hmdclog.log('debug', "\tTitle: " + title)
      self.hmdclog.log('debug', "\tIcon: " + icon)
      self.hmdclog.log('debug', "\tTimeout: " + timeout)
      self.hmdclog.log('debug', "\tUrgency: " + urgency)
      self.hmdclog.log('debug', "\tFull text: " + tooltip)

      outages.append({'title': title,
                      'icon': icon,
                      'timeout': int(timeout),
                      'urgency': urgency,
                      'tooltip': tooltip})

    return outages

  def widget_init(self):
    """Initializes the widget and does an initial check for outages.

    Attributes:
      icon (instance): GTK toolbar icon.
      notify_urgency (dictionary): Wrapper for pynotify urgency variables.
    """

    #
    # Initialize the pop-up widget.
    #
    self.notify = pynotify
    self.notify.init("OutageNotifier")
    self.notify_urgency = {
        'URGENCY_LOW': self.notify.URGENCY_LOW,
        'URGENCY_NORMAL': self.notify.URGENCY_NORMAL,
        'URGENCY_CRITICAL': self.notify.URGENCY_CRITICAL
    }

    #
    # Initialize PyGTK and setup the toolbar icon.
    #
    gtk.gdk.threads_init()
    default_icon = self.settings['icon_path'] + "/outages-default.svg"
    self.hmdclog.log('debug', "Default icon: " + default_icon)
    self.icon = gtk.status_icon_new_from_file(default_icon)
    self.icon.set_tooltip("Loading...")
    self.icon.set_visible(True)

    #
    # GTK signals: https://developer.gnome.org/gtk3/stable/GtkWidget.html
    #
    self.icon.connect('button-press-event', self._button_press_event)

    #
    # Begin polling for updates.
    #
    gobject.timeout_add(5000, self.get_updates)
    gtk.main()

if __name__ == '__main__':
  pass
