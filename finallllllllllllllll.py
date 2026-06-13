import sys
import numpy as np
import pyqtgraph as pg
import soundfile as sf
import sounddevice as sd
from scipy.signal import butter, lfilter, resample_poly
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

# === USER CONFIG ===
FNAME        = "/media/ahmed/78147566147527F0/desktop/ml_project/noisy_sine.wav"
MIC_RATE     = 48000  # Changed to common default rate
TARGET_FS    = 2000
CUTOFF       = 800
ORDER        = 5
WINDOW_SEC   = 0.1    # 100ms window
UPDATE_MS    = 30     # ~33 FPS
STAGE_SEC    = 3      # 3s per stage

# Derived parameters
WINDOW_SAMPS     = int(MIC_RATE * WINDOW_SEC)
CHUNK_SAMPS      = int(MIC_RATE * UPDATE_MS / 1000)
TICKS_PER_STAGE  = int((STAGE_SEC * 1000) / UPDATE_MS)

# === AUDIO INITIALIZATION ===
print("Available audio devices:")
print(sd.query_devices())

# Try to find a valid output device
try:
    default_device = sd.default.device[1]
    print(f"Using default output device: {default_device}")
except Exception as e:
    print(f"Error getting default device: {e}")
    default_device = None

# === LOAD + PROCESS AUDIO ===
try:
    audio, fs = sf.read(FNAME)
    audio = audio.astype(np.float32)[: fs * 3]
    audio /= np.max(np.abs(audio))
    print("Audio file loaded successfully")
except Exception as e:
    print(f"Error loading audio file: {e}")
    sys.exit(1)

# Signal processing pipeline
try:
    analog = resample_poly(audio, MIC_RATE, fs)
    adc    = resample_poly(analog, TARGET_FS, MIC_RATE)
    b1, a1 = butter(ORDER, CUTOFF/(0.5*TARGET_FS), 'low')
    filt   = lfilter(b1, a1, adc)
    
    t_full = np.arange(len(analog)) / MIC_RATE
    t_adc  = np.arange(0, t_full[-1], 1/TARGET_FS)
    
    def zoh(t_out, t_in, vals):
        idx = np.searchsorted(t_in, t_out, 'right') - 1
        idx = np.clip(idx, 0, len(vals)-1)
        return vals[idx]
    
    dac    = zoh(t_full, t_adc, filt)
    b2, a2 = butter(ORDER, CUTOFF/(0.5*MIC_RATE), 'low')
    recon  = lfilter(b2, a2, dac)
except Exception as e:
    print(f"Signal processing error: {e}")
    sys.exit(1)

# === STREAMS SETUP ===
def upsample(x, fs_in, length):
    t0 = np.linspace(0, len(x)/fs_in, len(x))
    t1 = np.linspace(0, len(x)/fs_in, length)
    return np.interp(t1, t0, x)

streams = {
    'Analog'        : analog,
    'ADC'           : upsample(adc, TARGET_FS, len(analog)),
    'Filter'        : upsample(filt, TARGET_FS, len(analog)),
    'DAC'           : dac,
    'Reconstructed' : recon,
}

# Visualization settings
colors = {
    'Analog'        : 'y',
    'ADC'           : 'c',
    'Filter'        : 'm',
    'DAC'           : 'r',
    'Reconstructed' : 'w',
}

play_stages    = {'Analog', 'DAC', 'Reconstructed'}
impulse_stages = {'ADC', 'Filter'}

# === GUI SETUP ===
app  = QApplication(sys.argv)
win  = pg.GraphicsLayoutWidget(title="Real-Time Pipeline")
plot = win.addPlot()
plot.setYRange(-1, 1)
plot.setXRange(0, WINDOW_SEC)

curve   = pg.PlotDataItem(pen=colors['Analog'], width=2)
lineseg = pg.PlotDataItem(pen=pg.mkPen(colors['ADC'], width=1))
plot.addItem(curve)
plot.addItem(lineseg)
win.show()

# === AUDIO STREAM HANDLING ===
class AudioManager:
    def __init__(self):
        self.stream = None
        self.active = False
        
    def start(self):
        try:
            if default_device is not None:
                self.stream = sd.OutputStream(
                    device=default_device,
                    channels=1,
                    samplerate=MIC_RATE,
                    blocksize=CHUNK_SAMPS,
                    dtype=np.float32
                )
                self.stream.start()
                self.active = True
                print("Audio stream started successfully")
        except Exception as e:
            print(f"Could not initialize audio stream: {e}")
            self.active = False

audio_mgr = AudioManager()
audio_mgr.start()

# === STATE MANAGEMENT ===
stages = list(streams.keys())
idx    = 0
pos    = 0
tick   = 0

# === MAIN UPDATE FUNCTION ===
def update():
    global idx, pos, tick

    name = stages[idx]
    sig  = streams[name]

    # Stage initialization
    if tick == 0:
        pos = 0
        if name in play_stages and audio_mgr.active:
            try:
                sd.stop()
                sd.play(sig, MIC_RATE, blocking=False)
            except Exception as e:
                print(f"Playback failed: {e}")

    # Window management
    if pos + WINDOW_SAMPS > len(sig):
        pos = 0
    window = sig[pos:pos+WINDOW_SAMPS]
    t = np.linspace(0, WINDOW_SEC, WINDOW_SAMPS)
    pos += CHUNK_SAMPS

    # Update visualization
    plot.setTitle(name, color=colors[name], size='14pt')

    if name in impulse_stages:
        curve.setData([], [])
        xs = np.empty(WINDOW_SAMPS*3, float)
        ys = np.empty(WINDOW_SAMPS*3, float)
        xs[0::3] = t; xs[1::3] = t; xs[2::3] = np.nan
        ys[0::3] = 0; ys[1::3] = window; ys[2::3] = np.nan
        lineseg.setData(xs, ys, pen=pg.mkPen(colors[name], width=1))
    else:
        lineseg.setData([], [])
        curve.setPen(colors[name], width=2)
        curve.setData(t, window)

    # Stage progression
    tick += 1
    if tick >= TICKS_PER_STAGE:
        tick = 0
        idx = (idx + 1) % len(stages)

# === TIMER AND EXECUTION ===
timer = QTimer()
timer.timeout.connect(update)
timer.start(UPDATE_MS)

try:
    sys.exit(app.exec_())
except Exception as e:
    print(f"Application error: {e}")
finally:
    if audio_mgr.active:
        sd.stop()
        audio_mgr.stream.stop()

