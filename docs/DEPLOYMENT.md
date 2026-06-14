# Deploying a versioned release

This guide covers running Armarium from **prebuilt Docker images** published
to the GitHub Container Registry (GHCR) for each tagged release — no clone,
build toolchain, or development environment required. It's the fastest path
to a production instance, and lets you pin or roll back to a specific
version.

If you'd rather build the images yourself from source (e.g. to make local
changes), use the root [README.md](../README.md) Quick Start with
`docker-compose.yml` instead. For local development, see
[DEVELOPMENT.md](DEVELOPMENT.md).

## How releases work

Tagging a commit `vX.Y.Z` and pushing the tag triggers
[`.github/workflows/release.yml`](../.github/workflows/release.yml), which:

1. Builds and pushes `ghcr.io/craig530/armarium-backend` and
   `ghcr.io/craig530/armarium-frontend` images, each tagged both `vX.Y.Z` and
   `latest`.
2. Creates a [GitHub Release](https://github.com/craig530/Armarium/releases)
   with the matching section of [CHANGELOG.md](../CHANGELOG.md) as its
   description, with `docker-compose.prod.yml` and `.env.example` attached as
   downloadable assets.

This is an ad-hoc step run when a version is declared — not on every push to
`main`.

## 1. Install Docker (Ubuntu Server)

```bash
# Official Docker apt repo — see https://docs.docker.com/engine/install/ubuntu/
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Optional: run docker without sudo
sudo usermod -aG docker "$USER"
```

(Other distributions / macOS / Windows: any host with Docker Desktop or
Docker Engine + the Compose plugin works the same way from step 2 onward.)

## 2. Get the deployment files

You only need two files — download them from the
[latest release](https://github.com/craig530/Armarium/releases/latest)'s
assets, or fetch them directly:

```bash
mkdir armarium && cd armarium
curl -fsSLO https://raw.githubusercontent.com/craig530/Armarium/main/docker-compose.prod.yml
curl -fsSLO https://raw.githubusercontent.com/craig530/Armarium/main/.env.example
mv .env.example .env
```

## 3. Configure `.env`

Edit `.env` and set at minimum:

- `JWT_SECRET` — generate with `openssl rand -hex 32`
- `ADMIN_PASSWORD` — password for the initial admin account

See the root [README.md](../README.md#configuration) for the full
configuration reference (TMDB API key, PostgreSQL, `COOKIE_SECURE`, etc.).

To pin a specific version instead of always running the latest release, add:

```bash
# .env
ARMARIUM_VERSION=v1.0.0
```

Omit it (or set `ARMARIUM_VERSION=latest`) to track the most recent release.

## 4. Pull and start

```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

Visit `http://<host>:8080` (or your configured `PORT`) and log in with the
admin credentials from `.env`.

> If `ghcr.io/craig530/armarium-*` packages are private, authenticate first
> with a GitHub [personal access token](https://github.com/settings/tokens)
> that has the `read:packages` scope:
> `echo "$GHCR_TOKEN" | docker login ghcr.io -u <your-github-username> --password-stdin`
> — never paste the token directly into the command or a file that gets
> committed.

## Upgrading or rolling back

```bash
# Edit ARMARIUM_VERSION in .env, then:
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

Both services use the same named volume (`app_data`) regardless of image
version, so your database, covers, and backups are preserved across upgrades.
Run a backup first (see below) before upgrading across major versions.

## Backups

Same as the source-build setup — see the root
[README.md "Backups"](../README.md#backups) section: trigger via the admin
panel or `POST /api/v1/library/backup`, and snapshot the whole `app_data`
volume for a full backup including covers and uploaded assets.

## Reverse proxy / HTTPS

Armarium's PWA features (installable app, offline browsing) require HTTPS.
Put a TLS-terminating reverse proxy (Caddy, nginx, Traefik, or your existing
ingress) in front of the `frontend` service's published port, and leave
`COOKIE_SECURE=true` (the default) so the login cookie is sent only over
HTTPS. Only set `COOKIE_SECURE=false` for plain-HTTP internal-network
deployments — PWA install/offline features won't be available in that case.
