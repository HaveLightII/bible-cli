#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from bibletui import app  # noqa: E402

globals().update({
    k: v for k, v in vars(app).items()
    if not (k.startswith("__") and k.endswith("__"))
})

if __name__ == "__main__":
    app.main()
