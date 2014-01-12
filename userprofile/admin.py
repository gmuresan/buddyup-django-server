from django.contrib import admin
from userprofile.models import UserProfile, Group, Feedback, Setting


admin.site.register(UserProfile)
admin.site.register(Group)
admin.site.register(Feedback)
admin.site.register(Setting)


