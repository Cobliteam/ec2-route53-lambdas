#!/bin/bash

set -e

flake8 src
pytest --cov=ec2_route53_lambdas "$@"
