# -*- coding: utf-8 -*-

import conf


def get_openstack_list_paginator(page_size=conf.openstack.request_page_size):
    assert callable(page_size) is False, 'This is not a decorator'
    assert type(page_size) is int, 'page_size is not Int'

    def paginator(fn):
        def under_page(*args, **kwargs):
            # Process listing as a regular call due to limit or marker parameters were passed
            limit = kwargs.pop('limit', None)
            marker = kwargs.pop('marker', None)
            if limit or marker:
                res = fn(*args, limit=limit, marker=marker, **kwargs)
                for item in res:
                    yield item
                return
            # Process listing with a pagination
            last_item_id = None
            while True:
                items = fn(*args, limit=page_size, marker=last_item_id, **kwargs)
                if not items:
                    break
                for item in items:
                    if type(item) is dict:
                        last_item_id = item['id']
                    else:
                        last_item_id = item.id
                    yield item

        def paged_requester(*args, **kwargs):
            return [item for item in under_page(*args, **kwargs)]

        # return under_page
        return paged_requester
    return paginator
