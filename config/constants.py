"""Constants module for trading parameters and instrument configuration"""

from decimal import Decimal
from nautilus_trader.model.objects import Price, Quantity, Money
from nautilus_trader.model.currencies import ETH, USDT
from nautilus_trader.model.identifiers import Symbol, Venue, InstrumentId

# Instrument Configuration
SYMBOL = Symbol("ETHUSDT")
INSTRUMENT_SYMBOL = Symbol("ETHUSDT.P")
VENUE = Venue("BINANCE")
INSTRUMENT_ID = InstrumentId(symbol=INSTRUMENT_SYMBOL, venue=VENUE)

# Trading Constants
MAKER_FEE = Decimal("0.0002")  # 0.02%
TAKER_FEE = Decimal("0.0005")  # 0.05%
MARGIN_INIT = Decimal("0.05")  # 20x leverage
MARGIN_MAINT = Decimal("0.03")

# Precision Constants
PRICE_PRECISION = 2
SIZE_PRECISION = 3

# Size/Price Constants
PRICE_INCREMENT = Price.from_str("0.01")
SIZE_INCREMENT = Quantity.from_str("0.001")
LOT_SIZE = Quantity.from_str("0.001")
MIN_QUANTITY = Quantity.from_str("0.001")
MAX_QUANTITY = Quantity.from_str("1000000")

# Notional Constants
MIN_NOTIONAL = Money(Decimal("5"), USDT)
MAX_NOTIONAL = Money(Decimal("10000000"), USDT)

# Price Limits
MIN_PRICE = Price.from_str("0.001")
MAX_PRICE = Price.from_str("1000000")

# Bar Configuration
BAR_STEP_MINUTES = 15

# Currency objects for easy import
CURRENCY_ETH = ETH
CURRENCY_USDT = USDT
