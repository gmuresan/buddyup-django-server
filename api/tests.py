"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""
from datetime import datetime, timedelta
import json
from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from django.core.urlresolvers import reverse
import pytz
from django.test import TestCase, Client
from chat.models import Conversation, Message
from status.models import Status, Poke, Location
from userprofile.models import UserProfile

DATETIME_FORMAT = '%m-%d-%Y %H:%M'


class FacebookRegisterTest(TestCase):
    def setUp(self):
        self.authKey = 'CAACBZAKw2g0ABADwArZBOZAq7TCJJZCI8P0ataZBX4bZCLLMmvfLr1pws6d5IrcUmzZCkpZCK2hQrromJSxm76nJ7ptPH6FqPV7JSELcE7lrPekq6pNjWfJNtEE3SSMNxGJsHx5DBzuotahMZBZBLzeO4lHHeS1jArYX3ECkAXZCP6NfwZDZD'
        self.firstName = 'George'
        self.lastName = 'Muresan'

    def testRegister(self):
        print "testRegister"
        client = Client()

        response = client.post(reverse('facebookRegisterAPI'), {'fbauthkey': self.authKey,
                                                                'device': 'android'})
        response = json.loads(response.content)
        self.assertEqual(response['success'], True)
        self.assertNotIn('error', response)
        self.assertEqual(response['firstname'], self.firstName)
        self.assertEqual(response['lastname'], self.lastName)

        userProfile = UserProfile.objects.get(pk=response['userid'])
        self.assertEqual(userProfile.user.first_name, self.firstName)
        self.assertEqual(userProfile.user.last_name, self.lastName)

    def testFacebookLoginWithFriends(self):
        print "testFacebookLoginWithFriends"
        client = Client()

        user = User.objects.create(username='user1', password='0', email='user1', first_name='first', last_name='last')
        userprofile = UserProfile.objects.create(user=user)

        response = client.post(reverse('facebookRegisterAPI'), {'fbauthkey': self.authKey,
                                                                'device': 'android'})
        response = json.loads(response.content)

        self.assertEqual(response['success'], True)
        self.assertIn('userid', response)
        myProfile = UserProfile.objects.get(pk=response['userid'])
        myProfile.friends.add(userprofile)
        myProfile.save()
        userprofile.friends.add(myProfile)
        userprofile.save()

        response = client.post(reverse('facebookRegisterAPI'), {'fbauthkey': self.authKey,
                                                                'device': 'android'})
        response = json.loads(response.content)

        userprofileFriendData = {'id': userprofile.id, 'firstName': user.first_name, 'lastName': user.last_name,
                                 'blocked': False}
        self.assertNotEqual(len(response['friends']), 0)
        self.assertIn(userprofileFriendData, response['friends'])


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

    def testPostNoLocation(self):
        print "testPostNoLocation"
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

    def testPostWithLocation(self):
        print "testPostWithLocation"
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


class getStatusesTest(TestCase):
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

        self.location = Location.objects.create(lng=self.lng, lat=self.lat, point=Point(self.lng, self.lat),
                                                city=self.city, state=self.state)
        self.status1 = Status.objects.create(user=self.user1, expires=datetime.utcnow() + timedelta(hours=1),
                                             text='Hang out', location=self.location)

    def testSingleStatus(self):
        print "testSingleStatus"
        client = Client()

        myLat = 42.321620
        myLng = -83.507794
        since = datetime.utcnow() - timedelta(hours=1)

        response = client.get(reverse('api.views.getStatuses'), {'userid': self.user2.id,
                                                                 'since': since.strftime(DATETIME_FORMAT),
                                                                 'lat': myLat,
                                                                 'lng': myLng})

        response = json.loads(response.content)

        self.assertEqual(response['success'], True)
        self.assertNotIn('error', response)
        self.assertEqual(len(response['statuses']), 1)
        self.assertEqual(response['statuses'][0]['text'], self.status1.text)

    def testSingleStatusOutOfRange(self):
        print "testSingleStatusOutOfRange"
        client = Client()

        myLat = 42.321620
        myLng = -83.507794
        since = datetime.utcnow() - timedelta(hours=1)

        response = client.get(reverse('api.views.getStatuses'), {'userid': self.user2.id,
                                                                 'since': since.strftime(DATETIME_FORMAT),
                                                                 'lat': myLat,
                                                                 'lng': myLng,
                                                                 'distance': 1})

        response = json.loads(response.content)

        self.assertEqual(response['success'], True)
        self.assertEqual(len(response['statuses']), 0)
        self.assertNotIn('error', response)


