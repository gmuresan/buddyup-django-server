import pdb
import urllib
import urllib2
from django.core.management import BaseCommand
import json
import facebook
from api import helpers
from buddyup import settings

PERMISSIONS = "email, publish_actions"


class Command(BaseCommand):
    help = "Creates a facebook test user"
    args = "<full_name>"

    def handle(self, *args, **options):
        fb = facebook.GraphAPI()
        accessToken = helpers.getFacebookAppAccessToken()

        print "Creating users with permissions: " + PERMISSIONS

        for full_name in args:
            print "Creating user with name: " + full_name
            response = fb.request(settings.FACEBOOK_APP_ID + "/accounts/test-users", None,
                                  {'installed': True, 'name': full_name,
                                   'locale': 'en_us', 'permissions': PERMISSIONS, 'access_token': accessToken})

            print response