from django.contrib import admin
from userprofile.models import UserProfile, Group, Feedback, Setting

class UserProileAdmin(admin.ModelAdmin):
    readonly_fields = ('id',)

admin.site.register(UserProfile, UserProileAdmin)
admin.site.register(Group)
admin.site.register(Feedback)
admin.site.register(Setting)


