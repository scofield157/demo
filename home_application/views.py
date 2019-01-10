# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making 蓝鲸智云(BlueKing) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
"""
import datetime
import json

from blueking.component.shortcuts import get_client_by_request
from common.mymako import render_mako_context, render_json
from home_application.celery_tasks import async_task
from home_application.models import executeHistory


def home(request):
    """
    首页
    """
    client = get_client_by_request(request)
    biz_param = {
        "fields": [
            "bk_biz_id",
            "bk_biz_name"
        ]
    }
    biz_result = client.cc.search_business(biz_param)
    if biz_result and biz_result.get('result'):
        return render_mako_context(request, '/home_application/index.html',
                                   {'bizList': biz_result.get('data').get('info')})


def history(request):
    """
    任务历史界面
    """
    client = get_client_by_request(request)
    biz_param = {
        "fields": [
            "bk_biz_id",
            "bk_biz_name"
        ]
    }
    biz_result = client.cc.search_business(biz_param)
    if biz_result and biz_result.get('result'):
        return render_mako_context(request, '/home_application/history.html',
                                   {'bizList': biz_result.get('data').get('info')})


def dev_guide(request):
    """
    开发指引
    """
    return render_mako_context(request, '/home_application/dev_guide.html')


def contactus(request):
    """
    联系我们
    """
    return render_mako_context(request, '/home_application/contact.html')


def test(request):
    """
    测试接口
    :param request:
    :return:
    """
    username = request.user.username
    now_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return render_json(
        {
            "result": True,
            "message": "success",
            "data": {
                'user': username,
                'time': str(now_time)
            }
        })


def search_set(request):
    """
    查询集群
    :param request:
    :return:
    """
    client = get_client_by_request(request)
    biz_id = request.GET['bizID']
    if not biz_id:
        return None
    set_param = {
        "bk_biz_id": biz_id,
        "fields": [
            "bk_set_id",
            "bk_set_name"
        ]
    }
    set_result = client.cc.search_set(set_param)
    if set_result and set_result.get('result'):
        return render_mako_context(request, '/home_application/setSelect.html',
                                   {'setList': set_result.get('data').get('info')})


def search_host(request):
    """
    查询机器
    :param request:
    :return:
    """
    client = get_client_by_request(request)
    biz_id = request.GET['bizID']
    set_id = request.GET['setID']
    if not biz_id:
        return None
    if not set_id:
        return None
    host_param = {
        "bk_biz_id": biz_id,
        "condition": [
            {
                "bk_obj_id": "set",
                "fields": [],
                "condition": [
                    {
                        "field": "bk_set_id",
                        "operator": "$eq",
                        "value": int(set_id)
                    }
                ]
            }
        ]
    }
    display_list = []
    host_result = client.cc.search_host(host_param)
    if host_result and host_result.get('result'):
        for host in host_result.get('data').get('info'):
            temp_dict = {
                'hostName': host.get('host').get('bk_host_name'),
                'ip': host.get('host').get('bk_host_innerip'),
                'cloudID': host.get('host').get('bk_cloud_id')[0].get('bk_inst_id'),
                'cloudName': host.get('host').get('bk_cloud_id')[0].get('bk_inst_name'),
                'osName': host.get('host').get('bk_os_name')
            }
            display_list.append(temp_dict)
    return render_mako_context(request,
                               '/home_application/hostTable.html', {'hostList': display_list})


def execute_job(request):
    """
    执行做业务
    :param request:
    :return:
    """
    username = request.user.username
    req = json.loads(request.body)
    host_list = req.get('hosts')
    biz_id = req.get('bizID')
    job_id = req.get('jobID')
    if host_list is not list and len(host_list) <= 0:
        return render_json({
            'result': False,
            'message': u"没有选择机器"
        })
    if not biz_id:
        return render_json(
            {
                "result": False,
                "message": u"没有选择业务",
            })
    if not job_id:
        return render_json(
            {
                "result": False,
                "message": u"没有选择作业",
            })
    job_detail_param = {
        "bk_biz_id": biz_id,
        "bk_job_id": job_id
    }
    client = get_client_by_request(request)
    job_detail_result = client.job.get_job_detail(job_detail_param)
    if job_detail_result and job_detail_result.get('result'):
        steps = job_detail_result.get('data').get('steps')
        steps[0]['ip_list'] = host_list
        execute_job_param = {
            "bk_biz_id": biz_id,
            "bk_job_id": job_id,
            "steps": steps
        }
        execute_job_result = client.job.execute_job(execute_job_param)
        if execute_job_result and execute_job_result.get("result"):
            job_instance_id = execute_job_result.get('data').get('job_instance_id')
            async_task.apply_async(args=(job_instance_id, biz_id, username), kwargs={})
            return render_json(
                {
                    "result": True,
                    "message": u"任务开始执行",
                })


def search_history(request):
    """
    查询作业历史
    :param request:
    :return:
    """
    biz_id = request.GET['bizID']
    if biz_id == 'all':
        history_result = executeHistory.objects.all()
    else:
        history_result = executeHistory.objects.filter(bizID=biz_id)
    display_list = []
    for history in history_result:
        temp = {
            "createUser": history.createUser,
            "log": history.log,
            "bizName": history.bizName,
            "ipList": history.ipList,
            "actionTime": str(history.actionTime),
            "jobID": history.jobID
        }
        if history.jobStatus == 3:
            temp["jobStatus"] = 'success'
        else:
            temp["jobStatus"] = 'failed'
        display_list.append(temp)
    return render_mako_context(request, '/home_application/historyTable.html',
                               {'historyList': display_list})
