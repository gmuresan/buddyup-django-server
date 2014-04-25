from django.conf.urls import patterns, url
from chat.api_functions import *

urlpatterns = patterns('',

                        url(r'^createchat/$', createChat, {}, 'createChatAPI'),
                       url(r'^invitetochat/$', inviteToChat, {}, 'inviteToChatAPI'),
                       url(r'^leavechat/$', leaveChat, {}, 'leaveChatAPI'),
                       url(r'^sendmessage/$', sendMessage, {}, 'sendMessageAPI'),
                       url(r'^getmessages/$', getMessages, {}, 'getMessagesAPI'),
                       url(r'^getchatpage/$', getChatPage, {}, 'getChatPageAPI'),
                       )