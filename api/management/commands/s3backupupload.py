import os
from django.core.management import BaseCommand
import time
import tinys3
from buddyup.settings import AWS_ACCESS_KEY, AWS_SECRET_KEY



class Command(BaseCommand):

    def handle(self, *args, **options):
        conn = tinys3.Connection(AWS_ACCESS_KEY,AWS_SECRET_KEY)
        now = time.strftime("%c")
        fileName = 'lasbdb' + now
        fileName.replace (" ", "_")
        os.system('sudo -u root sudo -u postgres pg_dump -Fc buddyup > ' + fileName)

        f = open('last.db', 'rb')
        conn.upload('last.db', f, 'buddyupbackup')

        os.system('rm ' + fileName)
