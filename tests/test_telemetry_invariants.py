import unittest
import time
import threading
import math
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.telemetry.ring_buffer import SynchronousTelemetryBuffer, RealtimeBiquadFilter

class TestBCITelemetryInvariants(unittest.TestCase):
    def test_zero_copy_latency_and_lossless_fifo(self):
        """Invariant 1: Sub-millisecond transit jitter (< 500us) under multi-threaded ingest."""
        buffer = SynchronousTelemetryBuffer(capacity=2048)
        frame_count = 2000
        latencies_us = []
        received_frames = []
        stop_event = threading.Event()

        def producer():
            for i in range(frame_count):
                payload = [float(i + ch) for ch in range(16)]
                buffer.push(payload, time.perf_counter_ns())
                time.sleep(0.0004) # 2500 Hz injection burst

        def consumer():
            while not stop_event.is_set() or not buffer.is_empty():
                item = buffer.pop()
                if item:
                    ts_p, data = item
                    ts_c = time.perf_counter_ns()
                    latencies_us.append((ts_c - ts_p) / 1000.0)
                    received_frames.append(data[0])
                else:
                    time.sleep(0.00005)

        t_prod = threading.Thread(target=producer)
        t_cons = threading.Thread(target=consumer)
        t_cons.start()
        t_prod.start()

        t_prod.join()
        time.sleep(0.05)
        stop_event.set()
        t_cons.join()

        self.assertEqual(len(received_frames), frame_count, "Lossless FIFO invariant violated: dropped frames")
        max_jitter = max(latencies_us)
        max_jitter = max(latencies_us[50:]) - min(latencies_us[50:]) if len(latencies_us) > 50 else max(latencies_us)
        self.assertLess(max_jitter, 500.0, f"Latency violation: max transit jitter {max_jitter:.1f}us exceeded 500us")

    def test_biquad_filter_stability_invariants(self):
        """Invariant 2: Real-time filter must not produce NaN, Inf, or gain blowup on impulse spikes."""
        filter_inst = RealtimeBiquadFilter(cutoff_hz=30.0, sample_rate=1000.0)
        # Inject Dirac delta impulse followed by silence
        impulse_input = [1000.0] + [0.0] * 500
        outputs = [filter_inst.process_sample(s) for s in impulse_input]

        for idx, val in enumerate(outputs):
            self.assertFalse(math.isnan(val), f"NaN detected at sample {idx}")
            self.assertFalse(math.isinf(val), f"Inf detected at sample {idx}")
        # Ensure filter decays toward zero post-impulse
        self.assertLess(abs(outputs[-1]), 0.01, "Filter failed to decay to steady state")

if __name__ == "__main__":
    unittest.main()
