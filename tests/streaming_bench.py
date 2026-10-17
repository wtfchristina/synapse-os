import sys
import os
import time
import numpy as np

# Ensure core package path is resolvable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../core")))

from synapse_dsp import NativeBiquadCascade

def run_benchmark():
    num_channels = 16
    sampling_rate_hz = 1000.0
    budget_us = (1.0 / sampling_rate_hz) * 1e6  # 1,000 µs
    iterations = 10_000

    # 4th-order Butterworth bandpass (8-30 Hz) represented as 2 cascaded biquads
    sos_coeffs = [
        [0.0055,  0.0110, 0.0055, -1.8890, 0.8920],
        [1.0000, -2.0000, 1.0000, -1.9310, 0.9350]
    ]

    cascade = NativeBiquadCascade(num_channels=num_channels, coefficients=sos_coeffs)
    in_frame = np.ones(num_channels, dtype=np.float32)
    out_frame = np.empty_like(in_frame)

    latencies_us = []

    # Warm-up run (1,000 frames)
    for _ in range(1000):
        cascade.process_sample(in_frame, out_frame=out_frame)

    # Timed measurement loop
    for _ in range(iterations):
        t0 = time.perf_counter_ns()
        cascade.process_sample(in_frame, out_frame=out_frame)
        t1 = time.perf_counter_ns()
        latencies_us.append((t1 - t0) / 1000.0)

    latencies_us = np.array(latencies_us)
    mean_lat = np.mean(latencies_us)
    jitter_std = np.std(latencies_us)
    p99 = np.percentile(latencies_us, 99)
    max_lat = np.max(latencies_us)

    print("\n" + "=" * 54)
    print("  SYNAPSE-OS CORE DSP BENCHMARK (16-CH @ 1,000 HZ)")
    print("=" * 54)
    print(f"Iterations:         {iterations:,}")
    print(f"Mean Latency:       {mean_lat:6.2f} µs")
    print(f"Timing Jitter (σ):  {jitter_std:6.2f} µs")
    print(f"99th Percentile:    {p99:6.2f} µs")
    print(f"Max Latency:        {max_lat:6.2f} µs")
    print(f"Frame Budget:       {budget_us:6.0f} µs")
    print(f"Budget Utilization: {(mean_lat / budget_us) * 100:6.2f}%")
    print("=" * 54)

    assert mean_lat < 100.0, f"Mean latency exceeded limit: {mean_lat} µs"
    assert jitter_std < 400.0, f"Transit jitter exceeded limit: {jitter_std} µs"
    print("✓ Deterministic streaming gates passed.\n")

if __name__ == "__main__":
    run_benchmark()
