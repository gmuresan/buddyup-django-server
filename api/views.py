import json
from datetime import timedelta

from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.http import HttpResponse
from django.utils.datetime_safe import datetime
import facebook
import pytz

from chat.models import Conversation, Message
from status.models import Status, Location, Poke
from userprofile.models import UserProfile, Group, Feedback


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
        user = User(username=profile['email'], email=profile['email'], first_name=profile['first_name'],
                    last_name=profile['last_name'],
                    password=0)
        user.save()

        userProfile = UserProfile(facebookUID=facebookId, user=user)
        userProfile.save()

    response['friends'] = []
    appFriends = graph.request("me/friends", {'fields': 'installed'})

    friendIds = []
    # Check all facebook friends to see if they are a buddyup friend
    for appFriend in appFriends['data']:

        if 'installed' in appFriend and appFriend['installed'] is True:
            friendFBID = appFriend['id']

            try:
                friendProfile = UserProfile.objects.get(facebookUID=friendFBID)

                # Add the user to the friends list if they arent a friend already
                if friendProfile not in userProfile.friends.all():
                    userProfile.friends.add(friendProfile)
                    userProfile.save()
                if userProfile not in friendProfile.friends.all():
                    friendProfile.friends.add(userProfile)
                    friendProfile.save()

                friendData = {'userid': friendProfile.id, 'firstname': friendProfile.user.first_name,
                              'lastname': friendProfile.user.last_name, 'blocked': False}

                if friendProfile in userProfile.blockedFriends.all():
                    friendData['blocked'] = True

                response['friends'].append(friendData)
                friendIds.append(friendProfile.id)

            except UserProfile.DoesNotExist:
                pass

    # Check all buddyup friends and add them if they weren't already included in facebook friends check
    for friend in userProfile.friends.all():
        if friend.id not in friendIds:
            friendData = {'userid': friend.id, 'firstname': friend.user.first_name,
                          'lastname': friend.user.last_name, 'blocked': False}

            if friend in userProfile.blockedFriends.all():
                friendData['blocked'] = True

            response['friends'].append(friendData)
            friendIds.append(friend.id)

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
                status.groups.add(group)
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
    point = Point(float(lng), float(lat))
    since = request.REQUEST.get('since', None)

    try:
        userprofile = UserProfile.objects.get(pk=userid)
    except UserProfile.DoesNotExist:
        return errorResponse('Invalid User Id')

    now = datetime.utcnow().replace(tzinfo=pytz.utc)
    friends = userprofile.getUnblockedFriends()

    if since is not None:
        since = datetime.strptime(since, DATETIME_FORMAT).replace(tzinfo=pytz.utc)
        statuses = Status.objects.filter(user__in=friends, date__gt=since, expires__gt=now,
                                         location__point__distance_lte=(point, D(mi=int(distance))))
    else:
        statuses = Status.objects.filter(user__in=friends, location__point__distance_lte=(point, D(mi=int(distance))))

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
        statusData['statusid'] = status.id
        statusData['userid'] = status.user_id
        statusData['text'] = status.text
        statusData['datecreated'] = status.date.strftime(DATETIME_FORMAT)

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

    # TODO: need to send push notification to target user

    response['success'] = True
    response['pokeid'] = poke.id

    return HttpResponse(json.dumps(response))


def createChat(request):
    response = dict()

    userid = request.REQUEST['userid']
    friendid = request.REQUEST['friendid']

    try:
        userProfile = UserProfile.objects.get(pk=userid)
    except UserProfile.DoesNotExist:
        return errorResponse("User ID is not valid")

    try:
        friendProfile = UserProfile.objects.get(pk=friendid)
    except UserProfile.DoesNotExist:
        return errorResponse("Friend ID is not valid")

    if friendProfile not in userProfile.getUnblockedFriends():
        return errorResponse("That user is not your friend")

    if userProfile not in friendProfile.getUnblockedFriends():
        return errorResponse("You are not that user's friend")

    if userProfile in friendProfile.blockedFriends.all():
        return errorResponse("That user has blocked you")

    conversation = Conversation.objects.create()
    conversation.members.add(userProfile)
    conversation.members.add(friendProfile)

    #TODO: Send push notification to friend that was invited to chat

    response['success'] = True
    response['chatid'] = conversation.id

    return HttpResponse(json.dumps(response))


