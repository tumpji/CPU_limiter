#!/usr/bin/python3
# -*- coding: utf-8 -*-
# =============================================================================
#         FILE: limiter.py
#  DESCRIPTION: Sends SIGSTOP to proceses with high time on cpu if limit reached
#        USAGE: ./limiter.py
#      OPTIONS: --ncpus [int]
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


SLEEP_TIME_THREASHOLD = 0.05 # precent of one cpu
SLEEP_TIME = 1  # sec
WAKE_TIME = 0.2 # sec 


class Locker:
    def __init__(self, allocated_cpus, verbose=False):
        self.list_of_stopped_processes = []
        self.allocated_cpus = allocated_cpus
        self.verbose = verbose

    def _threshold_process_time(self, started):
        passed = (time.time() - started)
        threashold = passed * SLEEP_TIME_THREASHOLD
        return threashold

    def _process_iter(self):
        username = psutil.users()[0].name
        for proc in psutil.process_iter(attrs=[
            'pid', 'cpu_times', 'username', 'name']):
            proc = proc.info
            if proc['username'] == username:
                yield proc

    def overtime(self):
        user_info = psutil.users()[0]
        started = user_info.started

        sum = 0
        for proc in self._process_iter():
            sum += proc['cpu_times']




    def _return_responsible_processes(self):
        user_info = psutil.users()[0]
        started = user_info.started
        threshold_process_time = self._threshold_process_time(started)

        user_name = user_info.name
        mypid = os.getpid()

        r = []
        for proc in psutil.process_iter(
                attrs=['pid', 'cpu_times', 'username', 'name']):
            proc = proc.info
            if proc['username'] != user_name:
                continue
            if proc['pid'] == mypid:
                continue

            t = proc['cpu_times']
            t = t.system + t.user
            if t >= threshold_process_time:
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
        print("Stopping {} ...".format(pid))
        os.kill(pid, signal.SIGSTOP)

    def _run_process(self, pid):
        print("Running {} ...".format(pid))
        os.kill(pid, signal.SIGCONT)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--ncpus', type=int, default=None)
    parser.add_argument('--renew', action='store_true')
    args = parser.parse_args()

    if args.ncpus is None:
        if 'PBS_RESC_TOTAL_PROCS' in os.environ:
            args.ncpus = int(os.environ['PBS_RESC_TOTAL_PROCS'])
            print('Warning: NCPUS is not provided assuming it is {}'.format(args.ncpus))
            print('\tBased on PBS_RESC_TOTAL_PROCS variable')
        else:
            args.ncpus = psutil.cpu_count()
            print('Warning: NCPUS is not provided assuming it is {}'.format(args.ncpus))
            print('\tBased on number of CPUS in system')

    while True:
        l = Locker(args.ncpus)

        while args.renew and l.overtime():
            l.stop()
            time.sleep(SLEEP_TIME) 
            l.run()
            time.sleep(WAKE_TIME)

        if not args.renew and l.overtime():
            l.stop()
            time.sleep(SLEEP_TIME)

            while l.overtime():
                time.sleep(SLEEP_TIME)
            else:
                l.run()
                
        time.sleep(CHECK_EVERY)
            


