"""
Gamepad/Controller Input Module for E-NOR
Detects and handles wireless gaming controllers (EasySMX, Xbox, PlayStation, etc.)

Uses evdev for Linux input event handling.
Controllers typically connect via:
- 2.4GHz USB dongle (most common for wireless)
- Bluetooth
"""

import asyncio
import atexit
from pathlib import Path
from typing import Optional, Dict, List, Callable, Any
import json

# Try to import evdev for Linux input handling
try:
    import evdev
    from evdev import InputDevice, categorize, ecodes
    EVDEV_AVAILABLE = True
except ImportError:
    EVDEV_AVAILABLE = False
    print("evdev not available - controller detection will be simulated")


# Common gamepad button/axis mappings (may vary by controller)
# EasySMX ESM-9101 typically maps as a generic gamepad
BUTTON_NAMES = {
    304: "A",        # BTN_SOUTH / BTN_A
    305: "B",        # BTN_EAST / BTN_B
    307: "X",        # BTN_NORTH / BTN_X
    308: "Y",        # BTN_WEST / BTN_Y
    310: "LB",       # BTN_TL
    311: "RB",       # BTN_TR
    314: "SELECT",   # BTN_SELECT
    315: "START",    # BTN_START
    316: "HOME",     # BTN_MODE
    317: "L3",       # BTN_THUMBL
    318: "R3",       # BTN_THUMBR
}

AXIS_NAMES = {
    0: "LEFT_X",     # ABS_X - Left stick horizontal
    1: "LEFT_Y",     # ABS_Y - Left stick vertical
    2: "RIGHT_X",    # ABS_RX - Right stick horizontal
    5: "RIGHT_Y",    # ABS_RY - Right stick vertical
    16: "DPAD_X",    # ABS_HAT0X - D-pad horizontal
    17: "DPAD_Y",    # ABS_HAT0Y - D-pad vertical
    9: "RT",         # ABS_GAS - Right trigger
    10: "LT",        # ABS_BRAKE - Left trigger
}


class ControllerInfo:
    """Information about a detected controller"""

    def __init__(self, device: Optional['InputDevice'] = None, path: str = "", simulated: bool = False):
        self.device = device
        self.path = path
        self.simulated = simulated

        if device and not simulated:
            self.name = device.name
            self.phys = device.phys or "Unknown"
            # Get capabilities
            caps = device.capabilities(verbose=True)
            self.has_buttons = ('EV_KEY', ecodes.EV_KEY) in caps or ecodes.EV_KEY in device.capabilities()
            self.has_axes = ('EV_ABS', ecodes.EV_ABS) in caps or ecodes.EV_ABS in device.capabilities()
        else:
            self.name = "Simulated Controller"
            self.phys = "virtual"
            self.has_buttons = True
            self.has_axes = True

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": self.path,
            "phys": self.phys,
            "has_buttons": self.has_buttons,
            "has_axes": self.has_axes,
            "simulated": self.simulated,
            "connected": True
        }


