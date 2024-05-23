import sounddevice as sd
from scipy.io.wavfile import write
from gpiozero import Button
import numpy as np
import requests
from openai import OpenAI
client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])
import os
from supabase import create_client, Client
import pygame
import random
import resend
from groq import Groq
import webrtcvad
import collections
import pyaudio
import wave
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
import time
RELAY_PIN = 18
BUTTON_PIN = 17

button = Button(BUTTON_PIN)

audios_path = os.environ['AUDIOS_PATH']

# Set up the relay pin as an output
GPIO.setup(RELAY_PIN, GPIO.OUT)

# Initially, make sure the relay is off
GPIO.output(RELAY_PIN, GPIO.LOW)
print("Initial State: Relay On (Locked)")

is_locked = False

def lock():
    global is_locked
    GPIO.output(RELAY_PIN, GPIO.LOW)  # Activate relay
    is_locked = True
    print("Locked: GPIO LOW")

# Function to unlock
def unlock():
    global is_locked
    GPIO.output(RELAY_PIN, GPIO.HIGH)  # Deactivate relay
    is_locked = False
    print("Unlocked: GPIO HIGH")


def unlock_timed(seconds):
    global is_locked
    unlock()  # Unlock the relay
    time.sleep(seconds)  # Wait for 5 seconds
    lock()  # Lock the relay again

# Example usage:
# unlock_for_5_seconds()


supabase: Client = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])

groq_key = os.environ['GROQ_KEY']
groq_client = Groq(
    api_key=groq_key,
)
resend.api_key = os.environ['RESEND_API_KEY']

def send_email(email, subject="Email from Heisenburgers", text='This is an email from the Heisenburgers residence.'):
    r = resend.Emails.send({
    "sender": "Heisenburgers<hello@email.bestphysicsproject.com>",
    "to": email,
    "subject": subject,
    "html": f"<p>{text}</p>"
    })   
    return r

def speech_to_text0(audio_path):
    # Replace this with your actual STT API call
    url = "https://api.example.com/speech_to_text"
    headers = {"Authorization": "Bearer YOUR_API_KEY"}
    files = {'audio': open(audio_path, 'rb')}
    response = requests.post(url, headers=headers, files=files)
    return response.json()['text']

def text_to_speech(text, file_name):
    CHUNK_SIZE = 1024
    url = "https://api.elevenlabs.io/v1/text-to-speech/K7EbQLShXFqtGVmmpB4R"

    headers = {
    "Accept": "audio/mpeg",
    "Content-Type": "application/json",
    "xi-api-key": os.environ['ELEVENLABS_API_KEY']
    }

    data = {
    "text": text,
    "model_id": "eleven_monolingual_v1",
    "voice_settings": {
        "stability": 0.5,
        "similarity_boost": 0.5
    }
    }

    response = requests.post(url, json=data, headers=headers)
    with open(f"{file_name}.mp3", 'wb') as f:
        for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
            if chunk:
                f.write(chunk)

def play_audio(audio_path):
    pygame.mixer.init()
    pygame.mixer.music.load(audio_path)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():  # wait for the music to finish playing
        pygame.time.Clock().tick(10)

def classify_intent(text):
    # Replace this with your actual classification API call
    chat_completion = groq_client.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": text,
        },
        {
            "role": "system",
            "content": "There is someone ringing a residnce doorbell. You have to classify their intent. Classify as enter (if they are a guest, cleaner, gardener, security, other staff), deliver (if it is a delivery) or message (if the person wants to leave a message). Response with only a single word in lowercase with no spaces(enter, deliver, message).",
        }
    ],
    model="llama3-70b-8192",
)

    return chat_completion.choices[0].message.content

def get_correct_passcode(id):
    response = supabase.table('people').select("*").eq('id', id).single().execute()
    return response.data['passcode']

def get_temp_code(id):
    response = supabase.table('people').select("*").eq('id', id).single().execute()
    return response.data['temp_code']

def get_security_method(id):
    response = supabase.table('people').select("*").eq('id', id).single().execute()
    return response.data['security_method']

def get_person_information(id):
    response = supabase.table('people').select("*").eq('id', id).single().execute()
    return response.data['name'], response.data['email'], response.data['role'], response.data['security_method'], response.data['passcode']

def send_one_time_code(email, id):
    code = generate_onetime_code()
    #response = supabase.table('people').select('email').eq('id', id).single().execute()
    supabase.table('people').update({"temp_code": code}).eq('id', id).execute()
    #email = response.data['email']
    send_email(email=email, subject="Heisenburgers One-Time Code", text=f"Your one-time code is {code}")

