from datetime import datetime
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

    def getActiveStatuses(self):
        now = datetime.utcnow()
        return self.statuses.filter(expires__gt=now)


class FacebookUser(models.Model):
    facebookUID = models.CharField(max_length=64, db_index=True)

    def __unicode__(self):
        return self.facebookUID


class Group(models.Model):
    def __unicode__(self):
        return self.name + " - " + self.user.user.username

    name = models.CharField(max_length=64, db_index=True)
    members = models.ManyToManyField(UserProfile, related_name='groupsIn', blank=True, null=True)
    fbMembers = models.ManyToManyField(FacebookUser, related_name='groupsIn', blank=True, null=True)
    user = models.ForeignKey(UserProfile, related_name='groups')


class Feedback(models.Model):
    def __unicode__(self):
        return self.user.user.email + " - " + self.text

    user = models.ForeignKey(UserProfile, related_name='submittedFeedback')
    date = models.DateTimeField(auto_now_add=True)
    text = models.TextField()


class Setting(models.Model):
    user = models.ForeignKey(UserProfile, related_name='settings')
    key = models.CharField(max_length=20)
    value = models.CharField(max_length=255)







