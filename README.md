# Jenkins Debug Service

A FastAPI-based service for analyzing and debugging Jenkins test results. This service processes test results, provides failure analysis, and offers solutions for common test failures.

## Features

- Test result analysis and processing
- Failure pattern detection
- Automated solution suggestions
- Historical test result tracking
- RESTful API endpoints for test result management
- PostgreSQL database for persistent storage
- Docker containerization for easy deployment

## Prerequisites

- Docker and Docker Compose
- Python 3.11 or higher (for local development)
- PostgreSQL (handled by Docker for production)

## Quick Start

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd jenkins-debug-service
   ```

2. Create and configure environment variables:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with your configuration:
   ```
   DB_USER=postgres
   DB_PASSWORD=your_secure_password
   DB_NAME=jenkins_debug
   DB_SCHEMA=public
   ENVIRONMENT=dev
   GOOGLE_API_KEY=your_google_api_key
   ```

3. Start the services using Docker Compose:
   ```bash
   docker compose up --build
   ```

4. Access the API at `http://localhost:8000`

## API Endpoints

### Test Results

- `POST /result/upload`: Upload test results for analysis
  - Accepts multiple test result files
  - Returns analysis and solutions for failures

### Health Check

- `GET /health`: Check service health status

## Development Setup

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the development server:
   ```bash
   uvicorn app.main:app --reload
   ```

## Database Schema

The service uses PostgreSQL with the following main tables:

### TestResult
- `test_name` (Primary Key): Name of the test
- `total_tests`: Total number of tests
- `passed`: Number of passed tests
- `failed`: Number of failed tests
- `fail_percentage`: Percentage of failed tests
- `failure_details`: JSON array of failure details
- `analysis`: JSON object containing causes and solutions
- `last_updated`: Timestamp of last update
- `is_active`: Boolean indicating if the test is active
- `version`: Version number for tracking changes
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

## Docker Services

The application is containerized using Docker with two main services:

1. **PostgreSQL Service**
   - Version: 15
   - Port: 5432
   - Persistent storage using Docker volumes
   - Health checks enabled

2. **FastAPI Service**
   - Python 3.11
   - Port: 8000
   - Hot-reload enabled for development
   - Non-root user for security

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| DB_USER | Database username | postgres |
| DB_PASSWORD | Database password | - |
| DB_NAME | Database name | jenkins_debug |
| DB_SCHEMA | Database schema | public |
| DB_ENDPOINT | Database host | localhost |
| DB_PORT | Database port | 5432 |
| ENVIRONMENT | Environment (dev/prod) | dev |
| GOOGLE_API_KEY | Google API key for analysis | - |

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Testing

Run tests using pytest:
```bash
pytest
```

## License

[Add your license information here]

## Support

[Add support information here]
