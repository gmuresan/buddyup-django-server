from datetime import datetime
import pdb
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.db.models import Q
from api.helpers import DATETIME_FORMAT
from status.models import Status
from userprofile.models import Setting, UserProfile

DEFAULT_STATUS_RADIUS = 50


def getNewStatusMessages(status, lastMessageId):
    messages = status.messages.all()
    if lastMessageId:
        messages = messages.filter(id__gt=lastMessageId)

    messagesJson = list()
    for message in messages:
        messageObj = dict()
        messageObj['id'] = message.id
        messageObj['userid'] = message.user.id
        messageObj['text'] = message.text
        messageObj['date'] = message.date.strftime(DATETIME_FORMAT)

        messagesJson.append(messageObj)

    return messagesJson


def getNewStatusesJsonResponse(userProfile, since, lat=None, lng=None, radius=None):
    friends = userProfile.getUnblockedFriends()
    friendsOfFriends = UserProfile.objects.filter(friends=friends).distinct().exclude(pk=userProfile.pk)
    now = datetime.utcnow()

    if not radius:
        try:
            radius = Setting.objects.get(user=userProfile, key='statusradius').value
        except Setting.DoesNotExist:
            radius = DEFAULT_STATUS_RADIUS

    inVisibleList = Q(friendsVisible=userProfile)
    friendsStatuses = Q(user__in=friends, visibility=Status.VIS_FRIENDS)
    friendsOfFriendsStatuses = Q(Q(user__in=friendsOfFriends) | Q(user__in=friends),
                                 visibility=Status.VIS_FRIENDS_OF_FRIENDS)
    visibilityQuery = inVisibleList | friendsStatuses | friendsOfFriendsStatuses

    if lat is not None and lng is not None:
        publicStatuses = Q(visibility=Status.VIS_PUBLIC)
        visibilityQuery = visibilityQuery | publicStatuses
        visibilityQuery = Q(visibilityQuery,
                            location__point__distance_lte=(Point(float(lng), float(lat)), D(mi=radius)))

    statuses = Status.objects.filter(visibilityQuery)
    statuses = statuses.filter(expires__gt=now)

    if since is not None:
        statuses = statuses.filter(date__gt=since)

    statuses = list(statuses)
    newSince = datetime.utcnow()

    statusesData = []
    for status in statuses:
        statusData = createStatusJsonObject(status)
        statusesData.append(statusData)

    return statusesData, newSince


def getMyStatusesJsonResponse(userProfile):
    myStatuses = userProfile.statuses.filter(user=userProfile).order_by('-expires')

    myStatusesData = []
    for status in myStatuses:
        statusData = createStatusJsonObject(status)
        myStatusesData.append(statusData)

    return myStatusesData


def createStatusJsonObject(status):
    statusData = dict()

    statusData['statusid'] = status.id
    statusData['userid'] = status.user_id
    statusData['text'] = status.text
    statusData['datecreated'] = status.date.strftime(DATETIME_FORMAT)
    statusData['dateexpires'] = status.expires.strftime(DATETIME_FORMAT)
    statusData['datestarts'] = status.starts.strftime(DATETIME_FORMAT)

    if status.location:
        location = dict()
        location['lat'] = status.location.lat
        location['lng'] = status.location.lng
        location['address'] = status.location.address
        location['city'] = status.location.city
        location['state'] = status.location.state
        location['venue'] = status.location.venue
        statusData['location'] = location

    return statusData
