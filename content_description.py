import threading
import cv2
from PIL import Image
import io
from dotenv import load_dotenv
import os
import tkinter as tk
from google.cloud import texttospeech
import google.generativeai as genai
import google.ai.generativelanguage as glm
from google.api_core import exceptions 
from queue import Queue, Empty
import pyaudio
import wave
import time

# Set the GOOGLE_APPLICATION_CREDENTIALS environment variable
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = r"C:\Users\btina\LLM\LiveRecording\src\liverecording2024-daf922ab2143.json"

load_dotenv()
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
model = genai.GenerativeModel('gemini-1.5-pro') 
#gemini-pro-vision

class ContentDescriber:
    def __init__(self, root, user_input, video_handler):
        self.root = root
        self.user_input = user_input
        self.video_handler = video_handler
        self.message_var = tk.StringVar()
        self.queue = Queue()
        self.is_closing = False  # Flag to handle app closure

        # Schedule the process_queue method
        self.root.after(100, self.process_queue)
        self.client = texttospeech.TextToSpeechClient()
        self.is_closing = False  # Flag to handle app closure

        # Ensure the output directory exists
        self.output_dir = "C:\\Users\\btina\\Documents\\AUDIO"
        os.makedirs(self.output_dir, exist_ok=True)

    def describe_content(self):
        current_frame = self.video_handler.get_current_frame()
        if current_frame is not None:
            pil_image = Image.fromarray(cv2.cvtColor(current_frame, cv2.COLOR_BGR2RGB))
            img_byte_arr = io.BytesIO()
            pil_image.save(img_byte_arr, format='JPEG')
            blob = glm.Blob(
                mime_type='image/jpeg',
                data=img_byte_arr.getvalue()
            )
            user_request = self.user_input.get()
            
            # Retry mechanism
            for attempt in range(3):  # Retry up to 3 times
                try:
                    response = model.generate_content([user_request, blob], stream=True)
                    for chunk in response:
                        self.queue.put(chunk.text)
                        self.text_to_speech(chunk.text)
                    break
                except exceptions.GoogleAPICallError as e:  # Catch the correct exception
                    print(f"Attempt {attempt+1} failed: {e}")
                    time.sleep(2)  # Wait before retrying
                except exceptions.RetryError as e:
                    print(f"Retry attempt {attempt+1} failed: {e}")
                    time.sleep(2)
                except exceptions.InternalServerError as e:
                    print(f"Internal Server Error on attempt {attempt+1}: {e}")
                    time.sleep(2)

        else:
            self.queue.put("No frame available")

    def threaded_describe_content(self):
        describe_thread = threading.Thread(target=self.describe_content)
        describe_thread.start()

    def process_queue(self):
        if self.is_closing:
            return  # Exit if the app is closing
        try:
            while True:
                new_text = self.queue.get_nowait()
                current_text = self.message_var.get()
                updated_text = current_text + new_text + "\n"
                self.message_var.set(updated_text)
        except Empty:
            pass
        self.root.after(100, self.process_queue)  # Reschedule the method

    def text_to_speech(self, text):
        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16
        )

        # Split the text into smaller chunks if it's too long
        max_chars = 5000  # Define a max character limit per request
        text_chunks = [text[i:i + max_chars] for i in range(0, len(text), max_chars)]

        wav_files = []
        for i, chunk in enumerate(text_chunks):
            for attempt in range(3):  # Retry up to 3 times for each chunk
                try:
                    response = self.client.synthesize_speech(
                        input=texttospeech.SynthesisInput(text=chunk), 
                        voice=voice, 
                        audio_config=audio_config
                    )
                    wav_path = os.path.join(self.output_dir, f'output_{i}.wav')
                    with open(wav_path, 'wb') as out:
                        out.write(response.audio_content)
                    wav_files.append(wav_path)
                    break
                except exceptions.GoogleAPICallError as e:
                    print(f"Attempt {attempt+1} failed: {e}")
                    time.sleep(2)  # Wait before retrying
                except exceptions.RetryError as e:
                    print(f"Retry attempt {attempt+1} failed: {e}")
                    time.sleep(2)
                except exceptions.InternalServerError as e:
                    print(f"Internal Server Error on attempt {attempt+1}: {e}")
                    time.sleep(2)

        # Play the concatenated audio
        self.play_audio_files(wav_files)

    def play_audio_files(self, wav_files):
        for wav_path in wav_files:
            chunk = 1024
            wf = wave.open(wav_path, 'rb')
            p = pyaudio.PyAudio()
            stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                            channels=wf.getnchannels(),
                            rate=wf.getframerate(),
                            output=True)
            data = wf.readframes(chunk)
            while data:
                stream.write(data)
                data = wf.readframes(chunk)
            stream.stop_stream()
            stream.close()
            p.terminate()

    def on_closing(self):
        self.is_closing = True  # Set the flag to stop the after loop
        self.root.destroy()

# Ensure to install necessary libraries:
# pip install google-cloud-texttospeech pyaudio
