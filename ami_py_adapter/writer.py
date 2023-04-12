"""
Threaded writer class which sends byte encoded messages to both
real-time as well as console ports
"""

#!/usr/bin/env python3
import threading

class Writer:
    "Writer class which sends inputs into the connected AMI Server"

    logger = None

    def __init__(self):
        self._should_run = True

        self._rt_socket = None
        self._rt_writer_thread = None
        self._rt_message_cv = threading.Condition()
        self._rt_messages = []

        self._socket = None
        self._writer_thread = None
        self._message_cv = threading.Condition()
        self._messages = []

    def init(self, logger, rt_socket, socket):
        "Initialize adapter class"
        Writer.logger = logger
        self._rt_socket = rt_socket
        self._socket = socket
        Writer.logger.debug("Starting writer thread...")

        if self._rt_socket is not None:
            self._rt_writer_thread = threading.Thread(
                name = "Real-time Writer Thread", target = self._rt_writer, args = ()
            )
            self._rt_writer_thread.start()

        if self._socket is not None:
            self._writer_thread = threading.Thread(
                name = "Real-time Writer Thread", target = self._writer, args = ()
            )
            self._writer_thread.start()

        Writer.logger.debug("Writer thread started!")


    def cleanup(self):
        "Performs any cleaning up of the writer class"
        Writer.logger.debug("Cleaning up writer class")
        self._should_run = False

        #Cleanup realtime
        if self._rt_writer_thread is not None:
            #Give a dummy message to force message loop to complete
            with self._rt_message_cv:
                self._rt_messages.append("")
                self._rt_message_cv.notify()

            self._rt_writer_thread.join()
            self._rt_writer_thread = None

        #Cleanup console
        if self._writer_thread is not None:
            #Give a dummy message to force message loop to complete
            with self._message_cv:
                self._messages.append("")
                self._message_cv.notify()

            self._writer_thread.join()
            self._writer_thread = None

        Writer.logger.debug("Writer class cleaned up!")


    def rt_add_string(self, msg: str):
        "Thread safe method of adding into the real-time message queue"
        if self._rt_socket is None:
            Writer.logger.warning("Real-time socket is disabled! Message not sent")
            return

        with self._rt_message_cv:
            self._rt_messages.append(msg)
            self._rt_message_cv.notify()

    def c_add_string(self, msg: str):
        "Thread safe method of adding into the console message queue"
        if self._socket is None:
            Writer.logger.warning("Console socket is disabled! Message not sent")
            return

        with self._message_cv:
            self._messages.append(msg)
            self._message_cv.notify()

    def rt_send_raw_msg(self, msg: str):
        "Converts a given string into bytes and sends it"
        if len(msg) == 0 or self._rt_socket is None:
            return

        #Adds a new line to the message to be sent
        if not msg.endswith('\n'):
            msg += '\n'

        #Attempt to send the message
        try:
            self._rt_socket.sendall(str.encode(msg))
        except Exception as exception:
            Writer.logger.error(f"Failed to send message ({msg}), error = {exception}")
            raise exception

    def c_send_raw_msg(self, msg: str):
        "Converts a given string into bytes and sends it"
        if len(msg) == 0 or self._socket is None:
            return

        #Adds a new line to the message to be sent
        if not msg.endswith('\n'):
            msg += '\n'

        #Attempt to send the message
        try:
            self._socket.send(str.encode(msg))
        except Exception as exception:
            Writer.logger.error(f"Failed to send message ({msg}), error = {exception}")
            raise exception from exception

    def _rt_writer(self):
        "Real-time writer thread"
        Writer.logger.debug("Real-time Writer is ready...")
        try:
            while self._should_run:
                with self._rt_message_cv:
                    while len(self._rt_messages) == 0:
                        self._rt_message_cv.wait()
                    for msg in self._rt_messages:
                        self.rt_send_raw_msg(msg)
                    self._rt_messages.clear()
        except Exception as exception:
            Writer.logger.error(f"Writer Error: {exception}")

        Writer.logger.debug("Real-time Writer terminated!")


    def _writer(self):
        "Console writer thread"
        Writer.logger.debug("Console Writer is ready...")
        try:
            while self._should_run:
                with self._message_cv:
                    while len(self._messages) == 0:
                        self._message_cv.wait()
                    for msg in self._messages:
                        self.c_send_raw_msg(msg)
                    self._messages.clear()
        except Exception as exception:
            Writer.logger.error(f"Writer Error: {exception}")

        Writer.logger.debug("Console Writer terminated!")
