import os.path
import time
import warnings
from typing import SupportsFloat, Any, Tuple, Dict

import requests
import json

import gymnasium as gym
from gymnasium.core import ObsType

import voyager.utils as U

from .minecraft_launcher import MinecraftInstance
from .process_monitor import SubprocessMonitor


class VoyagerEnv(gym.Env):
    def __init__(
        self,
        mc_port=None,
        azure_login=None,
        server_host="http://127.0.0.1",
        server_port=3000,
        request_timeout=1,
        log_path="./logs",
    ):
        if not mc_port and not azure_login:
            raise ValueError("Either mc_port or azure_login must be specified")
        if mc_port and azure_login:
            warnings.warn("Both mc_port and mc_login are specified, mc_port will be ignored")
        self.mc_port = mc_port
        self.azure_login = azure_login
        self.server = f"{server_host}:{server_port}"
        self.server_port = server_port
        self.request_timeout = request_timeout
        self.log_path = log_path
        self.mineflayer = self.get_mineflayer_process(server_port)
        if azure_login:
            self.mc_instance = self.get_mc_instance()
        else:
            self.mc_instance = None
        self.has_reset = False
        self.reset_options = None
        self.connected = False
        self.server_paused = False

    def get_mineflayer_process(self, server_port):
        U.f_mkdir(self.log_path, "mineflayer")
        file_path = os.path.abspath(os.path.dirname(__file__))
        return SubprocessMonitor(
            commands=["node", U.f_join(file_path, "mineflayer/index.js"), str(server_port)],
            name="mineflayer",
            ready_match=r"Server started on port (\d+)",
            log_path=U.f_join(self.log_path, "mineflayer"),
        )

    def get_mc_instance(self):
        print("Creating Minecraft server")
        U.f_mkdir(self.log_path, "minecraft")
        return MinecraftInstance(
            **self.azure_login,
            mineflayer=self.mineflayer,
            log_path=U.f_join(self.log_path, "minecraft"),
        )

    def send_request(self, url, json_data=None, timeout=None, max_retries=3, backoff_factor=1):
        """
        Send a request to the specified URL, retrying up to max_retries times with exponential backoff.

        Args:
            url (str): The URL to which the request is sent.
            json_data (dict, optional): The JSON data to send in the request. Defaults to None.
            timeout (int): Timeout for the request.
            max_retries (int): Maximum number of retries if the request fails.
            backoff_factor (int): Factor by which to multiply the wait time for each retry.

        Returns:
            requests.Response: The response object from the server.
        """
        effective_timeout = timeout or self.request_timeout
        attempts = 0

        while attempts < max_retries:
            try:
                print(f"Attempt {attempts + 1}: Sending request to {url}")
                response = requests.post(url, json=json_data, timeout=effective_timeout)
                response.raise_for_status()  # Raises an HTTPError for bad responses
                print("Received response successfully.")
                return response
            except requests.exceptions.HTTPError as errh:
                print("HTTP Error:", errh)
            except requests.exceptions.ConnectionError as errc:
                print("Error Connecting:", errc)
            except requests.exceptions.Timeout as errt:
                print("Timeout Error:", errt)
            except requests.exceptions.RequestException as err:
                print("Request Error:", err)

            attempts += 1
            sleep_time = backoff_factor * (2 ** attempts)
            print(f"Retrying in {sleep_time} seconds...")
            time.sleep(sleep_time)

        print("Failed to receive a valid response after several attempts.")
        return None

    def check_process(self):
        if self.mc_instance and not self.mc_instance.is_running:
            self.start_mc_instance()

        self.restart_mineflayer_with_backoff()

        return self.try_server_start_endpoint()

    def start_mc_instance(self):
        print("Starting Minecraft server")
        self.mc_instance.run()
        self.mc_port = self.mc_instance.port
        self.reset_options["port"] = self.mc_instance.port
        print(f"Server started on port {self.reset_options['port']}")

    def restart_mineflayer_with_backoff(self):
        retry, max_retries, backoff_factor = 0, 3, 2
        while retry <= max_retries:
            if not self.mineflayer.is_running():
                print(f"Mineflayer process has exited, restarting (Attempt {retry+1})")
                self.mineflayer.run()
            if self.mineflayer.is_ready():
                print("Mineflayer is ready.")
                break
            time.sleep(backoff_factor ** retry)
            retry += 1
        else:
            raise RuntimeError("Failed to restart Mineflayer after several attempts")

    def try_server_start_endpoint(self):
        try:
            result = self.send_request(f"{self.server}/start", json_data=self.reset_options)
            if result.status_code == 200:
                print("Server started successfully")
                return result.json()
            else:
                print(f"Received non-200 status code: {result.status_code}")
        except RuntimeError as e:
            print(f"Server start failed. Error: {str(e)}")
        raise RuntimeError("Failed to start server via /start endpoint")

    def step(self, code: str, programs: str = "",) -> Tuple[ObsType, SupportsFloat, bool, bool, Dict[str, Any]]:
        if not self.has_reset:
            raise RuntimeError("Environment has not been reset yet")
        self.check_process()
        data = {
            "code": code,
            "programs": programs,
        }
        result = self.send_request(f"{self.server}/step", json_data=data)

        if result.status_code != 200:
            raise RuntimeError("Failed to step Minecraft server")
        returned_data = result.json()
        return json.loads(returned_data)

    def render(self):
        raise NotImplementedError("render is not implemented")

    def reset(self, *, seed=None, options=None, ) -> Tuple[ObsType, Dict[str, Any]]:
        if options is None:
            options = {}
        if options.get("inventory", {}) and options.get("mode", "hard") != "hard":
            raise RuntimeError("Inventory can only be set when mode is 'hard'")

        self.reset_options = {
            "port": self.mc_port,
            "reset": options.get("mode", "hard"),
            "inventory": options.get("inventory", {}),
            "equipment": options.get("equipment", []),
            "spread": options.get("spread", False),
            "waitTicks": options.get("wait_ticks", 5),
            "position": options.get("position", None),
        }

        self.mineflayer.stop()
        time.sleep(1)  # wait for mineflayer to exit

        returned_data = self.check_process()
        if not returned_data:
            raise RuntimeError("Failed to reset environment due to server issues.")

        self.has_reset = True
        self.connected = True
        self.reset_options["reset"] = "soft"

        return json.loads(returned_data)

    def close(self):
        if self.connected:
            result = self.send_request(f"{self.server}/stop", json_data=None)
            if result.status_code == 200:
                self.connected = False
        if self.mc_instance:
            self.mc_instance.stop()
        self.mineflayer.stop()
        return not self.connected

    def pause(self):
        if self.mineflayer.is_running and not self.server_paused:
            result = self.send_request(f"{self.server}/pause", json_data=None)
            if result.status_code == 200:
                self.server_paused = True
        return self.server_paused

    def unpause(self):
        if self.mineflayer.is_running and self.server_paused:
            result = self.send_request(f"{self.server}/pause", json_data=None)
            if result.status_code == 200:
                self.server_paused = False
            else:
                print(result.json())
        return self.server_paused
