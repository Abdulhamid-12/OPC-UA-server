import asyncio
import logging
from asyncua import Server, ua

# Configuration for your OPC UA Server
UA_SERVER_ENDPOINT = "opc.tcp://192.168.7.101:4840"
UA_SERVER_NAME = "MyPythonIIoTServer"

# Configuration for connecting to the OPC UA Gateway (that gets data from RSLinx)
# This is the OPC UA server endpoint provided by your DA-UA gateway software
GATEWAY_UA_ENDPOINT = "opc.tcp://localhost:49320/Kepware.KEPServerEX.V6/UA" # Example for Kepware

async def main():
    _logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)

    # 1. Setup our Python OPC UA Server
    server = Server()
    await server.init()
    server.set_endpoint(UA_SERVER_ENDPOINT)
    server.set_server_name(UA_SERVER_NAME)

    # Setup our own namespace
    uri = "http://my.iiot.project.example.com"
    idx = await server.register_namespace(uri)

    # Get Objects node
    objects = server.nodes.objects

    # Create a folder for PLC data
    plc_data_folder = await objects.add_folder(idx, "PLC_Data")

    # Example: Create variables on our Python OPC UA server
    # These will be updated with data read from the gateway
    my_plc_tag1_var = await plc_data_folder.add_variable(idx, "PLC_Tag1_FromGateway", 0.0)
    my_plc_tag2_var = await plc_data_folder.add_variable(idx, "PLC_Tag2_FromGateway", False)
    await my_plc_tag1_var.set_writable() # If you want to write back (requires gateway write setup)
    await my_plc_tag2_var.set_writable()

    _logger.info(f"Python OPC UA Server started at {UA_SERVER_ENDPOINT}")

    # 2. Connect as a client to the OPC DA-UA Gateway's OPC UA Server
    #    and periodically read data to update our server's variables.
    async with server: # Manages server start/stop
        try:
            async with ua.Client(url=GATEWAY_UA_ENDPOINT) as client:
                _logger.info(f"Connected to Gateway OPC UA Server at {GATEWAY_UA_ENDPOINT}")

                # Find the NodeIDs of the tags in the Gateway's OPC UA server
                # You'll need an OPC UA client tool (like UaExpert) to browse the
                # gateway's address space and find these NodeIDs.
                # Example NodeIDs (these WILL be different for your setup):
                gateway_plc_tag1_node_id = "ns=2;s=Channel1.Device1.Tag1" # Example path
                gateway_plc_tag2_node_id = "ns=2;s=Channel1.Device1.Tag2" # Example path

                node_tag1_gw = client.get_node(gateway_plc_tag1_node_id)
                node_tag2_gw = client.get_node(gateway_plc_tag2_node_id)

                while True:
                    try:
                        # Read data from the gateway
                        tag1_val = await node_tag1_gw.read_value()
                        tag2_val = await node_tag2_gw.read_value()

                        _logger.info(f"Read from Gateway: Tag1={tag1_val}, Tag2={tag2_val}")

                        # Write data to our Python OPC UA server's variables
                        await server.write_attribute_value(my_plc_tag1_var.nodeid, ua.DataValue(tag1_val))
                        await server.write_attribute_value(my_plc_tag2_var.nodeid, ua.DataValue(tag2_val))

                        _logger.info("Updated local Python OPC UA server variables.")

                    except Exception as e:
                        _logger.error(f"Error during periodic read/update: {e}")
                    
                    await asyncio.sleep(5) # Read every 5 seconds

        except ConnectionRefusedError:
            _logger.error(f"Connection refused by Gateway OPC UA server at {GATEWAY_UA_ENDPOINT}. Ensure it's running and configured.")
        except Exception as e:
            _logger.error(f"Could not connect to Gateway OPC UA Server: {e}")
            _logger.info("Python OPC UA server will continue running without gateway data.")
            # Keep server running even if gateway connection fails, or handle as needed
            while True:
                await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())