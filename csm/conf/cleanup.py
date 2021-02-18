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

from cortx.utils.conf_store.conf_store import Conf
from cortx.utils.data.db.consul_db.storage import CONSUL_ROOT
from cortx.utils.kv_store.error import KvError
from cortx.utils.log import Log

from csm.common.errors import CSM_OPERATION_SUCESSFUL
from csm.common.payload import Yaml
from csm.conf.setup import CsmSetupError, Setup
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
        self._es_db_url = ""
        self._consul_db_url = ""


    async def execute(self, command):
        try:
            Conf.load(const.CONSUMER_INDEX,
                      command.options.get(const.CONFIG_URL))
            Conf.load(const.CSM_GLOBAL_INDEX, const.CSM_SOURCE_CONF_URL)
            Conf.load(const.DATABASE_INDEX, f"yaml://{const.DATABASE_CONF}")
        except KvError as e:
            Log.error(f"Loading csm.conf to conf store failed {e}")
            raise CsmSetupError("Failed to Load CSM Configuration File.")
        await self._db_cleanup()
        Cleanup._log_cleanup()
        self.directory_cleanup()
        return Response(output=const.CSM_SETUP_PASS, rc=CSM_OPERATION_SUCESSFUL)

    @staticmethod
    def _log_cleanup():
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
        consul_details = conf.get("databases", {}).get("consul_db")
        self._es_db_url = (f"http://{es_db_details['config']['host']}:"
                           f"{es_db_details['config']['port']}/")
        self._consul_db_url = (f"http://{consul_details['config']['host']}:"
                               f"{consul_details['config']['port']}/v1/kv/{CONSUL_ROOT}")

    def fetch_es_data(self, collection, selective=False):
        """

        :param collection:
        :param selective:
        :return:
        """
        url = f"{self._es_db_url}{collection}"
        if not selective:
            return url, const.DELETE
        return f"{url}/_delete_by_query", const.POST

    def fetch_consul_data(self, collection, selective=False):
        """

        :param collection:
        :param selective:
        :return:
        """
        url = f"{self._consul_db_url}/{collection}"
        if not selective:
            return f"{url}/?recurse", const.DELETE
        return url, const.DELETE

    async def _db_cleanup(self):
        """
        Clean Data Base Collection As per Logic.
        :return:
        """
        self.load_db()
        is_selective = False
        selective_cleanup = Yaml(const.SELECTIVE_CLEANUP).load()
        for each_model in Conf.get(const.DATABASE_INDEX, "models"):
            config = each_model.get("config", {})
            if config.get("es_db"):
                collection = config.get('es_db', {}).get(
                    'collection')
                is_selective = collection in selective_cleanup["models"].keys()
                url, method = self.fetch_es_data(collection, is_selective)
            else:
                collection = config.get('consul_db', {}).get(
                    'collection')
                is_selective = collection in selective_cleanup["models"].keys()
                url, method = self.fetch_consul_data(collection, is_selective)
            if is_selective:
                return self.selective_cleanup(collection, url, method,
                                      selective_cleanup["models"][collection])
            return await self.erase_index(collection, url, method)

    async def erase_index(self, collection, url, method):
        """
        Clean up all the CSM Elasticsearch Data for provided Index.
        :param collection:
        :param url:
        :param method:
        :return:
        """
        Log.info(f"Attempting Deletion of Collection {collection}")
        text, headers, status = await self.request(url, method)
        if status != 200:
            Log.error(f"Index {collection} Could Not Be Deleted.")
            Log.error(f"Response --> {text}")
            Log.error(f"Status Code--> {status}")
            return
        Log.info(f"Index {collection} Deleted.")

    def fetch_conf_store_values(self, query_keys):
        """

        :param query_keys:
        :return:
        """
        query_data = dict()
        machine_id = self._get_machine_id()
        server_nodes = Conf.get(const.CONSUMER_INDEX, "cluster>server_nodes")
        minion_id = server_nodes.get(machine_id)
        substitutes = {
            "machine_id": machine_id,
            "minion_id": minion_id
        }
        for each_key in query_keys.keys():
            query_data[each_key] = Conf.get(const.CONSUMER_INDEX,
                                            query_keys[each_key].format(
                                                **substitutes), None)
        return query_data

    async def selective_cleanup(self, collection, url, method, query_data):
        """
        Cleanup data by CSM  the Data.
        :param collection:
        :param url:
        :param method:
        :param query_data:
        :return:
        """
        Log.info(f"Cleaning up Collection {collection}")
        json = dict()
        query_keys = query_data.get("keys")
        conf_data = self.fetch_conf_store_values(query_keys)
        query = query_data.get("query", "")
        json = query.format(**conf_data).replace("<", "{").replace(">", "}")
        Log.info(f"Attempting Deletion of Collection {collection}")
        text, headers, status = await self.request(url, method, json=eval(json))
        if status != 200:
            Log.error(f"Index {collection} Could Not Be Deleted.")
            Log.error(f"Response --> {text}")
            Log.error(f"Status Code--> {status}")
            return
        Log.info(f"Index {collection} Deleted.")

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
