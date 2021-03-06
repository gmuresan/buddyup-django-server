import os
import pdb
import binascii
import random
from django.contrib.auth.models import User
import facebook
from api.FacebookProfile import FacebookProfile
from api.helpers import *
from api.views import *
from chat.helpers import getNewChatsData
from notifications.app_notifications import createFriendJoinedNotification
from notifications.helpers import getNotificationsJson
from notifications.models import GCMDevice, APNSDevice
from status.helpers import getNewStatusesJsonResponse, getMyStatusesJsonResponse
from userprofile.helpers import getUserProfileDetailsJson
from userprofile.models import UserProfile, Group, Feedback, Setting, FacebookUser
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def facebookLogin(request):
    """

    :param request:
    :return:
    """
    response = dict()

    device = request.REQUEST['device']
    facebookAuthKey = request.REQUEST['fbauthkey']
    lat = request.REQUEST.get('lat', None)
    lng = request.REQUEST.get('lng', None)

    if device != 'ios' and device != 'android':
        return errorResponse('Invalid device: ' + device)

    try:
        facebookProfile, newUser = FacebookProfile.getFacebookUserFromAuthKey(facebookAuthKey, device)
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

        friendData = getUserProfileDetailsJson(friend)
        response['friends'].append(friendData)

    # Check all buddyup friends and add them if they weren't already included in facebook friends check
    friends = userProfile.friends.all()
    for friend in friends:
        if friend not in facebookFriends:
            blocked = False
            if friend in blockedFriends:
                blocked = True

            friendData = getUserProfileDetailsJson(friend)
            response['friends'].append(friendData)

    statusesResponse, newSince = getNewStatusesJsonResponse(userProfile, None, lat, lng)
    myStatusesResponse = getMyStatusesJsonResponse(userProfile)

    settings = getSettingsData(userProfile)

    newSince = datetime.now().strftime(MICROSECOND_DATETIME_FORMAT)
    notifications = getNotificationsJson(userProfile)
    chatData = getNewChatsData(userProfile)

    if newUser:
        createFriendJoinedNotification(userProfile)
        Group.objects.create(name="Favorites", user=userProfile)

    groupsData = getMyGroupsJsonResponse(userProfile)


    response['success'] = True
    response['firstname'] = userProfile.user.first_name
    response['lastname'] = userProfile.user.last_name
    response['userid'] = userProfile.id
    response['facebookid'] = userProfile.facebookUID
    response['statuses'] = statusesResponse
    response['groups'] = groupsData
    response['mystatuses'] = myStatusesResponse
    response['chats'] = chatData
    response['newsince'] = newSince
    response['settings'] = settings
    response['notifications'] = notifications
    response['favoritesnotifications'] = userProfile.favoritesNotifications

    return HttpResponse(json.dumps(response))


@csrf_exempt
def refreshFacebookFriends(request):
    response = dict()

    userid = request.REQUEST.get('userid', None)
    accessToken = request.REQUEST.get('accesstoken')

    try:
        userProfile = UserProfile.getUser(userid)
    except UserProfile.DoesNotExist:
        return errorResponse("Invalid user id")

    facebookProfile = FacebookProfile(userProfile, accessToken)
    friends = facebookProfile.getFacebookFriends()

    response['users'] = []
    for friend in friends:
        response['users'].append(getUserProfileDetailsJson(friend))

    response['success'] = True

    return HttpResponse(json.dumps(response))


@csrf_exempt
def getUserDetails(request):
    response = dict()

    userid = request.REQUEST.get('userid', None)
    userids = request.REQUEST.get('userids', '[]')
    userids = json.loads(userids)

    if userid is None and len(userids) == 0:
        return errorResponse("Need to supply userid or userids")

    users = list()

    if userid is not None:
        try:
            userProfile = UserProfile.getUser(userid)
        except UserProfile.DoesNotExist:
            return errorResponse("Invalid user id")

        response['firstname'] = userProfile.user.first_name
        response['lastname'] = userProfile.user.last_name
        response['facebookid'] = userProfile.facebookUID
        response['userid'] = userProfile.id

    elif len(userids) > 0:
        for userid in userids:
            try:
                userProfile = UserProfile.getUser(userid)
            except UserProfile.DoesNotExist:
                return errorResponse("Invalid user id")

            userData = dict()
            userData['firstname'] = userProfile.user.first_name
            userData['lastname'] = userProfile.user.last_name
            userData['facebookid'] = userProfile.facebookUID
            userData['userid'] = userProfile.id

            users.append(userData)

        response['users'] = users

    response['success'] = True
    return HttpResponse(json.dumps(response))


