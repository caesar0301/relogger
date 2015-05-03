"""
Relogger server to read UDP logs from multiple sources.
"""
import threading
import SocketServer
from Queue import Queue

from syslog import Syslog

class RLServer(object):

    def __init__(self, flowtable):
        self.flowtable = flowtable
        self.message_queue = Queue()

    @property
    def flowtable(self):
        return self._flowtable

    @flowtable.setter
    def flowtable(self, value):
        self._flowtable = {}
        for k, v in value.items():
            ofiles = []
            logger = Syslog()
            for i in v:
                if i.startswith('file://'):
                    ofiles.append(open(i.replace('file://', ''), 'wb'))
                else:
                    logger.add_host(i)
            self._flowtable[k] = (logger, ofiles)

    def _serve_socket(self, host, port):
    	""" utility function to read socket and send to destinations
    	"""
        mqueue = self.message_queue

        class UDPHandler(SocketServer.BaseRequestHandler):
            def handle(self):
                data = self.request[0].strip()
                mqueue.put(('%s:%d' % (host, port), data))

        server = SocketServer.UDPServer((host, port), UDPHandler)
        server.serve_forever()

    def _serve_file(self, filename, count):
    	""" utility function to read file and send to destinations
    	"""
        for line in open(filename.replace('file://', ''), 'rb'):
            data = line.strip(' \r\n')
            self.message_queue.put((filename, data))

    def _message_consumer(self):
        while True:
            source, data = self.message_queue.get()
            logger, ofiles = self.flowtable[source]
            # sending message
            if logger.host_number > 0:
                logger.send_packet(data)
            if len(ofiles) > 0:
                for f in ofiles:
                    f.write(data + '\n')
                    f.flush()
            self.message_queue.task_done()

    def start(self):
    	"""
    	A quick example:
    	    rlconfig = RLConfig(config=args.config)
    	    server = RLServer(rlconfig.flowtable)
    	    server.start()
    	"""
    	thread_pool = []

        # message consumer
        t = threading.Thread(target=self._message_consumer)
        t.setDaemon(True)
        thread_pool.append(t)

        # message producers
        for source, dest in self._flowtable.items():
            if not source.startswith('file://'):
                host, port = source.split(':')
                t = threading.Thread(target=self._serve_socket, args=(host, int(port)))
                t.setDaemon(True)
                thread_pool.append(t)
            else:
            	t = threading.Thread(target=self._serve_file, args=(source, -1))
            	t.setDaemon(True)
            	thread_pool.append(t)

        # start all threads
        [ t.start() for t in thread_pool ]