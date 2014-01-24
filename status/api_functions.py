import pdb
from django.contrib.gis.geos import Point
from django.views.decorators.csrf import csrf_exempt
import pytz
from api.FacebookProfile import FacebookProfile
from api.views import *
from api.helpers import *
from push_notifications.notifications import sendPokeNotifcation, sendStatusMessageNotification
from status.helpers import getNewStatusMessages, getNewStatusesJsonResponse, getMyStatusesJsonResponse, getLocationObjectFromJson, createLocationJson, createLocationSuggestionJson, createTimeSuggestionJson
from status.models import Location, StatusMessage, Status, LocationSuggestion, TimeSuggestion
from userprofile.models import Group, UserProfile, FacebookUser

DEFAULT_GET_STATUS_RADIUS = 50


@csrf_exempt
def deleteStatus(request):
    response = dict()

    userid = request.REQUEST['userid']
    statusid = request.REQUEST['statusid']

    try:
        userProfile = UserProfile.objects.get(pk=userid)
        status = Status.objects.get(pk=statusid)
    except UserProfile.DoesNotExist:
        return errorResponse("Invalid user id")
    except Status.DoesNotExist:
        return errorResponse("Invalid statusid")

    if status.user == userProfile:
        status.delete()
        response['success'] = True
    else:
        response['success'] = False
        response['error'] = "Can not delete another user's status"

    return HttpResponse(json.dumps(response))


@csrf_exempt
def cancelStatus(request):
    response = dict()

    userid = request.REQUEST['userid']
    statusid = request.REQUEST['statusid']

    try:
        userProfile = UserProfile.objects.get(pk=userid)
        status = Status.objects.get(pk=statusid)
    except UserProfile.DoesNotExist:
        return errorResponse("Invalid user id")
    except Status.DoesNotExist:
        return errorResponse("Invalid statusid")

    if status.user != userProfile:
        return errorResponse("User does not own this status")

    now = datetime.utcnow()

    if status.expires > now:
        status.expires = now
        status.save()

    response['success'] = True

    return HttpResponse(json.dumps(response))


@csrf_exempt
def getStatuses(request):
    response = dict()

    userid = request.REQUEST['userid']
    lat = request.REQUEST.get('lat', None)
    lng = request.REQUEST.get('lng', None)
    radius = request.REQUEST.get('radius', None)

    since = request.REQUEST.get('since', None)

    if since:
        since = datetime.strptime(since, MICROSECOND_DATETIME_FORMAT)

    try:
        userprofile = UserProfile.objects.get(pk=userid)
    except UserProfile.DoesNotExist:
        return errorResponse('Invalid User Id')

    statusesData, newSince = getNewStatusesJsonResponse(userprofile, since, lat, lng, radius)

    response['success'] = True
    response['newsince'] = newSince.strftime(MICROSECOND_DATETIME_FORMAT)
    response['statuses'] = statusesData

    return HttpResponse(json.dumps(response))


@csrf_exempt
def getMyStatuses(request):
    response = dict()

    userid = request.REQUEST['userid']

    try:
        user = UserProfile.objects.get(pk=userid)
    except UserProfile.DoesNotExist:
        return errorResponse("Invalid user id")

    statusesData = getMyStatusesJsonResponse(user)

    response['success'] = True
    response['statuses'] = statusesData

    return HttpResponse(json.dumps(response))


@csrf_exempt
def poke(request):
    response = dict()

    userid = request.REQUEST['userid']
    friendid = request.REQUEST['friendid']
    lastHour = datetime.utcnow().replace(tzinfo=pytz.utc) - timedelta(hours=1)

    try:
        user = UserProfile.objects.get(pk=userid)
    except UserProfile.DoesNotExist:
        return errorResponse("Invalid user id")

    try:
        targetUser = UserProfile.objects.get(pk=friendid)
    except UserProfile.DoesNotExist:
        return errorResponse("Invalid target user id")

    if targetUser not in user.friends.all():
        return errorResponse("User is not your friend")

    poke = Poke.objects.filter(sender=user, recipient=targetUser, created__gt=lastHour)

    if poke:
        return errorResponse("Already poked user in the last hour")
    poke = Poke.objects.create(sender=user, recipient=targetUser)

    sendPokeNotifcation(poke)

    response['success'] = True

    return HttpResponse(json.dumps(response))


