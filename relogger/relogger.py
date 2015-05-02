"""
Relogger server to read UDP logs from multiple sources.
"""
import threading
import SocketServer

from syslog import Syslog

class RLServer(object):

    def __init__(self, flowtable):
        self.flowtable = flowtable

    @property
    def flowtable(self):
        return self._flowtable

    @flowtable.setter
    def flowtable(self, value):
        self._flowtable = {}
        for k, v in value.items():
            logger = Syslog(); ofiles = []
            for i in v:
                if i.startswith('file://'): ofiles.append(i[7:])
                else: logger.add_host(i)
            self._flowtable[k] = (logger, ofiles)

    def _serve_socket(self, host, port, destination):
    	""" utility function to read socket and send to destinations
    	"""
        class UDPHandler(SocketServer.BaseRequestHandler):
            def handle(self):
                data = self.request[0].strip()
                self._send_message(data, destination)

        server = SocketServer.UDPServer((host, port), UDPHandler)
        server.serve_forever()

    def _serve_file(self, filename, destination):
    	""" utility function to read file and send to destinations
    	"""
        for line in open(filename, 'rb'):
            data = line.strip(' \r\n')
            self._send_message(data, destination)

    def _send_message(self, data, destination):
        logger, ofiles = destination
        if logger.host_number > 0:
            logger.send_packet(data)
        if len(ofiles) > 0:
            for f in ofiles:
                open(f, 'ab').write(data + '\n')

    def start(self):
    	"""
    	A quick example:
    	    rlconfig = RLConfig(config=args.config)
    	    server = RLServer(rlconfig.flowtable)
    	    server.start()
    	"""
    	thread_pool = []
        for source, dest in self._flowtable.items():
            if not source.startswith('file://'):
                host, port = source.split(':')
                t = threading.Thread(target=self._serve_socket, args=(host, int(port), dest))
                t.setDaemon(True)
                thread_pool.append(t)
            else:
            	t = threading.Thread(target=self._serve_file, args=(source[7:], dest))
            	t.setDaemon(True)
            	thread_pool.append(t)

        [ t.start() for t in thread_pool ]