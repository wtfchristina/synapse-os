import numpy as np
from scipy import signal

class SynapseDSP:
    def __init__(self, sample_rate=1000.0, lowcut=0.5, highcut=100.0, notch_freq=60.0):
        self.sample_rate = sample_rate
        self.lowcut = lowcut
        self.highcut = highcut
        self.notch_freq = notch_freq
        
        nyq = 0.5 * sample_rate
        self.b_band, self.a_band = signal.butter(4, [lowcut / nyq, highcut / nyq], btype='band')
        self.b_notch, self.a_notch = signal.iirnotch(notch_freq / nyq, 30.0)
        
        self.zi_band = [signal.lfilter_zi(self.b_band, self.a_band) for _ in range(16)]
        self.zi_notch = [signal.lfilter_zi(self.b_notch, self.a_notch) for _ in range(16)]

    def process_frame(self, channels_data):
        filtered = []
        for i, val in enumerate(channels_data):
            y_notch, self.zi_notch[i] = signal.lfilter(self.b_notch, self.a_notch, [val], zi=self.zi_notch[i])
            y_band, self.zi_band[i] = signal.lfilter(self.b_band, self.a_band, y_notch, zi=self.zi_band[i])
            filtered.append(float(y_band[0]))
        return filtered

    def compute_band_powers(self, window_buffer):
        sig = np.array(window_buffer)
        if len(sig) < 32:
            return {"delta": 20.0, "theta": 20.0, "alpha": 20.0, "beta": 20.0, "gamma": 20.0}
        fft_vals = np.abs(np.fft.rfft(sig))
        freqs = np.fft.rfftfreq(len(sig), 1.0 / self.sample_rate)
        
        def band_power(f_low, f_high):
            idx = np.logical_and(freqs >= f_low, freqs <= f_high)
            return float(np.sum(fft_vals[idx]**2))
            
        d = band_power(0.5, 4.0)
        t = band_power(4.0, 8.0)
        a = band_power(8.0, 13.0)
        b = band_power(13.0, 30.0)
        g = band_power(30.0, 100.0)
        total = d + t + a + b + g + 1e-12
        
        return {
            "delta": round((d / total) * 100, 1),
            "theta": round((t / total) * 100, 1),
            "alpha": round((a / total) * 100, 1),
            "beta": round((b / total) * 100, 1),
            "gamma": round((g / total) * 100, 1)
        }
