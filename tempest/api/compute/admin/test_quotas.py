# Copyright 2012 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from oslo_log import log as logging
from testtools import matchers

from tempest.api.compute import base
from tempest.common import tempest_fixtures as fixtures
from tempest.common.utils import data_utils
from tempest.lib import decorators

LOG = logging.getLogger(__name__)


class QuotasAdminTestJSON(base.BaseV2ComputeAdminTest):
    force_tenant_isolation = True

    def setUp(self):
        # NOTE(mriedem): Avoid conflicts with os-quota-class-sets tests.
        self.useFixture(fixtures.LockFixture('compute_quotas'))
        super(QuotasAdminTestJSON, self).setUp()

    @classmethod
    def setup_clients(cls):
        super(QuotasAdminTestJSON, cls).setup_clients()
        cls.adm_client = cls.os_adm.quotas_client

    @classmethod
    def resource_setup(cls):
        super(QuotasAdminTestJSON, cls).resource_setup()

        # NOTE(afazekas): these test cases should always create and use a new
        # tenant most of them should be skipped if we can't do that
        cls.demo_tenant_id = cls.quotas_client.tenant_id

        cls.default_quota_set = set(('injected_file_content_bytes',
                                     'metadata_items', 'injected_files',
                                     'ram', 'floating_ips',
                                     'fixed_ips', 'key_pairs',
                                     'injected_file_path_bytes',
                                     'instances', 'security_group_rules',
                                     'cores', 'security_groups'))

    @decorators.idempotent_id('3b0a7c8f-cf58-46b8-a60c-715a32a8ba7d')
    def test_get_default_quotas(self):
        # Admin can get the default resource quota set for a tenant
        expected_quota_set = self.default_quota_set | set(['id'])
        quota_set = self.adm_client.show_default_quota_set(
            self.demo_tenant_id)['quota_set']
        self.assertEqual(quota_set['id'], self.demo_tenant_id)
        for quota in expected_quota_set:
            self.assertIn(quota, quota_set.keys())

    @decorators.idempotent_id('55fbe2bf-21a9-435b-bbd2-4162b0ed799a')
    def test_update_all_quota_resources_for_tenant(self):
        # Admin can update all the resource quota limits for a tenant
        default_quota_set = self.adm_client.show_default_quota_set(
            self.demo_tenant_id)['quota_set']
        new_quota_set = {'injected_file_content_bytes': 20480,
                         'metadata_items': 256, 'injected_files': 10,
                         'ram': 10240, 'floating_ips': 20, 'fixed_ips': 10,
                         'key_pairs': 200, 'injected_file_path_bytes': 512,
                         'instances': 20, 'security_group_rules': 20,
                         'cores': 2, 'security_groups': 20,
                         'server_groups': 20, 'server_group_members': 20}
        # Update limits for all quota resources
        quota_set = self.adm_client.update_quota_set(
            self.demo_tenant_id,
            force=True,
            **new_quota_set)['quota_set']

        default_quota_set.pop('id')
        self.addCleanup(self.adm_client.update_quota_set,
                        self.demo_tenant_id, **default_quota_set)
        for quota in new_quota_set:
            self.assertIn(quota, quota_set.keys())

    # TODO(afazekas): merge these test cases
    @decorators.idempotent_id('ce9e0815-8091-4abd-8345-7fe5b85faa1d')
    def test_get_updated_quotas(self):
        # Verify that GET shows the updated quota set of project
        project_name = data_utils.rand_name('cpu_quota_project')
        project_desc = project_name + '-desc'
        project = self.identity_utils.create_project(name=project_name,
                                                     description=project_desc)
        project_id = project['id']
        self.addCleanup(self.identity_utils.delete_project, project_id)

        self.adm_client.update_quota_set(project_id, ram='5120')
        quota_set = self.adm_client.show_quota_set(project_id)['quota_set']
        self.assertEqual(5120, quota_set['ram'])

        # Verify that GET shows the updated quota set of user
        user_name = data_utils.rand_name('cpu_quota_user')
        password = data_utils.rand_password()
        email = user_name + '@testmail.tm'
        user = self.identity_utils.create_user(username=user_name,
                                               password=password,
                                               project=project,
                                               email=email)
        user_id = user['id']
        self.addCleanup(self.identity_utils.delete_user, user_id)

        self.adm_client.update_quota_set(project_id,
                                         user_id=user_id,
                                         ram='2048')
        quota_set = self.adm_client.show_quota_set(
            project_id, user_id=user_id)['quota_set']
        self.assertEqual(2048, quota_set['ram'])

    @decorators.idempotent_id('389d04f0-3a41-405f-9317-e5f86e3c44f0')
    def test_delete_quota(self):
        # Admin can delete the resource quota set for a project
        project_name = data_utils.rand_name('ram_quota_project')
        project_desc = project_name + '-desc'
        project = self.identity_utils.create_project(name=project_name,
                                                     description=project_desc)
        project_id = project['id']
        self.addCleanup(self.identity_utils.delete_project, project_id)
        quota_set_default = (self.adm_client.show_quota_set(project_id)
                             ['quota_set'])
        ram_default = quota_set_default['ram']

        self.adm_client.update_quota_set(project_id, ram='5120')

        self.adm_client.delete_quota_set(project_id)

        quota_set_new = self.adm_client.show_quota_set(project_id)['quota_set']
        self.assertEqual(ram_default, quota_set_new['ram'])


class QuotaClassesAdminTestJSON(base.BaseV2ComputeAdminTest):
    """Tests the os-quota-class-sets API to update default quotas."""

    def setUp(self):
        # All test cases in this class need to externally lock on doing
        # anything with default quota values.
        self.useFixture(fixtures.LockFixture('compute_quotas'))
        super(QuotaClassesAdminTestJSON, self).setUp()

    @classmethod
    def resource_setup(cls):
        super(QuotaClassesAdminTestJSON, cls).resource_setup()
        cls.adm_client = cls.os_adm.quota_classes_client

    def _restore_default_quotas(self, original_defaults):
        LOG.debug("restoring quota class defaults")
        self.adm_client.update_quota_class_set(
            'default', **original_defaults)['quota_class_set']

    # NOTE(sdague): this test is problematic as it changes
    # global state, and possibly needs to be part of a set of
    # tests that get run all by themselves at the end under a
    # 'danger' flag.
    @decorators.idempotent_id('7932ab0f-5136-4075-b201-c0e2338df51a')
    def test_update_default_quotas(self):
        LOG.debug("get the current 'default' quota class values")
        body = (self.adm_client.show_quota_class_set('default')
                ['quota_class_set'])
        self.assertIn('id', body)
        self.assertEqual('default', body.pop('id'))
        # restore the defaults when the test is done
        self.addCleanup(self._restore_default_quotas, body.copy())
        # increment all of the values for updating the default quota class
        for quota, default in body.items():
            # NOTE(sdague): we need to increment a lot, otherwise
            # there is a real chance that we go from -1 (unlimited)
            # to a very small number which causes issues.
            body[quota] = default + 100
        LOG.debug("update limits for the default quota class set")
        update_body = self.adm_client.update_quota_class_set(
            'default', **body)['quota_class_set']
        LOG.debug("assert that the response has all of the changed values")
        self.assertThat(update_body.items(),
                        matchers.ContainsAll(body.items()))
