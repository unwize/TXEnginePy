"""
A file that contains configuration and utility code pertaining to PyTest
"""

import sys

from loguru import logger


def pytest_configure(config):
    logger.info("Modifying sys.path...")
    sys.path.insert(0, "src")
