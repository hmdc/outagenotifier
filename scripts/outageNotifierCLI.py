#!/usr/bin/env python

"""
This file is invoked from `/etc/profile.d`. It calls a method in Notifications
that handles printing outages to the CLI.
"""

from hmdcnotifications import HMDCNotifications
HMDCNotifications().printToCLI()