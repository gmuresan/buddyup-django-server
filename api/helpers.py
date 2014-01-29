from datetime import datetime, timedelta
import pdb
import urllib
import urllib2
from buddyup import settings
from status.models import Poke

DATETIME_FORMAT = '%m-%d-%Y %H:%M:%S'  # 06-01-2013 13:12
MICROSECOND_DATETIME_FORMAT = '%m-%d-%Y %H:%M:%S.%f'


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

    #pdb.set_trace()
    groupData['groupname'] = group.name
    groupData['groupid'] = group.id

    memberIds = group.members.values_list('id', flat=True)
    groupData['userids'] = map(int, memberIds)

    fbMemberIds = group.fbMembers.values_list('facebookUID', flat=True)
    groupData['userids'].extend(map(lambda fbId: "fb" + fbId, fbMemberIds))

    return groupData


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
        else:
            msgs = msgs.filter(created__gt=(convo.lastActivity - timedelta(days=3)))

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

    return chats


def getNewPokesData(userProfile, since=None):
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