from scipy.io import wavfile
from scipy.signal import butter, lfilter
import numpy as np
import matplotlib.pyplot as plt

INPUT_FILE = "/media/ahmed/78147566147527F0/desktop/ml_project/noisy_sine.wav"
OUTPUT_FILE = "clean_sine.wav"
TARGET_FS = 2000  # ADC/DAC rate
CUTOFF = 800      # Filter cutoff
PLOT_MS = 10 * 2     # Plot first 20ms

def main():
    # 1. Read and prepare signal
    fs, signal = wavfile.read(INPUT_FILE)
    signal = signal.astype(np.float32) / np.max(np.abs(signal))
    t = np.arange(len(signal)) / fs
    print(fs)

    # 2. ADC process (sampling)
    adc_times = np.arange(0, t[-1], 1 / TARGET_FS)
    sampled = np.interp(adc_times, t, signal)

    # 3. Digital filter
    b_digital, a_digital = butter(3, CUTOFF / (TARGET_FS / 2), 'low')
    filtered = lfilter(b_digital, a_digital, sampled)

    # 4. DAC process (zero-order hold)
    def zoh(out_times, in_times, values):
        indices = np.searchsorted(in_times, out_times, side='right') - 1
        return values[indices.clip(0, len(values) - 1)]
    
    dac_output = zoh(t, adc_times, filtered)

    # Save DAC output before reconstruction filter
    wavfile.write("dac_output_before_recon.wav", fs, dac_output.astype(np.float32))

    # 5. Reconstruction filter
    b_recon, a_recon = butter(3, CUTOFF / (fs / 2), 'low')
    recon_output = lfilter(b_recon, a_recon, dac_output)

    # Save final result
    wavfile.write(OUTPUT_FILE, fs, recon_output.astype(np.float32))

    # Create visualization
    plot_signals(t, signal, adc_times, sampled, filtered, dac_output, recon_output)

def plot_signals(t, original, adc_t, sampled, filtered, dac, recon):
    plt.figure(figsize=(10, 12))
    mask = t <= PLOT_MS / 1000
    plot_t = t[mask]
    
    # 1. Original Signal
    plt.subplot(5, 1, 1)
    plt.plot(plot_t, original[mask], 'gray')
    plt.title("1. Original Signal")
    plt.grid(True)
    
    # 2. Sampled Signal
    plt.subplot(5, 1, 2)
    plt.stem(adc_t[adc_t <= PLOT_MS / 1000], sampled[adc_t <= PLOT_MS / 1000], 
             linefmt='orange', markerfmt='o', basefmt=' ')
    plt.title("2. Sampled Signal")
    plt.grid(True)
    
    # 3. Filtered Signal
    plt.subplot(5, 1, 3)
    plt.stem(adc_t[adc_t <= PLOT_MS / 1000], filtered[adc_t <= PLOT_MS / 1000], 
             linefmt='green', markerfmt='o', basefmt=' ')
    plt.title("3. Filtered Signal")
    plt.grid(True)
    
    # 4. DAC Output
    plt.subplot(5, 1, 4)
    plt.plot(plot_t, dac[mask], 'blue', drawstyle='steps-post')
    plt.title("4. DAC Output")
    plt.grid(True)
    
     #5. Reconstructed Signal
    plt.subplot(5, 1, 5)
    plt.plot(plot_t, recon[mask], 'red')
    plt.title("5. Reconstructed Signal")
    plt.xlabel("Time (s)")
    plt.grid(True)

    
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()
