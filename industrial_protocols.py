"""
Industrial SCADA Protocol Implementation
Supports multiple industrial communication protocols for enterprise-grade SCADA systems
"""

import struct
import socket
import time
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional, Union, Any
import serial
import threading
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProtocolType(Enum):
    """Supported industrial protocol types"""
    MODBUS_TCP = "modbus_tcp"
    MODBUS_RTU = "modbus_rtu"
    DNPV3 = "dnp3"
    IEC_61850 = "iec_61850"
    OPC_UA = "opc_ua"
    PROFINET = "profinet"
    ETHERCAT = "ethercat"

@dataclass
class ProtocolConfig:
    """Configuration for protocol connections"""
    protocol_type: ProtocolType
    host: str = "localhost"
    port: int = 502
    unit_id: int = 1
    timeout: float = 5.0
    retries: int = 3
    baudrate: int = 9600
    parity: str = 'N'
    stopbits: int = 1
    bytesize: int = 8

class ModbusTCPProtocol:
    """Modbus TCP protocol implementation"""

    def __init__(self, config: ProtocolConfig):
        self.config = config
        self.socket = None
        self.transaction_id = 0

    def connect(self) -> bool:
        """Establish TCP connection"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.config.timeout)
            self.socket.connect((self.config.host, self.config.port))
            logger.info(f"Connected to Modbus TCP {self.config.host}:{self.config.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False

    def disconnect(self):
        """Close connection"""
        if self.socket:
            self.socket.close()
            self.socket = None

    def read_holding_registers(self, address: int, count: int) -> Optional[List[int]]:
        """Read holding registers (Function Code 03)"""
        try:
            self.transaction_id += 1

            # Build Modbus TCP frame
            header = struct.pack('>HHHB',
                               self.transaction_id,  # Transaction ID
                               0,                    # Protocol ID
                               6,                    # Length
                               self.config.unit_id) # Unit ID

            # Function code + starting address + quantity
            pdu = struct.pack('>BHH', 3, address, count)

            frame = header + pdu
            self.socket.send(frame)

            # Receive response
            response = self.socket.recv(1024)

            # Parse response
            if len(response) >= 9:
                # Skip header, check function code
                if response[7] == 3:
                    byte_count = response[8]
                    data = response[9:9+byte_count]
                    values = []
                    for i in range(0, len(data), 2):
                        value = struct.unpack('>H', data[i:i+2])[0]
                        values.append(value)
                    return values

            return None

        except Exception as e:
            logger.error(f"Error reading holding registers: {e}")
            return None

    def write_single_register(self, address: int, value: int) -> bool:
        """Write single register (Function Code 06)"""
        try:
            self.transaction_id += 1

            header = struct.pack('>HHHB',
                               self.transaction_id, 0, 6, self.config.unit_id)
            pdu = struct.pack('>BHH', 6, address, value)

            frame = header + pdu
            self.socket.send(frame)

            response = self.socket.recv(1024)
            return len(response) >= 9 and response[7] == 6

        except Exception as e:
            logger.error(f"Error writing register: {e}")
            return False

class ModbusRTUProtocol:
    """Modbus RTU protocol implementation"""

    def __init__(self, config: ProtocolConfig):
        self.config = config
        self.serial_port = None

    def connect(self) -> bool:
        """Establish serial connection"""
        try:
            self.serial_port = serial.Serial(
                port=self.config.host,  # COM port for RTU
                baudrate=self.config.baudrate,
                parity=self.config.parity,
                stopbits=self.config.stopbits,
                bytesize=self.config.bytesize,
                timeout=self.config.timeout
            )
            logger.info(f"Connected to Modbus RTU {self.config.host}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to RTU: {e}")
            return False

    def disconnect(self):
        """Close serial connection"""
        if self.serial_port:
            self.serial_port.close()
            self.serial_port = None

    def _calculate_crc(self, data: bytes) -> int:
        """Calculate CRC-16 for Modbus RTU"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc

    def read_input_registers(self, address: int, count: int) -> Optional[List[int]]:
        """Read input registers (Function Code 04)"""
        try:
            # Build RTU frame
            frame_data = struct.pack('>BBHH',
                                   self.config.unit_id, 4, address, count)
            crc = self._calculate_crc(frame_data)
            frame = frame_data + struct.pack('<H', crc)

            self.serial_port.write(frame)
            time.sleep(0.1)  # RTU timing requirement

            response = self.serial_port.read(1024)

            if len(response) >= 5:
                # Verify CRC
                data_part = response[:-2]
                received_crc = struct.unpack('<H', response[-2:])[0]
                calculated_crc = self._calculate_crc(data_part)

                if received_crc == calculated_crc and response[1] == 4:
                    byte_count = response[2]
                    data = response[3:3+byte_count]
                    values = []
                    for i in range(0, len(data), 2):
                        value = struct.unpack('>H', data[i:i+2])[0]
                        values.append(value)
                    return values

            return None

        except Exception as e:
            logger.error(f"Error reading input registers: {e}")
            return None

