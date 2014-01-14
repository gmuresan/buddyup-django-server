from datetime import datetime, timedelta
import json
from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from django.core.urlresolvers import reverse
import facebook
import pytz
from django.test import TestCase, Client
from api import helpers
from api.FacebookProfile import FacebookProfile
from api.helpers import DATETIME_FORMAT, MICROSECOND_DATETIME_FORMAT, createFriendJsonObject
from buddyup import settings
from chat.models import Conversation, Message
from push_notifications.models import GCMDevice, APNSDevice
from status.helpers import createLocationJson
from status.models import Status, Poke, Location, StatusMessage, TimeSuggestion, LocationSuggestion
from userprofile.models import UserProfile, Group, Setting, FacebookUser

FB_TEST_USER_1_ID = "100007243621022"
FB_TEST_USER_2_ID = "100007247311000"
FB_TEST_USER_3_ID = "100007237111164"
FB_TEST_USER_4_ID = "100007225201630"


def performFacebookRegister(accessToken):
    client = Client()

    fb = FacebookProfile.getFacebookUserFromAuthKey(accessToken, 'android')
    return fb.userProfile


class FacebookRegisterTest(TestCase):
    def setUp(self):
        self.authKey = 'CAACBZAKw2g0ABAL2mqHRpyDvv3BxYajL2xKhykASyg28bRct3azYZAlISY6CautIFDBXLfB61p82MiuiQH4vf2rsPoTuRXJlJAvUdjeYJRDHviFqi6Ld6neT993PdZBLmDbUOl6pGzNlFlx1rP0uGOvZC34iLYYVcqQiSoAJ4MhgSlmXJBesvkGbfwKgQfpcOYLvuUT9igZDZD'
        self.firstName = 'George'
        self.lastName = 'Muresan'

    def testRegister(self):
        print "Register"
        client = Client()

        response = client.post(reverse('facebookLoginAPI'), {
            'fbauthkey': self.authKey,
            'device': 'android'
        })
        response = json.loads(response.content)
        self.assertEqual(response['success'], True)
        self.assertNotIn('error', response)
        self.assertEqual(response['firstname'], self.firstName)
        self.assertEqual(response['lastname'], self.lastName)

        userProfile = UserProfile.objects.get(pk=response['userid'])
        self.assertEqual(userProfile.user.first_name, self.firstName)
        self.assertEqual(userProfile.user.last_name, self.lastName)

    def testFacebookLoginWithFriends(self):
        print "FacebookLoginWithFriends"
        client = Client()

        user = User.objects.create(username='user1', password='0', email='user1', first_name='first', last_name='last')
        userprofile = UserProfile.objects.create(user=user)

        response = client.post(reverse('facebookLoginAPI'), {
            'fbauthkey': self.authKey,
            'device': 'android'
        })
        response = json.loads(response.content)

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
        response = json.loads(response.content)

        userprofileFriendData = {u'userid': userprofile.id, u'firstname': user.first_name, u'lastname': user.last_name,
                                 u'blocked': False}
        self.assertNotEqual(len(response['friends']), 0)
        for key, val in userprofileFriendData.items():
            self.assertEqual(val, userprofileFriendData[key])

    def testFacebookLoginWithAllData(self):
        print "FacebookLoginWithAllData"
        client = Client()

        response = client.post(reverse('facebookLoginAPI'), {
            'fbauthkey': self.authKey,
            'device': 'android'
        })
        response = json.loads(response.content)

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

        response = json.loads(response.content)

        self.assertTrue(response['success'])
        self.assertEqual(response['statuses'][0]['statusid'], friendStatus.id)
        self.assertEqual(response['groups'][0]['groupid'], group.id)
        self.assertEqual(response['mystatuses'][0]['statusid'], myStatus.id)
        self.assertEqual(response['friends'][0]['userid'], friendProfile.id)
        self.assertIn('chats', response)

    def testGetSettingsOnLogin(self):
        print "FacebookLoginWithSettings"
        client = Client()

        response = client.post(reverse('facebookLoginAPI'), {
            'fbauthkey': self.authKey,
            'device': 'android'
        })
        response = json.loads(response.content)

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
        response = json.loads(response.content)

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
        print "Post Status Message"
        client = Client()

        status = Status.objects.create(user=self.user, text=self.text, expires=self.expires)

        response = client.post(reverse('postStatusMessageAPI'), {
            'userid': self.user.id,
            'statusid': status.id,
            'text': self.text
        })

        response = json.loads(response.content)

        self.assertTrue(response['success'])

        messages = status.messages.all()

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].text, self.text)
        self.assertEqual(len(response['messages']), 1)

        messageId = response['messages'][0]['id']

        message = StatusMessage.objects.create(user=self.friend1, text='text', status=status)

        response = client.post(reverse('postStatusMessageAPI'), {
            'userid': self.user.id,
            'statusid': status.id,
            'text': 'text',
            'lastmessageid': messageId
        })

        response = json.loads(response.content)

        self.assertTrue(response['success'])
        self.assertEqual(len(response['messages']), 2)

    def testGetStatusDetails(self):
        print "Get Status Details"
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
        locationSuggestion = LocationSuggestion.objects.create(user=self.friend1, status=status, location=locationSuggested)
        status.locationSuggestions.add(locationSuggestion)

        response = client.post(reverse('postStatusMessageAPI'), {
            'userid': self.user.id,
            'statusid': status.id,
            'text': self.text
        })

        response = client.post(reverse('getStatusDetailsAPI'), {
            'statusid': status.id
        })
        response = json.loads(response.content)

        self.assertTrue(response['success'])
        self.assertEqual(len(response['messages']), 1)
        message = response['messages'][0]
        self.assertEqual(message['userid'], self.user.id)
        self.assertEqual(message['text'], self.text)

        self.assertEqual(len(response['fbinvited']), 2)
        self.assertEqual(len(response['invited']), 2)
        self.assertEqual(len(response['attending']), 1)
        self.assertEqual(len(response['fbattending']), 1)
        self.assertEqual(len(response['timesuggestions']), 1)
        self.assertEqual(len(response['locationsuggestions']), 1)

        self.assertIn(fbUser1.facebookUID, response['fbinvited'])
        self.assertIn(fbUser2.facebookUID, response['fbinvited'])
        self.assertIn(fbUser1.facebookUID, response['fbattending'])
        self.assertIn(self.friend2.id, response['invited'])
        self.assertIn(self.friend1.id, response['invited'])
        self.assertIn(self.friend1.id, response['attending'])

        timeSugg = response['timesuggestions'][0]
        locationSugg = response['locationsuggestions'][0]

        self.assertEqual(timeSugg['time'], timeSuggestion.dateSuggested.strftime(DATETIME_FORMAT))
        self.assertEqual(timeSugg['userid'], timeSuggestion.user.id)

        self.assertEqual(locationSugg['location'], createLocationJson(locationSuggestion.location))
        self.assertEqual(locationSugg['userid'], locationSuggestion.user.id)



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
        print "PostNoLocation"
        client = Client()

        response = client.post(reverse('postStatusAPI'), {
            'userid': self.user.id,
            'expires': self.expires.strftime(DATETIME_FORMAT),
            'text': self.text,
            'type': 'sports'
        })

        responseObj = json.loads(response.content)
        self.assertEqual(responseObj['success'], True)
        self.assertNotIn('error', responseObj)

        status = Status.objects.get(pk=responseObj['statusid'])

        self.assertEqual(status.user, self.user)
        #self.assertEqual(status.expires, self.expires)
        self.assertEqual(status.text, self.text)

    def testPostWithLocation(self):
        print "PostWithLocation"
        client = Client()

        response = client.post(reverse('postStatusAPI'), {
            'userid': self.user.id,
            'expires': self.expires.strftime(DATETIME_FORMAT),
            'text': self.text,
            'location': json.dumps(self.location),
            'type': 'food',
            'visibility': 'friendsoffriends'
        })

        response = json.loads(response.content)

        status = Status.objects.get(pk=response['statusid'])

        self.assertEqual(status.location.lat, self.location['lat'])
        self.assertEqual(status.location.lng, self.location['lng'])
        self.assertEqual(status.location.city, self.location['city'])
        self.assertEqual(status.location.state, self.location['state'])
        self.assertEqual(status.location.address, self.location['address'])
        self.assertEqual(status.location.venue, self.location['venue'])

    def testPostWithGroups(self):
        print "PostWithGroups"
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

        response = json.loads(response.content)

        status = Status.objects.get(pk=response['statusid'])

        self.assertTrue(response['success'])

        self.assertIn(self.group1, status.groups.all())
        self.assertIn(self.group1, status.groups.all())

    def testPostWithStartTime(self):
        print "PostWithStartTime"
        client = Client()

        response = client.post(reverse('postStatusAPI'), {
            'userid': self.user.id,
            'starts': self.expires.strftime(DATETIME_FORMAT),
            'text': self.text,
            'location': json.dumps(self.location),
            'visibility': 'friends'
        })

        response = json.loads(response.content)

        status = Status.objects.get(pk=response['statusid'])

        self.assertTrue(response['success'])

        self.assertEqual(self.expires.strftime(DATETIME_FORMAT), status.starts.strftime(DATETIME_FORMAT))

    def testPostCustomVisibility(self):
        print "Post Status Custom Visibility"
        client = Client()

        friends = [self.friend1.id, self.friend2.id]
        fbfriends = ['asfafafsafs', '1u989h108f1f']

        response = client.post(reverse('postStatusAPI'), {
            'userid': self.user.id,
            'starts': self.expires.strftime(DATETIME_FORMAT),
            'text': self.text,
            'location': json.dumps(self.location),
            'visibility': 'custom',
            'visiblityfriends': json.dumps(friends),
            'visibilityfbfriends': json.dumps(fbfriends),
        })

        response = json.loads(response.content)

        self.assertTrue(response['success'])


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

    def testShareStatusOnFacebook(self):
        client = Client()

        text = "Hangout at my house"

        expires = datetime.now(pytz.timezone("UTC"))
        expires = expires + timedelta(hours=1)

        lng = 42.341560
        lat = -83.501783
        address = '46894 spinning wheel'
        city = 'canton'
        state = 'MI'
        venue = "My house"
        location = {'lat': lat, 'lng': lng, 'address': address, 'state': state,
                    'city': city, 'venue': venue}

        response = client.post(reverse('postStatusAPI'), {
            'userid': self.user.id,
            'expires': expires.strftime(DATETIME_FORMAT),
            'text': text,
            'groupids': json.dumps([self.group.id]),
            'location': json.dumps(location)
        })

        response = json.loads(response.content)

        statusId = response['statusid']
        status = Status.objects.get(pk=statusId)

        fbProfile = FacebookProfile(self.user, self.accessTokenUser)
        response = fbProfile.shareStatus(status)


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
        print "DeleteStatus"
        client = Client()

        response = client.post(reverse('deleteStatusAPI'), {
            'userid': self.user1.id,
            'statusid': self.status1Id
        })

        response = json.loads(response.content)

        self.assertTrue(response['success'])

        with self.assertRaises(Status.DoesNotExist):
            Status.objects.get(pk=self.status1Id)

    def testDeleteOtherUserStatus(self):
        print "DeleteOtherUserStatus"
        client = Client()

        Status.objects.get(pk=self.status1Id)

        response = client.post(reverse('deleteStatusAPI'), {
            'userid': self.user2.id,
            'statusid': self.status1Id
        })

        response = json.loads(response.content)

        self.assertFalse(response['success'])

        Status.objects.get(pk=self.status1Id)

    def testGoOffline(self):
        print "GoOffline"
        client = Client()

        response = client.post(reverse('goOfflineAPI'), {
            'userid': self.user1.id
        })
        response = json.loads(response.content)

        self.assertTrue(response['success'])

        status1 = Status.objects.get(pk=self.status1Id)
        status2 = Status.objects.get(pk=self.status2Id)

        now = datetime.utcnow()

        self.assertTrue(status1.expires < now)
        self.assertTrue(status2.expires < now)

    def testCancelStatus(self):
        print "CancelStatus"
        client = Client()

        response = client.post(reverse('cancelStatusAPI'), {
            'userid': self.user1.id,
            'statusid': self.status1Id
        })
        response = json.loads(response.content)

        status1 = Status.objects.get(pk=self.status1Id)
        status2 = Status.objects.get(pk=self.status2Id)
        now = datetime.utcnow()

        self.assertTrue(response['success'])
        self.assertTrue(status1.expires < now)
        self.assertFalse(status2.expires < now)

    def testCancelOtherUserStatus(self):
        print "CancelOtherUserStatus"
        client = Client()

        Status.objects.get(pk=self.status1Id)

        response = client.post(reverse('cancelStatusAPI'), {
            'userid': self.user2.id,
            'statusid': self.status1Id
        })

        response = json.loads(response.content)

        self.assertFalse(response['success'])

        status = Status.objects.get(pk=self.status1Id)

        now = datetime.utcnow()
        self.assertFalse(status.expires < now)

    def testDeleteStatus(self):
        print "DeleteStatus"
        client = Client()

        response = client.post(reverse('deleteStatusAPI'), {
            'userid': self.user1.id,
            'statusid': self.status1Id
        })

        response = json.loads(response.content)

        with self.assertRaises(Status.DoesNotExist):
            Status.objects.get(pk=self.status1Id)

        self.assertTrue(response['success'])

    def testDeleteOtherUserStatus(self):
        print "DeleteOtherUserStatus"
        client = Client()

        response = client.post(reverse('cancelStatusAPI'), {
            'userid': self.user2.id,
            'statusid': self.status1Id
        })

        response = json.loads(response.content)

        self.assertFalse(response['success'])

        status = Status.objects.get(pk=self.status1Id)


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

        self.user1.save()
        self.user2.save()
        self.user3.save()

        self.lat = 42.341560
        self.lng = -83.501783
        self.address = '46894 spinning wheel'
        self.city = 'canton'
        self.state = 'MI'
        self.venue = "My house"
        self.expirationDate = datetime.utcnow() + timedelta(hours=2)
        self.startDate = datetime.utcnow() + timedelta(hours=1)

        self.location = Location.objects.create(lng=self.lng, lat=self.lat, point=Point(self.lng, self.lat),
                                                city=self.city, state=self.state, venue=self.venue)

    def testSingleStatus(self):
        print "SingleStatus"
        client = Client()

        status1 = Status.objects.create(user=self.user1, expires=self.expirationDate, text='Hang out',
                                        location=self.location, starts=self.startDate,
                                        visibility=Status.VIS_FRIENDS)

        myLat = 42.321620
        myLng = -83.507794
        since = datetime.utcnow() - timedelta(hours=1)

        response = client.get(reverse('getStatusesAPI'), {
            'userid': self.user2.id,
            'since': since.strftime(MICROSECOND_DATETIME_FORMAT),
        })

        response = json.loads(response.content)

        self.assertEqual(response['success'], True)
        self.assertNotIn('error', response)
        self.assertEqual(len(response['statuses']), 1)
        self.assertEqual(response['statuses'][0]['text'], status1.text)
        self.assertEqual(response['statuses'][0]['dateexpires'], self.expirationDate.strftime(DATETIME_FORMAT))
        self.assertEqual(response['statuses'][0]['datestarts'], self.startDate.strftime(DATETIME_FORMAT))

        statusDate = response['statuses'][0]['datecreated']
        self.assertEqual(statusDate, status1.date.strftime(DATETIME_FORMAT))

    def testCustomVisibility(self):
        print "Get Status Custom Visibility"
        client = Client()

        status = Status.objects.create(user=self.user1, expires=self.expirationDate, text='text', starts=self.startDate,
                                       visibility=Status.VIS_CUSTOM)
        status.friendsVisible.add(self.user2)

        response = client.get(reverse('getStatusesAPI'), {
            'userid': self.user2.id
        })
        response = json.loads(response.content)

        self.assertTrue(response['success'])
        statuses = response['statuses']
        self.assertEqual(len(statuses), 1)

        response = client.get(reverse('getStatusesAPI'), {
            'userid': self.user3.id
        })
        response = json.loads(response.content)

        self.assertTrue(response['success'])
        statuses = response['statuses']
        self.assertEqual(len(statuses), 0)

    def testFriendsVisibility(self):
        print "Get Status Friends Visibility"
        client = Client()

        status = Status.objects.create(user=self.user2, expires=self.expirationDate, text='text', starts=self.startDate,
                                       visibility=Status.VIS_FRIENDS)

        response = client.get(reverse('getStatusesAPI'), {
            'userid': self.user1.id
        })
        response = json.loads(response.content)

        self.assertTrue(response['success'])
        statuses = response['statuses']
        self.assertEqual(len(statuses), 1)

        response = client.get(reverse('getStatusesAPI'), {
            'userid': self.user3.id
        })
        response = json.loads(response.content)

        self.assertTrue(response['success'])
        statuses = response['statuses']
        self.assertEqual(len(statuses), 0)

    def testFriendsOfFriendsVisibility(self):
        print "Get Status Friends of Friends Visibility"
        client = Client()

        status = Status.objects.create(user=self.user2, expires=self.expirationDate, text='text', starts=self.startDate,
                                       visibility=Status.VIS_FRIENDS_OF_FRIENDS)

        response = client.get(reverse('getStatusesAPI'), {
            'userid': self.user1.id
        })
        response = json.loads(response.content)

        self.assertTrue(response['success'])
        statuses = response['statuses']
        self.assertEqual(len(statuses), 1)

        response = client.get(reverse('getStatusesAPI'), {
            'userid': self.user3.id
        })
        response = json.loads(response.content)

        self.assertTrue(response['success'])
        statuses = response['statuses']
        self.assertEqual(len(statuses), 1)

    def testPublicVisibility(self):
        print "Get Status Public Visibility"
        client = Client()

        status = Status.objects.create(user=self.user4, expires=self.expirationDate, text='text', starts=self.startDate,
                                       visibility=Status.VIS_PUBLIC, location=self.location)


        # location right next to status
        response = client.get(reverse('getStatusesAPI'), {
            'userid': self.user1.id,
            'lat': str(self.location.lat + .01),
            'lng': str(self.location.lng + .01),
            'radius': 50
        })
        response = json.loads(response.content)

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
        response = json.loads(response.content)

        self.assertTrue(response['success'])
        statuses = response['statuses']
        self.assertEqual(len(statuses), 0)

        # should not see public statuses if lat and lng are not provided
        response = client.get(reverse('getStatusesAPI'), {
            'userid': self.user1.id,
            'radius': 50
        })
        response = json.loads(response.content)

        self.assertTrue(response['success'])
        statuses = response['statuses']
        self.assertEqual(len(statuses), 0)

    def testGetStatusDetails(self):
        print "Get Status Details"
        client = Client()

        status1 = Status.objects.create(user=self.user1, expires=self.expirationDate, text='Hang out',
                                        location=self.location, starts=self.startDate,
                                        visibility=Status.VIS_FRIENDS)

        response = client.post(reverse('getStatusDetailsAPI'), {
            'statusid': status1.id
        })
        response = json.loads(response.content)

        self.assertTrue(response['success'])


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
        print "GetMyStatuses"
        client = Client()

        response = client.post(reverse('getMyStatusesAPI'), {
            'userid': self.user1.id
        })

        response = json.loads(response.content)
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
        print "Poke"
        client = Client()

        response = client.post(reverse('pokeAPI'), {
            'userid': self.user1.id,
            'friendid': self.user2.id
        })

        response = json.loads(response.content)

        self.assertEqual(response['success'], True)

        response = client.post(reverse('pokeAPI'), {
            'userid': self.user1.id,
            'friendid': self.user2.id
        })

        response = json.loads(response.content)
        self.assertNotIn('pokeid', response)
        self.assertEqual(response['success'], False)
        self.assertIsNotNone(response['error'])

    def testPokeInLogin(self):
        print "PokeInLogin"
        client = Client()

        response = client.post(reverse('pokeAPI'), {
            'userid': self.user1.id,
            'friendid': self.user2.id
        })

        response = json.loads(response.content)

        self.assertEqual(response['success'], True)

        friendObj = createFriendJsonObject(self.user2, False, self.user1)

        pokeTime = friendObj['lastpoketime']
        lastPoke = Poke.objects.filter(sender=self.user1, recipient=self.user2).latest()
        lastPokeTime = lastPoke.created.strftime(DATETIME_FORMAT)

        self.assertEqual(lastPokeTime, pokeTime)


