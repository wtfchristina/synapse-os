import unittest
import numpy as np
from core.synapse_dsp import SynapseDSP
from neuromod.precision_actuator import PrecisionActuator

class TestQuantumNeuroSuite(unittest.TestCase):
    def setUp(self):
        self.dsp = SynapseDSP(sample_rate=1000.0)
        self.actuator = PrecisionActuator()

    def test_biquad_filtering_impulse_stability(self):
        impulse = [500.0] * 16
        response = self.dsp.process_frame(impulse)
        self.assertEqual(len(response), 16)
        self.assertFalse(any(np.isnan(response) | np.isinf(response)))

    def test_spectral_density_sum(self):
        window = [np.sin(i * 0.1) for i in range(256)]
        bands = self.dsp.compute_band_powers(window)
        total = sum(bands.values())
        self.assertAlmostEqual(total, 100.0, delta=2.0)

    def test_precision_actuation_threshold(self):
        bands = {"delta": 50.0, "theta": 20.0, "alpha": 20.0, "beta": 5.0, "gamma": 5.0}
        stim = self.actuator.evaluate_neural_feedback(bands, phase_velocity=20.0)
        self.assertTrue(stim["active"])
        self.assertEqual(stim["waveform"], "focussed_ultrasound_burst")

if __name__ == '__main__':
    unittest.main()
