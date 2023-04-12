"""
Python Adapter class which provides an easy way of writing to both the console interface (AMISQL),
and also the real-time messaging API.

Use command line arguments '--help' to view currently configurable arguments
"""

#!/usr/bin/env python3

from enum import Enum
import socket
import logging
import time
import argparse

from ami_py_adapter.constants import Constants
from ami_py_adapter.receiver import Receiver
from ami_py_adapter.writer import Writer
from ami_py_adapter.callback_group import CallbackGroup


class Adapter:
    "Primary adapter class that provides easy write access to the AMI Realtime Server Interface"
        
    args_built = False

    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("AMIAdapter")

    def __init__(self):
        self._rt_logged_in = False
        self._rt_socket = None
        self._logged_in = False
        self._socket = None
        self._receiver = None
        self._writer = None
        self._args = None
        self._monitor_log = None
        self.log_level = logging.INFO
        self.initialized = False

    def init(self, parser = argparse.ArgumentParser()):
        "Initialize adapter class"

        if self._rt_logged_in or self._logged_in:
            return

        if not Adapter.args_built:
            Adapter._build_args(parser)
        self._args = parser.parse_args()

        #Configure log level
        log_level = logging.INFO
        if self._args.debug:
            log_level = logging.DEBUG
        elif self._args.quiet:
            log_level = logging.WARNING
        self.log_level = log_level

        Adapter.logger.setLevel(log_level)

        if self._args.log_file != "":
            fh = logging.FileHandler(self._args.log_file, 'w+')
            fh.setLevel(logging.DEBUG)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            fh.setFormatter(formatter)
            Adapter.logger.addHandler(fh)

        self._monitor_log = self._args.monitor_log

        if not self._init_sockets():
            return

        self.attempt_login()
        self.register_callback("Relay AMI Message", Adapter._output_received_messages)

        Adapter.logger.debug("AMI Adapter Successfully Initialized!")

    def attempt_login(self):
        "Attempts the full sequence of creating a receiver and writer and logging in"
        #Create receiver and writer
        self._receiver = Receiver()
        self._receiver.init(
            logger = Adapter.logger, rt_socket = self._rt_socket, 
            c_socket = self._socket, logfile=self._monitor_log 
        )

        self._writer = Writer()
        self._writer.init(
            logger = Adapter.logger, rt_socket = self._rt_socket, socket = self._socket
        )

        if not self._login(
            rt_login = self._args.rt_id,
            c_login = self._args.c_id,
            c_pw = self._args.c_pw,
            attempts = self._args.login_attempts
        ):
            Adapter.logger.error("Failed to login to AMI Server")
            return
        self.initialized = True

    def remove_callback(self, callback_name: str, callback_group: CallbackGroup = CallbackGroup.ALL_LOGS):
        "Removes a callback for receiving messages"
        if self._receiver is not None:
            self._receiver.remove_callback(callback_name = callback_name, callbackGroup=callback_group)

    def register_callback(self, callback_name: str, callback, callbackGroup: CallbackGroup = CallbackGroup.ALL_LOGS):
        """Registers a callback for receiving messages
           callback is of type - Callable[[str], None]"""
        if self._receiver is not None:
            self._receiver.register_callback(callback_name = callback_name, callback = callback, callbackGroup = callbackGroup)

    def cleanup(self):
        "Performs any cleaning up of the adapter"
        Adapter.logger.debug("Cleaning up adapter")
        if self._writer is not None:
            self._writer.cleanup()
        if self._receiver is not None:
            self._receiver.cleanup()
        self._logged_in = False
        self._rt_logged_in = False
        self.initialized = False
        Adapter.logger.debug("Adapter cleanup complete!")

    def delete_obj(self, table_name: str, uid: str):
        "Sends a delete command to a given table with the given id"
        if not self._rt_logged_in:
            Adapter.logger.warning(
                "Failed to delete object via real-time API (Real-time Adapter not initialized)"
            )
            return

        if len(uid) == 0 or len(table_name) == 0:
            return

        msg = f"{Constants.RT_KEY_DELETE}|"\
            f"{Constants.RT_KEY_ID}=\"{uid}\"|"\
            f"{Constants.RT_KEY_TABLE}=\"{table_name}\""

        #Send value over
        self._writer.rt_add_string(msg)

    def send_obj(self, table_name: str, values, uid = ""):
        """Sends an object to a given table,
           values is treated as a dictionary of string key and string value
           actual string values should be enclosed with double quotes around them"""
        if not self._rt_logged_in:
            Adapter.logger.warning(
                "Failed to send object via real-time API (Real-time Adapter not initialized)"
            )
            return

        if len(values) == 0:
            return

        msg = f"{Constants.RT_KEY_OBJECT}"

        #Add id
        if len(uid) != 0:
            msg += f"|{Constants.RT_KEY_ID}=\"{uid}\""

        #Add table name
        msg += f"|{Constants.RT_KEY_TABLE}=\"{table_name}\""

        #Add values
        for key, val in values.items():
            msg += f"|{key}={val}"

        #Send value over
        self._writer.rt_add_string(msg)

    def send_ami_script(self, ami_script : str):
        "Sends an AMI script to the database"
        if not self._logged_in:
            Adapter.logger.warning(
                "Failed to send object via console (Console Adapter not initialized)"
            )
            return
        Adapter.logger.debug(ami_script)
        self._writer.c_add_string(ami_script)

    def send_rt_message(self, rt_message: str):
        "Sends a raw message via the real-time api"
        if not self._rt_logged_in:
            Adapter.logger.warning(
                "Failed to send object via real-time API (Real-time Adapter not initialized)"
            )
            return
        Adapter.logger.debug(rt_message)
        self._writer.rt_add_string(rt_message)

    def _init_sockets(self) -> bool:
        "Attempt to initialize the sockets according to the current configuration"
        #Real-time Socket initialization
        socket_type = socket.AF_INET if self._args.use_ipv4 else socket.AF_INET6

        if not self._args.disable_realtime:
            try:
                Adapter.logger.debug("Attempting to create real-time socket...")
                self._rt_socket = socket.socket(socket_type, socket.SOCK_STREAM, 0)
                Adapter.logger.debug("Successfully created real-time socket")
            except Exception as exception:
                Adapter.logger.error(f"Could not create real-time socket, exception - {exception}")
                return False
            try:
                Adapter.logger.debug("Attempting to connect to server...")
                self._rt_socket.settimeout(2)
                if self._args.use_ipv4:
                    self._rt_socket.connect((self._args.server_address, self._args.rt_port))
                else:
                    self._rt_socket.connect((self._args.server_address, self._args.rt_port,0,0))

                Adapter.logger.debug(
                    f"Successfully connected to ami server [Info: {self._rt_socket.getpeername()}]"
                )
            except Exception as exception:
                Adapter.logger.error(f"Could not connect to server, exception - {exception}")
                return False

        #Console Socket initialization
        if not self._args.disable_console:
            try:
                Adapter.logger.debug("Attempting to create socket...")
                self._socket = socket.socket(socket_type, socket.SOCK_STREAM, 0)
                Adapter.logger.debug("Successfully created socket")
            except Exception as exception:
                Adapter.logger.error(f"Could not create socket, exception - {exception}")
                return False
            try:
                Adapter.logger.debug("Attempting to connect to server...")
                self._socket.settimeout(2)
                if self._args.use_ipv4:
                    self._socket.connect(
                        (self._args.server_address, self._args.c_port)
                    )
                else:
                    self._socket.connect((self._args.server_address, self._args.c_port,0,0))
                Adapter.logger.debug(
                    f"Successfully connected to ami server [Info: {self._socket.getpeername()}]"
                )
            except Exception as exception:
                Adapter.logger.error(f"Could not connect to server, exception - {exception}")
                return False

        return True

    def _login(self, rt_login: str, c_login: str, c_pw: str, attempts: int) -> bool:
        "Attempt to login for both realtime access as well as console access"

        #Real-time Login
        if not self._args.disable_realtime:
            self.register_callback(
                callback_name = "RT Login callback", callback = self._rt_login_callback, callbackGroup=CallbackGroup.SOCKET_LOGS
            )
            for _ in range(attempts):
                if self._rt_logged_in:
                    break

                Adapter.logger.debug(f"Attempting to login with id {rt_login}")
                self._writer.rt_send_raw_msg(f"L|I=\"{rt_login}\"")
                time.sleep(0.2)

            if not self._rt_logged_in:
                Adapter.logger.error("Failed to login with real-time port, terminating!")
                self.cleanup()
                return False

            self.remove_callback(callback_name = "RT Login callback", callback_group=CallbackGroup.SOCKET_LOGS)

        #Console Login
        if not self._args.disable_console:
            self.register_callback(
                callback_name = "Console Login callback", callback = self._login_callback
            )
            for _ in range(attempts):
                if self._logged_in:
                    break

                Adapter.logger.debug(f"Attempting to login with id {c_login}")
                self._writer.c_send_raw_msg(f"login {c_login} {c_pw}")
                time.sleep(0.2)

            if not self._logged_in:
                Adapter.logger.error("Failed to login with AMISQL port, terminating!")
                self.cleanup()
                return False

            self.remove_callback(callback_name = "Console Login callback")

        Adapter.logger.debug("Successfully logged in!")
        return True

    def _close_socket(self):
        "Closes and cleans up the socket"
        if self._rt_socket is not None:
            Adapter.logger.debug("Closing real-time socket!")
            self._rt_socket.close()
            self._rt_socket = None
        if self._socket is not None:
            Adapter.logger.debug("Closing console socket!")
            self._socket.close()
            self._socket = None

    def _build_args(parser):
        "Builds argparse arguments"

        #Connection settings
        parser.add_argument(
            "-ipv4", "--use-ipv4",
            help = "Use a IPv4 connection for connecting to the server (Defaults to IPv6)",
            action = "store_true",
            default = False
        )

        parser.add_argument(
            "--server-address",
            help = "Specifies the server address to connect to (Defaults to \"::1\")",
            default = "::1"
        )

        #Component settings
        component_group = parser.add_mutually_exclusive_group()

        component_group.add_argument(
            "-rt", "--disable-realtime",
            help = "Disables automatic setup of real-time connection with AMI",
            action = "store_true",
            default = False
        )

        component_group.add_argument(
            "-c", "--disable-console",
            help = "Disables automatic setup with the AMI Backend Console",
            action = "store_true",
            default = False
        )

        #Real-time arguments
        parser.add_argument(
            "--rt-id",
            help = "Login identifier for the realtime console (Defaults to \"demo\")",
            default = "demo"
        )

        parser.add_argument(
            "--rt-port",
            help = "Port number for the realtime console (Defaults to 3289)",
            type = int,
            default = 3289
        )

        #Console arguments
        parser.add_argument(
            "--c-id",
            help = "Login identifier for the AMISQL console (Defaults to \"demo\")",
            default = "demo"
        )

        parser.add_argument(
            "--c-pw",
            help = "Password for the AMISQL console (Defaults to \"demo123\")",
            default = "demo123"
        )

        parser.add_argument(
            "--c-port",
            help = "Port number for the AMISQL console (Defaults to 3290)",
            type = int,
            default = 3290
        )

        parser.add_argument(
            "--monitor-log",
            help="Reads outputs from an AMI log file",
            default=""
        )

        #Log settings
        log_group = parser.add_mutually_exclusive_group()

        log_group.add_argument(
            "-d", "--debug",
            help = "Shows debug logs",
            action = "store_true",
            default = False
        )

        log_group.add_argument(
            "-q", "--quiet",
            help = "Shows only warnings and errors",
            action = "store_true",
            default = False
        )

        parser.add_argument(
            "--login-attempts",
            help = "Number of attempts taken to connect to the AMI Server before failing",
            type = int,
            default = 5
        )

        parser.add_argument(
            "--log-file",
            help = "Filepath to write logs into",
            default = "ami_py_adapter.log"
        )

        Adapter.args_built = True



    def _rt_login_callback(self, input_str: str):
        "Checks for a valid login status"
        result = Receiver.parse_msg(input_str)

        if Constants.RT_LOGIN_SUCCESS in result.message:
            self._rt_logged_in = True

    def _login_callback(self, input_str: str):
        "Checks for a valid login status"

        if (Constants.C_LOGIN_SUCCESS_HEAD in input_str):
            self._logged_in = True

    def _output_received_messages(input_str: str):
        "Prints all messages returned by the AMI Server"
        Adapter.logger.info(f"{input_str}")
