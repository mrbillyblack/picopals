# Deploying picopals to GKE

These manifests run picopals on GKE with **managed data services** (Cloud SQL +
Memorystore) and **secrets in GCP Secret Manager** — no secret values in git.

```
Internet
  └─ GKE Ingress (managed TLS, static IP)
        ├─ /api/* → picopals-backend  ─┬─ Cloud SQL (via Auth Proxy sidecar)
        │            envFrom: ConfigMap └─ Memorystore (Redis)
        │                    + Secret (synced from Secret Manager)
        └─ /*     → picopals-frontend (nginx static)
```

## Layout

```
k8s/
├── base/                     # the committable, value-free manifests
│   ├── namespace.yaml
│   ├── serviceaccount.yaml   # Workload Identity KSA
│   ├── configmap.yaml        # non-secret config (MYSQL_DATABASE, CORS, REDIS_URL)
│   ├── secretstore.yaml      # ESO -> Secret Manager (via Workload Identity)
│   ├── external-secret.yaml  # which secrets to sync, by name only
│   ├── secret.example.yaml   # TEMPLATE for the manual route (not applied)
│   ├── backend-deployment.yaml   # + Cloud SQL Auth Proxy sidecar
│   ├── backend-service.yaml
│   ├── frontend-deployment.yaml
│   ├── frontend-service.yaml
│   ├── managed-certificate.yaml
│   ├── ingress.yaml
│   └── kustomization.yaml
└── overlays/
    ├── dev/                  # 1 replica each
    └── prod/                 # pinned image tags
```

## What maps from the old `.env`

| `.env` key | Lands as | Where |
|---|---|---|
| `MYSQL_DATABASE`, `CORS_ORIGINS`, `REDIS_URL` | ConfigMap `picopals-config` | committed (non-secret) |
| `DATABASE_URL`, `MYSQL_USER`, `MYSQL_PASSWORD` | Secret `picopals-secrets` | **Secret Manager** → synced by ESO |
| `MYSQL_ROOT_PASSWORD` | — | not needed (Cloud SQL manages the instance) |
| `VITE_API_BASE` | Docker **build arg** | baked into the frontend image in CI, not a runtime env |

> **Secrets never enter git.** `.gitignore` blocks `k8s/**/secret.yaml`,
> `k8s/**/*.secret.yaml`, `*.secret.env`, and `*-sa-key.json`. The committed
> manifests reference secrets by *name* only.

## One-time GCP setup

```bash
PROJECT_ID=your-project; REGION=us-central1; CLUSTER=picopals

# 1. Artifact Registry + push images (built the same way as the compose files)
gcloud artifacts repositories create picopals --repository-format=docker --location=$REGION
docker build -t $REGION-docker.pkg.dev/$PROJECT_ID/picopals/backend:1.0.0 ./backend
docker build --build-arg VITE_API_BASE=/api \
  -t $REGION-docker.pkg.dev/$PROJECT_ID/picopals/frontend:1.0.0 ./frontend
docker push $REGION-docker.pkg.dev/$PROJECT_ID/picopals/backend:1.0.0
docker push $REGION-docker.pkg.dev/$PROJECT_ID/picopals/frontend:1.0.0

# 2. Cluster with Workload Identity
gcloud container clusters create-auto $CLUSTER --region $REGION   # Autopilot: WI on by default

# 3. Cloud SQL (MySQL 8) + database + user
gcloud sql instances create picopals-sql --database-version=MYSQL_8_0 --region=$REGION --tier=db-g1-small
gcloud sql databases create picopals --instance=picopals-sql
gcloud sql users create tama --instance=picopals-sql --password=SUPERSECRET

# 4. Memorystore (Redis), private IP -> put it in configmap.yaml REDIS_URL
gcloud redis instances create picopals-redis --size=1 --region=$REGION

# 5. Secret Manager values (the only place real secrets live)
printf 'mysql+pymysql://tama:SUPERSECRET@127.0.0.1:3306/picopals' \
  | gcloud secrets create picopals-database-url --data-file=-
printf 'tama'        | gcloud secrets create picopals-mysql-user --data-file=-
printf 'SUPERSECRET' | gcloud secrets create picopals-mysql-password --data-file=-

# 6. IAM service account for the app + grant it access, bind via Workload Identity
gcloud iam service-accounts create picopals
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:picopals@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:picopals@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"
gcloud iam service-accounts add-iam-policy-binding \
  picopals@$PROJECT_ID.iam.gserviceaccount.com \
  --role roles/iam.workloadIdentityUser \
  --member "serviceAccount:$PROJECT_ID.svc.id.goog[picopals/picopals]"

# 7. Reserve the Ingress IP and point DNS at it
gcloud compute addresses create picopals-ip --global

# 8. Install the External Secrets Operator (once per cluster)
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets -n external-secrets --create-namespace
```

## Fill in placeholders

Replace across `base/` (and overlay image names): `PROJECT_ID`, `REGION`,
`CLUSTER_NAME`, `INSTANCE_NAME` (the Cloud SQL connection name
`PROJECT_ID:REGION:picopals-sql`), `REDIS_PRIVATE_IP`, and `picopals.example.com`.

## Deploy

```bash
# Preview the rendered manifests
kubectl kustomize k8s/overlays/prod

# Apply
kubectl apply -k k8s/overlays/prod

# Watch rollout + cert (cert can take ~15 min after DNS resolves)
kubectl -n picopals get pods,ingress,managedcertificate
```

ESO will read Secret Manager and create the `picopals-secrets` Secret; the
backend picks it up via `envFrom`. The Cloud SQL Auth Proxy sidecar exposes the
database at `127.0.0.1:3306`, matching `DATABASE_URL`.

## Manual-secret alternative (not recommended)

If you don't want ESO, skip `secretstore.yaml` / `external-secret.yaml`, copy
`secret.example.yaml` → `secret.yaml` (gitignored), fill it in, add it to
`base/kustomization.yaml` resources, and `kubectl apply -k`. The values stay on
your machine / cluster and never get committed.

## Notes

- `/api/health` always returns HTTP 200 (with a `status` field), so the probes
  here check liveness/serving, not DB health. Tighten the readiness probe if you
  want pods pulled from rotation when the DB is unreachable.
- Autopilot ignores CPU/memory `limits` shaping but honors `requests`; on
  Standard clusters the limits apply as written.
