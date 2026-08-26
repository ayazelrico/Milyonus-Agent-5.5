---
name: kubernetes-kubectl
description: kubectl ile Kubernetes kaynaklarını inceleme ve yönetme
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - k8s
    - kubectl
    category: devops
    requires_toolsets:
    - terminal
    provenance: official
---

# kubectl
- **Bağlam:** `kubectl config current-context`, ns: `kubectl get ns`
- **Kaynaklar:** `kubectl get pods -A`, `kubectl get svc,deploy`
- **Detay:** `kubectl describe pod <ad>`
- **Log:** `kubectl logs -f <pod> [-c container]`
- **İçine gir:** `kubectl exec -it <pod> -- sh`
- **Uygula:** `kubectl apply -f manifest.yaml`; sil `kubectl delete -f manifest.yaml`
- **Ölçekle:** `kubectl scale deploy/<ad> --replicas=3`
