import math
import threading

class SynchronousTelemetryBuffer:
    def __init__(self, capacity: int = 2048):
        self.capacity = capacity
        self._buffer = [None] * capacity
        self._head = 0
        self._tail = 0
        self._lock = threading.Lock()

    def push(self, channels: list[float], timestamp_ns: int) -> bool:
        with self._lock:
            next_head = (self._head + 1) % self.capacity
            if next_head == self._tail:
                self._tail = (self._tail + 1) % self.capacity # Drop oldest on full
            self._buffer[self._head] = (timestamp_ns, channels)
            self._head = next_head
            return True

    def pop(self) -> tuple[int, list[float]] | None:
        with self._lock:
            if self._head == self._tail:
                return None
            frame = self._buffer[self._tail]
            self._buffer[self._tail] = None
            self._tail = (self._tail + 1) % self.capacity
            return frame

    def is_empty(self) -> bool:
        with self._lock:
            return self._head == self._tail


class RealtimeBiquadFilter:
    """
    Direct Form II Transposed 2nd-order Butterworth low-pass filter
    for real-time neural streaming data.
    """
    def __init__(self, cutoff_hz: float, sample_rate: float):
        w = math.tan(math.pi * cutoff_hz / sample_rate)
        w2 = w * w
        sqrt2 = math.sqrt(2.0)
        norm = 1.0 / (1.0 + sqrt2 * w + w2)

        self.b0 = w2 * norm
        self.b1 = 2.0 * self.b0
        self.b2 = self.b0
        self.a1 = 2.0 * (w2 - 1.0) * norm
        self.a2 = (1.0 - sqrt2 * w + w2) * norm

        self.d1 = 0.0
        self.d2 = 0.0

    def process_sample(self, x: float) -> float:
        y = self.b0 * x + self.d1
        self.d1 = self.b1 * x - self.a1 * y + self.d2
        self.d2 = self.b2 * x - self.a2 * y
        return y
