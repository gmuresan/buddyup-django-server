from django.conf.urls import patterns, include, url
from api.views import facebookRegister, postStatus, poke, getStatuses, createChat, inviteToChat, leaveChat, sendMessage, getMessages

urlpatterns = patterns('',
                       url(r'^facebookregister/$', facebookRegister, {}, 'facebookRegisterAPI'),
                       url(r'^poststatus/$', postStatus, {}, 'postStatusAPI'),
                       url(r'getstatuses/$', getStatuses, {}, 'getStatusesAPI'),
                       url(r'^poke/$', poke, {}, 'pokeAPI'),
                       url(r'^createchat/$', createChat, {}, 'createChatAPI'),
                       url(r'^invitetochat/$', inviteToChat, {}, 'inviteToChatAPI'),
                       url(r'^leavechat/$', leaveChat, {}, 'leaveChatAPI'),
                       url(r'^sendmessage/$', sendMessage, {}, 'sendMessageAPI'),
                       url(r'^getmessages/$', getMessages, {}, 'getMessagesAPI')

)
