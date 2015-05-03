# relogger

A relayer or replicator to send SYSLOG from one or multiple sources to one or
multiple destinations. Flexible configuration is also supported to fit
personalized scenarios.

# Motivation

* Not a replacement of Flume, but being complementary
* Light-weight relay focusing on syslog
* Flexible configuration from/to sockets and files

# Install

    $ sudo pip install -U relogger

# Designs

![Relogger work flow](https://github.com/caesar0301/relogger/raw/master/doc/relogger-flow.png)

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

# Contact

Xiaming Chen, <chenxm35@gmail.com>
