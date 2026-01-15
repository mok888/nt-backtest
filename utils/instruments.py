"""Instrument creation utilities"""

from nautilus_trader.model.instruments import CryptoPerpetual

# Import constants from config
from config.constants import (
    INSTRUMENT_ID,
    CURRENCY_ETH,
    CURRENCY_USDT,
    MAKER_FEE,
    TAKER_FEE,
    MARGIN_INIT,
    MARGIN_MAINT,
    PRICE_PRECISION,
    SIZE_PRECISION,
    PRICE_INCREMENT,
    SIZE_INCREMENT,
    LOT_SIZE,
    MIN_QUANTITY,
    MAX_QUANTITY,
    MIN_NOTIONAL,
    MAX_NOTIONAL,
    MIN_PRICE,
    MAX_PRICE,
)


def create_ethusdt_perpetual_instrument(instrument_id=None) -> CryptoPerpetual:
    """
    Create ETHUSDT perpetual futures instrument with standard configuration

    Args:
        instrument_id: Optional custom instrument_id (defaults to config.INSTRUMENT_ID)

    Returns:
        CryptoPerpetual: The configured ETHUSDT perpetual instrument
    """
    if instrument_id is None:
        instrument_id = INSTRUMENT_ID

    return CryptoPerpetual(
        instrument_id=instrument_id,
        raw_symbol=INSTRUMENT_ID.symbol,
        base_currency=CURRENCY_ETH,
        quote_currency=CURRENCY_USDT,
        settlement_currency=CURRENCY_USDT,
        is_inverse=False,
        price_precision=PRICE_PRECISION,
        price_increment=PRICE_INCREMENT,
        size_precision=SIZE_PRECISION,
        size_increment=SIZE_INCREMENT,
        lot_size=LOT_SIZE,
        max_quantity=MAX_QUANTITY,
        min_quantity=MIN_QUANTITY,
        max_notional=MAX_NOTIONAL,
        min_notional=MIN_NOTIONAL,
        max_price=MAX_PRICE,
        min_price=MIN_PRICE,
        margin_init=MARGIN_INIT,  # 20x leverage
        margin_maint=MARGIN_MAINT,
        maker_fee=MAKER_FEE,  # 0.02%
        taker_fee=TAKER_FEE,  # 0.05%
        ts_event=0,
        ts_init=0,
    )
