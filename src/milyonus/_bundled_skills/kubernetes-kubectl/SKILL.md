---
name: kubernetes-kubectl
description: Inspect and manage Kubernetes resources with kubectl
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
- **Context:** `kubectl config current-context`, ns: `kubectl get ns`
- **Resources:** `kubectl get pods -A`, `kubectl get svc,deploy`
- **Detail:** `kubectl describe pod <name>`
- **Logs:** `kubectl logs -f <pod> [-c container]`
- **Exec:** `kubectl exec -it <pod> -- sh`
- **Apply:** `kubectl apply -f manifest.yaml`; delete `kubectl delete -f manifest.yaml`
- **Scale:** `kubectl scale deploy/<name> --replicas=3`