class ControllerManager:
    """
    Manages gamepad/controller detection and input handling.
    Provides async event loop for reading controller input.
    """

    def __init__(self):
        self._controllers: Dict[str, ControllerInfo] = {}
        self._active_controller: Optional[str] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._input_callback: Optional[Callable[[str, str, Any], None]] = None
        self._motor_callback: Optional[Callable[[str, float], None]] = None

        # Dead zone for analog sticks (prevents drift)
        self.dead_zone = 0.15

        # Axis calibration (min, max, center)
        self._axis_calibration: Dict[int, tuple] = {}

        atexit.register(self.cleanup)

    @property
    def is_available(self) -> bool:
        """Check if evdev is available for controller detection"""
        return EVDEV_AVAILABLE

    @property
    def has_controller(self) -> bool:
        """Check if any controller is connected"""
        return len(self._controllers) > 0

    @property
    def active_controller(self) -> Optional[ControllerInfo]:
        """Get the currently active controller"""
        if self._active_controller and self._active_controller in self._controllers:
            return self._controllers[self._active_controller]
        return None

    def set_input_callback(self, callback: Callable[[str, str, Any], None]):
        """Set callback for input events: callback(controller_path, input_name, value)"""
        self._input_callback = callback

    def set_motor_callback(self, callback: Callable[[str, float], None]):
        """Set callback for motor commands: callback(direction, speed)"""
        self._motor_callback = callback

    def scan_controllers(self) -> List[ControllerInfo]:
        """
        Scan for connected game controllers.
        Returns list of detected controllers.
        """
        self._controllers.clear()

        if not EVDEV_AVAILABLE:
            print("evdev not available, returning simulated controller")
            return []

        try:
            devices = [evdev.InputDevice(path) for path in evdev.list_devices()]

            for device in devices:
                # Check if device looks like a gamepad
                caps = device.capabilities()

                # Gamepads typically have:
                # - EV_KEY (buttons) with gamepad button codes
                # - EV_ABS (absolute axes) for sticks/triggers
                has_gamepad_buttons = False
                has_axes = ecodes.EV_ABS in caps

                if ecodes.EV_KEY in caps:
                    key_caps = caps[ecodes.EV_KEY]
                    # Check for common gamepad button codes
                    gamepad_buttons = {304, 305, 307, 308, 310, 311, 314, 315, 316, 317, 318}
                    has_gamepad_buttons = bool(gamepad_buttons & set(key_caps))

                # Also check name for common gamepad indicators
                name_lower = device.name.lower()
                is_gamepad_name = any(kw in name_lower for kw in [
                    'gamepad', 'controller', 'joystick', 'xbox', 'playstation',
                    'ps4', 'ps5', 'dualshock', 'dualsense', 'nintendo', 'switch',
                    'easysmx', 'esm-', 'wireless', 'game pad', 'joypad'
                ])

                if (has_gamepad_buttons and has_axes) or is_gamepad_name:
                    info = ControllerInfo(device, device.path)
                    self._controllers[device.path] = info
                    print(f"Found controller: {device.name} at {device.path}")
                else:
                    device.close()

            return list(self._controllers.values())

        except Exception as e:
            print(f"Error scanning controllers: {e}")
            return []

    def get_controllers(self) -> List[dict]:
        """Get list of all detected controllers as dicts"""
        return [c.to_dict() for c in self._controllers.values()]

    def select_controller(self, path: str) -> bool:
        """Select a controller to use for input"""
        if path in self._controllers:
            self._active_controller = path
            print(f"Selected controller: {self._controllers[path].name}")
            return True
        return False

    def _normalize_axis(self, axis_code: int, value: int, device: InputDevice) -> float:
        """Normalize axis value to -1.0 to 1.0 range"""
        try:
            absinfo = device.absinfo(axis_code)
            if absinfo:
                min_val = absinfo.min
                max_val = absinfo.max
                center = (min_val + max_val) / 2
                range_val = (max_val - min_val) / 2

                if range_val > 0:
                    normalized = (value - center) / range_val
                    # Apply dead zone
                    if abs(normalized) < self.dead_zone:
                        return 0.0
                    return max(-1.0, min(1.0, normalized))
        except:
            pass

        # Fallback normalization (assume 0-255 range with 128 center)
        normalized = (value - 128) / 128
        if abs(normalized) < self.dead_zone:
            return 0.0
        return max(-1.0, min(1.0, normalized))

    async def _read_controller_events(self):
        """Async loop to read controller input events"""
        if not self._active_controller or self._active_controller not in self._controllers:
            return

        info = self._controllers[self._active_controller]
        if not info.device:
            return

        device = info.device

        try:
            async for event in device.async_read_loop():
                if not self._running:
                    break

                # Button events
                if event.type == ecodes.EV_KEY:
                    button_name = BUTTON_NAMES.get(event.code, f"BTN_{event.code}")
                    value = event.value  # 1 = pressed, 0 = released

                    if self._input_callback:
                        self._input_callback(self._active_controller, button_name, value)

                    # Map buttons to motor commands
                    if self._motor_callback:
                        await self._handle_button_motor(button_name, value)

                # Axis events (sticks, triggers, d-pad)
                elif event.type == ecodes.EV_ABS:
                    axis_name = AXIS_NAMES.get(event.code, f"AXIS_{event.code}")
                    value = self._normalize_axis(event.code, event.value, device)

                    if self._input_callback:
                        self._input_callback(self._active_controller, axis_name, value)

                    # Map axes to motor commands
                    if self._motor_callback:
                        await self._handle_axis_motor(axis_name, value)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Error reading controller: {e}")

    async def _handle_button_motor(self, button: str, pressed: int):
        """Map button presses to motor commands"""
        if not self._motor_callback:
            return

        if pressed:
            # D-pad or button motor control
            if button == "DPAD_UP":
                self._motor_callback("forward", 0.7)
            elif button == "DPAD_DOWN":
                self._motor_callback("backward", 0.7)
            elif button == "DPAD_LEFT":
                self._motor_callback("left", 0.7)
            elif button == "DPAD_RIGHT":
                self._motor_callback("right", 0.7)
        else:
            # Button released - stop
            if button in ["DPAD_UP", "DPAD_DOWN", "DPAD_LEFT", "DPAD_RIGHT"]:
                self._motor_callback("stop", 0)

    async def _handle_axis_motor(self, axis: str, value: float):
        """Map analog stick movement to motor commands"""
        if not self._motor_callback:
            return

        # Left stick Y-axis controls forward/backward
        if axis == "LEFT_Y":
            if value < -0.3:  # Stick pushed up
                self._motor_callback("forward", abs(value))
            elif value > 0.3:  # Stick pushed down
                self._motor_callback("backward", abs(value))
            else:
                self._motor_callback("stop", 0)

        # Left stick X-axis controls turning (when moving)
        elif axis == "LEFT_X":
            if value < -0.3:  # Stick pushed left
                self._motor_callback("left", abs(value))
            elif value > 0.3:  # Stick pushed right
                self._motor_callback("right", abs(value))

        # D-pad via axis events
        elif axis == "DPAD_Y":
            if value < -0.5:
                self._motor_callback("forward", 0.7)
            elif value > 0.5:
                self._motor_callback("backward", 0.7)
            else:
                self._motor_callback("stop", 0)
        elif axis == "DPAD_X":
            if value < -0.5:
                self._motor_callback("left", 0.7)
            elif value > 0.5:
                self._motor_callback("right", 0.7)

    async def start_reading(self):
        """Start the async controller input reading loop"""
        if self._running:
            return

        if not self._active_controller:
            # Auto-select first controller if available
            if self._controllers:
                self._active_controller = list(self._controllers.keys())[0]
            else:
                print("No controller selected")
                return

        self._running = True
        self._task = asyncio.create_task(self._read_controller_events())
        print(f"Started reading from controller: {self._active_controller}")

    async def stop_reading(self):
        """Stop the controller input reading loop"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        print("Stopped reading controller")

    def cleanup(self):
        """Clean up resources"""
        self._running = False
        for info in self._controllers.values():
            if info.device:
                try:
                    info.device.close()
                except:
                    pass
        self._controllers.clear()
        print("Controller manager cleaned up")

    def status(self) -> dict:
        """Get current controller manager status"""
        return {
            "evdev_available": EVDEV_AVAILABLE,
            "controllers": self.get_controllers(),
            "active_controller": self._active_controller,
            "reading": self._running,
            "dead_zone": self.dead_zone
        }


# Global controller manager instance
_controller_manager: Optional[ControllerManager] = None


def get_controller_manager() -> ControllerManager:
    """Get or create the global controller manager instance"""
    global _controller_manager
    if _controller_manager is None:
        _controller_manager = ControllerManager()
    return _controller_manager


# Convenience functions
def scan_controllers() -> List[dict]:
    """Scan for connected controllers"""
    manager = get_controller_manager()
    manager.scan_controllers()
    return manager.get_controllers()


def get_controllers() -> List[dict]:
    """Get list of detected controllers"""
    return get_controller_manager().get_controllers()


def select_controller(path: str) -> bool:
    """Select a controller to use"""
    return get_controller_manager().select_controller(path)


def status() -> dict:
    """Get controller status"""
    return get_controller_manager().status()


def cleanup():
    """Clean up controller resources"""
    global _controller_manager
    if _controller_manager:
        _controller_manager.cleanup()
        _controller_manager = None
