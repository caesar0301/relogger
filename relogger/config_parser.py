'''
Parse configurations of relogger from given file
'''
import ConfigParser as CP

class RLConfig(object):
	''' The general configuration for Relogger
	'''
	source_prefix = 'from'
	dest_prefix = 'toto'
	port_default = 514

	def __init__(self, config=None, source=None, dest=None):
		self.flow_table = list()

		if config is not None:
			# parse config file
			config_parser = CP.SafeConfigParser()
			fp = config if isinstance(config, file) else open(config)
			config_parser.readfp(fp)
			sections = config_parser.sections()

			# double check the correctness of config file
			froms = [s[4:].lstrip('.') for s in sections
				if s.startswith(RLConfig.source_prefix)]
			err_tos = [s for s in sections
				if s.startswith(RLConfig.dest_prefix) and
					s[4:].lstrip('.') not in froms]
			if len(err_tos) != 0:
				raise RuntimeError('You got destinations without any source: %s'
					% err_tos)

			# creat flow table from config file
			for src in froms:
				source = (RLConfig.source_prefix + '.' + src).rstrip('.')
				dest = (RLConfig.dest_prefix + '.' + src).rstrip('.')
				if dest not in sections:
					print("Warnning: omitting unpaired source: %s" % source)
					continue

				host, port = self._get_section_values(config_parser, source)
				shosts = self._assemble_hosts(host, port)

				host, port = self._get_section_values(config_parser, dest)
				dhosts = self._assemble_hosts(host, port)

				thistable = dict()
				for h in shosts:
					thistable[h] = dhosts
				self.flow_table.append(thistable)

		elif None not in (source, dest):
			# create flow table with source and dest strings
			shosts = self._assemble_hosts(source)
			dhosts = self._assemble_hosts(dest)
			thistable = dict()
			for h in shosts:
				thistable[h] = dhosts
			self.flow_table.append(thistable)

		self._detect_loop()

	def _get_section_values(self, config, section):
		""" extract host and port values from a section
		"""
		host = config.get(section, 'host') \
				if config.has_option(section, 'host') else None
		port = config.getint(section, 'port') \
			if config.has_option(section, 'port') else None
		return (host, port)

	def _assemble_hosts(self, host, port=None):
		""" assemble host strings give a pair of host and port
		"""
		if host is None:
			raise RuntimeError('You got a section without host option')
		port = RLConfig.port_default if port is None else port
		hosts = host.split(',')
		return [h if ':' in h else h + ':' + str(port) for h in hosts]

	def _detect_loop(self):
		""" detect loops in flow table, raise error if being present
		"""
		for source, dests in self.flowtable().items():
			if source in dests:
				raise RuntimeError('Loops are not allowed: %s-->%s' % (source, dests))

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

	def flowtables(self):
		""" get a list of flow table for individual source-dest pairs
		"""
		return self.flow_table