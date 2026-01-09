# Bpost Parcel Predictor

A Flask-based dashboard to track Bpost parcels, providing estimated stops remaining, location on a map, and notifications via ntfy.

## Features

- **Real-time Tracking**: Shows driver location and your location on a map.
- **Dynamic Updates**: Updates every 5 minutes by default, switching to every 1 minute when the package is less than 10 stops away.
- **Notifications**: Sends push notifications via [ntfy](https://ntfy.sh) when the package is 5 stops away and when it is delivered.
- **Dark Mode**: Fully dark-themed UI.
- **Responsive Design**: Works on desktop and mobile.

## Prerequisites

- Python 3.9+ (for local run)
- Docker & Docker Compose (for containerized run)
- A Bpost tracking number (Item ID) and Postal Code.

## Configuration

The application uses a `config.json` file to store settings. This file is automatically created on the first run if it doesn't exist, but for Docker, you should create it manually first to ensure proper file mounting.

**config.json** structure:
```json
{
    "item_id": "YOUR_TRACKING_ID",
    "postal_code": "YOUR_POSTAL_CODE",
    "ntfy_url": "https://ntfy.sh/your-topic",
    "ntfy_token": "YOUR_NTFY_TOKEN",
    "notified_proximity": false,
    "notified_delivered": false
}
```

> **Note**: `notified_proximity` and `notified_delivered` are internal flags to prevent duplicate notifications and are managed by the app.

## Running Locally

1.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Run the application**:
    ```bash
    python app.py
    ```

3.  Access the dashboard at `http://localhost:5000`.

## Running with Docker Compose

1.  **Ensure `config.json` exists**:
    If you haven't run the app locally, create a `config.json` file in the project root with your details (see Configuration above). Also create an empty `app.log` file to ensure permissions are correct when mounted.
    ```bash
    touch config.json app.log
    ```

2.  **Start the container**:
    ```bash
    docker-compose up -d --build
    ```

3.  Access the dashboard at `http://localhost:5000`.

4.  **View Logs**:
    ```bash
    docker-compose logs -f
    ```

## Usage

- **Settings**: Click the "⚙️ Settings" button in the top right to update the Tracking ID or Postal Code directly from the UI.
- **Notifications**: Ensure your ntfy URL and Token are set in `config.json` or updated via the Settings (if you add fields to the UI in the future, currently manual config edit is safest for the token).
