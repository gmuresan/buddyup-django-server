from datetime import datetime
from django.contrib.auth.models import User
from django.contrib.gis.measure import D
import facebook
import pytz
from status.models import Status
from userprofile.models import UserProfile

DATETIME_FORMAT = '%m-%d-%Y %H:%M'  # 06-01-2013 13:12


def createStatusJsonObject(status):
    statusData = dict()

    statusData['statusid'] = status.id
    statusData['userid'] = status.user_id
    statusData['text'] = status.text
    statusData['datecreated'] = status.date.strftime(DATETIME_FORMAT)
    statusData['dateexpires'] = status.expires.strftime(DATETIME_FORMAT)

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


def createFriendJsonObject(friend, blocked):
    friendData = {'userid': friend.id, 'firstname': friend.user.first_name,
                  'lastname': friend.user.last_name, 'blocked': False, 'facebookid': friend.facebookUID}

    if blocked:
        friendData['blocked'] = True

    return friendData


def createGroupJsonObject(group):
    groupData = dict()

    groupData['groupname'] = group.name
    groupData['groupid'] = group.id

    memberIds = group.members.values_list('id', flat=True)
    groupData['userids'] = map(int, memberIds)

    return groupData


def getNewStatusesJsonResponse(userProfile, since, point, distance=5):
    now = datetime.utcnow().replace(tzinfo=pytz.utc)
    friends = userProfile.getUnblockedFriends()

    # TODO: add expires date filter to status query
    #statuses = Status.objects.filter(user__in=friends, expires__gt=now)
    statuses = Status.objects.filter(user__in=friends)

    if since is not None:
        statuses = statuses.filter(date__gt=since)
    if point is not None:
        statuses = statuses.filter(location__point__distance_lte=(point, D(mi=int(distance))))

    statuses = list(statuses)
    userProfile.lastGetStatusTime = datetime.utcnow()
    userProfile.save()

    statusesData = []
    for status in statuses:

        # If the status is only broadcast to certain groups,
        # Check if the current user is in one of those groups
        if status.groups.count():
            inGroup = False
            for group in status.groups.all():
                if userProfile in group.members.all():
                    inGroup = True
                    break

            if not inGroup:
                continue

        statusData = createStatusJsonObject(status)
        statusesData.append(statusData)

    return statusesData


def getMyStatusesJsonResponse(userProfile):

    now = datetime.utcnow().replace(tzinfo=pytz.utc)
    myStatuses = Status.objects.filter(user=userProfile, expires__gt=now)

    myStatusesData = []
    for status in myStatuses:
        statusData = createStatusJsonObject(status)
        myStatusesData.append(statusData)

    return myStatusesData


def getMyGroupsJsonResponse(userProfile):
    groups = userProfile.groups.all()
    groupsData = list()

    for group in groups:
        groupData = createGroupJsonObject(group)
        groupsData.append(groupData)

    return groupsData


def getNewMessagesJsonResponse(userProfile, since=None):

    conversations = userProfile.conversations.all()

    if since is not None:
        conversations = conversations.filter(lastActivity__gt=since)

    conversations = list(conversations)
    userProfile.lastGetMessagesTime = datetime.utcnow()
    userProfile.save()

    messages = []
    for convo in conversations:
        msgs = convo.messages.all()
        if since is not None:
            msgs = msgs.filter(created__gt=since)
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

    return messagesData












