from datetime import datetime, timedelta
import pdb
import urllib
import urllib2
from buddyup import settings
from status.models import Poke

DATETIME_FORMAT = '%m-%d-%Y %H:%M:%S'  # 06-01-2013 13:12:11
MICROSECOND_DATETIME_FORMAT = '%m-%d-%Y %H:%M:%S.%f'


def createGroupJsonObject(group):
    groupData = dict()

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