import asyncio
import json
import websockets
import numpy as np
from synapse_dsp import NativeBiquadCascade

# 16-channel, 1,000 Hz setup
NUM_CHANNELS = 16
SAMPLING_RATE_HZ = 1000.0
PORT = 8766

# Standard 4th-order Butterworth bandpass (8–30 Hz sensorimotor Mu/Beta isolation)
SOS_COEFFS = [
    [0.0055,  0.0110, 0.0055, -1.8890, 0.8920],
    [1.0000, -2.0000, 1.0000, -1.9310, 0.9350]
]

# Instantiate native C99 filter cascade
filter_cascade = NativeBiquadCascade(num_channels=NUM_CHANNELS, coefficients=SOS_COEFFS)

# Pre-allocated float32 frame buffers for zero-allocation streaming
raw_frame = np.zeros(NUM_CHANNELS, dtype=np.float32)
filtered_frame = np.zeros(NUM_CHANNELS, dtype=np.float32)

connected_clients = set()

async def telemetry_broadcaster():
    """
    Simulates real-time 1,000 Hz biosignal acquisition, runs C-accelerated
    filtering, and broadcasts to connected WebGL/cockpit frontends.
    """
    t = 0.0
    dt = 1.0 / SAMPLING_RATE_HZ

    while True:
        # Synthetic 16-channel biosignal: 10 Hz Alpha wave + 60 Hz line noise + Gaussian noise
        alpha_wave = np.sin(2.0 * np.pi * 10.0 * t)
        mains_noise = 0.5 * np.sin(2.0 * np.pi * 60.0 * t)
        noise = np.random.normal(0.0, 0.2, NUM_CHANNELS).astype(np.float32)

        raw_frame[:] = (alpha_wave + mains_noise) + noise

        # Execute C-accelerated zero-copy filtering
        filter_cascade.process_sample(raw_frame, out_frame=filtered_frame)

        # Broadcast frame payload if clients are connected
        if connected_clients:
            payload = json.dumps({
                "timestamp_ms": round(t * 1000.0, 3),
                "raw": raw_frame.tolist(),
                "filtered": filtered_frame.tolist(),
            })
            await asyncio.gather(
                *[client.send(payload) for client in connected_clients],
                return_exceptions=True
            )

        t += dt
        await asyncio.sleep(dt)

async def handler(websocket):
    connected_clients.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        connected_clients.remove(websocket)

async def main():
    async with websockets.serve(handler, "localhost", PORT):
        print(f"[SYNAPSE-OS] Telemetry bridge listening on ws://localhost:{PORT}")
        print(f"[SYNAPSE-OS] Deterministic C-pipeline active ({NUM_CHANNELS} channels @ {SAMPLING_RATE_HZ:.0f} Hz)")
        await telemetry_broadcaster()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[SYNAPSE-OS] Bridge terminated.")
