from datetime import timedelta, datetime
import json
import pdb
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import Client, TestCase
from api.helpers import MICROSECOND_DATETIME_FORMAT, loadJson
from chat.helpers import CHAT_MESSAGE_PER_PAGE
from chat.models import Conversation, Message
from userprofile.models import UserProfile


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
        print("SendMessage")
        client = Client()

        response = client.post(reverse('createChatAPI'), {
            'userid': self.user.id,
            'friendid': self.friend.id
        })

        response = loadJson(response.content)
        chatid = response['chatid']

        response = client.post(reverse('sendMessageAPI'), {
            'userid': self.user.id,
            'chatid': chatid,
            'text': 'hello'
        })
        response = loadJson(response.content)

        self.assertEqual(response['success'], True)

        convo = Conversation.objects.get(pk=chatid)
        message = convo.messages.latest('created')

        self.assertEqual(message.user, self.user)
        self.assertEqual(message.text, 'hello')
        self.assertEqual(message.conversation, convo)
        self.assertIn('chats', response)
        self.assertIn('newsince', response)

    def testGetSingleMessage(self):
        print("GetSingleMessage")
        client = Client()

        response = client.post(reverse('createChatAPI'), {
            'userid': self.user.id,
            'friendid': self.friend.id
        })

        response = loadJson(response.content)
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

        response = loadJson(response.content)

        self.assertEqual(len(response['chats']), 1)
        self.assertEqual(response['success'], True)
        self.assertNotIn('error', response)
        self.assertIn('members', response['chats'][0])

        convo = Conversation.objects.get(pk=chatid)
        convoMessage = convo.messages.latest('created')

        chatResponse = response['chats'][0]
        messageResponse = chatResponse['messages'][0]

        self.assertEqual(messageResponse['messageid'], convoMessage.id)
        self.assertEqual(chatResponse['chatid'], convo.id)
        self.assertEqual(messageResponse['text'], convoMessage.text)
        self.assertEqual(messageResponse['userid'], convoMessage.user.id)

    def testGetChatPage(self):
        NUMBER_OF_MESSAGES = 30

        print("Test Chat Paging")
        client = Client()

        chat = Conversation.objects.create()
        chat.members.add(self.user, self.friend, self.friend2)
        chat.save()

        for x in range(0, NUMBER_OF_MESSAGES):
            Message.objects.create(user=self.friend, conversation=chat, text="a")

        latestMessage = chat.messages.latest('id')

        response = client.post(reverse('getChatPageAPI'), {
            'userid': self.user.id,
            'earliestmessageid': latestMessage.id,
            'chatid': chat.id
        })
        response = loadJson(response.content)

        self.assertNotIn('error', response)
        self.assertTrue(response['success'])
        chatData = response['chat']
        messages = chatData['messages']

        self.assertEqual(len(messages), CHAT_MESSAGE_PER_PAGE)

        earliestId = 999999999

        for msg in messages:
            newId = msg['messageid']
            if newId < earliestId:
                earliestId = newId

        response = client.post(reverse('getChatPageAPI'), {
            'userid': self.user.id,
            'earliestmessageid': earliestId,
            'chatid': chat.id
        })
        response = loadJson(response.content)

        self.assertTrue(response['success'])
        chatData = response['chat']
        messages = chatData['messages']

        self.assertEqual(len(messages), NUMBER_OF_MESSAGES - CHAT_MESSAGE_PER_PAGE - 1)


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
        print("CreateConversation")
        client = Client()

        response = client.post(reverse('createChatAPI'), {
            'userid': self.user.id,
            'friendid': self.friend.id
        })

        response = loadJson(response.content)
        chatid = response['chatid']

        self.assertEqual(response['success'], True)
        self.assertNotIn('error', response)

        conversation = Conversation.objects.get(pk=chatid)
        members = conversation.members.all()
        self.assertTrue(self.user in members)
        self.assertTrue(self.friend in members)

        response = client.post(reverse('createChatAPI'), {
            'userid': self.user.id,
            'friendid': self.friend.id
        })
        response = loadJson(response.content)
        self.assertEqual(response['success'], True)
        self.assertNotIn('error', response)
        self.assertEqual(response['chatid'], chatid)

        response = client.post(reverse('createChatAPI'), {
            'userid': self.user.id,
            'friendid': self.friend2.id
        })
        response = loadJson(response.content)
        self.assertEqual(response['success'], True)
        self.assertNotEqual(response['chatid'], chatid)
        chat2Id = response['chatid']

        response = client.post(reverse('createChatAPI'), {
            'userid': self.user.id,
            'friendids': json.dumps([self.friend2.id, self.friend.id])
        })
        response = loadJson(response.content)
        self.assertEqual(response['success'], True)
        self.assertNotEqual(response['chatid'], chatid)
        self.assertNotEqual(response['chatid'], chat2Id)
        chat3Id = response['chatid']

        response = client.post(reverse('createChatAPI'), {
            'userid': self.user.id,
            'friendids': json.dumps([self.friend2.id, self.friend.id])
        })
        response = loadJson(response.content)
        self.assertEqual(response['success'], True)
        self.assertNotEqual(response['chatid'], chatid)
        self.assertNotEqual(response['chatid'], chat2Id)
        self.assertEqual(response['chatid'], chat3Id)


    def testCreateConversationWithMultipleFriends(self):
        print("CreateConversationWithMultipleFriends")
        client = Client()

        friendids = [self.friend.id, self.friend2.id]
        response = client.post(reverse('createChatAPI'), {
            'userid': self.user.id,
            'friendid': json.dumps(friendids)
        })

        response = loadJson(response.content)
        chatid = response['chatid']

        self.assertEqual(response['success'], True)
        self.assertNotIn('error', response)

        conversation = Conversation.objects.get(pk=chatid)
        members = conversation.members.all()
        self.assertTrue(self.user in members)
        self.assertTrue(self.friend in members)
        self.assertTrue(self.friend2 in members)

    def testCreateConverationWithNonFriend(self):
        print("CreateConversationWithNonFriend")
        client = Client()

        response = client.post(reverse('createChatAPI'), {
            'userid': self.user.id,
            'friendid': self.nonFriend.id
        })

        response = loadJson(response.content)
        self.assertEqual(response['success'], False)
        self.assertIn('error', response)

    def testCreateConversationWithBlockedFriend(self):
        print("CreateConversationWithBlockedFriend")
        client = Client()

        response = client.post(reverse('createChatAPI'), {
            'userid': self.user.id,
            'friendid': self.blockedFriend.id
        })

        response = loadJson(response.content)
        self.assertEqual(response['success'], True)

        chatid = response['chatid']

        chat = Conversation.objects.get(pk=chatid)

        self.assertEqual(len(chat.members.all()), 1)
        self.assertNotIn(self.blockedFriend, chat.members.all())

    def testChatInvite(self):
        print("ChatInvite")
        client = Client()

        response = client.post(reverse('createChatAPI'), {
            'userid': self.user.id,
            'friendid': self.friend.id
        })

        response = loadJson(response.content)
        chatid = response['chatid']

        response = client.post(reverse('inviteToChatAPI'), {'userid': self.user.id,
                                                            'friendid': self.friend2.id,
                                                            'chatid': chatid})
        response = loadJson(response.content)

        self.assertEqual(response['success'], True)
        self.assertNotIn('error', response)

        conversation = Conversation.objects.get(pk=chatid)
        members = conversation.members.all()
        self.assertTrue(self.user in members)
        self.assertTrue(self.friend in members)
        self.assertTrue(self.friend2 in members)

    def testMutlipleFriendChatInvite(self):
        print("MultipleFriendChatInvite")
        client = Client()

        response = client.post(reverse('createChatAPI'), {
            'userid': self.user.id,
            'friendid': self.friend.id
        })

        response = loadJson(response.content)
        chatid = response['chatid']

        friendids = [self.friend2.id, self.friend3.id]
        response = client.post(reverse('inviteToChatAPI'), {'userid': self.user.id,
                                                            'friendids': json.dumps(friendids),
                                                            'chatid': chatid})
        response = loadJson(response.content)

        self.assertEqual(response['success'], True)
        self.assertNotIn('error', response)

        conversation = Conversation.objects.get(pk=chatid)
        members = conversation.members.all()
        self.assertTrue(self.user in members)
        self.assertTrue(self.friend in members)
        self.assertTrue(self.friend2 in members)
        self.assertIn(self.friend3, members)

    def testChatInviteNonFriend(self):
        print("ChatInviteNonFriend")
        client = Client()

        response = client.post(reverse('createChatAPI'), {
            'userid': self.user.id,
            'friendid': self.friend.id
        })

        response = loadJson(response.content)
        chatid = response['chatid']

        response = client.post(reverse('inviteToChatAPI'), {
            'userid': self.user.id,
            'friendid': self.nonFriend.id,
            'chatid': chatid
        })

        response = loadJson(response.content)
        self.assertEqual(response['success'], False)
        self.assertIn('error', response)

    def testChatInviteBlockedFriend(self):
        print("ChatInviteBlockedFriend")
        client = Client()

        response = client.post(reverse('createChatAPI'), {
            'userid': self.user.id,
            'friendid': self.friend.id
        })

        response = loadJson(response.content)
        chatid = response['chatid']

        response = client.post(reverse('inviteToChatAPI'), {
            'userid': self.user.id,
            'friendid': self.blockedFriend.id,
            'chatid': chatid
        })

        response = loadJson(response.content)
        self.assertEqual(response['success'], False)
        self.assertIn('error', response)

    def testLeaveChat(self):
        print("LeaveChat")
        client = Client()

        response = client.post(reverse('createChatAPI'), {
            'userid': self.user.id,
            'friendid': self.friend.id
        })
        response = loadJson(response.content)
        chatid = response['chatid']

        convo = Conversation.objects.get(pk=chatid)
        convo.members.add(self.friend2)

        response = client.post(reverse('leaveChatAPI'), {
            'userid': self.user.id,
            'chatid': chatid
        })
        response = loadJson(response.content)

        self.assertEqual(response['success'], True)
        self.assertNotIn('error', response)

        members = convo.members.all()
        self.assertTrue(self.user not in members)
        self.assertTrue(self.friend in members)

        response = client.post(reverse('leaveChatAPI'), {
            'userid': self.friend.id,
            'chatid': chatid
        })
        response = loadJson(response.content)

        members = convo.members.all()
        self.assertEqual(response['success'], True)
        self.assertNotIn('error', response)
        self.assertTrue(self.friend in members)

    def testLeaveInvalidChat(self):
        print("LeaveInvalidChat")
        client = Client()

        response = client.post(reverse('leaveChatAPI'), {
            'userid': self.user.id,
            'chatid': 1
        })
        response = loadJson(response.content)

        self.assertEqual(response['success'], False)
        self.assertIn('error', response)
