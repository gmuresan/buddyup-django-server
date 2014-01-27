import pdb
from django.contrib.auth.models import User
import facebook
from api.FacebookProfile import FacebookProfile
from api.helpers import *
from api.views import *
from push_notifications.models import GCMDevice, APNSDevice
from status.helpers import getNewStatusesJsonResponse, getMyStatusesJsonResponse
from userprofile.models import UserProfile, Group, Feedback, Setting, FacebookUser
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
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

        friendData = createFriendJsonObject(friend, blocked, userProfile)
        response['friends'].append(friendData)

    # Check all buddyup friends and add them if they weren't already included in facebook friends check
    friends = userProfile.friends.all()
    for friend in friends:
        if friend not in facebookFriends:
            blocked = False
            if friend in blockedFriends:
                blocked = True

            friendData = createFriendJsonObject(friend, blocked, userProfile)
            response['friends'].append(friendData)

    statusesResponse, newSince = getNewStatusesJsonResponse(userProfile, None)
    myStatusesResponse = getMyStatusesJsonResponse(userProfile)
    groupsData = getMyGroupsJsonResponse(userProfile)
    chatData, newSince = getNewChatsData(userProfile)
    settings = getSettingsData(userProfile)

    response['success'] = True
    response['firstname'] = userProfile.user.first_name
    response['lastname'] = userProfile.user.last_name
    response['userid'] = userProfile.id
    response['facebookid'] = userProfile.facebookUID
    response['statuses'] = statusesResponse
    response['groups'] = groupsData
    response['mystatuses'] = myStatusesResponse
    response['chats'] = chatData
    response['newsince'] = newSince.strftime(MICROSECOND_DATETIME_FORMAT)
    response['settings'] = settings

    return HttpResponse(json.dumps(response))


@csrf_exempt
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


@csrf_exempt
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


@csrf_exempt
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


@csrf_exempt
def setGroups(request):
    response = dict()

    userid = request.REQUEST['userid']
    friendid = str(request.REQUEST['friendid'])
    groupids = request.REQUEST.get('groupids', '[]')
    groupids = json.loads(groupids)

    try:
        userProfile = UserProfile.objects.get(pk=userid)
    except UserProfile.DoesNotExist:
        return errorResponse("Invalid user id")

    if friendid[:2] == 'fb':
        friendid = friendid[2:]
        try:
            friendProfile = UserProfile.objects.get(facebookUID=friendid)
        except UserProfile.DoesNotExist:
            try:
                friendProfile = FacebookUser.objects.get(facebookUID=friendid)
            except FacebookUser.DoesNotExist:
                friendProfile = FacebookUser.objects.create(facebookUID=friendid)
    else:
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
        members = None
        if isinstance(friendProfile, UserProfile):
            members = group.members
        elif isinstance(friendProfile, FacebookUser):
            members = group.fbMembers

        # if friend in current group and current group not in newGroups then remove from group
        if friendProfile in members.all():
            if group not in newGroups:
                members.remove(friendProfile)
                group.save()
        # if friend not in current group and current group is in newGroups then add to group
        else:
            if group in newGroups:
                members.add(friendProfile)
                group.save()

    response['success'] = True
    return HttpResponse(json.dumps(response))


@csrf_exempt
def addGroupMember(request):
    response = dict()

    userid = request.REQUEST['userid']
    friendid = str(request.REQUEST['friendid'])
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

    if friendid[:2] == 'fb':
        friendid = friendid[2:]
        try:
            friendProfile = UserProfile.objects.get(facebookUID=friendid)
            group.members.add(friendProfile)
        except UserProfile.DoesNotExist:
            try:
                facebookUser = FacebookUser.objects.get(facebookUID=friendid)
            except FacebookUser.DoesNotExist:
                facebookUser = FacebookUser.objects.create(facebookUID=friendid)
            group.fbMembers.add(facebookUser)
    else:
        try:
            friend = UserProfile.objects.get(pk=friendid)
            group.members.add(friend)
        except User.DoesNotExist:
            return errorResponse("Friend does not exist")

    response['success'] = True

    return HttpResponse(json.dumps(response))


@csrf_exempt
def removeGroupMember(request):
    response = dict()

    userid = request.REQUEST['userid']
    friendid = str(request.REQUEST['friendid'])
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

    if friendid[:2] == 'fb':
        friendid = friendid[2:]
        try:
            friendProfile = UserProfile.objects.get(facebookUID=friendid)
            group.members.remove(friendProfile)
        except UserProfile.DoesNotExist:
            try:
                facebookUser = FacebookUser.objects.get(facebookUID=friendid)
            except FacebookUser.DoesNotExist:
                facebookUser = FacebookUser.objects.create(facebookUID=friendid)
            group.fbMembers.remove(facebookUser)
    else:
        try:
            friend = UserProfile.objects.get(pk=friendid)
            group.members.remove(friend)
        except User.DoesNotExist:
            return errorResponse("Friend does not exist")

    response['success'] = True

    return HttpResponse(json.dumps(response))


@csrf_exempt
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


