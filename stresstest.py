#!/usr/bin/env python

from __future__ import print_function

__author__="Nick Moorman"
__date__="2011-08-05"

import os
import random
import sys
import time
import urllib2

from multiprocessing import Process
from threading import active_count, BoundedSemaphore, Thread

class RequestThread(Thread):
    """Thread subclass to handle each individual request.
    """
    def __init__(self, settings, threadpool, request, outfile):
        """Initializes the thread with its necessary attributes.

        Sets the references to the program's settings, the handling process'
        threadpool, the actual request URL to process, and the output file
        that will simulate the requestTimer.log.
        """
        Thread.__init__(self)
        self.settings = settings
        self.threadpool = threadpool
        self.request = request
        self.outfile = outfile

    def run(self):
        """Makes a request and writes timing output to the log file.

        This is the target method of each spawned thread.  It makes a request
        and writes a log entry that looks like
            YYYY-MM-DD HH:MM:SS|xxxx|requesturi
        where the first section is the date and time the request was made, the
        second section is the duration from the opening of the connection to
        the time the URL's content was read, and the final section is the path
        and query string of the request made (e.g. the full URL minus the
        scheme and domain.
        """
        self.threadpool.acquire()
        try:
            start = time.time()
            response = urllib2.urlopen("{0}".format(self.request))
            response.read()
            # Request duration in milliseconds
            duration = int(1000 * (time.time() - start))
            self.outfile.write("{0}|{1}|{2}\n".format(time.strftime("%Y-%m-%d %H:%M:%S"),
                            duration, self.request))
        except urllib2.HTTPError, httpe:
            print("\t\tError occurred making call {0}: {1}".format(self.request, httpe.code), file=sys.stderr)
        except urllib2.URLError, urle:
            print("\t\tFailed to establish a connection: {0}".format(urle.reason), file=sys.stderr)
        self.threadpool.release()

class RequestProcess(Process):
    """Process subclass to handle a chunk of requests.
    """
    def __init__(self, settings, requests, *args, **kwargs):
        """Initializes the process.

        Sets a reference to the program's settings and sets a list of requests
        to make.  Also passes along any additional positional and keyword
        arguments.
        """
        Process.__init__(self, *args, **kwargs)
        self.settings = settings
        self.requests = requests

    def run(self):
        """Runs threads to make requests.

        This is the target of each process spawned.  It maintains a thread
        pool, and each of the worker threads makes requests.
        """
        threadpool = BoundedSemaphore(self.settings['threads'])
        outfile = open("{0}.out".format(self.name), 'w')
        print("\tSpawned process {0} (pid {1}) to handle {2} requests with {3} threads"
                .format(self.name, os.getpid(), len(self.requests), self.settings['threads']))
        threads = []
        for r in self.requests:
            t = RequestThread(self.settings, threadpool, r, outfile)
            threads.append(t)

        for thread in threads:
            thread.start()

        # Wait for threads to finish running
        while [thread for thread in threads if thread.is_alive()] != []:
            time.sleep(1)

        outfile.close()
        print("\t{0} finished!".format(self.name))

class StressTest:
    """Class to perform the actual stress test.

    Capable of simulating real traffic by performing a multi-process,
    multi-threaded stress test on a system using a set of input URIs.
    """
    def __init__(self):
        """Initializes the class with the default settings."

        Quick rundown of the settings:
        - threads: number of threads to be used by each process
        - processes: number of processes to spawn to handle requests
        - numrequests: total number of sample requests to make
        - logfilename: name of the input file
        """
        self.settings = {
            'threads': 10,
            'processes': 2,
            'numrequests': 1000,
            'logfilename': 'input.txt'
        }

    def chunks(self, l, n):
        """Yield successive n-sized chunks from the list l.

        (borrowed from http://stackoverflow.com/questions/312443/how-do-you-split-a-list-into-evenly-sized-chunks-in-python/312464#312464)
        """
        for i in xrange(0, len(l), n):
            yield l[i:i+n]

    def checkSettings(self):
        """Shows the user the default settings and lets them change them as needed.
        """
        print("Running test with default settings:\n{0}".format(self.settings))
        choice = raw_input("Press Enter to continue, or type 'change' to change: ")
        if choice == '':
            return
        else:
            choice = 'N'
            while choice != 'Y':
                print("Change each setting accordingly (or press Enter to skip it)")
                for k, v in self.settings.iteritems():
                    s = raw_input("{0} (current value is {1}): ".format(k, v))
                    if s != '':
                        self.settings[k] = s if not isinstance(v, int) else int(s)
                print("New settings:\n{0}".format(self.settings))
                choice = raw_input("Everything OK? (Y or N): ")

    def runTest(self):
        """Performs the actual stress test.

        Reads in a requestTimer.log file for a bunch of sample requests, then
        randomizes it and spawns processes that spawn threads to make the
        requests.
        """
        startTime = time.time()
        stresstestLogFile = open('stresstest.log', 'w')
        stresstestLogFile.write("Starting stresstest ({0})\n\n".format(time.strftime("%Y-%m-%d %H:%M:%S")))
        stresstestLogFile.write("Settings:\n{0}\n\n".format(self.settings))

        print("Parsing out requests from log...")
        if not os.access(self.settings['logfilename'], os.F_OK):
            print("{0} does not exist!  Exiting...".format(logFile), file=sys.stderr)
            sys.exit(2)

        # Read the log file and built a list of all requests
        logFile = open(self.settings['logfilename'], 'r')
        requests = []
        for log in logFile.readlines():
            requests.append(log.strip().replace('?null', ''))
        logFile.close()

        # Spawn several processes with some random requests
        processes = []
        random.shuffle(requests)
        requestSample = list(self.chunks(random.sample(requests, self.settings['numrequests']),
                             int(self.settings['numrequests']/self.settings['processes'])))
        for i, s in enumerate(requestSample):
            if i < self.settings['processes']:
                p = RequestProcess(self.settings, random.sample(requests,
                                        int(self.settings['numrequests']/self.settings['processes'])),
                                   name="handleRequests_{0}".format(i))
                p.daemon = True
                processes.append(p)
            else:
                break

        # Start all processes
        for process in processes:
            process.start()

        s = "Started {0} processes with {1} threads each to handle ~{2} requests".format(
                self.settings['processes'], self.settings['threads'], self.settings['numrequests'])
        print(s)
        stresstestLogFile.write("{0}\n\n".format(s))
        print("Please wait while the simulation runs...")

        # Wait until all proceses finish
        while [process for process in processes if process.is_alive()] != []:
            print("Running simulation...")
            time.sleep(5)

        s = "Operation complete in {0} seconds".format(time.time()-startTime)
        print(s)
        stresstestLogFile.write("{0}\n".format(s))

        stresstestLogFile.close()

# "Main function" to run the program
if __name__ == "__main__":
    st = StressTest()
    st.checkSettings()
    st.runTest()

