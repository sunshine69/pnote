import pyaudio
import wave
import threading

# START RECORDING
chunk = 1024
FORMAT = pyaudio.paInt16

CHANNELS = 1
RATE = 44100
RECORD_SECONDS = 5
WAVE_OUTPUT_FILENAME = "recording.wav"
recording_done = False

p = pyaudio.PyAudio()

stream = p.open(format = FORMAT,
                channels = CHANNELS,
                rate = RATE,
                input = True,
                frames_per_buffer = chunk)

def stop_recording():
    global recording_done
    recording_done = True
    
t = threading.Timer(RECORD_SECONDS, stop_recording)

all = []
t.start()
while not recording_done:
    data = stream.read(chunk)
    all.append(data)

print "* done recording"

stream.close()
p.terminate()

# write data to WAVE file
data = ''.join(all)
wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
wf.setnchannels(CHANNELS)
wf.setsampwidth(p.get_sample_size(FORMAT))
wf.setframerate(RATE)
wf.writeframes(data)
wf.close()