from compiler.ast import name
from datetime import datetime, timedelta
import json
import pdb
from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.core.urlresolvers import reverse
import facebook
import pytz
from django.test import TestCase, Client
from api import helpers
from api.FacebookProfile import FacebookProfile
from api.helpers import DATETIME_FORMAT, MICROSECOND_DATETIME_FORMAT
from buddyup import settings
from chat.models import Conversation, Message
from status.models import Status, Poke, Location
from userprofile.models import UserProfile, Group, Feedback, Setting

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
        self.authKey = 'CAACBZAKw2g0ABAF5d2GPrfKoKWmvY3w5RUqj405euuuZB0iHysgSGZAXZCojHGDqm8m2sl0PbK0bL7duvYaZAwZAbRADPXFzX2GN0LlVM5Ttjj9l8rkh55eqxb9Hh27B00XFa3PoLrsVFUxDfcdjYDzYTf0NWgbsp5tvqZBkJNxZATclqtjjau44spKWhp9qlSQDZAPZAjcFMjFAZDZD'
        self.firstName = 'George'
        self.lastName = 'Muresan'

    def testRegister(self):
        print "Register"
        client = Client()

        response = client.post(reverse('facebookRegisterAPI'), {
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

        response = client.post(reverse('facebookRegisterAPI'), {
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

        response = client.post(reverse('facebookRegisterAPI'), {
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
            'key': 'key1',
            'value': 'value1'
        })

        client.post(reverse('setSettingAPI'), {
            'userid': user.id,
            'key': 'key2',
            'value': 'value2'
        })

        response = client.post(reverse('facebookLoginAPI'), {
            'fbauthkey': self.authKey,
            'device': 'android'
        })
        response = json.loads(response.content)

        self.assertTrue(response['success'])
        self.assertEqual(len(response['settings']), 2)
        setting1 = response['settings']['key1']
        setting2 = response['settings']['key2']

        self.assertEqual(setting1, 'value1')
        self.assertEqual(setting2, 'value2')


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
            'text': self.text
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
            'location': json.dumps(self.location)
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
            "groupids": json.dumps(groupids)
        })

        response = json.loads(response.content)

        status = Status.objects.get(pk=response['statusid'])

        self.assertTrue(response['success'])

        self.assertIn(self.group1, status.groups.all())
        self.assertIn(self.group1, status.groups.all())


class facebookShareStatusTests(TestCase):
    def setUp(self):
        fb = facebook.GraphAPI()
        appAccessToken = helpers.getFacebookAppAccessToken()
        testUsers = fb.request(settings.FACEBOOK_APP_ID + '/accounts/test-users', {'access_token': str(appAccessToken), })
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


class getStatusesTest(TestCase):
    # TODO: create a test for testing that the location is present in the status
    def setUp(self):
        user1 = User.objects.create(username='user1', password='0', email='user1')
        self.user1 = UserProfile.objects.create(user=user1)

        user2 = User.objects.create(username='user2', password='0', email='user2')
        self.user2 = UserProfile.objects.create(user=user2)

        self.user1.friends.add(self.user2)
        self.user2.friends.add(self.user1)

        self.user1.save()
        self.user2.save()

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

    def testSingleStatus(self):
        print "SingleStatus"
        client = Client()

        myLat = 42.321620
        myLng = -83.507794
        since = datetime.utcnow() - timedelta(hours=1)

        response = client.get(reverse('api.views.getStatuses'), {
            'userid': self.user2.id,
            'since': since.strftime(MICROSECOND_DATETIME_FORMAT),
        })

        response = json.loads(response.content)

        self.assertEqual(response['success'], True)
        self.assertNotIn('error', response)
        self.assertEqual(len(response['statuses']), 1)
        self.assertEqual(response['statuses'][0]['text'], self.status1.text)
        self.assertEqual(response['statuses'][0]['dateexpires'], self.expirationDate.strftime(DATETIME_FORMAT))

        statusDate = response['statuses'][0]['datecreated']
        self.assertEqual(statusDate, self.status1.date.strftime(DATETIME_FORMAT))

    def testGetStatusesWithGroups(self):
        print "GetStatusesWithGroups"

        group1 = Group.objects.create(name="group1", user=self.user1)
        group1.members.add(self.user2)
        group1.save()

        group2 = Group.objects.create(name="group2", user=self.user1)

        group1StatusText = 'group1StatusText'
        group1Status = Status.objects.create(user=self.user1, expires=self.expirationDate, location=self.location,
                                             text=group1StatusText)
        group1Status.groups.add(group1)
        group1Status.save()

        group2StatusText = "group2StatusText"
        group2Status = Status.objects.create(user=self.user1, expires=self.expirationDate, location=self.location,
                                             text=group2StatusText)
        group2Status.groups.add(group2)
        group2Status.save()

        client = Client()

        since = datetime.utcnow() - timedelta(hours=1)

        response = client.get(reverse('api.views.getStatuses'), {
            'userid': self.user2.id,
            'since': since.strftime(MICROSECOND_DATETIME_FORMAT),
            'lat': self.lat,
            'lng': self.lng
        })

        response = json.loads(response.content)

        self.assertEqual(len(response['statuses']), 2)

        group1StatusFound = False
        for status in response['statuses']:
            self.assertNotEqual(status['text'], group2StatusText)
            if status['text'] == group1StatusText:
                group1StatusFound = True
        self.assertTrue(group1StatusFound)


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

        response = client.post('/api/poke/', {
            'userid': self.user1.id,
            'friendid': self.user2.id
        })

        response = json.loads(response.content)

        self.assertEqual(response['success'], True)

        response = client.post('/api/poke/', {
            'userid': self.user1.id,
            'friendid': self.user2.id
        })

        response = json.loads(response.content)
        self.assertNotIn('pokeid', response)
        self.assertEqual(response['success'], False)
        self.assertIsNotNone(response['error'])


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


class GetNewDataTests(TestCase):
    def setUp(self):
        user = User.objects.create(username='user', password='0', email='user')
        self.user = UserProfile.objects.create(user=user)

        self.setting1 = Setting.objects.create(user=self.user, value="value1", key="key1")

    def testSetSetting(self):
        print "SetSetting"

        client = Client()

        response = client.post(reverse('setSettingAPI'), {
            'userid': self.user.id,
            'key': 'key2',
            'value': 'value2'
        })
        response = json.loads(response.content)

        self.assertTrue(response['success'])

        setting2 = self.user.settings.get(key='key2')
        self.assertEqual(setting2.value, 'value2')

        response = client.post(reverse('setSettingAPI'), {
            'userid': self.user.id,
            'key': 'key2',
            'value': 'value3'
        })
        response = json.loads(response.content)

        setting2 = self.user.settings.get(key='key2')
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