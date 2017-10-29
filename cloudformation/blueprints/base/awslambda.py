from troposphere import iam, events, awslambda, sns
from troposphere import AWS_ACCOUNT_ID, GetAtt, Join, Ref
from troposphere.awslambda import Code
from awacs.aws import Action, Allow, Policy, Statement
from awacs.helpers.trust import get_lambda_assumerole_policy
from stacker.blueprints.base import Blueprint
from stacker.blueprints.variables.types import CFNNumber, TroposphereType


class LambdaBlueprint(Blueprint):
    DEFAULT_PERMISSIONS = frozenset()

    VARIABLES = {
        'Code': {
            'type': awslambda.Code,
            'description': 'Lambda payload information'
        },
        'MemorySize': {
            'type': CFNNumber,
            'description': 'Amount of memory to allocate to the Lambda Function',
            'default': '128',
            'allowed_values': awslambda.MEMORY_VALUES
        },
        'Timeout': {
            'type': CFNNumber,
            'description': 'Maximum execution time of the Lambda Function',
            'default': '120'
        }
    }

    def add_lambda_role(self, title, extra_permissions):
        perms = self.DEFAULT_PERMISSIONS.union(extra_permissions)
        permissions = [Action(*perm) for perm in perms]

        return self.template.add_resource(iam.Role(
            title + 'LambdaRole',
            Path='/',
            Policies=[iam.Policy(
                PolicyName=title + 'LambdaExecution',
                PolicyDocument=Policy(Version='2012-10-17', Statement=[
                    Statement(
                        Effect=Allow,
                        Action=[Action('logs', '*')],
                        Resource=['arn:aws:logs:*:*:*']
                    ),
                    Statement(
                        Effect=Allow,
                        Action=list(permissions),
                        Resource=['*'],
                    )
                ])
            )],
            AssumeRolePolicyDocument=get_lambda_assumerole_policy()
        ))

    def add_lambda_events_rule(self, title, function, **kwargs):
        t = self.template

        schedule_rule = t.add_resource(events.Rule(
            title + 'ScheduleRule',
            Targets=[events.Target(Arn=GetAtt(function, 'Arn'),
                                   Id=title + 'LambdaFunction')],
            **kwargs
        ))

        perm = t.add_resource(awslambda.Permission(
            title + 'LambdaInvokePermission',
            FunctionName=Ref(function),
            Action='lambda:InvokeFunction',
            Principal='events.amazonaws.com',
            SourceArn=GetAtt(schedule_rule, 'Arn')
        ))

        return schedule_rule, perm

    def add_lambda_sns_topic_subscription(self, title, topic,
                                          aws_lambda_function):
        self.template.add_resource(sns.SubscriptionResource(
            title + 'LambdaSubscriptionToTopic',
            Protocol='lambda',
            TopicArn=topic,
            Endpoint=GetAtt(aws_lambda_function, 'Arn')))

        self.template.add_resource(awslambda.Permission(
            title + 'LambdaSubscriptionToTopicPermission',
            FunctionName=Ref(aws_lambda_function),
            Action='lambda:InvokeFunction',
            Principal='sns.amazonaws.com',
            SourceArn=topic
        ))
