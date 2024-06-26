import time
import re
import warnings
from typing import List

import psutil
import subprocess
import logging
import threading

import voyager.utils as U


class SubprocessMonitor:
    def __init__(
            self,
            commands: List[str],
            name: str,
            ready_match: str = r".*",
            log_path: str = "logs",
            callback_match: str = r"^(?!x)x$",  # regex that will never match
            callback: callable = None,
            finished_callback: callable = None,
    ):

        self.commands = commands
        self.name = name
        self.logger = logging.getLogger(name)
        handler = logging.FileHandler(U.f_join(log_path, f"{time.strftime('%Y%m%d_%H%M%S')}.log"))
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        self.process = None
        self.ready_match = ready_match
        self.ready_event = threading.Event()
        self.ready = False  # Indicates whether the subprocess is ready
        self.callback_match = callback_match
        self.callback = callback
        self.finished_callback = finished_callback
        self.match_info = None

    def _start(self):
        self.logger.info(f"Starting subprocess with commands: {self.commands}")

        self.process = psutil.Popen(
            self.commands,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        )
        print(f"Subprocess {self.name} started with PID {self.process.pid}.")

        try:
            for line in iter(self.process.stdout.readline, ""):
                self.logger.info(line.strip())
                if re.search(self.ready_match, line):
                    self.ready = True  # Set the ready flag when the ready condition is met
                    self.ready_event.set()
                    self.match_info = re.search(self.ready_match, line).group(1)
                    self.logger.info(f"Subprocess is ready on {self.match_info}.")
                    # self.logger.info("Subprocess is ready.")
                if re.search(self.callback_match, line) and self.callback:
                    self.callback()
            self.process.wait()
        finally:
            if self.finished_callback:
                self.finished_callback()
            self.logger.info("Subprocess has finished.")
            self.ready_event.set()  # Ensure it's set regardless of subprocess outcome

    def run(self):
        self.ready_event.clear()
        self.ready = False  # Reset ready state
        thread = threading.Thread(target=self._start)
        thread.start()
        self.ready_event.wait()

    def is_ready(self):
        return self.ready

    def stop(self):
        self.logger.info("Stopping subprocess.")
        if self.process and self.process.is_running():
            self.process.terminate()
            self.process.wait()

    def is_running(self):
        if self.process is None:
            return False
        return self.process.is_running()

    def get_match_info(self):
        return self.match_info
