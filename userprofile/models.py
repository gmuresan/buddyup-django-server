from django.db import models
from buddyup import settings
from django.contrib.auth.models import User


class UserProfile(models.Model):
    def __unicode__(self):
        return self.user.username

    user = models.OneToOneField(User)
    facebookUID = models.CharField(max_length=64, db_index=True, blank=True, null=True)
    lastActivity = models.DateTimeField(auto_now=True)
    friends = models.ManyToManyField("self", related_name='myFriends', null=True, blank=True)
    blockedFriends = models.ManyToManyField("self", related_name="blocked", null=True, blank=True)
    device = models.CharField(max_length=10, default='ios')

    def getUnblockedFriends(self):
        blocked = self.blockedFriends.values_list('pk', flat=True)
        return self.friends.exclude(pk__in=list(blocked))


class Group(models.Model):
    name = models.CharField(max_length=64, db_index=True)
    members = models.ManyToManyField(UserProfile, related_name='groupsIn')
    user = models.ForeignKey(UserProfile, related_name='groups')


class Feedback(models.Model):
    user = models.ForeignKey(UserProfile, related_name='submittedFeedback')
    date = models.DateTimeField(auto_now_add=True)
    text = models.TextField()

