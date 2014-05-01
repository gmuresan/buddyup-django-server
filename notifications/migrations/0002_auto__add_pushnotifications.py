# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'PushNotifications'
        db.create_table('notifications_pushnotifications', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('date', self.gf('django.db.models.fields.DateTimeField')(blank=True, auto_now=True)),
            ('sendingUser', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['userprofile.UserProfile'])),
            ('pushNotificationType', self.gf('django.db.models.fields.IntegerField')(db_index=True)),
            ('status', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['status.Status'], null=True, blank=True)),
            ('message', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['status.StatusMessage'], null=True, blank=True)),
            ('chatMessage', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['chat.Message'], null=True, blank=True)),
        ))
        db.send_create_signal('notifications', ['PushNotifications'])

        # Adding M2M table for field receivingUsers on 'PushNotifications'
        m2m_table_name = db.shorten_name('notifications_pushnotifications_receivingUsers')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('pushnotifications', models.ForeignKey(orm['notifications.pushnotifications'], null=False)),
            ('userprofile', models.ForeignKey(orm['userprofile.userprofile'], null=False))
        ))
        db.create_unique(m2m_table_name, ['pushnotifications_id', 'userprofile_id'])


    def backwards(self, orm):
        # Deleting model 'PushNotifications'
        db.delete_table('notifications_pushnotifications')

        # Removing M2M table for field receivingUsers on 'PushNotifications'
        db.delete_table(db.shorten_name('notifications_pushnotifications_receivingUsers'))


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True', 'symmetrical': 'False'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'blank': 'True', 'max_length': '75'}),
            'first_name': ('django.db.models.fields.CharField', [], {'blank': 'True', 'max_length': '30'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True', 'related_name': "'user_set'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'blank': 'True', 'max_length': '30'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True', 'related_name': "'user_set'"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'chat.conversation': {
            'Meta': {'object_name': 'Conversation'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lastActivity': ('django.db.models.fields.DateTimeField', [], {'blank': 'True', 'auto_now': 'True'}),
            'members': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['userprofile.UserProfile']", 'symmetrical': 'False', 'related_name': "'conversations'"})
        },
        'chat.message': {
            'Meta': {'ordering': "['-created']", 'object_name': 'Message'},
            'conversation': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chat.Conversation']", 'related_name': "'messages'"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['userprofile.UserProfile']", 'related_name': "'messages'"})
        },
        'contenttypes.contenttype': {
            'Meta': {'db_table': "'django_content_type'", 'unique_together': "(('app_label', 'model'),)", 'ordering': "('name',)", 'object_name': 'ContentType'},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'notifications.apnsdevice': {
            'Meta': {'object_name': 'APNSDevice'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'device_id': ('notifications.fields.UUIDField', [], {'null': 'True', 'blank': 'True', 'max_length': '32'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'null': 'True', 'blank': 'True', 'max_length': '255'}),
            'registration_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '64'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['userprofile.UserProfile']", 'null': 'True', 'blank': 'True'})
        },
        'notifications.gcmdevice': {
            'Meta': {'object_name': 'GCMDevice'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'device_id': ('notifications.fields.UUIDField', [], {'null': 'True', 'blank': 'True', 'max_length': '32'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'null': 'True', 'blank': 'True', 'max_length': '255'}),
            'registration_id': ('django.db.models.fields.TextField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['userprofile.UserProfile']", 'null': 'True', 'blank': 'True'})
        },
        'notifications.notification': {
            'Meta': {'object_name': 'Notification'},
            'date': ('django.db.models.fields.DateTimeField', [], {'blank': 'True', 'auto_now': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'initiatingUser': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['userprofile.UserProfile']", 'related_name': "'notificationsInitiated'"}),
            'message': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['status.StatusMessage']", 'null': 'True', 'blank': 'True'}),
            'notificationType': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'status': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['status.Status']", 'null': 'True', 'blank': 'True'}),
            'users': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['userprofile.UserProfile']", 'symmetrical': 'False', 'null': 'True', 'related_name': "'notifications'", 'blank': 'True'})
        },
        'notifications.pushnotifications': {
            'Meta': {'object_name': 'PushNotifications'},
            'chatMessage': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['chat.Message']", 'null': 'True', 'blank': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'blank': 'True', 'auto_now': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['status.StatusMessage']", 'null': 'True', 'blank': 'True'}),
            'pushNotificationType': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'receivingUsers': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['userprofile.UserProfile']", 'symmetrical': 'False', 'related_name': "'pushNotifications'"}),
            'sendingUser': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['userprofile.UserProfile']"}),
            'status': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['status.Status']", 'null': 'True', 'blank': 'True'})
        },
        'status.location': {
            'Meta': {'index_together': "[['address', 'city', 'state'], ['city', 'state']]", 'object_name': 'Location'},
            'address': ('django.db.models.fields.CharField', [], {'blank': 'True', 'null': 'True', 'max_length': '40', 'db_index': 'True'}),
            'city': ('django.db.models.fields.CharField', [], {'blank': 'True', 'null': 'True', 'max_length': '30', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lat': ('django.db.models.fields.FloatField', [], {}),
            'lng': ('django.db.models.fields.FloatField', [], {}),
            'point': ('django.contrib.gis.db.models.fields.PointField', [], {'geography': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'blank': 'True', 'null': 'True', 'max_length': '2', 'db_index': 'True'}),
            'venue': ('django.db.models.fields.CharField', [], {'blank': 'True', 'null': 'True', 'max_length': '60', 'db_index': 'True'})
        },
        'status.status': {
            'Meta': {'ordering': "['-date']", 'object_name': 'Status'},
            'attending': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['userprofile.UserProfile']", 'symmetrical': 'False', 'null': 'True', 'related_name': "'statusesAttending'", 'blank': 'True'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'blank': 'True', 'auto_now': 'True', 'db_index': 'True'}),
            'dateCreated': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True', 'default': 'datetime.datetime.now'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'expires': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True', 'db_index': 'True'}),
            'fbAttending': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['userprofile.FacebookUser']", 'symmetrical': 'False', 'null': 'True', 'related_name': "'statusesAttending'", 'blank': 'True'}),
            'fbFriendsVisible': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['userprofile.FacebookUser']", 'symmetrical': 'False', 'null': 'True', 'related_name': "'statusesVisible'", 'blank': 'True'}),
            'fbInvited': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['userprofile.FacebookUser']", 'symmetrical': 'False', 'null': 'True', 'related_name': "'statusesInvited'", 'blank': 'True'}),
            'friendsVisible': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['userprofile.UserProfile']", 'symmetrical': 'False', 'null': 'True', 'related_name': "'statusesVisible'", 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['userprofile.Group']", 'symmetrical': 'False', 'null': 'True', 'related_name': "'receivedStatuses'", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'imageOrientation': ('django.db.models.fields.CharField', [], {'blank': 'True', 'null': 'True', 'default': "'u'", 'max_length': '1'}),
            'imageUrl': ('django.db.models.fields.URLField', [], {'null': 'True', 'blank': 'True', 'max_length': '200'}),
            'invited': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['userprofile.UserProfile']", 'symmetrical': 'False', 'null': 'True', 'related_name': "'statusesInvited'", 'blank': 'True'}),
            'location': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['status.Location']", 'null': 'True', 'related_name': "'statuses'", 'blank': 'True'}),
            'starts': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'statusType': ('django.db.models.fields.CharField', [], {'blank': 'True', 'null': 'True', 'max_length': '10', 'default': "'other'", 'db_index': 'True'}),
            'text': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['userprofile.UserProfile']", 'related_name': "'statuses'"}),
            'visibility': ('django.db.models.fields.CharField', [], {'blank': 'True', 'null': 'True', 'max_length': '20', 'default': "'friends'", 'db_index': 'True'})
        },
        'status.statusmessage': {
            'Meta': {'ordering': "['-date']", 'object_name': 'StatusMessage'},
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'status': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['status.Status']", 'related_name': "'messages'"}),
            'text': ('django.db.models.fields.TextField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['userprofile.UserProfile']", 'related_name': "'statusMessages'"})
        },
        'userprofile.facebookuser': {
            'Meta': {'object_name': 'FacebookUser'},
            'facebookUID': ('django.db.models.fields.CharField', [], {'max_length': '64', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'userprofile.group': {
            'Meta': {'object_name': 'Group'},
            'fbMembers': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['userprofile.FacebookUser']", 'symmetrical': 'False', 'null': 'True', 'related_name': "'groupsIn'", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'members': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['userprofile.UserProfile']", 'symmetrical': 'False', 'null': 'True', 'related_name': "'groupsIn'", 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['userprofile.UserProfile']", 'related_name': "'groups'"})
        },
        'userprofile.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'blockedFriends': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['userprofile.UserProfile']", 'null': 'True', 'related_name': "'blockedFriends_rel_+'", 'blank': 'True'}),
            'device': ('django.db.models.fields.CharField', [], {'default': "'ios'", 'max_length': '10'}),
            'facebookUID': ('django.db.models.fields.CharField', [], {'blank': 'True', 'null': 'True', 'max_length': '64', 'db_index': 'True'}),
            'favoritesNotifications': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'friends': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['userprofile.UserProfile']", 'null': 'True', 'related_name': "'friends_rel_+'", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lastActivity': ('django.db.models.fields.DateTimeField', [], {'blank': 'True', 'auto_now': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
        }
    }

    complete_apps = ['notifications']