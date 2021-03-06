# Copyright 2014 Hewlett-Packard Development Company, L.P
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

from tempest.api.identity import base
from tempest.common.utils import data_utils
from tempest.lib import decorators


class ListProjectsTestJSON(base.BaseIdentityV3AdminTest):

    @classmethod
    def resource_setup(cls):
        super(ListProjectsTestJSON, cls).resource_setup()
        cls.project_ids = list()
        # Create a domain
        cls.domain = cls.create_domain()
        # Create project with domain
        cls.projects = list()
        cls.p1_name = data_utils.rand_name('project')
        cls.p1 = cls.projects_client.create_project(
            cls.p1_name, enabled=False,
            domain_id=cls.domain['id'])['project']
        cls.projects.append(cls.p1)
        cls.project_ids.append(cls.p1['id'])
        # Create default project
        p2_name = data_utils.rand_name('project')
        cls.p2 = cls.projects_client.create_project(p2_name)['project']
        cls.projects.append(cls.p2)
        cls.project_ids.append(cls.p2['id'])
        # Create a new project (p3) using p2 as parent project
        p3_name = data_utils.rand_name('project')
        cls.p3 = cls.projects_client.create_project(
            p3_name, parent_id=cls.p2['id'])['project']
        cls.projects.append(cls.p3)
        cls.project_ids.append(cls.p3['id'])

    @classmethod
    def resource_cleanup(cls):
        # Cleanup the projects created during setup in inverse order
        for project in reversed(cls.projects):
            cls.projects_client.delete_project(project['id'])
        # Cleanup the domain created during setup
        cls.domains_client.update_domain(cls.domain['id'], enabled=False)
        cls.domains_client.delete_domain(cls.domain['id'])
        super(ListProjectsTestJSON, cls).resource_cleanup()

    @decorators.idempotent_id('1d830662-22ad-427c-8c3e-4ec854b0af44')
    def test_list_projects(self):
        # List projects
        list_projects = self.projects_client.list_projects()['projects']

        for p in self.project_ids:
            show_project = self.projects_client.show_project(p)['project']
            self.assertIn(show_project, list_projects)

    @decorators.idempotent_id('fab13f3c-f6a6-4b9f-829b-d32fd44fdf10')
    def test_list_projects_with_domains(self):
        # List projects with domain
        self._list_projects_with_params(
            {'domain_id': self.domain['id']}, 'domain_id')

    @decorators.idempotent_id('0fe7a334-675a-4509-b00e-1c4b95d5dae8')
    def test_list_projects_with_enabled(self):
        # List the projects with enabled
        self._list_projects_with_params({'enabled': False}, 'enabled')

    @decorators.idempotent_id('fa178524-4e6d-4925-907c-7ab9f42c7e26')
    def test_list_projects_with_name(self):
        # List projects with name
        self._list_projects_with_params({'name': self.p1_name}, 'name')

    @decorators.idempotent_id('6edc66f5-2941-4a17-9526-4073311c1fac')
    def test_list_projects_with_parent(self):
        # List projects with parent
        params = {'parent_id': self.p3['parent_id']}
        fetched_projects = self.projects_client.list_projects(
            params)['projects']
        self.assertNotEmpty(fetched_projects)
        for project in fetched_projects:
            self.assertEqual(self.p3['parent_id'], project['parent_id'])

    def _list_projects_with_params(self, params, key):
        body = self.projects_client.list_projects(params)['projects']
        self.assertIn(self.p1[key], map(lambda x: x[key], body))
        self.assertNotIn(self.p2[key], map(lambda x: x[key], body))
