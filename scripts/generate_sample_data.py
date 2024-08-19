#! /usr/bin/env python

import argparse
import os.path
import time
import faker
import random
import uuid

from jule.state import LdapStorageContainer, LdapSnapshotData, LdapSnapshotMetadata


FAKE_TITLES = [
    'Software Engineer',
    'QA Engineer',
    'Engineering Manager',
]

FAKE_DEPARTMENTS = [
    'Core Tech',
    'R&D',
    'Support',
]


def generate(data_dir: str):
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    now = time.time()
    fake = faker.Faker()
    entries = {}

    def encode(s: str | None) -> list[bytes] | None:
        if not s:
            return None
        return [s.encode('utf-8')]

    def sanitize(entry_data: dict):
        return {k: v for k, v in entry_data.items() if v is not None}

    def generate_new_person():
        entry_dn = 'uid={},ou=People,dc=example,dc=com'.format(
            uuid.uuid4(),
        )
        manager_dn = random.choice(list(entries)) if entries else None
        entries[entry_dn] = sanitize({
            'displayName': encode(fake.name()),
            'title': encode(random.choice(FAKE_TITLES)),
            'department': encode(random.choice(FAKE_DEPARTMENTS)),
            'company': encode(fake.company()),
            'manager': encode(manager_dn),
        })

    for idx in range(3):
        if idx == 0:
            for record_idx in range(random.randint(30, 100)):
                generate_new_person()
        else:  # updates
            for record_idx in range(random.randint(1, 10)):
                generate_new_person()

            for dn in entries:
                if random.random() < 0.1:
                    entries[dn]['title'] = encode(random.choice(FAKE_TITLES))

        data = LdapSnapshotData(list(entries.items()))
        metadata = LdapSnapshotMetadata(
            label='sample-%d' % idx,
            timestamp=now + (60 * 60 * 24) * idx,
            entries_count=len(data.entries),
        )
        container = LdapStorageContainer(data, metadata)
        path = os.path.join(data_dir, 'ldap-snapshot-{}.jule'.format(idx))
        with open(path, 'wb') as file:
            container.save(file)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', type=str, default='sample-data')
    args = parser.parse_args()
    generate(args.data_dir)


if __name__ == '__main__':
    main()
