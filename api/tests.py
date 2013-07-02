"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
from datetime import datetime
import json
from django.contrib.auth.models import User
import pytz
from django.test import TestCase, Client
from status.models import Status, Poke
from userprofile.models import UserProfile

DATETIME_FORMAT = '%m-%d-%Y %H:%M'


class PostStatusTests(TestCase):
    def setUp(self):
        self.local = pytz.timezone("US/Eastern")
        self.utc = pytz.timezone("UTC")

        user1 = User.objects.create(username='user1', password='0', email='user1')
        self.user = UserProfile.objects.create(user=user1)

        self.text = "Hangout at my house"

        self.expires = self.utc.localize(datetime(2013, 5, 1))

        self.lng = 42.341560
        self.lat = -83.501783
        self.address = '46894 spinning wheel'
        self.city = 'canton'
        self.state = 'MI'
        self.location = {'lat': self.lat, 'lng': self.lng, 'address': self.address, 'state': self.state,
                         'city': self.city}

    def test_postNoLocation(self):
        client = Client()

        response = client.post('/api/poststatus/', {'userid': self.user.id,
                                                    'expires': self.expires.strftime(DATETIME_FORMAT),
                                                    'text': self.text
        })

        responseObj = json.loads(response.content)
        self.assertEqual(responseObj['success'], True)
        self.assertEqual(responseObj['statusid'], 1)
        self.assertNotIn('error', responseObj)

        status = Status.objects.get(pk=responseObj['statusid'])

        self.assertEqual(status.user, self.user)
        self.assertEqual(status.expires, self.expires)
        self.assertEqual(status.text, self.text)

    def test_postWithLocation(self):
        client = Client()

        response = client.post('/api/poststatus/', {'userid': self.user.id,
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


class PokeTest(TestCase):
    def setUp(self):
        user1 = User.objects.create(username='user1', password='0', email='user1')
        self.user1 = UserProfile.objects.create(user=user1)

        user2 = User.objects.create(username='user2', password='0', email='user2')
        self.user2 = UserProfile.objects.create(user=user2)

        self.user1.friends.add(self.user2)
        self.user2.friends.add(self.user1)

    def testPoke(self):
        client = Client()

        response = client.post('/api/poke/', {'userid': self.user1.id,
                                              'targetuserid': self.user2.id
        })

        response = json.loads(response.content)

        self.assertEqual(response['success'], True)
        self.assertIsNotNone(response['pokeid'])

        poke = Poke.objects.get(pk=response['pokeid'])

        self.assertEqual(poke.sender, self.user1)
        self.assertEqual(poke.recipient, self.user2)

        response = client.post('/api/poke/', {'userid': self.user1.id,
                                              'targetuserid': self.user2.id
        })

        response = json.loads(response.content)
        self.assertNotIn('pokeid', response)
        self.assertEqual(response['success'], False)
        self.assertIsNotNone(response['error'])
