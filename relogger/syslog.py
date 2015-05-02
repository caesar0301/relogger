# Copyright (C) 2005 Graham Ashton <ashtong@users.sourceforge.net>
#
# This module is free software, and you may redistribute it and/or modify
# it under the same terms as Python itself, so long as this copyright message
# and disclaimer are retained in their original form.
#
# IN NO EVENT SHALL THE AUTHOR BE LIABLE TO ANY PARTY FOR DIRECT, INDIRECT,
# SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES ARISING OUT OF THE USE OF
# THIS CODE, EVEN IF THE AUTHOR HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH
# DAMAGE.
#
# THE AUTHOR SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
# PARTICULAR PURPOSE.  THE CODE PROVIDED HEREUNDER IS ON AN "AS IS" BASIS,
# AND THERE IS NO OBLIGATION WHATSOEVER TO PROVIDE MAINTENANCE,
# SUPPORT, UPDATES, ENHANCEMENTS, OR MODIFICATIONS.
#
# $Id: netsyslog.py,v 1.9 2005/11/22 16:35:40 ashtong Exp $
#
# Slightly modified by Xiaming Chen, 2015/05/02.

"""
Syslog module of reSyslog

The format of the UDP packets sent by netsyslog adheres closely to
that defined in U{RFC 3164<http://www.ietf.org/rfc/rfc3164.txt>}. Much
of the terminology used in the RFC has been incorporated into the
names of the classes and properties and is used throughout this
documentation.

"""

import os
import socket
import sys
import time

class Facility:
    """Syslog facilities"""
    KERN, USER, MAIL, DAEMON, AUTH, SYSLOG, \
    LPR, NEWS, UUCP, CRON, AUTHPRIV, FTP = range(12)

    LOCAL0, LOCAL1, LOCAL2, LOCAL3, \
    LOCAL4, LOCAL5, LOCAL6, LOCAL7 = range(16, 24)

class Level:
    """Syslog levels"""
    EMERG, ALERT, CRIT, ERR, \
    WARNING, NOTICE, INFO, DEBUG = range(8)

class PRI(object):

    """The PRI part of the packet.

    Though never printed in the output from a syslog server, the PRI
    part is a crucial part of the packet. It encodes both the facility
    and severity of the packet, both of which are defined in terms of
    numerical constants from the standard syslog module.

    See Section 4.1.1 of RFC 3164 for details.

    """

    def __init__(self, facility, severity):
        """Initialise the object, specifying facility and severity.

        Specify the arguments using constants from the syslog module
        (e.g. syslog.LOG_USER, syslog.LOG_INFO).

        """
        assert facility is not None
        assert severity is not None
        self.facility = facility
        self.severity = severity

    def __str__(self):
        value = self.facility + self.severity
        return "<%s>" % value


class HEADER(object):

    """The HEADER part of the message.

    The HEADER contains a timestamp and a hostname. It is the first
    component of the log message that is displayed in the output of
    syslog.

    See Section 4.1.2 of RFC 3164 for details.

    """

    def __init__(self, timestamp=None, hostname=None):
        """Initialise the object, specifying timestamp and hostname.

        The timestamp represents the local time when the log message
        was created. If the timestamp is not set the current local
        time will be used. See the L{HEADER.timestamp} property
        for a note on the format.

        The hostname should be set to the hostname of the computer
        that originally generated the log message. If the hostname is
        not set the hostname of the local computer will be used. See
        the L{HEADER.hostname} property for a note on the format.

        """
        self.timestamp = timestamp
        self.hostname = hostname

    def __str__(self):
        return "%s %s" % (self.timestamp, self.hostname)

    @property
    def timestamp(self):
        return self._timestamp

    @timestamp.setter
    def timestamp(self, value):
        """
        The local time when the message was written.

        Must follow the format 'Mmm DD HH:MM:SS'.  If
        the day of the month is less than 10, then it
        MUST be represented as a space and then the
        number.

        """
        if not self._timestamp_is_valid(value):
            value = self._calculate_current_timestamp()
        self._timestamp = value

    def _calculate_current_timestamp(self):
        localtime = time.localtime()
        day = time.strftime("%d", localtime)
        if day[0] == "0":
            day = " " + day[1:]
        value = time.strftime("%b %%s %H:%M:%S", localtime)
        return value % day

    def _timestamp_is_valid(self, value):
        if value is None:
            return False
        for char in value:
            if ord(char) < 32 or ord(char) > 126:
                return False
        return True

    @property
    def hostname(self):
        return self._hostname

    @hostname.setter
    def hostname(self, value):
        """
        The hostname where the log message was created.

        Should be the first part of the hostname, or
        an IP address. Should NOT be set to a fully
        qualified domain name.

        """
        if value is None:
            value = socket.gethostname()
        self._hostname = value

