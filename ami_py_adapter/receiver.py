"""
Threaded receiver class which reads and formats messages from the
real-time as well as console ports
"""

#!/usr/bin/env python3

import socket
import threading
import os
import time

from ami_py_adapter.parsed_message import ParsedMessage
from ami_py_adapter.callback_group import CallbackGroup

class Receiver:
    "Receiver class which handles messages from the AMI Server"

    logger = None

    def __init__(self):
        self._rt_socket = None
        self._socket = None
        self._should_run = True

        self._accum_string = ""
        self._rt_accum_string = ""
        self._logfile = ""

        #Registered callbacks
        #Messages from socket
        self._receiver_callbacks = {}
        #Messages from log file
        self._receiver_log_callbacks = {}

        self._rt_receiver_process = None
        self._receiver_process = None
        self._logfile_process = None

    def init(self, logger, rt_socket, c_socket, logfile):
        "Initialize receiver class"
        Receiver.logger = logger

        self._rt_socket = rt_socket
        self._socket = c_socket
        self._logfile = logfile

        #Create threads
        Receiver.logger.debug("Starting receiver threads...")

        if self._rt_socket is not None:
            self._rt_receiver_process = threading.Thread(
                name = "Real-time Receiver Thread", target = self._rt_receiver, args = ()
            )
            self._rt_receiver_process.start()

        if self._socket is not None:
            self._receiver_process = threading.Thread(
                name = "Console Receiver Thread", target = self._receiver, args = ()
            )
            self._receiver_process.start()

        if self._logfile != "":
            if os.path.exists(self._logfile):
                self._logfile_process = threading.Thread(
                    name="Logfile Thread", target=self._logfile_parser, args=()
                )
                self._logfile_process.start()
        else:
            Receiver.logger.debug("Log file does not exist")
        Receiver.logger.debug("Receiver threads started!")

    def cleanup(self):
        "Performs any cleaning up of the receiver class"
        Receiver.logger.debug("Cleaning up receiver class")
        self._should_run = False
        if self._rt_receiver_process is not None:
            self._rt_receiver_process.join()
            self._rt_receiver_process = None
        if self._receiver_process is not None:
            self._receiver_process.join()
            self._receiver_process = None
        if self._logfile_process is not None:
            self._logfile_process.join()
            self._logfile_process = None
        Receiver.logger.debug("Receiver class cleaned up!")

    def remove_callback(self, callback_name: str, callbackGroup: CallbackGroup = CallbackGroup.ALL_LOGS):
        "Removes a callback for receiving messages"
        if callbackGroup == CallbackGroup.ALL_LOGS:
            self._receiver_callbacks.pop(callback_name)
            self._receiver_log_callbacks.pop(callback_name)
        elif callbackGroup == CallbackGroup.SOCKET_LOGS:
            self._receiver_callbacks.pop(callback_name)
        else:
            self._receiver_log_callbacks.pop(callback_name)
        Receiver.logger.debug(f"Removed callback {callback_name}")

    def register_callback(self, callback_name: str, callback, callbackGroup: CallbackGroup = CallbackGroup.ALL_LOGS):
        """Registers a callback for receiving messages
           callback is of type : Callable[[str], None]"""
        if callbackGroup == CallbackGroup.ALL_LOGS:
            self._receiver_callbacks[callback_name] = callback
            self._receiver_log_callbacks[callback_name] = callback
        elif callbackGroup == CallbackGroup.SOCKET_LOGS:
            self._receiver_callbacks[callback_name] = callback
        else:
            self._receiver_log_callbacks[callback_name] = callback
        
        Receiver.logger.debug(f"Registered new callback {callback_name}")

    @staticmethod
    def parse_msg(msg: str) -> ParsedMessage:
        """Returns a parsed message class containing the result message,
           error status, sequence number, and id"""
        id_idx = msg.find('|')
        seq_idx = msg.find('|', id_idx + 1)
        status_idx = msg.find('|', seq_idx + 1)

        msg_id = msg[0:id_idx]
        seq_num = msg[id_idx + 1:seq_idx]
        if not seq_num.startswith("Q="):
            raise Exception(f"Failed to parse sequence number [{seq_num}]")
        seq_num = int(seq_num[2:])

        status = msg[seq_idx + 1:status_idx]
        if not status.startswith("S="):
            raise Exception(f"Failed to parse status number [{status}]")
        status = int(status[2:])

        message = msg[status_idx + 1:]
        if not message.startswith("M=\""):
            raise Exception(f"Failed to parse message [{message}]")
        message = message[3:]

        return ParsedMessage(uid = msg_id, seq_num = seq_num, status = status, message = message)

    def _rt_receiver(self):
        "Primary receiver thread"

        Receiver.logger.debug("Real-time Receiver is listening...")
        while self._should_run:
            try:
                data = self._rt_socket.recv(1024).decode()
                if len(self._rt_accum_string) == 0:
                    self._rt_accum_string = data
                else:
                    self._rt_accum_string += data

                if '\n' in self._rt_accum_string:
                    self._rt_accum_string = self._rt_accum_string[:-2]
                    for callback in self._receiver_callbacks.values():
                        callback(self._rt_accum_string)
                    self._rt_accum_string = ""

            except BlockingIOError as exception:
                pass
            except socket.timeout:
                pass
            except Exception as exception:
                Receiver.logger.error(f"Real-time Receiver Error: {exception}")
                break

        Receiver.logger.debug("Real-time Receiver terminated!")

    def _receiver(self):
        "Primary receiver thread"

        Receiver.logger.debug("Console Receiver is listening...")
        while self._should_run:
            try:
                debug = self._socket.recv(2048)
                data = debug.decode("utf-8", "ignore")
                
                if len(self._accum_string) == 0:
                    self._accum_string = data
                else:
                    self._accum_string += data

                while '\n\r' in self._accum_string:
                    index = self._accum_string.find('\n\r')
                    result = self._accum_string[:index]
                    self._accum_string = self._accum_string[index+2:]
                    for callback in self._receiver_callbacks.values():
                        callback(result)

            except BlockingIOError as exception:
                pass
            except socket.timeout:
                pass
            except Exception as exception:
                Receiver.logger.error(f"Console Receiver Error: {exception}")
                break

        Receiver.logger.debug("Console Receiver terminated!")

    def _logfile_parser(self):
        "Primary logfile thread"
        Receiver.logger.debug(f"Monitoring logfile at [{self._logfile}]...")
        log_fp = open(self._logfile, 'r')
        while self._should_run:
            line = log_fp.readline()
            if '\n' in line:
                line = line[:-1]            
            if line:
                for callback in self._receiver_log_callbacks.values():
                    callback(line)
            else:
                time.sleep(0.5)
