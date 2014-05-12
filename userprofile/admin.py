from django.contrib import admin
from userprofile.models import UserProfile, Group, Feedback, Setting

class UserProileAdmin(admin.ModelAdmin):
    readonly_fields = ('id',)

admin.site.register(UserProfile, UserProileAdmin)
admin.site.register(Group)

class FeedBackAdmin(admin.ModelAdmin):
    readonly_fields = ('date')

admin.site.register(Feedback, FeedBackAdmin)
admin.site.register(Setting)


