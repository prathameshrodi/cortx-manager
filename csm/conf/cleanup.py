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

import aiohttp
from cortx.utils.conf_store.conf_store import Conf
from cortx.utils.kv_store.error import KvError
from cortx.utils.log import Log

from csm.common.errors import CSM_OPERATION_SUCESSFUL
from csm.common.payload import Yaml
from csm.conf.setup import CsmSetupError, Setup
from csm.conf.uds import UDSConfigGenerator
from csm.core.blogic import const
from csm.core.providers.providers import Response

class Cleanup(Setup):
    """
    Cleanup all the Files and Folders generated by csm.
    """

    def __init__(self):
        super(Cleanup, self).__init__()
        Log.info("Running Cleanup for CSM.")
        self._db = ""
        self._es_url = ""

    async def execute(self, command):
        try:
            Conf.load(const.CSM_GLOBAL_INDEX, const.CSM_SOURCE_CONF_URL)
            Conf.load(const.DATABASE_INDEX, f"yaml://{const.DATABASE_CONF}")
        except KvError as e:
            Log.error(f"Loading csm.conf to conf store failed {e}")
            raise CsmSetupError("Failed to Load CSM Configuration File.")
        self._log_cleanup()
        UDSConfigGenerator.delete()
        self.load_db()
        self.directory_cleanup()
        return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)

    def _log_cleanup(self):
        """
        Delete all logs
        """
        Log.info("Delete all logs")
        log_path = Conf.get(const.CSM_GLOBAL_INDEX, "Log>log_path")
        Setup._run_cmd("rm -rf " + log_path)

    def load_db(self):
        """
        Load Database Provider from database.yaml
        :return:
        """
        Log.info("Loading Database Provider.")
        conf = Yaml(const.DATABASE_CONF).load()
        es_db_details = conf.get("databases", {}).get("es_db")
        self._es_url = (f"http://{es_db_details['config']['host']}:"
                        f"{es_db_details['config']['port']}/")

    async def _db_cleanup(self):
        """
        :return:
        """
        for each_model in Conf.get(const.DATABASE_INDEX, "models"):
            if each_model.get("database", "") == "es_db":
                await self.erase_index(
                    each_model.get("config", {}).get("collection", ""))

    async def erase_index(self, index_name):
        """
        Clean up all the CSM Elasticsearch Data.
        :param index_name: Elasticsearch Index Name to be Deleted.
        :return:
        """
        Log.info(f"Attempting Deletion of Index {index_name}")
        async with aiohttp.ClientSession(headers={}) as session:
            async with session.request(method="delete",
                                       url=f"{self._es_url}{index_name}",
                                       ) as response:
                pass
        if response.status != 200:
            Log.error(f"Index {index_name} Could Not Be Deleted.")
            return
        Log.info(f"Index {index_name} Deleted.")

    def selective_cleanup(self, collection_details):
        """
        Cleanup all the CSM Consul Data.
        :param collection_details: Consul Collection Name to be Deleted.
        :return:
        """
        Log.info(f"Cleaning up Collection {collection_details}")

    def directory_cleanup(self):
        """
        Delete local Directories as Follows:
        /etc/csm
        /var/log/seagate/csm
        /var/log/seagate/support_bundle
        /tmp/csm
        /tmp/hotfix
        :return:
        """
        self.Config.delete()
        for each_directory in const.CLEANUP_DIRECTORIES:
            Log.info(f"Deleting Directory {each_directory}")
            Setup._run_cmd(f"rm -rf {each_directory}")