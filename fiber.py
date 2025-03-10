from flask import Flask, request, jsonify, render_template, redirect, url_for
import numpy as np
import os
import json
import time
import uuid
import hmac
import hashlib
from datetime import datetime
from functools import wraps
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
API_SECRET = os.environ.get('API_SECRET', 'your-secret-key-change-this')
DB_PATH = os.environ.get('DB_PATH', 'fiber_measurements.db')

# Email configuration
EMAIL_ENABLED = os.environ.get('EMAIL_ENABLED', 'false').lower() == 'true'
EMAIL_SERVER = os.environ.get('EMAIL_SERVER', 'mail.vrt.rw')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'true').lower() == 'true'
EMAIL_USERNAME = os.environ.get('EMAIL_USERNAME', 'info@vrt.rw')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', 'TheGreat@123!')
EMAIL_FROM = os.environ.get('EMAIL_FROM', 'info@vrt.rw')
EMAIL_TO = os.environ.get('EMAIL_TO', 'nepobutata@gmail.com').split(',')
EMAIL_SUBJECT_PREFIX = os.environ.get('EMAIL_SUBJECT_PREFIX', '[Fiber Optic Alert]')

# Notification settings
NOTIFICATION_COOLDOWN = int(os.environ.get('NOTIFICATION_COOLDOWN', '3600'))  # seconds
last_notification_time = {}  # device_id -> timestamp

