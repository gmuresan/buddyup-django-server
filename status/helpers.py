from datetime import datetime
from itertools import chain
import pdb
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.db.models import Q
from api.helpers import DATETIME_FORMAT
from status.models import Status, Location
from userprofile.helpers import getUserProfileDetailsJson
from userprofile.models import Setting, UserProfile

DEFAULT_STATUS_RADIUS = 50


def getNewStatusMessages(status, lastMessageId):
    messages = status.messages.all()
    if lastMessageId:
        messages = messages.filter(id__gt=lastMessageId)

    messagesJson = list()
    for message in messages:
        messageObj = dict()
        messageObj['messageid'] = message.id
        messageObj['userid'] = message.user.id
        messageObj['text'] = message.text
        messageObj['date'] = message.date.strftime(DATETIME_FORMAT)

        messagesJson.append(messageObj)

    return messagesJson


def getNewStatusesJsonResponse(userProfile, since, lat=None, lng=None, radius=None):
    friends = userProfile.friends.all()
    friendsOfFriends = UserProfile.objects.filter(friends__in=friends).exclude(pk=userProfile.pk).distinct()

    friendsOfFriends = list(chain(friendsOfFriends, friends))
    now = datetime.utcnow()

    if not radius:
        try:
            radius = Setting.objects.get(user=userProfile, key='statusradius').value
        except Setting.DoesNotExist:
            radius = DEFAULT_STATUS_RADIUS

    inVisibleList = Status.objects.filter(Q(friendsVisible=userProfile))
    friendsStatuses = Status.objects.filter(Q(user__in=friends, visibility=Status.VIS_FRIENDS))
    friendsOfFriendsStatuses = Status.objects.filter(
        Q(user__in=friendsOfFriends, visibility=Status.VIS_FRIENDS_OF_FRIENDS))
    invitedStatuses = Status.objects.filter(invited=userProfile)

    publicStatuses = None
    if lat is not None and lng is not None:
        distanceQuery = Q(location__point__distance_lte=(Point(float(lng), float(lat)), D(mi=radius)))
        publicStatuses = Status.objects.filter(Q(visibility=Status.VIS_PUBLIC))
        publicStatuses = publicStatuses.filter(distanceQuery)
        publicStatuses = publicStatuses.filter(expires__gt=now)
        if since is not None:
            publicStatuses = publicStatuses.filter(date__gt=since)

        publicStatuses = list(publicStatuses)

        inVisibleList = inVisibleList.filter(distanceQuery)
        friendsStatuses = friendsStatuses.filter(distanceQuery)
        friendsOfFriendsStatuses = friendsOfFriendsStatuses.filter(distanceQuery)

    inVisibleList = inVisibleList.filter(expires__gt=now)
    friendsStatuses = friendsStatuses.filter(expires__gt=now)
    friendsOfFriendsStatuses = friendsOfFriendsStatuses.filter(expires__gt=now)
    invitedStatuses = invitedStatuses.filter(expires__gt=now)

    if since is not None:
        inVisibleList = inVisibleList.filter(date__gt=since)
        friendsStatuses = friendsStatuses.filter(date__gt=since)
        friendsOfFriendsStatuses = friendsOfFriendsStatuses.filter(date__gt=since)
        invitedStatuses = invitedStatuses.filter(date__gt=since)

    inVisibleList = list(inVisibleList)
    friendsStatuses = list(friendsStatuses)
    friendsOfFriendsStatuses = list(friendsOfFriendsStatuses)
    invitedStatuses = list(invitedStatuses)

    if publicStatuses:
        statuses = set(inVisibleList + friendsStatuses + friendsOfFriendsStatuses + publicStatuses + invitedStatuses)
    else:
        statuses = set(inVisibleList + friendsStatuses + friendsOfFriendsStatuses + invitedStatuses)

    statuses = list(statuses)
    newSince = datetime.utcnow()

    statusesData = []
    for status in statuses:
        statusData = createStatusJsonObject(status)
        statusesData.append(statusData)

    return statusesData, newSince


def getMyStatusesJsonResponse(userProfile):
    myStatuses = userProfile.statuses.filter(user=userProfile, deleted=False).order_by('-expires')

    myStatusesData = []
    for status in myStatuses:
        statusData = createStatusJsonObject(status)
        myStatusesData.append(statusData)

    return myStatusesData


def createStatusJsonObject(status):
    statusData = dict()

    statusData['statusid'] = status.id
    statusData['userid'] = status.user_id
    statusData['userinfo'] = getUserProfileDetailsJson(status.user)
    statusData['text'] = status.text
    statusData['datecreated'] = status.dateCreated.strftime(DATETIME_FORMAT)
    statusData['dateexpires'] = status.expires.strftime(DATETIME_FORMAT)
    statusData['datestarts'] = status.starts.strftime(DATETIME_FORMAT)
    statusData['type'] = status.statusType
    statusData['deleted'] = status.deleted

    attending, invited, userDetails = createAttendingAndInvitedAndUserDetailsJsonResponse(status)
    statusData['invited'] = invited
    statusData['attending'] = attending
    statusData['users'] = userDetails

    if status.imageUrl:
        statusData['imageurl'] = status.imageUrl

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


def createAttendingAndInvitedAndUserDetailsJsonResponse(status):
    attending = status.attending.all()
    invited = status.invited.all()

    userDetails = list()
    for user in attending:
        userInfo = getUserProfileDetailsJson(user)
        userDetails.append(userInfo)

    for user in invited:
        if user not in attending:
            userInfo = getUserProfileDetailsJson(user)
            userDetails.append(userInfo)

    attending = list(attending.values_list('id', flat=True))
    invited = list(invited.values_list('id', flat=True))
    fbAttending = list(status.fbAttending.values_list('facebookUID', flat=True))
    fbInvited = list(status.fbInvited.values_list('facebookUID', flat=True))

    for fbId in fbAttending:
        attending.append("fb" + fbId)

    for fbId in fbInvited:
        invited.append("fb" + fbId)

    return attending, invited, userDetails


def isStatusVisibleToUser(status, user):

    if status.visibility == Status.VIS_PUBLIC:
        return True
    elif status.visibility == Status.VIS_CUSTOM and user in status.friendsVisible.all():
        return True
    elif status.visibility == Status.VIS_FRIENDS or status.visibility == Status.VIS_FRIENDS_OF_FRIENDS:
        friends = status.user.friends.all()
        if user in friends:
            return True

        friendsOfFriends = UserProfile.objects.filter(friends__in=friends)
        if status.visibility == Status.VIS_FRIENDS_OF_FRIENDS and user in friendsOfFriends:
            return True

    return False
