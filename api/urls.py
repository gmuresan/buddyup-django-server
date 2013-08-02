from django.conf.urls import patterns, url
from api.views import *

urlpatterns = patterns('',
                       url(r'^facebookregister/$', facebookRegister, {}, 'facebookRegisterAPI'),
                       url(r'^facebooklogin/$', facebookLogin, {}, 'facebookLoginAPI'),

                       url(r'^poststatus/$', postStatus, {}, 'postStatusAPI'),
                       url(r'^deletestatus/$', deleteStatus, {}, 'deleteStatusAPI'),
                       url(r'^getstatuses/$', getStatuses, {}, 'getStatusesAPI'),
                       url(r'^getmystatuses/$', getMyStatuses, {}, 'getMyStatusesAPI'),
                       url(r'^poke/$', poke, {}, 'pokeAPI'),

                       url(r'^createchat/$', createChat, {}, 'createChatAPI'),
                       url(r'^invitetochat/$', inviteToChat, {}, 'inviteToChatAPI'),
                       url(r'^leavechat/$', leaveChat, {}, 'leaveChatAPI'),
                       url(r'^sendmessage/$', sendMessage, {}, 'sendMessageAPI'),
                       url(r'^getmessages/$', getMessages, {}, 'getMessagesAPI'),

                       url(r'^creategroup/$', createGroup, {}, 'createGroupAPI'),
                       url(r'^editgroupname/$', editGroupName, {}, 'editGroupNameAPI'),
                       url(r'^deletegroup/$', deleteGroup, {}, 'deleteGroupAPI'),
                       url(r'^addgroupmember/$', addGroupMember, {}, 'addGroupMemberAPI'),
                       url(r'^removegroupmember/$', removeGroupMember, {}, 'removeGroupMemberAPI'),
                       url(r'^getgroups/$', getGroups, {}, 'getGroupsAPI'),
                       url(r'^setgroups/$', setGroups, {}, 'setGroupsAPI'),

                       url(r'^getfriends/$', getFriends, {}, 'getFriendsAPI'),
                       url(r'^blockfriend/$', blockFriend, {}, 'blockFriendAPI'),
                       url(r'^unblockfriend/$', unblockFriend, {}, 'unblockFriendAPI'),

                       url(r'^submitfeedback/$', submitFeedback, {}, 'submitFeedbackAPI')

)
