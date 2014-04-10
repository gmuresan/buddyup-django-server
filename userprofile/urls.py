from django.conf.urls import patterns, url
from api.facebookGraphObjects import fbObjectStatus
from status.api_functions import *
from userprofile.api_functions import *

urlpatterns = patterns('',
                       url(r'^facebooklogin/$', facebookLogin, {}, 'facebookLoginAPI'),
                       url(r'^getuserdetails', getUserDetails, {}, 'getUserDetailsAPI'),


                       url(r'^gooffline/$', goOffline, {}, 'goOfflineAPI'),

                       url(r'^fb_object/status/(\d+)/$', fbObjectStatus, {}, 'fbObjectStatus'),
                        url(r'^creategroup/$', createGroup, {}, 'createGroupAPI'),
                       url(r'^editgroupname/$', editGroupName, {}, 'editGroupNameAPI'),
                       url(r'^deletegroup/$', deleteGroup, {}, 'deleteGroupAPI'),
                       url(r'^addgroupmember/$', addGroupMember, {}, 'addGroupMemberAPI'),
                       url(r'^removegroupmember/$', removeGroupMember, {}, 'removeGroupMemberAPI'),
                       url(r'^getgroups/$', getGroups, {}, 'getGroupsAPI'),
                       url(r'^setgroups/$', setGroups, {}, 'setGroupsAPI'),
                       url(r'^setgroupmembers/$', setGroupMembers, {}, 'setGroupMembersAPI'),

                       url(r'^getfriends/$', getFriends, {}, 'getFriendsAPI'),
                       url(r'^blockfriend/$', blockFriend, {}, 'blockFriendAPI'),
                       url(r'^unblockfriend/$', unblockFriend, {}, 'unblockFriendAPI'),

                       url(r'^submitfeedback/$', submitFeedback, {}, 'submitFeedbackAPI'),

                       url(r'^getnewdata/$', getNewData, {}, 'getNewDataAPI'),

                       url(r'^setsetting/$', setSetting, {}, 'setSettingAPI'),
                       url(r'^getsetting/$', getSetting, {}, 'getSettingAPI'),

                       url(r'^registernotifications', registerForPushNotifications, {}, 'registerPushNotificationsAPI'),

                        url(r'^setfavnotif/$', setFavoritesNotifications, {}, 'setFavNotificationsAPI'),

                       )