"""
Simulation clock for backtesting with nanosecond precision.
Supports both wall-clock (for live trading) and simulation modes.
"""

from typing import Optional, Callable, List
from decimal import Decimal
import time


class Clock:
    """
    Unified clock interface for both simulation and live trading.
    Uses nanosecond precision internally.
    """

    def __init__(self, simulation_mode: bool = True, start_time_ns: Optional[int] = None):
        """
        Initialize clock.

        Args:
            simulation_mode: If True, use simulated time; if False, use wall clock
            start_time_ns: Initial simulation time (nanoseconds)
        """
        self._simulation_mode = simulation_mode
        self._current_time_ns = start_time_ns if start_time_ns else time.time_ns()
        self._start_time_ns = self._current_time_ns

        # Timer callbacks: list of (trigger_time_ns, callback, recurring, interval_ns)
        self._timers: List[tuple] = []
        self._timer_id_counter = 0

    # ========== Time Access ==========

    @property
    def now_ns(self) -> int:
        """Get current time in nanoseconds"""
        if self._simulation_mode:
            return self._current_time_ns
        else:
            return time.time_ns()

    @property
    def now_us(self) -> int:
        """Get current time in microseconds"""
        return self.now_ns // 1000

    @property
    def now_ms(self) -> int:
        """Get current time in milliseconds"""
        return self.now_ns // 1_000_000

    @property
    def now_sec(self) -> float:
        """Get current time in seconds (with decimal)"""
        return self.now_ns / 1_000_000_000

    # ========== Simulation Control ==========

    def advance(self, nanoseconds: int) -> None:
        """Advance simulation time (simulation mode only)"""
        if not self._simulation_mode:
            raise RuntimeError("Cannot advance time in live mode")

        target_time = self._current_time_ns + nanoseconds
        self.advance_to(target_time)

    def advance_to(self, timestamp_ns: int) -> None:
        """Advance simulation time to specific timestamp"""
        if not self._simulation_mode:
            raise RuntimeError("Cannot advance time in live mode")

        if timestamp_ns < self._current_time_ns:
            raise ValueError("Cannot advance to past time")

        # Process any timers that should trigger during this advance
        self._current_time_ns = timestamp_ns
        self._process_timers()

    def set_time(self, timestamp_ns: int) -> None:
        """Set simulation time directly (use with caution)"""
        if not self._simulation_mode:
            raise RuntimeError("Cannot set time in live mode")

        self._current_time_ns = timestamp_ns
        self._start_time_ns = min(self._start_time_ns, timestamp_ns)

    # ========== Timer Management ==========

    def set_timer(
        self,
        delay_ns: int,
        callback: Callable,
        recurring: bool = False,
        interval_ns: Optional[int] = None
    ) -> str:
        """
        Set a timer callback.

        Args:
            delay_ns: Delay before first trigger (nanoseconds)
            callback: Function to call when timer triggers
            recurring: If True, timer repeats
            interval_ns: Interval between recurring triggers

        Returns:
            Timer ID for cancellation
        """
        self._timer_id_counter += 1
        timer_id = f"timer_{self._timer_id_counter}"

        trigger_time = self.now_ns + delay_ns

        self._timers.append((
            trigger_time,
            timer_id,
            callback,
            recurring,
            interval_ns,
            0  # call count
        ))

        # Keep sorted by trigger time
        self._timers.sort(key=lambda x: x[0])

        return timer_id

    def cancel_timer(self, timer_id: str) -> bool:
        """Cancel a timer by ID"""
        for i, (trigger_time, tid, *rest) in enumerate(self._timers):
            if tid == timer_id:
                self._timers.pop(i)
                return True
        return False

    def _process_timers(self) -> None:
        """Process any expired timers"""
        current_time = self.now_ns
        expired = []

        # Find expired timers
        for timer in self._timers[:]:
            trigger_time = timer[0]
            if trigger_time <= current_time:
                expired.append(timer)
                self._timers.remove(timer)
            else:
                break  # List is sorted, so we can stop

        # Execute callbacks
        for trigger_time, timer_id, callback, recurring, interval_ns, call_count in expired:
            try:
                callback(timer_id)
            except Exception as e:
                print(f"Timer callback error: {e}")

            # Reschedule if recurring
            if recurring and interval_ns:
                next_trigger = trigger_time + interval_ns * (call_count + 1)
                self._timers.append((
                    next_trigger,
                    timer_id,
                    callback,
                    recurring,
                    interval_ns,
                    call_count + 1
                ))
                self._timers.sort(key=lambda x: x[0])

    # ========== Statistics ==========

    def get_stats(self) -> dict:
        """Get clock statistics"""
        return {
            "mode": "simulation" if self._simulation_mode else "live",
            "current_time_ns": self.now_ns,
            "elapsed_ns": self.now_ns - self._start_time_ns,
            "active_timers": len(self._timers),
        }


# Convenience functions

def create_simulation_clock(start_time_ns: Optional[int] = None) -> Clock:
    """Create a simulation clock"""
    return Clock(simulation_mode=True, start_time_ns=start_time_ns)


def create_live_clock() -> Clock:
    """Create a live (wall clock) clock"""
    return Clock(simulation_mode=False)
