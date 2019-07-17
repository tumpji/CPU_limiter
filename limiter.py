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

MAX_OVERTIME_PERC = 0.98    # maximum overtime allowed
MIN_OVERTIME_PERC = 0.96    # end limiting processes by this % overtime
CHECK_EVERY = 10            # if not stopped it will check every [sec] if is not overtime

SLEEP_TIME_THREASHOLD = 0.05    # if automatic selection of processes, this is minimum proportion of cpu time to select a process
SLEEP_TIME = 1                  # time in sleep until it will check again [sec]
WAKE_TIME = 0.2                 # when renew, it will be runing this [sec]


assert MAX_OVERTIME_PERC >= MIN_OVERTIME_PERC
assert CHECK_EVERY > 0
assert WAKE_TIME > 0
assert SLEEP_TIME > 0



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
                proc['time'] = proc['cpu_times'].user + proc['cpu_times'].system
                yield proc

    def overtime(self, MIN=False):
        user_info = psutil.users()[0]
        maxtime = (time.time() - user_info.started) * self.allocated_cpus

        sum = 0
        for proc in self._process_iter():
            sum += proc['time']

        if MIN:
            return maxtime * MIN_OVERTIME_PERC <= sum
        else:
            return maxtime * MAX_OVERTIME_PERC <= sum




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
    parser.add_argument('--ncpus', type=int, default=None, help='number of cores given')
    parser.add_argument('--renew', action='store_true', help='programs may be more safe: pauses program only for limited amount of time')
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

        if l.overtime():
            if args.renew:
                while l.overtime(MIN=True):
                    l.stop()
                    time.sleep(SLEEP_TIME) 
                    l.run()
                    time.sleep(WAKE_TIME)
            else:
                l.stop()
                time.sleep(SLEEP_TIME)

                while l.overtime(MIN=True):
                    time.sleep(SLEEP_TIME)
                l.run()
        time.sleep(CHECK_EVERY)
            


