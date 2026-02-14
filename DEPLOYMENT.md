# Deployment Guide

This guide explains how to set up and run the YouTube Clipper application on a Virtual Private Server (VPS).

## Prerequisites

Assuming you are using a Linux VPS (e.g., Ubuntu 20.04/22.04).

### 1. Install System Dependencies
You need properly installed Python, Node.js, FFmpeg, and some specific libraries for OpenCV.

### 1. Install System Dependencies

#### Option A: Docker (Recommended - Easiest)
You only need Docker and Docker Compose.
```bash
# Install Docker
sudo apt update
sudo apt install -y docker.io docker-compose
sudo usermod -aG docker $USER
newgrp docker
```

#### Option B: Manual Installation
If you prefer running without Docker, install these dependencies:
```bash
# 1. Update system & Install curl
sudo apt update && sudo apt install -y curl

# 2. Add NodeSource repository (for Node.js v20)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -

# 3. Install Node.js, FFmpeg, and Python deps
sudo apt install -y nodejs ffmpeg python3 python3-pip python3-venv libsm6 libxext6
```

## Deployment

### Method 1: Docker (Recommended)

1.  **Build and Run:**
    From the root of the project (where `docker-compose.yml` is):
    ```bash
    docker-compose up -d --build
    ```

2.  **View Logs:**
    ```bash
    docker-compose logs -f
    ```

3.  **Stop:**
    ```bash
    docker-compose down
    ```

### Method 2: Manual Setup (Legacy)

## Backend Setup (Python)
...

1.  **Navigate to the backend directory:**
    ```bash
    cd backend
    ```

2.  **Create a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the backend:**
    You can run it manually for testing:
    ```bash
    uvicorn main:app --host 0.0.0.0 --port 8000
    ```
    
    For a persistent background process, use `nohup` or create a systemd service.
    ```bash
    # Simple background run
    nohup uvicorn main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
    ```

## Frontend Setup (Next.js)

1.  **Navigate to the frontend directory:**
    ```bash
    cd ../frontend
    ```

2.  **Install dependencies:**
    ```bash
    npm install
    ```

3.  **Build the application:**
    ```bash
    npm run build
    ```

4.  **Run the frontend:**
    ```bash
    npm start
    ```
    By default, this runs on port 3000.

    For a persistent background process, use `pm2` (recommended) or `nohup`.
    ```bash
    # Install pm2 globally
    sudo npm install -g pm2
    
    # Start app
    pm2 start npm --name "frontend" -- start
    ```

## Accessing the Application

-   **Frontend:** Open your local browser and visit `http://<YOUR_VPS_IP>:8080`.
-   **Backend API:** Request sent to `http://<YOUR_VPS_IP>:8000`.

**Note:** Ensure your VPS firewall allows traffic on ports 8080 and 8000.
```bash
sudo ufw allow 8080
sudo ufw allow 8000
```