class ConversationTests(TestCase):
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

        nonFriend = User.objects.create(username='nonFriend', password='0', email='nonFriend')
        self.nonFriend = UserProfile.objects.create(user=nonFriend)

        blockedFriend = User.objects.create(username='blockedFriend', password='0', email='blockedFriend')
        self.blockedFriend = UserProfile.objects.create(user=blockedFriend)

        self.blockedFriend.friends.add(self.user)
        self.blockedFriend.blockedFriends.add(self.user)
        self.blockedFriend.save()

        self.user.friends.add(self.blockedFriend)
        self.user.save()

    def testCreateConversation(self):
        print "CreateConversation"
        client = Client()

        response = client.post(reverse('createChatAPI'), {
            'userid': self.user.id,
            'friendid': self.friend.id
        })

        response = json.loads(response.content)
        chatid = response['chatid']

        self.assertEqual(response['success'], True)
        self.assertNotIn('error', response)

        conversation = Conversation.objects.get(pk=chatid)
        members = conversation.members.all()
        self.assertTrue(self.user in members)
        self.assertTrue(self.friend in members)

    def testCreateConversationWithMultipleFriends(self):
        print "CreateConversationWithMultipleFriends"
        client = Client()

        friendids = [self.friend.id, self.friend2.id]
        response = client.post(reverse('createChatAPI'), {
            'userid': self.user.id,
            'friendid': json.dumps(friendids)
        })

        response = json.loads(response.content)
        chatid = response['chatid']

        self.assertEqual(response['success'], True)
        self.assertNotIn('error', response)

        conversation = Conversation.objects.get(pk=chatid)
        members = conversation.members.all()
        self.assertTrue(self.user in members)
        self.assertTrue(self.friend in members)
        self.assertTrue(self.friend2 in members)

    def testCreateConverationWithNonFriend(self):
        print "CreateConversationWithNonFriend"
        client = Client()

        response = client.post(reverse('createChatAPI'), {
            'userid': self.user.id,
            'friendid': self.nonFriend.id
        })

        response = json.loads(response.content)
        self.assertEqual(response['success'], False)
        self.assertIn('error', response)

    def testCreateConversationWithBlockedFriend(self):
        print "CreateConversationWithBlockedFriend"
        client = Client()

        response = client.post(reverse('createChatAPI'), {
            'userid': self.user.id,
            'friendid': self.blockedFriend.id
        })

        response = json.loads(response.content)
        self.assertEqual(response['success'], True)

        chatid = response['chatid']

        chat = Conversation.objects.get(pk=chatid)

        self.assertEqual(len(chat.members.all()), 1)
        self.assertNotIn(self.blockedFriend, chat.members.all())

    def testChatInvite(self):
        print "ChatInvite"
        client = Client()

        response = client.post(reverse('createChatAPI'), {
            'userid': self.user.id,
            'friendid': self.friend.id
        })

        response = json.loads(response.content)
        chatid = response['chatid']

        response = client.post(reverse('inviteToChatAPI'), {'userid': self.user.id,
                                                            'friendid': self.friend2.id,
                                                            'chatid': chatid})
        response = json.loads(response.content)

        self.assertEqual(response['success'], True)
        self.assertNotIn('error', response)

        conversation = Conversation.objects.get(pk=chatid)
        members = conversation.members.all()
        self.assertTrue(self.user in members)
        self.assertTrue(self.friend in members)
        self.assertTrue(self.friend2 in members)

    def testMutlipleFriendChatInvite(self):
        print "MultipleFriendChatInvite"
        client = Client()

        response = client.post(reverse('createChatAPI'), {
            'userid': self.user.id,
            'friendid': self.friend.id
        })

        response = json.loads(response.content)
        chatid = response['chatid']

        friendids = [self.friend2.id, self.friend3.id]
        response = client.post(reverse('inviteToChatAPI'), {'userid': self.user.id,
                                                            'friendids': json.dumps(friendids),
                                                            'chatid': chatid})
        response = json.loads(response.content)

        self.assertEqual(response['success'], True)
        self.assertNotIn('error', response)

        conversation = Conversation.objects.get(pk=chatid)
        members = conversation.members.all()
        self.assertTrue(self.user in members)
        self.assertTrue(self.friend in members)
        self.assertTrue(self.friend2 in members)
        self.assertIn(self.friend3, members)

    def testChatInviteNonFriend(self):
        print "ChatInviteNonFriend"
        client = Client()

        response = client.post(reverse('createChatAPI'), {
            'userid': self.user.id,
            'friendid': self.friend.id
        })

        response = json.loads(response.content)
        chatid = response['chatid']

        response = client.post(reverse('inviteToChatAPI'), {
            'userid': self.user.id,
            'friendid': self.nonFriend.id,
            'chatid': chatid
        })

        response = json.loads(response.content)
        self.assertEqual(response['success'], False)
        self.assertIn('error', response)

    def testChatInviteBlockedFriend(self):
        print "ChatInviteBlockedFriend"
        client = Client()

        response = client.post(reverse('createChatAPI'), {
            'userid': self.user.id,
            'friendid': self.friend.id
        })

        response = json.loads(response.content)
        chatid = response['chatid']

        response = client.post(reverse('inviteToChatAPI'), {
            'userid': self.user.id,
            'friendid': self.blockedFriend.id,
            'chatid': chatid
        })

        response = json.loads(response.content)
        self.assertEqual(response['success'], False)
        self.assertIn('error', response)

    def testLeaveChat(self):
        print "LeaveChat"
        client = Client()

        response = client.post(reverse('createChatAPI'), {
            'userid': self.user.id,
            'friendid': self.friend.id
        })
        response = json.loads(response.content)
        chatid = response['chatid']

        response = client.post(reverse('leaveChatAPI'), {
            'userid': self.user.id,
            'chatid': chatid
        })
        response = json.loads(response.content)

        self.assertEqual(response['success'], True)
        self.assertNotIn('error', response)

        convo = Conversation.objects.get(pk=chatid)
        members = convo.members.all()
        self.assertTrue(self.user not in members)
        self.assertTrue(self.friend in members)

    def testLeaveInvalidChat(self):
        print "LeaveInvalidChat"
        client = Client()

        response = client.post(reverse('leaveChatAPI'), {
            'userid': self.user.id,
            'chatid': 1
        })
        response = json.loads(response.content)

        self.assertEqual(response['success'], False)
        self.assertIn('error', response)

    def testLastPersonToLeaveChat(self):
        print "LastPersonToLeaveChat"
        client = Client()

        response = client.post(reverse('createChatAPI'), {
            'userid': self.user.id,
            'friendid': self.friend.id
        })
        response = json.loads(response.content)
        chatid = response['chatid']

        client.post(reverse('leaveChatAPI'), {
            'userid': self.user.id,
            'chatid': chatid
        })

        client.post(reverse('leaveChatAPI'), {
            'userid': self.friend.id,
            'chatid': chatid
        })

        convo = Conversation.objects.filter(pk=chatid)

        self.assertEqual(convo.count(), 0)