def generate_onetime_code():
    return ''.join([str(random.randint(0, 9)) for _ in range(6)])

def validate_phrase(input_phrase, correct_phrase='I like pineapple'):
    # Implement code validation logic here
    if input_phrase.lower().strip() == correct_phrase.lower().strip():
        return True
    else:
        return False

def validate_code(input_code, correct_code=1234):
    # Ensure both input_code and correct_code are integers
    try:
        input_code = int(input_code)
        correct_code = int(correct_code)
    except ValueError:
        return False

    # Implement code validation logic here
    if input_code == correct_code:
        return True
    else:
        return False

def send_notification(title, description=None, type='entry'):
    # Implement notification logic here
    supabase.table('notifications').insert({"title": title, "description": description, "type": type}).execute()

def notify_message(name, message_title, message_content):
        supabase.table('notifications').insert({"title": f"Message from {name}", "description": "Click to view.", "type": 'message', "message_title": message_title, "message_content": message_content, "message_sender": name }).execute()

def ask_groq(system='', prompt='', model='llama3-8b-8192'):
    # Replace this with your actual classification API call
    chat_completion = groq_client.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": prompt,
        },
        {
            "role": "system",
            "content": system,
        }
    ],
    max_tokens=2000,
    model=model,
)

    return chat_completion.choices[0].message.content


# Parameters
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
FRAME_DURATION_MS = 30  # Duration of a frame in milliseconds
FRAMES_PER_BUFFER = int(RATE * FRAME_DURATION_MS / 1000)
VAD_MODE = 2  # Aggressiveness mode of the VAD (0-3)
SILENCE_LIMIT = 80  # Number of silent frames to keep recording after silence is detected

# Voice Activity Detector
vad = webrtcvad.Vad(VAD_MODE)

def is_speech(frame, vad):
    return vad.is_speech(frame, RATE)

def record_audio(filename, duration=10):
    # Audio Stream
    audio = pyaudio.PyAudio()
    stream = audio.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=FRAMES_PER_BUFFER)
    #print("Recording...")

    frames = []
    ring_buffer = collections.deque(maxlen=SILENCE_LIMIT)
    silent_frames = 0
    recording = False
    start_time = time.time()

    while True:
        frame = stream.read(FRAMES_PER_BUFFER)
        is_speaking = is_speech(frame, vad)

        if is_speaking:
            if not recording:
                recording = True
                #print("Start speaking detected.")
            frames.append(frame)
            silent_frames = 0
        else:
            if recording:
                ring_buffer.append(frame)
                silent_frames += 1
                if silent_frames >= SILENCE_LIMIT:
                    #print("Silence detected, stopping recording.")
                    frames.extend(ring_buffer)
                    break
            else:
                ring_buffer.clear()

        # Check if the duration limit has been reached
        if duration and (time.time() - start_time) >= duration:
            if recording:
                frames.extend(ring_buffer)
            break

    #print("Recording stopped.")
    stream.stop_stream()
    stream.close()
    audio.terminate()

    # Save the recorded frames as a .wav file
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(audio.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))

    #print(f"Audio saved as {filename}")
    return filename

# Function to send audio to the API
def speech_to_text(file):
    #print("Sending to API...")
    audio_file = open(file, 'rb')
    transcription = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
    #print(transcription.text)
    return transcription.text

def ring_doorbell_sound():
    play_audio(audios_path + "doorbell.mp3")


