from __future__ import absolute_import, unicode_literals

import math
import re
import time
from collections import namedtuple

import boto3


class RecordSet(namedtuple('RecordSet', 'name type ttl records')):
    def __new__(cls, name, type, ttl, records, original_json=None):
        if type == 'CNAME':
            records = map(cls.normalize_name, records)

        inst = super(cls, RecordSet).__new__(cls, cls.normalize_name(name),
                                             type, ttl, frozenset(records))
        inst.original_json = original_json and dict(original_json)
        return inst

    @classmethod
    def normalize_name(cls, name):
        if not name.endswith("."):
            name += "."
        return name

    @classmethod
    def from_json(cls, json):
        return cls(name=json['Name'], type=json['Type'], ttl=json['TTL'],
                   records=[r['Value'] for r in json['ResourceRecords']],
                   original_json=json)

    def change_request(self, existing=False):
        return {
            'Action': ('UPSERT' if existing else 'CREATE'),
            'ResourceRecordSet': {
                'Name': self.name,
                'Type': self.type,
                'TTL': self.ttl,
                'ResourceRecords': [{'Value': r} for r in self.records]
            }
        }

    def delete_request(self):
        return {
            'Action': 'DELETE',
            'ResourceRecordSet': self.original_json
        }

    def merge(self, other):
        if other is None:
            return self
        if self.type != other.type:
            raise ValueError("Incompatible record types, cannot merge")
        if self.type == 'CNAME':
            if self == other:
                return self

            raise ValueError("Cannot merge CNAME records")

        return self._replace(records=self.records | other.records)


def aws_lambda():
    return boto3.client('lambda')


def ec2():
    return boto3.client('ec2')


def asg():
    return boto3.client('autoscaling')


def cfn():
    return boto3.client('cloudformation')


def route53():
    return boto3.client('route53')


def wait_asg_instance_state(instance_id, desired_state, delay=10, timeout=120):
    for attempt in range(int(math.ceil(timeout / delay))):
        response = asg().describe_auto_scaling_instances(
            InstanceIds=[instance_id])

        state = response['AutoScalingInstances'][0]['LifecycleState']
        if state == desired_state:
            break

        time.sleep(delay)
    else:
        raise RuntimeError('Failed to wait for instance LifecycleState')


def clean_hostname(s):
    return re.sub(r"[^a-z0-9-_]", "", s.lower())
