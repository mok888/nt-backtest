"""Configuration package for NautilusTrader RSI Strategy"""

from .constants import *
from .paths import *

__all__ = [
    "SYMBOL",
    "INSTRUMENT_SYMBOL",
    "VENUE",
    "INSTRUMENT_ID",
    "DEFAULT_CATALOG_PATH",
    "DEFAULT_OUTPUT_DIR",
    "BAR_STEP_MINUTES",
    "MAKER_FEE",
    "TAKER_FEE",
    "MARGIN_INIT",
    "MARGIN_MAINT",
    "PRICE_PRECISION",
    "SIZE_PRECISION",
    "PRICE_INCREMENT",
    "SIZE_INCREMENT",
    "LOT_SIZE",
    "MIN_QUANTITY",
    "MAX_QUANTITY",
    "MIN_NOTIONAL",
    "MAX_NOTIONAL",
    "MIN_PRICE",
    "MAX_PRICE",
]
