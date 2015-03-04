#!/usr/bin/env python

__author__ = "Harvard-MIT Data Center DevOps"
__copyright__ = "Copyright 2014, HMDC"
__credits__ = ["Bradley Frank"]
__license__ = "GPL"
__maintainer__ = "HMDC"
__email__ = "linux@lists.hmdc.harvard.edu"
__status__ = "Production"

from bs4 import BeautifulSoup
from icalendar import Calendar
from lxml import etree
import datetime
import dateutil.parser
import filecmp
import hashlib
import pytz
import re
import shutil
import sys
import time
import os
import urllib2


class HMDCOutages:
    """Module for parsing HMDC outages RSS feed and writing to a cache.

    Example:
        oh = HMDCOutages()
        oh.createCache 

    Public Functions:
        createCache: Calls appropriate methods to write the XML cache file.
        isFeedUpdated: Checks the calendar feed for updates.
        isOutageResolved: Searches outage description for a resolved string.
        parseDateHTML: Find outage dates by parsing HTML.
        parseDateISO: REMOVED; see sources/misc/parseDateISO.py.
        parseOutagesICAL: Parses the calendar ICAL feed.
        parseOutagesXML: Parses the raw RSS feed, and the clean XML version.
        writeParsedXML: Write parsed outage feed to an XML file.

    Class Variables:
        HMDC_ICAL_FEED (string): URL of the calendar ICAL feed.
        HMDC_RSS_FEED (string): URL of the calendar RSS feed.
        DIR (string): Path to RSS/ICAL/XML files.
        ICAL_CACHE (string): A local copy of the ICAL feed.
        ICAL_TEMP (string): Temporary copy of the ICAL feed.
        PARSED_FILE (string): XML of parsed outage info.
        RESOLVED_STRING (string): String for finding completed outages.
        RSS_CACHE (string): A local copy of the RSS feed.
        RSS_TEMP (string): Temporary copy of the RSS feed.
    """

    HMDC_ICAL_FEED = "http://projects.iq.harvard.edu/rce/calendar/export.ics"
    HMDC_RSS_FEED = "http://projects.iq.harvard.edu/rce/calendar/rss.xml"

    DIR = "/var/spool/HMDC/outagenotifier" # No trailing slash

    ICAL_CACHE = "OutagesCache.ics"
    ICAL_TEMP = "OutagesTemp.xml"

    PARSED_FILE = "OutagesParsed.xml"

    RESOLVED_STRING = "52fd10b1ca2d496af32163f088d8ec96"

    RSS_CACHE = "OutagesCache.xml"
    RSS_TEMP = "OutagesTemp.xml"


    def __init__( self ):
        """Assigns initial vaules."""

        #
        # ICAL is the default feed to work with.
        #
        self.feedURL = self.HMDC_ICAL_FEED
        self.cache = self.ICAL_CACHE
        self.temp = self.ICAL_TEMP
        self.parser = self.parseOutagesICAL


    def createCache( self, useRSS=False ):
        """Handles the method calls for creating a cache of the RSS feed."""

        if useRSS is True:
            self.feedURL = self.HMDC_RSS_FEED
            self.cache = self.RSS_CACHE
            self.temp = self.RSS_TEMP
            self.parser = self.parseOutagesXML

        self.isFeedUpdated()

        #if self.isFeedUpdated():
            #outages = self.parser()
            #self.writeParsedXML( outages )

    def isFeedUpdated( self ):
        """Detect updates by parsing the ICAL feed to a temp file and
        comparing to the current parsed XML file.

        Attributes:
            cache (string): Full path to the cache file.
            feed (object): File handler of the feed.
            feedURL (string): URL of the calendar feed to check.
            temp (string): Full path to the temp file.

        Returns:
            feedUpdated (boolean): If the outages feed has been updated.
        """

        #
        # Set variables based on parser being used.
        #
        cache = self.DIR + "/" + self.cache
        temp = self.DIR + "/" + self.temp
        parsed = self.DIR + "/" + self.PARSED_FILE

        #
        # Download a new copy of the calendar feed into a temp file.
        #
        try:
            feed = urllib2.urlopen( self.feedURL )
            with open( cache, "wb" ) as file:
                file.write( feed.read() )
            file.closed
        except urllib2.HTTPError, e:
            print "HTTP Error:", e.code, url
        except urllib2.URLError, e:
            print "URL Error:", e.reason, url

        outages = self.parseOutagesICAL( self.cache )
        self.writeParsedXML( outages, self.temp )

        if os.path.isfile( parsed ):
            feedUpdated = not filecmp.cmp( temp, parsed )
        else:
            #
            # Handles an initial case where the cache hasn't been created yet.
            #
            feedUpdated = True


        if feedUpdated:
            #
            # Make the temp file the new parsed file.
            #
            shutil.move( temp, parsed )
        else:
            #
            # The feed hasn't changed, so just delete the temp file.
            #
            try:
                os.remove( temp )
            except OSError, e:
                    print "Error deleting file: %s - %s." % \
                        ( e.filename, e.strerror )

        return feedUpdated


    def isOutageResolved( self, html ):
        """Attempts to find the resolved string with regex.

        Args:
            html (string): Description of the outage from the RSS feed.

        Attributes:
            resolvedRegex (string): Resolved string in regex form.

        Returns:
            matched (boolean): If the resolved string is present.
        """

        resolvedRegex = "(.*)(" + self.RESOLVED_STRING + ")(.*)"
        regex = re.compile( resolvedRegex, re.MULTILINE )
        matches = regex.search( html )

        #
        # Cast to bool to get True or False, not the actual match.
        #
        return bool( matches )


    def parseDateHTML( self, html ):
        """Parses the description HTML and uses regex to find human readable
        outage start and end time.

        Args:
            html (string): Description of the outage from the RSS feed.

        Attributes:
            months (tuple): List of months in three letter notation.
            regex (string): For parsing the human readable dates and times.
            dates (list): A list for staging parsed outage times.

        Returns:
            dataDict (dictionary): The start and end time as unix timestamps.
        """

        months = ( "Jan", "Feb", "Mar", "Apr", "May", "Jun", \
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec" )
        regex = "(\w{3})\s(3[01]|[12][0-9]|0[1-9])|(\d{4})|([0-5]?[0-9]):([0-5][0-9])(am|pm)"
        dates = []
        dateDict = {}

        #
        # The description tag contains both the event date, and the event
        # description. Splitting the HTML by this div tag breaks it into
        # two halves; the first half contains the dates.
        #
        desc = BeautifulSoup( html )
        eventInfo = desc.find_all( "div", class_=re.compile('even') )

        #
        # Searches the first half of the event description for the human
        # readable dates, using the defined regex. The first pair represent
        # the start time. The second pair is the end time. An example result:
        #
        # [('Mar', '24', '', '', '', ''), ('', '', '', '8', '35', 'am'),
        #  ('Mar', '25', '', '', '', ''), ('', '', '', '9', '35', 'pm')]
        # [('Mar', '26', '', '', '', ''), ('', '', '', '10', '10', 'pm')]
        # [('Mar', '27', '', '', '', '')]
        # [('Mar', '28', '', '', '', ''), ('', '', '', '3', '00', 'pm'),
        #  ('', '', '', '5', '00', 'pm')]
        # [('Mar', '29', '', '', '', ''), ('Mar', '30', '', '', '', '')]
        #
        #   o The year only appears if not the current year
        #   o The entire second pair (end time) may not exist
        #   o The second hour/minute/period may not have an associated
        #       month/day/year (ends on the same day)
        #   o The first month/day/year may not have an associated
        #       hour/minute/period (event is all day)
        #   o Both sections can be missing their associated
        #       hour/minute/period (event is multiple days long)
        #
        pattern = re.compile( regex, re.MULTILINE )
        matches = pattern.findall( str(eventInfo[0]) )

        #
        # Drop the blank strings from the regex matches. An example result:
        #
        # [('Mar', '24'), ('8', '35', 'am'), ('Mar', '25'), ('9', '35', 'pm')]
        # [('Mar', '26'), ('10', '10', 'pm')]
        # [('Mar', '27')]
        # [('Mar', '28'), ('3', '00', 'pm'), ('5', '00', 'pm')]
        # [('Mar', '29'), ('Mar', '30')]
        #
        for result in matches:
            dates.append( filter(None, result) )

        #
        # The number of elements in the list is used to determine what format
        # the outage is in, and how to pad it to a standard format.
        #
        numDateElements = len( dates )

        #
        # Fill in missing information as to make the lists follow a set format.
        # An example result:
        #
        # [('Mar', '24'), ('8', '35', 'am'), ('Mar', '25'), ('9', '35', 'pm')]
        # [('Mar', '26'), ('10', '10', 'pm')]
        # [('Mar', '27'), ('12', '00', 'am'), ('Mar', '27'), ('11', '59', 'pm')]
        # [('Mar', '28'), ('3', '00', 'pm'), ('Mar', '28'), ('5', '00', 'pm')]
        # [('Mar', '29'), ('12', '00', 'am'), ('Mar', '30'), ('11', '59', 'pm')]
        #
        if numDateElements == 4:
            pass
        elif numDateElements == 3:
            dates.insert( 2, dates[0] )
        elif numDateElements == 2:
            if dates[1][0] in months:
                dates = [ dates[0], ("12", "00", "am"), dates[1], \
                        ("11", "59", "pm") ]
        elif numDateElements == 1:
            dates += ( ("12", "00", "am"), dates[0], ("11", "59", "pm") )
        else:
            raise Exception( "Unexpected number of raw date elements found!" )

        #
        # The previous padding reduced the amount of formats down to two.
        # Getting the length of the list tells us which format is being used.
        # Specifically, which outages do not have an end time.
        #
        numCleanedDateElements = len( dates )

        #
        # The following function is used, as opposed to a loop, to handle
        # formatting the start and end datetimes.
        #
        def formatDateAsUnix( dates, index ):
            """Converts the human-readable date to a unix timestamp.

            Args:
                dates (list): The list of date elements.
                index (int): Denotes which section of the list to use.

            Returns:
                unixtime (string): The event time as a unix timstamp.
            """

            #
            # Day and hour need to be zero-padded. The current year is used
            # if it's not provided.
            #
            month = dates[index][0]
            day = "%02d" % int( dates[index][1] )
            hour = "%02d" % int( dates[index+1][0] )
            minute = dates[index+1][1]
            seconds = "00"
            period = dates[index+1][2]

            #
            # There are three elements in the list if the year was included.
            #
            if len( dates[index] ) == 3:
                year = str( dates[index][2] )
            elif len( dates[index] ) == 2:
                year = str( datetime.datetime.now().year )
            else:
                raise Exception( "Unexpected result computing year!" )

            completeDate = month + " " + day + " " + year + " " + hour + \
                           " " + minute + " " + seconds + " " + period

            #
            # Convert the new concatenated date into a unix timestamp.
            #
            dateTuple = time.strptime( completeDate, "%b %d %Y %I %M %S %p" )
            unixtime = int( time.mktime(dateTuple) )
            return str( unixtime )

        #
        # The start time is always present; calculate the unix timestamp.
        #
        dateDict["starttime"] = formatDateAsUnix( dates, 0 )

        #
        # If an end time exists, also calculate it's unix timestamp. Else,
        # set it to a zero'd unix timestamp.
        #
        if numCleanedDateElements > 2:
            dateDict["endtime"] = formatDateAsUnix( dates, 2 )
        else:
            dateDict["endtime"] = "0" * 10

        return dateDict


    def parseOutagesICAL( self, source=None ):
        """Parses an outages ICAL file.
        Arguments:
            source (string): Filename to parse.

        Attributes:
            source (string): Full path to the ICAL source file.

        Returns:
            outages (list) - A parsed list of the outages ICAL feed.
        """

        # Parse the cache file by default.
        source = source or self.cache
        # Add in the full path to the source file.
        source = self.DIR + "/" + source
        # Initialize outages list.
        outages = []

        if os.path.isfile( source ):
            with open( source, "rb" ) as inFile:
                hmdcCal = Calendar.from_ical( inFile.read() )
            inFile.closed
        else:
            raise Exception( "ICAL file not found!" )


        def convertISOtoUnix( isodate ):
            """Converts ISO8601 datetime to a unix timestamp."""

            # From python-dateutil; converts ISO to datetime object.
            dtobject = dateutil.parser.parse( isodate )
            # Converts the datetime object to tuple format.
            dtTuple = dtobject.timetuple()
            # Converts the tuple into a unix timestamp (floating point).
            timestamp = time.mktime( dtTuple )
            # Casts the floating point to int.
            return int( timestamp )


        for component in hmdcCal.walk():
            if component.name == "VEVENT":
                desc = component.get( "DESCRIPTION" )
                endtime = convertISOtoUnix( component.get('DTEND').to_ical() )
                link = component.get('URL')
                modtime = convertISOtoUnix(
                                component.get('LAST-MODIFIED').to_ical() )
                resolved = self.isOutageResolved( desc )
                starttime = convertISOtoUnix(
                                component.get('DTSTART').to_ical() )
                title = self.sanitizeText( component.get('SUMMARY') )

                #
                # If there's no endtime, ICAL sets it to be equal to the
                # starttime, which we don't want; so zero it out.
                #
                if endtime == starttime:
                    endtime = "0" * 10

                outages.append({ "endtime": str(endtime),
                                 "link": str(link),
                                 "modtime": str(modtime),
                                 "resolved": str(resolved),
                                 "starttime": str(starttime),
                                 "title": title })

        return outages


    def parseOutagesXML( self, parse=0 ):
        """Parses an RSS or XML file.

        Args:
            parse (int): Which file to parse.
                o 0 - The original RSS feed (default).
                o 1 - The clean (parsed) XML file.

        Attributes:
            source (string): Full path the file to parse.

        Returns:
            outages (list) - A parsed list of the outages RSS feed.
        """

        if parse == 0:
            source = self.DIR + "/" + self.RSS_CACHE
        elif parse == 1:
            source = self.DIR + "/" + self.PARSED_FILE

        outages = []

        if os.path.isfile( source ):
            with open( source, "r" ) as inFile:
                rssFeed = BeautifulSoup( inFile, "xml" )
            inFile.closed
        else:
            raise Exception( "XML file not found!" )

        #
        # Each outage in the feed is in an <item>...</item>
        #
        items = rssFeed.find_all( "item" )

        for item in items:
            if parse == 0:
                #
                # For output to XML file; all variables must be strings.
                #   o dates: parsed from the HTML description
                #   o link: taken directly from source
                #   o modtime: No modified time from RSS; "blank" timestamp
                #   o resolved: search description for resolved string
                #   o title: sanitize illegal characters
                #
                dates = self.parseDateHTML( item.description.text )
                link = str( item.link.text )
                modtime = "0" * 10
                resolved = self.isOutageResolved( item.description.text )
                resolved = str( resolved )
                title = self.sanitizeText( item.title.text )
            elif parse == 1:
                #
                # For displaying outages to the user via CLI or widget.
                #   o dates: cast to int for doing math
                #   o link: taken directly from source
                #   o modtime: cast to int for doing math
                #   o resolved: cast to boolean for testing
                #   o title: sanitize again in case of tampering
                #
                dates = { "starttime": int(item.starttime.text),
                          "endtime": int(item.endtime.text) }
                link = str( item.link.text )
                modtime = int( item.modtime.text )
                resolved = True if item.resolved.text == "True" else False
                title = self.sanitizeText( item.title.text )
            else:
                raise Exception( "Unable to find source RSS for parsing!" )

            outages.append({ "endtime": dates["endtime"],
                             "link": link,
                             "modtime": modtime,
                             "resolved": resolved,
                             "starttime": dates["starttime"],
                             "title": title })

        return outages


    def sanitizeText( self, text ):
        """Replaces non-alphanumeric characters with underscores."""
        pattern = re.compile( r'[^\w\s]', re.MULTILINE )
        return re.sub( pattern, "_", str(text) )


    def writeParsedXML( self, outages, output=None ):
        """Creates a new, clean RSS feed in XML, for easy notification parsing.

        Args:
            outages (list): A parsed list of the outages RSS feed.
            output (string): Name of the file to save to.

        Attributes:
            output: Path and file for the XML output.
            root: Top element in the XML tree.
            tree: Wrapper to save elements in XML format.
        """

        # Write to the parsed XML file by default.
        output = output or self.PARSED_FILE
        # Add in the full path to the output file.
        output = self.DIR + "/" + output

        root = etree.Element( "outages" )
        tree = etree.ElementTree( root )

        for outage in outages:
            #
            # Create a subelement for each outage:
            #   o title (the name of the ouage)
            #   o link (URL to the calendar event)
            #   o resolved (boolean, if the event is resolved)
            #   o starttime (the event's start time)
            #   o endtime (the event's end time)
            #   o modtime (last modification time)
            #
            item = etree.SubElement( root, "item" )

            title = etree.SubElement( item, "title" )
            title.text = outage["title"]

            link = etree.SubElement( item, "link" )
            link.text = outage["link"]

            resolved = etree.SubElement( item, "resolved" )
            resolved.text = outage["resolved"]

            starttime = etree.SubElement( item, "starttime" )
            starttime.text = outage["starttime"]

            endtime = etree.SubElement( item, "endtime" )
            endtime.text = outage["endtime"]

            modtime = etree.SubElement( item, "modtime" )
            modtime.text = outage["modtime"]

        #
        # The "pretty_print" argument writes the XML in tree form.
        #
        with open( output, 'w' ) as file:
            tree.write( file, pretty_print=True, xml_declaration=True )
        file.closed


if __name__ == '__main__':
    Outages().createCache( True )