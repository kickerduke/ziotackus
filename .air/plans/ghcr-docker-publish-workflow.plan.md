# Pubblicare l'immagine Docker su GitHub Container Registry (ghcr.io)

## Context

Il progetto ha già un `Dockerfile` funzionante ma nessun workflow CI/CD. L'obiettivo è pubblicare automaticamente l'immagine su `ghcr.io` ad ogni push su `main`/`master` (e opzionalmente a ogni release), così da poter deployare ovunque con un semplice `docker compose pull` senza dover buildare localmente.

---

## File da creare

### `.github/workflows/docker-publish.yml` (nuovo)

```yaml
name: Build and push Docker image

on:
  push:
    branches:
      - main
      - master
  release:
    types: [published]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository_owner }}/ziotackus

jobs:
  build-and-push:
    runs-on: ubuntu-latest

    permissions:
      contents: read
      packages: write          # obbligatorio per pushare su ghcr.io

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Extract Docker metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=sha,prefix=sha-,format=short
            type=raw,value=latest,enable={{is_default_branch}}
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push Docker image
        uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

**Perché `permissions: packages: write`**: senza di esso `GITHUB_TOKEN` è read-only di default e il push su ghcr.io fallisce con 403.

**Tag prodotti:**
- `sha-a1b2c3d` — sempre, per tracciabilità
- `latest` — solo su push al branch di default
- `1.2.3` / `1.2` — solo quando si pubblica una release con tag semver

---

## Modifica opzionale: `docker-compose.yml`

Per usare l'immagine pre-buildata in produzione invece di buildare localmente, sostituire `build: .` con:

```yaml
services:
  ziotackus:
    image: ghcr.io/kickerduke/ziotackus:latest
    container_name: ziotackus
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - db_data:/app/data

volumes:
  db_data:
    driver: local
```

Aggiornare il bot in produzione diventa:
```bash
docker compose pull && docker compose up -d
```

---

## Checklist primo avvio

1. Assicurarsi che il repo sia pushato su GitHub.
2. Committare `.github/workflows/docker-publish.yml` e pushare su `main`/`master` — il workflow parte automaticamente.
3. Dopo il primo run riuscito: **GitHub profile → Packages** → trovi `ghcr.io/TUO_USERNAME/ziotackus`.
4. Il package è **privato di default**. Per renderlo pubblico: Package settings → Change visibility → Public.
   - Se rimane privato, sul server di deploy bisogna autenticarsi: `echo TOKEN | docker login ghcr.io -u TUO_USERNAME --password-stdin`

---

## Verifica

1. Pushare su `main` → controllare la tab **Actions** su GitHub che il job `build-and-push` passi.
2. Andare su **GitHub → Packages** e verificare che l'immagine sia presente con i tag `latest` e `sha-*`.
3. Sul server di deploy: `docker pull ghcr.io/TUO_USERNAME/ziotackus:latest` → deve scaricare senza buildare.
