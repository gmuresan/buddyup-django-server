"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
import json
from datetime import datetime, timedelta
from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from django.core.urlresolvers import reverse

from django.test import TestCase, Client
from api.helpers import loadJson
from status.models import Location, Status
from userprofile.models import UserProfile, Group


class FacebookRegisterTest(TestCase):
    def setUp(self):
        self.authKey = 'CAACBZAKw2g0ABAIUJUTmug0ZB9x7EETEYhojqnGH1MF2q4ZCpUFO85ZCvtqc4sKFfvRrqpjAZBLMcSLUZBhSrMga3CbVzshqpwXGofZCIjsCsUhW2xFUoUCVyjmed0iAj422YqryToDhhDFmtiJqdfIoK2cZACiWeOkSOZBREk1IXnTWXaoZBVwfwXewxZCZB4nVr7YZD'
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
            group = Group.objects.get(user=userProfile, name="Favorites")
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
        self.assertEqual(response['groups'][1]['groupid'], group.id)
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

    def testRefreshFacebookFriends(self):
        print("refresh fb friends")

        client = Client()

        user = User.objects.create(email="asfaf@af.com", password=0)
        userProfile = UserProfile.objects.create(user=user)

        response = client.post(reverse('refreshFacebookFriendsAPI'), {
            'userid': userProfile.id,
            'accesstoken': self.authKey
        })
        response = loadJson(response.content)

        self.assertIn('users', response)
        friends = response['users']

        for friend in friends:
            self.assertIn('userid', friend)
            self.assertIn('facebookid', friend)
            self.assertIn('firstname', friend)
            self.assertIn('lastname', friend)


class UserDetailsTests(TestCase):
    def setUp(self):
        user = User.objects.create(first_name="first", last_name="last", email="email", username='asfasf')
        self.userProfile = UserProfile.objects.create(facebookUID='1234', user=user)

        user2 = User.objects.create(first_name="first2", last_name="last2", email="email2", username='aq1fqwq')
        self.userProfile2 = UserProfile.objects.create(facebookUID='12345', user=user2)

    def testGetDetails(self):
        print("Get User Details")
        client = Client()

        response = client.get(reverse('getUserDetailsAPI'), {
            'userid': self.userProfile.id
        })
        response = loadJson(response.content)

        self.assertTrue(response['success'])
        self.assertEqual(response['firstname'], self.userProfile.user.first_name)
        self.assertEqual(response['lastname'], self.userProfile.user.last_name)
        self.assertEqual(response['facebookid'], self.userProfile.facebookUID)

    def testGetMultipleDetails(self):
        print("Get Multiple user details")
        client = Client()

        response = client.get(reverse('getUserDetailsAPI'), {
            'userids': json.dumps([self.userProfile.id, self.userProfile2.id])
        })
        response = loadJson(response.content)

        self.assertTrue(response['success'])
        self.assertEqual(len(response['users']), 2)

        userA = response['users'][0]
        userB = response['users'][1]

        self.assertTrue(userA['firstname'] == self.userProfile.user.first_name or userA['firstname'] == self.userProfile2.user.first_name)
        self.assertTrue(userB['lastname'] == self.userProfile.user.last_name or userB['lastname'] == self.userProfile2.user.last_name)

    def testUserNotFound(self):
        print("User Not Found")
        with self.assertRaises(UserProfile.DoesNotExist):
            UserProfile.getUser(111232323223232)


class CreateTestUserTests(TestCase):
    def setUp(self):
        pass

    def testCreateTestUser(self):
        print("Create Test User")
        client = Client()

        response = client.post(reverse('createTestUserAPI'), {
            'numfriends': 100
        })

        response = loadJson(response.content)

        self.assertTrue(response['success'])

class MutualFriendsTests(TestCase):
    def setUp(self):
        user = User.objects.create(first_name="first", last_name="last", email="email", username='asfasf')
        self.userProfile = UserProfile.objects.create(facebookUID='1234', user=user)

        user2 = User.objects.create(first_name="first2", last_name="last2", email="email2", username='aq1fqwq')
        self.userProfile2 = UserProfile.objects.create(facebookUID='12345', user=user2)

        user3 = User.objects.create(first_name="first3", last_name="last3", email="email3", username='aq1fqwa')
        self.userProfile3 = UserProfile.objects.create(facebookUID='123456', user=user3)

        self.userProfile.friends.add(self.userProfile3)
        self.userProfile2.friends.add(self.userProfile3)

    def testMutalFriends(self):
        print("Mutal Friends Test")
        data = UserProfile.getMutualFriends(self.userProfile.id, self.userProfile2.id)
        userid = data[0]['userid']
        self.assertEqual(userid, self.userProfile3.id)

