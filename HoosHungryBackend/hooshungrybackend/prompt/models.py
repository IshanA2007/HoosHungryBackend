from django.db import models
from django.contrib.auth.models import User


class ChatSession(models.Model):
    """One chat session per user."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='chat_session')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s chat session"


class ChatMessage(models.Model):
    """Individual turns in the conversation."""
    ROLE_CHOICES = [('user', 'User'), ('assistant', 'Assistant')]

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    suggestions_json = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"[{self.role}] {self.content[:50]}"
