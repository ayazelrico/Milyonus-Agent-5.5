---
name: terraform
description: Terraform ile altyapıyı kod olarak yönetme (plan/apply/state)
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

## Temel döngü
```bash
terraform init      # sağlayıcıları/modülleri indir
terraform fmt       # biçimlendir
terraform validate  # doğrula
terraform plan      # ne değişecek (uygulamadan önce OKU)
terraform apply     # uygula (onay ister)
terraform destroy   # kaynakları yok et
```

## Yapı
- `main.tf` kaynaklar, `variables.tf` girdiler, `outputs.tf` çıktılar, `terraform.tfvars` değerler.
- **Kaynak:** `resource "aws_s3_bucket" "b" { bucket = var.name }`
- **Değişken:** `variable "name" { type = string }` → `var.name`
- **Çıktı:** `output "url" { value = aws_s3_bucket.b.website_endpoint }`
- **Modül:** `module "vpc" { source = "./modules/vpc" }`

## State (kritik)
- State dosyası (`terraform.tfstate`) gerçek altyapının kaydıdır — **asla git'e commit etme**, secret içerir.
- Takım için **remote backend** kullan (S3 + DynamoDB lock, Terraform Cloud).
- `terraform state list` / `terraform import` mevcut kaynakları yönetime al.

## Güvenli çalışma
- Her zaman önce `plan` oku; `apply` çıktısını gözden geçir.
- Ortamları workspace ile ayır: `terraform workspace new staging`.
- Sağlayıcı sürümlerini `required_providers` ile pinle.
