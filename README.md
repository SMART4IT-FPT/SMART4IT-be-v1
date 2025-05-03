# SMART4IT Backend

A FastAPI-based backend service for the SMART4IT platform, providing API endpoints for project management, CV processing, and position tracking.

## Features

- Project management and tracking
- CV processing and analysis
- Position management
- Dashboard statistics and analytics
- User authentication and authorization
- File handling and storage

## Tech Stack

- **Framework**: FastAPI
- **Database**: Firestore Database
- **Storage**: Firebase Storage
- **API Documentation**: FastAPI's built-in Swagger UI

## Prerequisites

- Python
- Firebase project with Firestore and Storage enabled
- Google Cloud credentials

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:


## Running the Application

1. Start the development server:
```bash
python main.py
```

2. Access the API documentation at:
```
http://localhost:7860
```

## Docker Support

The project includes Docker support for containerized deployment:

1. Build the Docker image:
```bash
docker build -t smart4it-backend .
```

2. Run the container:
```bash
docker run -p 7860:7860 smart4it-backend
```