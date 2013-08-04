import json
from datetime import timedelta

from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.http import HttpResponse
from django.utils.datetime_safe import datetime
import facebook
import pytz
from api.FacebookProfile import FacebookProfile
from api.helpers import createStatusJsonObject, DATETIME_FORMAT, getNewStatusesJsonResponse, createFriendJsonObject, getMyStatusesJsonResponse, getMyGroupsJsonResponse, getNewMessagesJsonResponse

from chat.models import Conversation, Message
from status.models import Status, Location, Poke
from userprofile.models import UserProfile, Group, Feedback


def errorResponse(error, response=None):
    if not response:
        response = dict()

    response['error'] = error
    response['success'] = False
    return HttpResponse(json.dumps(response))


def facebookLogin(request):
    response = dict()

    device = request.REQUEST['device']
    facebookAuthKey = request.REQUEST['fbauthkey']

    if device != 'ios' and device != 'android':
        return errorResponse('Invalid device: ' + device)

    try:
        facebookProfile = FacebookProfile.getFacebookUserFromAuthKey(facebookAuthKey, device)
        userProfile = facebookProfile.userProfile
    except facebook.GraphAPIError:
        return errorResponse("Invalid Facebook AUTH Key")

    response['friends'] = []

    facebookFriends = facebookProfile.getFacebookFriends()

    blockedFriends = userProfile.blockedFriends.all()
    for friend in facebookFriends:
        blocked = False
        if friend in blockedFriends:
            blocked = True

        friendData = createFriendJsonObject(friend, blocked)
        response['friends'].append(friendData)

    # Check all buddyup friends and add them if they weren't already included in facebook friends check
    friends = userProfile.friends.all()
    for friend in friends:
        if friend not in facebookFriends:
            blocked = False
            if friend in blockedFriends:
                blocked = True

            friendData = createFriendJsonObject(friend, blocked)
            response['friends'].append(friendData)

    statusesResponse = getNewStatusesJsonResponse(userProfile, None, None)
    myStatusesResponse = getMyStatusesJsonResponse(userProfile)
    groupsData = getMyGroupsJsonResponse(userProfile)
    chatMessagesData = getNewMessagesJsonResponse(userProfile, None)

    response['success'] = True
    response['firstname'] = userProfile.user.first_name
    response['lastname'] = userProfile.user.last_name
    response['userid'] = userProfile.id
    response['statuses'] = statusesResponse
    response['groups'] = groupsData
    response['mystatuses'] = myStatusesResponse
    response['messages'] = chatMessagesData

    return HttpResponse(json.dumps(response))


def facebookRegister(request):
    response = dict()

    device = request.REQUEST['device']
    facebookAuthKey = request.REQUEST['fbauthkey']

    if device != 'ios' and device != 'android':
        return errorResponse('Invalid device: ' + device)

    try:
        facebookProfile = FacebookProfile.getFacebookUserFromAuthKey(facebookAuthKey, device)
        userProfile = facebookProfile.userProfile
    except facebook.GraphAPIError:
        return errorResponse("Invalid Facebook AUTH Key")

    response['friends'] = []

    facebookFriends = facebookProfile.getFacebookFriends()

    blockedFriends = userProfile.blockedFriends.all()
    for friend in facebookFriends:
        blocked = False
        if friend in blockedFriends:
            blocked = True

        friendData = createFriendJsonObject(friend, blocked)
        response['friends'].append(friendData)

    # Check all buddyup friends and add them if they weren't already included in facebook friends check
    friends = userProfile.friends.all()
    for friend in friends:
        if friend not in facebookFriends:
            blocked = False
            if friend in blockedFriends:
                blocked = True

            friendData = createFriendJsonObject(friend, blocked)
            response['friends'].append(friendData)

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


def deleteStatus(request):
    response = dict()

    userid = request.REQUEST['userid']
    statusid = request.REQUEST['statusid']

    try:
        user = UserProfile.objects.get(pk=userid)
    except UserProfile.DoesNotExist:
        return errorResponse('Invalid User Id')

    try:
        status = Status.objects.get(pk=statusid)
    except Status.DoesNotExist:
        return errorResponse('Invalid Response Id')

    if status.user != user:
        return errorResponse('That is not your status')

    status.delete()

    response['success'] = True

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

    statusesData = getNewStatusesJsonResponse(userprofile, since, point, distance)

    response['success'] = True
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

    messagesData = getNewMessagesJsonResponse(userProfile, since)

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

    group.delete()

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


def setGroups(request):
    response = dict()

    userid = request.REQUEST['userid']
    friendid = request.REQUEST['friendid']
    groupids = request.REQUEST.get('groupids', '[]')
    groupids = json.loads(groupids)

    try:
        userProfile = UserProfile.objects.get(pk=userid)
    except UserProfile.DoesNotExist:
        return errorResponse("Invalid user id")

    try:
        friendProfile = UserProfile.objects.get(pk=friendid)
    except UserProfile.DoesNotExist:
        return errorResponse("Friend user does not exist")

    if friendProfile not in userProfile.friends.all():
        return errorResponse("That user is not your friend")

    newGroups = []
    for groupid in groupids:
        try:
            group = Group.objects.get(pk=groupid)
        except Group.DoesNotExist:
            return errorResponse("Group does not exist")

        if group not in userProfile.groups.all():
            return errorResponse("Invalid groupid")

        newGroups.append(group)

    for group in userProfile.groups.all():
        # if friend in current group and current group not in newGroups then remove from group
        if friendProfile in group.members.all():
            if group not in newGroups:
                group.members.remove(friendProfile)
                group.save()
        # if friend not in current group and current group is in newGroups then add to group
        else:
            if group in newGroups:
                group.members.add(friendProfile)
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

    groupsData = getMyGroupsJsonResponse(userProfile)

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
        blocked = False
        if friend in blockedFriends:
            blocked = True

        friendData = createFriendJsonObject(friend, blocked)

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