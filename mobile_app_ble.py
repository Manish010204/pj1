from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.label import Label
from kivy.clock import Clock
import asyncio
from bleak import BleakClient, BleakScanner
import serial
import serial.tools.list_ports
from threading import Thread
import time

# UUID for a custom characteristic that will handle our text data
TEXT_CHARACTERISTIC_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

class AutoTyperApp(App):
    def build(self):
        self.client = None
        self.is_connected = False
        self.device_address = None
        
        # Main layout
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Connection type spinner
        self.conn_type = Spinner(
            text='Bluetooth',
            values=('Bluetooth', 'USB'),
            size_hint=(1, None),
            height=44
        )
        layout.add_widget(self.conn_type)
        
        # Status label
        self.status_label = Label(text='Status: Not Connected')
        layout.add_widget(self.status_label)
        
        # Connect button
        self.connect_btn = Button(
            text='Connect',
            size_hint=(1, None),
            height=44
        )
        self.connect_btn.bind(on_press=self.toggle_connection)
        layout.add_widget(self.connect_btn)
        
        # Text input
        self.text_input = TextInput(
            multiline=True,
            hint_text='Enter text to type...',
            size_hint=(1, 0.7)
        )
        layout.add_widget(self.text_input)
        
        # Send button
        self.send_btn = Button(
            text='Send Text',
            size_hint=(1, None),
            height=44,
            disabled=True
        )
        self.send_btn.bind(on_press=self.send_text)
        layout.add_widget(self.send_btn)
        
        return layout
    
    async def scan_for_device(self):
        devices = await BleakScanner.discover()
        for device in devices:
            # Look for a device that advertises our service
            if device.name and ('AutoTyper' in device.name or 'PC-Listener' in device.name):
                return device.address
        return None

    async def connect_bluetooth(self):
        try:
            self.device_address = await self.scan_for_device()
            if not self.device_address:
                print("No compatible device found")
                return None
            
            client = BleakClient(self.device_address)
            await client.connect()
            return client
        except Exception as e:
            print(f"Bluetooth connection error: {e}")
            return None
    
    def connect_usb(self):
        try:
            available_ports = list(serial.tools.list_ports.comports())
            if not available_ports:
                return None
            
            for port in available_ports:
                try:
                    connection = serial.Serial(port.device, 9600, timeout=1)
                    return connection
                except serial.SerialException:
                    continue
            return None
        except Exception as e:
            print(f"USB connection error: {e}")
            return None
    
    def toggle_connection(self, instance):
        if not self.is_connected:
            def connect():
                try:
                    if self.conn_type.text == 'Bluetooth':
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        self.client = loop.run_until_complete(self.connect_bluetooth())
                    else:
                        self.client = self.connect_usb()
                    
                    if self.client:
                        self.is_connected = True
                        Clock.schedule_once(lambda dt: self.update_ui_connected())
                    else:
                        Clock.schedule_once(lambda dt: self.update_ui_error())
                except Exception as e:
                    print(f"Connection error: {e}")
                    Clock.schedule_once(lambda dt: self.update_ui_error())
            
            self.status_label.text = 'Status: Connecting...'
            Thread(target=connect).start()
        else:
            self.disconnect()
    
    def update_ui_connected(self):
        self.status_label.text = 'Status: Connected'
        self.connect_btn.text = 'Disconnect'
        self.send_btn.disabled = False
    
    def update_ui_error(self):
        self.status_label.text = 'Status: Connection Failed'
        self.connect_btn.text = 'Connect'
        self.send_btn.disabled = True
        self.is_connected = False
        if self.client:
            if self.conn_type.text == 'Bluetooth':
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.client.disconnect())
            else:
                self.client.close()
            self.client = None
    
    def disconnect(self):
        if self.client:
            try:
                if self.conn_type.text == 'Bluetooth':
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self.client.disconnect())
                else:
                    self.client.close()
            except:
                pass
        self.client = None
        self.is_connected = False
        self.status_label.text = 'Status: Disconnected'
        self.connect_btn.text = 'Connect'
        self.send_btn.disabled = True
    
    def send_text(self, instance):
        if not self.is_connected or not self.client:
            return
        
        text = self.text_input.text
        if not text:
            return
        
        try:
            if self.conn_type.text == 'Bluetooth':
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(
                    self.client.write_gatt_char(TEXT_CHARACTERISTIC_UUID, text.encode())
                )
            else:
                self.client.write(text.encode() + b'\n')
            self.text_input.text = ''
        except Exception as e:
            print(f"Send error: {e}")
            self.disconnect()

if __name__ == '__main__':
    AutoTyperApp().run()