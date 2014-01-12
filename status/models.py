import pdb
import datetime
from django.db import models
from chat.models import Message
from userprofile.models import UserProfile, Group, FacebookUser
from django.contrib.gis.db import models as geomodels


class Status(geomodels.Model):
    VIS_PUBLIC = 'public'
    VIS_FRIENDS = 'friends'
    VIS_FRIENDS_OF_FRIENDS = 'friendsoffriends'
    VIS_CUSTOM = 'custom'

    STATUS_TYPES = (('food', 'food'), ('drink', 'drink'), ('study', 'study'), ('couch', 'couch'), ('go out', 'go out'),
                    ('show', 'show'), ('sports', 'sports'), ('other', 'other'))
    VISIBILITY = ((VIS_FRIENDS, 'friends'), (VIS_PUBLIC, 'public'), (VIS_FRIENDS_OF_FRIENDS, 'friends of friends'),
                  (VIS_CUSTOM, 'custom'))

    class Meta:
        ordering = ['-date']

    def __unicode__(self):
        username = self.user.user.username
        return "{0} - {1}".format(username, self.text)

    user = geomodels.ForeignKey(UserProfile, related_name='statuses')
    date = geomodels.DateTimeField(auto_now=True, db_index=True)
    expires = geomodels.DateTimeField(db_index=True, null=True, blank=True)
    starts = geomodels.DateTimeField(db_index=True, default=datetime.datetime.now)
    text = geomodels.CharField(max_length=100, db_index=True)
    attending = geomodels.ManyToManyField(UserProfile, related_name="statusesAttending")
    invited = geomodels.ManyToManyField(UserProfile, related_name="statusesInvited")
    statusType = geomodels.CharField(max_length=10, db_index=True, choices=STATUS_TYPES, default='other')
    visibility = geomodels.CharField(max_length=20, db_index=True, choices=VISIBILITY, default='friends')
    friendsVisible = geomodels.ManyToManyField(UserProfile, related_name='visibleStatuses')
    fbFriendsVisible = geomodels.ManyToManyField(FacebookUser, related_name='visibleStatuses')

    location = geomodels.ForeignKey('Location', related_name='statuses', null=True, blank=True)
    groups = geomodels.ManyToManyField(Group, related_name='receivedStatuses', null=True, blank=True)

    objects = geomodels.GeoManager()

    def getStatusAudienceUsers(self):
        if self.groups:
            users = UserProfile.objects.filter(groupsIn__in=self.groups.all())
            return users
        else:
            return self.user.friends.all()


class StatusMessage(geomodels.Model):
    class Meta:
        ordering = ['-date']

    user = geomodels.ForeignKey(UserProfile, related_name="statusMessages")
    date = geomodels.DateTimeField(auto_now_add=True, db_index=True)
    text = geomodels.TextField()
    status = geomodels.ForeignKey(Status, related_name="messages")


class Location(geomodels.Model):
    def __unicode__(self):
        unicode = "{0}, {1}".format(self.lat, self.lng)
        if self.venue:
            unicode += " {0}".format(self.venue)

        return unicode

    lat = geomodels.FloatField()
    lng = geomodels.FloatField()
    point = geomodels.PointField(srid=4326, geography=True)
    objects = geomodels.GeoManager()

    venue = geomodels.CharField(max_length=60, db_index=True, null=True, blank=True)
    address = geomodels.CharField(max_length=40, db_index=True, null=True, blank=True)
    city = geomodels.CharField(max_length=30, db_index=True, null=True, blank=True)
    state = geomodels.CharField(max_length=2, db_index=True, null=True, blank=True)

    class Meta:
        index_together = [
            ["address", "city", "state"],
            ["city", "state"]
        ]


class Poke(models.Model):
    class Meta:
        get_latest_by = "created"

    sender = models.ForeignKey(UserProfile, related_name='sentPokes')
    recipient = models.ForeignKey(UserProfile, related_name='receivedPokes')
    created = models.DateTimeField(auto_now_add=True)

