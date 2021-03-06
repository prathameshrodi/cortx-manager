# CORTX-CSM: CORTX Management web and CLI interface.
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.

from csm.core.blogic import const
from cortx.utils.cli_framework.command_factory import CommandFactory
from argparse import ArgumentError
import unittest
import json
import os
import random
import string
from csm.test.common import Const

password = "".join(random.sample(string.ascii_letters, 12))

permissions = {
"s3iamusers": {"list": True, "delete": True, "create": True }
}
accounts_command = CommandFactory.get_command(
    ["s3iamuser", 'create', "csm_user", "-passwd", password], permissions)
t = unittest.TestCase()
file_path = Const.MOCK_PATH

with open(file_path + "s3_commands_output.json") as fp:
    EXPECTED_OUTPUT = json.loads(fp.read())

def test_1(*args):
    expected_output = 's3iamuser'
    actual_output = accounts_command.name
    t.assertEqual(actual_output, expected_output)

def test_2(*args):
    
    expected_output = EXPECTED_OUTPUT.get("iamuser", {}).get("create_test_2", {})
    expected_output.update({"password": password})
    actual_output = accounts_command.options
    t.assertDictEqual(actual_output, expected_output)

def test_3(*args):
    expected_output = 'post'
    actual_output = accounts_command.method
    t.assertEqual(actual_output, expected_output)
        
def init(args):
    pass    
    
test_list = [test_1, test_2, test_3]
