# AMI Python Adapter Repository

The python adapter is a library which provides access to both the console port as well as real-time port on python scripts via sockets.

The adapter is meant to be integrated with external python libraries and does not contain a `__main__` entry point. To use the simple python demo, switch branch to `example` and run `demo.py`.

The adapter has a few default arguments which should work with AMI out of the box but can be customized depending on the input arguments. To view the full set of arguments, run the program with the `--help` argument.

A simple example of using the adapter would be as such:
```
from ami_py_adapter.adapter import Adapter

if __name__ == "__main__":
    adapter = Adapter()
    adapter.init()
    adapter.send_ami_script(script)
    adapter.send_rt_message(script)
    adapter.cleanup()
```
