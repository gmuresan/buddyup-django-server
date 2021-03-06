import datetime
import pdb
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
import facebook
from notifications.app_notifications import createFriendJoinedNotification
from userprofile.models import UserProfile

FACEBOOK_DATETIME_FORMAT = "%Y-%m-%dT%H:%M"


class FacebookProfile:
    def __init__(self, userProfile, facebookAuthKey):
        self.userProfile = userProfile
        self.graph = facebook.GraphAPI(facebookAuthKey)

    def shareStatus(self, status, request=None):
        endTime = status.expires.strftime(FACEBOOK_DATETIME_FORMAT)

        params = {'end_time': endTime, 'fb:explicitly_shared': True}

        if request is not None:
            params['buddyup_status'] = request.build_absolute_uri(reverse('fbObjectStatus', args=(status.id,)))
        else:
            params['buddyup_status'] = 'http://www.buddyup.mobi/api/fb_object/status/228/'

        if len(status.groups.all()) > 0:
            userIds = status.getStatusAudienceUsers().values_list('facebookUID', flat='true')
            facebookIds = ",".join(userIds)
            params['privacy'] = {'value': 'CUSTOM', 'allow': facebookIds.encode("utf-8")}

        response = self.graph.request("me/buddyupapp:post", None, params)

        return response

    @classmethod
    def getFacebookUserFromAuthKey(cls, facebookAuthKey, device):
        graph = facebook.GraphAPI(facebookAuthKey)
        profile = graph.get_object("me")
        facebookId = profile['id']

        if 'email' in profile:
            username = str(profile['email'])
        elif not 'email' in profile:
            if 'first_name' in profile and 'last_name' in profile:
                username = str(profile['first_name']) + str(profile['last_name'])
            elif 'name' in profile:
                username = str(profile['name'])
            elif 'first_name' in profile:
                username = str(profile['first_name'])
            elif 'last_name' in profile:
                username = str(profile['last_name'])

        newUser = False
        try:
            userProfile = UserProfile.objects.get(facebookUID=facebookId)
        except UserProfile.DoesNotExist:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                username = username[:30]
                firstName = str(profile['first_name'])[:30]
                lastName = str(profile['last_name'])[:30]
                user = User(username=username, first_name=profile['first_name'],
                            last_name=profile['last_name'], password=0)
                if 'email' in profile:
                    user.email = str(profile['email'])
                else:
                    user.email = ''

                user.save()
                newUser = True

            userProfile = UserProfile(facebookUID=facebookId, user=user, device=device)
            userProfile.save()

        return FacebookProfile(userProfile, facebookAuthKey), newUser

    def getFacebookFriends(self):
        appFriends = self.graph.request("me/friends", {'fields': 'installed'})

        friends = []
        # Check all facebook friends to see if they are a buddyup friend
        for appFriend in appFriends['data']:

            if 'installed' in appFriend and appFriend['installed'] is True:
                friendFBID = appFriend['id']

                try:
                    friendProfile = UserProfile.objects.get(facebookUID=friendFBID)

                    # Add the user to the friends list if they arent a friend already
                    if friendProfile not in self.userProfile.friends.all():
                        self.userProfile.friends.add(friendProfile)
                        self.userProfile.save()
                    if self.userProfile not in friendProfile.friends.all():
                        friendProfile.friends.add(self.userProfile)
                        friendProfile.save()

                    friends.append(friendProfile)

                except UserProfile.DoesNotExist:
                    pass

        return friends
