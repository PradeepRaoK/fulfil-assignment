# Product Importer

A FastAPI-based product management application with CSV import and webhook support. This project uses **PostgreSQL**, **Redis**, **Celery**, and **Docker Compose** for local development and testing.

---

## Prerequisites

Make sure you have the following installed:

- [Docker](https://docs.docker.com/get-docker/) (v20+)
- [Docker Compose](https://docs.docker.com/compose/install/) (v2+)
- Git (optional, if cloning the repo)

---

## Installation

1. Clone the repository:

```bash
git clone <your-repo-url>
cd <repo-folder>
docker-compose up --build
```

2. Check localhost:8000

3. Stopping Services
```
docker-compose down -v
```