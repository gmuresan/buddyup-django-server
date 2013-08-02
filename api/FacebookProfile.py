from django.contrib.auth.models import User
import facebook
from userprofile.models import UserProfile


class FacebookProfile:
    def __init__(self, userProfile, facebookAuthKey):
        self.userProfile = userProfile
        self.graph = facebook.GraphAPI(facebookAuthKey)


    @classmethod
    def getFacebookUserFromAuthKey(cls, facebookAuthKey, device):
        graph = facebook.GraphAPI(facebookAuthKey)
        profile = graph.get_object("me")

        facebookId = profile['id']

        try:
            userProfile = UserProfile.objects.get(facebookUID=facebookId)
        except UserProfile.DoesNotExist:
            user = User(username=profile['email'], email=profile['email'], first_name=profile['first_name'],
                        last_name=profile['last_name'],
                        password=0)
            user.save()

            userProfile = UserProfile(facebookUID=facebookId, user=user, device=device)
            userProfile.save()

        return FacebookProfile(userProfile, facebookAuthKey)

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
