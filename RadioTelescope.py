import tkinter as tk
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, lfilter
from scipy.io.wavfile import write
import csv
import threading
import openai

try:
    from rtlsdr import RtlSdr
    sdr_available = True
except ImportError:
    sdr_available = False

# Globals for Control
scanning = False
recording = False
spectrogram_enabled = False
use_rtlsdr = sdr_available
auto_adjust_enabled = False  # Toggle for AI auto-adjustment

# Store scanned data for AI usage
scanned_data = []

# OpenAI API Key
openai.api_key = "your-openai-api-key"

# Signal Processing Functions
def amplify_signal(signal, factor=10):
    return signal * factor

def butter_lowpass_filter(data, cutoff, fs, order=5):
    nyquist = 0.5 * fs
    normal_cutoff = cutoff / nyquist
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    return lfilter(b, a, data)

# Simulated SDR Signal
def simulate_signal(frequency, sample_rate, duration=1.0):
    t = np.arange(0, duration, 1 / sample_rate)
    signal = np.sin(2 * np.pi * frequency * t)  # Pure tone
    noise = np.random.normal(0, 0.5, len(signal))  # Add noise
    return signal + noise

# Initialize RTL-SDR (if available)
if sdr_available:
    sdr = RtlSdr()
    sdr.sample_rate = 2.048e6
    sdr.center_freq = 1420e6
    sdr.gain = 49.6

# AI Decision-Making for Adjustments
def ai_adjust_settings():
    global scanned_data, auto_adjust_enabled

    if not auto_adjust_enabled or not scanned_data:
        return

    # Summarize the scanned data for AI input
    context = "\n".join(
        [f"Azimuth: {d['azimuth']}, Elevation: {d['elevation']}, Frequency: {d['frequency'] / 1e6:.2f} MHz, Max Power: {d['max_power']:.2f}" for d in scanned_data]
    )

    # Ask the AI for adjustments
    prompt = f"""
You are controlling a radio telescope. Based on the following scanned data, recommend adjustments to azimuth, elevation, or frequency range to improve signal detection.

Scanned Data:
{context}

Recommendations (e.g., "Increase azimuth to 90", "Focus on frequencies 1420-1425 MHz", etc.):
"""
    try:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=100
        )
        recommendations = response["choices"][0]["text"].strip()
        process_ai_recommendations(recommendations)
    except Exception as e:
        print(f"Error in AI adjustment: {e}")

def process_ai_recommendations(recommendations):
    """Parse and apply AI recommendations."""
    if "azimuth" in recommendations.lower():
        azimuth_value = int(recommendations.split("azimuth to")[1].split()[0])
        azimuth_slider.set(azimuth_value)
        print(f"AI adjusted azimuth to {azimuth_value}")

    if "elevation" in recommendations.lower():
        elevation_value = int(recommendations.split("elevation to")[1].split()[0])
        elevation_slider.set(elevation_value)
        print(f"AI adjusted elevation to {elevation_value}")

    if "frequency" in recommendations.lower():
        print("AI suggested frequency adjustment. Manual implementation required for range changes.")

