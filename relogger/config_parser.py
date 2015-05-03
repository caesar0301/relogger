"""
Configuration parser for relogger.

# Quick Start

The parser supports both CLI parameters and configuration file.  As the role of
relogger being a relay of syslog, CLI parameters or the configuration file
mainly aim to supply the source and destination description.

## Using configuration file

    $ relogger -F config_file.txt

The configuration file is consistent with the style of
[RFC 822](https://www.ietf.org/rfc/rfc0822.txt), and can be parsed with
`ConfigParser` module in Python 2.  The configuration of relogger consists of
several [section]s and each section defines a set of rules about sources and
destinations.  A quick example of `config_file.txt` is like:

    [rule1]
    src.host = localhost
    dst.host = localhost:666
    dst.file = output.dat

    [rule2]
    src.host = 10.50.100.100
    dst.host = 10.50.200.100

The section name is user-defined. Options in each section currently support
`src.host`, `src.file`, `dst.host`, `dst.file`.  In a section, at least one
src-dst pair should be configured.  For host descriptors, multiple values
are separated by commas.

## Using command lines

The CLI parameters behaves in a similar way with the configuration file, and
obey the rules described above. Here we give some quick examples:

* Replicate syslog from port 514 to two local ports:

        $ relogger -s localhost:514 -d localhost:30514,localhost:31514

* Reseive syslog from port 514 and save to a file:

        $ relogger -s localhost:514 -w syslog.txt

* Replay an offline file to remote server on port 514:

        $ relogger -r syslog.txt -d 10.50.200.100

* Replicate syslog from port 514 to remote host and offline file simultaneously:

        $ relogger -s localhost -d 10.50.200.100:514 -w syslog.txt

By Xiaming Chen <chenxm35@gmail.com>, 2015/05/02.

"""
import re
import os
import ConfigParser

class conferr(Exception): pass

def valid_hostname(hostname):
    validIP = r"^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$"
    validHN = r"^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$"

    ipregex = re.compile(validIP)
    hnregex = re.compile(validHN)
    return ipregex.match(hostname) or hnregex.match(hostname)

class RLConfig(object):
    """ The general configuration for Relogger

    Quick example:
        config = relogger.RLConfig(config=your_config_file.txt)
        config.flowtable

    """
    SPREFIX = 'src'
    DPREFIX = 'dst'
    HOST = 'localhost'
    PORT = 514

    def __init__(self, source=None, ifile=None, dest=None, ofile=None, config=None):
        self.flow_table = list()

        if config:
            # parse config file
            config_parser = ConfigParser.SafeConfigParser()
            fp = config if isinstance(config, file) else open(config)
            self.config_file = fp.name
            config_parser.readfp(fp)
            sections = config_parser.sections()

            for s in sections:
                fields = self._get_section_values(config_parser, s)
                thistable = self._assemble_flowtable(fields)
                self.flow_table.append(thistable)

        else:
            src_host = self._get_hosts_from_names(source) if source else None
            src_file = ['file://' + os.path.abspath(ifile)] if ifile else None
            dst_host = self._get_hosts_from_names(dest) if dest else None
            dst_file = ['file://' + os.path.abspath(ofile)] if ofile else None

            if src_host is None and src_file is None:
                raise conferr('No source detected, at least one required.')
            if dst_host is None and dst_file is None:
                raise conferr('No destination detected, at least one required.')

            fields = (src_host, src_file, dst_host, dst_file)
            thistable = self._assemble_flowtable(fields)
            self.flow_table.append(thistable)

        self._detect_loop()

    def _get_section_values(self, config, section):
        """ extract src and dst values from a section
        """
        src_host = self._get_hosts_from_names(config.get(section, 'src.host')) \
            if config.has_option(section, 'src.host') else None
        src_file = [self._get_abs_filepath(config.get(section, 'src.file'))] \
            if config.has_option(section, 'src.file') else None
        if src_host is None and src_file is None:
            raise conferr('Section "%s" gets no sources' % section)

        dst_host = self._get_hosts_from_names(config.get(section, 'dst.host')) \
            if config.has_option(section, 'dst.host') else None
        dst_file = [self._get_abs_filepath(config.get(section, 'dst.file'))] \
            if config.has_option(section, 'dst.file') else None
        if dst_host is None and dst_file is None:
            raise conferr('Section "%s" gets no destinations' % section)

        return (src_host, src_file, dst_host, dst_file)

    def _assemble_flowtable(self, values):
        """ generate a flowtable from a tuple of descriptors.
        """
        values = map(lambda x: [] if x is None else x, values)
        src = values[0] + values[1]
        dst = values[2] + values[3]

        thistable = dict()
        for s in src:
            thistable[s] = dst
        return thistable

    def _detect_loop(self):
        """ detect loops in flow table, raise error if being present
        """
        for source, dests in self.flowtable.items():
            if source in dests:
                raise conferr('Loops detected: %s --> %s' % (source, source))

    def _get_hosts_from_ports(self, ports):
        """ validate hostnames from a list of ports
        """
        hosts = map(lambda x: 'localhost:%d' % int(x.strip()), ports.split(','))
        return list(set(hosts))

    def _get_hosts_from_names(self, names):
        """ validate hostnames from a list of names
        """
        result = set()
        hosts = map(lambda x: x.strip(), names.split(','))
        for h in hosts:
            if valid_hostname(h.split(':')[0]):
                result.add(h if ':' in h else '%s:%d' % (h, self.PORT))
            else:
                raise conferr('Invalid hostname: %s' % h.split(':')[0])
        return list(result)

    def _get_abs_filepath(self, ifile):
        """ validate src or dst file path with self.config_file
        """
        assert ifile is not None
        ifile = ifile[7:] if ifile.startswith('file://') else ifile
        if ifile[0] != '/':
            basedir = os.path.abspath(os.path.dirname(self.config_file))
            ifile = os.path.join(basedir, ifile)
        return 'file://' + ifile

    @property
    def flowtable(self):
        """ get a flat flow table globally
        """
        ftable = dict()
        for table in self.flow_table:
            for k, v in table.items():
                if k not in ftable:
                    ftable[k] = set(v)
                else:
                    [ftable[k].add(i) for i in v]
        # convert set to list
        for k in ftable:
            ftable[k] = list(ftable[k])
        return ftable

    @property
    def flowtables(self):
        """ get a list of flow table for individual source-dest pairs
        """
        return self.flow_table

    def has_source_socket(self):
        hosts = [ i for i in self.flowtable if not i.startswith('file://') ]
        return len(hosts) > 0

    def has_source_file(self):
        files = [ i for i in self.flowtable if i.startswith('file://') ]
        return len(files) > 0