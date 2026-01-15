"""
RSI Strategy Module - Implements RSI-based trading strategy with SL/TP
Entry signals: Long when RSI crosses above oversold, Short when RSI crosses below overbought
"""

from decimal import Decimal
from typing import Optional

from nautilus_trader.core.data import Data
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.enums import OrderSide, PositionSide
from nautilus_trader.model.events import PositionOpened, PositionClosed, PositionChanged
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.orders import MarketOrder, StopMarketOrder, LimitOrder
from nautilus_trader.model.position import Position
from nautilus_trader.trading.strategy import Strategy


class RSIStrategy(Strategy):
    """
    RSI Trading Strategy for Perpetual Futures

    Features:
    - 15-minute RSI indicator
    - Long entry when RSI crosses above oversold threshold
    - Short entry when RSI crosses below overbought threshold
    - Stop Loss and Take Profit for each position
    - Position sizing as percentage of account equity
    - Symmetric long/short logic
    """

    def __init__(
        self,
        config: "RSIConfig",
        instrument_id: InstrumentId,
        bar_type: BarType,
    ):
        """
        Initialize the RSI strategy

        Args:
            config: Strategy configuration with RSI parameters
            instrument_id: Instrument to trade
            bar_type: Bar type for indicator calculation
        """
        super().__init__(config=config)

        self.instrument_id = instrument_id
        self.bar_type = bar_type
        self.config = config

        # RSI indicator will be initialized in on_start
        self.rsi = None

        # Track positions
        self.current_position: Optional[Position] = None
        self.position_entry_price: Optional[float] = None

        # Track signal state for crossovers
        self.previous_rsi = None

        # Track attached SL/TP orders
        self.sl_order_id = None
        self.tp_order_id = None

    def on_start(self) -> None:
        """
        Called when strategy starts - initialize RSI indicator
        """
        from nautilus_trader.indicators.rsi import RelativeStrengthIndex

        self.rsi = RelativeStrengthIndex(period=self.config.rsi_period)
        self.log.info(f"Strategy started: RSI({self.config.rsi_period})")
        self.log.info(f"Oversold threshold: {self.config.oversold_threshold}")
        self.log.info(f"Overbought threshold: {self.config.overbought_threshold}")
        self.log.info(f"Stop Loss: {self.config.stop_loss_pct}%")
        self.log.info(f"Take Profit: {self.config.take_profit_pct}%")
        self.log.info(f"Position Size: {self.config.position_size_pct}% of equity")

    def on_stop(self) -> None:
        """
        Called when strategy stops - cleanup
        """
        self.log.info("Strategy stopped")

    def on_bar(self, bar: Bar) -> None:
        """
        Process incoming bar data

        Args:
            bar: The bar event
        """
        # Update RSI indicator
        self.rsi.update_raw(bar.close.as_double())

        # Get current RSI value
        current_rsi = self.rsi.value

        # Log RSI periodically
        if current_rsi is not None and self.rsi.initialized:
            self.log.debug(f"Bar: {bar.ts_event} | Close: {bar.close} | RSI: {current_rsi:.2f}")

        # Wait for RSI to be initialized
        if not self.rsi.initialized or self.previous_rsi is None:
            self.previous_rsi = current_rsi
            return

        # Check for crossovers and generate signals
        self._check_entry_signals(current_rsi)

        # Update previous RSI
        self.previous_rsi = current_rsi

    def _check_entry_signals(self, current_rsi: float) -> None:
        """
        Check for RSI crossover signals and execute trades

        Args:
            current_rsi: Current RSI value
        """
        # Check if we already have an open position
        if self.current_position is not None:
            self.log.debug(f"Position already open, skipping entry signal")
            return

        # Long signal: RSI crosses above oversold threshold
        if self.previous_rsi < self.config.oversold_threshold and current_rsi >= self.config.oversold_threshold:
            self.log.info(
                f"LONG SIGNAL: RSI crossed above {self.config.oversold_threshold} "
                f"({self.previous_rsi:.2f} -> {current_rsi:.2f})"
            )
            self._open_long_position()

        # Short signal: RSI crosses below overbought threshold
        elif self.previous_rsi > self.config.overbought_threshold and current_rsi <= self.config.overbought_threshold:
            self.log.info(
                f"SHORT SIGNAL: RSI crossed below {self.config.overbought_threshold} "
                f"({self.previous_rsi:.2f} -> {current_rsi:.2f})"
            )
            self._open_short_position()

    def _open_long_position(self) -> None:
        """
        Open a long position with SL/TP
        """
        # Get current price from last bar
        if not self.rsi.initialized:
            return

        # Calculate position size
        position_size = self._calculate_position_size()
        if position_size is None:
            return

        # Get current price for logging
        current_price = self._get_current_price()
        if current_price is None:
            self.log.warning("Cannot determine current price for logging")
            return

        # Submit market order for long entry
        self.submit_order(
            MarketOrder(
                trader_id=self.trader_id,
                strategy_id=self.id,
                instrument_id=self.instrument_id,
                order_side=OrderSide.BUY,
                quantity=Decimal(str(position_size)),
                tags=["RSI_LONG_ENTRY"],
            )
        )

        self.log.info(f"Submitted LONG order: Size={position_size:.3f} ETH, Price={current_price:.2f}")

    def _open_short_position(self) -> None:
        """
        Open a short position with SL/TP
        """
        # Calculate position size
        position_size = self._calculate_position_size()
        if position_size is None:
            return

        # Get current price for logging
        current_price = self._get_current_price()
        if current_price is None:
            self.log.warning("Cannot determine current price for logging")
            return

        # Submit market order for short entry
        self.submit_order(
            MarketOrder(
                trader_id=self.trader_id,
                strategy_id=self.id,
                instrument_id=self.instrument_id,
                order_side=OrderSide.SELL,
                quantity=Decimal(str(position_size)),
                tags=["RSI_SHORT_ENTRY"],
            )
        )

        self.log.info(f"Submitted SHORT order: Size={position_size:.3f} ETH, Price={current_price:.2f}")

    def _get_current_price(self) -> Optional[float]:
        """
        Get current market price

        Returns:
            Current price or None if unavailable
        """
        # Try to get from portfolio last price
        from nautilus_trader.model.identifiers import Venue
        try:
            venue = self.instrument_id.venue
            return float(self.portfolio.last_price(self.instrument_id))
        except (AttributeError, KeyError, ValueError):
            self.log.debug(f"Could not get current price: portfolio unavailable or no price data")
            return None

    def on_position_opened(self, event: PositionOpened) -> None:
        """
        Handle position opened event - attach SL/TP orders

        Args:
            event: Position opened event
        """
        position = event.position
        self.current_position = position
        self.position_entry_price = float(position.avg_px_open)

        self.log.info(
            f"Position OPENED: Side={position.side}, "
            f"Quantity={position.quantity}, "
            f"Entry Price={self.position_entry_price:.2f}"
        )

        # Attach SL and TP orders
        self._attach_sl_tp_orders(position)

    def _calculate_position_size(self) -> Optional[float]:
        """
        Calculate position size based on account equity and config

        Returns:
            Position size in base currency (ETH) or None if calculation fails
        """
        account = self.portfolio.account(self.instrument_id.venue)
        if not account:
            self.log.warning("No account available for position sizing")
            return None

        free_balance = float(account.balance_free(self.instrument_id.venue))
        position_size_usdt = free_balance * (self.config.position_size_pct / 100)

        current_price = self._get_current_price()
        if current_price is None:
            self.log.warning("Cannot determine current price for position sizing")
            return None

        return position_size_usdt / current_price

    def _attach_sl_tp_orders(self, position: Position) -> None:
        """
        Attach Stop Loss and Take Profit orders to position

        Args:
            position: The open position
        """
        entry_price = float(position.avg_px_open)
        quantity = position.quantity

        # Calculate SL and TP levels
        if position.side == PositionSide.LONG:
            # Long position: SL below entry, TP above entry
            sl_price = entry_price * (1 - self.config.stop_loss_pct / 100)
            tp_price = entry_price * (1 + self.config.take_profit_pct / 100)
            sl_side = OrderSide.SELL
            tp_side = OrderSide.SELL
        else:
            # Short position: SL above entry, TP below entry
            sl_price = entry_price * (1 + self.config.stop_loss_pct / 100)
            tp_price = entry_price * (1 - self.config.take_profit_pct / 100)
            sl_side = OrderSide.BUY
            tp_side = OrderSide.BUY

        # Submit Stop Loss order
        self.submit_order(
            StopMarketOrder(
                trader_id=self.trader_id,
                strategy_id=self.id,
                instrument_id=self.instrument_id,
                order_side=sl_side,
                quantity=quantity,
                trigger_price=Decimal(str(sl_price)),
                tags=["STOP_LOSS"],
            )
        )

        # Submit Take Profit order
        self.submit_order(
            LimitOrder(
                trader_id=self.trader_id,
                strategy_id=self.id,
                instrument_id=self.instrument_id,
                order_side=tp_side,
                quantity=quantity,
                price=Decimal(str(tp_price)),
                tags=["TAKE_PROFIT"],
            )
        )

        self.log.info(
            f"SL/TP Attached: SL={sl_price:.2f}, TP={tp_price:.2f}, "
            f"Entry={entry_price:.2f}, Side={position.side}"
        )

    def on_position_closed(self, event: PositionClosed) -> None:
        """
        Handle position closed event

        Args:
            event: Position closed event
        """
        position = event.position
        realized_pnl = position.realized_pnl

        self.log.info(
            f"Position CLOSED: Side={position.side}, "
            f"PnL={realized_pnl:.2f} USDT, "
            f"Exit Price={position.avg_px_close:.2f}"
        )

        # Reset position tracking
        self.current_position = None
        self.position_entry_price = None
        self.sl_order_id = None
        self.tp_order_id = None

    def on_position_changed(self, event: PositionChanged) -> None:
        """
        Handle position changed event

        Args:
            event: Position changed event
        """
        self.log.debug(f"Position changed: {event}")


