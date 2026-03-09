"""
TWAP Strategy Demo - Example of running a 2-minute TWAP strategy.

This script demonstrates:
1. Setting up the event-driven backtest framework
2. Creating and configuring a TWAP strategy
3. Running the simulation
4. Collecting and displaying results

Usage:
    python -m examples.run_twap_demo
"""

import sys
import time
from decimal import Decimal
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, '..')

from market_making_backtest import (
    create_simulation_clock,
    EventBus,
    EventLoop,
    create_twap_strategy,
    Side,
    current_timestamp_ns,
)


class TWAPDemo:
    """Demo runner for TWAP strategy"""

    def __init__(
        self,
        symbol: str = "BTC-USD",
        total_quantity: float = 1000.0,
        side: str = "BUY",
        duration_seconds: int = 120,  # 2 minutes
        num_slices: int = 12,
    ):
        self.symbol = symbol
        self.total_quantity = Decimal(str(total_quantity))
        self.side = side
        self.duration_seconds = duration_seconds
        self.num_slices = num_slices

        # Components
        self.clock = None
        self.event_bus = None
        self.event_loop = None
        self.strategy = None

        # Results
        self.results = {}

    def setup(self) -> None:
        """Setup the backtest components"""
        print("=" * 60)
        print("TWAP Strategy Demo - Setup")
        print("=" * 60)

        # Create clock (simulation mode)
        start_time = current_timestamp_ns()
        self.clock = create_simulation_clock(start_time_ns=start_time)
        print(f"✓ Clock created (simulation mode)")
        print(f"  Start time: {start_time} ns")

        # Create event bus
        self.event_bus = EventBus()
        print(f"✓ Event bus created")

        # Create event loop
        self.event_loop = EventLoop(
            event_bus=self.event_bus,
            clock=self.clock,
            mode="event_driven"
        )
        print(f"✓ Event loop created (event-driven mode)")

        # Create TWAP strategy
        self.strategy = create_twap_strategy(
            strategy_id="twap_demo_1",
            symbol=self.symbol,
            side=self.side,
            total_quantity=float(self.total_quantity),
            duration_seconds=self.duration_seconds,
            num_slices=self.num_slices,
            order_type='MARKET'
        )
        print(f"✓ TWAP strategy created")
        print(f"  Strategy ID: {self.strategy.strategy_id}")
        print(f"  Symbol: {self.symbol}")
        print(f"  Side: {self.side}")
        print(f"  Total Qty: {self.total_quantity}")
        print(f"  Duration: {self.duration_seconds}s")
        print(f"  Slices: {self.num_slices}")
        print(f"  Interval: {self.duration_seconds // self.num_slices}s")

        print()

    def run(self) -> None:
        """Run the TWAP strategy"""
        print("=" * 60)
        print("TWAP Strategy Demo - Execution")
        print("=" * 60)

        if not all([self.clock, self.event_bus, self.event_loop, self.strategy]):
            print("Error: Setup not completed. Call setup() first.")
            return

        # Initialize strategy
        print("Initializing strategy...")
        from market_making_backtest.strategy.base import StrategyContext

        # Create a simple context (in real usage, this would be fully configured)
        context = StrategyContext(
            strategy_id=self.strategy.strategy_id,
            event_bus=self.event_bus,
            clock=self.clock,
            order_manager=None,  # Would be configured
            position_manager=None  # Would be configured
        )

        self.strategy.initialize(context)
        print("✓ Strategy initialized")

        # Start strategy
        print("\nStarting execution...")
        self.strategy.start()
        print("✓ Strategy started")

        # Simulate execution (in real usage, this would run through event loop)
        print(f"\nSimulating {self.duration_seconds}s execution...")

        for i in range(self.num_slices):
            # Execute slice
            self.strategy._execute_slice(i)

            # Advance time
            self.clock.advance(self.strategy.slice_interval_ns)

            # Print progress
            progress = (i + 1) / self.num_slices * 100
            print(f"  Slice {i + 1}/{self.num_slices} complete ({progress:.0f}%)")

            # Simulate fills (in real usage, these would come from matching engine)
            # For demo, we assume all slices fill immediately
            for slice_data in self.strategy.slices:
                if slice_data.sent and slice_data.status == "sent":
                    from ..core.types import Fill

                    fill = Fill(
                        fill_id=f"fill_{slice_data.index}",
                        order_id=slice_data.order_id or "",
                        symbol=self.symbol,
                        side=self.strategy.side,
                        price=Decimal('50000.00'),  # Simulated price
                        size=slice_data.quantity,
                        fee=Decimal('0'),
                        timestamp=self.clock.now_ns,
                        is_maker=True
                    )

                    self.strategy.on_order_filled(fill)

        print("\n✓ Execution simulation complete")

        # Stop strategy
        print("\nStopping strategy...")
        self.strategy.stop()
        print("✓ Strategy stopped")

        print()

    def report(self) -> None:
        """Generate and display results report"""
        print("=" * 60)
        print("TWAP Strategy Demo - Results")
        print("=" * 60)

        stats = self.strategy.get_stats()

        print("\nExecution Statistics:")
        print(f"  Total Slices: {stats['slices']['total']}")
        print(f"  Slices Sent: {stats['slices']['sent']}")
        print(f"  Slices Filled: {stats['slices']['filled']}")

        print("\nQuantity Statistics:")
        print(f"  Total Quantity: {stats['quantity']['total']}")
        print(f"  Filled: {stats['quantity']['filled']}")
        print(f"  Fill Rate: {stats['quantity']['fill_rate']:.2f}%")

        print("\nPrice Statistics:")
        print(f"  Avg Fill Price: {stats['price']['avg_fill']}")
        print(f"  VWAP: {stats['price']['vwap']}")

        print("\nCompletion Status:")
        print(f"  Complete: {stats['is_complete']}")

        print()
        print("=" * 60)
        print("Demo Complete!")
        print("=" * 60)


def main():
    """Main entry point"""
    print()
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  MARKET MAKING BACKTEST FRAMEWORK".center(58) + "║")
    print("║" + "  TWAP Strategy Demo".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "=" * 58 + "╝")
    print()

    # Create and run demo
    demo = TWAPDemo(
        symbol="BTC-USD",
        total_quantity=1000.0,
        side="BUY",
        duration_seconds=120,  # 2 minutes
        num_slices=12,
    )

    try:
        demo.setup()
        demo.run()
        demo.report()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
    except Exception as e:
        print(f"\n\nError: {e}")
        raise

    return 0


if __name__ == "__main__":
    sys.exit(main())
