from datetime import datetime
import urllib
import urllib2
import pytz
from buddyup import settings
from status.models import Status, Poke

DATETIME_FORMAT = '%m-%d-%Y %H:%M:%S'  # 06-01-2013 13:12
MICROSECOND_DATETIME_FORMAT = '%m-%d-%Y %H:%M:%S.%f'


def createStatusJsonObject(status):
    statusData = dict()

    statusData['statusid'] = status.id
    statusData['userid'] = status.user_id
    statusData['text'] = status.text
    statusData['datecreated'] = status.date.strftime(DATETIME_FORMAT)
    statusData['dateexpires'] = status.expires.strftime(DATETIME_FORMAT)
    statusData['datestarts'] = status.starts.strftime(DATETIME_FORMAT)

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


def createFriendJsonObject(friend, blocked, user):
    friendData = {'userid': friend.id, 'firstname': friend.user.first_name,
                  'lastname': friend.user.last_name, 'blocked': False, 'facebookid': friend.facebookUID}

    if blocked:
        friendData['blocked'] = True

    lastPoke = Poke.objects.filter(sender=user, recipient=friend)
    if lastPoke:
        lastPoke = lastPoke.latest()
        lastPokeTime = lastPoke.created.strftime(DATETIME_FORMAT)
        friendData['lastpoketime'] = lastPokeTime

    return friendData


def createGroupJsonObject(group):
    groupData = dict()

    groupData['groupname'] = group.name
    groupData['groupid'] = group.id

    memberIds = group.members.values_list('id', flat=True)
    groupData['userids'] = map(int, memberIds)

    return groupData


def getNewStatusesJsonResponse(userProfile, since):
    friends = userProfile.getUnblockedFriends()

    # TODO: add expires date filter to status query
    #statuses = Status.objects.filter(user__in=friends, expires__gt=now)
    statuses = Status.objects.filter(user__in=friends)

    if since is not None:
        statuses = statuses.filter(date__gt=since)

    statuses = list(statuses)
    newSince = datetime.utcnow()

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

    return statusesData, newSince


def getMyStatusesJsonResponse(userProfile):

    myStatuses = userProfile.statuses.filter(user=userProfile).order_by('-expires')

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


def getNewChatsData(userProfile, since=None):

    conversations = userProfile.conversations.all()

    if since is not None:
        conversations = conversations.filter(lastActivity__gt=since)

    conversations = list(conversations)
    newSince = datetime.utcnow()

    chats = []
    for convo in conversations:

        membersData = []
        members = convo.members.all()
        for member in members:
            memberData = dict()
            memberData['userid'] = member.id
            memberData['facebookid'] = member.facebookUID
            memberData['firstname'] = member.user.first_name
            memberData['lastname'] = member.user.last_name
            membersData.append(memberData)

        msgs = convo.messages.all()
        if since is not None:
            msgs = msgs.filter(created__gt=since)

        messagesData = []
        for message in msgs:
            messageData = dict()
            messageData['messageid'] = message.id
            messageData['date'] = message.created.strftime(DATETIME_FORMAT)
            messageData['text'] = message.text
            messageData['userid'] = message.user.id

            messagesData.append(messageData)

        chatData = dict()
        chatData['chatid'] = convo.id
        chatData['lastactivity'] = convo.lastActivity.strftime(DATETIME_FORMAT)
        chatData['messages'] = messagesData
        chatData['members'] = membersData

        chats.append(chatData)

    return chats, newSince


def getNewPokesData(userProfile, since):

    pokes = userProfile.receivedPokes.all()

    if since is not None:
        pokes = pokes.filter(created__gt=since)

    pokesData = []
    for poke in pokes:
        pokesData.append(poke.sender.id)

    return pokesData


def getSettingsData(userProfile):

    settings = userProfile.settings.all()

    settingsData = dict()
    for setting in settings:
        settingsData[setting.key] = setting.value

    return settingsData


def getFacebookAppAccessToken():
    response = urllib2.urlopen("https://graph.facebook.com/" + 'oauth/access_token' + "?" +
                               urllib.urlencode({'client_id': settings.FACEBOOK_APP_ID,
                                                 'client_secret': settings.FACEBOOK_APP_SECRET,
                                                 'grant_type': 'client_credentials'}), None)

    accessToken = str(response.read()).split('=')[1]

    return accessToken