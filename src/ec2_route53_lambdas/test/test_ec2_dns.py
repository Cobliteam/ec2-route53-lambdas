from __future__ import absolute_import, unicode_literals

from datetime import datetime
from .conftest import gen_instance_info_response

from ec2_route53_lambdas.util import RecordSet
from ec2_route53_lambdas import ec2_dns


PROD_VPC = "vpc-11111111"
DEV_VPC = "vpc-22222222"

VPC_DOMAIN_MAP = {
    PROD_VPC: "prod",
    DEV_VPC: "dev"
}

TTL = 60

STARTING_INSTANCES = [
    gen_instance_info_response(
        name='job-worker', instance_id="i-0000000000000001",
        vpc_id=PROD_VPC, private_ip="10.0.0.101",
        tags={'aws:autoscaling:groupName': 'job-workers-prod'},
        launch_time=datetime(2017, 1, 1, 1, 0, 0)),
    gen_instance_info_response(
        name='job-worker', instance_id="i-0000000000000002",
        vpc_id=PROD_VPC, private_ip="10.0.0.102",
        tags={'aws:autoscaling:groupName': 'job-workers-prod'},
        launch_time=datetime(2017, 1, 1, 0, 0, 0)),
    gen_instance_info_response(
        name='db', instance_id="i-0000000000000003",
        vpc_id=PROD_VPC, private_ip="10.0.0.103",
        launch_time=datetime(2017, 1, 1, 1, 0, 0)),
    gen_instance_info_response(
        name='db', instance_id="i-0000000000000004",
        vpc_id=PROD_VPC, private_ip="10.0.0.104",
        launch_time=datetime(2017, 1, 1, 0, 0, 0)),
    gen_instance_info_response(
        name='web-1', instance_id="i-0000000000000005",
        vpc_id=PROD_VPC, private_ip="10.0.0.105",
        launch_time=datetime(2017, 1, 1, 0, 0, 0)),
    gen_instance_info_response(
        name='job-worker-1', instance_id="i-0000000000000006",
        vpc_id=PROD_VPC, private_ip="10.0.0.106",
        launch_time=datetime(2017, 1, 1, 0, 0, 0)),
    gen_instance_info_response(
        name='job-worker', instance_id="i-0000000000000011",
        vpc_id=DEV_VPC, private_ip="10.0.1.101",
        tags={'aws:autoscaling:groupName': 'job-workers-dev'},
        launch_time=datetime(2017, 1, 1, 0, 0, 0)),
    gen_instance_info_response(
        name='job-worker', instance_id="i-0000000000000012",
        tags={'aws:autoscaling:groupName': 'job-workers-dev'},
        vpc_id=DEV_VPC, private_ip="10.0.1.102",
        launch_time=datetime(2017, 1, 1, 0, 0, 0))
]

STARTING_ZONES = [RecordSet(r[0], "A", TTL, r[1]) for r in [
    ("i-0000000000000001.prod.",
     {"10.0.0.101"}),
    ("i-0000000000000002.prod.",
     {"10.0.0.102"}),
    ("i-0000000000000003.prod.",
     {"10.0.0.103"}),
    ("i-0000000000000004.prod.",
     {"10.0.0.104"}),
    ("i-0000000000000005.prod.",
     {"10.0.0.105"}),
    ("i-0000000000000006.prod.",
     {"10.0.0.106"}),
    ("i-0000000000000011.dev.",
     {"10.0.1.101"}),
    ("i-0000000000000012.dev.",
     {"10.0.1.102"}),
    ("job-worker.prod",
     {"10.0.0.101", "10.0.0.102"}),
    ("db.prod",
     {"10.0.0.103", "10.0.0.104"}),
    ("db-1.prod",
     {"10.0.0.104"}),
    ("db-2.prod",
     {"10.0.0.103"}),
    ("web-1.prod",
     {"10.0.0.105"}),
    ("job-worker-1.prod",
     {"10.0.0.106"}),
    ("job-worker.dev",
     {"10.0.1.101", "10.0.1.102"})
]]


def test_records_from_instances():
    records = ec2_dns.records_from_instances(STARTING_INSTANCES, VPC_DOMAIN_MAP,
                                             TTL)
    assert records == set(STARTING_ZONES)


def test_records_from_running_instances(mocker, ec2_stub):
    mocker.patch("ec2_route53_lambdas.ec2_dns.records_from_instances",
                 return_value=STARTING_ZONES, autospec=True)

    ec2_stub.add_response(
        "describe_instances",
        {
            "Reservations": [{
                "OwnerId": "258273616434",
                "ReservationId": "r-4ae132a8",
                "Groups": [],
                "Instances": STARTING_INSTANCES
            }]
        },
        {
            "Filters": [{
                "Name": "instance-state-name",
                "Values": ["pending", "running"]
            }]
        })

    extracted = ec2_dns.records_from_running_instances(VPC_DOMAIN_MAP, TTL)
    assert extracted == STARTING_ZONES


