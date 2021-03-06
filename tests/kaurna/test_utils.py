#!/usr/bin/env python

from boto.dynamodb.condition import EQ
from boto.exception import DynamoDBResponseError
from kaurna import *
import kaurna # necessary to test _generate_encryption_context
from mock import call, MagicMock, Mock, patch
from nose.tools import assert_equals, raises
from unittest import TestCase

# http://www.openp2p.com/pub/a/python/2004/12/02/tdd_pyunit.html

class KaurnaUtilsTests(TestCase):

    def setUp(self):
        self.mock_kms = MagicMock()
        self.mock_connect_kms = MagicMock(return_value=self.mock_kms)
        patch('kaurna.boto.kms.connect_to_region', self.mock_connect_kms).start()

        self.mock_ddb = MagicMock()
        self.mock_connect_ddb = MagicMock(return_value=self.mock_ddb)
        patch('kaurna.boto.dynamodb.connect_to_region', self.mock_connect_ddb).start()

        self.region = 'us-west-1'

    def tearDown(self):
        patch.stopall()

    def test_GIVEN_kaurna_table_doesnt_exist_WHEN_get_kaurna_table_called_THEN_table_created_and_returned(self):
        # GIVEN - set up mocks
        self.mock_ddb.get_table.side_effect = [DynamoDBResponseError('Foo','Bar')]

        mock_table = MagicMock()
        self.mock_ddb.create_table.return_value = mock_table

        mock_schema = MagicMock()
        self.mock_ddb.create_schema.return_value = mock_schema

        # WHEN - perform the actions under test
        returned_table = get_kaurna_table(region=self.region, read_throughput=5, write_throughput=2)

        # THEN - verify the expected results were observed
        assert_equals(mock_table, returned_table)
        assert_equals(
            self.mock_connect_ddb.call_args_list,
            [call(region_name=self.region)]
            )
        assert_equals(
            self.mock_ddb.create_table.call_args_list,
            [call(name='kaurna', schema=mock_schema, read_units=5, write_units=2)]
            )

    def test_GIVEN_kaurna_table_exists_WHEN_get_kaurna_table_called_THEN_table_returned(self):
        # GIVEN - set up mocks
        mock_table = MagicMock()
        self.mock_ddb.get_table.return_value = mock_table

        # WHEN - perform the actions under test
        returned_table = get_kaurna_table(region=self.region, read_throughput=5, write_throughput=2)

        # THEN - verify the expected results were observed
        assert_equals(mock_table, returned_table)
        assert_equals(
            self.mock_connect_ddb.call_args_list,
            [call(region_name=self.region)]
            )
        assert_equals(
            self.mock_ddb.create_table.call_args_list,
            []
            )

    def test_GIVEN_kaurna_key_doesnt_exist_WHEN_create_kaurna_key_called_THEN_kaurna_key_created(self):
        # GIVEN
        self.mock_kms.list_aliases.return_value = {'Aliases':[
                {'AliasArn': 'arn:aws:kms:us-east-1:000000000000:alias/aws/ebs', 'AliasName': 'alias/aws/ebs'},
                {'AliasArn': 'arn:aws:kms:us-east-1:000000000000:alias/aws/redshift', 'AliasName': 'alias/aws/redshift'},
                {'AliasArn': 'arn:aws:kms:us-east-1:000000000000:alias/aws/s3', 'AliasName': 'alias/aws/s3'},
                ]}
        self.mock_kms.create_key.return_value = {'KeyMetadata':{'KeyId':'foobar'}}

        # WHEN
        response = create_kaurna_key(region=self.region)

        # THEN
        assert_equals(
            True,
            response
            )
        assert_equals(
            self.mock_connect_kms.call_args_list,
            [call(region_name=self.region)]
            )
        assert_equals(
            self.mock_kms.create_key.call_args_list,
            [call()]
            )
        assert_equals(
            self.mock_kms.create_alias.call_args_list,
            [call('alias/kaurna', 'foobar')]
            )

    def test_GIVEN_kaurna_key_exists_WHEN_create_kaurna_key_called_THEN_nothing_happens(self):
        # GIVEN
        self.mock_kms.list_aliases.return_value = {'Aliases':[
                {'AliasArn': 'arn:aws:kms:us-east-1:000000000000:alias/aws/ebs', 'AliasName': 'alias/aws/ebs'},
                {'AliasArn': 'arn:aws:kms:us-east-1:000000000000:alias/aws/redshift', 'AliasName': 'alias/aws/redshift'},
                {'AliasArn': 'arn:aws:kms:us-east-1:000000000000:alias/aws/s3', 'AliasName': 'alias/aws/s3'},
                {'AliasArn': 'arn:aws:kms:us-east-1:000000000000:alias/kaurna', 'AliasName': 'alias/kaurna'},
                ]}

        # WHEN
        response = create_kaurna_key(region=self.region)

        # THEN
        assert_equals(
            False,
            response
            )
        assert_equals(
            self.mock_connect_kms.call_args_list,
            [call(region_name=self.region)]
            )
        assert_equals(
            self.mock_kms.create_key.call_args_list,
            []
            )
        assert_equals(
            self.mock_kms.create_alias.call_args_list,
            []
            )

    def test_WHEN_get_data_key_called_THEN_kaurna_key_created_and_data_key_generated(self):
        # GIVEN
        expected_data_key = {'Plaintext': '<binary blob>', 'KeyId': 'arn:aws:kms:us-east-1:000000000000:key/1234abcd-12ab-12ab-12ab-123456abcdef', 'CiphertextBlob': '<binary blob>'}
        self.mock_kms.generate_data_key.return_value = expected_data_key

        encryption_context = {'hafgufa':'kaurna','edofleini':'kaurna'}

        # WHEN
        actual_data_key = get_data_key(encryption_context=encryption_context, region=self.region)

        # THEN
        assert_equals(
            expected_data_key,
            actual_data_key
            )
        assert_equals(
            self.mock_connect_kms.call_args_list,
            [call(region_name=self.region)]
            )
        assert_equals(
            self.mock_kms.generate_data_key.call_args_list,
            [call(key_id='alias/kaurna', encryption_context=encryption_context, key_spec='AES_256')]
            )

    # Don't really need to test; it's an entirely internal method with no network calls.
    # It's covered by other tests, but testing it separately makes it easy to pinpoint if it ever gets broken.
    def test_WHEN__generate_encryption_context_called_THEN_proper_encryption_context_generated(self):
        # GIVEN
        expected_encryption_context = {'hafgufa':'kaurna','edofleini':'kaurna'}
        authorized_entities = ['hafgufa','edofleini']

        # WHEN
        actual_encryption_context = kaurna._generate_encryption_context(authorized_entities=authorized_entities)

        # THEN
        assert_equals(
            expected_encryption_context,
            actual_encryption_context
            )

    @raises(Exception)
    def test_GIVEN_secret_not_provided_WHEN_store_secret_called_THEN_error_thrown(self):
        # GIVEN
        secret = None
        secret_name = 'password'
        secret_version = None
        authorized_entities = ['Sterling Archer', 'Cyril Figgis']

        # WHEN
        store_secret(secret=secret, secret_name=secret_name, secret_version=secret_version, authorized_entities=authorized_entities, region=self.region)

        # THEN
        # Exception should get thrown and we should never get here

    @raises(Exception)
    def test_GIVEN_secret_name_not_provided_WHEN_store_secret_called_THEN_error_thrown(self):
        # GIVEN
        secret = 'guest'
        secret_name = None
        secret_version = None
        authorized_entities = ['Sterling Archer', 'Cyril Figgis']

        # WHEN
        store_secret(secret=secret, secret_name=secret_name, secret_version=secret_version, authorized_entities=authorized_entities, region=self.region)

        # THEN
        # Exception should get thrown and we should never get here

    @raises(Exception)
    def test_GIVEN_secret_version_exists_WHEN_store_secret_called_THEN_error_thrown(self):
        # GIVEN
        secret = 'guest'
        secret_name = 'password'
        secret_version = 3
        authorized_entities = ['Sterling Archer', 'Cyril Figgis']

        patch(
            'kaurna.load_all_entries',
            Mock(
                return_value = [
                    {'secret_name':'password','secret_version':3}
                    ]
                )
            ).start()

        # WHEN
        store_secret(secret=secret, secret_name=secret_name, secret_version=secret_version, authorized_entities=authorized_entities, region=self.region)

        # THEN
        # Exception should get thrown and we should never get here

    def test_GIVEN_secret_version_not_provided_WHEN_store_secret_called_THEN_secret_properly_stored(self):
        # GIVEN
        secret = 'guest'
        secret_name = 'password'
        secret_version = None
        authorized_entities = ['Sterling Archer', 'Cyril Figgis']

        patch(
            'kaurna.load_all_entries',
            Mock(
                return_value = [
                    {'secret_name':'password','secret_version':1},
                    {'secret_name':'password','secret_version':2},
                    {'secret_name':'password','secret_version':4}
                    ]
                )
            ).start()

        patch('kaurna.get_data_key', Mock(return_value={'CiphertextBlob':'abcdabcdabcdabcd','Plaintext':'1234123412341234'})).start()
        patch('kaurna.encrypt_with_key', Mock(return_value='<insert encrypted stuff here>')).start()
        patch('kaurna.time.time', Mock(return_value=1234.5678)).start()

        mock_table = MagicMock()
        mock_get_table = MagicMock(return_value=mock_table)
        patch('kaurna.get_kaurna_table', mock_get_table).start()

        mock_item = MagicMock()
        mock_table.new_item.return_value = mock_item

        expected_attributes = {
            'secret_name': secret_name,
            'secret_version': 5,
            'encrypted_secret': '<insert encrypted stuff here>',
            'encrypted_data_key': binascii.b2a_base64('abcdabcdabcdabcd'),
            'encryption_context': '{"Sterling Archer": "kaurna", "Cyril Figgis": "kaurna"}',
            'authorized_entities': json.dumps(authorized_entities),
            'create_date': 1234,
            'last_data_key_rotation': 1234,
            'deprecated': False
            }

        # WHEN
        store_secret(secret=secret, secret_name=secret_name, secret_version=secret_version, authorized_entities=authorized_entities, region=self.region)

        # THEN
        assert_equals(
            mock_get_table.call_args_list,
            [call(region=self.region)]
            )
        assert_equals(
            mock_table.new_item.call_args_list,
            [call(attrs=expected_attributes)]
            )
        assert_equals(
            mock_item.save.call_args_list,
            [call()]
            )

    def test_GIVEN_secret_version_provided_WHEN_store_secret_called_THEN_secret_properly_stored(self):
        # GIVEN
        secret = 'guest'
        secret_name = 'password'
        secret_version = 3
        authorized_entities = ['Sterling Archer', 'Cyril Figgis']

        patch(
            'kaurna.load_all_entries',
            Mock(
                return_value = []
                )
            ).start()

        patch('kaurna.get_data_key', Mock(return_value={'CiphertextBlob':'abcdabcdabcdabcd','Plaintext':'1234123412341234'})).start()
        patch('kaurna.encrypt_with_key', Mock(return_value='<insert encrypted stuff here>')).start()
        patch('kaurna.time.time', Mock(return_value=1234.5678)).start()

        mock_table = MagicMock()
        mock_get_table = MagicMock(return_value=mock_table)
        patch('kaurna.get_kaurna_table', mock_get_table).start()

        mock_item = MagicMock()
        mock_table.new_item.return_value = mock_item

        expected_attributes = {
            'secret_name': secret_name,
            'secret_version': 3,
            'encrypted_secret': '<insert encrypted stuff here>',
            'encrypted_data_key': binascii.b2a_base64('abcdabcdabcdabcd'),
            'encryption_context': '{"Sterling Archer": "kaurna", "Cyril Figgis": "kaurna"}',
            'authorized_entities': json.dumps(authorized_entities),
            'create_date': 1234,
            'last_data_key_rotation': 1234,
            'deprecated': False
            }

        # WHEN
        store_secret(secret=secret, secret_name=secret_name, secret_version=secret_version, authorized_entities=authorized_entities, region=self.region)

        # THEN
        assert_equals(
            mock_get_table.call_args_list,
            [call(region=self.region)]
            )
        assert_equals(
            mock_table.new_item.call_args_list,
            [call(attrs=expected_attributes)]
            )
        assert_equals(
            mock_item.save.call_args_list,
            [call()]
            )

    @raises(Exception)
    def test_GIVEN_secret_version_but_not_secret_name_provided_WHEN_load_all_entries_called_THEN_error_thrown(self):
        # GIVEN
        secret_name = None
        secret_version = 2

        # WHEN
        load_all_entries(secret_name=secret_name, secret_version=secret_version, region=self.region)

        # THEN
        # Exception should get thrown and we should never get here

    def test_GIVEN_secret_name_and_secret_version_provided_WHEN_load_all_entries_called_THEN_proper_dynamodb_call_made(self):
        # GIVEN
        secret_name = 'password'
        secret_version = 2
        attributes_to_get = ['secret_name', 'secret_version']

        mock_table = MagicMock()
        mock_get_table = MagicMock(return_value=mock_table)
        patch('kaurna.get_kaurna_table', mock_get_table).start()
        expected_output = [
            {'secret_name':secret_name,'secret_version':secret_version}
            ]
        mock_table.query.return_value = expected_output

        # WHEN
        actual_output = load_all_entries(secret_name=secret_name, secret_version=secret_version, attributes_to_get=attributes_to_get, region=self.region)

        # THEN
        assert_equals(
            mock_get_table.call_args_list,
            [call(region=self.region)]
            )
        assert_equals(
            expected_output,
            actual_output
            )
        assert_equals(
            mock_table.query.call_args_list,
            [call(hash_key=secret_name, range_key_condition=EQ(int(secret_version)), attributes_to_get=attributes_to_get)]
            )

    def test_GIVEN_secret_name_but_not_secret_version_provided_WHEN_load_all_entries_called_THEN_proper_dynamodb_call_made(self):
        # GIVEN
        secret_name = 'password'
        secret_version = None
        attributes_to_get = ['secret_name', 'secret_version']

        mock_table = MagicMock()
        mock_get_table = MagicMock(return_value=mock_table)
        patch('kaurna.get_kaurna_table', mock_get_table).start()
        expected_output = [
            {'secret_name':secret_name,'secret_version':1},
            {'secret_name':secret_name,'secret_version':2}
            ]
        mock_table.query.return_value = expected_output

        # WHEN
        actual_output = load_all_entries(secret_name=secret_name, secret_version=secret_version, attributes_to_get=attributes_to_get, region=self.region)

        # THEN
        assert_equals(
            mock_get_table.call_args_list,
            [call(region=self.region)]
            )
        assert_equals(
            expected_output,
            actual_output
            )
        assert_equals(
            mock_table.query.call_args_list,
            [call(hash_key=secret_name, attributes_to_get=attributes_to_get)]
            )

    def test_GIVEN_no_secret_information_provided_WHEN_load_all_entries_called_THEN_proper_dynamodb_call_made(self):
        # GIVEN
        secret_name = None
        secret_version = None
        attributes_to_get = ['secret_name', 'secret_version']

        mock_table = MagicMock()
        mock_get_table = MagicMock(return_value=mock_table)
        patch('kaurna.get_kaurna_table', mock_get_table).start()
        expected_output = [
            {'secret_name':'password','secret_version':1},
            {'secret_name':'password','secret_version':2},
            {'secret_name':'private_key','secret_version':1},
            {'secret_name':'private_key','secret_version':2}
            ]
        mock_table.scan.return_value = expected_output

        # WHEN
        actual_output = load_all_entries(secret_name=secret_name, secret_version=secret_version, attributes_to_get=attributes_to_get, region=self.region)

        # THEN
        assert_equals(
            mock_get_table.call_args_list,
            [call(region=self.region)]
            )
        assert_equals(
            expected_output,
            actual_output
            )
        assert_equals(
            mock_table.scan.call_args_list,
            [call(attributes_to_get=attributes_to_get)]
            )

    def test_GIVEN_secret_version_not_provided_WHEN_rotate_data_keys_called_THEN_data_keys_rotated(self):
        # GIVEN
        secret_name = 'password'
        secret_version = None

        item1 = MagicMock()
        item2 = MagicMock()
        item3 = MagicMock()
        mock_load_all_entries = MagicMock(return_value = [item1, item2, item3])
        patch(
            'kaurna.load_all_entries',
            mock_load_all_entries
            ).start()

        mock_reencrypt_item_and_save = MagicMock()
        patch(
            'kaurna._reencrypt_item_and_save',
            mock_reencrypt_item_and_save
            ).start()

        # WHEN
        rotate_data_keys(secret_name=secret_name, secret_version=secret_version, region=self.region)

        # THEN
        assert_equals(
            mock_load_all_entries.call_args_list,
            [call(secret_name=secret_name, secret_version=secret_version, region=self.region)]
            )
        assert_equals(
            mock_reencrypt_item_and_save.call_args_list,
            [
                call(item=item1, region=self.region),
                call(item=item2, region=self.region),
                call(item=item3, region=self.region)
                ]
            )

    def test_GIVEN_secret_version_provided_WHEN_rotate_data_keys_called_THEN_data_keys_rotated(self):
        # GIVEN
        secret_name = 'password'
        secret_version = 2

        item = MagicMock()
        mock_load_all_entries = MagicMock(return_value = [item])
        patch(
            'kaurna.load_all_entries',
            mock_load_all_entries
            ).start()

        mock_reencrypt_item_and_save = MagicMock()
        patch(
            'kaurna._reencrypt_item_and_save',
            mock_reencrypt_item_and_save
            ).start()

        # WHEN
        rotate_data_keys(secret_name=secret_name, secret_version=secret_version, region=self.region)

        # THEN
        assert_equals(
            mock_load_all_entries.call_args_list,
            [call(secret_name=secret_name, secret_version=secret_version, region=self.region)]
            )
        assert_equals(
            mock_reencrypt_item_and_save.call_args_list,
            [call(item=item, region=self.region)]
            )

    def test_WHEN__reencrypt_item_and_save_called_THEN_item_reencrypted_and_saved(self):
        # GIVEN

        item = MagicMock()
        item.getitem.side_effect = ['old_encrypted_secret', 'old_encrypted_data_key', '{"Mallory Archer": "kaurna"}', '["Sterling Archer", "Cyril Figgis"]']

        mock_get_data_key = MagicMock(return_value = {'Plaintext':'data_key_plaintext', 'CiphertextBlob':'data_key_ciphertext'})
        patch(
            'kaurna.get_data_key',
            mock_get_data_key
            ).start()

        mock_decrypt_with_kms = MagicMock(return_value = {'Plaintext': 'decrypt_with_kms_output'})
        patch(
            'kaurna.decrypt_with_kms',
            mock_decrypt_with_kms
            ).start()

        mock_decrypt_with_key = MagicMock(return_value = 'decrypt_with_key_output')
        patch(
            'kaurna.decrypt_with_key',
            mock_decrypt_with_key
            ).start()

        mock_encrypt_with_key = MagicMock(return_value = 'encrypt_with_key_output')
        patch(
            'kaurna.encrypt_with_key',
            mock_encrypt_with_key
            ).start()

        patch(
            'kaurna.time.time',
            Mock(return_value = 1234.567)
            ).start()

        # WHEN

        output = kaurna._reencrypt_item_and_save(item=item, region=self.region)

        # THEN

        assert_equals(
            item.mock_calls,
            [
                call.getitem('encrypted_secret'),
                call.getitem('encrypted_data_key'),
                call.getitem('encryption_context'),
                call.getitem('authorized_entities'),
                call.__setitem__('encryption_context', '{"Sterling Archer": "kaurna", "Cyril Figgis": "kaurna"}'),
                call.__setitem__('encrypted_secret', 'encrypt_with_key_output'),
                call.__setitem__('encrypted_data_key', 'ZGF0YV9rZXlfY2lwaGVydGV4dA==\n'),
                call.__setitem__('last_data_key_rotation', 1234),
                call.save()
                ]
            )

        assert_equals(
            item,
            output
            )

    def test_GIVEN_secret_name_but_not_secret_version_provided_WHEN_update_secrets_called_THEN_proper_secrets_updated(self):
        # GIVEN
        secret_name = 'password'
        secret_version = None
        authorized_entities = ['Sterling Archer','Cyril Figgis']

        item1 = {'secret_name':secret_name, 'secret_version':1, 'authorized_entities':json.dumps(['Mallory Archer'])}
        expected_item1 = {'secret_name':secret_name, 'secret_version':1, 'authorized_entities':json.dumps(['Sterling Archer','Cyril Figgis'])}
        item2 = {'secret_name':secret_name, 'secret':2, 'authorized_entities':json.dumps(['Algernop Krieger'])}
        expected_item2 = {'secret_name':secret_name, 'secret':2, 'authorized_entities':json.dumps(['Sterling Archer','Cyril Figgis'])}
        mock_load_all_entries = MagicMock(return_value = [item1, item2])
        patch(
            'kaurna.load_all_entries',
            mock_load_all_entries
            ).start()

        mock_reencrypt_item_and_save = MagicMock()
        patch(
            'kaurna._reencrypt_item_and_save',
            mock_reencrypt_item_and_save
            ).start()

        # WHEN
        update_secrets(secret_name=secret_name, secret_version=secret_version, region=self.region, authorized_entities=authorized_entities)

        # THEN
        assert_equals(
            mock_load_all_entries.call_args_list,
            [call(secret_name=secret_name, secret_version=secret_version, region=self.region)]
            )
        assert_equals(
            mock_reencrypt_item_and_save.call_args_list,
            [
                call(item=expected_item1, region=self.region),
                call(item=expected_item2, region=self.region)
                ]
            )

    def test_GIVEN_secret_name_and_secret_version_provided_WHEN_update_secrets_called_THEN_proper_secrets_updated(self):
        # GIVEN
        secret_name = 'password'
        secret_version = 2
        authorized_entities = ['Sterling Archer','Cyril Figgis']

        item = {'secret_name':secret_name, 'secret_version':2, 'authorized_entities':json.dumps(['Mallory Archer'])}
        expected_item = {'secret_name':secret_name, 'secret_version':2, 'authorized_entities':json.dumps(['Sterling Archer','Cyril Figgis'])}
        mock_load_all_entries = MagicMock(return_value = [item])
        patch(
            'kaurna.load_all_entries',
            mock_load_all_entries
            ).start()

        mock_reencrypt_item_and_save = MagicMock()
        patch(
            'kaurna._reencrypt_item_and_save',
            mock_reencrypt_item_and_save
            ).start()

        # WHEN
        update_secrets(secret_name=secret_name, secret_version=secret_version, region=self.region, authorized_entities=authorized_entities)

        # THEN
        assert_equals(
            mock_load_all_entries.call_args_list,
            [call(secret_name=secret_name, secret_version=secret_version, region=self.region)]
            )
        assert_equals(
            mock_reencrypt_item_and_save.call_args_list,
            [
                call(item=expected_item, region=self.region)
                ]
            )

    @raises(Exception)
    def test_GIVEN_provided_secret_name_is_None_WHEN_erase_secret_called_THEN_error_thrown(self):
        # GIVEN
        secret_name = None
        secret_version = None

        # WHEN
        erase_secret(secret_name=secret_name, secret_version=secret_version)

        # THEN
        # Exception should get thrown and we should never get here

    def test_GIVEN_secret_name_but_not_secret_version_provided_WHEN_erase_secret_called_THEN_proper_secret_erased(self):
        # GIVEN
        secret_name = 'password'
        secret_version = None

        item1 = MagicMock()
        item2 = MagicMock()
        item3 = MagicMock()
        mock_load_all_entries = MagicMock(return_value = [item1, item2, item3])
        patch(
            'kaurna.load_all_entries',
            mock_load_all_entries
            ).start()

        # WHEN
        erase_secret(secret_name=secret_name, secret_version=secret_version, region=self.region)

        # THEN
        assert_equals(
            mock_load_all_entries.call_args_list,
            [call(secret_name=secret_name, secret_version=secret_version, region=self.region)]
            )
        assert_equals(
            item1.delete.call_args_list,
            [
                call()
                ]
            )
        assert_equals(
            item2.delete.call_args_list,
            [
                call()
                ]
            )
        assert_equals(
            item3.delete.call_args_list,
            [
                call()
                ]
            )

    def test_GIVEN_secret_name_and_secret_version_provided_WHEN_erase_secret_called_THEN_proper_secret_erased(self):
        # GIVEN
        secret_name = 'password'
        secret_version = 2

        item = MagicMock()
        mock_load_all_entries = MagicMock(return_value = [item])
        patch(
            'kaurna.load_all_entries',
            mock_load_all_entries
            ).start()

        # WHEN
        erase_secret(secret_name=secret_name, secret_version=secret_version, region=self.region)

        # THEN
        assert_equals(
            mock_load_all_entries.call_args_list,
            [call(secret_name=secret_name, secret_version=secret_version, region=self.region)]
            )
        assert_equals(
            item.delete.call_args_list,
            [
                call()
                ]
            )

    def test_GIVEN_seriously_is_False_WHEN_erase_all_the_things_called_THEN_nothing_happens(self):
        # GIVEN
        mock_table = MagicMock()
        mock_get_table = MagicMock(return_value=mock_table)
        patch('kaurna.get_kaurna_table', mock_get_table).start()

        # WHEN
        erase_all_the_things(seriously=False, region=self.region)

        # THEN
        assert_equals(
            mock_get_table.call_args_list,
            []
            )
        assert_equals(
            mock_table.delete.call_args_list,
            []
            )

    def test_GIVEN_seriously_is_True_WHEN_erase_all_the_things_called_THEN_kaurna_table_deleted(self):
        # GIVEN
        mock_table = MagicMock()
        mock_get_table = MagicMock(return_value=mock_table)
        patch('kaurna.get_kaurna_table', mock_get_table).start()

        # WHEN
        erase_all_the_things(seriously=True, region=self.region)

        # THEN
        assert_equals(
            mock_get_table.call_args_list,
            [call(region=self.region)]
            )
        assert_equals(
            mock_table.delete.call_args_list,
            [call()]
            )

    def test_GIVEN_secret_name_but_not_secret_version_provided_WHEN_deprecate_secrets_called_THEN_proper_secrets_deprecated(self):
        # GIVEN
        secret_name = 'password'
        secret_version = None

        item1 = MagicMock()
        item2 = MagicMock()

        mock_load_all_entries = MagicMock(return_value = [item1, item2])
        patch(
            'kaurna.load_all_entries',
            mock_load_all_entries
            ).start()

        # WHEN
        deprecate_secrets(secret_name=secret_name, secret_version=secret_version, region=self.region)

        # THEN
        assert_equals(
            mock_load_all_entries.call_args_list,
            [call(secret_name=secret_name, secret_version=secret_version, region=self.region)]
            )
        assert_equals(
            item1.mock_calls,
            [call.__setitem__('deprecated', True), call.save()]
            )
        assert_equals(
            item2.mock_calls,
            [call.__setitem__('deprecated', True), call.save()]
            )

    def test_GIVEN_secret_name_and_secret_version_provided_WHEN_deprecate_secrets_called_THEN_proper_secrets_deprecated(self):
        # GIVEN
        secret_name = 'password'
        secret_version = 2

        item = MagicMock()

        mock_load_all_entries = MagicMock(return_value = [item])
        patch(
            'kaurna.load_all_entries',
            mock_load_all_entries
            ).start()

        # WHEN
        deprecate_secrets(secret_name=secret_name, secret_version=secret_version, region=self.region)

        # THEN
        assert_equals(
            mock_load_all_entries.call_args_list,
            [call(secret_name=secret_name, secret_version=secret_version, region=self.region)]
            )
        assert_equals(
            item.mock_calls,
            [call.__setitem__('deprecated', True), call.save()]
            )

    def test_GIVEN_secret_name_but_not_secret_version_provided_WHEN_activate_secrets_called_THEN_proper_secrets_activated(self):
        # GIVEN
        secret_name = 'password'
        secret_version = None

        item1 = MagicMock()
        item2 = MagicMock()

        mock_load_all_entries = MagicMock(return_value = [item1, item2])
        patch(
            'kaurna.load_all_entries',
            mock_load_all_entries
            ).start()

        # WHEN
        activate_secrets(secret_name=secret_name, secret_version=secret_version, region=self.region)

        # THEN
        assert_equals(
            mock_load_all_entries.call_args_list,
            [call(secret_name=secret_name, secret_version=secret_version, region=self.region)]
            )
        assert_equals(
            item1.mock_calls,
            [call.__setitem__('deprecated', False), call.save()]
            )
        assert_equals(
            item2.mock_calls,
            [call.__setitem__('deprecated', False), call.save()]
            )

    def test_GIVEN_secret_name_and_secret_version_provided_WHEN_activate_secrets_called_THEN_proper_secrets_activated(self):
        # GIVEN
        secret_name = 'password'
        secret_version = 2

        item = MagicMock()

        mock_load_all_entries = MagicMock(return_value = [item])
        patch(
            'kaurna.load_all_entries',
            mock_load_all_entries
            ).start()

        # WHEN
        activate_secrets(secret_name=secret_name, secret_version=secret_version, region=self.region)

        # THEN
        assert_equals(
            mock_load_all_entries.call_args_list,
            [call(secret_name=secret_name, secret_version=secret_version, region=self.region)]
            )
        assert_equals(
            item.mock_calls,
            [call.__setitem__('deprecated', False), call.save()]
            )

    def test_GIVEN_neither_secret_name_nor_secret_version_provided_WHEN_describe_secrets_called_THEN_proper_descriptions_returned(self):
        # GIVEN
        secret_name = None
        secret_version = None

        item1 = {'secret_name': 'password', 'secret_version': 1, 'create_date': 1234, 'last_data_key_rotation': 2345, 'authorized_entities': '["Mallory Archer"]', 'deprecated': True}
        item2 = {'secret_name': 'password', 'secret_version': 2, 'create_date': 2300, 'last_data_key_rotation': 2300, 'authorized_entities': '["Sterling Archer", "Cyril Figgis"]', 'deprecated': False}
        item3 = {'secret_name': 'github_pem', 'secret_version': 1, 'create_date': 0001, 'last_data_key_rotation': 0003, 'authorized_entities': '["Algernop Krieger"]', 'deprecated': True}
        item4 = {'secret_name': 'github_pem', 'secret_version': 3, 'create_date': 0002, 'last_data_key_rotation': 0004, 'authorized_entities': '["Algernop Krieger"]', 'deprecated': True}
        item5 = {'secret_name': 'github_pem', 'secret_version': 4, 'create_date': 0003, 'last_data_key_rotation': 0005, 'authorized_entities': '["Algernop Krieger"]', 'deprecated': False}

        patch(
            'kaurna.load_all_entries',
            Mock(
                return_value = [
                    item1,
                    item2,
                    item3,
                    item4,
                    item5
                    ]
                )
            ).start()

        expected_descriptions = {
            'password':
                {
                1:{
                    'create_date': 1234,
                    'last_data_key_rotation': 2345,
                    'authorized_entities': ['Mallory Archer'],
                    'deprecated': True
                    },
                2:{
                    'create_date': 2300,
                    'last_data_key_rotation': 2300,
                    'authorized_entities': ['Sterling Archer', 'Cyril Figgis'],
                    'deprecated': False
                    }
                },
            'github_pem':
                {
                1:{
                    'create_date': 0001,
                    'last_data_key_rotation': 0003,
                    'authorized_entities': ['Algernop Krieger'],
                    'deprecated': True
                    },
                3:{
                    'create_date': 0002,
                    'last_data_key_rotation': 0004,
                    'authorized_entities': ['Algernop Krieger'],
                    'deprecated': True
                    },
                4:{
                    'create_date': 0003,
                    'last_data_key_rotation': 0005,
                    'authorized_entities': ['Algernop Krieger'],
                    'deprecated': False
                    },
                }
            }

        # WHEN
        actual_descriptions = describe_secrets(secret_name=secret_name, secret_version=secret_version, region=self.region)

        # THEN
        assert_equals(
            expected_descriptions,
            actual_descriptions
            )

    def test_GIVEN_secret_name_but_not_secret_version_provided_WHEN_describe_secrets_called_THEN_proper_descriptions_returned(self):
        # GIVEN
        secret_name = 'password'
        secret_version = None

        item1 = {'secret_name': 'password', 'secret_version': 1, 'create_date': 1234, 'last_data_key_rotation': 2345, 'authorized_entities': '["Mallory Archer"]', 'deprecated': True}
        item2 = {'secret_name': 'password', 'secret_version': 2, 'create_date': 2300, 'last_data_key_rotation': 2300, 'authorized_entities': '["Sterling Archer", "Cyril Figgis"]', 'deprecated': False}

        patch(
            'kaurna.load_all_entries',
            Mock(
                return_value = [
                    item1,
                    item2
                    ]
                )
            ).start()

        expected_descriptions = {
            'password':
                {
                1:{
                    'create_date': 1234,
                    'last_data_key_rotation': 2345,
                    'authorized_entities': ['Mallory Archer'],
                    'deprecated': True
                    },
                2:{
                    'create_date': 2300,
                    'last_data_key_rotation': 2300,
                    'authorized_entities': ['Sterling Archer', 'Cyril Figgis'],
                    'deprecated': False
                    }
                }
            }

        # WHEN
        actual_descriptions = describe_secrets(secret_name=secret_name, secret_version=secret_version, region=self.region)

        # THEN
        assert_equals(
            expected_descriptions,
            actual_descriptions
            )

    def test_GIVEN_secret_name_and_secret_version_provided_WHEN_describe_secrets_called_THEN_proper_descriptions_returned(self):
        # GIVEN
        secret_name = 'password'
        secret_version = 2

        item2 = {'secret_name': 'password', 'secret_version': 2, 'create_date': 2300, 'last_data_key_rotation': 2300, 'authorized_entities': '["Sterling Archer", "Cyril Figgis"]', 'deprecated': False}

        patch(
            'kaurna.load_all_entries',
            Mock(
                return_value = [
                    item2
                    ]
                )
            ).start()

        expected_descriptions = {
            'password':
                {
                2:{
                    'create_date': 2300,
                    'last_data_key_rotation': 2300,
                    'authorized_entities': ['Sterling Archer', 'Cyril Figgis'],
                    'deprecated': False
                    }
                }
            }

        # WHEN
        actual_descriptions = describe_secrets(secret_name=secret_name, secret_version=secret_version, region=self.region)

        # THEN
        assert_equals(
            expected_descriptions,
            actual_descriptions
            )

    @raises(Exception)
    def test_GIVEN_provided_secret_name_is_None_WHEN_get_secret_called_THEN_error_thrown(self):
        # GIVEN
        secret_name = None
        secret_version = None

        # WHEN
        get_secret(secret_name=secret_name, secret_version=secret_version)

        # THEN
        # Exception should get thrown and we should never get here

    @raises(Exception)
    def test_GIVEN_secret_not_found_WHEN_get_secret_called_THEN_error_thrown(self):
        # GIVEN
        secret_name = 'password'
        secret_version = 3

        patch(
            'kaurna.load_all_entries',
            Mock(
                return_value = []
                )
            ).start()

        # WHEN
        get_secret(secret_name=secret_name, secret_version=secret_version)

        # THEN
        # Exception should get thrown and we should never get here

    @raises(Exception)
    def test_GIVEN_all_secret_versions_are_deprecated_WHEN_get_secret_called_THEN_error_thrown(self):
        # GIVEN
        secret_name = 'password'
        secret_version = None

        patch(
            'kaurna.load_all_entries',
            Mock(
                return_value = [
                    {'secret_name':'password','deprecated':True,'secret_version':1},
                    {'secret_name':'password','deprecated':True,'secret_version':2},
                    {'secret_name':'password','deprecated':True,'secret_version':3}
                    ]
                )
            ).start()

        # WHEN
        get_secret(secret_name=secret_name, secret_version=secret_version)

        # THEN
        # Exception should get thrown and we should never get here

    def test_GIVEN_secret_name_but_not_secret_version_provided_WHEN_get_secret_called_THEN_proper_secret_returned(self):
        self.fail()

    def test_GIVEN_secret_name_and_secret_version_provided_WHEN_get_secret_called_THEN_proper_secret_returned(self):
        self.fail()

    def test_GIVEN_valid_item_provided_WHEN__decrypt_item_called_THEN_proper_secret_returned(self):
        # GIVEN
        item = {
            'encrypted_secret': '<encrypted_secret>',
            'encrypted_data_key': '<encrypted_data_key>',
            'encryption_context': '{"Algernop Krieger": "kaurna"}'
            }
        
        expected_secret = '<decrypted_secret>'
        mock_decrypt_with_key = MagicMock(return_value = expected_secret)
        mock_decrypt_with_kms = MagicMock(return_value = {'Plaintext': '<decrypted_data_key>'})

        patch(
            'kaurna.decrypt_with_key',
            mock_decrypt_with_key
            ).start()

        patch(
            'kaurna.decrypt_with_kms',
            mock_decrypt_with_kms
            ).start()


        # WHEN
        actual_secret = kaurna._decrypt_item(item=item, region=self.region)

        # THEN
        assert_equals(
            expected_secret,
            actual_secret
            )

        assert_equals(
            mock_decrypt_with_key.call_args_list,
            [call('<encrypted_secret>', '<decrypted_data_key>')]
            )

        assert_equals(
            mock_decrypt_with_kms.call_args_list,
            [call('<encrypted_data_key>', {'Algernop Krieger':'kaurna'}, region=self.region)]
            )

    def test_GIVEN_iv_provided_WHEN_encrypt_with_key_called_THEN_plaintext_properly_encrypted(self):
        # GIVEN
        iv = base64.b64decode('kYSYMMqlQaVoUlXwmKUNLQ==')
        key = base64.b64decode('E/knR0ElllVyrTt3FkrTvI4mwvLdoCTR6mf2KtkAAXg=')
        plaintext = 'This is a test message.'
        expected_ciphertext = 'kYSYMMqlQaVoUlXwmKUNLXSY4J8XzrGgkV2iU1DSgM3J+ebbf5ifZE6tRKNZ6X+9'

        # WHEN
        actual_ciphertext = encrypt_with_key(plaintext=plaintext, key=key, iv=iv)

        # THEN
        assert_equals(
            expected_ciphertext,
            actual_ciphertext
            )

    def test_GIVEN_iv_not_provided_WHEN_encrypt_with_key_called_THEN_plaintext_properly_encrypted(self):
        # GIVEN
        mock_random = MagicMock()
        mock_random.read.return_value = base64.b64decode('sPMIV8lM3nHPpSV7DrtD1Q==')
        patch(
            'kaurna.Random.new',
            Mock(return_value=mock_random)
            ).start()

        iv = None
        key = base64.b64decode('b638ba+zFUD8LGvnIOBXas1BWDEb90CwYBNbqYh9NeQ=')
        plaintext = 'This is a test message.'
        expected_ciphertext = 'sPMIV8lM3nHPpSV7DrtD1XDzeZU8uxaUt5eEeif4U8wfgfeBsHLZntMhNjW74LIW'

        # WHEN
        actual_ciphertext = encrypt_with_key(plaintext=plaintext, key=key, iv=iv)

        # THEN
        assert_equals(
            expected_ciphertext,
            actual_ciphertext
            )

    def test_WHEN_decrypt_with_key_called_THEN_plaintext_properly_decrypted(self):
        # GIVEN
        key = base64.b64decode('E/knR0ElllVyrTt3FkrTvI4mwvLdoCTR6mf2KtkAAXg=')
        ciphertext = 'kYSYMMqlQaVoUlXwmKUNLXSY4J8XzrGgkV2iU1DSgM3J+ebbf5ifZE6tRKNZ6X+9'
        expected_plaintext = 'This is a test message.'

        # WHEN
        actual_plaintext = decrypt_with_key(ciphertext=ciphertext, key=key)

        # THEN
        assert_equals(
            expected_plaintext,
            actual_plaintext
            )

    def test_WHEN_encrypt_with_kms_called_THEN_proper_kms_call_made(self):
        self.fail()

    def test_WHEN_decrypt_with_kms_called_THEN_proper_kms_call_made(self):
        self.fail()
