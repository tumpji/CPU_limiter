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
import collections

MAX_OVERTIME_PERC = 0.70    # maximum overtime allowed
MIN_OVERTIME_PERC = 0.50    # end limiting processes by this % overtime
CHECK_EVERY = 10            # if not stopped it will check every [sec] if is not overtime

SLEEP_TIME_THREASHOLD = 0.10    # if automatic selection of processes, this is minimum proportion of cpu time to select a process
SLEEP_TIME = 1                  # time in sleep until it will check again [sec]
WAKE_TIME = 0.2                 # when renew, it will be runing this [sec]


assert MAX_OVERTIME_PERC >= MIN_OVERTIME_PERC
assert CHECK_EVERY > 0
assert WAKE_TIME > 0
assert SLEEP_TIME > 0
assert SLEEP_TIME_THREASHOLD > 0.

class Locker:
    def __init__(self, allocated_cpus, from_now, pids=None, regexp=None):
        self.allocated_cpus = allocated_cpus
        self.from_now = from_now
        self.pids = pids
        self.regexp = regexp

        self.started_time = time.time() if from_now else psutil.users()[0].started
        self.list_of_stopped_processes = []

        # set up initial state
        self.state_in_start = collections.defaultdict(float)
        for proc in self._process_iter():
            self.state_in_start[proc['pid']] = proc['time']

    '''
    def _init_time(self):
        """ return initial time -> user log in / start of script """
        return psutil.users()[0].started if not self.from_now else self.started_time
    '''

    def _threshold_process_time(self):
        """ returns limit from which is process targeted in automatic detection """
        return (time.time() - self.started_time) * SLEEP_TIME_THREASHOLD

    def _process_iter(self):
        """ iterate through all $USER process """
        username = psutil.users()[0].name
        for proc in psutil.process_iter(attrs=[
            'pid', 'cpu_times', 'username', 'name']):
            proc = proc.info
            if proc['username'] == username:
                proc['time'] = proc['cpu_times'].user + proc['cpu_times'].system

                if proc['time'] < self.state_in_start[proc['pid']]:
                    print('Cleaning PID {}'.format(proc['pid']))
                    self.state_in_start[proc['pid']] = 0.

                proc['time'] -= self.state_in_start[proc['pid']]

                yield proc

    def _process_filter(self, input):
        threshold_process_time = self._threshold_process_time()
        for proc in input:
            if proc['time'] >= threshold_process_time:
                yield proc

    def overtime(self, MIN=False):
        maxtime = (time.time() - self.started_time) * self.allocated_cpus

        sum = 0
        for proc in self._process_iter():
            sum += proc['time']
        if MIN: return maxtime * MIN_OVERTIME_PERC <= sum
        else: return maxtime * MAX_OVERTIME_PERC <= sum


    def _return_responsible_processes(self):
        user_info = psutil.users()[0]
        user_name = user_info.name
        mypid = os.getpid()

        r = []
        for proc in self._process_filter(self._process_iter()):
            if proc['pid'] == mypid:
                continue
            print(proc['name'], proc['time'], self._threshold_process_time())
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
        """ stop process by pid """
        print("Stopping {} ...".format(pid))
        #os.kill(pid, signal.SIGSTOP)

    def _run_process(self, pid):
        """ returns to its runing state (by pid)"""
        print("Running {} ...".format(pid))
        #os.kill(pid, signal.SIGCONT)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--from_now', action='store_true')
    parser.add_argument('--ncpus', type=int, default=None, help='number of cores given')
    parser.add_argument('--renew', action='store_true', help='programs may be more safe: pauses program only for limited amount of time')

    parser.add_argument('--pids', type=int, nargs='+', default=None)
    parser.add_argument('--regexp', type=str, nargs='+', default=None)

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

    locker = Locker(args.ncpus, from_now=args.from_now, pids=args.pids, regexp=args.regexp)

    while True:
        time.sleep(CHECK_EVERY)
        print('Check')

        if locker.overtime():
            if args.renew:
                while locker.overtime(MIN=True):
                    locker.stop()
                    time.sleep(SLEEP_TIME) 
                    locker.run()
                    time.sleep(WAKE_TIME)
            else:
                locker.stop()
                time.sleep(SLEEP_TIME)

                while locker.overtime(MIN=True):
                    time.sleep(SLEEP_TIME)
                locker.run()
            