def inviteToChat(request):
    response = dict()

    userid = request.REQUEST['userid']
    friendid = request.REQUEST['friendid']
    chatid = request.REQUEST['chatid']

    try:
        userProfile = UserProfile.objects.get(pk=userid)
    except UserProfile.DoesNotExist:
        return errorResponse("User ID is not valid")

    try:
        friendProfile = UserProfile.objects.get(pk=friendid)
    except UserProfile.DoesNotExist:
        return errorResponse("Friend ID is not valid")

    if friendProfile not in userProfile.getUnblockedFriends():
        return errorResponse("That user is not your friend")

    if userProfile not in friendProfile.getUnblockedFriends():
        return errorResponse("You are not that user's friend")

    if userProfile in friendProfile.blockedFriends.all():
        return errorResponse("That user has blocked you")

    try:
        conversation = Conversation.objects.get(pk=chatid)
    except Conversation.DoesNotExist:
        return errorResponse("Chat id does not exist")

    members = conversation.members.all()
    if userProfile not in members:
        return errorResponse("You are not part of this conversation")

    if friendProfile in members:
        return errorResponse("Friend is already a member of this chat")

    conversation.members.add(friendProfile)
    conversation.save()

    #TODO: Send push notification to friend that he was invited to chat

    response['success'] = True

    return HttpResponse(json.dumps(response))


def leaveChat(request):
    response = dict()

    userid = request.REQUEST['userid']
    chatid = request.REQUEST['chatid']

    try:
        userProfile = UserProfile.objects.get(pk=userid)
    except UserProfile.DoesNotExist:
        return errorResponse("Invalid user id")

    try:
        convo = Conversation.objects.get(pk=chatid)
    except Conversation.DoesNotExist:
        return errorResponse("Invalid chat id")

    if userProfile not in convo.members.all():
        return errorResponse("User is not a member of this chat")

    convo.members.remove(userProfile)
    convo.save()

    if convo.members.count() == 0:
        convo.delete()

    response['success'] = True

    return HttpResponse(json.dumps(response))


def sendMessage(request):
    response = dict()

    userid = request.REQUEST['userid']
    chatid = request.REQUEST['chatid']
    text = request.REQUEST['text']

    try:
        userProfile = UserProfile.objects.get(pk=userid)
    except UserProfile.DoesNotExist:
        return errorResponse("Invalid user id")

    try:
        convo = Conversation.objects.get(pk=chatid)
    except Conversation.DoesNotExist:
        return errorResponse("Invalid chat id")

    if userProfile not in convo.members.all():
        return errorResponse("User is not a member of this chat")

    Message.objects.create(user=userProfile, conversation=convo, text=text)

    response['success'] = True

    return HttpResponse(json.dumps(response))


def getMessages(request):
    response = dict()

    userid = request.REQUEST['userid']
    since = request.REQUEST['since']
    since = datetime.strptime(since, DATETIME_FORMAT).replace(tzinfo=pytz.utc)

    try:
        userProfile = UserProfile.objects.get(pk=userid)
    except UserProfile.DoesNotExist:
        return errorResponse("Invalid user id")

    conversations = userProfile.conversations.filter(lastActivity__gt=since)

    messages = []
    for convo in conversations:
        msgs = convo.messages.filter(created__gt=since)
        msgs.latest('created')
        for msg in msgs:
            messages.append(msg)

    messagesData = []
    for message in messages:
        messageData = dict()
        messageData['messageid'] = message.id
        messageData['chatid'] = message.conversation.id
        messageData['date'] = message.created.strftime(DATETIME_FORMAT)
        messageData['text'] = message.text
        messageData['userid'] = message.user.id

        messagesData.append(messageData)

    response['success'] = True
    response['messages'] = messagesData

    return HttpResponse(json.dumps(response))


def createGroup(request):
    response = dict()

    userid = request.REQUEST['userid']
    groupName = request.REQUEST['groupname']

    try:
        userProfile = UserProfile.objects.get(pk=userid)
    except UserProfile.DoesNotExist:
        return errorResponse("Invalid user id")

    group = Group.objects.filter(name=groupName, user=userProfile)
    if group.count() != 0:
        return errorResponse("You already have a group with that name")

    group = Group.objects.create(name=groupName, user=userProfile)

    response['success'] = True
    response['groupid'] = group.id

    return HttpResponse(json.dumps(response))


def deleteGroup(request):
    response = dict()

    userid = request.REQUEST['userid']
    groupid = request.REQUEST['groupid']

    try:
        userProfile = UserProfile.objects.get(pk=userid)
    except UserProfile.DoesNotExist:
        return errorResponse("Invalid user id")

    try:
        group = Group.objects.get(pk=groupid)
    except Group.DoesNotExist:
        return errorResponse("Invalid group id")

    if group.user != userProfile:
        return errorResponse("Group does not belong to user")

    response['success'] = True

    return HttpResponse(json.dumps(response))


def editGroupName(request):
    response = dict()

    userid = request.REQUEST['userid']
    groupName = request.REQUEST['groupname']
    groupid = request.REQUEST['groupid']

    try:
        userProfile = UserProfile.objects.get(pk=userid)
    except UserProfile.DoesNotExist:
        return errorResponse("Invalid user id")

    try:
        group = Group.objects.get(pk=groupid)
    except Group.DoesNotExist:
        return errorResponse("Invalid group id")

    if group.user != userProfile:
        return errorResponse("Group does not belong to user")

    group.name = groupName
    group.save()

    response['success'] = True

    return HttpResponse(json.dumps(response))