HOSTED_ZONE_ID = "/hostedzone/Z1111111111111"
RECORD_SETS = [
    {
        "ResourceRecords": [
            {"Value": "ns-1536.awsdns-00.co.uk."},
            {"Value": "ns-0.awsdns-00.com."},
            {"Value": "ns-1024.awsdns-00.org."},
            {"Value": "ns-512.awsdns-00.net."}
        ],
        "Type": "NS",
        "Name": "example.com.",
        "TTL": 86400
    },
    {
        "ResourceRecords": [
            {"Value": "ns-1536.awsdns-00.co.uk. "
                      "awsdns-hostmaster.amazon.com. 1 7200 900 1209600 "
                      "86400"}
        ],
        "Type": "SOA",
        "Name": "example.com.",
        "TTL": 900
    },
    {
        "ResourceRecords": [
            {"Value": "api.prod.aws.example.com"}
        ],
        "Type": "CNAME",
        "Name": "api.example.com.",
        "TTL": 300
    },
    {
        "ResourceRecords": [
            {"Value": "elb-whatever-11111111.us-east-1.elb.amazonaws.com"}
        ],
        "Type": "CNAME",
        "Name": "api.prod.aws.example.com.",
        "TTL": 300
    },
    {
        "ResourceRecords": [
            {"Value": "10.0.0.101"},
            {"Value": "10.0.0.102"},
            {"Value": "10.0.0.103"}
        ],
        "Type": "A",
        "Name": "db.dev.aws.example.com.",
        "TTL": 300
    },
    {
        "ResourceRecords": [
            {"Value": "172.31.17.33"}
        ],
        "Type": "CNAME",
        "Name": "prefix-prod.aws.example.com.",
        "TTL": 300
    },
]


def test_extract_existing_records():
    extracted = ec2_dns.extract_existing_records(
        RECORD_SETS, ["prod.aws.example.com", "dev.aws.example.com"])
    expected = {
        RecordSet("api.prod.aws.example.com", "CNAME", 300,
                  {"elb-whatever-11111111.us-east-1.elb.amazonaws.com."}),
        RecordSet("db.dev.aws.example.com.", "A", 300,
                  {"10.0.0.101", "10.0.0.102", "10.0.0.103"})
    }

    assert set(extracted) == expected


def test_existing_records(route53_stub):
    route53_stub.add_response(
        "list_resource_record_sets",
        {
            "ResourceRecordSets": RECORD_SETS,
            "IsTruncated": False,
            "MaxItems": "100"
        },
        {"HostedZoneId": HOSTED_ZONE_ID})

    extracted = ec2_dns.existing_records(
        HOSTED_ZONE_ID, ["prod.aws.example.com", "dev.aws.example.com"])
    expected = {
        RecordSet("api.prod.aws.example.com", "CNAME", 300,
                  {"elb-whatever-11111111.us-east-1.elb.amazonaws.com."}),
        RecordSet("db.dev.aws.example.com.", "A", 300,
                  {"10.0.0.101", "10.0.0.102", "10.0.0.103"})
    }

    assert extracted == expected


OLD_RECORDS = [
    RecordSet.from_json({
        "Name": "a.asd",
        "Type": "A",
        "TTL": 300,
        "ResourceRecords": [{"Value": "1.1.1.1"}]
    }),
    RecordSet.from_json({
        "Name": "b.asd",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [{"Value": "a.asd"}]
    }),
    RecordSet.from_json({
        "Name": "c.asd",
        "Type": "A",
        "TTL": 300,
        "ResourceRecords": [{"Value": "1.1.1.2"}],
        "HealthCheckId": "H123134"
    }),
    RecordSet.from_json({
        "Name": "d.asd",
        "Type": "A",
        "TTL": 300,
        "ResourceRecords": [{"Value": "1.1.1.3"}]
    }),
    RecordSet.from_json({
        "Name": "e.asd",
        "Type": "A",
        "TTL": 300,
        "ResourceRecords": [{"Value": "1.1.1.4"}]
    })
]

NEW_RECORDS = [
    RecordSet("a.asd", "A",     300, {"1.1.1.1"}),
    RecordSet("b.asd", "A",     300, {"1.1.1.5"}),
    RecordSet("d.asd", "A",     300, {"1.1.1.3"}),
    RecordSet("e.asd", "A",     300, {"1.1.1.8"}),
    RecordSet("f.asd", "CNAME", 300, {"b.asd"})
]