# Database setup
def init_db():
    """Initialize the SQLite database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS devices (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        api_key TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        alert_threshold REAL DEFAULT 0.7,
        alert_email TEXT,
        last_alert_sent TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS measurements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        signal_power REAL NOT NULL,
        attenuation REAL NOT NULL,
        distance REAL NOT NULL,
        fault_type TEXT NOT NULL,
        confidence REAL NOT NULL,
        notification_sent BOOLEAN DEFAULT 0,
        FOREIGN KEY (device_id) REFERENCES devices (id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id TEXT NOT NULL,
        measurement_id INTEGER NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        fault_type TEXT NOT NULL,
        recipients TEXT NOT NULL,
        status TEXT NOT NULL,
        error_message TEXT,
        FOREIGN KEY (device_id) REFERENCES devices (id),
        FOREIGN KEY (measurement_id) REFERENCES measurements (id)
    )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("Database initialized")

# Initialize database on startup
init_db()

# Simple rule-based model
def predict_fault(signal_power, attenuation, distance):
    """
    Simple rule-based model that doesn't require training
    Based on the patterns in our synthetic data
    """
    # Initialize probabilities
    probabilities = {
        'No Fault': 0.0,
        'Fiber Break': 0.0,
        'High Loss': 0.0,
        'Splice Loss': 0.0
    }
    
    # Fiber Break: Very low signal power, high attenuation
    if signal_power < -40 and attenuation > 1.5:
        probabilities['Fiber Break'] = 0.85
        probabilities['High Loss'] = 0.10
        probabilities['Splice Loss'] = 0.03
        probabilities['No Fault'] = 0.02
    # High Loss: Moderate-low signal power, moderate-high attenuation
    elif signal_power < -30 and signal_power >= -40 and attenuation > 1.0:
        probabilities['High Loss'] = 0.75
        probabilities['Fiber Break'] = 0.15
        probabilities['Splice Loss'] = 0.08
        probabilities['No Fault'] = 0.02
    # Splice Loss: Moderate signal power, low-moderate attenuation
    elif signal_power < -20 and signal_power >= -30 and attenuation > 0.5 and attenuation <= 1.5:
        probabilities['Splice Loss'] = 0.70
        probabilities['High Loss'] = 0.15
        probabilities['No Fault'] = 0.10
        probabilities['Fiber Break'] = 0.05
    # No Fault: Good signal power, low attenuation
    else:
        probabilities['No Fault'] = 0.85
        probabilities['Splice Loss'] = 0.10
        probabilities['High Loss'] = 0.04
        probabilities['Fiber Break'] = 0.01
    
    # Add some randomness to make it more realistic
    for key in probabilities:
        # Add random noise ±5%
        probabilities[key] += (np.random.random() * 0.1 - 0.05)
        # Ensure probabilities stay in valid range
        probabilities[key] = max(0, min(1, probabilities[key]))
    
    # Normalize probabilities to sum to 1
    total = sum(probabilities.values())
    for key in probabilities:
        probabilities[key] /= total
    
    # Find the most likely fault type
    prediction = max(probabilities, key=probabilities.get)
    confidence = probabilities[prediction]
    
    return prediction, probabilities, confidence

# Email notification function
def send_email_notification(device_id, device_name, fault_type, confidence, signal_power, attenuation, distance, measurement_id, recipients):
    """Send email notification about a detected fault"""
    if not EMAIL_ENABLED or not EMAIL_USERNAME or not EMAIL_PASSWORD:
        logger.warning("Email notifications are disabled or not configured")
        return False, "Email notifications are disabled or not configured"
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = EMAIL_FROM
        msg['To'] = ", ".join(recipients)
        msg['Subject'] = f"{EMAIL_SUBJECT_PREFIX} {fault_type} Detected on {device_name}"
        
        # Email body
        body = f"""
        <html>
        <body>
            <h2>Fiber Optic Fault Alert</h2>
            <p>A potential issue has been detected in your fiber optic network.</p>
            
            <h3>Alert Details:</h3>
            <ul>
                <li><strong>Device:</strong> {device_name} ({device_id})</li>
                <li><strong>Fault Type:</strong> <span style="color: red; font-weight: bold;">{fault_type}</span></li>
                <li><strong>Confidence:</strong> {confidence:.1%}</li>
                <li><strong>Time Detected:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li>
            </ul>
            
            <h3>Measurements:</h3>
            <ul>
                <li><strong>Signal Power:</strong> {signal_power} dB</li>
                <li><strong>Attenuation:</strong> {attenuation} dB/km</li>
                <li><strong>Distance:</strong> {distance} m</li>
            </ul>
            
            <h3>Recommended Actions:</h3>
            <ul>
        """
        
        # Add recommendations based on fault type
        if fault_type == "Fiber Break":
            body += """
                <li>Immediately check for physical damage to the fiber</li>
                <li>Verify connectivity at both ends of the fiber link</li>
                <li>Prepare replacement fiber if necessary</li>
                <li>Use OTDR to locate the exact break point</li>
            """
        elif fault_type == "High Loss":
            body += """
                <li>Check for bends or stress points in the fiber</li>
                <li>Inspect connectors for damage or contamination</li>
                <li>Verify transmitter power levels</li>
                <li>Consider cleaning or replacing connectors</li>
            """
        elif fault_type == "Splice Loss":
            body += """
                <li>Inspect splice points for proper alignment</li>
                <li>Check for contamination at splice locations</li>
                <li>Consider re-splicing if loss is above acceptable threshold</li>
                <li>Verify splice protection is properly installed</li>
            """
        
        body += """
            </ul>
            
            <p>Please investigate this issue promptly to prevent service disruption.</p>
            
            <p style="color: gray; font-size: 0.8em;">This is an automated message from the Fiber Optic Fault Detection System. 
            Do not reply to this email.</p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        # Connect to server and send
        server = smtplib.SMTP(EMAIL_SERVER, EMAIL_PORT)
        if EMAIL_USE_TLS:
            server.starttls()
        server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Email notification sent for device {device_id}, fault: {fault_type}")
        
        # Record notification in database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO notifications 
        (device_id, measurement_id, fault_type, recipients, status)
        VALUES (?, ?, ?, ?, ?)
        ''', (device_id, measurement_id, fault_type, json.dumps(recipients), 'sent'))
        
        # Update measurement to mark notification as sent
        cursor.execute('''
        UPDATE measurements
        SET notification_sent = 1
        WHERE id = ?
        ''', (measurement_id,))
        
        # Update device last alert time
        cursor.execute('''
        UPDATE devices
        SET last_alert_sent = ?
        WHERE id = ?
        ''', (datetime.now().isoformat(), device_id))
        
        conn.commit()
        conn.close()
        
        return True, "Email notification sent successfully"
        
    except Exception as e:
        error_message = str(e)
        logger.error(f"Failed to send email notification: {error_message}")
        
        # Record failed notification
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
            INSERT INTO notifications 
            (device_id, measurement_id, fault_type, recipients, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (device_id, measurement_id, fault_type, json.dumps(recipients), 'failed', error_message))
            conn.commit()
            conn.close()
        except Exception as db_error:
            logger.error(f"Failed to record notification error: {db_error}")
        
        return False, error_message

# Check if notification should be sent
def should_send_notification(device_id, fault_type, confidence):
    """Determine if a notification should be sent based on rules and cooldown period"""
    # Don't notify for "No Fault"
    if fault_type == "No Fault":
        return False
    
    # Check cooldown period
    current_time = time.time()
    if device_id in last_notification_time:
        time_since_last = current_time - last_notification_time[device_id]
        if time_since_last < NOTIFICATION_COOLDOWN:
            logger.info(f"Notification for device {device_id} skipped (cooldown period)")
            return False
    
    # Get device alert threshold
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT alert_threshold FROM devices WHERE id = ?', (device_id,))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return False
    
    alert_threshold = result[0]
    
    # Check if confidence exceeds threshold
    if confidence < alert_threshold:
        logger.info(f"Notification for device {device_id} skipped (below threshold: {confidence:.2f} < {alert_threshold:.2f})")
        return False
    
    return True

# Authentication decorator for API endpoints
def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({'error': 'API key is missing'}), 401
        
        # Check if API key exists in database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT id, name FROM devices WHERE api_key = ?', (api_key,))
        device = cursor.fetchone()
        conn.close()
        
        if not device:
            return jsonify({'error': 'Invalid API key'}), 401
        
        # Add device_id and device_name to request
        request.device_id = device[0]
        request.device_name = device[1]
        return f(*args, **kwargs)
    return decorated

# Routes
@app.route('/')
def home():
    """Render the home page"""
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    """Web UI endpoint for making predictions"""
    try:
        # Get data from request
        data = request.get_json()
        
        # Extract features
        signal_power = float(data['signal_power'])
        attenuation = float(data['attenuation'])
        distance = float(data['distance'])
        
        # Make prediction using rule-based model
        prediction, probabilities, confidence = predict_fault(signal_power, attenuation, distance)
        
        return jsonify({
            'prediction': prediction,
            'probabilities': probabilities,
            'confidence': confidence
        })
    
    except Exception as e:
        logger.error(f"Error in predict endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/api/measurements', methods=['POST'])
@require_api_key
def add_measurement():
    """API endpoint for IoT devices to submit measurements"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['signal_power', 'attenuation', 'distance']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Extract measurements
        signal_power = float(data['signal_power'])
        attenuation = float(data['attenuation'])
        distance = float(data['distance'])
        
        # Make prediction
        prediction, probabilities, confidence = predict_fault(signal_power, attenuation, distance)
        
        # Store measurement in database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO measurements 
        (device_id, signal_power, attenuation, distance, fault_type, confidence)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (request.device_id, signal_power, attenuation, distance, prediction, confidence))
        
        measurement_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Check if notification should be sent
        if should_send_notification(request.device_id, prediction, confidence):
            # Get notification recipients
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('SELECT alert_email FROM devices WHERE id = ?', (request.device_id,))
            result = cursor.fetchone()
            conn.close()
            
            device_email = result[0] if result and result[0] else None
            
            # Combine global recipients with device-specific recipient
            recipients = EMAIL_TO.copy()
            if device_email and device_email not in recipients:
                recipients.append(device_email)
            
            if recipients:
                # Send notification in a separate thread to avoid blocking
                notification_thread = threading.Thread(
                    target=send_email_notification,
                    args=(
                        request.device_id, 
                        request.device_name, 
                        prediction, 
                        confidence, 
                        signal_power, 
                        attenuation, 
                        distance, 
                        measurement_id,
                        recipients
                    )
                )
                notification_thread.start()
                
                # Update last notification time
                last_notification_time[request.device_id] = time.time()
        
        return jsonify({
            'id': measurement_id,
            'device_id': request.device_id,
            'timestamp': datetime.now().isoformat(),
            'signal_power': signal_power,
            'attenuation': attenuation,
            'distance': distance,
            'fault_type': prediction,
            'confidence': confidence
        })
    
    except Exception as e:
        logger.error(f"Error in add_measurement endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/api/measurements', methods=['GET'])
@require_api_key
def get_measurements():
    """API endpoint for IoT devices to retrieve their measurements"""
    try:
        # Get query parameters
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Get measurements from database
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # Return results as dictionaries
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT * FROM measurements
        WHERE device_id = ?
        ORDER BY timestamp DESC
        LIMIT ? OFFSET ?
        ''', (request.device_id, limit, offset))
        
        measurements = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify(measurements)
    
    except Exception as e:
        logger.error(f"Error in get_measurements endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/dashboard')
def dashboard():
    """Render the dashboard page"""
    return render_template('dashboard.html')

@app.route('/devices')
def devices():
    """Render the devices management page"""
    # Get all devices from database
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, created_at, alert_threshold, alert_email, last_alert_sent FROM devices')
    devices = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return render_template('devices.html', devices=devices)

@app.route('/devices/new', methods=['GET', 'POST'])
def new_device():
    """Create a new IoT device"""
    if request.method == 'POST':
        name = request.form.get('name')
        alert_email = request.form.get('alert_email', '')
        alert_threshold = request.form.get('alert_threshold', 0.7)
        
        try:
            alert_threshold = float(alert_threshold)
        except ValueError:
            alert_threshold = 0.7
        
        if not name:
            return render_template('new_device_notification.html', error='Device name is required')
        
        # Generate device ID and API key
        device_id = str(uuid.uuid4())
        api_key = generate_api_key()
        
        # Store device in database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO devices (id, name, api_key, alert_threshold, alert_email)
        VALUES (?, ?, ?, ?, ?)
        ''', (device_id, name, api_key, alert_threshold, alert_email))
        conn.commit()
        conn.close()
        
        return render_template('device_created_notification.html', 
                              device_id=device_id, 
                              api_key=api_key, 
                              name=name,
                              alert_email=alert_email,
                              alert_threshold=alert_threshold)
    
    return render_template('new_device_notification.html')

@app.route('/devices/<device_id>/edit', methods=['GET', 'POST'])
def edit_device(device_id):
    """Edit device settings"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if request.method == 'POST':
        name = request.form.get('name')
        alert_email = request.form.get('alert_email', '')
        alert_threshold = request.form.get('alert_threshold', 0.7)
        
        try:
            alert_threshold = float(alert_threshold)
        except ValueError:
            alert_threshold = 0.7
        
        if not name:
            cursor.execute('SELECT * FROM devices WHERE id = ?', (device_id,))
            device = dict(cursor.fetchone())
            conn.close()
            return render_template('edit_device.html', device=device, error='Device name is required')
        
        # Update device in database
        cursor.execute('''
        UPDATE devices 
        SET name = ?, alert_threshold = ?, alert_email = ?
        WHERE id = ?
        ''', (name, alert_threshold, alert_email, device_id))
        conn.commit()
        
        return redirect(url_for('devices'))
    
    # GET request - show edit form
    cursor.execute('SELECT * FROM devices WHERE id = ?', (device_id,))
    device = cursor.fetchone()
    conn.close()
    
    if not device:
        return redirect(url_for('devices'))
    
    return render_template('edit_device.html', device=dict(device))

@app.route('/notifications')
def notifications_list():
    """View notification history"""
    # Get all notifications from database
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT n.*, d.name as device_name
    FROM notifications n
    JOIN devices d ON n.device_id = d.id
    ORDER BY n.timestamp DESC
    LIMIT 100
    ''')
    
    notifications = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return render_template('notifications.html', notifications=notifications)

