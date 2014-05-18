# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Location.venue'
        db.alter_column('status_location', 'venue', self.gf('django.db.models.fields.CharField')(max_length=80, null=True))

        # Changing field 'Location.address'
        db.alter_column('status_location', 'address', self.gf('django.db.models.fields.CharField')(max_length=100, null=True))

    def backwards(self, orm):

        # Changing field 'Location.venue'
        db.alter_column('status_location', 'venue', self.gf('django.db.models.fields.CharField')(max_length=60, null=True))

        # Changing field 'Location.address'
        db.alter_column('status_location', 'address', self.gf('django.db.models.fields.CharField')(max_length=40, null=True))

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80', 'unique': 'True'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['auth.Permission']", 'blank': 'True'})
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
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['auth.Group']", 'blank': 'True', 'related_name': "'user_set'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['auth.Permission']", 'blank': 'True', 'related_name': "'user_set'"}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '30', 'unique': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'ordering': "('name',)", 'db_table': "'django_content_type'", 'object_name': 'ContentType'},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'status.location': {
            'Meta': {'object_name': 'Location', 'index_together': "[['address', 'city', 'state'], ['city', 'state']]"},
            'address': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True', 'db_index': 'True'}),
            'city': ('django.db.models.fields.CharField', [], {'max_length': '30', 'null': 'True', 'blank': 'True', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lat': ('django.db.models.fields.FloatField', [], {}),
            'lng': ('django.db.models.fields.FloatField', [], {}),
            'point': ('django.contrib.gis.db.models.fields.PointField', [], {'geography': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '2', 'null': 'True', 'blank': 'True', 'db_index': 'True'}),
            'venue': ('django.db.models.fields.CharField', [], {'max_length': '80', 'null': 'True', 'blank': 'True', 'db_index': 'True'})
        },
        'status.locationsuggestion': {
            'Meta': {'ordering': "['-dateCreated']", 'object_name': 'LocationSuggestion'},
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
            'Meta': {'ordering': "['-date']", 'object_name': 'Status'},
            'attending': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['userprofile.UserProfile']", 'null': 'True', 'blank': 'True', 'related_name': "'statusesAttending'"}),
            'date': ('django.db.models.fields.DateTimeField', [], {'blank': 'True', 'db_index': 'True', 'auto_now': 'True'}),
            'dateCreated': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'blank': 'True', 'auto_now_add': 'True'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'expires': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True', 'db_index': 'True'}),
            'fbAttending': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['userprofile.FacebookUser']", 'null': 'True', 'blank': 'True', 'related_name': "'statusesAttending'"}),
            'fbFriendsVisible': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['userprofile.FacebookUser']", 'null': 'True', 'blank': 'True', 'related_name': "'statusesVisible'"}),
            'fbInvited': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['userprofile.FacebookUser']", 'null': 'True', 'blank': 'True', 'related_name': "'statusesInvited'"}),
            'friendsVisible': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['userprofile.UserProfile']", 'null': 'True', 'blank': 'True', 'related_name': "'statusesVisible'"}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['userprofile.Group']", 'null': 'True', 'blank': 'True', 'related_name': "'receivedStatuses'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'imageOrientation': ('django.db.models.fields.CharField', [], {'max_length': '1', 'default': "'u'", 'blank': 'True', 'null': 'True'}),
            'imageUrl': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True', 'null': 'True'}),
            'invited': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['userprofile.UserProfile']", 'null': 'True', 'blank': 'True', 'related_name': "'statusesInvited'"}),
            'location': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['status.Location']", 'null': 'True', 'blank': 'True', 'related_name': "'statuses'"}),
            'starts': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'statusType': ('django.db.models.fields.CharField', [], {'max_length': '10', 'default': "'other'", 'blank': 'True', 'db_index': 'True', 'null': 'True'}),
            'text': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['userprofile.UserProfile']", 'related_name': "'statuses'"}),
            'visibility': ('django.db.models.fields.CharField', [], {'max_length': '20', 'default': "'friends'", 'blank': 'True', 'db_index': 'True', 'null': 'True'})
        },
        'status.statusmessage': {
            'Meta': {'ordering': "['-date']", 'object_name': 'StatusMessage'},
            'date': ('django.db.models.fields.DateTimeField', [], {'blank': 'True', 'db_index': 'True', 'auto_now_add': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'status': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['status.Status']", 'related_name': "'messages'"}),
            'text': ('django.db.models.fields.TextField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['userprofile.UserProfile']", 'related_name': "'statusMessages'"})
        },
        'status.timesuggestion': {
            'Meta': {'ordering': "['-dateCreated']", 'object_name': 'TimeSuggestion'},
            'dateCreated': ('django.db.models.fields.DateTimeField', [], {'blank': 'True', 'auto_now_add': 'True'}),
            'dateSuggested': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'status': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['status.Status']", 'related_name': "'timeSuggestions'"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['userprofile.UserProfile']", 'related_name': "'timeSuggestions'"})
        },
        'userprofile.facebookuser': {
            'Meta': {'object_name': 'FacebookUser'},
            'facebookUID': ('django.db.models.fields.CharField', [], {'max_length': '64', 'db_index': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'userprofile.group': {
            'Meta': {'object_name': 'Group'},
            'fbMembers': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['userprofile.FacebookUser']", 'null': 'True', 'blank': 'True', 'related_name': "'groupsIn'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'members': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['userprofile.UserProfile']", 'null': 'True', 'blank': 'True', 'related_name': "'groupsIn'"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['userprofile.UserProfile']", 'related_name': "'groups'"})
        },
        'userprofile.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'blockedFriends': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['userprofile.UserProfile']", 'null': 'True', 'blank': 'True', 'related_name': "'blockedFriends_rel_+'"}),
            'device': ('django.db.models.fields.CharField', [], {'max_length': '10', 'default': "'ios'"}),
            'facebookUID': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True', 'db_index': 'True'}),
            'favoritesNotifications': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'friends': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['userprofile.UserProfile']", 'null': 'True', 'blank': 'True', 'related_name': "'friends_rel_+'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lastActivity': ('django.db.models.fields.DateTimeField', [], {'blank': 'True', 'auto_now': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
        }
    }

    complete_apps = ['status']