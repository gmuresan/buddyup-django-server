from django.db import models
from userprofile.models import UserProfile, Group
from django.contrib.gis.db import models as geomodels


class Status(models.Model):
    user = models.ForeignKey(UserProfile, related_name='statuses')
    date = models.DateTimeField(auto_now=True, db_index=True)
    expires = models.DateTimeField(db_index=True)
    text = models.CharField(max_length=100, db_index=True)

    location = models.ForeignKey('Location', related_name='statuses', null=True, blank=True)
    groups = models.ManyToManyField(Group, related_name='receivedStatuses', null=True, blank=True)


class Location(geomodels.Model):
    lat = geomodels.FloatField()
    lng = geomodels.FloatField()
    point = geomodels.PointField(srid=4326, geography=True)
    objects = geomodels.GeoManager()

    address = geomodels.CharField(max_length=40, db_index=True, null=True, blank=True)
    city = geomodels.CharField(max_length=30, db_index=True, null=True, blank=True)
    state = models.CharField(max_length=2, db_index=True, null=True, blank=True)

    class Meta:
        index_together = [
            ["address", "city", "state"],
            ["city", "state"]
        ]


class Poke(models.Model):
    sender = models.ForeignKey(UserProfile, related_name='sentPokes')
    recipient = models.ForeignKey(UserProfile, related_name='receivedPokes')
    created = models.DateTimeField(auto_now_add=True)

