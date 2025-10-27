# Kubernetes Manifests

This directory contains Kubernetes deployment manifests for the Arash Bot application.

## Directory Structure

```
manifests/
├── dev/           # Development environment
│   ├── deployment.yaml
│   ├── ingress.yaml
│   └── service.yaml
├── stage/         # Staging environment
│   ├── deployment.yaml
│   ├── ingress.yaml
│   └── service.yaml
└── prod/          # Production environment
    ├── deployment.yaml
    ├── ingress.yaml
    └── service.yaml
```

## Environments

### Development
- **Namespace**: `arash`
- **Image**: `repo3.lucidfirm.ir/primebot/arash-external-api:dev-latest`
- **Domain**: `arash-api-dev.irisaprime.ir`
- **Resources**: CPU: 2 cores, Memory: 2Gi

### Staging
- **Namespace**: `arash`
- **Image**: `repo3.lucidfirm.ir/primebot/arash-external-api:latest`
- **Domain**: `arash-api-stage.irisaprime.ir`
- **Resources**: CPU: 2 cores, Memory: 2Gi

### Production
- **Namespace**: `arash`
- **Image**: `repo3.lucidfirm.ir/primebot/arash-external-api:latest`
- **Domain**: `arash-api.irisaprime.ir`
- **Resources**: CPU: 2 cores, Memory: 2Gi

## Deployment Instructions

### Deploy to Development

```bash
kubectl apply -f manifests/dev/
```

### Deploy to Staging

```bash
kubectl apply -f manifests/stage/
```

### Deploy to Production

```bash
kubectl apply -f manifests/prod/
```

## Service Configuration

All services are configured to:
- Listen on port 80 (external)
- Forward to port 3000 (container)
- Use nginx ingress controller
- Support up to 25MB request body size

## Image Registry

Images are stored in: `repo3.lucidfirm.ir/primebot/arash-external-api`

- Dev tag: `dev-latest`
- Stage/Prod tag: `latest`

## Notes

- All deployments use the `regcred` image pull secret
- Timezone is set to `Asia/Tehran`
- RestartPolicy is set to `Always` for high availability
- ImagePullPolicy is set to `Always` to ensure latest image
