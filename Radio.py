# -*- coding: utf-8 -*-
"""
Created on Tue Nov 26 18:59:57 2024

@author: Legoboy
"""
import subprocess
import numpy as np
import wave
import os

def listen_to_radio(frequency: float, sample_rate: int, gain: int, output_file: str):
    """
    Listen to a radio frequency and save raw IQ data or activate demo mode.
    
    Args:
        frequency (float): Frequency to tune to, in MHz.
        sample_rate (int): Sampling rate, in Hz.
        gain (int): Gain setting for the radio hardware.
        output_file (str): File to save raw IQ data.
    """
    try:
        # Convert MHz to Hz for RTL-SDR
        frequency_hz = int(frequency * 1e6)

        # Construct the command to use rtl_sdr
        command = [
            "rtl_sdr",
            "-f", str(frequency_hz),
            "-s", str(sample_rate),
            "-g", str(gain),
            output_file
        ]

        print(f"Starting radio capture at {frequency} MHz...")
        subprocess.run(command, check=True)
        print(f"Data saved to {output_file}.")
    except FileNotFoundError:
        print("rtl_sdr command not found. Activating demo mode...")
        activate_demo_mode(output_file)
    except subprocess.CalledProcessError as e:
        print(f"Error capturing radio signal: {e}. Activating demo mode...")
        activate_demo_mode(output_file)
    except Exception as e:
        print(f"An unexpected error occurred: {e}. Activating demo mode...")
        activate_demo_mode(output_file)

def activate_demo_mode(output_file: str):
    """
    Simulate radio signal reception by generating demo data.

    Args:
        output_file (str): File to save simulated data.
    """
    print("Generating demo radio signal...")
    
    # Simulate an audio tone
    duration = 5  # seconds
    sample_rate = 44100  # Hz
    frequency = 1000  # Hz (tone frequency)
    amplitude = 32767  # Max value for 16-bit audio

    # Create a sine wave
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    wave_data = (amplitude * np.sin(2 * np.pi * frequency * t)).astype(np.int16)

    # Save the sine wave as a WAV file
    with wave.open("demo_output.wav", "w") as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit audio
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(wave_data.tobytes())

    print("Demo mode signal saved as 'demo_output.wav'. Play this file for the demo.")
    print("Exiting demo mode.")

# Example usage
if __name__ == "__main__":
    output_file = "radio_output.bin"
    listen_to_radio(frequency=100.1, sample_rate=2_048_000, gain=30, output_file=output_file)