class ChatMessageTests(TestCase):
    def setUp(self):
        user = User.objects.create(username='user', password='0', email='user', first_name="user", last_name="one")
        self.user = UserProfile.objects.create(user=user)

        friend = User.objects.create(username='friend', password='0', email='friend', first_name="user",
                                     last_name="two")
        self.friend = UserProfile.objects.create(user=friend)

        self.user.friends.add(self.friend)
        self.friend.friends.add(self.user)

        friend2 = User.objects.create(username='friend2', password='0', email='friend2', first_name="user",
                                      last_name="three")
        self.friend2 = UserProfile.objects.create(user=friend2)

        self.user.friends.add(self.friend2)
        self.friend2.friends.add(self.user)

    def testSendMessage(self):
        print "SendMessage"
        client = Client()

        response = client.post(reverse('createChatAPI'), {
            'userid': self.user.id,
            'friendid': self.friend.id
        })

        response = json.loads(response.content)
        chatid = response['chatid']

        response = client.post(reverse('sendMessageAPI'), {
            'userid': self.user.id,
            'chatid': chatid,
            'text': 'hello'
        })
        response = json.loads(response.content)

        self.assertEqual(response['success'], True)

        convo = Conversation.objects.get(pk=chatid)
        message = convo.messages.latest('created')

        self.assertEqual(message.user, self.user)
        self.assertEqual(message.text, 'hello')
        self.assertEqual(message.conversation, convo)
        self.assertIn('chats', response)
        self.assertIn('newsince', response)

    def testGetSingleMessage(self):
        print "GetSingleMessage"
        client = Client()

        response = client.post(reverse('createChatAPI'), {
            'userid': self.user.id,
            'friendid': self.friend.id
        })

        response = json.loads(response.content)
        chatid = response['chatid']

        client.post(reverse('sendMessageAPI'), {
            'userid': self.user.id,
            'chatid': chatid,
            'text': 'hello'
        })

        since = datetime.utcnow() - timedelta(hours=1)

        response = client.post(reverse('getMessagesAPI'), {
            'userid': self.friend.id,
            'since': since.strftime(MICROSECOND_DATETIME_FORMAT)
        })

        response = json.loads(response.content)

        self.assertEqual(len(response['chats']), 1)
        self.assertEqual(response['success'], True)
        self.assertNotIn('error', response)

        convo = Conversation.objects.get(pk=chatid)
        convoMessage = convo.messages.latest('created')

        chatResponse = response['chats'][0]
        messageResponse = chatResponse['messages'][0]

        self.assertEqual(messageResponse['messageid'], convoMessage.id)
        self.assertEqual(chatResponse['chatid'], convo.id)
        self.assertEqual(messageResponse['text'], convoMessage.text)
        self.assertEqual(messageResponse['userid'], convoMessage.user.id)


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
        print "CreateGroup"

        client = Client()
        groupName = "group1"

        response = client.post(reverse('createGroupAPI'), {
            'userid': self.user.id,
            'groupname': groupName
        })
        response = json.loads(response.content)

        groupid = response['groupid']
        group = self.user.groups.latest('id')
        self.assertEqual(response['success'], True)
        self.assertNotIn('error', response)
        self.assertEqual(group.id, groupid)

    def testCreateGroupDuplicateName(self):
        print "CreateGroupDuplicateName"

        client = Client()
        groupName = "group1"

        client.post(reverse('createGroupAPI'), {
            'userid': self.user.id,
            'groupname': groupName
        })

        response = client.post(reverse('createGroupAPI'), {
            'userid': self.user.id,
            'groupname': groupName
        })
        response = json.loads(response.content)
        self.assertEqual(response['success'], False)
        self.assertIn('error', response)

    def testDeleteGroup(self):
        print "DeleteGroup"

        client = Client()
        groupName = "group1"

        response = client.post(reverse('createGroupAPI'), {
            'userid': self.user.id,
            'groupname': groupName
        })

        response = json.loads(response.content)
        groupid = response['groupid']

        response = client.post(reverse('deleteGroupAPI'), {
            'userid': self.user.id,
            'groupid': groupid
        })

        response = json.loads(response.content)
        self.assertEqual(response['success'], True)
        self.assertNotIn('error', response)

        with self.assertRaises(Group.DoesNotExist):
            Group.objects.get(pk=groupid)

    def testDeleteOtherUserGroup(self):
        print "DeleteOtherUserGroup"

        client = Client()
        groupName = "group1"

        response = client.post(reverse('createGroupAPI'), {
            'userid': self.user.id,
            'groupname': groupName
        })

        response = json.loads(response.content)
        groupid = response['groupid']

        response = client.post(reverse('deleteGroupAPI'), {
            'userid': self.friend.id,
            'groupid': groupid
        })
        response = json.loads(response.content)

        self.assertFalse(response['success'])
        self.assertIn('error', response)

    def testEditGroupName(self):
        print "EditGroupName"

        client = Client()
        groupName = "group1"
        newGroupName = "group2"

        response = client.post(reverse('createGroupAPI'), {
            'userid': self.user.id,
            'groupname': groupName
        })

        response = json.loads(response.content)
        groupid = response['groupid']

        response = client.post(reverse('editGroupNameAPI'), {
            'userid': self.user.id,
            'groupid': groupid,
            'groupname': newGroupName
        })
        response = json.loads(response.content)

        self.assertTrue(response['success'])

        group = Group.objects.get(pk=groupid)
        self.assertEqual(group.name, newGroupName)

    def testEditOtherUserGroupName(self):
        print "EditOtherUserGroupName"

        client = Client()
        groupName = "group1"
        newGroupName = "group2"

        response = client.post(reverse('createGroupAPI'), {
            'userid': self.user.id,
            'groupname': groupName
        })

        response = json.loads(response.content)
        groupid = response['groupid']

        response = client.post(reverse('editGroupNameAPI'), {
            'userid': self.friend.id,
            'groupid': groupid,
            'groupname': newGroupName
        })
        response = json.loads(response.content)

        self.assertFalse(response['success'])
        self.assertIn('error', response)

        group = Group.objects.get(pk=groupid)
        self.assertEqual(group.name, groupName)

    def testAddGroupMembers(self):
        print "AddGroupMembers"

        client = Client()
        groupName = "group1"

        response = client.post(reverse('createGroupAPI'), {
            'userid': self.user.id,
            'groupname': groupName
        })

        response = json.loads(response.content)
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
        response = json.loads(response.content)

        self.assertTrue(response['success'])

        group = Group.objects.get(pk=groupid)
        members = group.members.all()

        self.assertIn(self.friend, members)
        self.assertIn(self.friend2, members)

    def testRemoveGroupMembers(self):
        print "RemoveGroupMembers"

        client = Client()
        groupName = "group1"

        response = client.post(reverse('createGroupAPI'), {
            'userid': self.user.id,
            'groupname': groupName
        })

        response = json.loads(response.content)
        groupid = response['groupid']

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
        response = json.loads(response.content)

        self.assertTrue(response['success'])

        group = Group.objects.get(pk=groupid)
        members = group.members.all()

        self.assertNotIn(self.friend, members)
        self.assertNotIn(self.friend2, members)

        response = client.post(reverse('removeGroupMemberAPI'), {
            'userid': self.user.id,
            'friendid': self.friend.id,
            'groupid': groupid
        })
        response = json.loads(response.content)

        self.assertTrue(response['success'])

    def testGetGroups(self):
        print "GetGroups"
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
        response = json.loads(response.content)

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
        print "SetGroups"
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
        response = json.loads(response.content)

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
        response = json.loads(response.content)

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
        response = json.loads(response.content)

        self.assertEqual(response['success'], True)
        self.assertTrue(self.friend not in group1.members.all())
        self.assertTrue(self.friend not in group2.members.all())
        self.assertTrue(self.friend not in group3.members.all())

    def testSetGroupMembers(self):
        print "SetGroupMembers"
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

        members1 = [self.friend.id, self.friend2.id]
        members2 = []

        response = client.post(reverse('setGroupMembersAPI'), {
            'userid': self.user.id,
            'groupid': group1.id,
            'friendids': json.dumps(members1)
        })
        response = json.loads(response.content)

        self.assertTrue(response['success'])

        self.assertTrue(self.friend in group1.members.all())
        self.assertTrue(self.friend2 in group1.members.all())

        response = client.post(reverse('setGroupMembersAPI'), {
            'userid': self.user.id,
            'groupid': group2.id,
            'friendids': json.dumps(members2)
        })
        response = json.loads(response.content)

        self.assertTrue(response['success'])
        self.assertTrue(self.friend not in group2.members.all())
        self.assertTrue(self.friend2 not in group2.members.all())


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
        print "GetFriends"

        client = Client()

        response = client.post(reverse('getFriendsAPI'), {
            'userid': self.user.id
        })
        response = json.loads(response.content)

        self.assertTrue(response['success'])

        friends = response['friends']
        self.assertEqual(len(friends), 2)

        friend1 = {'userid': self.friend.id, 'firstname': self.friend.user.first_name,
                   'lastname': self.friend.user.last_name, 'blocked': False, 'facebookid': self.friend.facebookUID}
        friend2 = {'userid': self.friend2.id, 'firstname': self.friend2.user.first_name,
                   'lastname': self.friend2.user.last_name, 'blocked': False,
                   'facebookid': self.friend2.facebookUID}

        self.assertIn(friend1, friends)
        self.assertIn(friend2, friends)

    def testBlockFriends(self):
        print "BlockFriends"

        client = Client()

        client.post(reverse('blockFriendAPI'), {
            'userid': self.user.id,
            'friendid': self.friend.id
        })

        response = client.post(reverse('blockFriendAPI'), {
            'userid': self.user.id,
            'friendid': self.friend2.id
        })
        response = json.loads(response.content)

        self.assertTrue(response['success'])

        self.assertIn(self.friend, self.user.blockedFriends.all())
        self.assertIn(self.friend2, self.user.blockedFriends.all())

    def testUnblockFriends(self):
        print "UnblockFriends"

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
        response = json.loads(response.content)

        self.assertTrue(response['success'])

        self.assertNotIn(self.friend, self.user.blockedFriends.all())
        self.assertNotIn(self.friend2, self.user.blockedFriends.all())


