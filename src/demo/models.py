from django.db import models


class Transcription(models.Model):
    audio_file = models.FileField(upload_to="audio_files/")
    transcript = models.TextField()
    gemini_response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Transcription {self.id}"