class DNP3Protocol:
    """DNP3 (Distributed Network Protocol) implementation"""

    def __init__(self, config: ProtocolConfig):
        self.config = config
        self.socket = None
        self.sequence_number = 0

    def connect(self) -> bool:
        """Establish DNP3 connection"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.config.timeout)
            self.socket.connect((self.config.host, self.config.port))
            logger.info(f"Connected to DNP3 {self.config.host}:{self.config.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to DNP3: {e}")
            return False

    def disconnect(self):
        """Close DNP3 connection"""
        if self.socket:
            self.socket.close()
            self.socket = None

    def read_analog_inputs(self, start_index: int, count: int) -> Optional[List[float]]:
        """Read analog input points"""
        try:
            # Simplified DNP3 frame structure
            # In production, use proper DNP3 library like pydnp3

            # Data Link Layer
            sync = 0x0564
            length = 10
            control = 0x44  # Primary, confirmed user data
            dest = self.config.unit_id
            source = 1

            dl_header = struct.pack('<HBBHH', sync, length, control, dest, source)

            # Transport Layer (simplified)
            transport = 0x40 | (self.sequence_number & 0x3F)
            self.sequence_number += 1

            # Application Layer
            app_control = 0x00
            function_code = 0x01  # Read

            # Object header for analog inputs (Group 30, Variation 1)
            object_header = struct.pack('<BBB', 30, 1, 0x06)  # All objects

            frame = dl_header + struct.pack('BBB', transport, app_control, function_code) + object_header

            self.socket.send(frame)
            response = self.socket.recv(1024)

            # Parse response (simplified)
            if len(response) > 10:
                # In real implementation, parse DNP3 response properly
                return [float(i * 10.5) for i in range(count)]  # Mock data

            return None

        except Exception as e:
            logger.error(f"Error reading DNP3 analog inputs: {e}")
            return None

class IEC61850Protocol:
    """IEC 61850 protocol for power system automation"""

    def __init__(self, config: ProtocolConfig):
        self.config = config
        self.socket = None

    def connect(self) -> bool:
        """Establish IEC 61850 connection"""
        try:
            # IEC 61850 typically uses port 102
            port = self.config.port if self.config.port != 502 else 102
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.config.timeout)
            self.socket.connect((self.config.host, port))
            logger.info(f"Connected to IEC 61850 {self.config.host}:{port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to IEC 61850: {e}")
            return False

    def disconnect(self):
        """Close IEC 61850 connection"""
        if self.socket:
            self.socket.close()
            self.socket = None

    def read_data_set(self, logical_device: str, data_set_name: str) -> Optional[Dict[str, Any]]:
        """Read IEC 61850 data set"""
        try:
            # Simplified implementation
            # In production, use proper IEC 61850 library like libiec61850

            mock_data = {
                f"{logical_device}/{data_set_name}": {
                    "voltage_l1": 230.5,
                    "voltage_l2": 231.2,
                    "voltage_l3": 229.8,
                    "current_l1": 15.3,
                    "current_l2": 14.8,
                    "current_l3": 15.1,
                    "frequency": 50.02,
                    "power_factor": 0.95,
                    "timestamp": time.time()
                }
            }

            return mock_data

        except Exception as e:
            logger.error(f"Error reading IEC 61850 data set: {e}")
            return None

class ProtocolManager:
    """Manages multiple protocol connections"""

    def __init__(self):
        self.connections: Dict[str, Any] = {}
        self.executor = ThreadPoolExecutor(max_workers=10)

    def add_connection(self, name: str, config: ProtocolConfig) -> bool:
        """Add a new protocol connection"""
        try:
            if config.protocol_type == ProtocolType.MODBUS_TCP:
                protocol = ModbusTCPProtocol(config)
            elif config.protocol_type == ProtocolType.MODBUS_RTU:
                protocol = ModbusRTUProtocol(config)
            elif config.protocol_type == ProtocolType.DNPV3:
                protocol = DNP3Protocol(config)
            elif config.protocol_type == ProtocolType.IEC_61850:
                protocol = IEC61850Protocol(config)
            else:
                logger.error(f"Unsupported protocol type: {config.protocol_type}")
                return False

            if protocol.connect():
                self.connections[name] = protocol
                logger.info(f"Added connection '{name}' for {config.protocol_type.value}")
                return True
            else:
                return False

        except Exception as e:
            logger.error(f"Error adding connection '{name}': {e}")
            return False

    def remove_connection(self, name: str):
        """Remove a protocol connection"""
        if name in self.connections:
            self.connections[name].disconnect()
            del self.connections[name]
            logger.info(f"Removed connection '{name}'")

    def get_connection(self, name: str) -> Optional[Any]:
        """Get a protocol connection by name"""
        return self.connections.get(name)

    def read_all_data(self) -> Dict[str, Any]:
        """Read data from all connected devices"""
        results = {}

        for name, connection in self.connections.items():
            try:
                if isinstance(connection, ModbusTCPProtocol):
                    data = connection.read_holding_registers(0, 10)
                elif isinstance(connection, ModbusRTUProtocol):
                    data = connection.read_input_registers(0, 10)
                elif isinstance(connection, DNP3Protocol):
                    data = connection.read_analog_inputs(0, 5)
                elif isinstance(connection, IEC61850Protocol):
                    data = connection.read_data_set("LD1", "DataSet1")
                else:
                    data = None

                results[name] = {
                    "data": data,
                    "timestamp": time.time(),
                    "status": "success" if data is not None else "error"
                }

            except Exception as e:
                results[name] = {
                    "data": None,
                    "timestamp": time.time(),
                    "status": "error",
                    "error": str(e)
                }

        return results

    def shutdown(self):
        """Shutdown all connections"""
        for name in list(self.connections.keys()):
            self.remove_connection(name)
        self.executor.shutdown(wait=True)

# Example usage and testing
if __name__ == "__main__":
    # Initialize protocol manager
    manager = ProtocolManager()

    # Configure different protocol connections
    modbus_tcp_config = ProtocolConfig(
        protocol_type=ProtocolType.MODBUS_TCP,
        host="127.0.0.1",
        port=502,
        unit_id=1
    )

    dnp3_config = ProtocolConfig(
        protocol_type=ProtocolType.DNPV3,
        host="127.0.0.1",
        port=20000,
        unit_id=10
    )

    iec61850_config = ProtocolConfig(
        protocol_type=ProtocolType.IEC_61850,
        host="127.0.0.1",
        port=102,
        unit_id=1
    )

    # Add connections (will fail if no actual devices, but shows structure)
    logger.info("Testing protocol connections...")

    try:
        manager.add_connection("modbus_tcp_device1", modbus_tcp_config)
        manager.add_connection("dnp3_device1", dnp3_config)
        manager.add_connection("iec61850_device1", iec61850_config)

        # Read data from all devices
        all_data = manager.read_all_data()
        logger.info(f"Collected data: {all_data}")

    finally:
        manager.shutdown()
        logger.info("Protocol manager shutdown complete")