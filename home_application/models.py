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

from django.db import models


class executeHistory(models.Model):
    createUser = models.CharField(max_length=100, null=True)
    log = models.CharField(max_length=1000, null=True)
    bizID = models.IntegerField(null=True)
    bizName = models.CharField(max_length=100, null=True)
    ipList = models.CharField(max_length=500, null=True)
    jobStatus = models.IntegerField(null=True)
    actionTime = models.DateTimeField(null=True)
    jobID = models.IntegerField(null=True)

    def toDic(self):
        return dict([(attr, getattr(self, attr)) for attr in [f.name for f in self._meta.fields]])
