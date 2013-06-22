from django.db import models
from userprofile.models import UserProfile


class Conversation(models.Model):
    members = models.ManyToManyField(UserProfile, related_name='conversations')
    created = models.DateTimeField(auto_now_add=True)
    lastActivity = models.DateTimeField(auto_now=True)


class Message(models.Model):
    user = models.ForeignKey(UserProfile, related_name='messages')
    conversation = models.ForeignKey(Conversation, related_name='messages')
    created = models.DateTimeField(auto_now_add=True)
    text = models.TextField()

