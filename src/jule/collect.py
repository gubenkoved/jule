#! /usr/bin/env python3

import argparse
import datetime
import json
import logging
import os.path
import sys
from typing import Dict, Tuple, List

import coloredlogs
import ldap
from ldap.controls.pagedresults import SimplePagedResultsControl
from ldap.ldapobject import LDAPObject

from jule.common import fully_qualified_class_name
from jule.plugin import LdapQuerySet, load_from_module
from jule.state import LdapStorageContainer, LdapSnapshotData, LdapSnapshotMetadata

LOGGER = logging.getLogger(__name__)


class LdapHelper:
    def __init__(self, client: LDAPObject):
        self.client: LDAPObject = client

    def fetch_paged(
            self,
            base_dn: str, scope: int, filter=None, attributes=None,
            page_size=1000,
            limit=100000) -> List[Tuple[str, Dict]]:

        LOGGER.info(
            'processing "%s" request with scope %d (filter=%s)...',
            base_dn, scope, filter)

        data = []
        page_number = 0
        page_control = SimplePagedResultsControl(criticality=True, size=page_size)

        while True:
            page_number += 1
            LOGGER.debug(
                'fetching page #%d (already retrieved: %d)...',
                page_number, len(data))

            msg_id = self.client.search_ext(
                base_dn, scope, filter, attributes, serverctrls=[page_control])
            _, page_data, _, response_ctrls = self.client.result3(msg_id)

            if not page_data:
                break

            page_response_ctrl = [
                control for control in response_ctrls
                if control.controlType == SimplePagedResultsControl.controlType
            ]

            data.extend(page_data)

            if not page_response_ctrl or not page_response_ctrl[0].cookie:
                break

            if len(data) > limit:
                LOGGER.warning('max limit of requested entries reached -- stop')
                break

            page_control.cookie = page_response_ctrl[0].cookie
        LOGGER.info('retrieved %d result entries', len(data))
        return data


def gen_filename(label):
    now = datetime.datetime.now()
    prefix = now.strftime('%Y%m%d-%H%M%S')
    return '%s_%s' % (prefix, label)


def extract(ldap_helper: LdapHelper, query_set: LdapQuerySet, plugin_name: str):
    all_entries = []

    for query in query_set.queries:
        entries = ldap_helper.fetch_paged(
            query.root_dn,
            scope=ldap.SCOPE_SUBTREE,
            filter=query.filter,
            attributes=query_set.attributes)
        all_entries.extend(entries)

    return LdapStorageContainer(
        data=LdapSnapshotData(all_entries),
        metadata=LdapSnapshotMetadata(
            entries_count=len(all_entries),
            parameters={
                'root_dns': [q.root_dn for q in query_set.queries],
                # 'scope': scope,
                # 'filter': filter,
                'attributes': query_set.attributes,
                'plugin_name': plugin_name,
            }
        )
    )


def load_config(path):
    LOGGER.info('loading config at %s...', path)
    with open(path, 'r') as f:
        data = json.load(f)
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('type', type=str, default='light', choices=['light', 'full'])
    parser.add_argument('--config-path', type=str, default='config.json', required=False)
    parser.add_argument('--data-dir', type=str, default='data', required=False)
    parser.add_argument('--log-path', type=str, default='collect.log', required=False)

    args = parser.parse_args()

    logging.basicConfig(
        filename=args.log_path,
        filemode='a',
        format='%(asctime)s.%(msecs)03d %(levelname)s [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        level=logging.DEBUG)

    # install colorful logging for all the loggers
    coloredlogs.install(level=logging.DEBUG)

    # TODO: store name of the plugin class inside the config
    config = load_config(
        path=args.config_path
    )

    endpoint = config['endpoint']
    who = config['who']
    password = config['password']

    client = ldap.initialize(endpoint)
    client.set_option(ldap.OPT_NETWORK_TIMEOUT, 30.0)
    client.set_option(ldap.OPT_TIMEOUT, 30)

    LOGGER.debug('authenticate at %s...', endpoint)
    client.simple_bind_s(
        who=who,
        cred=password,
    )
    LOGGER.debug('authenticated')

    helper = LdapHelper(client)
    plugin = load_from_module('jule.plugin.sample')
    query_sets_by_label = {
        qs.label: qs for qs in plugin.ldap_query_sets
    }

    query_set_name = args.type

    if query_set_name not in query_sets_by_label:
        raise Exception('unknown type "%s" (known: %s)' % (
            args.type, list(query_sets_by_label)))

    query_set = query_sets_by_label[query_set_name]

    container = extract(helper, query_set, fully_qualified_class_name(type(plugin)))
    container.metadata.label = query_set_name
    filename = gen_filename('%s.jule' % query_set_name)

    path = os.path.join(args.data_dir, filename)
    with open(path, 'wb') as f:
        container.save(f)


if __name__ == '__main__':
    try:
        main()
    except Exception as err:
        LOGGER.fatal('error! %s', err, exc_info=True)
        sys.exit(1)
