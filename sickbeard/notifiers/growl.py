# Author: Nic Wolfe <nic@wolfeden.ca>
# URL: http://code.google.com/p/sickbeard/
#
# This file is part of SickGear.
#
# SickGear is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# SickGear is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SickGear.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function
import socket

import sickbeard

from sickbeard import logger, common
from sickbeard.exceptions import ex

from lib.growl import gntp


class GrowlNotifier:
    def test_notify(self, host, password):
        self._sendRegistration(host, password, 'Test')
        return self._sendGrowl("Test Growl", "Testing Growl settings from SickGear", "Test", host, password,
                               force=True)

    def notify_snatch(self, ep_name):
        if sickbeard.GROWL_NOTIFY_ONSNATCH:
            self._sendGrowl(common.notifyStrings[common.NOTIFY_SNATCH], ep_name)

    def notify_download(self, ep_name):
        if sickbeard.GROWL_NOTIFY_ONDOWNLOAD:
            self._sendGrowl(common.notifyStrings[common.NOTIFY_DOWNLOAD], ep_name)

    def notify_subtitle_download(self, ep_name, lang):
        if sickbeard.GROWL_NOTIFY_ONSUBTITLEDOWNLOAD:
            self._sendGrowl(common.notifyStrings[common.NOTIFY_SUBTITLE_DOWNLOAD], ep_name + ": " + lang)
            
    def notify_git_update(self, new_version = "??"):
        if sickbeard.USE_GROWL:
            update_text=common.notifyStrings[common.NOTIFY_GIT_UPDATE_TEXT]
            title=common.notifyStrings[common.NOTIFY_GIT_UPDATE]
            self._sendGrowl(title, update_text + new_version)

    def _send_growl(self, options, message=None):

        #Send Notification
        notice = gntp.GNTPNotice()

        #Required
        notice.add_header('Application-Name', options['app'])
        notice.add_header('Notification-Name', options['name'])
        notice.add_header('Notification-Title', options['title'])

        if options['password']:
            notice.set_password(options['password'])

        #Optional
        if options['sticky']:
            notice.add_header('Notification-Sticky', options['sticky'])
        if options['priority']:
            notice.add_header('Notification-Priority', options['priority'])
        if options['icon']:
            notice.add_header('Notification-Icon',
                              'https://raw.github.com/SickGear/SickGear/master/gui/slick/images/sickgear.png')

        if message:
            notice.add_header('Notification-Text', message)

        response = self._send(options['host'], options['port'], notice.encode(), options['debug'])
        if isinstance(response, gntp.GNTPOK): return True
        return False

    def _send(self, host, port, data, debug=False):
        if debug: print('<Sending>\n', data, '\n</Sending>')

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        s.send(data)
        response = gntp.parse_gntp(s.recv(1024))
        s.close()

        if debug: print('<Recieved>\n', response, '\n</Recieved>')

        return response

    def _sendGrowl(self, title="SickGear Notification", message=None, name=None, host=None, password=None,
                   force=False):
        if not sickbeard.USE_GROWL and not force:
            return False

        if name == None:
            name = title

        if host == None:
            hostParts = sickbeard.GROWL_HOST.split(':')
        else:
            hostParts = host.split(':')

        if len(hostParts) != 2 or hostParts[1] == '':
            port = 23053
        else:
            port = int(hostParts[1])

        growlHosts = [(hostParts[0], port)]

        opts = {}

        opts['name'] = name

        opts['title'] = title
        opts['app'] = 'SickGear'

        opts['sticky'] = None
        opts['priority'] = None
        opts['debug'] = False

        if password == None:
            opts['password'] = sickbeard.GROWL_PASSWORD
        else:
            opts['password'] = password

        opts['icon'] = True

        for pc in growlHosts:
            opts['host'] = pc[0]
            opts['port'] = pc[1]
            logger.log(u"GROWL: Sending message '" + message + "' to " + opts['host'] + ":" + str(opts['port']), logger.DEBUG)
            try:
                if self._send_growl(opts, message):
                    return True
                else:
                    if self._sendRegistration(host, password, 'Sickbeard'):
                        return self._send_growl(opts, message)
                    else:
                        return False
            except Exception as e:
                logger.log(u"GROWL: Unable to send growl to " + opts['host'] + ":" + str(opts['port']) + " - " + ex(e), logger.WARNING)
                return False

    def _sendRegistration(self, host=None, password=None, name='SickGear Notification'):
        opts = {}

        if host == None:
            hostParts = sickbeard.GROWL_HOST.split(':')
        else:
            hostParts = host.split(':')

        if len(hostParts) != 2 or hostParts[1] == '':
            port = 23053
        else:
            port = int(hostParts[1])

        opts['host'] = hostParts[0]
        opts['port'] = port

        if password == None:
            opts['password'] = sickbeard.GROWL_PASSWORD
        else:
            opts['password'] = password

        opts['app'] = 'SickGear'
        opts['debug'] = False

        #Send Registration
        register = gntp.GNTPRegister()
        register.add_header('Application-Name', opts['app'])
        register.add_header('Application-Icon',
                            'https://raw.githubusercontent.com/SickGear/SickGear/master/gui/slick/images/ico/apple-touch-icon-72x72.png')

        register.add_notification('Test', True)
        register.add_notification(common.notifyStrings[common.NOTIFY_SNATCH], True)
        register.add_notification(common.notifyStrings[common.NOTIFY_DOWNLOAD], True)
        register.add_notification(common.notifyStrings[common.NOTIFY_GIT_UPDATE], True)
        
        if opts['password']:
            register.set_password(opts['password'])

        try:
            return self._send(opts['host'], opts['port'], register.encode(), opts['debug'])
        except Exception as e:
            logger.log(u"GROWL: Unable to send growl to " + opts['host'] + ":" + str(opts['port']) + " - " + ex(e), logger.WARNING)
            return False


notifier = GrowlNotifier
