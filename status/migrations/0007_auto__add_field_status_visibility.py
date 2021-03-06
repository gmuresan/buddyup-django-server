# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Status.visibility'
        db.add_column(u'status_status', 'visibility',
                      self.gf('django.db.models.fields.CharField')(default='friends', max_length=20, db_index=True),
                      keep_default=False)

        # Adding M2M table for field friendsVisible on 'Status'
        m2m_table_name = db.shorten_name(u'status_status_friendsVisible')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('status', models.ForeignKey(orm[u'status.status'], null=False)),
            ('userprofile', models.ForeignKey(orm[u'userprofile.userprofile'], null=False))
        ))
        db.create_unique(m2m_table_name, ['status_id', 'userprofile_id'])

        # Adding M2M table for field fbFriendsVisible on 'Status'
        m2m_table_name = db.shorten_name(u'status_status_fbFriendsVisible')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('status', models.ForeignKey(orm[u'status.status'], null=False)),
            ('facebookuser', models.ForeignKey(orm[u'userprofile.facebookuser'], null=False))
        ))
        db.create_unique(m2m_table_name, ['status_id', 'facebookuser_id'])


    def backwards(self, orm):
        # Deleting field 'Status.visibility'
        db.delete_column(u'status_status', 'visibility')

        # Removing M2M table for field friendsVisible on 'Status'
        db.delete_table(db.shorten_name(u'status_status_friendsVisible'))

        # Removing M2M table for field fbFriendsVisible on 'Status'
        db.delete_table(db.shorten_name(u'status_status_fbFriendsVisible'))


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'status.location': {
            'Meta': {'object_name': 'Location', 'index_together': "[['address', 'city', 'state'], ['city', 'state']]"},
            'address': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '40', 'null': 'True', 'blank': 'True'}),
            'city': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '30', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lat': ('django.db.models.fields.FloatField', [], {}),
            'lng': ('django.db.models.fields.FloatField', [], {}),
            'point': ('django.contrib.gis.db.models.fields.PointField', [], {'geography': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'venue': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '60', 'null': 'True', 'blank': 'True'})
        },
        u'status.poke': {
            'Meta': {'object_name': 'Poke'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'recipient': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'receivedPokes'", 'to': u"orm['userprofile.UserProfile']"}),
            'sender': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sentPokes'", 'to': u"orm['userprofile.UserProfile']"})
        },
        u'status.status': {
            'Meta': {'ordering': "['-date']", 'object_name': 'Status'},
            'attending': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'statusesAttending'", 'symmetrical': 'False', 'to': u"orm['userprofile.UserProfile']"}),
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'db_index': 'True', 'blank': 'True'}),
            'expires': ('django.db.models.fields.DateTimeField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'fbFriendsVisible': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'visibleStatuses'", 'symmetrical': 'False', 'to': u"orm['userprofile.FacebookUser']"}),
            'friendsVisible': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'visibleStatuses'", 'symmetrical': 'False', 'to': u"orm['userprofile.UserProfile']"}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'receivedStatuses'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['userprofile.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invited': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'statusesInvited'", 'symmetrical': 'False', 'to': u"orm['userprofile.UserProfile']"}),
            'location': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'statuses'", 'null': 'True', 'to': u"orm['status.Location']"}),
            'starts': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'db_index': 'True'}),
            'statusType': ('django.db.models.fields.CharField', [], {'default': "'other'", 'max_length': '10', 'db_index': 'True'}),
            'text': ('django.db.models.fields.CharField', [], {'max_length': '100', 'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'statuses'", 'to': u"orm['userprofile.UserProfile']"}),
            'visibility': ('django.db.models.fields.CharField', [], {'default': "'friends'", 'max_length': '20', 'db_index': 'True'})
        },
        u'status.statusmessage': {
            'Meta': {'ordering': "['-date']", 'object_name': 'StatusMessage'},
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'status': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'messages'", 'to': u"orm['status.Status']"}),
            'text': ('django.db.models.fields.TextField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'statusMessages'", 'to': u"orm['userprofile.UserProfile']"})
        },
        u'userprofile.facebookuser': {
            'Meta': {'object_name': 'FacebookUser'},
            'facebookUID': ('django.db.models.fields.CharField', [], {'max_length': '64', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'userprofile.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'members': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'groupsIn'", 'symmetrical': 'False', 'to': u"orm['userprofile.UserProfile']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'groups'", 'to': u"orm['userprofile.UserProfile']"})
        },
        u'userprofile.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'blockedFriends': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'blockedFriends_rel_+'", 'null': 'True', 'to': u"orm['userprofile.UserProfile']"}),
            'device': ('django.db.models.fields.CharField', [], {'default': "'ios'", 'max_length': '10'}),
            'facebookUID': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'friends': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'friends_rel_+'", 'null': 'True', 'to': u"orm['userprofile.UserProfile']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lastActivity': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True'})
        }
    }

    complete_apps = ['status']