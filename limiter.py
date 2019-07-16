#!/usr/bin/python3
# -*- coding: utf-8 -*-
# =============================================================================
#         FILE: limiter.py
#  DESCRIPTION:
#        USAGE:
#      OPTIONS:
# REQUIREMENTS:
#
#      LICENCE:
#
#         BUGS:
#        NOTES:
#       AUTHOR: Jiri Tumpach (tumpji),
# ORGANIZATION:
#      VERSION: 1.0
#      CREATED: 2019 07.16.
# =============================================================================

import signal
import os
import time
import psutil
import argparse

MIN_OVERTIME_PERC = 0.97
MAX_OVERTIME_PERC = 0.99
CHECK_EVERY = 10 # sec

SLEEP_TIME = 1  # sec
WAKE_TIME = 0.2 # sec

class Locker:
    def __init__(self):
        self.list_of_stopped_processes = []

    def _return_responsible_processes():
        mypid = os.getpid()

        user_info = psutil.users()[0]

        started = user_info.started
        user_name = user_info.name


        r = []
        for proc in psutil.process_iter(attrs=['pid', 'cpu_times', 'username']):
            proc = proc.info

            if proc['username'] != user_name:
                continue
            if proc['pid'] == mypid:
                continue
            if proc['cpu_times'] >= maximum_cpu_times:
                r.append(proc['pid'])
        return r


    def stop(self):
        self.list_of_stopped_processes = self._return_responsible_processes()
        for i in self.list_of_stopped_processes:
            self._stop_process(i)

    def run(self):
        for i in self.list_of_stopped_processes:
            self._run_process(i)

    def _stop_process(self, pid):
        os.kill(pid, signal.SIGSTOP)
    def _run_process(self, pid):
        os.kill(pid, signal.SIGCONT)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--ncpus', type=int, default=None)
    args = parser.parse_args()

    if args.ncpus is None:
        args.ncpus = psutil.cpu_count()
        print('Warning: NCPUS is not provided assuming it is {}'.format(args.ncpus))


    while True:
        while overtime():
            l = Locker()
            l.stop()
            time.sleep(SLEEP_TIME) 
            l.run()
            time.sleep(WAKE_TIME)
        else:
            time.sleep(CHECK_EVERY)
            


