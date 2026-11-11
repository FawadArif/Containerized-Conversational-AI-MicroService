# UniSolveBot: Containerized Conversational AI Microservice & Cloud Testbed

A decoupled, multi-container conversational AI microservice combining a Flask web/authentication gateway with a Rasa NLU inference engine. The system is orchestrated via Docker Compose, benchmarked for concurrent tail-latency behavior, and deployed to AWS Elastic Container Registry (ECR) using Infrastructure as Code (Terraform).

## System Architecture & Engineering Highlights

UniSolveBot separates stateful user session management from CPU-bound NLU inference across isolated containers communicating over an internal Docker bridge network:

* **Decoupled Microservice Topology:** Separates the Flask HTTP gateway (port 5000) from the Rasa NLU/Dialogue inference server (port 5005) to isolate web traffic from model execution.
* **Declarative Cloud Provisioning (IaC):** Provisions AWS ECR repositories and image mutability policies via Terraform rather than manual console configuration.
* **Concurrency & Tail-Latency Benchmarking:** Includes a zero-dependency Python load generator (`benchmark.py`) to profile request throughput saturation and p50/p95/p99 tail latency across concurrency tiers.
* **Stateful Session & Auth Management:** Implements bcrypt password hashing, Flask session management, and SQLAlchemy ORM backed by SQLite.

```text
[Client Browser / Load Generator]
               |
               v  (HTTP :5000)
+----------------------------------------------+
| Flask Gateway Container (rasa-flask)         |
| - Session Auth (bcrypt) & SQLAlchemy/SQLite  |
| - Asynchronous REST Proxy (/webhook)         |
+----------------------------------------------+
               |
               v  (Docker Internal DNS :5005)
+----------------------------------------------+
| Rasa Inference Container (rasa-rasa)         |
| - NLU Pipeline & Dialogue Policies           |
| - Packaged Custom Domain Model               |
+----------------------------------------------+
```

## System Performance & Tail-Latency Benchmark

To evaluate container serving capacity and queuing behavior under concurrent load, the microservice was benchmarked in GitHub Codespaces using `benchmark.py` across concurrency tiers from 1 to 50 concurrent workers (100 requests per tier following 5 warm-up requests).

| Concurrency | Throughput | p50 Latency | p95 Latency | p99 Latency |
|---|---|---|---|---|
| 1 worker | 47.89 req/s | 19.2 ms | 28.8 ms | 33.2 ms |
| 10 workers | 43.30 req/s | 226.0 ms | 266.8 ms | 307.6 ms |
| 25 workers | 44.06 req/s | 565.9 ms | 585.5 ms | 592.4 ms |
| 50 workers | 36.97 req/s | 1249.8 ms | 1480.9 ms | 1485.0 ms |

**Key Systems Observations:**
* **Throughput Saturation & Contention:** Single-container throughput saturates immediately at 47.89 req/s with 1 worker. Scaling concurrency beyond 10 workers introduces CPU context-switching and worker contention, reducing effective throughput to 36.97 req/s at 50 workers.
* **Tail-Latency Amplification:** Following Little's Law, ingress request queuing at 50 concurrent workers drives a 44.7x increase in p99 tail latency (from 33.2 ms to 1485.0 ms), demonstrating the need for horizontal container scaling and congestion-aware admission control under bursty workloads.

## Tech Stack

* **Application Gateway:** Python, Flask, Jinja2
* **AI / NLU Engine:** Rasa Open Source (NLU & Core Dialogue)
* **Database & Auth:** SQLite, SQLAlchemy ORM, bcrypt
* **Containerization & Orchestration:** Docker, Docker Compose
* **Infrastructure as Code & Cloud:** Terraform, AWS Elastic Container Registry (ECR)
* **Benchmarking & Runtime:** Python `concurrent.futures`, Linux, GitHub Codespaces

## Project Structure

```text
Containerized-Conversational-AI-MicroService/
|-- Flask/
|   |-- app.py                  # Flask routes, auth, DB models, Rasa REST proxy
|   |-- templates/              # HTML views (login, register, dashboard, chat)
|   |-- static/                 # Stylesheets and static assets
|-- data/                       # Rasa NLU training data (nlu.yml, stories.yml, rules.yml)
|-- actions/                    # Custom Rasa action server definitions
|-- infrastructure/
|   |-- main.tf                 # Declarative Terraform configuration for AWS ECR
|-- tests/                      # Automated test suites
|-- screenshots/                # Deployment and runtime verification captures
|-- benchmark.py                # Concurrent load generator & tail-latency profiler
|-- domain.yml                  # Rasa intents, entities, and response templates
|-- config.yml                  # NLU pipeline and policy configuration
|-- credentials.yml             # REST channel credentials
|-- endpoints.yml               # Action and tracker store endpoints
|-- Dockerfile.flask            # Flask gateway container build instructions
|-- Dockerfile.rasa             # Rasa inference container build instructions
|-- docker-compose.yml          # Multi-container orchestration specification
|-- README.md
```

## Infrastructure as Code (Terraform)

The AWS ECR repository is provisioned declaratively in `infrastructure/main.tf`:

```hcl
resource "aws_ecr_repository" "unisolvebot" {
  name                 = "unisolvebot"
  image_tag_mutability = "MUTABLE"
}
```

To initialize and provision the cloud registry:

```bash
cd infrastructure
terraform init
terraform plan
terraform apply
```

## Local Reproduction & Benchmarking

Clone the repository and launch the multi-container stack via Docker Compose:

```bash
git clone [https://github.com/FawadArif/Containerized-Conversational-AI-MicroService.git](https://github.com/FawadArif/Containerized-Conversational-AI-MicroService.git)
cd Containerized-Conversational-AI-MicroService

docker compose up -d --build
```

Once the containers are running (web UI on `http://localhost:5000` and Rasa REST API on `http://localhost:5005`), run the concurrency benchmark suite:

```bash
python3 benchmark.py
```

## Cloud Registry Deployment (AWS ECR)

Tag and push the built container images to AWS ECR:

```bash
docker tag rasa-flask:latest <aws_account_id>.dkr.ecr.<region>[.amazonaws.com/unisolvebot:flask-latest](https://.amazonaws.com/unisolvebot:flask-latest)
docker tag rasa-rasa:latest <aws_account_id>.dkr.ecr.<region>[.amazonaws.com/unisolvebot:rasa-latest](https://.amazonaws.com/unisolvebot:rasa-latest)

docker push <aws_account_id>.dkr.ecr.<region>[.amazonaws.com/unisolvebot:flask-latest](https://.amazonaws.com/unisolvebot:flask-latest)
docker push <aws_account_id>.dkr.ecr.<region>[.amazonaws.com/unisolvebot:rasa-latest](https://.amazonaws.com/unisolvebot:rasa-latest)
```

## Verification Screenshots

### Multi-Container Orchestration (Docker Compose)
![Docker Compose Running](screenshots/Running.png)

### Cloud Registry Deployment (AWS ECR)
![AWS ECR](screenshots/Aws_ECR.png)

### Live Conversational Interface
![Chat Page](screenshots/chat_page.png)
## Author
``` 
Fawad Arif — DevOps Engineer
LinkedIn: www.linkedin.com/in/fawad-ar1f
GitHub: https://github.com/FawadArif
```
