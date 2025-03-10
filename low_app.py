import subprocess
import os
import sys
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time
import glob
import json
import signal

class MinLinkCRAF19App:
    def __init__(self, root):
        self.root = root
        self.root.title("MinLink CRAF 19 Tool")
        
        # Set appropriate size for Raspberry Pi display
        self.root.geometry("800x480")
        self.root.minsize(640, 400)
        
        self.minlink_process = None
        self.connection_active = False
        self.config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "minlink_craf19_config.json")
        
        # Load saved configuration
        self.load_config()
        
        # Create main frame
        main_frame = ttk.Frame(root, padding="8")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create notebook for tabbed interface
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Connection tab
        connection_tab = ttk.Frame(notebook, padding=5)
        notebook.add(connection_tab, text="Connection")
        
        # CRAF 19 Settings tab
        craf_tab = ttk.Frame(notebook, padding=5)
        notebook.add(craf_tab, text="CRAF 19")
        
        # Advanced tab
        advanced_tab = ttk.Frame(notebook, padding=5)
        notebook.add(advanced_tab, text="Advanced")
        
        # Console tab
        console_tab = ttk.Frame(notebook, padding=5)
        notebook.add(console_tab, text="Console")
        
        # Status bar at the bottom
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=2)
        
        # Status indicator
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(status_frame, text="Status:")
        status_label.pack(side=tk.LEFT, padx=5)
        self.status_indicator = ttk.Label(status_frame, textvariable=self.status_var, font=("Arial", 10, "bold"))
        self.status_indicator.pack(side=tk.LEFT, padx=5)
        
        # Connection tab content
        # Device settings
        settings_frame = ttk.LabelFrame(connection_tab, text="USB Connection", padding="8")
        settings_frame.pack(fill=tk.X, pady=8)
        
        # USB Device with auto-detection
        ttk.Label(settings_frame, text="USB Device:").grid(row=0, column=0, sticky=tk.W, pady=8)
        self.device_var = tk.StringVar(value=self.config.get("device", "/dev/ttyUSB0"))
        device_combo = ttk.Combobox(settings_frame, textvariable=self.device_var, width=25)
        device_combo.grid(row=0, column=1, sticky=tk.W, padx=5)
        refresh_btn = ttk.Button(settings_frame, text="↻", width=3, command=self.refresh_devices)
        refresh_btn.grid(row=0, column=2, padx=2)
        
        # Populate device list initially
        self.refresh_devices(update_combo=device_combo)
        
        # Baud rate - CRAF 19 specific rates
        ttk.Label(settings_frame, text="Baud Rate:").grid(row=1, column=0, sticky=tk.W, pady=8)
        self.baud_var = tk.StringVar(value=self.config.get("baud_rate", "115200"))
        baud_combo = ttk.Combobox(settings_frame, textvariable=self.baud_var, width=10)
        baud_combo['values'] = ('9600', '19200', '38400', '57600', '115200', '230400', '460800', '921600')
        baud_combo.grid(row=1, column=1, sticky=tk.W, padx=5)
        
        # Connection buttons
        btn_frame = ttk.Frame(connection_tab)
        btn_frame.pack(fill=tk.X, pady=10)
        
        self.connect_button = ttk.Button(btn_frame, text="Connect CRAF 19", command=self.connect_minlink)
        self.connect_button.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)
        
        self.disconnect_button = ttk.Button(btn_frame, text="Disconnect", command=self.disconnect_minlink, state=tk.DISABLED)
        self.disconnect_button.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)
        
        # CRAF 19 tab content
        craf_frame = ttk.LabelFrame(craf_tab, text="CRAF 19 Protocol Settings", padding="8")
        craf_frame.pack(fill=tk.X, pady=8)
        
        # CRAF 19 Mode
        ttk.Label(craf_frame, text="CRAF Mode:").grid(row=0, column=0, sticky=tk.W, pady=8)
        self.craf_mode_var = tk.StringVar(value=self.config.get("craf_mode", "standard"))
        craf_mode_combo = ttk.Combobox(craf_frame, textvariable=self.craf_mode_var, width=15)
        craf_mode_combo['values'] = ('standard', 'extended', 'diagnostic', 'legacy')
        craf_mode_combo.grid(row=0, column=1, sticky=tk.W, padx=5)
        
        # CRAF 19 Channel
        ttk.Label(craf_frame, text="Channel:").grid(row=1, column=0, sticky=tk.W, pady=8)
        self.channel_var = tk.StringVar(value=self.config.get("channel", "1"))
        channel_combo = ttk.Combobox(craf_frame, textvariable=self.channel_var, width=5)
        channel_combo['values'] = tuple(str(i) for i in range(1, 17))  # Channels 1-16
        channel_combo.grid(row=1, column=1, sticky=tk.W, padx=5)
        
        # CRAF 19 Address
        ttk.Label(craf_frame, text="Device Address:").grid(row=2, column=0, sticky=tk.W, pady=8)
        self.address_var = tk.StringVar(value=self.config.get("address", "0x01"))
        ttk.Entry(craf_frame, textvariable=self.address_var, width=10).grid(row=2, column=1, sticky=tk.W, padx=5)
        
        # CRAF 19 Timeout
        ttk.Label(craf_frame, text="Timeout (ms):").grid(row=3, column=0, sticky=tk.W, pady=8)
        self.timeout_var = tk.StringVar(value=self.config.get("timeout", "1000"))
        ttk.Entry(craf_frame, textvariable=self.timeout_var, width=10).grid(row=3, column=1, sticky=tk.W, padx=5)
        
        # CRAF 19 Protocol Version
        ttk.Label(craf_frame, text="Protocol Version:").grid(row=4, column=0, sticky=tk.W, pady=8)
        self.protocol_var = tk.StringVar(value=self.config.get("protocol", "19"))
        protocol_combo = ttk.Combobox(craf_frame, textvariable=self.protocol_var, width=5)
        protocol_combo['values'] = ('17', '18', '19', '19.1')
        protocol_combo.grid(row=4, column=1, sticky=tk.W, padx=5)
        
        # CRAF 19 Command Buttons
        craf_cmd_frame = ttk.LabelFrame(craf_tab, text="CRAF 19 Commands", padding="8")
        craf_cmd_frame.pack(fill=tk.X, pady=8)
        
        # Create a grid of command buttons
        commands = [
            ("Initialize", self.cmd_initialize),
            ("Read Status", self.cmd_read_status),
            ("Calibrate", self.cmd_calibrate),
            ("Reset", self.cmd_reset),
            ("Diagnostics", self.cmd_diagnostics),
            ("Update Firmware", self.cmd_update_firmware)
        ]
        
        for i, (cmd_name, cmd_func) in enumerate(commands):
            col = i % 3
            row = i // 3
            ttk.Button(craf_cmd_frame, text=cmd_name, command=cmd_func).grid(
                row=row, column=col, padx=5, pady=5, sticky=tk.W+tk.E)
        
        # Advanced tab content
        adv_frame = ttk.LabelFrame(advanced_tab, text="Advanced Settings", padding="8")
        adv_frame.pack(fill=tk.X, pady=8)
        
        # GPIO reset pin
        ttk.Label(adv_frame, text="Reset GPIO Pin:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.reset_pin_var = tk.StringVar(value=self.config.get("reset_pin", ""))
        ttk.Entry(adv_frame, textvariable=self.reset_pin_var, width=5).grid(row=0, column=1, sticky=tk.W, padx=5)
        ttk.Button(adv_frame, text="Reset Device", command=self.reset_device).grid(row=0, column=2, padx=5)
        
        # Additional parameters
        ttk.Label(adv_frame, text="Additional Parameters:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.params_var = tk.StringVar(value=self.config.get("params", ""))
        ttk.Entry(adv_frame, textvariable=self.params_var, width=30).grid(row=1, column=1, columnspan=2, sticky=tk.W+tk.E, padx=5)
        
        # Debug mode
        self.debug_var = tk.BooleanVar(value=self.config.get("debug", False))
        ttk.Checkbutton(adv_frame, text="Enable Debug Mode", 
                        variable=self.debug_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Auto-start options
        autostart_frame = ttk.LabelFrame(advanced_tab, text="Startup Options", padding="8")
        autostart_frame.pack(fill=tk.X, pady=8)
        
        # Auto-connect on startup
        self.autoconnect_var = tk.BooleanVar(value=self.config.get("autoconnect", False))
        ttk.Checkbutton(autostart_frame, text="Auto-connect on startup", 
                        variable=self.autoconnect_var).grid(row=0, column=0, sticky=tk.W, pady=5)
        
        # Save settings button
        ttk.Button(advanced_tab, text="Save Settings", command=self.save_config).pack(pady=10)
        
        # Console tab content
        # Output console
        self.console = scrolledtext.ScrolledText(console_tab, wrap=tk.WORD, font=("Courier", 9))
        self.console.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.console.config(state=tk.DISABLED)
        
        # Console control buttons
        console_btn_frame = ttk.Frame(console_tab)
        console_btn_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=5)
        
        ttk.Button(console_btn_frame, text="Clear Console", command=self.clear_console).pack(side=tk.LEFT, padx=5)
        ttk.Button(console_btn_frame, text="Save Log", command=self.save_log).pack(side=tk.LEFT, padx=5)
        
        # Instructions
        self.write_to_console("MinLink CRAF 19 Connection Tool for Raspberry Pi\n")
        self.write_to_console("1. Select your USB device from the dropdown")
        self.write_to_console("2. Configure CRAF 19 protocol settings in the CRAF 19 tab")
        self.write_to_console("3. Click 'Connect CRAF 19' to establish connection")
        self.write_to_console("\nCRAF 19 Protocol Version: " + self.protocol_var.get())
        
        # Handle window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Auto-connect if configured
        if self.autoconnect_var.get():
            self.root.after(1000, self.connect_minlink)
    
    def load_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
            else:
                self.config = {}
        except Exception as e:
            self.config = {}
            print(f"Error loading config: {str(e)}")
    
    def save_config(self):
        try:
            config = {
                "device": self.device_var.get(),
                "baud_rate": self.baud_var.get(),
                "craf_mode": self.craf_mode_var.get(),
                "channel": self.channel_var.get(),
                "address": self.address_var.get(),
                "timeout": self.timeout_var.get(),
                "protocol": self.protocol_var.get(),
                "params": self.params_var.get(),
                "reset_pin": self.reset_pin_var.get(),
                "debug": self.debug_var.get(),
                "autoconnect": self.autoconnect_var.get()
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            messagebox.showinfo("Settings Saved", "CRAF 19 configuration has been saved successfully.")
            self.write_to_console("CRAF 19 configuration saved.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {str(e)}")
            self.write_to_console(f"Error saving configuration: {str(e)}")
    
    def refresh_devices(self, update_combo=None):
        try:
            # Find all USB serial devices on Raspberry Pi
            devices = []
            
            # Common USB serial device patterns
            for pattern in ['/dev/ttyUSB*', '/dev/ttyACM*', '/dev/serial/by-id/*']:
                devices.extend(glob.glob(pattern))
            
            # Update the combobox if provided
            if update_combo is not None and devices:
                update_combo['values'] = devices
                
                # Select the first device if none is selected
                if not self.device_var.get() and devices:
                    self.device_var.set(devices[0])
            
            return devices
        except Exception as e:
            self.write_to_console(f"Error refreshing devices: {str(e)}")
            return []
    
    def reset_device(self):
        try:
            reset_pin = self.reset_pin_var.get()
            if not reset_pin:
                messagebox.showinfo("Info", "No GPIO pin specified for reset.")
                return
                
            # Check if RPi.GPIO is available
            try:
                import RPi.GPIO as GPIO
                
                pin = int(reset_pin)
                self.write_to_console(f"Resetting CRAF 19 device using GPIO pin {pin}...")
                
                # Setup GPIO
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(pin, GPIO.OUT)
                
                # Toggle pin to reset
                GPIO.output(pin, GPIO.LOW)
                time.sleep(0.5)
                GPIO.output(pin, GPIO.HIGH)
                time.sleep(0.5)
                
                # Cleanup
                GPIO.cleanup(pin)
                
                self.write_to_console("CRAF 19 device reset complete.")
                
            except ImportError:
                messagebox.showerror("Error", "RPi.GPIO module not available. Cannot control GPIO pins.")
                self.write_to_console("Error: RPi.GPIO module not available. Cannot control GPIO pins.")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to reset device: {str(e)}")
            self.write_to_console(f"Error resetting device: {str(e)}")
    
    def write_to_console(self, text):
        self.console.config(state=tk.NORMAL)
        self.console.insert(tk.END, text + "\n")
        self.console.see(tk.END)
        self.console.config(state=tk.DISABLED)
    
    def clear_console(self):
        self.console.config(state=tk.NORMAL)
        self.console.delete(1.0, tk.END)
        self.console.config(state=tk.DISABLED)
    
    def save_log(self):
        try:
            log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
            os.makedirs(log_dir, exist_ok=True)
            
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            log_file = os.path.join(log_dir, f"craf19_log_{timestamp}.txt")
            
            with open(log_file, 'w') as f:
                f.write(self.console.get(1.0, tk.END))
            
            self.write_to_console(f"Log saved to {log_file}")
            
        except Exception as e:
            self.write_to_console(f"Error saving log: {str(e)}")
    
    def connect_minlink(self):
        if self.connection_active:
            return
        
        device = self.device_var.get()
        baud_rate = self.baud_var.get()
        craf_mode = self.craf_mode_var.get()
        channel = self.channel_var.get()
        address = self.address_var.get()
        timeout = self.timeout_var.get()
        protocol = self.protocol_var.get()
        params = self.params_var.get()
        debug = self.debug_var.get()
        
        if not device:
            messagebox.showerror("Error", "Please select a USB device")
            return
        
        try:
            # Construct the MinLink CRAF 19 command for Raspberry Pi
            script_dir = os.path.dirname(os.path.abspath(__file__))
            minlink_script = os.path.join(script_dir, "minlink.py")
            
            # Check if the script exists
            if not os.path.exists(minlink_script):
                # Try to find it in the parent directory (minlinker)
                minlink_script = os.path.join(os.path.dirname(script_dir), "minlink.py")
                if not os.path.exists(minlink_script):
                    messagebox.showerror("Error", "MinLink script not found. Please check the installation.")
                    return
            
            cmd = f"python3 {minlink_script}"
            cmd += f" --device {device} --baud {baud_rate} --mode {craf_mode}"
            cmd += f" --protocol craf{protocol} --channel {channel} --address {address} --timeout {timeout}"
            
            if debug:
                cmd += " --debug"
                
            if params:
                cmd += f" {params}"
            
            self.write_to_console(f"\nConnecting to MinLink CRAF 19...")
            self.write_to_console(f"Protocol Version: CRAF {protocol}")
            self.write_to_console(f"Command: {cmd}")
            
            # Start MinLink process
            self.minlink_process = subprocess.Popen(
                cmd, 
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                preexec_fn=os.setsid  # Use process group for proper termination
            )
            
            # Start threads to read output
            threading.Thread(target=self._read_output, args=(self.minlink_process.stdout, False), daemon=True).start()
            threading.Thread(target=self._read_output, args=(self.minlink_process.stderr, True), daemon=True).start()
            
            # Update UI
            self.connection_active = True
            self.status_var.set("Connected to CRAF 19")
            self.status_indicator.configure(foreground="green")
            self.connect_button.config(state=tk.DISABLED)
            self.disconnect_button.config(state=tk.NORMAL)
            
        except Exception as e:
            self.write_to_console(f"Error connecting to MinLink CRAF 19: {str(e)}")
            messagebox.showerror("Error", f"Failed to connect: {str(e)}")
    
    def _read_output(self, pipe, is_error):
        try:
            for line in pipe:
                if is_error:
                    self.write_to_console(f"ERROR: {line.strip()}")
                else:
                    self.write_to_console(line.strip())
        except Exception as e:
            self.write_to_console(f"Error reading output: {str(e)}")
    
    def disconnect_minlink(self):
        if not self.connection_active:
            return
        
        try:
            if self.minlink_process:
                # Kill the process group to ensure all child processes are terminated
                os.killpg(os.getpgid(self.minlink_process.pid), signal.SIGTERM)
                self.minlink_process = None
            
            # Update UI
            self.connection_active = False
            self.status_var.set("Ready")
            self.status_indicator.configure(foreground="black")
            self.connect_button.config(state=tk.NORMAL)
            self.disconnect_button.config(state=tk.DISABLED)
            
            self.write_to_console("\nDisconnected from MinLink CRAF 19.")
            
        except Exception as e:
            self.write_to_console(f"Error disconnecting: {str(e)}")
    
    # CRAF 19 Command Functions
    def cmd_initialize(self):
        if not self.connection_active:
            messagebox.showinfo("Info", "Please connect to CRAF 19 device first.")
            return
            
        self.write_to_console("\nSending Initialize command to CRAF 19 device...")
        # Here you would send the actual command to the device
        # This is a placeholder for the actual implementation
        self.write_to_console("CRAF 19 device initialized successfully.")
    
    def cmd_read_status(self):
        if not self.connection_active:
            messagebox.showinfo("Info", "Please connect to CRAF 19 device first.")
            return
            
        self.write_to_console("\nReading status from CRAF 19 device...")
        # Placeholder for actual implementation
        status_data = {
            "device_id": "CRAF19-001",
            "firmware": "v2.3.4",
            "status": "READY",
            "temperature": "32.5°C",
            "uptime": "01:23:45",
            "channel": self.channel_var.get(),
            "mode": self.craf_mode_var.get()
        }
        
        self.write_to_console("\nCRAF 19 Status:")
        for key, value in status_data.items():
            self.write_to_console(f"  {key}: {value}")
    
    def cmd_calibrate(self):
        if not self.connection_active:
            messagebox.showinfo("Info", "Please connect to CRAF 19 device first.")
            return
            
        if messagebox.askyesno("Calibrate", "Start CRAF 19 calibration process?"):
            self.write_to_console("\nStarting CRAF 19 calibration...")
            # Placeholder for actual implementation
            for i in range(5):
                self.write_to_console(f"Calibration step {i+1}/5...")
                time.sleep(0.5)  # Simulate calibration steps
            self.write_to_console("CRAF 19 calibration completed successfully.")
    
    def cmd_reset(self):
        if not self.connection_active:
            messagebox.showinfo("Info", "Please connect to CRAF 19 device first.")
            return
            
        if messagebox.askyesno("Reset", "Reset CRAF 19 device to factory defaults?"):
            self.write_to_console("\nResetting CRAF 19 device to factory defaults...")
            # Placeholder for actual implementation
            time.sleep(1)  # Simulate reset process
            self.write_to_console("CRAF 19 device has been reset to factory defaults.")
            self.write_to_console("Please disconnect and reconnect to apply changes.")
    
    def cmd_diagnostics(self):
        if not self.connection_active:
            messagebox.showinfo("Info", "Please connect to CRAF 19 device first.")
            return
            
        self.write_to_console("\nRunning CRAF 19 diagnostics...")
        # Placeholder for actual implementation
        diagnostics = [
            "Testing communication channel... OK",
            "Verifying protocol version... OK",
            "Checking device memory... OK",
            "Testing signal strength... 87%",
            "Verifying timing parameters... OK",
            "Checking error counters... 0 errors found"
        ]
        
        for line in diagnostics:
            self.write_to_console(line)
            time.sleep(0.3)  # Simulate diagnostics running
            
        self.write_to_console("\nCRAF 19 diagnostics completed. No issues found.")
    
    def cmd_update_firmware(self):
        if not self.connection_active:
            messagebox.showinfo("Info", "Please connect to CRAF 19 device first.")
            return
            
        if messagebox.askyesno("Update Firmware", "Start CRAF 19 firmware update process?\n\nWARNING: Do not disconnect the device during update."):
            self.write_to_console("\nPreparing for CRAF 19 firmware update...")
            # Placeholder for actual implementation
            progress_steps = ["Checking current firmware", "Downloading update package", 
                             "Verifying package integrity", "Backing up settings",
                             "Flashing firmware", "Verifying installation", 
                             "Restoring settings", "Restarting device"]
            
            for i, step in enumerate(progress_steps):
                self.write_to_console(f"[{i+1}/{len(progress_steps)}] {step}...")
                time.sleep(0.7)  # Simulate update process
                
            self.write_to_console("\nCRAF 19 firmware update completed successfully.")
            self.write_to_console("New firmware version: CRAF 19.1")
    
    def on_closing(self):
        if self.connection_active:
            if messagebox.askyesno("Quit", "Active CRAF 19 connection will be terminated. Are you sure you want to quit?"):
                self.disconnect_minlink()
                self.root.destroy()
        else:
            self.root.destroy()

if __name__ == "__main__":
    # Create a simple splash screen
    splash_root = tk.Tk()
    splash_root.overrideredirect(True)
    screen_width = splash_root.winfo_screenwidth()
    screen_height = splash_root.winfo_screenheight()
    
    # Position in the center of the screen
    width = 300
    height = 200
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    
    splash_root.geometry(f"{width}x{height}+{x}+{y}")
    
    # Add a label with the app name
    splash_label = tk.Label(splash_root, text="MinLink CRAF 19", font=("Arial", 18, "bold"))
    splash_label.pack(pady=30)
    
    # Add version info
    version_label = tk.Label(splash_root, text="Protocol Version 19", font=("Arial", 12))
    version_label.pack(pady=5)
    
    # Add a loading message
    loading_label = tk.Label(splash_root, text="Initializing...", font=("Arial", 10))
    loading_label.pack(pady=10)
    
    def main_app():
        splash_root.destroy()
        root = tk.Tk()
        app = MinLinkCRAF19App(root)
        root.mainloop()
    
    # Schedule the main app to appear after 1.5 seconds
    splash_root.after(1500, main_app)
    
    # Start the splash screen
    splash_root.mainloop()