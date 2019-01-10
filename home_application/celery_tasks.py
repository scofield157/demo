# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making 蓝鲸智云(BlueKing) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.

celery 任务示例

本地启动celery命令: python  manage.py  celery  worker  --settings=settings
周期性任务还需要启动celery调度命令：python  manage.py  celerybeat --settings=settings
"""
import datetime
import json
import time

from celery import task, Celery, shared_task
from celery.schedules import crontab
from celery.task import periodic_task

import settings
from blueking.component.shortcuts import get_client_by_user
from common.log import logger
from home_application.models import executeHistory

app = Celery('tasks')

app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@shared_task
def async_task(job_instance_id, bk_biz_id, create_user):
    """
    定义一个 celery 异步任务
    """
    # logger.error(u"celery 定时任务执行成功，执行结果：{:0>2}:{:0>2}".format(x, y))
    # return x + y
    client = get_client_by_user(create_user)
    poll_job_result(job_instance_id, bk_biz_id, client, create_user)


def poll_job_result(task_inst_id, bk_biz_id, client, create_user, max_retries=30,
                    sleep_time=3):
    """
    轮询ijobs任务，返回任务执行的结果，和状态码
    """

    retries = 0
    while retries <= max_retries:
        logger.info(u'【%s】waiting for job finished（%s/%s）' % (task_inst_id, retries, max_retries))
        is_finished, is_ok = get_ijob_result(task_inst_id, bk_biz_id, client, create_user)

        # 等待执行完毕
        if not is_finished:
            retries += 1
            time.sleep(sleep_time)
            continue

        # 执行成功
        if is_ok:
            logger.info(u'【%s】job execute success' % task_inst_id)
            return True

        # 执行失败
        return False

    # 执行超时
    if retries > max_retries:
        return False


def get_ijob_result(task_instance_id, bk_biz_id, client, create_user):
    """
    查询ijobs任务实例，获取ijobs任务的业务ID、步骤详情以及当前状态
    """

    # 查询作业
    task_info = client.job.get_job_instance_status({'job_instance_id': task_instance_id,
                                                    "bk_biz_id": bk_biz_id
                                                    })
    is_ok, is_finished = False, task_info.get('data').get('is_finished')

    if is_finished:
        logger.info(u'【%s】job finished.' % task_instance_id)
        task_instance = task_info.get('data').get('job_instance', {})
        status = task_instance.get('status', 0)  # 作业状态, 2=run, 3=success, 4=fail
        is_ok = (status == 3)
        get_job_log(task_instance_id, bk_biz_id, client, create_user, status)

        # 获取所有任务的执行情况，用一个list来装
        # err_desc = err_log.get('logContent')

        # if is_finished and not is_ok:
        #     # err_desc = task_info['blocks'][0]['stepInstances'][0]['stepIpResult'][0]['resultTypeText']
        #     err_log = get_job_log(task_instance_id, bk_biz_id)
        #     # err_desc = err_log.get('logContent')

    return is_finished, is_ok


def get_job_log(task_instance_id, bk_biz_id, client, create_user, status):
    """
    查询作业日志，分析结果
    """
    data = client.job.get_job_instance_log({'job_instance_id': task_instance_id,
                                            "bk_biz_id": bk_biz_id
                                            })
    biz_param = {
        "fields": [
            "bk_biz_name"
        ],
        "condition": {
            "bk_biz_id": int(bk_biz_id)
        },
    }
    action_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    biz_name = client.cc.search_business(biz_param).get('data').get('info')[0].get('bk_biz_name')
    results = data.get('data')[0].get('step_results')
    ip_list = []
    log_list = []
    for result in results:
        for ip_content in result.get("ip_logs"):
            ip = ip_content.get("ip")
            log = ip_content.get('log_content')
            log = ip+"|"+log
            ip_list.append(ip)
            log_list.append(log)
    executeHistory.objects.create(
        createUser=create_user,
        log=json.dumps(log_list),
        ipList=json.dumps(ip_list),
        bizID=bk_biz_id,
        bizName=biz_name,
        jobStatus=status,
        actionTime=action_time,
        jobID=int(task_instance_id)
    )
