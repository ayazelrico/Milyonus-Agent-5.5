---
name: aws-cli
description: Manage cloud resources with the AWS CLI (S3, EC2, IAM, logs)
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - aws
    - cloud
    - cli
    category: devops
    requires_toolsets:
    - terminal
    provenance: official
---

# AWS CLI
## Setup & identity
```bash
aws configure                 # key, region, output format
aws sts get-caller-identity   # verify who you are
export AWS_PROFILE=prod       # switch profile
```
## S3
```bash
aws s3 ls
aws s3 cp file.txt s3://bucket/path/
aws s3 sync ./dir s3://bucket/dir
aws s3 presign s3://bucket/key --expires-in 3600
```
## EC2 / general
```bash
aws ec2 describe-instances --query "Reservations[].Instances[].[InstanceId,State.Name]" --output table
aws logs tail /aws/lambda/fn --follow
aws ecr get-login-password | docker login --username AWS --password-stdin <acct>.dkr.ecr.<region>.amazonaws.com
```
## Tips
- Filter output with `--query` (JMESPath); `--output table|json|text`.
- Try `--dry-run` where supported first.
- Never hardcode credentials; use IAM roles + least privilege.
- Prefer `aws configure sso` (short-lived credentials) over long-lived keys.
