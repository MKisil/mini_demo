import uuid
import wave
import io
import re

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from google.cloud import speech
import google.generativeai as genai
from pydub import AudioSegment

from config import settings

speech_client = speech.SpeechClient.from_service_account_file(settings.GOOGLE_CREDENTIALS_PATH)


def prepare_text(text, symbols):
    for symbol in symbols:
        text = re.sub(f"{re.escape(symbol)}+", "", text)
    return text


def convert_audio_to_mono(input_file):
    audio = AudioSegment.from_file(input_file)
    audio = audio.set_channels(1)

    buffer = io.BytesIO()
    audio.export(buffer, format="wav")

    file_path = f'temp/{uuid.uuid4()}.wav'
    saved_path = settings.MEDIA_ROOT + default_storage.save(file_path, ContentFile(buffer.getvalue()))

    return saved_path


def transcribe_audio(input_file):
    converted_audio_filepath = convert_audio_to_mono(input_file)

    with wave.open(converted_audio_filepath, 'rb') as wav_file:
        sample_rate = wav_file.getframerate()

    with open(converted_audio_filepath, "rb") as audio_file:
        content = audio_file.read()
        audio = speech.RecognitionAudio({'content': content})
        config = speech.RecognitionConfig(
            {
                'encoding': speech.RecognitionConfig.AudioEncoding.LINEAR16,
                'language_code': "uk-UA",
                'enable_automatic_punctuation': True,
                'sample_rate_hertz': sample_rate,
            }
        )

    response = speech_client.recognize(config=config, audio=audio)

    default_storage.delete(converted_audio_filepath)

    return " ".join(
        [result.alternatives[0].transcript for result in
         response.results]) if response.results else False


def get_gemini_response(transcript):
    with open(settings.GEMINI_PROMPT, "r", encoding="utf-8") as file:
        prompt_text = prepare_text(file.read(), ' -')

    full_prompt = f"{prompt_text}: {transcript}"

    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(full_prompt)

    return response.text if response else False
