import os
from django.core.management import BaseCommand
import tinys3
from buddyup.settings import AWS_ACCESS_KEY, AWS_SECRET_KEY



class Command(BaseCommand):

    def handle(self, *args, **options):
        conn = tinys3.Connection(AWS_ACCESS_KEY,AWS_SECRET_KEY)

        os.system('sudo -u root sudo -u postgres pg_dump -Fc buddyup > last.db')

        f = open('last.db', 'rb')
        conn.upload('last.db', f, 'buddyupbackup')
