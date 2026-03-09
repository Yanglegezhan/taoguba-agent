"""
Event Loop - Main simulation loop with nanosecond precision timing.
Coordinates all components through the event bus.
"""

from typing import Optional, Callable, List, Dict, Any, Set
from dataclasses import dataclass, field
from collections import deque
import time
import heapq

from .types import Event, EventType, current_timestamp_ns
from .event_bus import EventBus
from .clock import Clock


@dataclass
class LoopStats:
    """Event loop statistics"""
    events_processed: int = 0
    events_by_type: Dict[EventType, int] = field(default_factory=dict)
    cycles: int = 0
    idle_cycles: int = 0
    start_time_ns: int = 0
    end_time_ns: int = 0

    @property
    def elapsed_ns(self) -> int:
        if self.end_time_ns > 0:
            return self.end_time_ns - self.start_time_ns
        return current_timestamp_ns() - self.start_time_ns

    @property
    def events_per_second(self) -> float:
        elapsed_sec = self.elapsed_ns / 1e9
        if elapsed_sec <= 0:
            return 0.0
        return self.events_processed / elapsed_sec

    def record_event(self, event_type: EventType) -> None:
        self.events_processed += 1
        self.events_by_type[event_type] = self.events_by_type.get(event_type, 0) + 1


class EventLoop:
    """
    Main event loop for backtesting.

    Supports two modes:
    - Event-driven: Process events as they arrive
    - Time-synchronized: Advance simulation time to match data timestamps
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        clock: Optional[Clock] = None,
        mode: str = "event_driven"  # or "time_sync"
    ):
        self.event_bus = event_bus or EventBus()
        self.clock = clock or Clock(simulation_mode=True)
        self.mode = mode

        # State
        self._running = False
        self._paused = False
        self._stop_requested = False

        # Event sources
        self._data_feeds: List[Any] = []
        self._scheduled_events: List[tuple] = []  # (time_ns, callback)

        # Statistics
        self.stats = LoopStats()

        # Callbacks
        self._on_cycle_start: Optional[Callable[[], None]] = None
        self._on_cycle_end: Optional[Callable[[], None]] = None
        self._on_idle: Optional[Callable[[], None]] = None

    # ========== Configuration ==========

    def set_callbacks(
        self,
        on_cycle_start: Optional[Callable[[], None]] = None,
        on_cycle_end: Optional[Callable[[], None]] = None,
        on_idle: Optional[Callable[[], None]] = None
    ) -> None:
        """Set loop callbacks"""
        self._on_cycle_start = on_cycle_start
        self._on_cycle_end = on_cycle_end
        self._on_idle = on_idle

    def add_data_feed(self, feed: Any) -> None:
        """Add a data feed (e.g., CSV, database, websocket)"""
        self._data_feeds.append(feed)

    def schedule_event(self, delay_ns: int, callback: Callable[[], None]) -> None:
        """Schedule a callback to be executed after delay"""
        trigger_time = self.clock.now_ns + delay_ns
        self._scheduled_events.append((trigger_time, callback))
        self._scheduled_events.sort(key=lambda x: x[0])

    # ========== Loop Control ==========

    def start(self) -> None:
        """Start the event loop"""
        if self._running:
            return

        self._running = True
        self._stop_requested = False
        self.stats.start_time_ns = self.clock.now_ns

        self._main_loop()

    def stop(self) -> None:
        """Request loop stop"""
        self._stop_requested = True

    def pause(self) -> None:
        """Pause the loop"""
        self._paused = True

    def resume(self) -> None:
        """Resume the loop"""
        self._paused = False

    def is_running(self) -> bool:
        """Check if loop is running"""
        return self._running

    # ========== Main Loop ==========

    def _main_loop(self) -> None:
        """Main event processing loop"""
        while self._running and not self._stop_requested:
            # Check for pause
            if self._paused:
                time.sleep(0.001)
                continue

            # Start cycle
            if self._on_cycle_start:
                self._on_cycle_start()

            # Process data feeds
            events_generated = self._process_data_feeds()

            # Process scheduled events
            scheduled_processed = self._process_scheduled_events()

            # Process events from bus
            bus_events = self._process_event_bus()

            # Update statistics
            self.stats.cycles += 1
            total_events = events_generated + scheduled_processed + bus_events

            if total_events == 0:
                self.stats.idle_cycles += 1
                if self._on_idle:
                    self._on_idle()
                # Brief sleep to prevent busy loop when idle
                time.sleep(0.001)

            # End cycle
            if self._on_cycle_end:
                self._on_cycle_end()

        # Cleanup
        self._cleanup()

    def _process_data_feeds(self) -> int:
        """Process all data feeds and return count of events generated"""
        count = 0
        for feed in self._data_feeds:
            try:
                events = feed.read_batch()
                for event in events:
                    self.event_bus.publish(event, priority=3)
                    count += 1
            except Exception as e:
                # Log error but continue with other feeds
                print(f"Error reading from feed: {e}")
        return count

    def _process_scheduled_events(self) -> int:
        """Process scheduled callbacks and return count executed"""
        count = 0
        current_time = self.clock.now_ns

        # Find expired timers
        expired = []
        remaining = []

        for trigger_time, callback in self._scheduled_events:
            if trigger_time <= current_time:
                expired.append((trigger_time, callback))
            else:
                remaining.append((trigger_time, callback))

        self._scheduled_events = remaining

        # Execute callbacks
        for trigger_time, callback in expired:
            try:
                callback()
                count += 1
            except Exception as e:
                print(f"Error in scheduled callback: {e}")

        return count

    def _process_event_bus(self) -> int:
        """Process events from event bus and return count processed"""
        count = 0

        # Process up to 100 events per cycle to prevent starvation
        max_per_cycle = 100

        while count < max_per_cycle:
            if not self.event_bus.process_once(timeout_ms=0):
                break
            count += 1

        return count

    def _cleanup(self) -> None:
        """Cleanup resources"""
        self.stats.end_time_ns = self.clock.now_ns
        self._running = False

        # Close data feeds
        for feed in self._data_feeds:
            try:
                feed.close()
            except:
                pass

    # ========== Statistics ==========

    def get_stats(self) -> Dict[str, Any]:
        """Get loop statistics"""
        return {
            "running": self._running,
            "paused": self._paused,
            **self.stats.__dict__,
            "handlers_registered": len(self.event_bus._handlers),
            "feeds_active": len(self._data_feeds),
        }

    def reset_stats(self) -> None:
        """Reset statistics"""
        self.stats = LoopStats()
