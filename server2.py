from opcua import Server, ua
import time

# Setup OPC UA Server
server = Server()
server.set_endpoint("opc.tcp://0.0.0.0:4840")
server.set_server_name("CustomTankServer")
server.set_security_policy([ua.SecurityPolicyType.NoSecurity])

uri = "http://example.com/opcua/tank"
idx = server.register_namespace(uri)
objects = server.get_objects_node()

# Create TankSystem object and variables
tank = objects.add_object(idx, "TankSystem")
tank_level = tank.add_variable(idx, "TankLevel", 0.0)
set_point = tank.add_variable(idx, "SetPoint", 50.0)
start_cmd = tank.add_variable(idx, "StartCmd", False)
stop_cmd = tank.add_variable(idx, "StopCmd", False)
fill_valve = tank.add_variable(idx, "FillValve", False)
drain_valve = tank.add_variable(idx, "DrainValve", False)

# Make all writable
for var in [tank_level, set_point, start_cmd, stop_cmd, fill_valve, drain_valve]:
    var.set_writable()

# Run server
server.start()
print("✅ OPC UA Server started at opc.tcp://localhost:4840")

try:
    auto_mode = False

    while True:
        # Read inputs
        start = start_cmd.get_value()
        stop = stop_cmd.get_value()
        level = tank_level.get_value()
        sp = set_point.get_value()

        # If Start is pressed → Enable auto-mode
        if start:
            auto_mode = True
            start_cmd.set_value(False)  # Reset after read

        # If Stop is pressed → Disable auto-mode and close valves
        if stop:
            auto_mode = False
            fill_valve.set_value(False)
            drain_valve.set_value(False)
            stop_cmd.set_value(False)  # Reset after read

        if auto_mode:
            if level < sp:
                fill_valve.set_value(True)
                drain_valve.set_value(False)
            else:
                fill_valve.set_value(False)
                drain_valve.set_value(True)
        # Manual valve control still allowed outside auto-mode

        # Simulate tank level
        if fill_valve.get_value():
            level += 0.2
        elif drain_valve.get_value():
            level -= 0.3

        # Clamp between 0 and 100
        level = max(0.0, min(100.0, level))
        tank_level.set_value(level)

        print(f"AutoMode:{auto_mode} | Level:{level:.2f} | SP:{sp:.1f} | Fill:{fill_valve.get_value()} | Drain:{drain_valve.get_value()}")
        time.sleep(1)

except KeyboardInterrupt:
    print("🛑 Stopping OPC UA Server...")
    server.stop()