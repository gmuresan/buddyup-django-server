import json
from django.contrib.auth.models import User
from django.http import HttpResponse
import facebook
from userprofile.models import UserProfile


def facebookRegister(request, facebookAuthKey):
    response = dict()

    try:
        graph = facebook.GraphAPI(facebookAuthKey)
        profile = graph.get_object("me")
    except facebook.GraphAPIError:
        response['error'] = "Invalid Facebook AUTH Key"
        response['success'] = False
        return HttpResponse(json.dumps(response))

    facebookId = profile['id']


    try:
        userProfile = UserProfile.objects.get(facebookUID=facebookId)
    except UserProfile.DoesNotExist:
        user = User(username=profile['email'], first_name=profile['first_name'], last_name=profile['last_name'],
                    password=0)
        user.save()

        userProfile = UserProfile(facebookUID=facebookId, user=user)
        userProfile.save()

    response['friends'] = []
    appFriends = graph.request("me/friends", {'fields': 'installed'})
    for appFriend in appFriends['data']:

        if 'installed' in appFriend and appFriend['installed'] is True:
            friendFBID = appFriend['id']

            try:
                friendProfile = UserProfile.objects.get(facebookUID=friendFBID)
                friendData = {'id': friendProfile.id, 'firstName': friendProfile.user.first_name, 'lastName': friendProfile.user.last_name}
                if friendProfile in userProfile.blockedFriends.all():
                    friendData['blocked'] = True
            except UserProfile.DoesNotExist:
                pass

            response['friends'].append(friendData)

    response['success'] = True
    response['firstName'] = userProfile.user.first_name
    response['lastName'] = userProfile.user.last_name
    response['id'] = userProfile.id

    return HttpResponse(json.dumps(response))

