# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Status.imageOrientation'
        db.add_column('status_status', 'imageOrientation',
                      self.gf('django.db.models.fields.CharField')(null=True, default='u', blank=True, max_length=1),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Status.imageOrientation'
        db.delete_column('status_status', 'imageOrientation')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'blank': 'True', 'to': "orm['auth.Permission']"})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission', 'ordering': "('content_type__app_label', 'content_type__model', 'codename')"},
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
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'blank': 'True', 'to': "orm['auth.Group']", 'related_name': "'user_set'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'blank': 'True', 'max_length': '30'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'blank': 'True', 'to': "orm['auth.Permission']", 'related_name': "'user_set'"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'", 'ordering': "('name',)"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'status.location': {
            'Meta': {'index_together': "[['address', 'city', 'state'], ['city', 'state']]", 'object_name': 'Location'},
            'address': ('django.db.models.fields.CharField', [], {'null': 'True', 'blank': 'True', 'max_length': '40', 'db_index': 'True'}),
            'city': ('django.db.models.fields.CharField', [], {'null': 'True', 'blank': 'True', 'max_length': '30', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lat': ('django.db.models.fields.FloatField', [], {}),
            'lng': ('django.db.models.fields.FloatField', [], {}),
            'point': ('django.contrib.gis.db.models.fields.PointField', [], {'geography': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'null': 'True', 'blank': 'True', 'max_length': '2', 'db_index': 'True'}),
            'venue': ('django.db.models.fields.CharField', [], {'null': 'True', 'blank': 'True', 'max_length': '60', 'db_index': 'True'})
        },
        'status.locationsuggestion': {
            'Meta': {'object_name': 'LocationSuggestion', 'ordering': "['-dateCreated']"},
            'dateCreated': ('django.db.models.fields.DateTimeField', [], {'blank': 'True', 'auto_now_add': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['status.Location']"}),
            'status': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['status.Status']", 'related_name': "'locationSuggestions'"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['userprofile.UserProfile']", 'related_name': "'locationSuggestions'"})
        },
        'status.poke': {
            'Meta': {'object_name': 'Poke'},
            'created': ('django.db.models.fields.DateTimeField', [], {'blank': 'True', 'auto_now_add': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'recipient': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['userprofile.UserProfile']", 'related_name': "'receivedPokes'"}),
            'sender': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['userprofile.UserProfile']", 'related_name': "'sentPokes'"})
        },
        'status.status': {
            'Meta': {'object_name': 'Status', 'ordering': "['-date']"},
            'attending': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'blank': 'True', 'null': 'True', 'to': "orm['userprofile.UserProfile']", 'related_name': "'statusesAttending'"}),
            'date': ('django.db.models.fields.DateTimeField', [], {'blank': 'True', 'auto_now': 'True', 'db_index': 'True'}),
            'dateCreated': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True', 'auto_now_add': 'True'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'expires': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'blank': 'True', 'null': 'True'}),
            'fbAttending': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'blank': 'True', 'null': 'True', 'to': "orm['userprofile.FacebookUser']", 'related_name': "'statusesAttending'"}),
            'fbFriendsVisible': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'blank': 'True', 'null': 'True', 'to': "orm['userprofile.FacebookUser']", 'related_name': "'statusesVisible'"}),
            'fbInvited': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'blank': 'True', 'null': 'True', 'to': "orm['userprofile.FacebookUser']", 'related_name': "'statusesInvited'"}),
            'friendsVisible': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'blank': 'True', 'null': 'True', 'to': "orm['userprofile.UserProfile']", 'related_name': "'statusesVisible'"}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'blank': 'True', 'null': 'True', 'to': "orm['userprofile.Group']", 'related_name': "'receivedStatuses'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'imageOrientation': ('django.db.models.fields.CharField', [], {'null': 'True', 'default': "'u'", 'blank': 'True', 'max_length': '1'}),
            'imageUrl': ('django.db.models.fields.URLField', [], {'null': 'True', 'blank': 'True', 'max_length': '200'}),
            'invited': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'blank': 'True', 'null': 'True', 'to': "orm['userprofile.UserProfile']", 'related_name': "'statusesInvited'"}),
            'location': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'statuses'", 'blank': 'True', 'null': 'True', 'to': "orm['status.Location']"}),
            'starts': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'statusType': ('django.db.models.fields.CharField', [], {'null': 'True', 'default': "'other'", 'blank': 'True', 'max_length': '10', 'db_index': 'True'}),
            'text': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '100'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['userprofile.UserProfile']", 'related_name': "'statuses'"}),
            'visibility': ('django.db.models.fields.CharField', [], {'null': 'True', 'default': "'friends'", 'blank': 'True', 'max_length': '20', 'db_index': 'True'})
        },
        'status.statusmessage': {
            'Meta': {'object_name': 'StatusMessage', 'ordering': "['-date']"},
            'date': ('django.db.models.fields.DateTimeField', [], {'blank': 'True', 'db_index': 'True', 'auto_now_add': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'status': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['status.Status']", 'related_name': "'messages'"}),
            'text': ('django.db.models.fields.TextField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['userprofile.UserProfile']", 'related_name': "'statusMessages'"})
        },
        'status.timesuggestion': {
            'Meta': {'object_name': 'TimeSuggestion', 'ordering': "['-dateCreated']"},
            'dateCreated': ('django.db.models.fields.DateTimeField', [], {'blank': 'True', 'auto_now_add': 'True'}),
            'dateSuggested': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'status': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['status.Status']", 'related_name': "'timeSuggestions'"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['userprofile.UserProfile']", 'related_name': "'timeSuggestions'"})
        },
        'userprofile.facebookuser': {
            'Meta': {'object_name': 'FacebookUser'},
            'facebookUID': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '64'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'userprofile.group': {
            'Meta': {'object_name': 'Group'},
            'fbMembers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'blank': 'True', 'null': 'True', 'to': "orm['userprofile.FacebookUser']", 'related_name': "'groupsIn'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'members': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'blank': 'True', 'null': 'True', 'to': "orm['userprofile.UserProfile']", 'related_name': "'groupsIn'"}),
            'name': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '64'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['userprofile.UserProfile']", 'related_name': "'groups'"})
        },
        'userprofile.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'blockedFriends': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'blockedFriends_rel_+'", 'blank': 'True', 'null': 'True', 'to': "orm['userprofile.UserProfile']"}),
            'device': ('django.db.models.fields.CharField', [], {'default': "'ios'", 'max_length': '10'}),
            'facebookUID': ('django.db.models.fields.CharField', [], {'null': 'True', 'blank': 'True', 'max_length': '64', 'db_index': 'True'}),
            'favoritesNotifications': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'friends': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'friends_rel_+'", 'blank': 'True', 'null': 'True', 'to': "orm['userprofile.UserProfile']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lastActivity': ('django.db.models.fields.DateTimeField', [], {'blank': 'True', 'auto_now': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'unique': 'True', 'to': "orm['auth.User']"})
        }
    }

    complete_apps = ['status']