class PokeTest(TestCase):
    def setUp(self):
        user1 = User.objects.create(username='user1', password='0', email='user1')
        self.user1 = UserProfile.objects.create(user=user1)

        user2 = User.objects.create(username='user2', password='0', email='user2')
        self.user2 = UserProfile.objects.create(user=user2)

        self.user1.friends.add(self.user2)
        self.user2.friends.add(self.user1)

    def testPoke(self):
        print "testPoke"
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
        print "testCreateConversation"
        client = Client()

        response = client.post(reverse('createChatAPI'), {'userid': self.user.id,
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

    def testCreateConverationWithNonFriend(self):
        print "testCreateConversationWithNonFriend"
        client = Client()

        response = client.post(reverse('createChatAPI'), {'userid': self.user.id,
                                                          'friendid': self.nonFriend.id
        })

        response = json.loads(response.content)
        self.assertEqual(response['success'], False)
        self.assertIn('error', response)

    def testCreateConversationWithBlockedFriend(self):
        print "testCreateConversationWithBlockedFriend"
        client = Client()

        response = client.post(reverse('createChatAPI'), {'userid': self.user.id,
                                                          'friendid': self.blockedFriend.id
        })

        response = json.loads(response.content)
        self.assertEqual(response['success'], False)
        self.assertIn('error', response)

    def testChatInvite(self):
        print "testChatInvite"
        client = Client()

        response = client.post(reverse('createChatAPI'), {'userid': self.user.id,
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

    def testChatInviteNonFriend(self):
        print "testChatInviteNonFriend"
        client = Client()

        response = client.post(reverse('createChatAPI'), {'userid': self.user.id,
                                                          'friendid': self.friend.id
        })

        response = json.loads(response.content)
        chatid = response['chatid']

        response = client.post(reverse('inviteToChatAPI'), {'userid': self.user.id,
                                                            'friendid': self.nonFriend.id,
                                                            'chatid': chatid
        })

        response = json.loads(response.content)
        self.assertEqual(response['success'], False)
        self.assertIn('error', response)

    def testChatInviteBlockedFriend(self):
        print "testChatInviteBlockedFriend"
        client = Client()

        response = client.post(reverse('createChatAPI'), {'userid': self.user.id,
                                                          'friendid': self.friend.id
        })

        response = json.loads(response.content)
        chatid = response['chatid']

        response = client.post(reverse('inviteToChatAPI'), {'userid': self.user.id,
                                                            'friendid': self.blockedFriend.id,
                                                            'chatid': chatid
        })

        response = json.loads(response.content)
        self.assertEqual(response['success'], False)
        self.assertIn('error', response)

    def testLeaveChat(self):
        print "testLeaveChat"
        client = Client()

        response = client.post(reverse('createChatAPI'), {'userid': self.user.id,
                                                          'friendid': self.friend.id
        })
        response = json.loads(response.content)
        chatid = response['chatid']

        response = client.post(reverse('leaveChatAPI'), {'userid': self.user.id,
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
        print "testLeaveInvalidChat"
        client = Client()

        response = client.post(reverse('leaveChatAPI'), {'userid': self.user.id,
                                                         'chatid': 1
        })
        response = json.loads(response.content)

        self.assertEqual(response['success'], False)
        self.assertIn('error', response)

    def testLastPersonToLeaveChat(self):
        print "testLastPersonToLeaveChat"
        client = Client()

        response = client.post(reverse('createChatAPI'), {'userid': self.user.id,
                                                          'friendid': self.friend.id
        })
        response = json.loads(response.content)
        chatid = response['chatid']

        response = client.post(reverse('leaveChatAPI'), {'userid': self.user.id,
                                                         'chatid': chatid
        })

        response = client.post(reverse('leaveChatAPI'), {'userid': self.friend.id,
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
        print "testSendMessage"
        client = Client()

        response = client.post(reverse('createChatAPI'), {'userid': self.user.id,
                                                          'friendid': self.friend.id
        })

        response = json.loads(response.content)
        chatid = response['chatid']

        response = client.post(reverse('sendMessageAPI'), {'userid': self.user.id,
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

    def testGetSingleMessage(self):
        print "testGetSingleMessage"
        client = Client()

        response = response = client.post(reverse('createChatAPI'), {'userid': self.user.id,
                                                          'friendid': self.friend.id
        })

        response = json.loads(response.content)
        chatid = response['chatid']

        response = client.post(reverse('sendMessageAPI'), {'userid': self.user.id,
                                                           'chatid': chatid,
                                                           'text': 'hello'
        })
        response = json.loads(response.content)

        since = datetime.utcnow() - timedelta(hours=1)
        response = client.post(reverse('getMessagesAPI'), {'userid': self.friend.id,
                                                           'since': since.strftime(DATETIME_FORMAT)
        })

        response = json.loads(response.content)

        self.assertEqual(len(response['messages']), 1)
        self.assertEqual(response['success'], True)
        self.assertNotIn('error', response)

        convo = Conversation.objects.get(pk=chatid)
        convoMessage = convo.messages.latest('created')

        message = response['messages'][0]
        self.assertEqual(message['messageid'], convoMessage.id)
        self.assertEqual(message['chatid'], convo.id)
        self.assertEqual(message['text'], convoMessage.text)
        self.assertEqual(message['userid'], convoMessage.user.id)


