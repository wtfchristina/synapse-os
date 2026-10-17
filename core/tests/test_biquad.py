import unittest
import numpy as np
from synapse_dsp import NativeBiquadCascade, check_biquad_stability

class TestSynapseBiquad(unittest.TestCase):

    def test_stability_bounds(self):
        # Stable system: poles within unit circle (|p| < 1.0)
        self.assertTrue(check_biquad_stability(1.0, 0.0, -1.0, -1.2, 0.72))
        
        # Unstable system: pole strictly outside (|a2| >= 1.0)
        self.assertFalse(check_biquad_stability(1.0, 0.0, 0.0, 0.5, 1.15))
        
        # Unstable system: violates Schur-Cohn bounds (1 + a1 + a2 <= 0)
        self.assertFalse(check_biquad_stability(1.0, 0.0, 0.0, -1.5, 0.4))

    def test_rejection_of_unstable_cascade(self):
        unstable_coeffs = [[1.0, 0.0, 0.0, 0.5, 1.25]]
        with self.assertRaises(ValueError):
            NativeBiquadCascade(num_channels=4, coefficients=unstable_coeffs)

    def test_impulse_response_bibo_stability(self):
        # Lowpass biquad section
        coeffs = [[0.05, 0.1, 0.05, -1.2, 0.45]]
        cascade = NativeBiquadCascade(num_channels=1, coefficients=coeffs)
        
        # Inject large impulse load: delta[0] = 10,000 uV followed by zeros
        impulse = np.zeros(256, dtype=np.float32)
        impulse[0] = 10000.0
        
        out = cascade.process_block(channel_idx=0, in_samples=impulse)
        
        # Check for no NaNs, no Infs, and output convergence to 0
        self.assertFalse(np.isnan(out).any())
        self.assertFalse(np.isinf(out).any())
        self.assertLess(abs(out[-1]), 1e-4)

    def test_multi_channel_sample_stream(self):
        coeffs = [[0.1, 0.2, 0.1, -1.0, 0.5]]
        num_channels = 16
        cascade = NativeBiquadCascade(num_channels=num_channels, coefficients=coeffs)
        
        frame = np.ones(num_channels, dtype=np.float32)
        out = cascade.process_sample(frame)
        
        self.assertEqual(out.shape, (num_channels,))
        np.testing.assert_allclose(out, 0.1, atol=1e-5)

if __name__ == "__main__":
    unittest.main()
