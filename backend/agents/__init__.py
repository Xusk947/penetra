"""Multi-agent pentest backend."""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

# Load local .env into os.environ during normal (non-test) runs. Tests that need
# .env values can load it explicitly via tests.helpers.settings.default_settings.
if "pytest" not in sys.modules and "PYTEST_CURRENT_TEST" not in os.environ:
    load_dotenv(dotenv_path=".env")
