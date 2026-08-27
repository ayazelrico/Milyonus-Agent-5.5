---
name: terraform
description: Manage infrastructure as code with Terraform (plan/apply/state)
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - terraform
    - iac
    - infra
    category: devops
    requires_toolsets:
    - terminal
    provenance: official
---

# Terraform (Infrastructure as Code)
## Core loop
```bash
terraform init      # download providers/modules
terraform fmt       # format
terraform validate  # validate
terraform plan      # what will change (READ before applying)
terraform apply     # apply (asks for confirmation)
terraform destroy   # tear down resources
```
## Structure
- `main.tf` resources, `variables.tf` inputs, `outputs.tf` outputs, `terraform.tfvars` values.
- **Resource:** `resource "aws_s3_bucket" "b" { bucket = var.name }`
- **Variable:** `variable "name" { type = string }` -> `var.name`
- **Output:** `output "url" { value = aws_s3_bucket.b.website_endpoint }`
- **Module:** `module "vpc" { source = "./modules/vpc" }`
## State (critical)
- The state file (`terraform.tfstate`) records real infra — **never commit it**, it holds secrets.
- For teams use a **remote backend** (S3 + DynamoDB lock, Terraform Cloud).
- `terraform state list` / `terraform import` to manage existing resources.
## Working safely
- Always read `plan` first; review the `apply` output.
- Separate environments with workspaces: `terraform workspace new staging`.
- Pin provider versions with `required_providers`.
