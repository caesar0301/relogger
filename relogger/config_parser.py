"""
Configuration parser for relogger.

The parser supports both CLI parameters and configuration file.
As the role of relogger being a relay of syslog, CLI parameters
or the configuration file mainly aim to supply the source and
destination description.

The configuration file is consistent with the style of RFC 822,
and can be parsed with ConfigParser module in Python 2.
The configuration of relogger consists of several [section]s and
each section defines a set of rules about sources and destinations.
A quick example:

    ## comments on configuration starting

    [test1]
    src.port = 514,30514
    dst.host = localhost:666,10.50.1.100:514
    dst.file = output.dat

    [test2]
    src.file = logs.dat
    dst.host = localhost:888

    ## comments on ending

The section name is user-defined and the options of each sections
currently support `src.port`, `src.file`, `dst.host`, `dst.file`.
In a section, at least one src-dst pair should be configured,
The port and file descriptor for source can not co-exist, while
the destination takes no constraints.
For port and host descriptors, multiple values are separated by commas.

The CLI parameters behaves in a similar way with the configuration file,
and obey the rules described above.

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
    if not ipregex.match(hostname) and not hnregex.match(hostname):
        return False
    return True

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
                self.flow_table.append(self._assemble_flowtable(fields))

        else:
            src_host = self._get_hosts_from_names(source) if source else None
            src_file = ['file://' + os.path.abspath(ifile)] if ifile else None
            dst_host = self._get_hosts_from_names(dest) if dest else None
            dst_file = ['file://' + os.path.abspath(ofile)] if ofile else None

            if None not in (source, ifile):
                raise conferr('You got both socket and file for the source, only one required.')
            if dest is None and ofile is None:
                raise conferr('No destination given, at least one required.')

            fields = (src_host, src_file, dst_host, dst_file)
            thistable = self._assemble_flowtable(fields)
            self.flow_table.append(thistable)

        self._detect_loop()

    def _get_hosts_from_ports(self, ports):
        return map(lambda x: 'localhost:%d' % int(x.strip()), ports.split(','))

    def _get_hosts_from_names(self, names):
        result = list()
        hosts = map(lambda x: x.strip(), names.split(','))
        for h in hosts:
            if valid_hostname(h.split(':')[0]):
                result.append(h if ':' in h else '%s:%d' % (h, self.PORT))
            else:
                raise conferr('Invalid hostname: %s' % h.split(':')[0])
        return result

    def _get_section_values(self, config, section):
        """ extract src and dst values from a section
        """
        src_host = self._get_hosts_from_ports(config.get(section, 'src.port')) \
            if config.has_option(section, 'src.port') else None
        src_file = [self._get_abs_filepath(config.get(section, 'src.file'))] \
            if config.has_option(section, 'src.file') else None
        if None not in (src_host, src_file):
            raise conferr('Section "%s" gets both socket and file for the source' % section)

        dst_host = self._get_hosts_from_names(config.get(section, 'dst.host')) \
            if config.has_option(section, 'dst.host') else None
        dst_file = [self._get_abs_filepath(config.get(section, 'dst.file'))] \
            if config.has_option(section, 'dst.file') else None
        if dst_host is None and dst_file is None:
            raise conferr('Section "%s" gets no destinations' % section)

        return (src_host, src_file, dst_host, dst_file)

    def _get_abs_filepath(self, ifile):
        """ validate src or dst file path with self.config_file
        """
        assert ifile is not None
        ifile = self._strip_file_prefix(ifile)
        if ifile[0] != '/':
            ifile = os.path.join(os.path.dirname(self.config_file), ifile)
        return 'file://' + ifile

    def _strip_file_prefix(self, filename):
        return filename[7:] if filename.startswith('file://') else filename

    def _assemble_flowtable(self, values):
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

    @property
    def flowtable(self):
        """ get a flat flow table globally
        """
        ftable = dict()
        for table in self.flow_table:
            for k, v in table.items():
                if k not in ftable:
                    ftable[k] = v
                else:
                    ftable[k] += v
        return ftable

    @property
    def flowtables(self):
        """ get a list of flow table for individual source-dest pairs
        """
        return self.flow_table