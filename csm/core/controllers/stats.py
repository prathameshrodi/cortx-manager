#!/usr/bin/env python3

"""
 ****************************************************************************
 Filename:          stats.py
 Description:       Implementation of stats view

 Creation Date:     10/16/2019
 Author:            Naval Patel
                    Eduard Aleksandrov

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
from .view import CsmView
from csm.core.services.stats import StatsAppService

@CsmView._app_routes.view("/api/v1/stats/{panel}")
class StatsView(CsmView):
    def __init__(self, request):
        super(StatsView, self).__init__(request)
        self._service = self.request.app["stat_service"]
        self._service_dispatch = {
            "get": self._service.get
        }

    """
    GET REST implementation for Statistics request
    """
    async def get(self):
        """Calling Stats Get Method"""
        stats_id = self.request.rel_url.query.get("id", None)
        panel = self.request.match_info["panel"]
        from_t = self.request.rel_url.query.get("from", None)
        to_t = self.request.rel_url.query.get("to", None)
        metric_list = self.request.rel_url.query.getall("metric_list", [])
        interval = self.request.rel_url.query.get("interval", None)
        output_format = self.request.rel_url.query.get("output_format", "gui")
        query = self.request.rel_url.query.get("query", "")

        return await self._service.get(stats_id, panel, from_t, to_t, metric_list,
                                        interval, output_format, query)