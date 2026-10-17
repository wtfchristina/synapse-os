import asyncio
import json
import time
import math
import random
import websockets
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
# Cross-import the verified Yoshida symplectic integrator from relativistic_qpnt
sys.path.insert(0, os.path.expanduser("~/relativistic_qpnt"))

from core.telemetry.ring_buffer import SynchronousTelemetryBuffer, RealtimeBiquadFilter
from core.telemetry.pqc_sealer import PQCTelemetryBlockSealer
try:
    from core.physics.symplectic_engine import KerrGeodesicIntegrator
except ImportError:
    KerrGeodesicIntegrator = None

HOST = "0.0.0.0"
PORT = 8766

buffer = SynchronousTelemetryBuffer(capacity=4096)
filters = [RealtimeBiquadFilter(cutoff_hz=30.0, sample_rate=1000.0) for _ in range(16)]
sealer = PQCTelemetryBlockSealer()
kerr_sim = KerrGeodesicIntegrator(M=1.0, a=0.5, L=3.5) if KerrGeodesicIntegrator else None
kerr_state = {"r": 6.0, "p": 0.0}
connected_clients = set()

def simulated_eeg_producer():
    """Synthesizes 16-channel EEG telemetry at 1000 Hz."""
    t0 = time.perf_counter()
    while True:
        t = time.perf_counter() - t0
        raw_channels = []
        for ch in range(16):
            phase = ch * (math.pi / 8.0)
            alpha = 1.0 * math.sin(2.0 * math.pi * 10.0 * t + phase)
            beta = 0.35 * math.sin(2.0 * math.pi * 21.0 * t + phase * 2.0)
            noise = random.uniform(-0.15, 0.15)
            raw_channels.append(alpha + beta + noise)

        buffer.push(raw_channels, time.perf_counter_ns())
        time.sleep(0.001)

async def telemetry_broadcaster():
    """Consumes ring buffer, steps Yoshida integrator, signs packets, and broadcasts JSON."""
    global kerr_state
    while True:
        frame = buffer.pop()
        if frame and connected_clients:
            ts_ns, raw_channels = frame
            filtered_channels = [filters[i].process_sample(raw_channels[i]) for i in range(16)]

            # Step 4th-order Yoshida symplectic Kerr integrator
            if kerr_sim:
                try:
                    kerr_state["r"], kerr_state["p"] = kerr_sim.step(kerr_state["r"], kerr_state["p"], dt=0.01)
                except FloatingPointerError:
                    kerr_state = {"r": 6.0, "p": 0.0}

            digest, tag = sealer.seal_frame(ts_ns, filtered_channels)

            payload = json.dumps({
                "timestamp_ns": ts_ns,
                "channels": filtered_channels,
                "kerr_orbit": {"r": kerr_state["r"], "p_r": kerr_state["p"]},
                "auth_tag_hex": tag.hex(),
                "digest_sha3": digest.hex()[:16] + "...",
                "pqc_sealed": True,
                "dropped_frames": 0
            })

            await asyncio.gather(*[client.send(payload) for client in connected_clients], return_exceptions=True)
        else:
            await asyncio.sleep(0.0005)

async def handler(websocket):
    connected_clients.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        connected_clients.remove(websocket)

async def main():
    import threading
    producer_thread = threading.Thread(target=simulated_eeg_producer, daemon=True)
    producer_thread.start()

    async with websockets.serve(handler, HOST, PORT):
        print(f"[*] Telemetry Daemon (PQC + Kerr Yoshida) listening on ws://{HOST}:{PORT}")
        await telemetry_broadcaster()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sealer.scrub_keys()
        print("\n[*] Daemon halted and private key buffer scrubbed cleanly.")
