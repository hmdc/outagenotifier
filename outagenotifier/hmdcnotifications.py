#!/usr/bin/env python

__author__ = "Harvard-MIT Data Center DevOps"
__copyright__ = "Copyright 2014, HMDC"
__credits__ = ["Bradley Frank"]
__license__ = "GPL"
__maintainer__ = "HMDC"
__email__ = "linux@lists.hmdc.harvard.edu"
__status__ = "Production"

from hmdcoutages import HMDCOutages
from termcolor import colored
import datetime
import gobject
import os
import time
import webbrowser


class HMDCNotifications:
    """Formats and displays notifications to a CLI or a Gnome panel widget.

    Example:
        nh = HMDCNotifications()
        nh.printToCLI()         # Print outages to CLI (e.g. SSH login)
        nh.widgetInit()         # Creates a GTK widget for notifications.

    Private Functions:
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
        ICON_PATH (string): File path to the widget icons.
        NOTIFY (object): Instance of pynotify class (for replacement later on).
        SCOPE_AHEAD (int): How far into the future upcoming outages should be
            displayed, measured in seconds.
        SCOPE_PAST (int): How far into the past completed outages should be
            displayed, measured in seconds.
        STATES (dictionary): Stores outage variables for the Gnome widget.
        UPDATE_INTERVAL (int): Milliseconds between widget updates.
        WEBSITE_URL (string): The URL of the outages calendar.
        XML_FILE (string): XML file that stores outage information.
    """

    ICON_PATH = "/usr/share/icons/hicolor/scalable/hmdc/"

    NOTIFY = None

    #
    # 31 days = 2678400; 1 week = 604800; 1 day = 86400; 6 hours = 21600
    #
    SCOPE_AHEAD = 2678400
    SCOPE_PAST = 43200

    STATES = {
        "active":
        {
            "file": ICON_PATH + "outages-active.svg",
            "tooltip": "An outage is active.",
            "timeout": 0,
        },
        "completed":
        {
            "file": ICON_PATH + "outages-completed.svg",
            "tooltip": "An outage was recently completed.",
            "timeout": 5000,
        },
        "default":
        {
            "file": ICON_PATH + "outages-error.svg",
            "tooltip": "Processing outages feed.",
            "timeout": 0,
        },
        "error":
        {
            "file": ICON_PATH + "outages-error.svg",
            "tooltip": "There was an error checking for outages.",
            "timeout": 5000,
        },
        "none":
        {
            "file": ICON_PATH + "outages-completed.svg",
            "tooltip": "No upcoming outages.",
            "timeout": 0,
        },
        "scheduled":
        {
            "file": ICON_PATH + "outages-scheduled.svg",
            "tooltip": "There are upcoming outages.",
            "timeout": 10000,
        }
    }

    #
    # 30 seconds = 30000; 1 min = 60000; 5 min = 300000; 10 min = 600000
    #
    UPDATE_INTERVAL = 300000

    WEBSITE_URL = "http://projects.iq.harvard.edu/rce/calendar"
    #WEBSITE_URL = "http://scholar.harvard.edu/bfrank/calendar"

    #
    # Use the Outages class variable to keep things orderly.
    #
    XML_FILE = Outages.DIR + "/" + Outages.PARSED_FILE


    def __init__( self ):
        """
        Instance Variables:
            lastUpdate (int): The mtime of the XML file.
        """

        #
        # Set to 0 so the initial run will immediately poll for outages.
        #
        self.lastUpdate = 0


    def _buttonPressEvent( self, widget, event ):
        """Wrapper function for capturing mouse clicks on the widget."""

        if event.button == 1: # left click
            self.checkForUpdates( True )
        elif event.button == 3: # right click
            webbrowser.open( self.WEBSITE_URL, 2 ) # 2 = open in new tab


    def _getRSSupdateTime( self ):
        """Returns the mtime of the parsed (clean) RSS feed."""

        return os.path.getmtime( self.XML_FILE )


    def checkForUpdates( self, forceUpdate=False ):
        """Re-runs the widget if the RSS feed mtime has changed (i.e. updated).

        Args:
            forceUpdate (boolean): Allows for skipping the mtime check.

        Attributes:
            modTime (int): The file's mtime as a unix timestamp.
        """

        modTime = self._getRSSupdateTime()

        if modTime != self.lastUpdate or forceUpdate:
            parsedOutages = Outages.parseOutagesXML( HMDCOutages(), 1 )
            sortedOutages = self.sortOutagesByStatus( parsedOutages )
            self.displayOutages( sortedOutages, True )

        self.lastUpdate = modTime
        gobject.timeout_add( self.UPDATE_INTERVAL,
                             self.checkForUpdates )


    def displayOutages( self, sortedOutages, useWidget=False ):
        """Prints outage information to stdout or Gnome widget.

        Args:
            sortedOutages (dictionary): Outages sorted into buckets of
                "completed", "active", and "scheduled".

        Attributes:
            cliText (string): Link header text for printing to the CLI.
            guiText (string): Link header text for displaying to the widget.
            linkColor (string): Shared text color for URLs.
        """

        guiText = "Right click the outages toolbar icon for more information."
        cliText = "Please see the following URL for more information:"
        linkColor = "blue"


        def formatDate( unixtime ):
            """Formats a unix timestamp into a readable date and time."""
            timestamp = datetime.datetime.fromtimestamp( unixtime )
            return timestamp.strftime( "%B %d at %I:%M" ) + \
                timestamp.strftime( "%p" ).lower()


        #
        # Set a default icon, important for first runs.
        #
        if useWidget:
            self.icon.set_from_file( self.STATES["none"]["file"] )
            self.icon.set_tooltip( self.STATES["none"]["tooltip"] )

        #
        # Create output for all completed outages.
        #
        for completed in sortedOutages["completed"]:
            #
            # Completed outages without a specific end time won't display
            # at all; see sortOutagesByStatus() for more information.
            #
            endtime = formatDate( completed["endtime"] )
            text = completed["title"] + " is now complete."

            if useWidget:
                self.updateWidget( "completed", text,
                                   completed["link"], guiText )
            else:
                text = colored( text, "yellow", attrs=['bold'] )
                link = colored( completed["link"], linkColor )
                print text + "\n" + cliText + "\n\t" + link + "\n"


        #
        # Create output for upcoming outages.
        #
        for scheduled in sortedOutages["scheduled"]:
            starttime = formatDate( scheduled["starttime"] )

            if useWidget:
                text = scheduled["title"] + \
                       " is scheduled to start on " + starttime
                self.updateWidget( "scheduled", text, \
                                   scheduled["link"], guiText )
            else:
                text = colored( scheduled["title"], attrs=['bold']) + \
                       " is scheduled to start on " + \
                       colored(starttime, "green" ) + "."
                link = colored( scheduled["link"], linkColor )
                print text + "\n" + cliText + "\n\t" + link + "\n"


        #
        # Create output for all outages currently in progress.
        #
        for active in sortedOutages["active"]:
            if active["endtime"] != 0:
                endtime = " until " + formatDate( active["endtime"] )
            else:
                endtime = ""

            if useWidget:
                text = active["title"] + " is in progress" + endtime + "."
                self.updateWidget( "active", text, active["link"], guiText )
            else:
                text = colored( active["title"], attrs=['bold'] ) + \
                       colored( " is in progress" + endtime + ".", \
                       "red", attrs=['bold'] )
                link = colored( active["link"], linkColor )
                print text + "\n" + cliText + "\n\t" + link + "\n"


    def printToCLI( self ):
        """Prints outages to the command line."""

        parsedOutages = Outages.parseOutagesXML( Outages(), 1 )
        sortedOutages = self.sortOutagesByStatus( parsedOutages )
        self.displayOutages( sortedOutages )


    def sortOutagesByStatus( self, parsedOutages ):
        """Sorts outages into one of three categories based on status.

        Args:
            parsedOutages (dictionary): A list of outages from the RSS feed.

        Attributes:
            now (int): current date and time as a unix timestamp.

        Returns:
            sortedOutages (dictionary): Outages sorted into buckets of
                "completed", "active", and "scheduled".
        """

        sortedOutages = { "completed": [], "scheduled": [], "active": [] }
        now = int( time.time() )

        #
        # Iterate over each outage and sort it based on several factors.
        #
        for outage in parsedOutages:
            #
            # Calculates how many seconds until the start and end time.
            #
            secondsUntilStart = outage["starttime"] - now
            secondsUntilEnd = outage["endtime"] - now

            #
            # Determines if the outage has started and ended.
            #
            hasStarted = secondsUntilStart <= 0
            hasEnded = secondsUntilEnd <= 0

            #
            # Some outages may not have a defined end time.
            #
            hasEndtime = outage["endtime"] != 0

            #
            # This should never happen, so attempt to capture it.
            #
            if hasEndtime and ( hasEnded and not hasStarted ):
                raise Exception( "Event can't end without starting!" )

            #
            # Determines if the outage fits into the defined scopes.
            #
            isWithinFutureScope = secondsUntilStart < self.SCOPE_AHEAD
            isWithinPastScope = abs(secondsUntilEnd) < self.SCOPE_PAST

            #
            # Should already be a boolean, but defined for readability.
            #
            resolved = outage["resolved"]

            #
            # Outage is in progress if it:
            #   o has already started
            #   o has not ended or doesn't have an end time
            #   o is not resolved yet
            #
            if hasStarted and ( not hasEnded or not hasEndtime ) and \
                    not resolved:
                sortedOutages["active"].append( outage )

            #
            # Outage is complete if it:
            #   o has started and ended
            #   o is resolved
            # ...but only display the completed outage if it falls in the
            # scope. NOTE: isWithinPastScope doesn't work for outages that
            # are missing a defined end time, so those events will not
            # display once they are marked "resolved" in the calendar.
            #
            elif ( (hasStarted and hasEnded) or resolved ) and \
                    isWithinPastScope:
                sortedOutages["completed"].append( outage )

            #
            # Outage is upcoming if it:
            #   o has not started
            #   o is not resolved
            # ...but only display the outage if it falls in the scope.
            #
            elif not hasStarted and not resolved and isWithinFutureScope:
                sortedOutages["scheduled"].append( outage )

        return sortedOutages


    def updateWidget( self, status, text, link, guiText ):
        """Sets widget icon and displays notifications."""

        self.icon.set_from_file( self.STATES[status]["file"] )
        self.icon.set_tooltip( self.STATES[status]["tooltip"] )

        notifySend = self.NOTIFY.Notification(
            self.STATES[status]["tooltip"],
            text + "\n" + guiText + "\n" + link,
            self.STATES[status]["file"] )
        notifySend.set_urgency( self.STATES[status]["urgency"] )
        notifySend.set_timeout( self.STATES[status]["timeout"] )
        notifySend.show()


    def widgetInit( self ):
        """Initializes the widget and does an initial check for outages."""

        import gtk
        import pygtk
        import pynotify

        #
        # These came from an example widget; not 100% sure what they do.
        #
        pygtk.require('2.0')
        gtk.gdk.threads_init()

        self.NOTIFY = pynotify
        self.NOTIFY.init( "Outage Notifier" )

        self.STATES["active"]["urgency"] = self.NOTIFY.URGENCY_CRITICAL
        self.STATES["completed"]["urgency"] = self.NOTIFY.URGENCY_CRITICAL
        self.STATES["default"]["urgency"] = self.NOTIFY.URGENCY_LOW
        self.STATES["error"]["urgency"] = self.NOTIFY.URGENCY_LOW
        self.STATES["none"]["urgency"] = self.NOTIFY.URGENCY_LOW
        self.STATES["scheduled"]["urgency"] = self.NOTIFY.URGENCY_NORMAL

        #
        # Sets up the icon on the Gnome toolbar.
        #
        self.icon = gtk.status_icon_new_from_file(
            self.STATES["default"]["file"] )
        self.icon.set_tooltip( self.STATES["default"]["tooltip"] )
        self.icon.set_visible( True )

        #
        # Connects the icon to a method based on the signal.
        # GTK signals: https://developer.gnome.org/gtk3/stable/GtkWidget.html
        #
        self.icon.connect( "button-press-event", self._buttonPressEvent )

        #
        # Wait 5 seconds to do the intial outage pop-up. This avoids a bug (?)
        # where the pop-ups disappear immediately.
        #
        gobject.timeout_add( 5000, self.checkForUpdates )
        gtk.main()


if __name__ == '__main__':
    pass
