from datetime import datetime, timedelta
import json
import pdb
from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from django.core.urlresolvers import reverse
import facebook
import pytz
from django.test import TestCase, Client, LiveServerTestCase
from api import helpers
from api.FacebookProfile import FacebookProfile
from api.helpers import DATETIME_FORMAT, MICROSECOND_DATETIME_FORMAT, loadJson
from buddyup import settings
from chat.models import Conversation, Message
from notifications.models import GCMDevice, APNSDevice, Notification
from notifications.push_notifications import sendFavoritesStatusPushNotification, sendChatNotifications, \
    sendAttendingStatusPushNotification, sendInvitedToStatusNotification, sendDeleteStatusNotfication, \
    sendStatusMessageNotification, sendEditStatusNotification
from status.helpers import createLocationJson
from status.models import Status, Poke, Location, StatusMessage, TimeSuggestion, LocationSuggestion
from userprofile.models import UserProfile, Group, Setting, FacebookUser
from userprofile.helpers import getUserProfileDetailsJson

FB_TEST_USER_1_ID = "100007243621022"
FB_TEST_USER_2_ID = "100007247311000"
FB_TEST_USER_3_ID = "100007237111164"
FB_TEST_USER_4_ID = "100007225201630"


def performFacebookRegister(accessToken):
    client = Client()

    fb, newUser = FacebookProfile.getFacebookUserFromAuthKey(accessToken, 'android')
    return fb.userProfile


class FacebookRegisterTest(TestCase):
    def setUp(self):
        self.authKey = 'CAACBZAKw2g0ABAKsEUXw0tkwZBy2dsRXx8kh3GxGGlD9h3tlr2nlqTJRguVqWczePNXIAVIw0hG7tud6ZA97hqF4hFbqZBmm9iROwrMskXO4ZCSrSFeLWOVpPbHmMBBcrHS57yTOfPJauGSn6ImfZBlKP8Q0lDBKYzIRLvTBpwZC6ImU6Em0daD97avmfvX3H4ZD'
        self.firstName = 'George'
        self.lastName = 'Muresan'

    def testRegister(self):
        print("Register")
        client = Client()

        response = client.post(reverse('facebookLoginAPI'), {
            'fbauthkey': self.authKey,
            'device': 'android',
            'lat': 42.151515,
            'lng': -87.498989
        })
        response = loadJson(response.content)
        self.assertEqual(response['success'], True)
        self.assertNotIn('error', response)
        self.assertEqual(response['firstname'], self.firstName)
        self.assertEqual(response['lastname'], self.lastName)

        userProfile = UserProfile.objects.get(pk=response['userid'])
        self.assertEqual(userProfile.user.first_name, self.firstName)
        self.assertEqual(userProfile.user.last_name, self.lastName)

        try:
            group = Group.object.get(user=userProfile, name="Favorites")
        except Group.DoesNotExist:
            self.assertTrue(False)

    def testFacebookLoginWithFriends(self):
        print("FacebookLoginWithFriends")
        client = Client()

        user = User.objects.create(username='user1', password='0', email='user1', first_name='first', last_name='last')
        userprofile = UserProfile.objects.create(user=user)

        response = client.post(reverse('facebookLoginAPI'), {
            'fbauthkey': self.authKey,
            'device': 'android',
            'lat': 42.151515,
            'lng': -87.498989
        })
        response = loadJson(response.content)

        self.assertEqual(response['success'], True)
        self.assertIn('userid', response)

        myProfile = UserProfile.objects.get(pk=response['userid'])
        myProfile.friends.add(userprofile)
        myProfile.save()
        userprofile.friends.add(myProfile)
        userprofile.save()

        response = client.post(reverse('facebookLoginAPI'), {
            'fbauthkey': self.authKey,
            'device': 'android'
        })
        response = loadJson(response.content)

        userprofileFriendData = {'userid': userprofile.id, 'firstname': user.first_name, 'lastname': user.last_name,
                                 'blocked': False}
        self.assertNotEqual(len(response['friends']), 0)
        for key, val in userprofileFriendData.items():
            self.assertEqual(val, userprofileFriendData[key])

    def testFacebookLoginWithAllData(self):
        print("FacebookLoginWithAllData")
        client = Client()

        response = client.post(reverse('facebookLoginAPI'), {
            'fbauthkey': self.authKey,
            'device': 'android',
            'lat': 42.151515,
            'lng': -87.498989
        })
        response = loadJson(response.content)

        self.assertTrue(response['success'])
        userid = response['userid']
        userProfile = UserProfile.objects.get(pk=userid)

        friend = User.objects.create(username='friend', password='0', email='friend')
        friendProfile = UserProfile.objects.create(user=friend)

        userProfile.friends.add(friendProfile)
        friendProfile.friends.add(userProfile)

        group = Group.objects.create(name='group1', user=userProfile)
        group.members.add(friendProfile)
        group.save()

        lat = 42.341560
        lng = -83.501783
        address = '46894 spinning wheel'
        city = 'canton'
        state = 'MI'
        venue = "My house"
        expirationDate = datetime.utcnow() + timedelta(hours=1)

        location = Location.objects.create(lng=lng, lat=lat, point=Point(lng, lat), city=city, state=state, venue=venue,
                                           address=address)

        friendStatus = Status.objects.create(user=friendProfile, expires=expirationDate, text='Hang out1',
                                             location=location)

        myStatus = Status.objects.create(user=userProfile, expires=expirationDate, text='mystatus', location=location)

        response = client.post(reverse('facebookLoginAPI'), {
            'fbauthkey': self.authKey,
            'device': 'android'
        })

        response = loadJson(response.content)

        self.assertTrue(response['success'])
        self.assertEqual(response['statuses'][0]['statusid'], friendStatus.id)
        self.assertEqual(response['groups'][0]['groupid'], group.id)
        self.assertEqual(response['mystatuses'][0]['statusid'], myStatus.id)
        self.assertEqual(response['friends'][0]['userid'], friendProfile.id)
        self.assertIn('chats', response)
        self.assertEqual(response['favoritesnotifications'], True)

    def testGetSettingsOnLogin(self):
        print("FacebookLoginWithSettings")
        client = Client()

        response = client.post(reverse('facebookLoginAPI'), {
            'fbauthkey': self.authKey,
            'device': 'android',
            'lat': 42.151515,
            'lng': -87.498989
        })
        response = loadJson(response.content)

        self.assertTrue(response['success'])

        user = UserProfile.objects.get(pk=response['userid'])

        client.post(reverse('setSettingAPI'), {
            'userid': user.id,
            'key': 'statusradius',
            'value': 'value1'
        })

        client.post(reverse('setSettingAPI'), {
            'userid': user.id,
            'key': 'imboredtext',
            'value': 'value2'
        })

        response = client.post(reverse('facebookLoginAPI'), {
            'fbauthkey': self.authKey,
            'device': 'android'
        })
        response = loadJson(response.content)

        self.assertTrue(response['success'])
        self.assertEqual(len(response['settings']), 2)
        setting1 = response['settings']['statusradius']
        setting2 = response['settings']['imboredtext']

        self.assertEqual(setting1, 'value1')
        self.assertEqual(setting2, 'value2')


