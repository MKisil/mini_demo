# views.py
import google.cloud.speech as speech
import google.generativeai as genai
from django.core.files.storage import default_storage
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from config import settings
from .models import Transcription
from .serializers import TranscriptionSerializer, AudioUploadSerializer

genai.configure(api_key="YOUR_GEMINI_API_KEY")


class AudioAnalyzeAPIView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = AudioUploadSerializer

    def post(self, request, *args, **kwargs):
        if "audio_files" not in request.FILES:
            return Response({"error": "No audio file provided"}, status=status.HTTP_400_BAD_REQUEST)

        audio_files = request.FILES.getlist("audio_files")
        results = []

        for audio_file in audio_files:
            file_path = default_storage.save(f"temp/{audio_file.name}", audio_file)

            transcript = self.transcribe_audio(file_path)
            if not transcript:
                return Response({"error": "Failed to transcribe"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            gemini_response = self.get_gemini_response(transcript)

            transcription_obj = Transcription.objects.create(
                audio_file=audio_file, transcript=transcript, gemini_response=gemini_response
            )

            results.append(TranscriptionSerializer(transcription_obj).data)

            default_storage.delete(file_path)

        return Response({"results": results}, status=status.HTTP_201_CREATED)

    def transcribe_audio(self, file_path):
        client = speech.SpeechClient.from_service_account_file(settings.GOOGLE_CREDENTIALS_PATH)

        with open(file_path, "rb") as audio_file:
            audio_content = audio_file.read()

        audio = speech.RecognitionAudio(content=audio_content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="uk-UA",
        )

        response = client.recognize(config=config, audio=audio)

        return " ".join(
            [result.alternatives[0].transcript for result in
             response.results]) if response.results else 'No transcription'

    def get_gemini_response(self, transcript):
        with open(settings.GEMINI_PROMPT, "r", encoding="utf-8") as file:
            prompt_text = file.read().strip()

        full_prompt = f"{prompt_text}: {transcript}"

        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(full_prompt)

        return response.text if response else "No response from Gemini"
