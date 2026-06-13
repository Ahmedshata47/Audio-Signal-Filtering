import sys
import numpy as np
import pyqtgraph as pg
import soundfile as sf
import sounddevice as sd
from scipy.signal import butter, lfilter, resample_poly
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
import cv2
import threading
import mss
import time
import moviepy.editor as mp

# === USER CONFIG ===
FNAME        = "/media/ahmed/78147566147527F0/desktop/ml_project/noisy_sine.wav"
MIC_RATE     = 44100
TARGET_FS    = 2000
CUTOFF       = 800
ORDER        = 5
WINDOW_SEC   = 0.1      # 100ms window
UPDATE_MS    = 30       # ~33 FPS
STAGE_SEC    = 3        # 3s per stage
FPS          = 30       # Video frame rate

# Derived
WINDOW_SAMPS     = int(MIC_RATE * WINDOW_SEC)
CHUNK_SAMPS      = int(MIC_RATE * UPDATE_MS / 1000)
TICKS_PER_STAGE  = int((STAGE_SEC * 1000) / UPDATE_MS)

# === LOAD + NORMALIZE ===
audio, fs = sf.read(FNAME)
audio = audio.astype(np.float32)[: fs * 3]
audio /= np.max(np.abs(audio))

# === PIPELINE ===
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

# === STREAMS ===
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

play_stages    = {'Analog', 'DAC', 'Reconstructed'}
impulse_stages = {'ADC', 'Filter'}

# New color mapping:
colors = {
    'Analog'        : 'y',
    'ADC'           : 'c',   # cyan impulses
    'Filter'        : 'm',   # magenta impulses
    'DAC'           : 'r',
    'Reconstructed' : 'w',
}

# === QT + PLOT ===
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

# silent callback
def silent_cb(out, frames, time, status):
    out[:] = 0
stream = sd.OutputStream(channels=1, samplerate=MIC_RATE, callback=silent_cb)
stream.start()

# === STATE ===
stages = list(streams.keys())
idx    = 0
pos    = 0
tick   = 0

# === UPDATE ===
def update():
    global idx, pos, tick

    name = stages[idx]
    sig  = streams[name]

    # on stage start
    if tick == 0:
        pos = 0
        if name in play_stages:
            sd.stop()
            sd.play(sig, MIC_RATE)

    # wrap scroll
    if pos + WINDOW_SAMPS > len(sig):
        pos = 0
    window = sig[pos:pos+WINDOW_SAMPS]
    t = np.linspace(0, WINDOW_SEC, WINDOW_SAMPS)
    pos += CHUNK_SAMPS

    plot.setTitle(name, color=colors[name], size='14pt')

    if name in impulse_stages:
        # hide curve
        curve.setData([], [])
        # build impulse segments
        xs = np.empty(WINDOW_SAMPS*3, float)
        ys = np.empty(WINDOW_SAMPS*3, float)
        xs[0::3] = t;      xs[1::3] = t;      xs[2::3] = np.nan
        ys[0::3] = 0;      ys[1::3] = window; ys[2::3] = np.nan
        lineseg.setData(xs, ys, pen=pg.mkPen(colors[name], width=1))
    else:
        # hide impulses
        lineseg.setData([], [])
        # draw waveform
        curve.setPen(colors[name], width=2)
        curve.setData(t, window)

    tick += 1
    if tick >= TICKS_PER_STAGE:
        tick = 0
        idx = (idx + 1) % len(stages)

# === SCREEN AND AUDIO RECORDING ===
recording = True
def record_screen_and_audio(filename="signal_visualization_with_audio.avi", duration=3 * STAGE_SEC, fps=FPS):
    global recording
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        out = cv2.VideoWriter(filename, cv2.VideoWriter_fourcc(*"XVID"),
                              fps, (monitor["width"], monitor["height"]))
        start_time = time.time()
        
        # Audio file to save the sound
        audio_file = "audio_recorded.wav"
        sd.play(streams['Analog'], MIC_RATE)  # Play the audio stream
        while recording and time.time() - start_time < duration:
            # Capture screen frame
            img = np.array(sct.grab(monitor))
            frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            out.write(frame)
            time.sleep(1 / fps)
        out.release()

        # Save audio to file
        sf.write(audio_file, audio, MIC_RATE)
        print(f"✅ Screen and audio recording saved to: {filename} and {audio_file}")

# === SCREEN RECORD THREAD ===
record_thread = threading.Thread(target=record_screen_and_audio)
record_thread.start()

# === TIMER ===
timer = QTimer()
timer.timeout.connect(update)
timer.start(UPDATE_MS)

sys.exit(app.exec_())

# Stop recording
recording = False
record_thread.join()

# === Combine Video and Audio using moviepy ===
def combine_audio_video(video_file="signal_visualization_with_audio.avi", audio_file="audio_recorded.wav", final_output="final_output_with_audio.avi"):
    video_clip = mp.VideoFileClip(video_file)
    audio_clip = mp.AudioFileClip(audio_file)

    # Set audio to video
    video_clip = video_clip.set_audio(audio_clip)

    # Write final video with audio
    video_clip.write_videofile(final_output, codec="libx264", audio_codec="aac")
    print(f"✅ Final video with audio saved as: {final_output}")

# Combine audio and video after the recording ends
combine_audio_video()
