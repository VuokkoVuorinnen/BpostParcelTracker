import requests
import logging
import json
import os
from flask import Flask, jsonify, render_template, request

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Constants
CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "item_id": "",
    "postal_code": "",
    "ntfy_url": "",
    "ntfy_token": "",
    "notified_proximity": False,
    "notified_delivered": False
}

def send_notification(message, url, token):
    if not url or not token:
        return

    try:
        headers = {"Authorization": f"Bearer {token}"}
        requests.post(url, data=message.encode(encoding='utf-8'), headers=headers)
        logger.info(f"Notification sent: {message}")
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")

def load_config():
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, 'r') as f:
            loaded_config = json.load(f)
            # Merge with defaults to ensure all keys exist
            config = DEFAULT_CONFIG.copy()
            config.update(loaded_config)
            return config
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return DEFAULT_CONFIG

def save_config(config):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving config: {e}")

@app.route('/')
def index():
    config = load_config()
    return render_template('index.html', config=config)

@app.route('/api/config', methods=['POST'])
def update_config():
    data = request.json
    new_item_id = data.get('item_id')
    new_postal_code = data.get('postal_code')
    new_ntfy_url = data.get('ntfy_url', '')
    new_ntfy_token = data.get('ntfy_token', '')
    
    if not new_item_id or not new_postal_code:
        return jsonify({"error": "Missing item_id or postal_code"}), 400
        
    config = {
        "item_id": new_item_id,
        "postal_code": new_postal_code,
        "ntfy_url": new_ntfy_url,
        "ntfy_token": new_ntfy_token,
        "notified_proximity": False,
        "notified_delivered": False
    }
    save_config(config)
    
    logger.info(f"Configuration updated: {config}")
    return jsonify({"success": True, "config": config})

@app.route('/api/status')
def get_status():
    try:
        config = load_config()
        item_id = config.get("item_id")
        postal_code = config.get("postal_code")
        ntfy_url = config.get("ntfy_url")
        ntfy_token = config.get("ntfy_token")
        
        api_url = f"https://track.bpost.cloud/track/itemonroundstatus?itemIdentifier={item_id}&postalCode={postal_code}"
        
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()
        
        # Handle "Delivered" state where API returns an error or missing status
        if data.get("error") == "No round status info can be rendered" or data.get('itemOnRoundStatus') is None:
            logger.info(f"Package {item_id} appears delivered (API returned error/null).")
            
            if not config.get("notified_delivered"):
                send_notification(f"✅ Package {item_id} has been delivered!", ntfy_url, ntfy_token)
                config["notified_delivered"] = True
                save_config(config)
            
            return jsonify({
                "stops_remaining": 0,
                "progress_percent": 100,
                "eta_minutes": 0,
                "driver_location": None,
                "user_location": None
            })

        status = data.get('itemOnRoundStatus', {})
        
        # Extract basic info
        stops_remaining = int(status.get('nrOfStopsUntilTarget', [0])[0])
        progress = float(status.get('progressUntilTarget', [0])[0]) * 100
        
        # Locations
        # Note: API returns arrays like ["4.268563"], so we take index 0
        driver_loc = status.get('lastKnownLocation', [{}])[0]
        target_loc = status.get('targetLocation', [{}])[0]
        
        driver_lat = float(driver_loc.get('lat', [0])[0])
        driver_lng = float(driver_loc.get('long', [0])[0])
        
        target_lat = float(target_loc.get('lat', [0])[0])
        target_lng = float(target_loc.get('long', [0])[0])

        # Calculate ETA (Assumption: 3 minutes per stop)
        minutes_remaining = stops_remaining * 3

        logger.info(f"Update for {item_id}: {stops_remaining} stops away, ETA {minutes_remaining}m, "
                    f"Driver at ({driver_lat}, {driver_lng}), Progress {progress:.1f}%")
        
        # Check for notification trigger
        if stops_remaining <= 5 and stops_remaining > 0 and not config.get("notified_proximity"):
            send_notification(f"📦 Bpost parcel is close! {stops_remaining} stops away (~{minutes_remaining} min).", ntfy_url, ntfy_token)
            config["notified_proximity"] = True
            save_config(config)
        elif stops_remaining == 0 and not config.get("notified_delivered"):
            send_notification(f"✅ Package {item_id} has been delivered!", ntfy_url, ntfy_token)
            config["notified_delivered"] = True
            save_config(config)
        elif stops_remaining > 5 and (config.get("notified_proximity") or config.get("notified_delivered")):
            # Reset flags if package moves back to > 5 stops (e.g. data correction)
            config["notified_proximity"] = False
            config["notified_delivered"] = False
            save_config(config)
        
        return jsonify({
            "stops_remaining": stops_remaining,
            "progress_percent": progress,
            "eta_minutes": minutes_remaining,
            "driver_location": {"lat": driver_lat, "lng": driver_lng},
            "user_location": {"lat": target_lat, "lng": target_lng}
        })

    except Exception as e:
        logger.error(f"Error fetching status: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
