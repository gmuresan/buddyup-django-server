from datetime import datetime
from django.db import models
import pdb
from buddyup import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from userprofile.helpers import getUserProfileDetailsJson


class UserProfile(models.Model):
    def __str__(self):
        return self.user.username

    user = models.OneToOneField(User)
    facebookUID = models.CharField(max_length=64, db_index=True, blank=True, null=True)
    lastActivity = models.DateTimeField(auto_now=True)
    friends = models.ManyToManyField("self", related_name='myFriends', null=True, blank=True)
    blockedFriends = models.ManyToManyField("self", related_name="blocked", null=True, blank=True)
    device = models.CharField(max_length=10, default='ios')
    favoritesNotifications = models.BooleanField(default=True)

    def getUnblockedFriends(self):
        blocked = self.blockedFriends.values_list('pk', flat=True)
        return self.friends.exclude(pk__in=list(blocked))

    def getActiveStatuses(self):
        now = datetime.utcnow()
        return self.statuses.filter(expires__gt=now)

    @staticmethod
    def getCacheId(userId):
        return "user_" + str(userId)

    @staticmethod
    def getUser(userId):
        cacheKey= UserProfile.getCacheId(userId)
        user = cache.get(cacheKey)
        if user is None:
            user = UserProfile.objects.get(pk=userId)
            cache.set(cacheKey, user)
            return user
        return user

    @staticmethod
    def getMutualFriends(userId1, userId2):
        user1 = UserProfile.getUser(userId1)
        user2 = UserProfile.getUser(userId2)
        mutualFriends = UserProfile.objects.filter(friends=user1).filter(friends=user2)
        if(userId1 > userId2):
            key =  str(userId2) + '_' + str(userId1)
        else:
            key = str(userId1) + '_' + str(userId2)
        mutualFriendsList = cache.get(key)
        if mutualFriendsList is None:
            mutualFriendsList =  mutualFriends.all()

        mutualFriendsData = list()

        for mutualFriend in mutualFriendsList:
            mutualFriendData = getUserProfileDetailsJson(mutualFriend)
            mutualFriendsData.append(mutualFriendData)

        return mutualFriendsData


class FacebookUser(models.Model):
    facebookUID = models.CharField(max_length=64, db_index=True)

    def __str__(self):
        return self.facebookUID


class Group(models.Model):
    FAVORITES_GROUP_NAME = "Favorites"

    def __str__(self):
        return self.name + " - " + self.user.user.username

    name = models.CharField(max_length=64, db_index=True)
    members = models.ManyToManyField(UserProfile, related_name='groupsIn', blank=True, null=True)
    fbMembers = models.ManyToManyField(FacebookUser, related_name='groupsIn', blank=True, null=True)
    user = models.ForeignKey(UserProfile, related_name='groups')


class Feedback(models.Model):
    def __str__(self):
        return self.user.user.email + " - " + self.text

    user = models.ForeignKey(UserProfile, related_name='submittedFeedback')
    date = models.DateTimeField(auto_now_add=True)
    text = models.TextField()


class Setting(models.Model):
    user = models.ForeignKey(UserProfile, related_name='settings')
    key = models.CharField(max_length=20)
    value = models.CharField(max_length=255)







