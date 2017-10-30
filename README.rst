ec2-route53-lambdas
===================

Collection of Lambda functions to better integrate AWS compute (EC2) and DNS
(Route53) resources.


Installation / Deployment
-------------------------

The functions are packaged inside a module named ``ec2_route53_lambdas``, so
that they can be include programatically if desired, but the most common usage
will be to deploy them directly to your AWS account.

To make that easier, a Cloudformation stack is provided, that can be deployed
using `stacker <https://github.com/remind101/stacker>`_. To use it, copy
``cloudformation/config.env.example`` to ``cloudformation/config.env``,
and edit it with your own settings:

.. code:: yaml

    namespace: my-namespace
    route53_private_zone_id: Z1111111111111
    ec2_dns_vpcs: vpc-11111111,vpc-22222222
    ec2_dns_domains: i.prod.aws.example.com,i.dev.aws.example.com

Then run ``cloudformation/deploy.sh`` after setting up your AWS credentials with
environment variables (e.g. ``AWS_PROFILE`` and ``AWS_DEFAULT_REGION``). The
namespace will be used to create an S3 bucket and prefix the CloudFormation
resource names. The VPCs and domains will be matched in the corresponding
position in their list (separated by commas). So in the example above, the
instances in ``vpc-11111111`` will have records created in
``i.prod.aws.example.com``.

When working with multiple regions, the stack can be deployed multiple times using
different environment files by specifying all the ``stacker`` options:

::

    cd cloudformation
    source venv/bin/activate
    AWS_DEFAULT_REGION=us-east-1 stacker build -i -t us-east-1.env stack.yml


EC2 Instances to Route53 synchronization
----------------------------------------

The ``ec2_dns`` function creates DNS entries for EC2 instances automatically.
It associates a DNS subdomain with a VPC, such that records corresponding to
each instance's ID and tagged Name are created in a designated hosted zone.

Due to the lack of tagging support for individual records, the function works
by determining the desired state of the **whole** subdomain, and creating or
deleting any records to converge to that state. Hence, any chosen
subdomain should be used **exclusively for the instance aliases of one
VPC in one region**.

For example, when managing instances for ``example.com``, multiple subdomains
could be set up for production and development VPCs in different regions, and
running one instance of the function in each region.

- ``prod.us-east-1.aws.example.com``
- ``dev.us-east-1.aws.example.com``
- ``prod.us-west-1.aws.example.com``
- ``dev.us-west-1.aws.example.com``

Records will be created only for instances in the ``pending`` or ``running``
states, based on their IDs, their Name tags, and whether they belong to Auto
Scaling Groups. Whenever instances are stopped or terminated, their records are
erased.
This is achieved by subscring to Instance State Change events through
CloudWatch. Additionaly, the function is scheduled to run periodically
(by default, every 2 minutes) to handle tag changes, that are not easily
subscribed to without setting up CloudTrail.

For each suitable instance, records will be created as follows (listed in BIND
syntax, with the base domain implied)


Instance ID
    ::

        i-1111111111111111  IN  A  10.0.0.100
        i-2222222222222222  IN  A  10.0.0.101

Name Tag
    If multiple instances have the same name, A records for all of them will be
    created with the same hostname.

    ::

        db-server   IN  A  10.0.0.102
                    IN  A  10.0.0.103
        web-server  IN  A  10.0.0.104
                    IN  A  10.0.0.105

Name Tag (Numbered)
    Instances that do not belong to Auto Scaling Groups have additional numbered
    records created based on their names, if the names don't already end in a
    numeric pattern (i.e. matching the regex ``-[0-9]+$``). Instances with
    earlier launch times are assigned smaller numbers.

    Use these records with care, as instance numbers can change somewhat
    unpredictably. Use instance IDs whenever you want absolute certainty of
    which instance you are accessing.

    ::

        db-server-1   IN  A  10.0.0.102
        db-server-2   IN  A  10.0.0.103
        web-server-1  IN  A  10.0.0.104
        web-server-2  IN  A  10.0.0.105


Required Permissions
--------------------

The ``stacker`` templates already set up the required permissions for the
Lambdas using an IAM role.

The ``ec2_dns`` function requires read access to EC2 instances, and write access
to the chosen Route53 hosted zone:

- ``ec2:DescribeInstances``
- ``ec2:DescribeTags``
- ``route53:ChangeResourceRecordSets``
- ``route53:ListResourceRecordSets``
- ``route53:GetChange``


License (MIT)
-------------

::

    Copyright (C) 2017 Cobli

    Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