class StatusMessageTests(TestCase):
    def setUp(self):
        self.local = pytz.timezone("US/Eastern")
        self.utc = pytz.timezone("UTC")

        user1 = User.objects.create(username='user1', password='0', email='user1')
        self.user = UserProfile.objects.create(user=user1)

        friend1 = User.objects.create(username='friend1', password='0', email='friend1')
        self.friend1 = UserProfile.objects.create(user=friend1)

        friend2 = User.objects.create(username='friend2', password='0', email='friend2')
        self.friend2 = UserProfile.objects.create(user=friend2)

        self.group1 = Group.objects.create(name="group1", user=self.user)
        self.group1.members.add(self.friend1)
        self.group1.members.add(self.friend2)
        self.group1.save()

        self.group2 = Group.objects.create(name="group2", user=self.user)
        self.group2.members.add(self.friend1)
        self.group2.save()

        self.text = "Hangout at my house"

        self.expires = self.utc.localize(datetime(2013, 5, 1))

        self.lng = 42.341560
        self.lat = -83.501783
        self.address = '46894 spinning wheel'
        self.city = 'canton'
        self.state = 'MI'
        self.venue = "My house"
        self.location = {'lat': self.lat, 'lng': self.lng, 'address': self.address, 'state': self.state,
                         'city': self.city, 'venue': self.venue}


    def testPostStatusMessage(self):
        print("Post Status Message")
        client = Client()

        status = Status.objects.create(user=self.user, text=self.text, expires=self.expires)

        response = client.post(reverse('postStatusMessageAPI'), {
            'userid': self.user.id,
            'statusid': status.id,
            'text': self.text
        })

        response = loadJson(response.content)

        self.assertTrue(response['success'])

        messages = status.messages.all()

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].text, self.text)
        self.assertEqual(len(response['messages']), 1)

        messageId = response['messages'][0]['messageid']

        message = StatusMessage.objects.create(user=self.friend1, text='text', status=status)

        response = client.post(reverse('postStatusMessageAPI'), {
            'userid': self.user.id,
            'statusid': status.id,
            'text': 'text',
            'lastmessageid': messageId
        })

        response = loadJson(response.content)

        self.assertTrue(response['success'])
        self.assertEqual(len(response['messages']), 2)

    def testGetStatusDetails(self):
        print("Get Status Details")
        client = Client()

        fbId1 = "foijf09190fj19j"
        fbId2 = "asfafafsafsfafs"
        dateSuggested = datetime.utcnow() + timedelta(hours=2)
        locationSuggested = Location.objects.create(lat=80.0, lng=70.0, point=Point(70.0, 80.0), city="ann arbor",
                                                    state="mi", venue="some place")

        status = Status.objects.create(user=self.user, text=self.text, expires=self.expires)

        status.attending.add(self.friend1)
        status.invited.add(self.friend2)
        status.invited.add(self.friend1)

        fbUser1 = FacebookUser.objects.create(facebookUID=fbId1)
        fbUser2 = FacebookUser.objects.create(facebookUID=fbId2)

        status.fbInvited.add(fbUser1)
        status.fbInvited.add(fbUser2)
        status.fbAttending.add(fbUser1)

        timeSuggestion = TimeSuggestion.objects.create(user=self.friend2, status=status, dateSuggested=dateSuggested)
        status.timeSuggestions.add(timeSuggestion)
        locationSuggestion = LocationSuggestion.objects.create(user=self.friend1, status=status,
                                                               location=locationSuggested)
        status.locationSuggestions.add(locationSuggestion)

        response = client.post(reverse('postStatusMessageAPI'), {
            'userid': self.user.id,
            'statusid': status.id,
            'text': self.text
        })

        response = client.post(reverse('getStatusDetailsAPI'), {
            'statusid': status.id
        })
        response = loadJson(response.content)

        self.assertTrue(response['success'])
        self.assertEqual(len(response['messages']), 1)
        message = response['messages'][0]
        self.assertEqual(message['userid'], self.user.id)
        self.assertEqual(message['text'], self.text)

        self.assertEqual(len(response['invited']), 4)
        self.assertEqual(len(response['attending']), 2)
        self.assertEqual(len(response['timesuggestions']), 1)
        self.assertEqual(len(response['locationsuggestions']), 1)

        self.assertIn("fb" + fbUser1.facebookUID, response['invited'])
        self.assertIn("fb" + fbUser2.facebookUID, response['invited'])
        self.assertIn("fb" + fbUser1.facebookUID, response['attending'])
        self.assertIn(self.friend2.id, response['invited'])
        self.assertIn(self.friend1.id, response['invited'])
        self.assertIn(self.friend1.id, response['attending'])

        timeSugg = response['timesuggestions'][0]
        locationSugg = response['locationsuggestions'][0]

        self.assertEqual(timeSugg['time'], timeSuggestion.dateSuggested.strftime(DATETIME_FORMAT))
        self.assertEqual(timeSugg['userid'], timeSuggestion.user.id)

        self.assertEqual(locationSugg['location'], createLocationJson(locationSuggestion.location))
        self.assertEqual(locationSugg['userid'], locationSuggestion.user.id)

        self.assertEqual(response['statusid'], status.id)
        self.assertEqual(response['text'], status.text)


class PostStatusTests(TestCase):
    def setUp(self):
        self.local = pytz.timezone("US/Eastern")
        self.utc = pytz.timezone("UTC")

        user1 = User.objects.create(username='user1', password='0', email='user1')
        self.user = UserProfile.objects.create(user=user1)

        friend1 = User.objects.create(username='friend1', password='0', email='friend1')
        self.friend1 = UserProfile.objects.create(user=friend1)

        friend2 = User.objects.create(username='friend2', password='0', email='friend2')
        self.friend2 = UserProfile.objects.create(user=friend2)

        self.group1 = Group.objects.create(name="group1", user=self.user)
        self.group1.members.add(self.friend1)
        self.group1.members.add(self.friend2)
        self.group1.save()

        self.group2 = Group.objects.create(name="group2", user=self.user)
        self.group2.members.add(self.friend1)
        self.group2.save()

        self.text = "Hangout at my house"

        self.expires = self.utc.localize(datetime(2013, 5, 1))

        self.lng = 42.341560
        self.lat = -83.501783
        self.address = '46894 spinning wheel'
        self.city = 'canton'
        self.state = 'MI'
        self.venue = "My house"
        self.location = {'lat': self.lat, 'lng': self.lng, 'address': self.address, 'state': self.state,
                         'city': self.city, 'venue': self.venue}

    def testPostNoLocation(self):
        print("PostNoLocation")
        client = Client()

        response = client.post(reverse('postStatusAPI'), {
            'userid': self.user.id,
            'expires': self.expires.strftime(DATETIME_FORMAT),
            'text': self.text,
            'type': 'sports',
            'imageorientation': 'd'
        })

        responseObj = loadJson(response.content)
        self.assertEqual(responseObj['success'], True)
        self.assertNotIn('error', responseObj)

        status = Status.objects.get(pk=responseObj['statusid'])

        self.assertEqual(status.user, self.user)
        #self.assertEqual(status.expires, self.expires)
        self.assertEqual(status.text, self.text)
        self.assertEqual(status.imageOrientation, 'd')

    def testPostWithLocation(self):
        print("PostWithLocation")
        client = Client()

        response = client.post(reverse('postStatusAPI'), {
            'userid': self.user.id,
            'expires': self.expires.strftime(DATETIME_FORMAT),
            'text': self.text,
            'location': json.dumps(self.location),
            'type': 'food',
            'visibility': 'friendsoffriends'
        })

        response = loadJson(response.content)

        status = Status.objects.get(pk=response['statusid'])

        self.assertEqual(status.location.lat, self.location['lat'])
        self.assertEqual(status.location.lng, self.location['lng'])
        self.assertEqual(status.location.city, self.location['city'])
        self.assertEqual(status.location.state, self.location['state'])
        self.assertEqual(status.location.address, self.location['address'])
        self.assertEqual(status.location.venue, self.location['venue'])

    def testPostWithGroups(self):
        print("PostWithGroups")
        client = Client()

        groupids = [self.group1.id, self.group2.id]

        response = client.post(reverse('postStatusAPI'), {
            'userid': self.user.id,
            'expires': self.expires.strftime(DATETIME_FORMAT),
            'text': self.text,
            'location': json.dumps(self.location),
            "groupids": json.dumps(groupids),
            'type': 'other',
            'visibility': 'public'
        })

        response = loadJson(response.content)

        status = Status.objects.get(pk=response['statusid'])

        self.assertTrue(response['success'])

        self.assertIn(self.group1, status.groups.all())
        self.assertIn(self.group1, status.groups.all())

    def testPostWithStartTime(self):
        print("PostWithStartTime")
        client = Client()

        response = client.post(reverse('postStatusAPI'), {
            'userid': self.user.id,
            'starts': self.expires.strftime(DATETIME_FORMAT),
            'text': self.text,
            'location': json.dumps(self.location),
            'visibility': 'friends'
        })

        response = loadJson(response.content)

        status = Status.objects.get(pk=response['statusid'])

        self.assertTrue(response['success'])

        self.assertEqual(self.expires.strftime(DATETIME_FORMAT), status.starts.strftime(DATETIME_FORMAT))

    def testPostCustomVisibility(self):
        print("Post Status Custom Visibility")
        client = Client()

        friends = [self.friend1.id, self.friend2.id]
        fbId1 = "1871409491024"
        fbId2 = "11807901980890"
        fbfriends = [fbId1, fbId2]
        allFriends = list(friends)
        for fbfriend in fbfriends:
            fbId = "fb{}".format(fbfriend)
            allFriends.append(fbId)

        response = client.post(reverse('postStatusAPI'), {
            'userid': self.user.id,
            'starts': self.expires.strftime(DATETIME_FORMAT),
            'text': self.text,
            'location': json.dumps(self.location),
            'visibility': 'custom',
            'visibilityfriends': json.dumps(allFriends),
        })

        response = loadJson(response.content)

        status = Status.objects.get(pk=response['statusid'])

        self.assertIn(self.friend2, status.friendsVisible.all())
        self.assertIn(self.friend1, status.friendsVisible.all())

        fbFriendsVisible = status.fbFriendsVisible.values_list('facebookUID', flat=True)
        self.assertIn(fbId1, fbFriendsVisible)
        self.assertIn(fbId2, fbFriendsVisible)

        self.assertTrue(response['success'])

    def testInviteUsersToStatus(self):
        print("Invite Users To Status")
        client = Client()
        friends = [self.friend1.id, self.friend2.id]
        fbfriends = ['asfafafsafs', '1u989h108f1f']
        allFriends = list(friends)
        for friend in fbfriends:
            allFriends.append("fb" + friend)

        response = client.post(reverse('postStatusAPI'), {
            'userid': self.user.id,
            'starts': self.expires.strftime(DATETIME_FORMAT),
            'text': self.text,
            'location': json.dumps(self.location),
            'visibility': 'friends'
        })
        response = loadJson(response.content)

        self.assertTrue(response['success'])
        statusId = response['statusid']

        response = client.post(reverse('inviteToStatusAPI'), {
            'userid': self.user.id,
            'statusid': response['statusid'],
            'friends': json.dumps(allFriends),
        })
        response = loadJson(response.content)

        self.assertTrue(response['success'])

        status = Status.objects.get(pk=statusId)

        invitedFriendIds = status.invited.values_list('id', flat=True)
        fbFriendIds = status.fbInvited.values_list('facebookUID', flat=True)

        for friendId in friends:
            self.assertIn(friendId, invitedFriendIds)

        for facebookId in fbfriends:
            self.assertIn(facebookId, fbFriendIds)

    def testStatusCaching(self):
        pass