@app.route('/api/data/recent', methods=['GET'])
def get_recent_data():
    """Get recent measurements for dashboard"""
    try:
        # Get query parameters
        limit = request.args.get('limit', 100, type=int)
        
        # Get measurements from database
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT m.*, d.name as device_name
        FROM measurements m
        JOIN devices d ON m.device_id = d.id
        ORDER BY m.timestamp DESC
        LIMIT ?
        ''', (limit,))
        
        measurements = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify(measurements)
    
    except Exception as e:
        logger.error(f"Error in get_recent_data endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/api/data/stats', methods=['GET'])
def get_stats():
    """Get statistics for dashboard"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get device count
        cursor.execute('SELECT COUNT(*) as count FROM devices')
        device_count = cursor.fetchone()['count']
        
        # Get measurement count
        cursor.execute('SELECT COUNT(*) as count FROM measurements')
        measurement_count = cursor.fetchone()['count']
        
        # Get fault type distribution
        cursor.execute('''
        SELECT fault_type, COUNT(*) as count
        FROM measurements
        GROUP BY fault_type
        ''')
        fault_distribution = {row['fault_type']: row['count'] for row in cursor.fetchall()}
        
        # Get notification count
        cursor.execute('SELECT COUNT(*) as count FROM notifications')
        notification_count = cursor.fetchone()['count']
        
        # Get recent alerts (last 24 hours)
        cursor.execute('''
        SELECT COUNT(*) as count FROM notifications
        WHERE timestamp > datetime('now', '-1 day')
        ''')
        recent_alerts = cursor.fetchone()['count']
        
        conn.close()
        
        return jsonify({
            'device_count': device_count,
            'measurement_count': measurement_count,
            'fault_distribution': fault_distribution,
            'notification_count': notification_count,
            'recent_alerts': recent_alerts
        })
    
    except Exception as e:
        logger.error(f"Error in get_stats endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/api/test-email', methods=['POST'])
def test_email():
    """Test email configuration by sending a test email"""
    try:
        if not EMAIL_ENABLED or not EMAIL_USERNAME or not EMAIL_PASSWORD:
            return jsonify({'success': False, 'message': 'Email notifications are disabled or not configured'}), 400
        
        recipients = request.json.get('recipients', EMAIL_TO)
        if not recipients:
            return jsonify({'success': False, 'message': 'No recipients specified'}), 400
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = EMAIL_FROM
        msg['To'] = ", ".join(recipients)
        msg['Subject'] = f"{EMAIL_SUBJECT_PREFIX} Test Email"
        
        body = """
        <html>
        <body>
            <h2>Fiber Optic Fault Detector - Test Email</h2>
            <p>This is a test email from your Fiber Optic Fault Detection System.</p>
            <p>If you received this email, your notification system is configured correctly.</p>
            <p style="color: gray; font-size: 0.8em;">This is an automated message. Do not reply to this email.</p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        # Connect to server and send
        server = smtplib.SMTP(EMAIL_SERVER, EMAIL_PORT)
        if EMAIL_USE_TLS:
            server.starttls()
        server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Test email sent to {recipients}")
        
        return jsonify({'success': True, 'message': 'Test email sent successfully'})
        
    except Exception as e:
        error_message = str(e)
        logger.error(f"Failed to send test email: {error_message}")
        return jsonify({'success': False, 'message': f'Failed to send test email: {error_message}'}), 500

def generate_api_key():
    """Generate a secure API key"""
    # Create a random string
    random_bytes = os.urandom(32)
    # Create a hash using HMAC and SHA-256
    api_key = hmac.new(API_SECRET.encode(), random_bytes, hashlib.sha256).hexdigest()
    return api_key

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    # Use a single worker to reduce memory usage
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), threaded=True)