# Micro Queue Starter Project

A template for creating a Celery-powered task queue with FastAPI, supporting GPU-based workloads, billing tracking, and type-safe code.

## Features

- Task Queue: Celery-powered queue with Redis as the broker.
- FastAPI: Provides an API to enqueue tasks and monitor their status.
- Billing Tracking: Tracks costs for tasks with a customizable decorator.
- Docker Support: Easily run the project with Docker Compose.
- Development Tools:
- Ruff: Linting and formatting.
- Mypy: Static type checking.
- Pytest: Functional and unit testing.

## Requirements

- Python: 3.10 or later
- Redis: Running Redis instance for Celery
- Docker: Optional, for containerized development

## Installation

1.	Clone the repository:

```bash
git clone https://github.com/your-repo/micro-queue-template.git
cd micro-queue-template
```

2.	Install dependencies:

```bash
uv install
```

3.	Set up the environment variables:

- Create a .env file in the project root:

```bash
touch .env
```

- Add the following variables to .env:

```ini
REDIS_URL=redis://localhost:6379/0
API_KEYS=default_api_key
```

## Usage

### Running the Worker

The Celery worker processes tasks enqueued via the API. Start the worker with:

```bash
uv run python -m app.worker
```

### Running the API

The FastAPI app provides endpoints for task management. Start the API with:

```bash
uv run main.py
```

### Functional Tests

Run functional tests to verify that the API and worker are working correctly:

```bash
pytest
```

### Code Formatting

Format the codebase with Ruff:

```bash
ruff format .
```

### Linting

Check for linting issues:

```bash
ruff check .
```

Fix optional linting issues:

```bash
ruff check --fix .
```

### Type Checking

Run the type checker with Mypy:

```bash
mypy .
```

## Docker Support

### Build the Docker Image

To build the Docker image:

```bash
docker compose build
```

### Run the Application

Run the application using Docker Compose:

```bash
docker compose up -d
```

This will start:

- The API server on http://localhost:8000
- The Celery worker

### Stop the Application

Stop all running containers:

```bash
docker compose down
```

## Project Structure

```
micro-queue-template/
├── app/
│   ├── auth.py              # API key authentication logic
│   ├── billing.py           # Billing tracking logic
│   ├── tasks.py             # Celery task definitions
│   ├── settings.py          # Application configuration
│   ├── worker.py            # Celery worker entrypoint
│   └── __init__.py
├── fixtures/
│   └── users.json           # User data for authentication
├── main.py                  # FastAPI entrypoint
├── celery_app.py            # Celery app configuration
├── test_api.py              # Functional tests
├── pyproject.toml           # Project configuration
├── .env                     # Environment variables
├── .pre-commit-config.yaml  # Pre-commit hook configuration
├── Dockerfile               # Docker image configuration
├── docker-compose.yml       # Docker Compose configuration
└── README.md                # Project documentation
```

## API Endpoints

### Enqueue a Task

__POST /enqueue-task__

__Description:__ Submit a new GPU task.
__Headers:__
    - X-API-Key: API key for authentication.
__Body:__

```json
{
  "data": {
    "image": "example_image_data",
    "model": "resnet50"
  }
}
```

__Response:__

```json
{
  "task_id": "12345678-1234-5678-1234-567812345678",
  "status": "queued"
}
```

### Check Task Status

__GET /task-status/{task_id}__

__Description:__ Check the status of a submitted task.
__Headers:__
    - X-API-Key: API key for authentication.

__Response:__

```json
{
  "task_id": "12345678-1234-5678-1234-567812345678",
  "status": "SUCCESS",
  "result": {
    "status": "success",
    "processed_data": {
      "image": "example_image_data",
      "model": "resnet50"
    }
  }
}
```

### Stream Task Status

__GET /task-status/stream/{task_id}__

__Description:__ Stream real-time updates for task status.
__Headers:__
- X-API-Key: API key for authentication.

__Response:__

```
data: PENDING

data: STARTED

data: SUCCESS
```

## Contributing

1.	Fork the repository.
2.	Create a feature branch:

```bash
git checkout -b feature-name
```

3.	Commit your changes:

```bash
git commit -m "Add feature-name"
```

4.	Push your branch and submit a pull request.

## License

This project is licensed under the MIT License. See the LICENSE file for details.
