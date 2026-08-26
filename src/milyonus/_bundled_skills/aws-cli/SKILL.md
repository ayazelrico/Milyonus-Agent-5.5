---
name: aws-cli
description: AWS CLI ile bulut kaynaklarını yönetme (S3, EC2, IAM, logs)
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

## Kurulum & kimlik
```bash
aws configure                 # anahtar, bölge, çıktı formatı
aws sts get-caller-identity   # kim olduğunu doğrula
export AWS_PROFILE=prod       # profil değiştir
```

## S3
```bash
aws s3 ls                             # bucket'ları listele
aws s3 cp dosya.txt s3://bucket/yol/  # yükle
aws s3 sync ./dir s3://bucket/dir     # senkron
aws s3 presign s3://bucket/key --expires-in 3600   # geçici link
```

## EC2 / genel
```bash
aws ec2 describe-instances --query "Reservations[].Instances[].[InstanceId,State.Name]" --output table
aws logs tail /aws/lambda/fn --follow      # CloudWatch log akışı
aws ecr get-login-password | docker login --username AWS --password-stdin <acct>.dkr.ecr.<region>.amazonaws.com
```

## İpuçları
- `--query` (JMESPath) ile çıktıyı süz; `--output table|json|text`.
- `--dry-run` destekleyen komutlarda önce dene.
- Kimlik bilgisini asla koda gömme; IAM rol + en az ayrıcalık kullan.
- `aws configure sso` ile kısa ömürlü kimlik (kalıcı anahtardan iyidir).
