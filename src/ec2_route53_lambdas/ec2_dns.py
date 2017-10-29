from __future__ import absolute_import, unicode_literals

import re
import pprint
import os
import logging
from datetime import datetime

from ec2_route53_lambdas.util import \
    RecordSet, clean_hostname, ec2, route53


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def records_from_instances(instances, vpc_map, ttl=60):
    zones = {}
    indexes = {}

    for instance in sorted(instances, key=lambda inst: inst["LaunchTime"]):
        domain = vpc_map.get(instance["VpcId"])
        if not domain:
            continue

        instance_id = instance["InstanceId"]
        ips = frozenset([instance["PrivateIpAddress"]])
        zones[(instance_id, domain)] = \
            RecordSet(instance_id + "." + domain, "A", ttl, ips)

        tags = dict((t["Key"], t["Value"]) for t in instance.get("Tags", []))
        name = tags.get("Name")
        if not name:
            continue

        name = clean_hostname(name)
        asg_name = tags.get("aws:autoscaling:groupName")
        index_match = re.match(r'^(.+)-(\d+)$', name)
        if not asg_name and not index_match:
            prev_index = indexes.get((name, domain), 0)
            index = indexes[(name, domain)] = prev_index + 1
            indexed_name = "{}-{}".format(name, index)

            zones[(indexed_name, domain)] = \
                RecordSet(indexed_name + "." + domain, "A", ttl, ips)

        record = RecordSet(name + "." + domain, "A", ttl, ips)
        old_record = zones.get((name, domain), None)
        zones[(name, domain)] = record.merge(old_record)

    return frozenset(zones.values())


def records_from_running_instances(vpc_map, ttl):
    response = ec2().describe_instances(Filters=[{
        "Name": "instance-state-name", "Values": ["pending", "running"]
    }])
    instances = [i for r in response["Reservations"] for i in r["Instances"]]

    return records_from_instances(instances, vpc_map, ttl)


def extract_existing_records(records, domains):
    domains = list(map(RecordSet.normalize_name, domains))
    for record in records:
        tpe = record["Type"]
        if tpe not in ("A", "CNAME"):
            pass

        name = record["Name"]
        for domain in domains:
            if name.endswith("." + domain):
                break
        else:
            continue

        resources = {r["Value"] for r in record["ResourceRecords"]}
        yield RecordSet(name, tpe, record["TTL"], resources,
                        original_json=record)


def existing_records(hosted_zone_id, domains):
    records = set()
    paginator = route53().get_paginator("list_resource_record_sets")
    for page in paginator.paginate(HostedZoneId=hosted_zone_id):
        page_records = extract_existing_records(
            page["ResourceRecordSets"], domains)
        for record in page_records:
            records.add(record)

    return frozenset(records)


def diff_records(old, new):
    old = sorted(old, key=lambda r: r.name)
    new = sorted(new, key=lambda r: r.name)

    old_i = iter(old)
    new_i = iter(new)

    try:
        old_r = next(old_i)
        new_r = next(new_i)

        while True:
            if old_r.name < new_r.name:
                yield old_r.delete_request()
                old_r = next(old_i)
            elif old_r.name > new_r.name:
                yield new_r.change_request()
                new_r = next(new_i)
            else:
                if old_r != new_r:
                    yield new_r.change_request(existing=True)
                old_r = next(old_i)
                new_r = next(new_i)
    except StopIteration:
        pass

    try:
        while True:
            yield next(old_i).delete_request()
    except StopIteration:
        pass

    try:
        while True:
            yield next(new_i).change_request()
    except StopIteration:
        pass


def converge_records(hosted_zone_id, vpc_map, ttl):
    current = existing_records(hosted_zone_id, list(vpc_map.values()))
    updated = records_from_running_instances(vpc_map, ttl)

    changes = list(diff_records(current, updated))
    if not changes:
        logger.info("No changes to be made, stopping.")
        return True

    logger.info("Applying {} changes:\n{}".format(len(changes),
                                                  pprint.pformat(changes)))

    start_time = datetime.utcnow()

    change_batch = {"Changes": changes}
    change_response = route53().change_resource_record_sets(
        HostedZoneId=hosted_zone_id, ChangeBatch=change_batch)

    if change_response["ChangeInfo"]["Status"] != "INSYNC":
        waiter = route53().get_waiter("resource_record_sets_changed")
        waiter.wait(Id=change_response["ChangeInfo"]["Id"])

    elapsed_time = datetime.utcnow() - start_time
    logger.info("Route53 changes completed in {}".format(elapsed_time))

    return True


def handler(event, context):
    hosted_zone_id = os.environ['EC2_DNS_HOSTED_ZONE_ID']
    vpcs = os.environ['EC2_DNS_VPC_IDS'].split(",")
    domains = os.environ['EC2_DNS_VPC_DOMAINS'].split(",")
    ttl = int(os.environ['EC2_DNS_RECORD_TTL'])

    vpc_map = dict(zip(vpcs, domains))
    logger.info("Updating DNS from EC2 instances: HostedZoneId={}, VpcMap={}, "
                "TTL={}".format(hosted_zone_id, vpc_map, ttl))

    return converge_records(hosted_zone_id, vpc_map, ttl)