class facebookShareStatusTests(TestCase):
    def setUp(self):
        fb = facebook.GraphAPI()
        appAccessToken = helpers.getFacebookAppAccessToken()
        testUsers = fb.request(settings.FACEBOOK_APP_ID + '/accounts/test-users',
                               {'access_token': str(appAccessToken), })
        testUsers = testUsers['data']
        for user in testUsers:

            if user['id'] == FB_TEST_USER_1_ID:
                self.accessTokenUser = user['access_token']
                continue

            if user['id'] == FB_TEST_USER_2_ID:
                self.accessTokenFriend1 = user['access_token']
                continue

            if user['id'] == FB_TEST_USER_3_ID:
                self.accessTokenFriend2 = user['access_token']
                continue

            if user['id'] == FB_TEST_USER_4_ID:
                self.accessTokenFriend3 = user['access_token']
                continue

        self.user = performFacebookRegister(self.accessTokenUser)
        self.friend1 = performFacebookRegister(self.accessTokenFriend1)
        self.friend2 = performFacebookRegister(self.accessTokenFriend2)
        self.friend3 = performFacebookRegister(self.accessTokenFriend3)

        self.group = Group.objects.create(user=self.user, name="group1")
        self.group.members.add(self.friend1)
        self.group.members.add(self.friend2)
        self.group.save()

        # def testShareStatusOnFacebook(self):
        #     client = Client()
        #
        #     text = "Hangout at my house"
        #
        #     expires = datetime.now(pytz.timezone("UTC"))
        #     expires = expires + timedelta(hours=1)
        #
        #     lng = 42.341560
        #     lat = -83.501783
        #     address = '46894 spinning wheel'
        #     city = 'canton'
        #     state = 'MI'
        #     venue = "My house"
        #     location = {'lat': lat, 'lng': lng, 'address': address, 'state': state,
        #                 'city': city, 'venue': venue}
        #
        #     response = client.post(reverse('postStatusAPI'), {
        #         'userid': self.user.id,
        #         'expires': expires.strftime(DATETIME_FORMAT),
        #         'text': text,
        #         'groupids': json.dumps([self.group.id]),
        #         'location': json.dumps(location)
        #     })
        #
        #     response = loadJson(response.content)
        #
        #     statusId = response['statusid']
        #     status = Status.objects.get(pk=statusId)
        #
        #     fbProfile = FacebookProfile(self.user, self.accessTokenUser)
        #     response = fbProfile.shareStatus(status)


class deleteStatusTest(TestCase):
    def setUp(self):
        user1 = User.objects.create(username='user1', password='0', email='user1')
        self.user1 = UserProfile.objects.create(user=user1)

        user2 = User.objects.create(username='user2', password='0', email='user2')
        self.user2 = UserProfile.objects.create(user=user2)

        self.lat = 42.341560
        self.lng = -83.501783
        self.address = '46894 spinning wheel'
        self.city = 'canton'
        self.state = 'MI'
        self.venue = "My house"
        self.expirationDate = datetime.utcnow() + timedelta(hours=1)

        self.location = Location.objects.create(lng=self.lng, lat=self.lat, point=Point(self.lng, self.lat),
                                                city=self.city, state=self.state, venue=self.venue)
        self.status1 = Status.objects.create(user=self.user1, expires=self.expirationDate, text='Hang out',
                                             location=self.location)
        self.status1Id = self.status1.id

        self.status2 = Status.objects.create(user=self.user1, expires=self.expirationDate, text='Hang out',
                                             location=self.location)
        self.status2Id = self.status2.id

    def testDeleteStatus(self):
        print("DeleteStatus")
        client = Client()

        response = client.post(reverse('deleteStatusAPI'), {
            'userid': self.user1.id,
            'statusid': self.status1Id
        })

        response = loadJson(response.content)

        self.assertTrue(response['success'])

        status = Status.objects.get(pk=self.status1Id)
        self.assertTrue(status.deleted)

    def testDeleteOtherUserStatus(self):
        print("DeleteOtherUserStatus")
        client = Client()

        Status.objects.get(pk=self.status1Id)

        response = client.post(reverse('deleteStatusAPI'), {
            'userid': self.user2.id,
            'statusid': self.status1Id
        })

        response = loadJson(response.content)

        self.assertFalse(response['success'])

        Status.objects.get(pk=self.status1Id)

    def testGoOffline(self):
        print("GoOffline")
        client = Client()

        response = client.post(reverse('goOfflineAPI'), {
            'userid': self.user1.id
        })
        response = loadJson(response.content)

        self.assertTrue(response['success'])

        status1 = Status.objects.get(pk=self.status1Id)
        status2 = Status.objects.get(pk=self.status2Id)

        now = datetime.utcnow()

        self.assertTrue(status1.expires < now)
        self.assertTrue(status2.expires < now)

    def testCancelStatus(self):
        print("CancelStatus")
        client = Client()

        response = client.post(reverse('cancelStatusAPI'), {
            'userid': self.user1.id,
            'statusid': self.status1Id
        })
        response = loadJson(response.content)

        status1 = Status.objects.get(pk=self.status1Id)
        status2 = Status.objects.get(pk=self.status2Id)
        now = datetime.utcnow()

        self.assertTrue(response['success'])
        self.assertTrue(status1.expires < now)
        self.assertFalse(status2.expires < now)

    def testCancelOtherUserStatus(self):
        print("CancelOtherUserStatus")
        client = Client()

        Status.objects.get(pk=self.status1Id)

        response = client.post(reverse('cancelStatusAPI'), {
            'userid': self.user2.id,
            'statusid': self.status1Id
        })

        response = loadJson(response.content)

        self.assertFalse(response['success'])

        status = Status.objects.get(pk=self.status1Id)

        now = datetime.utcnow()
        self.assertFalse(status.expires < now)


