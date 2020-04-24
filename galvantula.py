#! /usr/bin/python3
### 4TU Tools: galvantula.py by LyfeOnEdge, and the 4TU Team
### Build and maintain multiple libget repositories
import os, sys, json, time, signal, argparse, threading, multiprocessing
from collections import deque
from spinarak import Spinner

class Threader:
	def __init__(self, max_worker_threads: int = 3):
		self.queue = deque()
		self.threads = deque()
		self.soft_exit = True #Var to keep track of soft or hard exit status, hitting ctrl+c once will allow builds to finish, hitting it again will result in a hard exit killing the spin threads
		self.kill_ran = False #Var to keep track of if of thread kill has been run

		self.max_worker_threads = max_worker_threads
		self.watchdogrunning = True
		self.stopwatchdog = False #Flag to stop the loop thread

		signal.signal(signal.SIGINT, self.exit)
		signal.signal(signal.SIGTERM, self.exit)

		#Call mainloop
		self._update_running_threads()

	def add(self, callback, arglist: list = []):
		"""Add a callback to be done as a thread with an optional arglist"""
		t = multiprocessing.Process(target = callback, args = arglist)
		#t.daemon = True
		self.queue.append(t)

	#Not to be called by user
	def _update_running_threads(self):
		if self.stopwatchdog:
			self.watchdogrunning = False
			return
		
		self.clear_dead_threads()

		while (self.queue and len(self.threads) < self.max_worker_threads):
			t = self.queue.popleft()
			t.start()
			self.threads.append(t)

		if not self.stopwatchdog:
			self.watchdog = threading.Timer(0.1, self._update_running_threads) # Runs every 100 milliseconds
			self.watchdog.start()

	def clear_dead_threads(self):
		if self.threads:
			for t in list(self.threads):
				if not t.is_alive():
					self.threads.remove(t)

	def kill_threads(self):
		if not self.kill_ran:
			self.kill_ran = True
			print("Killing all worker threads.")
			if self.threads:
				for t in list(self.threads):
					t.terminate()

	def exit(self, _ = None, __ = None):
		if self.soft_exit: 
			#The first time through stop the watchdog which actually just prevents the watchdog thread from being respawning
			#This will allow the current watchdog thread to allow the currently running worker threads to complete
			#Calling this function again will cause a hard exit by killing the worker threads and raising KeyboardInterrupt
			self.soft_exit = False
			self.join()
			print("\nThreader Info - Stopping watchdog")
			self.stopwatchdog = True
			while self.watchdogrunning:
				time.sleep(0.5)
			print("Threader Info - Watchdog stopped")
		else:
			self.kill_threads()	
			raise KeyboardInterrupt("Killed by user.")
	
	def join(self):
		for t in self.threads:
			t.join()

class Skeiner:
	def __init__(self, repos_file: str, max_concurrent_spinners = 3, ignore_non_empty_output = False):
		self.threader = Threader(max_concurrent_spinners)
		self.spinning = False
		self.repos = []
		if not repos_file:
			raise ValueError("Skeiner Error - No repos file provided")
		if type(repos_file) is str:
			if not os.path.isfile(repos_file):
				raise FileNotFoundError(f"Skeiner Error - File not found {repos_file}")
			with open(repos_file) as f:
				repos = json.load(f)
		elif type(repos_file) is list:
			repos = repos_file
		else:
			raise TypeError("Skeiner Error - Failed to obtain repos list from passed repos_file")
		if not repos:
			raise ValueError("Skeiner Error - Provided repos json is empty")

		for repo in repos:
			self.repos.append(Spinner(repo["metadata"], repo["output"], ignore_non_empty_output))

	def spin_all(self):
		if not self.spinning:
			self.spinning = True
			for spinner in self.repos:
				self.threader.add(spinner.spin)
			self.threader.join()
			self.spinning = False
		else:
			print("Skeiner Warning - last session still running, can't spin.")

def maintain(skeiner, interval):
	time.sleep(interval)
	skeiner.spin_all()


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Galvantula by LyfeOnEdge, and the 4TU Team.\n\tBuild and maintain libget repositories from pkgbuild metadata repositories.')
	parser.add_argument("-r", "--repos", help = "Path to repos.json file (defaults to './repos.json)'", required = True)
	parser.add_argument("-i", "--ignore_non_empty_output", action = "store_true", help = "Ignore error raised when trying to build a repo for the first time in a non-empty output dir")
	parser.add_argument("-m", "--maintain", action = "store_true", help = "Maintain a repo or repos by spinning them at an interval")
	parser.add_argument("-d", "--delay", help = "Delay interval in seconds between spins in maintainance mode")
	parser.add_argument("-c", "--concurrent", action = "store_true", help = "Max number of repos to spin concurrently")

	args = parser.parse_args()

	concurrent = args.concurrent or 1
	skeiner = Skeiner(args.repos, concurrent, args.ignore_non_empty_output)
	skeiner.spin_all()

	delay = args.delay or 30 * 60
	if args.maintain:
		maintain(skeiner, delay)