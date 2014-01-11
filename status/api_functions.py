from django.contrib.gis.geos import Point
from api.FacebookProfile import FacebookProfile
from api.views import *
from api.helpers import *
from push_notifications.notifications import sendPokeNotifcation, sendStatusMessageNotification
from status.models import Location, StatusMessage
from userprofile.models import Group, UserProfile


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


def getStatuses(request):
    response = dict()

    userid = request.REQUEST['userid']
    since = request.REQUEST.get('since', None)

    if since:
        since = datetime.strptime(since, MICROSECOND_DATETIME_FORMAT)

    try:
        userprofile = UserProfile.objects.get(pk=userid)
    except UserProfile.DoesNotExist:
        return errorResponse('Invalid User Id')

    statusesData, newSince = getNewStatusesJsonResponse(userprofile, since)

    response['success'] = True
    response['newsince'] = newSince.strftime(MICROSECOND_DATETIME_FORMAT)
    response['statuses'] = statusesData

    return HttpResponse(json.dumps(response))


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

    try:
        status = Status.objects.get(pk=statusid)
    except Status.DoesNotExist:
        status = Status(expires=expires, text=text, user=userprofile, starts=starts, statusType=statusType)

    if locationData:
        lat = locationData.get('lat', None)
        lng = locationData.get('lng', None)
        address = locationData.get('address', None)
        city = locationData.get('city', None)
        state = locationData.get('state', None)
        venue = locationData.get('venue', None)

        loc = Location.objects
        if lat:
            loc = loc.filter(lat=lat)
        if lng:
            loc = loc.filter(lng=lng)
        if address:
            loc = loc.filter(address=address)
        if city:
            loc = loc.filter(city=city)
        if state:
            loc = loc.filter(state=state)
        if venue:
            loc = loc.filter(venue=venue)

        if loc:
            location = loc[0]
        else:
            location = Location(lat=lat, lng=lng, address=address, city=city, state=state, venue=venue)
            if lat and lng:
                location.point = Point(lng, lat)
            location.save()

        status.location = location

    status.save()
    status.attending.add(userprofile)

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


def sendStatusMessage(request):
    response = dict()

    text = request.REQUEST['text']
    userid = request.REQUEST['userid']
    statusid = request.REQUEST['statusid']

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
    response['id'] = message.id

    return HttpResponse(json.dumps(response))


def getStatusDetails(request):
    response = dict()

    statusid = request.REQUEST['statusid']
    lastmessageid = request.REQUEST.get('lastid', None)

    try:
        status = Status.objects.get(pk=statusid)
    except Status.DoesNotExist:
        return errorResponse("Invalid status")

    messages = status.messages.all()
    if lastmessageid:
        messages = messages.filter(id__gt=lastmessageid)

    messagesJson = list()
    for message in messages:
        messageObj = dict()
        messageObj['id'] = message.id
        messageObj['userid'] = message.user.id
        messageObj['text'] = message.text
        messageObj['date'] = message.date.strftime(DATETIME_FORMAT)

        messagesJson.append(messageObj)

    response['success'] = True
    response['messages'] = messagesJson
    response['attending'] = []
    response['invited'] = []

    return HttpResponse(json.dumps(response))