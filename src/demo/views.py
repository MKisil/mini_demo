from django.core.files.storage import default_storage
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from config import settings
from . import services
from .models import Transcription
from .serializers import TranscriptionSerializer, AudioUploadSerializer


class AudioAnalyzeAPIView(APIView):
    serializer_class = AudioUploadSerializer

    def post(self, request, *args, **kwargs):
        if "audio_files" not in request.FILES:
            return Response({"error": "No audio file provided"}, status=status.HTTP_400_BAD_REQUEST)

        audio_files = request.FILES.getlist("audio_files")
        results = []

        for audio_file in audio_files:
            file_path = settings.MEDIA_ROOT + default_storage.save(f"temp/{audio_file.name}", audio_file)

            transcript = services.transcribe_audio(file_path)

            if transcript:
                gemini_response = services.get_gemini_response(transcript)

                transcription_obj = Transcription.objects.create(
                    audio_file=audio_file, transcript=transcript, gemini_response=gemini_response
                )
            else:
                transcription_obj = Transcription.objects.create(
                    audio_file=audio_file, transcript='No transcription', gemini_response='No response from gemini'
                )

            results.append(TranscriptionSerializer(transcription_obj).data)

            default_storage.delete(file_path)

        return Response({"results": results}, status=status.HTTP_201_CREATED)