@csrf_exempt
def postStatus(request):
    response = dict()

    text = request.REQUEST['text']
    userid = request.REQUEST['userid']
    groupids = request.REQUEST.get('groupids', '[]')
    expires = request.REQUEST.get('expires', None)
    starts = request.REQUEST.get('starts', None)
    locationData = request.REQUEST.get('location', '{}')
    statusid = request.REQUEST.get('statusid', 0)
    accessToken = request.REQUEST.get('accesstoken', None)
    shareOnFacebook = request.REQUEST.get('facebookshare', False)
    statusType = request.REQUEST.get('type', 'other')
    visibility = request.REQUEST.get('visibility', 'friends')
    visibilityFriends = request.REQUEST.get('visibilityFriends', '[]')
    visibilityFbFriends = request.REQUEST.get('visibilityfbfriends', '[]')

    groupids = json.loads(groupids)
    locationData = json.loads(locationData)

    if starts:
        starts = datetime.strptime(starts, DATETIME_FORMAT).replace(tzinfo=pytz.utc)
    else:
        starts = datetime.utcnow()

    if expires:
        expires = datetime.strptime(expires, DATETIME_FORMAT).replace(tzinfo=pytz.utc)
    else:
        expires = starts + timedelta(hours=8)

    try:
        userprofile = UserProfile.objects.get(pk=userid)
    except UserProfile.DoesNotExist:
        return errorResponse("User Id not valid")

    if statusid:
        try:
            status = Status.objects.get(pk=statusid)
        except Status.DoesNotExist:
            return errorResponse('status does not exist with that id')
    else:
        status = Status(user=userprofile)

    status.expires = expires
    status.text = text
    status.starts = starts
    status.statusType = statusType
    status.visibility = visibility

    if locationData:
        location = getLocationObjectFromJson(locationData)
        status.location = location

    status.save()
    status.attending.add(userprofile)

    if status.visibility == 'custom':
        visibilityFriends = json.loads(visibilityFriends)
        visibilityFbFriends = json.loads(visibilityFbFriends)

        for friendId in visibilityFriends:
            try:
                friendProfile = UserProfile.objects.get(pk=friendId)
                status.friendsVisible.add(friendProfile)
            except UserProfile.DoesNotExist:
                pass

        for fbFriendId in visibilityFbFriends:
            try:
                friendProfile = UserProfile.objects.get(facebookUID=fbFriendId)
                status.friendsVisible.add(friendProfile)
            except UserProfile.DoesNotExist:
                try:
                    facebookUser = FacebookUser.objects.get(facebookUID=fbFriendId)
                except FacebookUser.DoesNotExist:
                    facebookUser = FacebookUser.objects.create(facebookUID=fbFriendId)

                status.fbFriendsVisible.add(facebookUser)

    if groupids:
        groups = Group.objects.filter(id__in=groupids)
        status.groups.add(*groups)
    else:
        status.groups.clear()

    status.save()

    if shareOnFacebook:
        if accessToken is not None:
            fbProfile = FacebookProfile(userprofile, accessToken)
            fbProfile.shareStatus(status, request)

    response['success'] = True
    response['statusid'] = status.id

    return HttpResponse(json.dumps(response))


@csrf_exempt
def inviteToStatus(request):
    response = dict()
    userid = request.REQUEST['userid']
    statusId = request.REQUEST['statusid']
    friends = request.REQUEST.get('friends', '[]')
    fbFriends = request.REQUEST.get('fbfriends', '[]')

    friends = json.loads(friends)
    fbFriends = json.loads(fbFriends)

    try:
        userProfile = UserProfile.objects.get(pk=userid)
    except UserProfile.DoesNotExist:
        return errorResponse('Invalid User')

    try:
        status = Status.objects.get(pk=statusId)
    except Status.DoesNotExist:
        return errorResponse('Invalid Status')

    # if status.user != userProfile:
    #     if status.visibility == Status.VIS_FRIENDS or status.visibility == Status.VIS_CUSTOM:
    #         return errorResponse("Cant invite people to private events")

    friends = UserProfile.objects.filter(pk__in=friends)
    status.invited.add(*list(friends))

    for fbFriendId in fbFriends:
        try:
            friend = UserProfile.objects.get(facebookUID=fbFriendId)
            status.invited.add(friend)
        except UserProfile.DoesNotExist:
            try:
                friend = FacebookUser.objects.get(facebookUID=fbFriendId)
            except FacebookUser.DoesNotExist:
                friend = FacebookUser.objects.create(facebookUID=fbFriendId)

            status.fbInvited.add(friend)

    response['success'] = True

    return HttpResponse(json.dumps(response))