# Scanning Function
def scan():
    global scanning, recording, spectrogram_enabled, scanned_data

    azimuth = azimuth_slider.get()
    elevation = elevation_slider.get()
    frequencies = np.linspace(1400e6, 1430e6, 100)
    sample_rate = 2.048e6

    scanned_data = []  # Reset scanned data for each new scan

    if recording:
        file = open("scan_results.csv", "a")
        writer = csv.writer(file)

    plt.figure(figsize=(10, 6))

    for idx, freq in enumerate(frequencies):
        if not scanning:
            break

        if use_rtlsdr and sdr_available:
            sdr.center_freq = freq
            samples = sdr.read_samples(256 * 1024)
        else:
            samples = simulate_signal(freq, sample_rate)

        amplified = amplify_signal(samples, factor=15)
        filtered = butter_lowpass_filter(amplified, cutoff=0.1 * sample_rate, fs=sample_rate)

        fft_result = np.fft.fftshift(np.fft.fft(filtered))
        power = np.abs(fft_result) ** 2

        if recording:
            writer.writerow([azimuth, elevation, freq, np.max(power)])

        frequency_label.config(text=f"Frequency: {freq / 1e6:.2f} MHz")

        # Save as a .wav file
        scaled_filtered = np.int16(filtered / np.max(np.abs(filtered)) * 32767)  # Scale to int16
        write(f"output_{idx}.wav", int(sample_rate), scaled_filtered)

        # Store data for AI analysis
        scanned_data.append({
            "azimuth": azimuth,
            "elevation": elevation,
            "frequency": freq,
            "max_power": np.max(power)
        })

        # AI-driven auto-adjustment
        ai_adjust_settings()

        # Live Power Spectrum Plot
        plt.clf()
        plt.subplot(2, 1, 1)
        plt.plot(np.fft.fftshift(np.fft.fftfreq(len(filtered), 1 / sample_rate)), power)
        plt.title(f"Power Spectrum at {freq / 1e6:.2f} MHz")
        plt.grid()

        # Optional Spectrogram
        if spectrogram_enabled:
            plt.subplot(2, 1, 2)
            plt.specgram(filtered, Fs=int(sample_rate), NFFT=1024, noverlap=512, cmap="viridis")
            plt.title("Spectrogram")
            plt.xlabel("Time")
            plt.ylabel("Frequency")

        plt.pause(0.1)

    if recording:
        file.close()

    plt.show()

# Toggle Auto-Adjustment
def toggle_auto_adjust():
    global auto_adjust_enabled
    auto_adjust_enabled = not auto_adjust_enabled
    auto_adjust_button.config(
        text="Auto Adjust: ON" if auto_adjust_enabled else "Auto Adjust: OFF",
        bg="lightgreen" if auto_adjust_enabled else "lightgray"
    )

# Start/Stop Scanning Functions
def start_scanning():
    global scanning
    if not scanning:
        scanning = True
        threading.Thread(target=scan, daemon=True).start()

def stop_scanning():
    global scanning
    scanning = False

def toggle_recording():
    global recording
    recording = not recording
    record_button.config(text="Recording: ON" if recording else "Recording: OFF", bg="lightgreen" if recording else "lightgray")

# Toggle Spectrogram
def toggle_spectrogram():
    global spectrogram_enabled
    spectrogram_enabled = not spectrogram_enabled
    spectrogram_button.config(text="Spectrogram: ON" if spectrogram_enabled else "Spectrogram: OFF", bg="lightblue" if spectrogram_enabled else "lightgray")

# UI Setup
root = tk.Tk()
root.title("Telescope Controller with AI Auto-Adjustment")

# Display Current Frequency
frequency_label = tk.Label(root, text="Frequency: - MHz", font=("Arial", 14))
frequency_label.pack(pady=10)

# Azimuth and Elevation Sliders
azimuth_slider = tk.Scale(root, from_=0, to=180, label="Azimuth", orient=tk.HORIZONTAL)
azimuth_slider.pack(fill=tk.X, padx=20, pady=10)

elevation_slider = tk.Scale(root, from_=0, to=180, label="Elevation", orient=tk.HORIZONTAL)
elevation_slider.pack(fill=tk.X, padx=20, pady=10)

# Control Buttons
button_frame = tk.Frame(root)
button_frame.pack(pady=10)

start_button = tk.Button(button_frame, text="Start Scanning", command=start_scanning, font=("Arial", 12), bg="lightblue")
start_button.grid(row=0, column=0, padx=5)

stop_button = tk.Button(button_frame, text="Stop Scanning", command=stop_scanning, font=("Arial", 12), bg="red")
stop_button.grid(row=0, column=1, padx=5)

auto_adjust_button = tk.Button(button_frame, text="Auto Adjust: OFF", command=toggle_auto_adjust, font=("Arial", 12), bg="lightgray")
auto_adjust_button.grid(row=0, column=2, padx=5)

record_button = tk.Button(button_frame, text="Recording: OFF", command=toggle_recording, font=("Arial", 12), bg="lightgray")
record_button.grid(row=0, column=4, padx=5)

spectrogram_button = tk.Button(button_frame, text="Spectrogram: OFF", command=toggle_spectrogram, font=("Arial", 12), bg="lightgray")
spectrogram_button.grid(row=0, column=3, padx=5)
# Cleanup on Close
def on_close():
    global scanning
    scanning = False
    if sdr_available and use_rtlsdr:
        sdr.close()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)
root.mainloop()
