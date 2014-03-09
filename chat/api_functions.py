from django.views.decorators.csrf import csrf_exempt
from api.helpers import *
from api.views import *
from chat.models import Conversation, Message
from notifications.push_notifications import sendChatNotifications
from userprofile.models import *


@csrf_exempt
def createChat(request):
    response = dict()

    userid = request.REQUEST['userid']
    try:
        userProfile = UserProfile.objects.get(pk=userid)
    except UserProfile.DoesNotExist:
        return errorResponse("User ID is not valid")

    friendids = request.REQUEST.get('friendid')
    if not friendids:
        friendids = request.REQUEST.get('friendids')

    try:
        friendids = int(friendids)
        friendids = [friendids, ]
    except:
        friendids = json.loads(friendids)

    conversation = Conversation.objects.create()

    for friendid in friendids:

        try:
            friendProfile = UserProfile.objects.get(pk=friendid)
        except UserProfile.DoesNotExist:
            conversation.delete()
            return errorResponse("Friend ID is not valid")

        if friendProfile not in userProfile.friends.all():
            conversation.delete()
            return errorResponse("That user is not your friend")

        if not userProfile in friendProfile.blockedFriends.all():
            conversation.members.add(friendProfile)

    conversation.members.add(userProfile)
    conversation.save()

    #TODO: Send push notification to friend that was invited to chat

    response['success'] = True
    response['chatid'] = conversation.id

    return HttpResponse(json.dumps(response))


@csrf_exempt
def inviteToChat(request):
    response = dict()

    userid = request.REQUEST['userid']
    try:
        userProfile = UserProfile.objects.get(pk=userid)
    except UserProfile.DoesNotExist:
        return errorResponse("User ID is not valid")

    friendids = request.REQUEST.get('friendid')
    if not friendids:
        friendids = request.REQUEST.get('friendids')

    try:
        friendids = int(friendids)
        friendids = [friendids, ]
    except:
        friendids = json.loads(friendids)

    chatid = request.REQUEST['chatid']

    try:
        conversation = Conversation.objects.get(pk=chatid)
    except Conversation.DoesNotExist:
        return errorResponse("Chat id does not exist")

    for friendid in friendids:
        try:
            friendProfile = UserProfile.objects.get(pk=friendid)
        except UserProfile.DoesNotExist:
            return errorResponse("Friend ID is not valid")

        if friendProfile not in userProfile.getUnblockedFriends():
            return errorResponse("That user is not your friend")

        if userProfile not in friendProfile.getUnblockedFriends():
            return errorResponse("You are not that user's friend")

        if userProfile in friendProfile.blockedFriends.all():
            return errorResponse("That user has blocked you")

        members = conversation.members.all()
        if userProfile not in members:
            return errorResponse("You are not part of this conversation")

        if not friendProfile in members:
            conversation.members.add(friendProfile)

    conversation.save()

    #TODO: Send push notification to friend that he was invited to chat

    response['success'] = True

    return HttpResponse(json.dumps(response))


@csrf_exempt
def leaveChat(request):
    response = dict()

    userid = request.REQUEST['userid']
    chatid = request.REQUEST['chatid']

    try:
        userProfile = UserProfile.objects.get(pk=userid)
    except UserProfile.DoesNotExist:
        return errorResponse("Invalid user id")

    try:
        convo = Conversation.objects.get(pk=chatid)
    except Conversation.DoesNotExist:
        return errorResponse("Invalid chat id")

    if userProfile not in convo.members.all():
        return errorResponse("User is not a member of this chat")

    convo.members.remove(userProfile)
    convo.save()

    if convo.members.count() == 0:
        convo.delete()

    response['success'] = True

    return HttpResponse(json.dumps(response))


@csrf_exempt
def sendMessage(request):
    response = dict()

    userid = request.REQUEST['userid']
    chatid = request.REQUEST['chatid']
    text = request.REQUEST['text']
    text = str(text)
    since = request.REQUEST.get('since', None)

    if since:
        since = datetime.strptime(since, MICROSECOND_DATETIME_FORMAT)

    try:
        userProfile = UserProfile.objects.get(pk=userid)
    except UserProfile.DoesNotExist:
        return errorResponse("Invalid user id")

    try:
        convo = Conversation.objects.get(pk=chatid)
    except Conversation.DoesNotExist:
        return errorResponse("Invalid chat id")

    if userProfile not in convo.members.all():
        return errorResponse("User is not a member of this chat")

    message = Message.objects.create(user=userProfile, conversation=convo, text=text)
    convo.save(force_update=True)

    chatData = getNewChatsData(userProfile, since)

    newSince = datetime.now().strftime(MICROSECOND_DATETIME_FORMAT)

    response['chats'] = chatData
    response['newsince'] = newSince
    response['success'] = True

    sendChatNotifications(message)

    return HttpResponse(json.dumps(response))


@csrf_exempt
def getMessages(request):
    response = dict()

    userid = request.REQUEST['userid']
    since = request.REQUEST.get('since', None)
    if since:
        since = datetime.strptime(since, MICROSECOND_DATETIME_FORMAT)

    try:
        userProfile = UserProfile.objects.get(pk=userid)
    except UserProfile.DoesNotExist:
        return errorResponse("Invalid user id")

    newSince = datetime.now().strftime(MICROSECOND_DATETIME_FORMAT)

    chatData = getNewChatsData(userProfile, since)

    response['success'] = True
    response['newsince'] = newSince
    response['chats'] = chatData

    return HttpResponse(json.dumps(response))
