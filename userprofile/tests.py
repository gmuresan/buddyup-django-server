"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
import json
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from django.test import TestCase, Client
from api.helpers import loadJson
from userprofile.models import UserProfile

class FavoritesNotificationsTests(TestCase):
    def setUp(self):
        user = User.objects.create(first_name="first", last_name="last", email="email", username='asfasf')
        self.user = UserProfile.objects.create(facebookUID='1234', user=user)

    def testSetFavNotifications(self):
        print("Set Fav Notifs")
        client = Client()

        response = client.get(reverse('setFavNotificationsAPI'), {
            'userid': self.user.id,
            'value': False
        })
        response = loadJson(response.content)

        self.assertTrue(response['success'])

        user = UserProfile.objects.get(pk=self.user.id)
        self.assertFalse(user.favoritesNotifications)


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
        userid = data['userd']
        self.assertEqual(userid, self.userProfile3.id)

