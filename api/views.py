import json
from django.contrib.auth.models import User
from django.contrib.gis.db.models import PointField
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.http import HttpResponse
from django.utils.datetime_safe import datetime
from datetime import timedelta
import facebook
import pytz
from status.models import Status, Location, Poke
from userprofile.models import UserProfile, Group

DATETIME_FORMAT = '%m-%d-%Y %H:%M'  # 06-01-2013 13:12


def errorResponse(error, response=None):
    if not response:
        response = dict()

    response['error'] = error
    response['success'] = False
    return HttpResponse(json.dumps(response))


def facebookRegister(request):
    response = dict()

    device = request.REQUEST['device']
    facebookAuthKey = request.REQUEST['fbauthkey']

    if device != 'ios' and device != 'android':
        return errorResponse('Invalid device: ' + device)

    try:
        graph = facebook.GraphAPI(facebookAuthKey)
        profile = graph.get_object("me")
    except facebook.GraphAPIError:
        return errorResponse("Invalid Facebook AUTH Key")

    facebookId = profile['id']

    try:
        userProfile = UserProfile.objects.get(facebookUID=facebookId)
    except UserProfile.DoesNotExist:
        user = User(username=profile['email'], email=profile['email'], first_name=profile['first_name'], last_name=profile['last_name'],
                    password=0)
        user.save()

        userProfile = UserProfile(facebookUID=facebookId, user=user)
        userProfile.save()

    response['friends'] = []
    appFriends = graph.request("me/friends", {'fields': 'installed'})
    for appFriend in appFriends['data']:

        if 'installed' in appFriend and appFriend['installed'] is True:
            friendFBID = appFriend['id']

            try:
                friendProfile = UserProfile.objects.get(facebookUID=friendFBID)

                friendData = {'id': friendProfile.id, 'firstName': friendProfile.user.first_name,
                              'lastName': friendProfile.user.last_name}

                if friendProfile in userProfile.blockedFriends.all():
                    friendData['blocked'] = True

                response['friends'].append(friendData)

            except UserProfile.DoesNotExist:
                pass

    response['success'] = True
    response['firstname'] = userProfile.user.first_name
    response['lastname'] = userProfile.user.last_name
    response['userid'] = userProfile.id

    return HttpResponse(json.dumps(response))


def postStatus(request):
    response = dict()

    text = request.REQUEST['text']
    userid = request.REQUEST['userid']
    groupids = request.REQUEST.get('groupids', '[]')
    expires = request.REQUEST['expires']
    locationData = request.REQUEST.get('location', '{}')
    statusid = request.REQUEST.get('statusid', 0)

    groupids = json.loads(groupids)
    locationData = json.loads(locationData)
    expires = datetime.strptime(expires, DATETIME_FORMAT).replace(tzinfo=pytz.utc)

    try:
        userprofile = UserProfile.objects.get(pk=userid)
    except UserProfile.DoesNotExist:
        return errorResponse(response, "User Id not valid")

    try:
        status = Status.objects.get(pk=statusid)
    except Status.DoesNotExist:
        status = Status(expires=expires, text=text, user=userprofile)

    if locationData:
        lat = locationData.get('lat', None)
        lng = locationData.get('lng', None)
        address = locationData.get('address', None)
        city = locationData.get('city', None)
        state = locationData.get('state', None)

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

        if loc:
            location = loc[0]
        else:
            location = Location(lat=lat, lng=lng, address=address, city=city, state=state)
            if lat and lng:
                location.point = Point(lng, lat)
            location.save()

        status.location = location

    status.save()

    if groupids:
        groups = []
        for id in groupids:
            try:
                group = Group.objects.get(pk=id)
            except Group.DoesNotExist:
                return errorResponse(response, "Group does not exist: " + id)

            if group.user is not userprofile:
                return errorResponse(response, "Group does not belong to this user: " + id)
    else:
        status.groups.clear()
        status.save()

    response['success'] = True
    response['statusid'] = status.id

    return HttpResponse(json.dumps(response))


def getStatuses(request):
    response = dict()

    userid = request.REQUEST['userid']
    lat = request.REQUEST['lat']
    lng = request.REQUEST['lng']
    distance = request.REQUEST.get('distance', 5)
    point = Point(lng, lat)

    try:
        userprofile = UserProfile.objects.get(pk=userid)
    except UserProfile.DoesNotExist:
        return errorResponse('Invalid User Id')

    since = request.REQUEST['since']
    since = datetime.strptime(since, DATETIME_FORMAT)

    now = datetime.now('UTC')

    friends = userprofile.getUnblockedFriends()
    statuses = Status.objects.filter(user__in=list(friends), expires__gt=now, date__gt=since,
                                     location__point__distance_lte=(point, D(mi=distance)))

    statusesData = []
    for status in statuses:

        # If the status is only broadcast to certain groups,
        # Check if the current user is in one of those groups
        if status.groups.count():
            inGroup = False
            for group in status.groups:
                if userprofile in group.members:
                    inGroup = True
                    break

            if not inGroup:
                continue

        statusData = dict()
        statusData['id'] = status.id
        statusData['userid'] = status.user_id
        statusData['text'] = status.text

        if status.location:
            location = dict()
            location['lat'] = status.location.lat
            location['lng'] = status.location.lng
            location['address'] = status.location.address
            location['city'] = status.location.city
            location['state'] = status.location.state

        statusesData.append(statusData)

    response['success'] = True
    response['statuses'] = statusesData

    return HttpResponse(json.dumps(response))


def poke(request):
    response = dict()

    userid = request.REQUEST['userid']
    targetid = request.REQUEST['targetid']
    lastHour = datetime.now() - timedelta()

    try:
        user = UserProfile.objects.get(pk=userid)
    except UserProfile.DoesNotExist:
        return errorResponse("Invalid user id")

    try:
        targetUser = UserProfile.objects.get(pk=targetid)
    except UserProfile.DoesNotExist:
        return errorResponse("Invalid target user id")

    if targetUser not in user.friends:
        return errorResponse("User is not your friend")

    try:
        poke = Poke.objects.filter(sender=user, recipient=targetUser, created_gt=lastHour)
        return errorResponse("Already poked user in the last hour")
    except Poke.DoesNotExist:
        poke = Poke.objects.create(sender=user, recipient=targetUser)

    # TODO: need to send push notification to target user

    response['success'] = True
    response['pokeid'] = poke.id

    return HttpResponse(json.dumps(response))


def createChat(request):
    response = dict()

    userid = request.REQUEST['userid']
    friendid = request.REQUEST['friendid']



















