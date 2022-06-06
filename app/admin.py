import json

from flask_admin import Admin
from flask import Markup, url_for

from retry_tasks_lib.admin.views import (
    RetryTaskAdminBase,
    TaskTypeAdminBase,
    TaskTypeKeyAdminBase,
    TaskTypeKeyValueAdminBase,
)

from retry_tasks_lib.db.models import RetryTask, TaskType, TaskTypeKey, TaskTypeKeyValue
from app.db import db_session

from app.redis_retry import redis

admin = Admin(
    name="Midas Admin",
    template_mode="bootstrap3",
)


class RetryTaskAdmin(RetryTaskAdminBase):
    redis = redis

    column_formatters = {
        "params": lambda view, c, model, n: Markup("<p>%s</p>")
        % Markup(
            "".join(
                [
                    '<strong><a href="{0}">{1}</a></strong>: {2}</br>'.format(
                        url_for(
                            "task-type-key-values.details_view",
                            id=f"{value.retry_task_id},{value.task_type_key_id}",
                        ),
                        value.task_type_key.name,
                        value.value,
                    )
                    for value in sorted(model.task_type_key_values, key=lambda value: value.task_type_key.name)
                ]
            )
        ),
        "audit_data": lambda v, c, model, n: Markup("<pre>%s</pre>")
        % json.dumps(model.audit_data, indent=4, sort_keys=True),
    }


class TaskTypeAdmin(TaskTypeAdminBase):
    pass


class TaskTypeKeyAdmin(TaskTypeKeyAdminBase):
    pass


class TaskTypeKeyValueAdmin(TaskTypeKeyValueAdminBase):
    can_view_details = True


admin.add_view(RetryTaskAdmin(RetryTask, db_session, "RetryTask", endpoint="tasks"))
admin.add_view(TaskTypeAdmin(TaskType, db_session, "TaskType", endpoint="task-types"))
admin.add_view(TaskTypeKeyAdmin(TaskTypeKey, db_session, "TaskTypeKey", endpoint="task-type-keys"))
admin.add_view(
    TaskTypeKeyValueAdmin(TaskTypeKeyValue, db_session, "TaskTypeKeyValues", endpoint="task-type-key-values")
)
