import matplotlib
matplotlib.use('Agg')  # Must be set before importing pyplot
import numpy as np
import wave
import pyaudio
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore
import sys
import threading
import matplotlib.pyplot as plt
import cv2
from moviepy.editor import VideoFileClip, AudioFileClip

# Constants
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
FPS = 30
VIDEO_DURATION = 5  # seconds

# Globals
audio_frames = []
recording = True

# Suppress ALSA errors
from ctypes import *
ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)
def py_error_handler(filename, line, function, err, fmt):
    pass
c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)
asound = cdll.LoadLibrary('libasound.so')
asound.snd_lib_error_set_handler(c_error_handler)

pa = pyaudio.PyAudio()

# PyQtGraph window
class AudioVisualizer(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Real-Time Audio Visualizer")
        self.plot_widget = pg.PlotWidget()
        self.setCentralWidget(self.plot_widget)
        self.plot = self.plot_widget.plot()
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.plot_widget.setYRange(-32768, 32767)
        self.timer.start(1000 // FPS)

    def update_plot(self):
        if audio_frames:
            current_chunk = audio_frames[-1]
            audio_np = np.frombuffer(current_chunk, dtype=np.int16)
            self.plot.setData(audio_np)

def record_audio():
    stream = pa.open(format=FORMAT,
                     channels=CHANNELS,
                     rate=RATE,
                     input=True,
                     frames_per_buffer=CHUNK)
    while recording:
        try:
            data = stream.read(CHUNK, exception_on_overflow=False)
            audio_frames.append(data)
        except IOError as e:
            print(f"Audio read error: {e}")
            continue
    stream.stop_stream()
    stream.close()

def save_audio(filename="audio_recorded.wav"):
    total_samples = RATE * VIDEO_DURATION
    audio_data = np.frombuffer(b''.join(audio_frames), dtype=np.int16)
    
    if len(audio_data) > total_samples:
        audio_data = audio_data[:total_samples]
    elif len(audio_data) < total_samples:
        audio_data = np.pad(audio_data, (0, total_samples - len(audio_data)), 'constant')
    
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(pa.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(audio_data.tobytes())

def create_video(filename="signal_visualization.mp4"):
    with wave.open("audio_recorded.wav", 'rb') as wf:
        audio_data = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
    
    height, width = 480, 640
    writer = cv2.VideoWriter(filename, cv2.VideoWriter_fourcc(*'mp4v'), FPS, (width, height))
    samples_per_frame = RATE // FPS
    total_frames = int(VIDEO_DURATION * FPS)
    
    for i in range(total_frames):
        start = i * samples_per_frame
        end = start + samples_per_frame
        frame_samples = audio_data[start:end] if start < len(audio_data) else np.zeros(samples_per_frame, dtype=np.int16)
        
        fig, ax = plt.subplots(figsize=(6.4, 4.8), dpi=100)
        ax.plot(frame_samples, color='lime')
        ax.set_ylim(-32768, 32767)
        ax.axis('off')
        fig.tight_layout(pad=0)
        fig.canvas.draw()
        
        img = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
        img = img.reshape((480, 640, 3))
        plt.close(fig)
        
        writer.write(cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    
    writer.release()

def combine_audio_video(output="final_output_with_audio.mp4"):
    video = VideoFileClip("signal_visualization.mp4")
    audio = AudioFileClip("audio_recorded.wav")
    video = video.set_audio(audio)
    video.write_videofile(output, codec="libx264", audio_codec="aac")

def main():
    global recording
    app = QtWidgets.QApplication(sys.argv)
    visualizer = AudioVisualizer()
    visualizer.show()

    audio_thread = threading.Thread(target=record_audio)
    audio_thread.start()

    QtCore.QTimer.singleShot(VIDEO_DURATION * 1000, app.quit)
    app.exec()

    recording = False
    audio_thread.join()

    save_audio()
    create_video()
    combine_audio_video()
    print("✅ Processing complete! Output: final_output_with_audio.mp4")

if __name__ == "__main__":
    main()