from django.contrib import admin
from status.models import Status, Location, Poke

class StatusAdmin(admin.ModelAdmin):
    list_display = ('text', 'user', 'starts', 'expires', 'location', 'attendingCount', 'invitedCount')
    readonly_fields = ('user', 'attending', 'invited', 'location', 'groups', 'friendsVisible', 'fbFriendsVisible', 'fbInvited', 'fbAttending',)

    def attendingCount(self, obj):
        return obj.attending.count()

    def invitedCount(self, obj):
        return obj.invited.count()

admin.site.register(Status, StatusAdmin)
admin.site.register(Location)
admin.site.register(Poke)