class getStatusesTest(TestCase):
    # TODO: create a test for testing that the location is present in the status
    def setUp(self):
        # user1 and user2 are friends, user1 and user3 are friends
        user1 = User.objects.create(username='user1', password='0', email='user1')
        self.user1 = UserProfile.objects.create(user=user1)

        user2 = User.objects.create(username='user2', password='0', email='user2')
        self.user2 = UserProfile.objects.create(user=user2)

        user3 = User.objects.create(username='user3', password='0', email='user3')
        self.user3 = UserProfile.objects.create(user=user3)

        user4 = User.objects.create(username='user4', password='0', email='user4')
        self.user4 = UserProfile.objects.create(user=user4)

        self.user1.friends.add(self.user2)
        self.user2.friends.add(self.user1)

        self.user1.friends.add(self.user3)
        self.user3.friends.add(self.user1)

        self.user2.friends.add(self.user4)
        self.user4.friends.add(self.user2)

        self.user1.save()
        self.user2.save()
        self.user3.save()
        self.user4.save()

        self.lat = 42.341560
        self.lng = -83.501783
        self.address = '46894 spinning wheel'
        self.city = 'canton'
        self.state = 'MI'
        self.venue = "My house"
        self.expirationDate = datetime.utcnow() + timedelta(hours=2)
        self.startDate = datetime.utcnow() + timedelta(hours=1)
        self.statusType = 'food'

        self.location = Location.objects.create(lng=self.lng, lat=self.lat, point=Point(self.lng, self.lat),
                                                city=self.city, state=self.state, venue=self.venue)

    def testSingleStatus(self):
        print("SingleStatus")
        client = Client()

        status1 = Status.objects.create(user=self.user1, expires=self.expirationDate, text='Hang out',
                                        location=self.location, starts=self.startDate,
                                        visibility=Status.VIS_FRIENDS, statusType=self.statusType, imageOrientation='d')

        myLat = 42.321620
        myLng = -83.507794
        since = datetime.utcnow() - timedelta(hours=1)

        response = client.get(reverse('getStatusesAPI'), {
            'userid': self.user2.id,
            'since': since.strftime(MICROSECOND_DATETIME_FORMAT),
        })

        response = loadJson(response.content)

        self.assertEqual(response['success'], True)
        self.assertNotIn('error', response)
        self.assertEqual(len(response['statuses']), 1)
        status = response['statuses'][0]

        self.assertEqual(status['text'], status1.text)
        self.assertEqual(status['dateexpires'], self.expirationDate.strftime(DATETIME_FORMAT))
        self.assertEqual(status['datestarts'], self.startDate.strftime(DATETIME_FORMAT))
        self.assertEqual(status['imageorientation'], status1.imageOrientation)

        statusDate = status['datecreated']
        self.assertEqual(statusDate, status1.date.strftime(DATETIME_FORMAT))
        self.assertEqual(self.statusType, response['statuses'][0]['type'])

        userInfo = status['userinfo']
        self.assertEqual(self.user1.id, userInfo['userid'])
        self.assertEqual(self.user1.user.first_name, userInfo['firstname'])
        self.assertEqual(self.user1.user.last_name, userInfo['lastname'])
        self.assertEqual(self.user1.facebookUID, userInfo['facebookid'])

        self.assertIn('invited', status)
        self.assertIn('attending', status)
        self.assertIn('users', status)

    def testCustomVisibility(self):
        print("Get Status Custom Visibility")
        client = Client()

        status = Status.objects.create(user=self.user1, expires=self.expirationDate, text='text', starts=self.startDate,
                                       visibility=Status.VIS_CUSTOM, statusType=self.statusType)
        status.friendsVisible.add(self.user2)

        response = client.get(reverse('getStatusesAPI'), {
            'userid': self.user2.id
        })
        response = loadJson(response.content)

        self.assertTrue(response['success'])
        statuses = response['statuses']
        self.assertEqual(len(statuses), 1)

        response = client.get(reverse('getStatusesAPI'), {
            'userid': self.user3.id
        })
        response = loadJson(response.content)

        self.assertTrue(response['success'])
        statuses = response['statuses']
        self.assertEqual(len(statuses), 0)

    def testFriendsVisibility(self):
        print("Get Status Friends Visibility")
        client = Client()

        status = Status.objects.create(user=self.user2, expires=self.expirationDate, text='text', starts=self.startDate,
                                       visibility=Status.VIS_FRIENDS, statusType=self.statusType)

        response = client.get(reverse('getStatusesAPI'), {
            'userid': self.user1.id
        })
        response = loadJson(response.content)

        self.assertTrue(response['success'])
        statuses = response['statuses']
        self.assertEqual(len(statuses), 1)

        response = client.get(reverse('getStatusesAPI'), {
            'userid': self.user3.id
        })
        response = loadJson(response.content)

        self.assertTrue(response['success'])
        statuses = response['statuses']
        self.assertEqual(len(statuses), 0)

    def testFriendsOfFriendsVisibility(self):
        print("Get Status Friends of Friends Visibility")
        client = Client()

        status = Status.objects.create(user=self.user2, expires=self.expirationDate, text='text', starts=self.startDate,
                                       visibility=Status.VIS_FRIENDS_OF_FRIENDS, statusType=self.statusType)

        response = client.get(reverse('getStatusesAPI'), {
            'userid': self.user1.id
        })
        response = loadJson(response.content)

        self.assertTrue(response['success'])
        statuses = response['statuses']
        self.assertEqual(len(statuses), 1)

        response = client.get(reverse('getStatusesAPI'), {
            'userid': self.user3.id
        })
        response = loadJson(response.content)

        self.assertTrue(response['success'])
        statuses = response['statuses']
        self.assertEqual(len(statuses), 1)

    def testPublicVisibility(self):
        print("Get Status Public Visibility")
        client = Client()

        status = Status.objects.create(user=self.user4, expires=self.expirationDate, text='text', starts=self.startDate,
                                       visibility=Status.VIS_PUBLIC, location=self.location, statusType=self.statusType)

        # location right next to status
        response = client.get(reverse('getStatusesAPI'), {
            'userid': self.user1.id,
            'lat': str(self.location.lat + .01),
            'lng': str(self.location.lng + .01),
            'radius': 50
        })
        response = loadJson(response.content)

        self.assertTrue(response['success'])
        statuses = response['statuses']
        self.assertEqual(len(statuses), 1)

        #location far away from status
        response = client.get(reverse('getStatusesAPI'), {
            'userid': self.user1.id,
            'lat': str(self.location.lat + 20),
            'lng': str(self.location.lng + 20),
            'radius': 50
        })
        response = loadJson(response.content)

        self.assertTrue(response['success'])
        statuses = response['statuses']
        self.assertEqual(len(statuses), 0)

        # should not see public statuses if lat and lng are not provided
        response = client.get(reverse('getStatusesAPI'), {
            'userid': self.user1.id,
            'radius': 50
        })
        response = loadJson(response.content)

        self.assertTrue(response['success'])
        statuses = response['statuses']
        self.assertEqual(len(statuses), 0)

    def testInvitedStatus(self):
        print("Test Invited Status")
        client = Client()

        farAwayLocation = self.location
        farAwayLocation.lng = 0
        farAwayLocation.lat = 0
        farAwayLocation.point = Point(0, 0)
        farAwayLocation.save()
        status1 = Status.objects.create(user=self.user4, expires=self.expirationDate, text='Hang out',
                                        location=farAwayLocation, starts=self.startDate,
                                        visibility=Status.VIS_FRIENDS, statusType=self.statusType)
        status1.invited.add(self.user1)

        response = client.get(reverse('getStatusesAPI'), {
            'userid': self.user1.id,
            'radius': 50
        })
        response = loadJson(response.content)

        self.assertTrue(response['success'])
        statuses = response['statuses']

        self.assertEqual(len(statuses), 1)

    def testGetStatusDetails(self):
        print("Get Status Details")
        client = Client()

        status1 = Status.objects.create(user=self.user1, expires=self.expirationDate, text='Hang out',
                                        location=self.location, starts=self.startDate,
                                        visibility=Status.VIS_FRIENDS, statusType=self.statusType)

        response = client.post(reverse('getStatusDetailsAPI'), {
            'statusid': status1.id
        })
        response = loadJson(response.content)

        self.assertTrue(response['success'])

    def testDeletedStatuses(self):
        print("Test Deleted Statuses")
        client = Client()

        friends = Status.objects.create(user=self.user2, expires=self.expirationDate, text='friends',
                                        location=self.location, starts=self.startDate,
                                        visibility=Status.VIS_FRIENDS, statusType=self.statusType, deleted=True)
        friendsOfFriends = Status.objects.create(user=self.user4, expires=self.expirationDate,
                                                 text='friends of friends',
                                                 starts=self.startDate, location=self.location,
                                                 visibility=Status.VIS_FRIENDS_OF_FRIENDS, statusType=self.statusType,
                                                 deleted=True)
        public = Status.objects.create(user=self.user4, expires=self.expirationDate, text='public',
                                       starts=self.startDate,
                                       visibility=Status.VIS_PUBLIC, location=self.location, statusType=self.statusType,
                                       deleted=True)
        custom = Status.objects.create(user=self.user2, expires=self.expirationDate, text='custom',
                                       starts=self.startDate,
                                       visibility=Status.VIS_CUSTOM, statusType=self.statusType, location=self.location,
                                       deleted=True)
        custom.friendsVisible.add(self.user1)
        custom.save()

        response = client.get(reverse('getStatusesAPI'), {
            'userid': self.user1.id,
            'radius': 50,
            'lat': str(self.location.lat + .01),
            'lng': str(self.location.lng + .01)
        })
        response = loadJson(response.content)

        self.assertTrue(response['success'])
        self.assertEqual(len(response['statuses']), 4)
        statuses = response['statuses']
        self.assertTrue(statuses[0]['deleted'])
        self.assertTrue(statuses[1]['deleted'])
        self.assertTrue(statuses[2]['deleted'])
        self.assertTrue(statuses[3]['deleted'])


class GetMyStatusesTest(TestCase):
    def setUp(self):
        user1 = User.objects.create(username='user1', password='0', email='user1')
        self.user1 = UserProfile.objects.create(user=user1)

        self.lat = 42.341560
        self.lng = -83.501783
        self.address = '46894 spinning wheel'
        self.city = 'canton'
        self.state = 'MI'
        self.venue = "My house"
        self.expirationDate = datetime.utcnow() + timedelta(hours=1)

        self.location = Location.objects.create(lng=self.lng, lat=self.lat, point=Point(self.lng, self.lat),
                                                city=self.city, state=self.state, venue=self.venue)

        self.status1 = Status.objects.create(user=self.user1, expires=self.expirationDate, text='Hang out1',
                                             location=self.location)

        self.status2 = Status.objects.create(user=self.user1, expires=self.expirationDate, text='Hang out2',
                                             location=self.location)

        self.status3 = Status.objects.create(user=self.user1, expires=self.expirationDate, text='Hang out3',
                                             location=self.location)

    def testGetMyStatuses(self):
        print("GetMyStatuses")
        client = Client()

        response = client.post(reverse('getMyStatusesAPI'), {
            'userid': self.user1.id
        })

        response = loadJson(response.content)
        self.assertTrue(response['success'])

        status1Found = False
        status2Found = False
        status3Found = False
        for status in response['statuses']:

            if status['text'] == self.status1.text:
                status1Found = True
            if status['text'] == self.status2.text:
                status2Found = True
            if status['text'] == self.status3.text:
                status3Found = True

        self.assertTrue(status1Found)
        self.assertTrue(status2Found)
        self.assertTrue(status3Found)


class PokeTest(TestCase):
    def setUp(self):
        user1 = User.objects.create(username='user1', password='0', email='user1')
        self.user1 = UserProfile.objects.create(user=user1)

        user2 = User.objects.create(username='user2', password='0', email='user2')
        self.user2 = UserProfile.objects.create(user=user2)

        self.user1.friends.add(self.user2)
        self.user2.friends.add(self.user1)

    def testPoke(self):
        print("Poke")
        client = Client()

        response = client.post(reverse('pokeAPI'), {
            'userid': self.user1.id,
            'friendid': self.user2.id
        })

        response = loadJson(response.content)

        self.assertEqual(response['success'], True)

        response = client.post(reverse('pokeAPI'), {
            'userid': self.user1.id,
            'friendid': self.user2.id
        })

        response = loadJson(response.content)
        self.assertNotIn('pokeid', response)
        self.assertEqual(response['success'], False)
        self.assertIsNotNone(response['error'])

    def testPokeInLogin(self):
        print("PokeInLogin")
        client = Client()

        response = client.post(reverse('pokeAPI'), {
            'userid': self.user1.id,
            'friendid': self.user2.id
        })

        response = loadJson(response.content)

        self.assertEqual(response['success'], True)

        friendObj = getUserProfileDetailsJson(self.user2)


