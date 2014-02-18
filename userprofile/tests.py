"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
import json
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from django.test import TestCase, Client
from userprofile.models import UserProfile


class UserDetailsTests(TestCase):
    def setUp(self):
        user = User.objects.create(first_name="first", last_name="last", email="email")
        self.userProfile = UserProfile.objects.create(facebookUID='1234', user=user)

    def testGetDetails(self):
        print "Get User Details"
        client = Client()

        response = client.get(reverse('getUserDetailsAPI'), {
            'userid': self.userProfile.id
        })
        response = json.loads(response.content)

        self.assertTrue(response['success'])
        self.assertEqual(response['firstname'], self.userProfile.user.first_name)
        self.assertEqual(response['lastname'], self.userProfile.user.last_name)
        self.assertEqual(response['facebookid'], self.userProfile.facebookUID)