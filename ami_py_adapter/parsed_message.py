"""
Basic data structure for storing messages returned from
the real-time port
"""

#!/usr/bin/env python3

class ParsedMessage:
    "Data structure storing information sent back from AMI"

    def __init__(self, uid = "", seq_num = 0, status = 0, message = ""):
        self.uid = uid
        self.seq_num = seq_num
        self.status = status
        self.message = message

    def to_string(self) -> str:
        "Returns the class as a formatted string"
        return f"[{self.uid}]-{self.seq_num} {self.message} <STATUS = {self.status}>"

    def has_error(self) -> bool:
        "Returns if the parsed message was flagged as an error"
        return self.status != 0