class GroupTests(TestCase):
    def setUp(self):
        user = User.objects.create(username='user', password='0', email='user')
        self.user = UserProfile.objects.create(user=user)

        friend = User.objects.create(username='friend', password='0', email='friend')
        self.friend = UserProfile.objects.create(user=friend)

        self.user.friends.add(self.friend)
        self.friend.friends.add(self.user)

        friend2 = User.objects.create(username='friend2', password='0', email='friend2')
        self.friend2 = UserProfile.objects.create(user=friend2)

        self.user.friends.add(self.friend2)
        self.friend2.friends.add(self.user)

    def testCreateGroup(self):
        print("CreateGroup")

        client = Client()
        groupName = "group1"

        response = client.post(reverse('createGroupAPI'), {
            'userid': self.user.id,
            'groupname': groupName
        })
        response = loadJson(response.content)

        groupid = response['groupid']
        group = self.user.groups.latest('id')
        self.assertEqual(response['success'], True)
        self.assertNotIn('error', response)
        self.assertEqual(group.id, groupid)

    def testCreateGroupDuplicateName(self):
        print("CreateGroupDuplicateName")

        client = Client()
        groupName = "group1"

        response = client.post(reverse('createGroupAPI'), {
            'userid': self.user.id,
            'groupname': groupName
        })
        response = loadJson(response.content)
        groupId = response['groupid']

        response = client.post(reverse('createGroupAPI'), {
            'userid': self.user.id,
            'groupname': groupName
        })

        response = loadJson(response.content)
        self.assertEqual(response['success'], True)
        self.assertEqual(response['groupid'], groupId)

    def testDeleteGroup(self):
        print("DeleteGroup")

        client = Client()
        groupName = "group1"

        response = client.post(reverse('createGroupAPI'), {
            'userid': self.user.id,
            'groupname': groupName
        })

        response = loadJson(response.content)
        groupid = response['groupid']

        response = client.post(reverse('deleteGroupAPI'), {
            'userid': self.user.id,
            'groupid': groupid
        })

        response = loadJson(response.content)
        self.assertEqual(response['success'], True)
        self.assertNotIn('error', response)

        with self.assertRaises(Group.DoesNotExist):
            Group.objects.get(pk=groupid)

    def testDeleteOtherUserGroup(self):
        print("DeleteOtherUserGroup")

        client = Client()
        groupName = "group1"

        response = client.post(reverse('createGroupAPI'), {
            'userid': self.user.id,
            'groupname': groupName
        })

        response = loadJson(response.content)
        groupid = response['groupid']

        response = client.post(reverse('deleteGroupAPI'), {
            'userid': self.friend.id,
            'groupid': groupid
        })
        response = loadJson(response.content)

        self.assertFalse(response['success'])
        self.assertIn('error', response)

    def testEditGroupName(self):
        print("EditGroupName")

        client = Client()
        groupName = "group1"
        newGroupName = "group2"

        response = client.post(reverse('createGroupAPI'), {
            'userid': self.user.id,
            'groupname': groupName
        })

        response = loadJson(response.content)
        groupid = response['groupid']

        response = client.post(reverse('editGroupNameAPI'), {
            'userid': self.user.id,
            'groupid': groupid,
            'groupname': newGroupName
        })
        response = loadJson(response.content)

        self.assertTrue(response['success'])

        group = Group.objects.get(pk=groupid)
        self.assertEqual(group.name, newGroupName)

    def testEditOtherUserGroupName(self):
        print("EditOtherUserGroupName")

        client = Client()
        groupName = "group1"
        newGroupName = "group2"

        response = client.post(reverse('createGroupAPI'), {
            'userid': self.user.id,
            'groupname': groupName
        })

        response = loadJson(response.content)
        groupid = response['groupid']

        response = client.post(reverse('editGroupNameAPI'), {
            'userid': self.friend.id,
            'groupid': groupid,
            'groupname': newGroupName
        })
        response = loadJson(response.content)

        self.assertFalse(response['success'])
        self.assertIn('error', response)

        group = Group.objects.get(pk=groupid)
        self.assertEqual(group.name, groupName)

    def testAddGroupMembers(self):
        print("AddGroupMembers")

        client = Client()
        groupName = "group1"

        response = client.post(reverse('createGroupAPI'), {
            'userid': self.user.id,
            'groupname': groupName
        })

        response = loadJson(response.content)
        groupid = response['groupid']

        client.post(reverse('addGroupMemberAPI'), {
            'userid': self.user.id,
            'friendid': self.friend.id,
            'groupid': groupid
        })

        response = client.post(reverse('addGroupMemberAPI'), {
            'userid': self.user.id,
            'friendid': self.friend2.id,
            'groupid': groupid
        })
        response = loadJson(response.content)

        self.assertTrue(response['success'])

        group = Group.objects.get(pk=groupid)
        members = group.members.all()

        self.assertIn(self.friend, members)
        self.assertIn(self.friend2, members)

    def testRemoveGroupMembers(self):
        print("RemoveGroupMembers")

        client = Client()
        groupName = "group1"

        response = client.post(reverse('createGroupAPI'), {
            'userid': self.user.id,
            'groupname': groupName
        })

        response = loadJson(response.content)
        groupid = response['groupid']
        fbFriendId = 'asfasfqfqfqfwqwf'

        client.post(reverse('addGroupMemberAPI'), {
            'userid': self.user.id,
            'friendid': self.friend.id,
            'groupid': groupid
        })

        client.post(reverse('addGroupMemberAPI'), {
            'userid': self.user.id,
            'friendid': self.friend2.id,
            'groupid': groupid
        })

        client.post(reverse('addGroupMemberAPI'), {
            'userid': self.user.id,
            'friendid': "fb" + fbFriendId,
            'groupid': groupid
        })

        client.post(reverse('removeGroupMemberAPI'), {
            'userid': self.user.id,
            'friendid': "fb" + fbFriendId,
            'groupid': groupid
        })

        client.post(reverse('removeGroupMemberAPI'), {
            'userid': self.user.id,
            'friendid': self.friend.id,
            'groupid': groupid
        })

        response = client.post(reverse('removeGroupMemberAPI'), {
            'userid': self.user.id,
            'friendid': self.friend2.id,
            'groupid': groupid
        })
        response = loadJson(response.content)

        self.assertTrue(response['success'])

        group = Group.objects.get(pk=groupid)
        members = group.members.all()

        self.assertNotIn(self.friend, members)
        self.assertNotIn(self.friend2, members)
        self.assertNotIn(fbFriendId, group.fbMembers.values_list('facebookUID', flat=True))

        response = client.post(reverse('removeGroupMemberAPI'), {
            'userid': self.user.id,
            'friendid': self.friend.id,
            'groupid': groupid
        })
        response = loadJson(response.content)

        self.assertTrue(response['success'])

    def testGetGroups(self):
        print("GetGroups")
        client = Client()

        groupName1 = "group1"
        groupName2 = "group2"
        groupName3 = "group3"

        group1 = Group.objects.create(user=self.user, name=groupName1)
        group2 = Group.objects.create(user=self.user, name=groupName2)
        group3 = Group.objects.create(user=self.user, name=groupName3)

        group1.members.add(self.friend)
        group1.save()

        group2.members.add(self.friend2)
        group2.save()

        group3.members.add(self.friend)
        group3.members.add(self.friend2)
        group3.save()

        response = client.post(reverse('getGroupsAPI'), {
            'userid': self.user.id
        })
        response = loadJson(response.content)

        self.assertTrue(response['success'])
        self.assertIn('groups', response)
        self.assertEqual(len(response['groups']), 3)

        groups = {group['groupname']: group for group in response['groups']}

        group1Data = groups['group1']
        self.assertEqual(group1Data['groupid'], group1.id)
        self.assertIn(self.friend.id, group1Data['userids'])

        group2Data = groups['group2']
        self.assertEqual(group2Data['groupid'], group2.id)
        self.assertIn(self.friend2.id, group2Data['userids'])

        group3Data = groups['group3']
        self.assertEqual(group3Data['groupid'], group3.id)
        self.assertIn(self.friend.id, group3Data['userids'])
        self.assertIn(self.friend2.id, group3Data['userids'])

    def testSetGroups(self):
        print("SetGroups")
        client = Client()

        groupName1 = "group1"
        groupName2 = "group2"
        groupName3 = "group3"

        group1 = Group.objects.create(user=self.user, name=groupName1)
        group2 = Group.objects.create(user=self.user, name=groupName2)
        group3 = Group.objects.create(user=self.user, name=groupName3)

        group1.members.add(self.friend)
        group1.save()

        group2.members.add(self.friend2)
        group2.save()

        group3.members.add(self.friend)
        group3.members.add(self.friend2)
        group3.save()

        groups = [group1.id, group2.id, group3.id]
        response = client.post(reverse('setGroupsAPI'), {
            'userid': self.user.id,
            'friendid': self.friend.id,
            'groupids': json.dumps(groups)
        })
        response = loadJson(response.content)

        self.assertEqual(response['success'], True)
        self.assertTrue(self.friend in group1.members.all())
        self.assertTrue(self.friend in group2.members.all())
        self.assertTrue(self.friend in group3.members.all())

        groups = [group1.id]
        response = client.post(reverse('setGroupsAPI'), {
            'userid': self.user.id,
            'friendid': self.friend2.id,
            'groupids': json.dumps(groups)
        })
        response = loadJson(response.content)

        self.assertEqual(response['success'], True)
        self.assertTrue(self.friend2 in group1.members.all())
        self.assertTrue(self.friend2 not in group2.members.all())
        self.assertTrue(self.friend2 not in group3.members.all())

        groups = []
        response = client.post(reverse('setGroupsAPI'), {
            'userid': self.user.id,
            'friendid': self.friend.id,
            'groupids': json.dumps(groups)
        })
        response = loadJson(response.content)

        self.assertEqual(response['success'], True)
        self.assertTrue(self.friend not in group1.members.all())
        self.assertTrue(self.friend not in group2.members.all())
        self.assertTrue(self.friend not in group3.members.all())

    def testSetGroupsForFBUser(self):
        print("Set Groups FB User")
        client = Client()

        groupName1 = "group1"
        groupName2 = "group2"
        groupName3 = "group3"

        fbFriendId = 'fbffaf198yf89hf180h'

        group1 = Group.objects.create(user=self.user, name=groupName1)
        group2 = Group.objects.create(user=self.user, name=groupName2)
        group3 = Group.objects.create(user=self.user, name=groupName3)

        groups = [group1.id, group2.id, group3.id]
        response = client.post(reverse('setGroupsAPI'), {
            'userid': self.user.id,
            'friendid': fbFriendId,
            'groupids': json.dumps(groups)
        })
        response = loadJson(response.content)

        fbFriend = FacebookUser.objects.get(facebookUID=fbFriendId[2:])

        self.assertEqual(response['success'], True)
        self.assertTrue(fbFriend in group1.fbMembers.all())
        self.assertTrue(fbFriend in group2.fbMembers.all())
        self.assertTrue(fbFriend in group3.fbMembers.all())

        groups = [group1.id]
        response = client.post(reverse('setGroupsAPI'), {
            'userid': self.user.id,
            'friendid': fbFriendId,
            'groupids': json.dumps(groups)
        })
        response = loadJson(response.content)

        self.assertEqual(response['success'], True)
        self.assertTrue(fbFriend in group1.fbMembers.all())
        self.assertTrue(fbFriend not in group2.fbMembers.all())
        self.assertTrue(fbFriend not in group3.fbMembers.all())

        response = client.post(reverse('getGroupsAPI'), {
            'userid': self.user.id
        })
        response = loadJson(response.content)

        for group in response['groups']:
            if group['groupid'] == group1.id:
                self.assertIn(fbFriendId, list(group['userids']))

        groups = []
        response = client.post(reverse('setGroupsAPI'), {
            'userid': self.user.id,
            'friendid': fbFriendId,
            'groupids': json.dumps(groups)
        })
        response = loadJson(response.content)

        self.assertEqual(response['success'], True)
        self.assertTrue(fbFriend not in group1.fbMembers.all())
        self.assertTrue(fbFriend not in group2.fbMembers.all())
        self.assertTrue(fbFriend not in group3.fbMembers.all())


    def testSetGroupMembers(self):
        print("SetGroupMembers")
        client = Client()

        groupName1 = "group1"
        groupName2 = "group2"

        group1 = Group.objects.create(user=self.user, name=groupName1)
        group2 = Group.objects.create(user=self.user, name=groupName2)

        group1.members.add(self.friend)
        group2.members.add(self.friend)
        group2.members.add(self.friend2)

        group1.save()
        group2.save()

        fbFriendId1 = 'ff13f13f13f13f13f1f'
        fbFriendId2 = 'fbf0u190uni130fj91j31f'

        members1 = [self.friend.id, self.friend2.id, "fb" + fbFriendId1, "fb" + fbFriendId2]
        members2 = []

        response = client.post(reverse('setGroupMembersAPI'), {
            'userid': self.user.id,
            'groupid': group1.id,
            'friendids': json.dumps(members1)
        })
        response = loadJson(response.content)

        self.assertTrue(response['success'])

        self.assertTrue(self.friend in group1.members.all())
        self.assertTrue(self.friend2 in group1.members.all())
        self.assertTrue(fbFriendId2 in group1.fbMembers.values_list('facebookUID', flat=True))
        self.assertTrue(fbFriendId1 in group1.fbMembers.values_list('facebookUID', flat=True))

        response = client.post(reverse('setGroupMembersAPI'), {
            'userid': self.user.id,
            'groupid': group2.id,
            'friendids': json.dumps(members2)
        })
        response = loadJson(response.content)

        self.assertTrue(response['success'])
        self.assertTrue(self.friend not in group2.members.all())
        self.assertTrue(self.friend2 not in group2.members.all())
        self.assertTrue(fbFriendId2 not in group2.fbMembers.values_list('facebookUID', flat=True))
        self.assertTrue(fbFriendId1 not in group2.fbMembers.values_list('facebookUID', flat=True))