class RSIConfig(StrategyConfig):
    """
    Configuration for RSI Strategy
    """

    def __init__(
        self,
        rsi_period: int = 14,
        oversold_threshold: float = 30.0,
        overbought_threshold: float = 70.0,
        stop_loss_pct: float = 1.5,
        take_profit_pct: float = 3.0,
        position_size_pct: float = 2.0,
        instrument_id: Optional[InstrumentId] = None,
    ):
        """
        Initialize RSI strategy configuration

        Args:
            rsi_period: RSI calculation period (default: 14)
            oversold_threshold: RSI level for long entry (default: 30)
            overbought_threshold: RSI level for short entry (default: 70)
            stop_loss_pct: Stop loss percentage from entry (default: 1.5%)
            take_profit_pct: Take profit percentage from entry (default: 3.0%)
            position_size_pct: Position size as % of account equity (default: 2.0%)
            instrument_id: Instrument to trade (optional)
        """
        self.rsi_period = rsi_period
        self.oversold_threshold = oversold_threshold
        self.overbought_threshold = overbought_threshold
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.position_size_pct = position_size_pct
        self.instrument_id = instrument_id

    def __repr__(self) -> str:
        return (
            f"RSIConfig(rsi_period={self.rsi_period}, "
            f"oversold={self.oversold_threshold}, "
            f"overbought={self.overbought_threshold}, "
            f"sl={self.stop_loss_pct}%, "
            f"tp={self.take_profit_pct}%, "
            f"size={self.position_size_pct}%)"
        )
