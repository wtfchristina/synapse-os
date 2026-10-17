import time

class PrecisionActuator:
    def __init__(self, target_frequency_hz=40.0, max_intensity_mw_cm2=150.0):
        self.target_freq = target_frequency_hz
        self.max_intensity = max_intensity_mw_cm2
        self.active_stim = False
        self.last_pulse_ts = 0.0

    def evaluate_neural_feedback(self, band_powers, phase_velocity):
        if band_powers.get("gamma", 0.0) < 12.0 and abs(phase_velocity) > 15.0:
            return self.trigger_microburst()
        return {"active": False, "intensity": 0.0}

    def trigger_microburst(self, duration_ms=20.0):
        self.active_stim = True
        self.last_pulse_ts = time.time()
        return {
            "active": True,
            "target_freq_hz": self.target_freq,
            "intensity_mw_cm2": self.max_intensity,
            "duration_ms": duration_ms,
            "waveform": "focussed_ultrasound_burst"
        }