class FriendsListTests(TestCase):
    def setUp(self):
        user = User.objects.create(username='user', password='0', email='user')
        self.user = UserProfile.objects.create(user=user)

        friend = User.objects.create(username='friend', password='0', email='friend', first_name="friend",
                                     last_name="1")
        self.friend = UserProfile.objects.create(user=friend, facebookUID='friend1fbid')

        self.user.friends.add(self.friend)
        self.friend.friends.add(self.user)

        friend2 = User.objects.create(username='friend2', password='0', email='friend2', first_name='friend2',
                                      last_name="2")
        self.friend2 = UserProfile.objects.create(user=friend2, facebookUID='friend2fbid')

        self.user.friends.add(self.friend2)
        self.friend2.friends.add(self.user)

    def testGetFriends(self):
        print("GetFriends")

        client = Client()

        response = client.post(reverse('getFriendsAPI'), {
            'userid': self.user.id
        })
        response = loadJson(response.content)

        self.assertTrue(response['success'])

        friends = response['users']
        self.assertEqual(len(friends), 2)

        friend1 = {'userid': self.friend.id, 'firstname': self.friend.user.first_name,
                   'lastname': self.friend.user.last_name, 'facebookid': self.friend.facebookUID}
        friend2 = {'userid': self.friend2.id, 'firstname': self.friend2.user.first_name,
                   'lastname': self.friend2.user.last_name,
                   'facebookid': self.friend2.facebookUID}

        self.assertIn(friend1, friends)
        self.assertIn(friend2, friends)

    def testBlockFriends(self):
        print("BlockFriends")

        client = Client()

        client.post(reverse('blockFriendAPI'), {
            'userid': self.user.id,
            'friendid': self.friend.id
        })

        response = client.post(reverse('blockFriendAPI'), {
            'userid': self.user.id,
            'friendid': self.friend2.id
        })
        response = loadJson(response.content)

        self.assertTrue(response['success'])

        self.assertIn(self.friend, self.user.blockedFriends.all())
        self.assertIn(self.friend2, self.user.blockedFriends.all())

    def testUnblockFriends(self):
        print("UnblockFriends")

        self.user.blockedFriends.add(self.friend)
        self.user.blockedFriends.add(self.friend2)

        client = Client()

        client.post(reverse("unblockFriendAPI"), {
            'userid': self.user.id,
            'friendid': self.friend.id
        })

        response = client.post(reverse("unblockFriendAPI"), {
            'userid': self.user.id,
            'friendid': self.friend2.id
        })
        response = loadJson(response.content)

        self.assertTrue(response['success'])

        self.assertNotIn(self.friend, self.user.blockedFriends.all())
        self.assertNotIn(self.friend2, self.user.blockedFriends.all())


class FeedbackTests(TestCase):
    def setUp(self):
        user = User.objects.create(username='user', password='0', email='user')
        self.user = UserProfile.objects.create(user=user)

    def testSubmitFeedback(self):
        print("SubmitFeedback")

        client = Client()
        text = "I think this app is very useful and well made"

        response = client.post(reverse('submitFeedbackAPI'), {
            'userid': self.user.id,
            'text': text
        })
        response = loadJson(response.content)

        self.assertTrue(response['success'])

        feedback = self.user.submittedFeedback.latest('id')

        self.assertEqual(feedback.text, text)


class GetNewDataTests(TestCase):
    def setUp(self):
        user = User.objects.create(username='user', password='0', email='user')
        self.user = UserProfile.objects.create(user=user)

        friend = User.objects.create(username='friend', password='0', email='friend')
        self.friend = UserProfile.objects.create(user=friend)

        self.user.friends.add(self.friend)
        self.friend.friends.add(self.user)

        friend2 = User.objects.create(username='friend2', password='0', email='friend2')
        self.friend2 = UserProfile.objects.create(user=friend2)

        self.user.friends.add(self.friend2)
        self.friend2.friends.add(self.user)

        self.convo = Conversation.objects.create()
        self.convo.members.add(self.user)
        self.convo.members.add(self.friend)
        self.convo.save()

        self.message = Message.objects.create(user=self.user, conversation=self.convo, text="text")

    def testGetNewData(self):
        print("GetNewData")

        client = Client()

        response = client.post(reverse('getNewDataAPI'), {
            'userid': self.user.id,
        })

        response = loadJson(response.content)

        self.assertTrue(response['success'])
        self.assertEqual(len(response['chats'][0]['messages']), 1)

        response = client.post(reverse('getNewDataAPI'), {
            'userid': self.user.id,
            'since': response['newsince'],
        })

        response = loadJson(response.content)

        self.assertTrue(response['success'])
        self.assertEqual(len(response['chats']), 0)

    def testGetPokes(self):
        print("GetPokes")

        client = Client()

        response = client.post(reverse('pokeAPI'), {
            'userid': self.friend.id,
            'friendid': self.user.id
        })

        response = loadJson(response.content)

        self.assertTrue(response['success'])

        response = client.post(reverse('getNewDataAPI'), {
            'userid': self.user.id
        })

        response = loadJson(response.content)

        self.assertTrue(response['success'])

        pokes = response['pokes']
        poke1 = pokes[0]

        self.assertEqual(poke1, self.friend.id)

        newSince = response['newsince']

        response = client.post(reverse('getNewDataAPI'), {
            'userid': self.user.id,
            'since': newSince
        })

        response = loadJson(response.content)

        self.assertTrue(response['success'])
        self.assertEqual(len(response['pokes']), 0)


