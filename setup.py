from setuptools import setup

VERSION = '0.1.0'

setup(
    name='ec2-route53-lambdas',
    package_dir={'': 'src'},
    packages=['ec2_route53_lambdas'],
    version=VERSION,
    description='Automatically provision AWS EBS volumes from snapshots',
    long_description=open('README.rst').read(),
    url='https://github.com/Cobliteam/ec2-route53-lambdas',
    download_url='https://github.com/Cobliteam/ec2-route53-lambdas/archive/{}.tar.gz'.format(VERSION),
    author='Daniel Miranda',
    author_email='daniel@cobli.co',
    license='MIT',
    # These requirements are provided by the Lambda environment, so we omit them
    # here and add them to requirements-dev.txt
    #
    # install_requires=['boto3', 'python-dateutil'],
    keywords='aws ec2 route53 dns lambda')
