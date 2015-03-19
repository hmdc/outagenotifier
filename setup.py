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
           ('/etc/xdg/autostart', ['startup/hmdcoutages.desktop']),
           ('/etc/profile.d', [
               'startup/hmdcoutages.csh',
               'startup/hmdcoutages.sh']),
      description='Displays outage notifications in the RCE.',
      license='GPLv2',
      name='OutageNotifier',
      packages=['outagenotifier'],
      requires=[
           'bs4',
           'ConfigParser',
           'gobject',
           'gtk',
           'os',
           'pygtk',
           'pynotify',
           'webbrowser'],
      scripts=[
           'scripts/outages.py',
           'scripts/outagenotifier.py'],
      url='https://git.huit.harvard.edu/hmdc/outagenotifier',
      version='1.5',
)