class SettingsTests(TestCase):
    def setUp(self):
        self.key1 = 'statusradius'
        self.key2 = 'imboredtext'

        user = User.objects.create(username='user', password='0', email='user')
        self.user = UserProfile.objects.create(user=user)

        self.setting1 = Setting.objects.create(user=self.user, value="value1", key=self.key1)

    def testSetSetting(self):
        print("SetSetting")

        client = Client()

        response = client.post(reverse('setSettingAPI'), {
            'userid': self.user.id,
            'key': self.key1,
            'value': 'value2'
        })
        response = loadJson(response.content)

        self.assertTrue(response['success'])

        setting1 = self.user.settings.get(key=self.key1)
        self.assertEqual(setting1.value, 'value2')

        response = client.post(reverse('setSettingAPI'), {
            'userid': self.user.id,
            'key': self.key2,
            'value': 'value3'
        })
        response = loadJson(response.content)

        setting2 = self.user.settings.get(key=self.key2)
        self.assertTrue(response['success'])
        self.assertEqual(setting2.value, 'value3')


    def testGetSetting(self):
        print("GetSetting")

        client = Client()

        response = client.post(reverse('getSettingAPI'), {
            'userid': self.user.id,
            'key': self.setting1.key
        })

        response = loadJson(response.content)

        self.assertTrue(response['success'])
        self.assertEqual(self.setting1.value, response['value'])

    def testGetBlankSetting(self):
        print("GetBlankSetting")

        client = Client()

        response = client.post(reverse('getSettingAPI'), {
            'userid': self.user.id,
            'key': 'nokey'
        })

        response = loadJson(response.content)

        self.assertTrue(response['success'])
        self.assertEqual('', response['value'])


class PushNotificationTests(LiveServerTestCase):
    def setUp(self):
        user = User.objects.create(username='user', password='0', email='user')
        self.user = UserProfile.objects.create(user=user)

        friend = User.objects.create(username='friend', password='0', email='friend', first_name="friend 1")
        self.friend = UserProfile.objects.create(user=friend)

        self.user.friends.add(self.friend)
        self.friend.friends.add(self.user)

        friend2 = User.objects.create(username='friend2', password='0', email='friend2', first_name="friend 2")
        self.friend2 = UserProfile.objects.create(user=friend2)

        self.user.friends.add(self.friend2)
        self.friend2.friends.add(self.user)

        friend3 = User.objects.create(username='friend3', password='0', email='friend3', first_name="friend 3")
        self.friend3 = UserProfile.objects.create(user=friend3)

        self.user.friends.add(self.friend3)
        self.friend3.friends.add(self.user)

        nonFriend = User.objects.create(username='friend4', password='0', email='friend4', first_name="friend 4")
        self.nonFriend = UserProfile.objects.create(user=nonFriend)

        self.friend3.friends.add(self.nonFriend)
        self.nonFriend.friends.add(self.friend3)

        self.convo = Conversation.objects.create()
        self.convo.members.add(self.user, self.friend, self.friend2, self.friend3)

        self.message = Message.objects.create(user=self.user, text='Hello', conversation=self.convo)
        self.convo.save()

        expires = datetime.now() + timedelta(hours=1)
        text = "text"

        lat = 42.341560
        lng = -83.501783
        address = '46894 spinning wheel'
        city = 'canton'
        state = 'MI'
        venue = "My house"
        expirationDate = datetime.utcnow() + timedelta(hours=1)

        location = Location.objects.create(lng=lng, lat=lat, point=Point(lng, lat), city=city, state=state, venue=venue,
                                           address=address)

        self.status = Status.objects.create(user=self.user, expires=expirationDate, text='Hang out1', location=location)

        self.friend1Device = APNSDevice.objects.create(user=self.friend,
                                                       registration_id="ae134ff0db615fc5725e44d29bf3d83f606f801fed126741ac92ce3489ad77a7")

        self.friend2Device = GCMDevice.objects.create(user=self.friend2,
                                                      registration_id="f7f6544e7bdb153cb17b0fb2c01dcd72d1ba315b753b29844258c66243b69f08")
        self.friend2APNSDevice = APNSDevice.objects.create(user=self.friend2,
                                                           registration_id="f7f6544e7bdb153cb17b0fb2c01dcd72d1ba315b753b29844258c66243b69f08")
        self.friend3APNSDevice = APNSDevice.objects.create(user=self.friend3,
                                                           registration_id="ef4a0cc519a800ab0f56356135ca98a0d22528f4a1277534295af02684df0bed")

        self.pokeObj = Poke.objects.create(sender=self.user, recipient=self.friend2)

    def testAttendingPushNotification(self):
        print("Attending Push Notification")

        self.status.attending.add(self.friend)
        sendAttendingStatusPushNotification(self.status, self.friend)

    def testInvitePushNotification(self):
        print("Invite Push Notification")

        self.status.invited.add(self.friend)
        sendInvitedToStatusNotification(self.status, self.user, [self.friend, ])

    def testStatusDeletePushNotification(self):
        print("Delete Status Push Notification")

        self.status.attending.add(self.friend)
        sendDeleteStatusNotfication(self.status)

    def testStatusEditPushNotification(self):
        print("Status Edit Push Notification")
        sendEditStatusNotification(self.status)

    def testStatusMessagePushNotification(self):
        print("Status Message Push Notification")
        self.status.attending.add(self.friend)
        statusMessage = StatusMessage.objects.create(user=self.user, text='safa', status=self.status)

        sendStatusMessageNotification(statusMessage)

    def testWithFavoritesNotification(self):
        print("Post Status With Favorites Notification")
        client = Client()

        group1 = Group.objects.create(name=Group.FAVORITES_GROUP_NAME, user=self.friend)
        group2 = Group.objects.create(name=Group.FAVORITES_GROUP_NAME, user=self.friend2)
        group3 = Group.objects.create(name=Group.FAVORITES_GROUP_NAME, user=self.friend3)
        group4 = Group.objects.create(name=Group.FAVORITES_GROUP_NAME, user=self.nonFriend)

        group1.members.add(self.user)
        group2.members.add(self.user)
        group3.members.add(self.user)
        group4.members.add(self.user)

        expires = datetime.now() + timedelta(hours=1)
        text = "text"

        lat = 42.341560
        lng = -83.501783
        address = '46894 spinning wheel'
        city = 'canton'
        state = 'MI'
        venue = "My house"
        expirationDate = datetime.utcnow() + timedelta(hours=1)

        location = Location.objects.create(lng=lng, lat=lat, point=Point(lng, lat), city=city, state=state, venue=venue,
                                           address=address)

        status = Status.objects.create(user=self.user, expires=expirationDate, text='Hang out1', location=location)

        usersSent = sendFavoritesStatusPushNotification(status)
        self.assertEqual(len(usersSent), 3)
        self.assertNotIn(self.nonFriend, usersSent)

        status.visibility = Status.VIS_FRIENDS_OF_FRIENDS
        status.save()

        usersSent = sendFavoritesStatusPushNotification(status)
        self.assertEqual(len(usersSent), 4)

        status.visibility = Status.VIS_CUSTOM
        status.friendsVisible.add(self.friend)
        status.save()

        usersSent = sendFavoritesStatusPushNotification(status)
        self.assertEqual(len(usersSent), 1)

    #     self.assertIn(self.friend, usersSent)

    def testSimpleChatNotification(self):
        pass
        print("Chat Push Notification")

        sendChatNotifications(self.message)

    def testRegisterToken(self):
        print("Resgister Push Notification Token")
        client = Client()

        iosToken = 'asfafqwf1f13f1f'
        androidToken = 'asff1fh881f9h1fh1ifh'

        response = client.post(reverse('registerPushNotificationsAPI'), {
            'userid': self.friend.id,
            'token': iosToken,
            'platform': 'ios'
        })

        response = loadJson(response.content)

        self.assertTrue(response['success'])

        response = client.post(reverse('registerPushNotificationsAPI'), {
            'userid': self.friend.id,
            'token': androidToken,
            'platform': 'android'
        })

        response = loadJson(response.content)

        self.assertTrue(response['success'])

        androidDevice = GCMDevice.objects.get(user=self.friend, registration_id=androidToken)
        iosDevice = APNSDevice.objects.get(user=self.friend, registration_id=iosToken)

    def testDeviceFiltering(self):
        print("test device filtering")

        allUsers = UserProfile.objects.all()
        apnsDevices = APNSDevice.objects.filter(user__in=allUsers)

        self.assertGreaterEqual(len(apnsDevices), 2)

    def testDeviceFilteringConversation(self):
        print("Push Notif Device Convo Filter")
        client = Client()

        chat = Conversation.objects.create()
        chat.members.add(self.friend)
        chat.members.add(self.friend2)
        chat.members.add(self.friend3)
        self.assertGreaterEqual(chat.members.all().count(), 2)

        members = chat.members.all()
        apnsDevices = APNSDevice.objects.filter(user__in=members)
        self.assertEqual(len(apnsDevices), 3)

        membersMinusSender = chat.members.all().exclude(id=self.friend.id)
        apnsDevices = APNSDevice.objects.filter(user__in=membersMinusSender)
        self.assertEqual(len(apnsDevices), 2)
        response = client.post(reverse('sendMessageAPI'), {
            'userid': self.friend.id,
            'chatid': chat.id,
            'text': 'hello'
        })