class FeedbackTests(TestCase):
    def setUp(self):
        user = User.objects.create(username='user', password='0', email='user')
        self.user = UserProfile.objects.create(user=user)

    def testSubmitFeedback(self):
        print "SubmitFeedback"

        client = Client()
        text = "I think this app is very useful and well made"

        response = client.post(reverse('submitFeedbackAPI'), {
            'userid': self.user.id,
            'text': text
        })
        response = json.loads(response.content)

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
        print "GetNewData"

        client = Client()

        response = client.post(reverse('getNewDataAPI'), {
            'userid': self.user.id,
        })

        response = json.loads(response.content)

        self.assertTrue(response['success'])
        self.assertEqual(len(response['chats'][0]['messages']), 1)

        response = client.post(reverse('getNewDataAPI'), {
            'userid': self.user.id,
            'since': response['newsince'],
        })

        response = json.loads(response.content)

        self.assertTrue(response['success'])
        self.assertEqual(len(response['chats']), 0)

    def testGetPokes(self):
        print "GetPokes"

        client = Client()

        response = client.post(reverse('pokeAPI'), {
            'userid': self.friend.id,
            'friendid': self.user.id
        })

        response = json.loads(response.content)

        self.assertTrue(response['success'])

        response = client.post(reverse('getNewDataAPI'), {
            'userid': self.user.id
        })

        response = json.loads(response.content)

        self.assertTrue(response['success'])

        pokes = response['pokes']
        poke1 = pokes[0]

        self.assertEqual(poke1, self.friend.id)

        newSince = response['newsince']

        response = client.post(reverse('getNewDataAPI'), {
            'userid': self.user.id,
            'since': newSince
        })

        response = json.loads(response.content)

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
        print "SetSetting"

        client = Client()

        response = client.post(reverse('setSettingAPI'), {
            'userid': self.user.id,
            'key': self.key1,
            'value': 'value2'
        })
        response = json.loads(response.content)

        self.assertTrue(response['success'])

        setting1 = self.user.settings.get(key=self.key1)
        self.assertEqual(setting1.value, 'value2')

        response = client.post(reverse('setSettingAPI'), {
            'userid': self.user.id,
            'key': self.key2,
            'value': 'value3'
        })
        response = json.loads(response.content)

        setting2 = self.user.settings.get(key=self.key2)
        self.assertTrue(response['success'])
        self.assertEqual(setting2.value, 'value3')


    def testGetSetting(self):
        print "GetSetting"

        client = Client()

        response = client.post(reverse('getSettingAPI'), {
            'userid': self.user.id,
            'key': self.setting1.key
        })

        response = json.loads(response.content)

        self.assertTrue(response['success'])
        self.assertEqual(self.setting1.value, response['value'])

    def testGetBlankSetting(self):
        print "GetBlankSetting"

        client = Client()

        response = client.post(reverse('getSettingAPI'), {
            'userid': self.user.id,
            'key': 'nokey'
        })

        response = json.loads(response.content)

        self.assertTrue(response['success'])
        self.assertEqual('', response['value'])