RECORDS_DIFF = [
    {
        "Action": "UPSERT",
        "ResourceRecordSet": {
            "Name": "b.asd.",
            "ResourceRecords": [{"Value": "1.1.1.5"}],
            "TTL": 300,
            "Type": "A"
        }
    },
    {
        "Action": "DELETE",
        "ResourceRecordSet": {
            "Name": "c.asd",
            "ResourceRecords": [{"Value": "1.1.1.2"}],
            "TTL": 300,
            "Type": "A",
            "HealthCheckId": "H123134"
        }
    },
    {
        "Action": "UPSERT",
        "ResourceRecordSet": {
            "Name": "e.asd.",
            "ResourceRecords": [{"Value": "1.1.1.8"}],
            "TTL": 300,
            "Type": "A"
        }
    },
    {
        "Action": "CREATE",
        "ResourceRecordSet": {
            "Name": "f.asd.",
            "ResourceRecords": [{"Value": "b.asd."}],
            "TTL": 300,
            "Type": "CNAME"
        }
    }
]


def test_diff_records():
    def sort_key(e):
        return e["ResourceRecordSet"]["Name"], e["ResourceRecordSet"]["Type"]

    generated = ec2_dns.diff_records(OLD_RECORDS, NEW_RECORDS)
    assert sorted(generated, key=sort_key) == sorted(RECORDS_DIFF, key=sort_key)


def test_converge_records(mocker, route53_stub):
    vpc_domain_map = {"vpc-1234": "asd"}
    comment = "test comment"
    change_id = "C1234567"

    existing_records = mocker.patch(
        "ec2_route53_lambdas.ec2_dns.existing_records",
        return_value=OLD_RECORDS, autospec=True)
    records_from_running_instances = mocker.patch(
        "ec2_route53_lambdas.ec2_dns.records_from_running_instances",
        return_value=NEW_RECORDS, autospec=True)
    diff_records = mocker.patch(
        "ec2_route53_lambdas.ec2_dns.diff_records",
        return_value=RECORDS_DIFF, autospec=True)

    route53_stub.add_response(
        "change_resource_record_sets",
        {
            "ChangeInfo": {
                "Id": change_id,
                "Status": "PENDING",
                "SubmittedAt": datetime(2017, 1, 1, 0, 0, 0),
                "Comment": comment
            }
        },
        {
            "HostedZoneId": HOSTED_ZONE_ID,
            "ChangeBatch": {"Changes": RECORDS_DIFF}
        })

    route53_stub.add_response(
        "get_change",
        {
            "ChangeInfo": {
                "Id": change_id,
                "Status": "INSYNC",
                "SubmittedAt": datetime(2017, 1, 1, 0, 0, 0),
                "Comment": comment
            }
        },
        {
            "Id": change_id
        })

    ec2_dns.converge_records(HOSTED_ZONE_ID, vpc_domain_map, TTL)
    route53_stub.assert_no_pending_responses()

    existing_records.assert_called_once_with(
        HOSTED_ZONE_ID, list(vpc_domain_map.values()))
    records_from_running_instances.assert_called_once_with(
        vpc_domain_map, TTL)
    diff_records.assert_called_once_with(
        OLD_RECORDS, NEW_RECORDS)


EC2_STATE_EVENT = {
    "id": "7bf73129-1428-4cd3-a780-95db273d1602",
    "detail-type": "EC2 Instance State-change Notification",
    "source": "aws.ec2",
    "account": "123456789012",
    "time": "2015-11-11T21:29:54Z",
    "region": "us-east-1",
    "resources": [
        "arn:aws:ec2:us-east-1:123456789012:instance/i-abcd1111"
    ],
    "detail": {
        "instance-id": "i-abcd1111",
        "state": "pending"
    }
}


def test_handler(mocker, monkeypatch):
    monkeypatch.setenv('EC2_DNS_HOSTED_ZONE_ID', HOSTED_ZONE_ID)
    monkeypatch.setenv("EC2_DNS_VPC_IDS", ",".join(VPC_DOMAIN_MAP.keys()))
    monkeypatch.setenv("EC2_DNS_VPC_DOMAINS", ",".join(VPC_DOMAIN_MAP.values()))
    monkeypatch.setenv("EC2_DNS_RECORD_TTL", str(TTL))

    converge_records = mocker.patch(
        "ec2_route53_lambdas.ec2_dns.converge_records",
        return_value=True, autospec=True)

    context = mocker.MagicMock()

    assert ec2_dns.handler(EC2_STATE_EVENT, context)

    converge_records.assert_called_once_with(HOSTED_ZONE_ID, VPC_DOMAIN_MAP,
                                             TTL)