@csrf_exempt
def rsvpStatus(request):
    response = dict()

    userId = request.REQUEST['userid']
    statusId = request.REQUEST['statusid']
    attending = request.REQUEST['attending']

    try:
        userProfile = UserProfile.objects.get(pk=userId)
    except UserProfile.DoesNotExist:
        return errorResponse('Invalid User')

    try:
        status = Status.objects.get(pk=statusId)
    except Status.DoesNotExist:
        return errorResponse('Invalid Status')

    if attending == 'true' or attending == 'True':
        status.attending.add(userProfile)
    elif attending == 'false' or attending == 'False':
        status.attending.remove(userProfile)
    else:
        return errorResponse("Invalid Attending value. Must be true or false")

    response['success'] = True

    return HttpResponse(json.dumps(response))


@csrf_exempt
def sendStatusMessage(request):
    response = dict()

    text = request.REQUEST['text']
    userid = request.REQUEST['userid']
    statusid = request.REQUEST['statusid']
    lastMessageId = request.REQUEST.get('lastmessageid', None)

    try:
        userProfile = UserProfile.objects.get(pk=userid)
    except UserProfile.DoesNotExist:
        return errorResponse('Invalid User')

    try:
        status = Status.objects.get(pk=statusid)
    except Status.DoesNotExist:
        return errorResponse('Invalid status id')

    message = StatusMessage.objects.create(user=userProfile, text=text, status=status)
    sendStatusMessageNotification(message)

    response['success'] = True
    response['messages'] = getNewStatusMessages(status, lastMessageId)

    return HttpResponse(json.dumps(response))


@csrf_exempt
def getStatusDetails(request):
    response = dict()

    statusid = request.REQUEST['statusid']
    lastmessageid = request.REQUEST.get('lastmessageid', None)

    try:
        status = Status.objects.get(pk=statusid)
    except Status.DoesNotExist:
        return errorResponse("Invalid status")

    messagesJson = getNewStatusMessages(status, lastmessageid)
    locationSuggestions = list()
    for locationSugg in status.locationSuggestions.all():
        locationSuggestions.append(createLocationSuggestionJson(locationSugg))

    timeSuggestions = list()
    for timeSugg in status.timeSuggestions.all():
        timeSuggestions.append(createTimeSuggestionJson(timeSugg))

    response['success'] = True
    response['messages'] = messagesJson
    response['attending'] = list(status.attending.values_list('id', flat=True))
    response['fbattending'] = list(status.fbAttending.values_list('facebookUID', flat=True))
    response['invited'] = list(status.invited.values_list('id', flat=True))
    response['fbinvited'] = list(status.fbInvited.values_list('facebookUID', flat=True))
    response['locationsuggestions'] = locationSuggestions
    response['timesuggestions'] = timeSuggestions

    return HttpResponse(json.dumps(response))


@csrf_exempt
def suggestLocationTime(request):
    response = dict()

    userid = request.REQUEST['userid']
    statusid = request.REQUEST['statusid']
    suggestionType = request.REQUEST['type']
    location = request.REQUEST.get('location', None)
    time = request.REQUEST.get('time', None)

    if suggestionType != 'location' or suggestionType != 'time':
        return errorResponse('type must be location or time')

    try:
        userProfile = UserProfile.objects.get(pk=userid)
    except UserProfile.DoesNotExist:
        return errorResponse('Invalid User')

    try:
        status = Status.objects.get(pk=statusid)
    except Status.DoesNotExist:
        return errorResponse('Invalid status id')

    if suggestionType == 'location':
        location = getLocationObjectFromJson(json.loads(location))
        locationSuggestion = LocationSuggestion.objects.get_or_create(user=userProfile, status=status,
                                                                      location=location)

    if suggestionType == 'time':
        date = datetime.strptime(time, DATETIME_FORMAT)
        timeSuggestion = TimeSuggestion.objects.get_or_create(user=userProfile, status=status, dateSuggested=time)

    response['success'] = True

    return HttpResponse(json.dumps(response))




