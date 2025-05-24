from opcua import Server
from datetime import datetime
import random
import time
import http.client
import json

# Setup OPC UA Server
server = Server()
server.set_endpoint("opc.tcp://0.0.0.0:4840/pumping_station/server/")
server.set_server_name("SimulatedRemotePumpingStation")

uri = "http://example.org/pumpingstation"
idx = server.register_namespace(uri)
station = server.get_objects_node().add_object(idx, "RemotePumpingStation")

# Add Variables
flow_in = station.add_variable(idx, "Flow_In_LPM", 0.0)
flow_out = station.add_variable(idx, "Flow_Out_LPM", 0.0)
pump1_status = station.add_variable(idx, "Pump1_Status", False)
pump1_power = station.add_variable(idx, "Pump1_Power_kW", 0.0)
pump1_vibration = station.add_variable(idx, "Pump1_Vibration_mm_s", 0.0)
pump1_temp = station.add_variable(idx, "Pump1_Temperature_C", 0.0)
tank_level = station.add_variable(idx, "Tank_Level_Percent", 0.0)
valve_fill = station.add_variable(idx, "Valve_Fill_Status", False)
valve_discharge = station.add_variable(idx, "Valve_Discharge_Status", False)
voltage = station.add_variable(idx, "Voltage_Pump1_V", 0.0)

# Anomaly controls
anomaly_enabled = station.add_variable(idx, "Anomaly_Enabled", False)
anomaly_triggered = station.add_variable(idx, "Anomaly_Triggered", False)
anomaly_enabled.set_writable()
anomaly_triggered.set_writable()

# Set writable variables
for var in [flow_in, flow_out, pump1_status, tank_level, valve_fill, valve_discharge]:
    var.set_writable()

# Start the server
server.start()
print("✅ OPC UA Server running at: opc.tcp://0.0.0.0:4840")

# conn = http.client.HTTPConnection("localhost", 3000)  # Persistent connection
conn = http.client.HTTPSConnection("blueboat.vercel.app")  # Persistent connection

try:
    while True:
        enable_anomaly = anomaly_enabled.get_value()
        manual_trigger = anomaly_triggered.get_value()
        anomaly_now = False

        if enable_anomaly and random.random() < 0.05:
            anomaly_now = True
        if manual_trigger:
            anomaly_now = True
            anomaly_triggered.set_value(False)

        # Simulated data
        flow_val_in = round(random.uniform(100, 200), 2)
        flow_val_out = round(random.uniform(90, 190), 2)
        power = round(random.uniform(5.0, 15.0), 2)
        vibration = round(random.uniform(0.1, 1.5), 2)
        temp = round(random.uniform(35.0, 75.0), 2)
        voltage_val = round(random.uniform(380.0, 420.0), 2)

        if anomaly_now:
            vibration = round(random.uniform(5.0, 10.0), 2)
            temp = round(random.uniform(85.0, 100.0), 2)
            voltage_val = round(random.uniform(450.0, 500.0), 2)

        # Update values
        flow_in.set_value(flow_val_in)
        flow_out.set_value(flow_val_out)
        pump1_power.set_value(power)
        pump1_vibration.set_value(vibration)
        pump1_temp.set_value(temp)
        voltage.set_value(voltage_val)

        level = round(random.uniform(10.0, 90.0), 2)
        tank_level.set_value(level)

        # Logic control
        if level < 25:
            valve_fill.set_value(True)
            valve_discharge.set_value(False)
            pump1_status.set_value(True)
        elif level > 85:
            valve_fill.set_value(False)
            valve_discharge.set_value(True)
            pump1_status.set_value(False)
        else:
            valve_fill.set_value(False)
            valve_discharge.set_value(False)

        # Print terminal status
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] System Status:")
        print(f"  ➤ Flow In         : {flow_val_in:.2f} LPM")
        print(f"  ➤ Flow Out        : {flow_val_out:.2f} LPM")
        print(f"  ➤ Tank Level      : {level:.2f} %")
        print(f"  ➤ Pump1 Status    : {'ON' if pump1_status.get_value() else 'OFF'}")
        print(f"    - Power         : {power:.2f} kW")
        print(f"    - Vibration     : {vibration:.2f} mm/s")
        print(f"    - Temperature   : {temp:.2f} °C")
        print(f"  ➤ Fill Valve      : {'OPEN' if valve_fill.get_value() else 'CLOSED'}")
        print(f"  ➤ Discharge Valve : {'OPEN' if valve_discharge.get_value() else 'CLOSED'}")
        print(f"  ➤ Voltage         : {voltage_val:.2f} V")
        print(f"  ⚠ Anomaly Triggered: {'YES' if anomaly_now else 'No'}")
        print("------------------------------------------------------------")

        payload = json.dumps({
            "flow_in": flow_val_in,
            "flow_out": flow_val_out,
            "pump1_status": pump1_status.get_value(),
            "pump1_power": power,
            "pump1_vibration": vibration,
            "pump1_temp": temp,
            "tank_level": level,
            "valve_fill": valve_fill.get_value(),
            "valve_discharge": valve_discharge.get_value(),
            "voltage": voltage_val,
            "anomaly_triggered": anomaly_now
        })
        headers = {
            'Content-Type': 'application/json'
        }
        try:
            conn.request("POST", "/api/factory_tank", payload, headers)
            res = conn.getresponse()
            data = res.read()
            print(data.decode("utf-8"))
        except Exception as e:
            print(f"[HTTP ERROR] {e}. Reconnecting...")
            conn.close()
            # conn = http.client.HTTPConnection("localhost", 3000)
            conn = http.client.HTTPSConnection("blueboat.vercel.app")
        time.sleep(1)

except KeyboardInterrupt:
    print("🛑 Shutting down server...")
    server.stop()
    conn.close()