@csrf_exempt
def createGroup(request):
    response = dict()

    userid = request.REQUEST['userid']
    groupName = request.REQUEST['groupname']

    try:
        userProfile = UserProfile.getUser(userid)
    except UserProfile.DoesNotExist:
        return errorResponse("Invalid user id")

    group, created = Group.objects.get_or_create(name=groupName, user=userProfile)

    response['success'] = True
    response['groupid'] = group.id

    return HttpResponse(json.dumps(response))


@csrf_exempt
def deleteGroup(request):
    response = dict()

    userid = request.REQUEST['userid']
    groupid = request.REQUEST['groupid']

    try:
        userProfile = UserProfile.getUser(userid)
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
        userProfile = UserProfile.getUser(userid)
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
        userProfile = UserProfile.getUser(userid)
    except UserProfile.DoesNotExist:
        return errorResponse("Invalid user id")

    if friendid[:2] == 'fb':
        friendid = friendid[2:]
        if friendid:
            try:
                friendProfile = UserProfile.objects.get(facebookUID=friendid)
            except UserProfile.DoesNotExist:
                try:
                    friendProfile = FacebookUser.objects.get(facebookUID=friendid)
                except FacebookUser.DoesNotExist:
                    friendProfile = FacebookUser.objects.create(facebookUID=friendid)
    else:
        try:
            friendProfile = UserProfile.getUser(friendid)
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
        userProfile = UserProfile.getUser(userid)
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
            friend = UserProfile.getUser(friendid)
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
        userProfile = UserProfile.getUser(userid)
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
        if friendid:
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
            friend = UserProfile.getUser(friendid)
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
        userProfile = UserProfile.getUser(userid)
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
        userProfile = UserProfile.getUser(userid)
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
    group.fbMembers.clear()

    for friendid in friendids:
        friendid = str(friendid)
        if friendid[:2] == 'fb':
            friendid = friendid[2:]
            if friendid:
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
                friend = UserProfile.getUser(friendid)
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
        userProfile = UserProfile.getUser(userid)
    except UserProfile.DoesNotExist:
        return errorResponse("Invalid user id")

    # blockedFriends = userProfile.blockedFriends.all()
    friendsData = list()

    for friend in userProfile.friends.all():
        # blocked = False
        # if friend in blockedFriends:
        #     blocked = True
        friendData = getUserProfileDetailsJson(friend)
        friendsData.append(friendData)

    response['success'] = True
    response['users'] = friendsData

    return HttpResponse(json.dumps(response))


@csrf_exempt
def blockFriend(request):
    response = dict()

    userid = request.REQUEST['userid']
    friendid = request.REQUEST['friendid']

    try:
        userProfile = UserProfile.getUser(userid)
    except UserProfile.DoesNotExist:
        return errorResponse("Invalid user id")

    try:
        friendProfile = UserProfile.getUser(friendid)
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
        userProfile = UserProfile.getUser(userid)
    except UserProfile.DoesNotExist:
        return errorResponse("Invalid user id")

    try:
        friendProfile = UserProfile.getUser(friendid)
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
        userProfile = UserProfile.getUser(userid)
    except UserProfile.DoesNotExist:
        return errorResponse("Invalid user id")

    Feedback.objects.create(user=userProfile, text=text)

    response['success'] = True

    return HttpResponse(json.dumps(response))