class MSG(object):
    """Represents the MSG part of a syslog packet.

    The MSG part of the packet consists of the TAG and CONTENT. The
    TAG and the CONTENT fields must be separated by a non-alphanumeric
    character. Unless you ensure that the CONTENT field begins with
    such a character a seperator of a colon and space will be inserted
    between them when the C{MSG} object is converted into a UDP
    packet.

    See Section 4.1.3 of RFC 3164 for details.

    """

    MAX_TAG_LEN = 32

    def __init__(self, tag=None, content="", pid=None):
        """Initialise the object, specifying tag and content.

        See the documentation for the L{MSG.tag} and
        L{MSG.content} properties for further documentation.

        If the pid is set it will be prepended to the content in
        square brackets when the packet is created.

        """
        self.tag = tag
        self.content = content
        self.pid = pid

    def __str__(self):
        content = self.content
        if self.pid is not None:
            content = "[%s]" % self.pid + content
        return self.tag + content

    @property
    def tag(self):
        return self._tag

    @tag.setter
    def tag(self, value):
        """The name of the program that generated the log message.

        The tag can only contain alphanumeric
        characters. If the tag is longer than {MAX_TAG_LEN} characters
        it will be truncated automatically.

        """
        if value is None:
            value = sys.argv[0]
        self._tag = value[:self.MAX_TAG_LEN]

    @property
    def content(self):
        return self._content

    @content.setter
    def content(self, value):
        """The main component of the log message.

        The content field is a freeform field that
        often begins with the process ID (pid) of the
        program that created the message.

        """
        value = self._prepend_seperator(value)
        self._content = value

    def _prepend_seperator(self, value):
        try:
            first_char = value[0]
        except IndexError:
            pass
        else:
            if first_char.isalnum():
                value = ": " + value
        return value

class Packet(object):
    """Combines the PRI, HEADER and MSG into a packet.

    If the packet is longer than L{MAX_LEN} bytes in length it is
    automatically truncated prior to sending; any extraneous bytes are
    lost.

    """

    MAX_LEN = 1024

    def __init__(self, pri, header, msg):
        """Initialise the object.

        The three arguments must be instances of the L{PRI},
        L{HEADER} and L{MSG} classes.

        """
        self.pri = pri
        self.header = header
        self.msg = msg

    def __str__(self):
        message = "%s%s %s" % (self.pri, self.header, self.msg)
        return message[:self.MAX_LEN]


class Syslog(object):
    """Send log messages to syslog servers.

    The Syslog class provides two different methods for sending log
    messages. The first approach (the L{log} method) is suitable for
    creating new log messages from within a normal application. The
    second (the L{send_packet} method) is designed for use in
    circumstances where you need full control over the contents of
    the syslog packet.

    """

    PORT = 514

    def __init__(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._hostnames = {}

    def add_host(self, hostname):
        """Add hostname to the list of hosts that will receive packets.

        Can be a hostname or an IP address. Note that if the hostname
        cannot be resolved calls to L{log} or L{send_packet} will take
        a long time to return.
        """
        self._hostnames[hostname] = 1

    def remove_host(self, hostname):
        """Remove hostname from the list of hosts that will receive packets."""
        del self._hostnames[hostname]

    def host_number(self):
        return len(self._hostnames)

    def _send_packet_to_hosts(self, packet):
        for hostname in self._hostnames:
            host = hostname
            port = self.PORT
            if ':' in hostname:
                host, port = hostname.split(':')
            self._sock.sendto(str(packet), (host, int(port)))

    def log(self, facility, level, text, pid=False):
        """Send the message text to all registered hosts.

        The facility and level will be used to create the packet's PRI
        part. The HEADER will be automatically determined from the
        current time and hostname. The MSG will be set from the
        running program's name and the text parameter.

        This is the simplest way to use reSyslog.Syslog, creating log
        messages containing the current time, hostname, program name,
        etc. This is how you do it::

            logger = syslog.Syslog()
            logger.add_host("localhost")
            logger.log(Facility.USER, Level.INFO, "Hello World")

        If pid is True the process ID will be prepended to the text
        parameter, enclosed in square brackets and followed by a
        colon.

        """
        pri = PRI(facility, level)
        header = HEADER()
        if pid:
            msg = MSG(content=text, pid=os.getpid())
        else:
            msg = MSG(content=text)
        packet = Packet(pri, header, msg)
        self._send_packet_to_hosts(packet)

    def send_packet(self, packet):
        """Send a L{Packet} object to all registered hosts.

        This method requires more effort than L{log} as you need to
        construct your own L{Packet} object beforehand, but it does
        give you full control over the contents of the packet::

            pri = syslog.PRI(Facility.USER, Level.INFO)
            header = syslog.HEADER("Jun  1 18:34:03", "myhost")
            msg = syslog.MSG("myprog", "Hello World", mypid)
            packet = syslog.Packet(pri, header, msg)

            logger = syslog.Syslog()
            logger.add_host("localhost")
            logger.send_packet(packet)

        """
        self._send_packet_to_hosts(packet)