class AppNotificationTests(TestCase):
    def setUp(self):
        user = User.objects.create(username='user', password='0', email='user')
        self.user = UserProfile.objects.create(user=user)

        friend = User.objects.create(username='friend', password='0', email='friend')
        self.friend = UserProfile.objects.create(user=friend)

        self.user.friends.add(self.friend)
        self.friend.friends.add(self.user)

        friend2 = User.objects.create(username='friend2', password='0', email='friend2')
        self.friend2 = UserProfile.objects.create(user=friend2)

        self.user.friends.add(self.friend2)
        self.friend2.friends.add(self.user)

        friend3 = User.objects.create(username='friend3', password='0', email='friend3')
        self.friend3 = UserProfile.objects.create(user=friend3)

        self.user.friends.add(self.friend3)
        self.friend3.friends.add(self.user)

        lat = 42.341560
        lng = -83.501783
        address = '46894 spinning wheel'
        city = 'canton'
        state = 'MI'
        venue = "My house"
        expirationDate = datetime.utcnow() + timedelta(hours=1)

        location = Location.objects.create(lng=lng, lat=lat, point=Point(lng, lat), city=city, state=state, venue=venue,
                                           address=address)

        self.status = Status.objects.create(user=self.user, expires=expirationDate, text='Hang out1',
                                            location=location)
        self.status.attending.add(self.friend)

    def testFriendJoinedNotification(self):
        print("Friend Joined Notification")

        UserProfile.objects.all().delete()
        User.objects.all().delete()

        fb = facebook.GraphAPI()
        appAccessToken = helpers.getFacebookAppAccessToken()
        testUsers = fb.request(settings.FACEBOOK_APP_ID + '/accounts/test-users',
                               {'access_token': str(appAccessToken), })
        testUsers = testUsers['data']
        for user in testUsers:

            if user['id'] == FB_TEST_USER_1_ID:
                self.accessTokenUser = user['access_token']
                continue

            if user['id'] == FB_TEST_USER_2_ID:
                self.accessTokenFriend1 = user['access_token']
                continue

            if user['id'] == FB_TEST_USER_3_ID:
                self.accessTokenFriend2 = user['access_token']
                continue

            if user['id'] == FB_TEST_USER_4_ID:
                self.accessTokenFriend3 = user['access_token']
                continue

        client = Client()
        response = client.post(reverse('facebookLoginAPI'), {
            'fbauthkey': self.accessTokenUser,
            'device': 'android'
        })
        response = loadJson(response.content)
        self.assertTrue(response['success'])

        userId = response['userid']
        user = UserProfile.objects.get(pk=userId)

        response = client.post(reverse('facebookLoginAPI'), {
            'fbauthkey': self.accessTokenFriend1,
            'device': 'android'
        })
        response = loadJson(response.content)
        self.assertTrue(response['success'])

        friend1Id = response['userid']
        friend1 = UserProfile.objects.get(pk=friend1Id)

        response = client.post(reverse('getNewDataAPI'), {
            'userid': user.id
        })
        response = loadJson(response.content)

        self.assertTrue(response['success'])
        self.assertEqual(len(response['notifications']), 1)
        notif = response['notifications'][0]

        self.assertEqual(notif['type'], Notification.NOTIF_FRIEND_JOINED)
        self.assertEqual(notif['friendid'], friend1.id)

        response = client.post(reverse('facebookLoginAPI'), {
            'fbauthkey': self.accessTokenFriend2,
            'device': 'android'
        })
        response = loadJson(response.content)

        friend2Id = response['userid']
        friend2 = UserProfile.objects.get(pk=friend2Id)

        response = client.post(reverse('getNewDataAPI'), {
            'userid': user.id
        })
        response = loadJson(response.content)

        self.assertTrue(response['success'])
        self.assertEqual(len(response['notifications']), 2)
        notif1 = response['notifications'][0]
        notif2 = response['notifications'][1]

        self.assertEqual(notif['type'], Notification.NOTIF_FRIEND_JOINED)
        self.assertIn(notif['friendid'], [friend1.id, friend2.id])

        self.assertEqual(notif['type'], Notification.NOTIF_FRIEND_JOINED)
        self.assertIn(notif['friendid'], [friend1.id, friend2.id])

    def testStatusMessageNotification(self):
        print("Status Message Notification")
        client = Client()

        response = client.post(reverse('postStatusMessageAPI'), {
            'userid': self.friend.id,
            'statusid': self.status.id,
            'text': "asfasfasfasfasf"
        })

        response = client.post(reverse('getNewDataAPI'), {
            'userid': self.user.id
        })
        response = loadJson(response.content)

        notifications = response['notifications']
        self.assertEqual(len(notifications), 1)
        notif = notifications[0]

        self.assertEqual(notif['type'], Notification.NOTIF_STATUS_MESSAGE)
        self.assertEqual(notif['friendid'], self.friend.id)
        self.assertEqual(notif['statusid'], self.status.id)

    def testStatusChangedNotification(self):
        print("Status Change Notification")
        client = Client()

        response = client.post(reverse('postStatusAPI'), {
            'statusid': self.status.id,
            'text': 'afafqwf13f13f1f',
            'userid': self.user.id
        })
        response = loadJson(response.content)

        self.assertTrue(response['success'])

        response = client.post(reverse('getNewDataAPI'), {
            'userid': self.friend.id
        })
        response = loadJson(response.content)

        notifications = response['notifications']
        self.assertEqual(len(notifications), 1)
        notif = notifications[0]

        self.assertEqual(notif['type'], Notification.NOTIF_STATUS_CHANGED)
        self.assertEqual(notif['friendid'], self.user.id)
        self.assertEqual(notif['statusid'], self.status.id)

    def testStatusAttendingNotification(self):
        print("Status Attending Notification")
        client = Client()

        response = client.post(reverse('rsvpStatusAPI'), {
            'userid': self.friend2.id,
            'statusid': self.status.id,
            'attending': 'true'
        })
        response = loadJson(response.content)

        response = client.post(reverse('getNewDataAPI'), {
            'userid': self.friend.id
        })
        response = loadJson(response.content)

        notifications = response['notifications']
        self.assertEqual(len(notifications), 1)

        notif = notifications[0]
        self.assertEqual(notif['type'], Notification.NOTIF_STATUS_MEMBERS_ADDED)
        self.assertEqual(notif['friendid'], self.friend2.id)
        self.assertEqual(notif['statusid'], self.status.id)

    def testNoDuplicateAttendingNotification(self):
        print("No Duplicate Attending Notification")
        client = Client()

        response = client.post(reverse('rsvpStatusAPI'), {
            'userid': self.friend2.id,
            'statusid': self.status.id,
            'attending': 'true'
        })

        response = client.post(reverse('rsvpStatusAPI'), {
            'userid': self.friend2.id,
            'statusid': self.status.id,
            'attending': 'false'
        })

        response = client.post(reverse('rsvpStatusAPI'), {
            'userid': self.friend2.id,
            'statusid': self.status.id,
            'attending': 'true'
        })

        response = client.post(reverse('rsvpStatusAPI'), {
            'userid': self.friend2.id,
            'statusid': self.status.id,
            'attending': 'false'
        })

        response = client.post(reverse('rsvpStatusAPI'), {
            'userid': self.friend2.id,
            'statusid': self.status.id,
            'attending': 'true'
        })

        response = client.post(reverse('getNewDataAPI'), {
            'userid': self.friend.id
        })
        response = loadJson(response.content)

        notifications = response['notifications']
        self.assertEqual(len(notifications), 1)

        notif = notifications[0]
        self.assertEqual(notif['type'], Notification.NOTIF_STATUS_MEMBERS_ADDED)
        self.assertEqual(notif['friendid'], self.friend2.id)
        self.assertEqual(notif['statusid'], self.status.id)

    def testInvitedToStatusNotification(self):
        print("Invited To Status Notification")
        client = Client()

        response = client.post(reverse('inviteToStatusAPI'), {
            'userid': self.user.id,
            'statusid': self.status.id,
            'friends': json.dumps([self.friend2.id, self.friend3.id])
        })

        response = client.post(reverse('getNewDataAPI'), {
            'userid': self.friend2.id
        })
        response = loadJson(response.content)

        notifications = response['notifications']
        self.assertEqual(len(notifications), 1)

        notif = notifications[0]

        self.assertEqual(notif['type'], Notification.NOTIF_INVITED)
        self.assertEqual(notif['friendid'], self.user.id)
        self.assertEqual(notif['statusid'], self.status.id)

    def testDeletedStatusNoNotification(self):
        print("Delete Status No Notification")
        client = Client()

        response = client.post(reverse('inviteToStatusAPI'), {
            'userid': self.user.id,
            'statusid': self.status.id,
            'friends': json.dumps([self.friend2.id, self.friend3.id])
        })

        response = client.post(reverse('getNewDataAPI'), {
            'userid': self.friend2.id
        })
        response = loadJson(response.content)

        notifications = response['notifications']
        self.assertEqual(len(notifications), 1)

        notif = notifications[0]

        self.assertEqual(notif['type'], Notification.NOTIF_INVITED)
        self.assertEqual(notif['friendid'], self.user.id)
        self.assertEqual(notif['statusid'], self.status.id)

        self.status.deleted = True
        self.status.save()

        response = client.post(reverse('getNewDataAPI'), {
            'userid': self.friend2.id
        })
        response = loadJson(response.content)

        notifications = response['notifications']
        self.assertEqual(len(notifications), 0)
