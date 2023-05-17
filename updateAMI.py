#!/usr/bin/env python3

import sys
import argparse

# dir_path = os.path.dirname(os.path.realpath(__file__))
# sys.path.append(dir_path)

from ami_py_adapter.adapter import Adapter

parser = argparse.ArgumentParser()

parser.add_argument("--CHANGELIST", help = "Changelist number")
parser.add_argument("--BUILDSTATUS", help = "Status of current build")
parser.add_argument("--STREAM", help = "Name of branch/stream")
parser.add_argument("--BUILDURL", help = "URL of build job")

adapter = Adapter()
adapter.init(parser = parser)

args = parser.parse_args()
CHANGELIST = args.CHANGELIST
BUILDSTATUS = args.BUILDSTATUS
STREAM = args.STREAM
BUILDURL = args.BUILDURL

adapter.send_obj('Branches', {'buildStatus':f"\"{BUILDSTATUS}\"", 'lastChange':CHANGELIST, 'Branch':f"\"{STREAM}\"", 'buildUrl':f"\"{BUILDURL}\""})
adapter.cleanup()

sys.exit(0)