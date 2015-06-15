from subprocess import Popen, PIPE, STDOUT
import codecs
import threading

import tornado.ioloop

try:
    from queue import Queue
except ImportError: # Python 2
    from Queue import Queue

class PseudoPseudoTerminal(object):
    def __init__(self, popen, encoding='utf-8', codec_errors='replace', loop=None):
        self.popen = popen
        self.encoding = encoding
        self.codec_errors = codec_errors
        self.loop = loop or tornado.ioloop.IOLoop.instance()
        self.decoder = codecs.getincrementaldecoder(encoding)(errors=codec_errors)
        self.queue = Queue(maxsize=5)

    @classmethod
    def spawn(cls, argv, env, cwd):
        assert argv[0] == 'bash'
        argv[:1] = ["C:\\Program Files (x86)\\Git\\bin\\bash.exe", '--login', '-i']
        return cls(Popen(argv, env=env, cwd=cwd, bufsize=0,
                stdin=PIPE, stdout=PIPE, stderr=STDOUT))

    @property
    def fd(self):
        return self.popen.stdout.fileno()

    def write(self, text):
        self.popen.stdin.write(text.encode(self.encoding, self.codec_errors))

    def read(self, nbytes):
        b = self.queue.get()
        if b == b'':
            raise EOFError
        return self.decoder.decode(b, final=False).replace(u'\n', u'\r\n')

    def start_read_thread(self, callback):
        def output_to_queue():
            while True:
                b = self.popen.stdout.read(1)
                self.queue.put(b)
                self.loop.add_callback(callback, self.fd)
                if b == b'':
                    # The pipe was closed, we can stop trying to read it
                    break

        self._read_thread = threading.Thread(target=output_to_queue)
        self._read_thread.daemon = True
        self._read_thread.start()
