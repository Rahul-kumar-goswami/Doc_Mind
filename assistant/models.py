from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_delete
from django.dispatch import receiver
import os

class Document(models.Model):
    file = models.FileField(upload_to='documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_processed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.file.name} (Uploaded at: {self.uploaded_at})"

@receiver(post_delete, sender=Document)
def delete_document_from_rag(sender, instance, **kwargs):
    from .rag_engine import rag_engine
    try:
        file_path = instance.file.path
        rag_engine.delete_document(file_path)
    except Exception as e:
        print(f"Error removing document {instance.file.name} from RAG: {e}")

class UserMemory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    key = models.CharField(max_length=100)
    value = models.TextField()

    class Meta:
        unique_together = ('user', 'key')

    def __str__(self):
        return f"{self.user.username} - {self.key}: {self.value}"

class ChatHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20) # 'user' or 'assistant'
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    session_id = models.CharField(max_length=100, null=True, blank=True)
    session_title = models.CharField(max_length=255, default="New Chat")

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.user.username} ({self.role}): {self.content[:30]}..."
    

    
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s profile"

class CustomUser(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=100)
    otp = models.CharField(max_length=6, blank=True, null=True)

    def __str__(self):
        return self.email