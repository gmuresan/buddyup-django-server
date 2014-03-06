import pdb
import datetime
from django.db import models
from django.utils.encoding import smart_str
from chat.models import Message
from userprofile.models import UserProfile, Group, FacebookUser
from django.contrib.gis.db import models as geomodels


class Status(geomodels.Model):
    VIS_PUBLIC = 'public'
    VIS_FRIENDS = 'friends'
    VIS_FRIENDS_OF_FRIENDS = 'friendsoffriends'
    VIS_CUSTOM = 'custom'

    STATUS_TYPES = (('food', 'food'), ('study', 'study'), ('couch', 'couch'), ('go out', 'go out'),
                    ('show', 'show'), ('sports', 'sports'), ('other', 'other'))
    VISIBILITY = ((VIS_FRIENDS, 'friends'), (VIS_PUBLIC, 'public'), (VIS_FRIENDS_OF_FRIENDS, 'friends of friends'),
                  (VIS_CUSTOM, 'custom'))

    class Meta:
        ordering = ['-date']

    def __unicode__(self):
        username = self.user.user.username
        return "{0} - {1}".format(username, unicode(self.text))

    user = geomodels.ForeignKey(UserProfile, related_name='statuses')
    date = geomodels.DateTimeField(auto_now=True, db_index=True)
    expires = geomodels.DateTimeField(db_index=True, null=True, blank=True)
    starts = geomodels.DateTimeField(db_index=True, default=datetime.datetime.now)
    text = geomodels.CharField(max_length=100, db_index=True)
    attending = geomodels.ManyToManyField(UserProfile, related_name="statusesAttending", null=True, blank=True)
    invited = geomodels.ManyToManyField(UserProfile, related_name="statusesInvited", null=True, blank=True)
    statusType = geomodels.CharField(max_length=10, db_index=True, choices=STATUS_TYPES, default='other', null=True,
                                     blank=True)
    visibility = geomodels.CharField(max_length=20, db_index=True, choices=VISIBILITY, default='friends', null=True,
                                     blank=True)
    imageUrl = geomodels.URLField(null=True, blank=True)

    friendsVisible = geomodels.ManyToManyField(UserProfile, related_name='statusesVisible', null=True, blank=True)
    fbFriendsVisible = geomodels.ManyToManyField(FacebookUser, related_name='statusesVisible', null=True, blank=True)
    invited = geomodels.ManyToManyField(UserProfile, related_name='statusesInvited', null=True, blank=True)
    fbInvited = geomodels.ManyToManyField(FacebookUser, related_name='statusesInvited', null=True, blank=True)
    attending = geomodels.ManyToManyField(UserProfile, related_name='statusesAttending', null=True, blank=True)
    fbAttending = geomodels.ManyToManyField(FacebookUser, related_name='statusesAttending', null=True, blank=True)

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
        unicode = u"{0}, {1}".format(self.lat, self.lng)
        if self.venue:
            unicode += u" {0}".format(self.venue)

        s = smart_str(unicode)

        return s

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


class LocationSuggestion(models.Model):
    class Meta:
        ordering = ['-dateCreated']

    status = models.ForeignKey(Status, related_name="locationSuggestions")
    user = models.ForeignKey(UserProfile, related_name="locationSuggestions")
    dateCreated = models.DateTimeField(auto_now_add=True)
    location = models.ForeignKey(Location)


class TimeSuggestion(models.Model):
    class Meta:
        ordering = ['-dateCreated']

    status = models.ForeignKey(Status, related_name="timeSuggestions")
    user = models.ForeignKey(UserProfile, related_name="timeSuggestions")
    dateCreated = models.DateTimeField(auto_now_add=True)
    dateSuggested = models.DateTimeField()


class Poke(models.Model):
    class Meta:
        get_latest_by = "created"

    sender = models.ForeignKey(UserProfile, related_name='sentPokes')
    recipient = models.ForeignKey(UserProfile, related_name='receivedPokes')
    created = models.DateTimeField(auto_now_add=True)

