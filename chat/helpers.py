from datetime import timedelta
import pdb
from api.helpers import DATETIME_FORMAT

CHAT_MESSAGE_PER_PAGE = 20

def getNewChatsData(userProfile, since=None):
    conversations = userProfile.conversations.all()

    if since is not None:
        conversations = conversations.filter(lastActivity__gt=since)

    conversations = list(conversations)

    chats = []
    for convo in conversations:
        msgs = convo.messages.all()
        if since is not None:
            msgs = msgs.filter(created__gt=since)
        else:
            msgs = msgs.filter(created__gt=(convo.lastActivity - timedelta(days=7)))

        chats.append(createChatJson(convo, msgs))

    return chats


def createMessageJson(messageObj):
    messageData = dict()
    messageData['messageid'] = messageObj.id
    messageData['date'] = messageObj.created.strftime(DATETIME_FORMAT)
    messageData['text'] = messageObj.text
    messageData['userid'] = messageObj.user.id

    return messageData


def createChatMembersJson(chat):
    membersData = []
    members = chat.members.all()
    for member in members:
        memberData = dict()
        memberData['userid'] = member.id
        memberData['facebookid'] = member.facebookUID
        memberData['firstname'] = member.user.first_name
        memberData['lastname'] = member.user.last_name
        membersData.append(memberData)


def createChatJson(chat, messageObjects):
    messagesData = []
    for message in messageObjects:
        messagesData.append(createMessageJson(message))

    chatData = dict()
    chatData['chatid'] = chat.id
    chatData['lastactivity'] = chat.lastActivity.strftime(DATETIME_FORMAT)
    chatData['messages'] = messagesData
    chatData['members'] = createChatMembersJson(chat)

    return chatData


def getChatMessagesPage(chat, earliestMessageId):
    messages = chat.messages.filter(id__lt=earliestMessageId)[:CHAT_MESSAGE_PER_PAGE]

    return createChatJson(chat, messages)

