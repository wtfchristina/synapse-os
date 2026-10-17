import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import asyncio
import json
import websockets
import numpy as np
from core.synapse_dsp import SynapseDSP
from neuromod.precision_actuator import PrecisionActuator

dsp = SynapseDSP(sample_rate=1000.0)
actuator = PrecisionActuator(target_frequency_hz=40.0)

async def stream_handler(websocket):
    phase = 0.0
    history_window = []
    try:
        while True:
            phase += 0.05
            raw_frame = [
                float(np.sin(phase * (1.0 + ch * 0.2)) * 30.0 + np.random.normal(0, 3.0))
                for ch in range(16)
            ]
            filtered_frame = dsp.process_frame(raw_frame)
            history_window.append(filtered_frame[0])
            if len(history_window) > 256:
                history_window.pop(0)
            
            band_powers = dsp.compute_band_powers(history_window)
            x_coord = float(filtered_frame[0])
            v_coord = float(np.cos(phase) * 25.0)
            stim_feedback = actuator.evaluate_neural_feedback(band_powers, v_coord)
            
            payload = {
                "timestamp": asyncio.get_event_loop().time(),
                "channels": filtered_frame,
                "attractor": {"x": x_coord, "v": v_coord},
                "bands": band_powers,
                "actuator": stim_feedback
            }
            await websocket.send(json.dumps(payload))
            await asyncio.sleep(0.001)
    except websockets.ConnectionClosed:
        pass

async def main():
    async with websockets.serve(stream_handler, "0.0.0.0", 8766):
        print("[*] SYNAPSE-OS Q-Nexus Bridge live on ws://0.0.0.0:8766")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
