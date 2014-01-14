from datetime import datetime
import pdb
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.db.models import Q
from api.helpers import DATETIME_FORMAT
from status.models import Status, Location
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
    friends = userProfile.friends.all()
    friendsOfFriends = UserProfile.objects.filter(friends=friends).distinct().exclude(pk=userProfile.pk)
    now = datetime.utcnow()

    if not radius:
        try:
            radius = Setting.objects.get(user=userProfile, key='statusradius').value
        except Setting.DoesNotExist:
            radius = DEFAULT_STATUS_RADIUS

    inVisibleList = Status.objects.filter(Q(friendsVisible=userProfile))
    friendsStatuses = Status.objects.filter(Q(user__in=friends, visibility=Status.VIS_FRIENDS))
    friendsOfFriendsStatuses = Status.objects.filter(Q(Q(user__in=friendsOfFriends) | Q(user__in=friends),
                                 visibility=Status.VIS_FRIENDS_OF_FRIENDS))
    #visibilityQuery = inVisibleList | friendsStatuses | friendsOfFriendsStatuses

    statuses = inVisibleList | friendsOfFriendsStatuses | friendsStatuses

    if lat is not None and lng is not None:
        publicStatuses = Status.objects.filter(Q(visibility=Status.VIS_PUBLIC))
        test = list(publicStatuses)
        statuses = statuses | publicStatuses
        #visibilityQuery = visibilityQuery | publicStatuses
        #visibilityQuery = Q(visibilityQuery,
       #                     location__point__distance_lte=(Point(float(lng), float(lat)), D(mi=radius)))

    test = list(inVisibleList)
    test = list(friendsStatuses)
    test = list(friendsOfFriendsStatuses)


    #statuses = Status.objects.filter(visibilityQuery)
    statuses = statuses.filter(expires__gt=now)
    test = list(statuses)

    if since is not None:
        statuses = statuses.filter(date__gt=since)

    if lat is not None and lng is not None:
        statuses = statuses.filter(location__point__distance_lte=(Point(float(lng), float(lat)), D(mi=radius)))
        test = list(statuses)

    test = list(statuses)

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
        statusData['location'] = createLocationJson(status.location)

    return statusData


def createLocationJson(locationObj):
    location = dict()
    location['lat'] = locationObj.lat
    location['lng'] = locationObj.lng
    location['address'] = locationObj.address
    location['city'] = locationObj.city
    location['state'] = locationObj.state
    location['venue'] = locationObj.venue

    return location



def getLocationObjectFromJson(locationData):
    lat = locationData.get('lat', None)
    lng = locationData.get('lng', None)
    address = locationData.get('address', None)
    city = locationData.get('city', None)
    state = locationData.get('state', None)
    venue = locationData.get('venue', None)

    try:
        location = Location.objects.get(lat=lat, lng=lng, address=address, city=city, state=state, venue=venue)
    except Location.DoesNotExist:
        point = Point(lng, lat)
        location = Location.objects.create(lat=lat, lng=lng, address=address, city=city, state=state, venue=venue,
                                           point=point)
        location.save()

    return location


def createTimeSuggestionJson(timeSuggestion):
    sugg = dict()
    sugg['userid'] = timeSuggestion.user.id
    sugg['time'] = timeSuggestion.dateSuggested.strftime(DATETIME_FORMAT)

    return sugg


def createLocationSuggestionJson(locSugg):
    sugg = dict()
    sugg['userid'] = locSugg.user.id
    sugg['location'] = createLocationJson(locSugg.location)

    return sugg