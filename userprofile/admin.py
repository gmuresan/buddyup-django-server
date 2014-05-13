from django.contrib import admin
from userprofile.models import UserProfile, Group, Feedback, Setting

class UserProileAdmin(admin.ModelAdmin):
    list_display = ('user','id',)
    readonly_fields = ('id', 'user', 'friends', 'blockedFriends')

admin.site.register(UserProfile, UserProileAdmin)
admin.site.register(Group)

class FeedBackAdmin(admin.ModelAdmin):
    list_display = ('text', 'user', 'date',)
    readonly_fields = ('user', 'date', )

admin.site.register(Feedback, FeedBackAdmin)
admin.site.register(Setting)


