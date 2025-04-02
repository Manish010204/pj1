import sys
import time
import asyncio
import threading
import tkinter as tk
from tkinter import ttk
import pyautogui
import serial
from serial.tools import list_ports
from bleak import BleakServer
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.service import BleakGATTService

# Define UUIDs for our custom service and characteristic
SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
TEXT_CHARACTERISTIC_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

class PCListener:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Auto Typer PC Listener")
        self.root.geometry("400x300")
        self.setup_gui()
        self.connection = None
        self.is_listening = False
        self.listen_thread = None
        self.server = None

    def setup_gui(self):
        # Connection type selection
        self.conn_type = tk.StringVar(value="bluetooth")
        ttk.Radiobutton(self.root, text="Bluetooth", variable=self.conn_type,
                        value="bluetooth").pack(pady=5)
        ttk.Radiobutton(self.root, text="USB", variable=self.conn_type,
                        value="usb").pack(pady=5)

        # Status display
        self.status_label = ttk.Label(self.root, text="Status: Not Connected")
        self.status_label.pack(pady=10)

        # Buttons
        self.start_button = ttk.Button(self.root, text="Start Listening",
                                    command=self.toggle_listening)
        self.start_button.pack(pady=10)

        # Log display
        self.log_text = tk.Text(self.root, height=10, width=40)
        self.log_text.pack(pady=10)

    def log_message(self, message):
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)

    def handle_text_write(self, characteristic: BleakGATTCharacteristic, data: bytearray):
        text = data.decode()
        self.log_message(f"Received text: {text}")
        self.type_text(text)
        return True

    async def start_bluetooth_server(self):
        # Create a custom service
        text_characteristic = BleakGATTCharacteristic(
            uuid=TEXT_CHARACTERISTIC_UUID,
            properties=("write",),
            value=None,
            service_uuid=SERVICE_UUID,
        )
        text_characteristic.set_write_handler(self.handle_text_write)

        service = BleakGATTService(uuid=SERVICE_UUID)
        service.add_characteristic(text_characteristic)

        # Create and start the server
        self.server = BleakServer([service], name="PC-Listener")
        await self.server.start()
        self.log_message("BLE server started. Waiting for connections...")
        return True

    def start_usb_server(self):
        available_ports = list_ports.comports()
        if not available_ports:
            self.log_message("No USB ports available")
            return None
        
        for port in available_ports:
            try:
                self.connection = serial.Serial(port.device, 9600, timeout=1)
                self.log_message(f"Connected to USB port: {port.device}")
                return self.connection
            except serial.SerialException:
                continue
        
        self.log_message("Could not connect to any USB port")
        return None

    def type_text(self, text):
        pyautogui.write(text, interval=0.01)

    def listen_for_usb_data(self):
        while self.is_listening:
            try:
                data = self.connection.readline().decode().strip()
                if data:
                    self.log_message(f"Received text: {data}")
                    self.type_text(data)
            except Exception as e:
                self.log_message(f"Error receiving data: {e}")
                break

        self.is_listening = False
        if self.connection:
            self.connection.close()
        self.connection = None
        self.status_label.config(text="Status: Not Connected")
        self.start_button.config(text="Start Listening")

    def toggle_listening(self):
        if not self.is_listening:
            self.is_listening = True
            self.start_button.config(text="Stop Listening")
            self.status_label.config(text="Status: Connecting...")

            def start_server():
                try:
                    if self.conn_type.get() == "bluetooth":
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(self.start_bluetooth_server())
                        self.status_label.config(text="Status: Listening for BLE connections")
                        loop.run_forever()
                    else:
                        self.connection = self.start_usb_server()
                        if self.connection:
                            self.status_label.config(text="Status: Connected")
                            self.listen_for_usb_data()
                except Exception as e:
                    self.log_message(f"Connection error: {e}")
                    self.is_listening = False
                    self.start_button.config(text="Start Listening")
                    self.status_label.config(text="Status: Not Connected")

            self.listen_thread = threading.Thread(target=start_server)
            self.listen_thread.daemon = True
            self.listen_thread.start()
        else:
            self.is_listening = False
            if self.server:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.server.stop())
                self.server = None
            self.start_button.config(text="Start Listening")

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = PCListener()
    app.run()