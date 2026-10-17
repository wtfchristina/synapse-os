import asyncio
import json
import websockets

async def verify_stream():
    uri = "ws://localhost:8766"
    async with websockets.connect(uri) as ws:
        message = await ws.recv()
        data = json.loads(message)

        # Telemetry & PQC Invariants
        assert len(data["channels"]) == 16, f"Expected 16 channels, got {len(data['channels'])}"
        assert data.get("pqc_sealed") is True, "PQC seal invariant missing"
        assert len(data.get("auth_tag_hex", "")) == 64, "Malformed SHA-256 HMAC authentication tag"

        # Relativistic Kerr Symplectic Orbit Invariant
        assert "kerr_orbit" in data, "Missing 'kerr_orbit' in telemetry packet"
        kerr = data["kerr_orbit"]
        assert "r" in kerr and "p_r" in kerr, "Malformed Kerr phase-space state vector"
        assert kerr["r"] > 1.866, "Coordinate entered or crossed event horizon boundary"

        print(f"Verification Successful: Connected to {uri}")
        print(f"PQC Seal Tag: {data['auth_tag_hex']}")
        print(f"Kerr Geodesic State: r={kerr['r']:.4f}, p_r={kerr['p_r']:.4f}")
        print(f"Channels verified: 16/16 at {data['timestamp_ns']} ns")

if __name__ == "__main__":
    asyncio.run(verify_stream())
