"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
from datetime import datetime
import json
from django.contrib.auth.models import User

from django.test import TestCase, Client
from userprofile.models import UserProfile

DATETIME_FORMAT = '%m-%d-%Y %H:%M'


class PostStatusTests(TestCase):

    def setUp(self):
        user1 = User.objects.create(username='user1', password='0', email='user1')
        self.user = UserProfile.objects.create(user=user1)

        self.text = "Hangout at my house"
        self.expires = datetime(2013, 5, 1)

    def postNoLocation(self):
        client = Client()

        response = client.post('/api/poststatus/', {'userid': self.user.id,
                                                    'expires': self.expires.strftotime(DATETIME_FORMAT),
                                                    'text': self.text
                                                    }
        )

        responseObj = json.loads(response)
        self.assertEqual(responseObj['success'], True)
        self.assertEqual(responseObj['statusid'], 1)
        self.assertIsNot(responseObj['error'])
        print responseObj


    def postWithLocation(self):
        client = Client()