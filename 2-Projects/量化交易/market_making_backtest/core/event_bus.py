"""
Event Bus - Central event distribution system with priority queue support.
Provides pub-sub pattern for decoupled component communication.
"""

import heapq
import threading
from collections import defaultdict, deque
from typing import Dict, List, Callable, Optional, Set, Any
from dataclasses import dataclass, field
from .types import Event, EventType, current_timestamp_ns


@dataclass(order=True)
class PrioritizedEvent:
    """Event wrapper with priority for heap queue"""
    priority: int
    timestamp: int = field(compare=True)
    event: Event = field(compare=False)
    sequence: int = field(default=0, compare=True)  # For tie-breaking


class EventHandler:
    """Wrapper for event handler with filter support"""

    def __init__(
        self,
        callback: Callable[[Event], None],
        event_types: Optional[Set[EventType]] = None,
        symbols: Optional[Set[str]] = None,
        priority: int = 5
    ):
        self.callback = callback
        self.event_types = event_types or set()
        self.symbols = symbols or set()
        self.priority = priority
        self.call_count = 0
        self.total_latency_ns = 0

    def matches(self, event: Event) -> bool:
        """Check if event matches handler filters"""
        # Check event type
        if self.event_types and event.event_type not in self.event_types:
            return False

        # Check symbol
        if self.symbols and hasattr(event, 'symbol'):
            if event.symbol not in self.symbols:
                return False

        return True

    def handle(self, event: Event) -> None:
        """Process event"""
        start = current_timestamp_ns()
        self.callback(event)
        latency = current_timestamp_ns() - start

        self.call_count += 1
        self.total_latency_ns += latency

    @property
    def avg_latency_ns(self) -> float:
        """Average handler latency"""
        if self.call_count == 0:
            return 0.0
        return self.total_latency_ns / self.call_count


class EventBus:
    """
    Central event bus with priority queue support.
    Supports both synchronous and asynchronous event processing.
    """

    def __init__(self, async_mode: bool = False, max_queue_size: int = 100000):
        self.async_mode = async_mode
        self.max_queue_size = max_queue_size

        # Handler registry
        self._handlers: Dict[str, EventHandler] = {}
        self._type_handlers: Dict[EventType, List[str]] = defaultdict(list)

        # Priority event queue (for synchronous mode)
        self._event_queue: List[PrioritizedEvent] = []
        self._sequence = 0

        # Async mode components
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()

        # Statistics
        self.events_published = 0
        self.events_processed = 0
        self.events_dropped = 0

    # ========== Handler Registration ==========

    def subscribe(
        self,
        handler_id: str,
        callback: Callable[[Event], None],
        event_types: Optional[List[EventType]] = None,
        symbols: Optional[List[str]] = None,
        priority: int = 5
    ) -> None:
        """
        Subscribe to events with filters.

        Args:
            handler_id: Unique handler identifier
            callback: Event callback function
            event_types: Filter by event types (None = all)
            symbols: Filter by symbols (None = all)
            priority: Handler priority (0-9, lower = higher priority)
        """
        with self._lock:
            if handler_id in self._handlers:
                raise ValueError(f"Handler {handler_id} already exists")

            handler = EventHandler(
                callback=callback,
                event_types=set(event_types) if event_types else set(),
                symbols=set(symbols) if symbols else set(),
                priority=priority
            )

            self._handlers[handler_id] = handler

            # Index by event type for fast lookup
            if event_types:
                for et in event_types:
                    self._type_handlers[et].append(handler_id)

    def unsubscribe(self, handler_id: str) -> None:
        """Unsubscribe a handler"""
        with self._lock:
            if handler_id not in self._handlers:
                return

            handler = self._handlers[handler_id]

            # Remove from type index
            for et in handler.event_types:
                if handler_id in self._type_handlers[et]:
                    self._type_handlers[et].remove(handler_id)

            # Remove handler
            del self._handlers[handler_id]

    # ========== Event Publishing ==========

    def publish(self, event: Event, priority: int = 5) -> bool:
        """
        Publish an event to the bus.

        Args:
            event: The event to publish
            priority: Event priority (0-9, lower = higher priority)

        Returns:
            True if event was queued, False if dropped
        """
        with self._lock:
            if len(self._event_queue) >= self.max_queue_size:
                self.events_dropped += 1
                return False

            prioritized = PrioritizedEvent(
                priority=priority,
                timestamp=event.timestamp,
                event=event,
                sequence=self._sequence
            )
            self._sequence += 1

            heapq.heappush(self._event_queue, prioritized)
            self.events_published += 1

            return True

    def publish_immediate(self, event: Event) -> None:
        """
        Publish and process an event immediately (synchronous).
        Bypasses the queue for urgent events.
        """
        self._process_event(event)
        self.events_published += 1
        self.events_processed += 1

    # ========== Event Processing ==========

    def process_once(self, timeout_ms: float = 0) -> bool:
        """
        Process a single event from the queue.

        Args:
            timeout_ms: Maximum time to wait for an event (0 = non-blocking)

        Returns:
            True if an event was processed, False if queue was empty
        """
        with self._lock:
            if not self._event_queue:
                return False

            prioritized = heapq.heappop(self._event_queue)

        # Process outside the lock
        self._process_event(prioritized.event)
        self.events_processed += 1
        return True

    def process_all(self) -> int:
        """Process all events in the queue. Returns count processed."""
        count = 0
        while self.process_once():
            count += 1
        return count

    def _process_event(self, event: Event) -> None:
        """Route event to matching handlers."""
        # Get candidate handlers
        handler_ids = set()

        # Add type-specific handlers
        if event.event_type in self._type_handlers:
            handler_ids.update(self._type_handlers[event.event_type])

        # Add wildcard handlers (no type filter)
        for hid, handler in self._handlers.items():
            if not handler.event_types:
                handler_ids.add(hid)

        # Sort by priority and call
        handlers_with_priority = [
            (self._handlers[hid].priority, hid, self._handlers[hid])
            for hid in handler_ids
            if hid in self._handlers
        ]
        handlers_with_priority.sort(key=lambda x: x[0])

        for priority, hid, handler in handlers_with_priority:
            if handler.matches(event):
                try:
                    handler.handle(event)
                except Exception as e:
                    # Log error but continue with other handlers
                    print(f"Error in handler {hid}: {e}")

    # ========== Async Mode ==========

    def start_async(self) -> None:
        """Start async event processing in background thread."""
        if self._running:
            return

        self._running = True
        self._worker_thread = threading.Thread(target=self._async_worker, daemon=True)
        self._worker_thread.start()

    def stop_async(self, timeout: float = 5.0) -> None:
        """Stop async processing."""
        self._running = False

        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=timeout)

    def _async_worker(self) -> None:
        """Background worker thread."""
        while self._running:
            if not self.process_once(timeout_ms=100):
                # No event processed, brief sleep to prevent busy loop
                time.sleep(0.001)

    # ========== Statistics ==========

    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        with self._lock:
            return {
                "handlers_registered": len(self._handlers),
                "events_published": self.events_published,
                "events_processed": self.events_processed,
                "events_dropped": self.events_dropped,
                "queue_size": len(self._event_queue),
                "async_running": self._running,
            }

    def reset_stats(self) -> None:
        """Reset statistics counters."""
        with self._lock:
            self.events_published = 0
            self.events_processed = 0
            self.events_dropped = 0