# Main function to run the program
def main():
    button.wait_for_press()
    ring_doorbell_sound()
    play_audio(audios_path + "welcome.mp3")
    print("Welcome to our residence. How may I help you?")
    audio_filename = 'intent.wav'
    audio = record_audio(audio_filename)  # Added 'output.wav' as filename
    print("Transcribing")
    transcription = speech_to_text(audio)
    #print(transcription)
    print("Classifying intent")
    intent = classify_intent(transcription)
    print(f"Intent: {intent}")
    os.remove(audio_filename)  # Delete the file after transcription
    if (intent == 'enter'):
        play_audio(audios_path + "ask_id.mp3")
        print("Could you please provide your id which was communicated to you?")
        audio_filename = 'id.wav'
        audio = record_audio(audio_filename)  # Added 'output.wav' as filename
        print("Transcribing")
        transcription = speech_to_text(audio)
        print("Extracting id")
        id = int(ask_groq("Extract the id from the user message and only output the id in numbers and nothing else.", transcription))
        print(f"ID: {id}")
        os.remove(audio_filename)  # Delete the file after transcription
        name, email, role, security_method, passcode = get_person_information(id)
        if (security_method == 'passcode'):
            play_audio(audios_path + "ask_passcode.mp3")
            print(f'Hi, {name}. Please provide your passcode.')
            audio_filename = 'passphrase.wav'
            audio = record_audio(audio_filename)  # Added 'output.wav' as filename
            print("Transcribing")
            transcription = speech_to_text(audio)
            os.remove(audio_filename)  # Delete the file after transcription
            print("Extracting passcode")
            guest_code = int(ask_groq("Extract the passcode provided by the user. Only output the passcode in integers and nothing else. No spaces. Just the number as a signle number.", transcription))
            print(f"Code: {guest_code}")
            if validate_code(guest_code, passcode):
                play_audio(audios_path + "all_good_welcome.mp3")
                unlock_timed(2)
                print(f'Welcome, {name}.')
                send_notification(title=f"{name} entered the house")
            else:
                play_audio(audios_path + "deny_entrance.mp3")
                print(f'Sorry, {name}. We could not validate the passcode and cannot let you in.')
                send_notification(title=f"{name} failed to enter the house")

        if (security_method == 'one-time'):
            send_one_time_code(email, id)
            temp_code = get_temp_code(id)
            play_audio(audios_path + "ask_one_time_code.mp3")
            print(f'Could you please provide the one-time code sent to your email, {name}. Press the button once you have it.')
            button.wait_for_press()
            #print(f'You have been sent a code to your email at {email}. Please provide it.')
            play_audio(audios_path + "provide_one_time_code.mp3")
            print(f'You have been sent a code to your email at {email}. Please provide it.')
            audio_filename = 'code.wav'
            audio = record_audio(audio_filename)  # Added 'output.wav' as filename
            print("Transcribing")
            transcription = speech_to_text(audio)
            os.remove(audio_filename)  # Delete the file after transcription
            print("Extracting code")
            guest_code = int(ask_groq("Extract the passcode provided by the user. Only output the passcode in integers and nothing else. No spaces. Just the number as a signle number.", transcription))
            print(f"Code: {guest_code}")
            if validate_code(guest_code, temp_code):
                play_audio(audios_path + "all_good_welcome.mp3")
                unlock_timed(2)
                print(f'Welcome, {name}.')
                send_notification(title=f"{name} entered the house",)


            else:
                play_audio(audios_path + "deny_entrance.mp3")
                print(f'Sorry, {name}. We could not validate the one-time code and cannot let you in.')
                send_notification(title=f"{name} failed to enter the house")
    if (intent == 'deliver'):
        play_audio(audios_path + "delivery_what_where.mp3")
        print("What are you delivering and from where?")
        audio_filename = 'delivery.wav'
        audio = record_audio(audio_filename)  # Added 'output.wav' as filename
        print("Transcribing")
        transcription = speech_to_text(audio)
        os.remove(audio_filename)  # Delete the file after transcription
        print("Extracting delivery")
        delivery_extract = ask_groq("There is a delivery at the residence door. Summarize the delivery, indicating what was delivered and from where. Only output the summary and nothing else. Example: An aquarium was delivered from Amazon.", transcription)
        play_audio(audios_path + "delivery_instructions.mp3")
        print("Thank you. I have notified the owner.")
        send_notification(title=f"Delivery", description=f"{delivery_extract}", type="delivery")
    if (intent == 'message'):
        play_audio(audios_path + "ask_name_message.mp3")
        print("Please indicate your name and your message.")
        audio_filename = 'message.wav'
        audio = record_audio(audio_filename)  # Added 'output.wav' as filename
        print("Transcribing")
        transcription = speech_to_text(audio)
        os.remove(audio_filename)  # Delete the file after transcription
        print("Extracting message")
        message_extract = ask_groq("The user left us a message at the door. Extract 1. Their name, 2. a fitting title that summarizes their message, and 3. their message. Output 1.their name, 2. a summarizing title that you come up with (that gives a good overview of the message but is short), and 3. the message, separated by only a hyphen(-) (no space). Only output those values. Nothing more. Example: John-Grocery Trip-I want to go to the store and buy groceries. Don't put a hyphen before, after or anywhere else in the output. Only in between the name, title and message.", transcription, model="llama3-70b-8192")
        print(message_extract)
        name, title, message = message_extract.split('-')
        play_audio(audios_path + "pass_message.mp3")
        notify_message(name, title, message)
if __name__ == "__main__":
    print("Press the button to ring the bell.")
    while True:
        main()

