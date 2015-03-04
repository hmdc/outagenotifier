#!/usr/bin/env python

"""
This file is invoked from `/usr/local/HMDC/etc/RCE/startup`. It calls a method
in Notifications that handles printing outages to the GUI.
"""

from hmdcnotifications import HMDCNotifications
HMDCNotifications().widgetInit()