@csrf_exempt
def setGroupMembers(request):
    response = dict()

    userid = request.REQUEST['userid']
    groupid = request.REQUEST['groupid']
    friendids = request.REQUEST.get('friendids', [])
    friendids = json.loads(friendids)

    try:
        userProfile = UserProfile.objects.get(pk=userid)
    except UserProfile.DoesNotExist:
        return errorResponse("Invalid user id")

    try:
        group = Group.objects.get(pk=groupid)
    except Group.DoesNotExist:
        return errorResponse("Invalid group id")

    if group.user != userProfile:
        return errorResponse("User does not own that group")

    userFriends = userProfile.friends.all()
    group.members.clear()

    for friendid in friendids:
        friendid = str(friendid)
        if friendid[:2] == 'fb':
            friendid = friendid[2:]
            try:
                friendProfile = UserProfile.objects.get(facebookUID=friendid)
                group.members.add(friendProfile)
            except UserProfile.DoesNotExist:
                try:
                    facebookUser = FacebookUser.objects.get(facebookUID=friendid)
                except FacebookUser.DoesNotExist:
                    facebookUser = FacebookUser.objects.create(facebookUID=friendid)
                group.fbMembers.add(facebookUser)
        else:
            try:
                friend = UserProfile.objects.get(pk=friendid)
            except User.DoesNotExist:
                return errorResponse("Friend does not exist")

            if friend not in userFriends:
                return errorResponse("User is not a friend")

            group.members.add(friend)

    group.save()

    response['success'] = True

    return HttpResponse(json.dumps(response))


@csrf_exempt
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

        friendData = createFriendJsonObject(friend, blocked, userProfile)

        friendsData.append(friendData)

    response['success'] = True
    response['friends'] = friendsData

    return HttpResponse(json.dumps(response))


@csrf_exempt
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


@csrf_exempt
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


@csrf_exempt
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


@csrf_exempt
def getNewData(request):
    response = dict()

    userid = request.REQUEST['userid']
    since = request.REQUEST.get('since')
    if since:
        since = datetime.strptime(since, MICROSECOND_DATETIME_FORMAT)

    try:
        userProfile = UserProfile.objects.get(pk=userid)
    except UserProfile.DoesNotExist:
        return errorResponse("Invalid user id")

    pokes = getNewPokesData(userProfile, since)
    chats, newSince = getNewChatsData(userProfile, since)

    response['chats'] = chats
    response['newsince'] = newSince.strftime(MICROSECOND_DATETIME_FORMAT)
    response['success'] = True
    response['pokes'] = pokes

    return HttpResponse(json.dumps(response))


@csrf_exempt
def goOffline(request):
    response = dict()

    userid = request.REQUEST['userid']

    try:
        userProfile = UserProfile.objects.get(pk=userid)
    except UserProfile.DoesNotExist:
        return errorResponse("User does not exist")

    activeStatuses = userProfile.getActiveStatuses()

    now = datetime.utcnow()
    for status in activeStatuses:
        status.expires = now
        status.save()

    response['success'] = True

    return HttpResponse(json.dumps(response))


@csrf_exempt
def setSetting(request):
    response = dict()

    userid = request.REQUEST['userid']
    key = request.REQUEST['key']
    value = request.REQUEST['value']

    if key != 'statusradius' and key != 'imboredtext':
        return errorResponse("unknown key. Must be statusradius or imboredtext")

    try:
        userProfile = UserProfile.objects.get(pk=userid)
    except UserProfile.DoesNotExist:
        return errorResponse("User does not exist")

    try:
        setting = userProfile.settings.get(key=key)
        setting.value = value
        setting.save()
    except Setting.DoesNotExist:
        Setting.objects.create(user=userProfile, value=value, key=key)

    response['success'] = True

    return HttpResponse(json.dumps(response))


@csrf_exempt
def getSetting(request):
    response = dict()

    userid = request.REQUEST['userid']
    key = request.REQUEST['key']

    try:
        userProfile = UserProfile.objects.get(pk=userid)
    except UserProfile.DoesNotExist:
        return errorResponse("User does not exist")

    try:
        setting = userProfile.settings.get(key=key)
        value = setting.value
    except Setting.DoesNotExist:
        value = ''

    response['success'] = True
    response['value'] = value

    return HttpResponse(json.dumps(response))


@csrf_exempt
def registerForPushNotifications(request):
    response = dict()

    userid = request.REQUEST['userid']
    token = request.REQUEST['token']
    platform = request.REQUEST['platform']

    try:
        userProfile = UserProfile.objects.get(pk=userid)
    except UserProfile.DoesNotExist:
        return errorResponse("User does not exist")

    if platform == 'ios':
        try:
            device = APNSDevice.objects.get(user=userProfile, registration_id=token)
        except APNSDevice.DoesNotExist:
            device = APNSDevice.objects.create(user=userProfile, registration_id=token)
    elif platform == 'android':
        try:
            device = GCMDevice.objects.get(user=userProfile, registration_id=token)
        except GCMDevice.DoesNotExist:
            device = GCMDevice.objects.create(user=userProfile, registration_id=token)
    else:
        return errorResponse("platform must be ios or android")

    response['success'] = True

    return HttpResponse(json.dumps(response))