class PushNotificationTests(TestCase):
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

        self.convo = Conversation.objects.create()
        self.convo.members.add(self.user, self.friend, self.friend2, self.friend3)

        self.message = Message.objects.create(user=self.user, text='Hello', conversation=self.convo)
        self.convo.save()

        self.friend1Device = APNSDevice.objects.create(user=self.friend,
                                                       registration_id="ef4a0cc519a800ab0f56356135ca98a0d22528f4a1277534295af02684df0bed")

        self.friend2Device = GCMDevice.objects.create(user=self.friend2,
                                                      registration_id="APA91bH7XrOXRl4pdORQVM_ISWWr1FrcaAkuCS9BYJMStNqSTdO70wqUc2pAc8ty82jlPaED9m3SX92Oj1CVMKT-qTLNDqXz5M_LQDMOdDJgl2JcQuQEAzddJLpOGvSzu13Xb2sJdbTN90GkFVH3u82j06oJljPr5w")

        self.pokeObj = Poke.objects.create(sender=self.user, recipient=self.friend2)

    def testSimpleChatNotification(self):
        pass
        #print "Chat Push Notification"

        #androidResponse, iosResponse = sendChatNotificationsSynchronous(self.message)
        #print androidResponse
        #print iosResponse

    def testPokeNotification(self):
        pass
        #print "Poke Push Notification"

        #androidResponse, iosResponse = sendPokeNotificationSynchronous(self.pokeObj)
        #print androidResponse
        # print iosResponse

    def testRegisterToken(self):
        print "Resgister Push Notification Token"
        client = Client()

        iosToken = 'asfafqwf1f13f1f'
        androidToken = 'asff1fh881f9h1fh1ifh'

        response = client.post(reverse('registerPushNotificationsAPI'), {
            'userid': self.friend.id,
            'token': iosToken,
            'platform': 'ios'
        })

        response = json.loads(response.content)

        self.assertTrue(response['success'])

        response = client.post(reverse('registerPushNotificationsAPI'), {
            'userid': self.friend.id,
            'token': androidToken,
            'platform': 'android'
        })

        response = json.loads(response.content)

        self.assertTrue(response['success'])

        androidDevice = GCMDevice.objects.get(user=self.friend, registration_id=androidToken)
        iosDevice = APNSDevice.objects.get(user=self.friend, registration_id=iosToken)
