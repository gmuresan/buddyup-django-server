from django.db import models
from userprofile.models import UserProfile


class Conversation(models.Model):

    def __str__(self):
        membersString = ''

        for member in self.members.all():
            membersString += member.user.username + ", "

        return "chat between " + membersString

    members = models.ManyToManyField(UserProfile, related_name='conversations')
    created = models.DateTimeField(auto_now_add=True)
    lastActivity = models.DateTimeField(auto_now=True)


class Message(models.Model):

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return self.text

    user = models.ForeignKey(UserProfile, related_name='messages')
    conversation = models.ForeignKey(Conversation, related_name='messages')
    created = models.DateTimeField(auto_now_add=True)
    text = models.TextField()