def addGroupMember(request):
    response = dict()

    userid = request.REQUEST['userid']
    friendid = request.REQUEST['friendid']
    groupid = request.REQUEST['groupid']

    try:
        userProfile = UserProfile.objects.get(pk=userid)
    except UserProfile.DoesNotExist:
        return errorResponse("Invalid user id")

    try:
        group = Group.objects.get(pk=groupid)
    except Group.DoesNotExist:
        return errorResponse("Invalid group id")

    if group.user != userProfile:
        return errorResponse("Group does not belong to user")

    try:
        friendProfile = UserProfile.objects.get(pk=friendid)
    except UserProfile.DoesNotExist:
        return errorResponse("Friend user does not exist")

    if friendProfile not in userProfile.friends.all():
        return errorResponse("That user is not your friend")

    if friendProfile not in group.members.all():
        group.members.add(friendProfile)

    response['success'] = True

    return HttpResponse(json.dumps(response))


def removeGroupMember(request):
    response = dict()

    userid = request.REQUEST['userid']
    friendid = request.REQUEST['friendid']
    groupid = request.REQUEST['groupid']

    try:
        userProfile = UserProfile.objects.get(pk=userid)
    except UserProfile.DoesNotExist:
        return errorResponse("Invalid user id")

    try:
        group = Group.objects.get(pk=groupid)
    except Group.DoesNotExist:
        return errorResponse("Invalid group id")

    if group.user != userProfile:
        return errorResponse("Group does not belong to user")

    try:
        friendProfile = UserProfile.objects.get(pk=friendid)
    except UserProfile.DoesNotExist:
        return errorResponse("Friend user does not exist")

    if friendProfile not in userProfile.friends.all():
        return errorResponse("That user is not your friend")

    if friendProfile in group.members.all():
        group.members.remove(friendProfile)

    response['success'] = True

    return HttpResponse(json.dumps(response))


def getGroups(request):
    response = dict()

    userid = request.REQUEST['userid']

    try:
        userProfile = UserProfile.objects.get(pk=userid)
    except UserProfile.DoesNotExist:
        return errorResponse("Invalid user id")

    groups = userProfile.groups.all()
    groupsData = list()

    for group in groups:
        groupData = dict()

        groupData['groupname'] = group.name
        groupData['groupid'] = group.id

        memberIds = group.members.values_list('id', flat=True)
        groupData['userids'] = map(int, memberIds)
        groupsData.append(groupData)

    response['success'] = True
    response['groups'] = groupsData

    return HttpResponse(json.dumps(response))


def getFriends(request):
    response = dict()

    userid = request.REQUEST['userid']

    try:
        userProfile = UserProfile.objects.get(pk=userid)
    except UserProfile.DoesNotExist:
        return errorResponse("Invalid user id")

    blockedFriends = userProfile.blockedFriends.all()
    friendsData = list()

    for friend in userProfile.friends.all():
        friendData = dict()
        friendData['userid'] = friend.id
        friendData['firstname'] = friend.user.first_name
        friendData['lastname'] = friend.user.last_name
        friendData['blocked'] = friend in blockedFriends

        friendsData.append(friendData)

    response['success'] = True
    response['friends'] = friendsData

    return HttpResponse(json.dumps(response))


def blockFriend(request):
    response = dict()

    userid = request.REQUEST['userid']
    friendid = request.REQUEST['friendid']

    try:
        userProfile = UserProfile.objects.get(pk=userid)
    except UserProfile.DoesNotExist:
        return errorResponse("Invalid user id")

    try:
        friendProfile = UserProfile.objects.get(pk=friendid)
    except UserProfile.DoesNotExist:
        return errorResponse("Invalid friend id")

    if friendProfile not in userProfile.friends.all():
        return errorResponse("Target is not your friend")

    userProfile.blockedFriends.add(friendProfile)
    userProfile.save()

    response['success'] = True

    return HttpResponse(json.dumps(response))


def unblockFriend(request):
    response = dict()

    userid = request.REQUEST['userid']
    friendid = request.REQUEST['friendid']

    try:
        userProfile = UserProfile.objects.get(pk=userid)
    except UserProfile.DoesNotExist:
        return errorResponse("Invalid user id")

    try:
        friendProfile = UserProfile.objects.get(pk=friendid)
    except UserProfile.DoesNotExist:
        return errorResponse("Invalid friend id")

    if friendProfile not in userProfile.friends.all():
        return errorResponse("Target is not your friend")

    if friendProfile in userProfile.blockedFriends.all():
        userProfile.blockedFriends.remove(friendProfile)
        userProfile.save()

    response['success'] = True

    return HttpResponse(json.dumps(response))


def submitFeedback(request):
    response = dict()

    userid = request.REQUEST['userid']
    text = request.REQUEST['text']

    try:
        userProfile = UserProfile.objects.get(pk=userid)
    except UserProfile.DoesNotExist:
        return errorResponse("Invalid user id")

    Feedback.objects.create(user=userProfile, text=text)

    response['success'] = True

    return HttpResponse(json.dumps(response))