"""Compatibility entrypoint; aliases the testable HTTP module."""

import sys
from . import webserver

if __name__ == "__main__":
    webserver.main()
else:
    sys.modules[__name__] = webserver
