from app import celery
from redis import StrictRedis
import importlib
import settings


@celery.task
def credentials_retry():
    print(" in resend task")
    # needs to try all tasks in list on each scheduled retry beat
    task = ReTryTaskStore()
    for i in range(0, task.length):
        task.call_next_task()


def add_retry_task(module, name, data):
    task = ReTryTaskStore()
    task.set_task(module, name, data)


class ReTryTaskStore:

    def __init__(self, task_list="retrytasks", data_prefix="taskretry_", retry_name="retries"):
        self.task_list = task_list
        self.data_prefix = data_prefix
        self.count_name = retry_name
        self.storage = StrictRedis.from_url(settings.REDIS_URL)
        self.module_name = None
        self.function_name = None
        self._reference = None
        self._key = None

    @property
    def length(self):
        return self.storage.llen(self.task_list)

    def _make_refs(self):
        self._reference = '{}~{}'.format(self.module_name, self.function_name)
        self._make_key()

    def _make_key(self):
        self._key = '{}_{}'.format(self.data_prefix, self._reference)

    def set_task(self, module_name, function_name,  data):
        self.module_name = module_name
        self.function_name = function_name
        self._make_refs()
        if not data.get(self.count_name, False):
            data[self.count_name] = 1
        self.storage.hmset(self._key, data)
        self.storage.lpush(self.task_list, self._reference)

    def call_next_task(self):
        """Calls the retry function passing data saved.
        The function must return True or it will continue to retry
        Function should return True if it has failed when "retries" reaches a defined value in retry task

        :return:
        """
        self._key = None
        self._reference = self.storage.rpop(self.task_list).decode('utf-8')
        if self._reference:
            self._make_key()
            data = self.get_data()
            self.module_name, self.module_name = self._reference.split('~')
            module = importlib.import_module(self.module_name)
            func = getattr(module, self.module_name)
            self._make_refs()
            result = func(data)
            if result:
                self.delete()
            else:
                self.storage.lpush(self.task_list, self._reference)
            return True
        return False

    def get_data(self):
        self.storage.hincrby(self._key, self.count_name, 1)
        return self.storage.hmget(self._key)

    def delete(self):
        self.storage.delete(self._key)
