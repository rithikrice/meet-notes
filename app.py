from flask import Flask, request, jsonify
import threading
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import pyaudio
import wave
from google.cloud import speech
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import os
import chromedriver_autoinstaller
chromedriver_autoinstaller.install()  # Installs the correct version

app = Flask(__name__)

# Audio recording configurations
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
WAVE_OUTPUT_FILENAME = "meeting_audio.wav"
recording_event = threading.Event()

def record_audio():
    audio = pyaudio.PyAudio()
    stream = audio.open(format=FORMAT, channels=CHANNELS,
                        rate=RATE, input=True,
                        frames_per_buffer=CHUNK)
    frames = []

    print("Recording started...")
    try:
        while recording_event.is_set():
            data = stream.read(CHUNK)
            frames.append(data)
    except Exception as e:
        print(f"Error during recording: {e}")
    finally:
        print("Recording stopped.")
        stream.stop_stream()
        stream.close()
        audio.terminate()

    with wave.open(WAVE_OUTPUT_FILENAME, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(audio.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))


def join_meeting(link):
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--headless')  # Run in headless mode
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--window-size=1920,1080')

    service = Service(chromedriver_autoinstaller.install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get(link)

    time.sleep(5)  # Wait for the page to load

    try:
        join_button = driver.find_element(By.XPATH, "//span[text()='Join now']")
        join_button.click()
        print("Bot joined the meeting.")
    except Exception as e:
        print(f"Failed to join meeting: {e}")

    return driver

def transcribe_audio():
    client = speech.SpeechClient()

    with open(WAVE_OUTPUT_FILENAME, 'rb') as audio_file:
        audio_content = audio_file.read()

    audio = speech.RecognitionAudio(content=audio_content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=RATE,
        language_code="en-US",
    )

    response = client.recognize(config=config, audio=audio)
    transcript = " ".join(result.alternatives[0].transcript for result in response.results)
    return transcript

@app.route('/join_meeting', methods=['POST'])
def handle_meeting():
    try:
        global recording
        recording = True

        data = request.json
        meeting_link = data.get('meeting_link')
        flash_api_key = data.get('flash_api_key')

        if not meeting_link or not flash_api_key:
            return jsonify({"error": "Meeting link and Flash API key are required."}), 400

        app.logger.info(f"Meeting Link: {meeting_link}")
        app.logger.info(f"Flash API Key: {flash_api_key}")

        # Start recording audio in a separate thread
        recorder_thread = threading.Thread(target=record_audio)
        recorder_thread.start()

        # Join the meeting
        driver = join_meeting(meeting_link)

        # Simulate meeting duration (e.g., 60 seconds)
        time.sleep(60)

        # Stop recording
        recording = False
        recorder_thread.join()

        # Quit the browser
        driver.quit()

        # Transcribe the recorded audio
        transcript = transcribe_audio()

        # Send transcript to Flash API for summarization (Placeholder)
        summary = f"[Simulated Summary] {transcript[:100]}..."

        return jsonify({"transcript": transcript, "summary": summary}), 200

    except Exception as e:
        app.logger.error(f"Error: {e}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
