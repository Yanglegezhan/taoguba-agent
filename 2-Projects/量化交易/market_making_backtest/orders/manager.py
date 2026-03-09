"""
Order Manager - Simplified order management for the backtest framework.
Tracks orders, positions, and account balance for strategies.
"""

from typing import Dict, List, Optional, Callable, Set
from decimal import Decimal
from dataclasses import dataclass, field
from collections import defaultdict

from ..core.types import (
    Order, OrderRequest, OrderStatus, Side, Fill,
    current_timestamp_ns
)


@dataclass
class Account:
    """Account state tracking"""
    balance: Decimal = Decimal('100000.00')  # Starting balance
    margin_used: Decimal = Decimal('0')
    margin_available: Decimal = Decimal('100000.00')
    unrealized_pnl: Decimal = Decimal('0')
    realized_pnl: Decimal = Decimal('0')


@dataclass
class Position:
    """Position tracking for a symbol"""
    symbol: str
    side: Side  # NET_LONG, NET_SHORT, FLAT
    quantity: Decimal
    avg_entry_price: Decimal
    unrealized_pnl: Decimal = Decimal('0')
    realized_pnl: Decimal = Decimal('0')

    def update_with_fill(self, fill: Fill) -> None:
        """Update position with a fill"""
        fill_side = fill.side
        fill_qty = fill.size
        fill_price = fill.price

        if self.quantity == 0:
            # New position
            self.side = fill_side
            self.quantity = fill_qty
            self.avg_entry_price = fill_price
        elif self.side == fill_side:
            # Adding to existing position
            total_cost = self.avg_entry_price * self.quantity + fill_price * fill_qty
            self.quantity += fill_qty
            self.avg_entry_price = total_cost / self.quantity
        else:
            # Reducing or reversing position
            if fill_qty < self.quantity:
                # Partial close
                realized_pnl = (fill_price - self.avg_entry_price) * fill_qty
                if self.side == Side.SELL:
                    realized_pnl = -realized_pnl
                self.realized_pnl += realized_pnl
                self.quantity -= fill_qty
            elif fill_qty == self.quantity:
                # Full close
                realized_pnl = (fill_price - self.avg_entry_price) * fill_qty
                if self.side == Side.SELL:
                    realized_pnl = -realized_pnl
                self.realized_pnl += realized_pnl
                self.quantity = Decimal('0')
                self.side = Side.BUY  # Flat, default to BUY side
            else:
                # Reverse position
                realized_pnl = (fill_price - self.avg_entry_price) * self.quantity
                if self.side == Side.SELL:
                    realized_pnl = -realized_pnl
                self.realized_pnl += realized_pnl

                # New position in opposite direction
                self.side = fill_side
                self.quantity = fill_qty - self.quantity
                self.avg_entry_price = fill_price