@csrf_exempt
def getNewData(request):
    response = dict()

    userid = request.REQUEST['userid']
    since = request.REQUEST.get('since', None)
    if since:
        since = datetime.strptime(since, MICROSECOND_DATETIME_FORMAT)

    try:
        userProfile = UserProfile.getUser(userid)
    except UserProfile.DoesNotExist:
        return errorResponse("Invalid user id")

    newSince = datetime.now().strftime(MICROSECOND_DATETIME_FORMAT)

    pokes = getNewPokesData(userProfile, since)
    chats = getNewChatsData(userProfile, since)
    notifications = getNotificationsJson(userProfile, since)

    response['chats'] = chats
    response['newsince'] = newSince
    response['notifications'] = notifications
    response['success'] = True
    response['pokes'] = pokes

    return HttpResponse(json.dumps(response))


@csrf_exempt
def goOffline(request):
    response = dict()

    userid = request.REQUEST['userid']

    try:
        userProfile = UserProfile.getUser(userid)
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
        userProfile = UserProfile.getUser(userid)
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
        userProfile = UserProfile.getUser(userid)
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
        userProfile = UserProfile.getUser(userid)
    except UserProfile.DoesNotExist:
        return errorResponse("User does not exist")

    if platform == 'ios':
        try:
            device = APNSDevice.objects.get(registration_id=token)
            device.user = userProfile
            device.save()
        except APNSDevice.DoesNotExist:
            device = APNSDevice.objects.create(user=userProfile, registration_id=token)
    elif platform == 'android':
        try:
            device = GCMDevice.objects.get(registration_id=token)
            device.user = userProfile
            device.save()
        except GCMDevice.DoesNotExist:
            device = GCMDevice.objects.create(user=userProfile, registration_id=token)
    else:
        return errorResponse("platform must be ios or android")

    response['success'] = True

    return HttpResponse(json.dumps(response))


@csrf_exempt
def setFavoritesNotifications(request):
    userId = request.REQUEST['userid']
    value = request.REQUEST['value']

    try:
        userProfile = UserProfile.getUser(userId)
    except UserProfile.DoesNotExist:
        return errorResponse("User does not exist")

    if not value or value == 'False' or value == 'false':
        userProfile.favoritesNotifications = False
    else:
        userProfile.favoritesNotifications = True
    userProfile.save()

    response = dict()
    response['success'] = True

    return HttpResponse(json.dumps(response))


@csrf_exempt
def createTestUser(request):
    numberOfFriends = request.REQUEST['numfriends']
    response = dict()

    name = "test%d" % random.randint(1, 10000000)
    email = "%s@buddyup.im" % name
    firstName = name
    lastName = name
    user = User(username=email, email=email, first_name=firstName,
                last_name=lastName, password=0)

    user.save()
    userProfile = UserProfile(user=user, device='ios')
    userProfile.save()

    numberOfFriends = int(numberOfFriends)
    friends = UserProfile.objects.all().order_by('-id')[:numberOfFriends]

    blockedFriends = userProfile.blockedFriends.all()
    for friend in friends:
        if friend not in friend.friends.all():
            friend.friends.add(userProfile)
            userProfile.friends.add(friend)

    friends = userProfile.friends.all()
    response['friends'] = list()
    for friend in friends:
        friendData = getUserProfileDetailsJson(friend)
        response['friends'].append(friendData)

    statusesResponse, newSince = getNewStatusesJsonResponse(userProfile, None, None, None)
    myStatusesResponse = getMyStatusesJsonResponse(userProfile)
    groupsData = getMyGroupsJsonResponse(userProfile)

    buddyupSettings = getSettingsData(userProfile)

    newSince = datetime.now().strftime(MICROSECOND_DATETIME_FORMAT)
    notifications = getNotificationsJson(userProfile)
    chatData = getNewChatsData(userProfile)

    response['success'] = True
    response['firstname'] = userProfile.user.first_name
    response['lastname'] = userProfile.user.last_name
    response['userid'] = userProfile.id
    response['facebookid'] = userProfile.facebookUID
    response['statuses'] = statusesResponse
    response['groups'] = groupsData
    response['mystatuses'] = myStatusesResponse
    response['chats'] = chatData
    response['newsince'] = newSince
    response['settings'] = buddyupSettings
    response['notifications'] = notifications
    response['favoritesnotifications'] = userProfile.favoritesNotifications

    return HttpResponse(json.dumps(response))
