from rest_framework import serializers
from .models import Transcription


class TranscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transcription
        fields = "__all__"


class AudioUploadSerializer(serializers.Serializer):
    audio_files = serializers.FileField()
