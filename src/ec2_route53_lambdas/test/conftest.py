from __future__ import absolute_import, unicode_literals

from datetime import datetime

import pytest
from dateutil.tz import tzutc

import boto3
from botocore import UNSIGNED
from botocore.client import Config
from botocore.stub import Stubber


def boto3_stub(mocker, mocked_svc):
    client = boto3.client(mocked_svc, config=Config(signature_version=UNSIGNED),
                          region_name='us-east-1')

    orig_get_client = boto3.client

    def get_client(svc, *args, **kwargs):
        if mocked_svc == svc:
            return client

        return orig_get_client(svc, *args, **kwargs)

    orig_get_waiter = client.get_waiter

    def get_waiter_no_delay(*args, **kwargs):
        waiter = orig_get_waiter(*args, **kwargs)
        waiter.config.delay = 0
        return waiter

    mocker.patch.object(boto3, 'client', get_client)
    mocker.patch.object(client, 'get_waiter', wraps=get_waiter_no_delay)

    stub = Stubber(client)
    stub.activate()

    yield stub

    stub.deactivate()


@pytest.fixture
def ec2_stub(mocker):
    for stub in boto3_stub(mocker, 'ec2'):
        yield stub


@pytest.fixture
def route53_stub(mocker):
    for stub in boto3_stub(mocker, 'route53'):
        yield stub


@pytest.fixture
def asg_stub(mocker):
    for stub in boto3_stub(mocker, 'autoscaling'):
        yield stub


def gen_instance_info_response(instance_id, private_ip, name='test-instance',
                               public_ip='1.1.1.1', vpc_id='vpc-11111111',
                               availability_zone='us-east-1a',
                               launch_time=None, tags=None):
    public_dns = "ec2-{}.compute-1.amazonaws.com".format(
        '-'.join(public_ip.split('.')))
    private_dns = "ip-{}.ec2.internal".format(
        '-'.join(private_ip.split('.')))

    tags = tags or {}
    tags['Name'] = name
    tag_pairs = [{'Key': k, 'Value': v} for k, v in tags.items()]

    if launch_time is None:
        launch_time = datetime(2017, 1, 1, 0, 0, 0, tz=tzutc())

    launch_time_str = launch_time.isoformat()

    return {
        "Monitoring": {"State": "disabled"},
        "PublicDnsName": public_dns,
        "State": {"Code": 16, "Name": "running"},
        "EbsOptimized": True,
        "LaunchTime": launch_time_str,
        "PublicIpAddress": public_ip,
        "PrivateIpAddress": private_ip,
        "ProductCodes": [],
        "VpcId": vpc_id,
        "StateTransitionReason": "",
        "InstanceId": instance_id,
        "ImageId": "ami-11111111",
        "PrivateDnsName": private_dns,
        "KeyName": "ssh-key",
        "SecurityGroups": [],
        "SubnetId": "subnet-11111111",
        "InstanceType": "m4.xlarge",
        "NetworkInterfaces": [{
            "Status": "in-use",
            "MacAddress": "00:00:00:00:00:00",
            "SourceDestCheck": True,
            "VpcId": vpc_id,
            "Description": "",
            "NetworkInterfaceId": "eni-11111111",
            "PrivateIpAddresses": [{
                "PrivateDnsName": private_dns,
                "PrivateIpAddress": private_ip,
                "Primary": True,
                "Association": {
                    "PublicIp": public_ip,
                    "PublicDnsName": public_dns,
                    "IpOwnerId": "amazon"
                }
            }],
            "PrivateDnsName": private_dns,
            "Attachment": {
                "Status": "attached",
                "DeviceIndex": 0,
                "DeleteOnTermination": True,
                "AttachmentId": "eni-attach-11111111",
                "AttachTime": launch_time_str
            },
            "Groups": [],
            "Ipv6Addresses": [],
            "OwnerId": "111111111111",
            "PrivateIpAddress": private_ip,
            "SubnetId": "subnet-11111111",
            "Association": {
                "PublicIp": public_ip,
                "PublicDnsName": public_dns,
                "IpOwnerId": "amazon"
            }
        }],
        "SourceDestCheck": True,
        "Placement": {
            "Tenancy": "default",
            "GroupName": "",
            "AvailabilityZone": availability_zone
        },
        "Hypervisor": "xen",
        "InstanceLifecycle": "",
        "BlockDeviceMappings": [{
            "DeviceName": "/dev/sda1",
            "Ebs": {
                "Status": "attached",
                "DeleteOnTermination": True,
                "VolumeId": "vol-1111111111111111",
                "AttachTime": launch_time_str
            }
        }],
        "Architecture": "x86_64",
        "RootDeviceType": "ebs",
        "IamInstanceProfile": {},
        "RootDeviceName": "/dev/sda1",
        "VirtualizationType": "hvm",
        "Tags": tag_pairs,
        "AmiLaunchIndex": 0
    }