class OrderManager:
    """
    Simplified order manager for backtesting.
    Tracks orders, positions, and account state.
    """

    def __init__(self, initial_balance: Decimal = Decimal('100000.00')):
        # Orders by strategy
        self._orders: Dict[str, Dict[str, Order]] = defaultdict(dict)  # strategy_id -> {order_id: Order}

        # Positions by strategy
        self._positions: Dict[str, Dict[str, Position]] = defaultdict(dict)  # strategy_id -> {symbol: Position}

        # Accounts by strategy
        self._accounts: Dict[str, Account] = defaultdict(lambda: Account(balance=initial_balance))

        # Order ID counter
        self._order_counter = 0

        # Callbacks
        self._fill_callbacks: List[Callable[[str, Fill], None]] = []

    # ========== Order Management ==========

    def create_order(
        self,
        strategy_id: str,
        order_req: OrderRequest
    ) -> Order:
        """
        Create a new order.

        Returns:
            Created order
        """
        self._order_counter += 1
        order_id = f"{strategy_id}_{self._order_counter}_{current_timestamp_ns()}"

        order = Order(
            order_id=order_id,
            client_order_id=order_req.get('client_order_id', order_id),
            request=order_req,
            status=OrderStatus.CREATED,
            filled_quantity=Decimal('0'),
            avg_price=None,
            created_at=current_timestamp_ns(),
            updated_at=current_timestamp_ns()
        )

        # Store order
        self._orders[strategy_id][order_id] = order

        return order

    def get_order(self, strategy_id: str, order_id: str) -> Optional[Order]:
        """Get an order by ID"""
        return self._orders.get(strategy_id, {}).get(order_id)

    def get_orders(
        self,
        strategy_id: str,
        symbol: Optional[str] = None
    ) -> List[Order]:
        """Get active orders for a strategy"""
        orders = list(self._orders.get(strategy_id, {}).values())

        if symbol:
            orders = [o for o in orders if o.request.symbol == symbol]

        # Only return active orders
        active_status = {
            OrderStatus.CREATED,
            OrderStatus.PENDING,
            OrderStatus.ACCEPTED,
            OrderStatus.PARTIALLY_FILLED,
            OrderStatus.CANCELLING
        }

        return [o for o in orders if o.status in active_status]

    def update_order_status(
        self,
        strategy_id: str,
        order_id: str,
        new_status: OrderStatus
    ) -> bool:
        """Update order status"""
        order = self.get_order(strategy_id, order_id)
        if order is None:
            return False

        order.status = new_status
        order.updated_at = current_timestamp_ns()
        return True

    # ========== Position Management ==========

    def get_position(self, strategy_id: str, symbol: str) -> Position:
        """Get or create position for a symbol"""
        positions = self._positions[strategy_id]

        if symbol not in positions:
            positions[symbol] = Position(
                symbol=symbol,
                side=Side.BUY,  # Flat
                quantity=Decimal('0'),
                avg_entry_price=Decimal('0'),
                unrealized_pnl=Decimal('0'),
                realized_pnl=Decimal('0')
            )

        return positions[symbol]

    def get_all_positions(self, strategy_id: str) -> List[Position]:
        """Get all positions for a strategy"""
        return [
            pos for pos in self._positions[strategy_id].values()
            if pos.quantity > 0
        ]

    def update_position_with_fill(self, strategy_id: str, fill: Fill) -> None:
        """Update position with a fill"""
        position = self.get_position(strategy_id, fill.symbol)
        position.update_with_fill(fill)

        # Update account
        account = self._accounts[strategy_id]
        account.realized_pnl += position.realized_pnl

    # ========== Account Management ==========

    def get_account(self, strategy_id: str) -> Account:
        """Get account for a strategy"""
        return self._accounts[strategy_id]

    def update_balance(
        self,
        strategy_id: str,
        amount: Decimal
    ) -> bool:
        """Update account balance"""
        account = self._accounts[strategy_id]

        new_balance = account.balance + amount
        if new_balance < 0:
            return False

        account.balance = new_balance
        return True

    # ========== Fill Processing ==========

    def process_fill(
        self,
        strategy_id: str,
        order_id: str,
        fill: Fill
    ) -> bool:
        """
        Process a fill for an order.

        Returns:
            True if fill was processed successfully
        """
        order = self.get_order(strategy_id, order_id)
        if order is None:
            return False

        # Update order fill data
        order.filled_quantity += fill.size

        if order.avg_price is None:
            order.avg_price = fill.price
        else:
            # VWAP
            total_cost = (
                order.avg_price * (order.filled_quantity - fill.size) +
                fill.price * fill.size
            )
            order.avg_price = total_cost / order.filled_quantity

        # Update status
        if order.filled_quantity >= order.request.quantity:
            order.status = OrderStatus.FILLED
        else:
            order.status = OrderStatus.PARTIALLY_FILLED

        order.updated_at = current_timestamp_ns()

        # Update position
        self.update_position_with_fill(strategy_id, fill)

        # Execute callbacks
        for callback in self._fill_callbacks:
            try:
                callback(strategy_id, fill)
            except Exception as e:
                print(f"Fill callback error: {e}")

        return True

    def add_fill_callback(self, callback: Callable[[str, Fill], None]) -> None:
        """Add callback for fill events"""
        self._fill_callbacks.append(callback)

    # ========== Statistics ==========

    def get_stats(self) -> dict:
        """Get order manager statistics"""
        total_orders = sum(
            len(orders) for orders in self._orders.values()
        )

        return {
            "strategies": len(self._orders),
            "total_orders": total_orders,
            "accounts": len(self._accounts),
            "total_balance": sum(
                acc.balance for acc in self._accounts.values()
            ),
        }
