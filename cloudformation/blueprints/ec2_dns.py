from troposphere import awslambda
from troposphere import GetAtt, Ref, Join
from stacker.blueprints.variables.types import \
    CFNCommaDelimitedList, CFNNumber, CFNString, EC2VPCIdList, \
    Route53HostedZoneId, TroposphereType

from .base.awslambda import LambdaBlueprint


class Ec2Dns(LambdaBlueprint):
    VARIABLES = {
        'HostedZoneID': {
            'type': Route53HostedZoneId,
            'description': 'Hosted Zone ID to create DNS entries in'
        },
        'TargetVPCIDs': {
            'type': EC2VPCIdList,
            'description': 'List of VPCs whose instances will have records '
                           'created with entry in TargetDomains in the same '
                           'position'
        },
        'TargetDomains': {
            'type': CFNCommaDelimitedList,
            'description': 'List of domain prefixes to be used when creating '
                           'records for instances of each VPC'
        },
        'RecordTTL': {
            'type': CFNNumber,
            'description': 'TTL to assign to created records',
            'default': '60'
        },
        'Schedule': {
            'type': CFNString,
            'description': 'Time for periodic DNS refresh',
            'default': 'rate(2 minutes)'
        }
    }

    def defined_variables(self):
        v = super(Ec2Dns, self).VARIABLES
        v.update(self.VARIABLES)
        return v

    def create_template(self):
        t = self.template
        v = self.get_variables()

        lambda_role = self.add_lambda_role('Ec2Dns', [
            ('ec2', 'DescribeInstances'),
            ('ec2', 'DescribeTags'),
            ('route53', 'ChangeResourceRecordSets'),
            ('route53', 'ListResourceRecordSets'),
            ('route53', 'GetChange')
        ])

        func = t.add_resource(awslambda.Function(
            'Ec2DnsLambdaFunction',
            Code=v['Code'],
            Handler='ec2_route53_lambdas.ec2_dns.handler',
            Role=GetAtt(lambda_role, 'Arn'),
            Runtime='python2.7',
            MemorySize=Ref('MemorySize'),
            Timeout=Ref('Timeout'),
            Environment=awslambda.Environment(Variables={
                'EC2_DNS_HOSTED_ZONE_ID': Ref('HostedZoneID'),
                'EC2_DNS_VPC_IDS': Join(',', Ref('TargetVPCIDs')),
                'EC2_DNS_VPC_DOMAINS': Join(',', Ref('TargetDomains')),
                'EC2_DNS_RECORD_TTL': Ref('RecordTTL')
            })
        ))

        self.add_lambda_events_rule(
            'Ec2DnsInstanceChange', func,
            EventPattern={
                'source': ['aws.ec2'],
                'detail-type': ['EC2 Instance State-change Notification'],
                "detail": {
                    "state": ["running", "stopped", "terminated"]
                }
            }
        )

        self.add_lambda_events_rule(
            'Ec2DnsRefresh', func, ScheduleExpression=Ref('Schedule'))
