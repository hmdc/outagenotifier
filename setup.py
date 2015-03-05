from distutils.core import setup

setup(author='Bradley Frank',
      author_email='bfrank@hmdc.harvard.edu',
      data_files=[
           ('/usr/share/icons/hicolor/scalable/hmdc', [
               'icons/outages-active.svg',
               'icons/outages-completed.svg',
               'icons/outages-default.svg',
               'icons/outages-error.svg',
               'icons/outages-scheduled.svg',]),
           ('/etc/cron.d', ['cron/HMDC_cacheOutages']),
           ('/etc/xdg/autostart', ['startup/hmdcoutages.desktop']),
           ('/etc/profile.d', [
               'startup/hmdcoutages.csh',
               'startup/hmdcoutages.sh']),
           ('/var/spool/outagenotifier',[
               'spool/OutagesCache.ics',
               'spool/OutagesParsed.xml'])],
      description='Displays outage notifications in the RCE.',
      license='GPLv2',
      name='OutageNotifier',
      packages=['outagenotifier'],
      requires=[
           'bs4',
           'icalendar',
           'termcolor',
           'datetime',
           'dateutil',
           'filecmp',
           'gobject',
           'hashlib',
           'lxml',
           'os',
           'pytz',
           're',
           'shutil',
           'sys',
           'time',
           'urllib2',
           'webbrowser'],
      scripts=[
           'scripts/cacheOutages.py',
           'scripts/outageNotifierCLI.py',
           'scripts/outageNotifierGUI.py'],
      url='https://git.huit.harvard.edu/hmdc/outagenotifier',
      version='1.4',
)
