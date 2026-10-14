#!/usr/bin/env python3
"""Run the inherited read-only spender collector without environment proxy lookup."""
from pathlib import Path
import sys
import urllib.request

sys.path.insert(0, str(Path('line-2/tools/spender-code').resolve()))
import spender_code

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
                                    spender_code.changes.lens.NoRedirect())
urllib.request.urlopen = opener.open

if __name__ == '__main__':
    sys.exit(spender_code.main())
