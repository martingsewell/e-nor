"""
Motor Control Module for E-NOR
Uses DRV8833 dual H-bridge driver with two DC motors (tank track configuration)

GPIO Pin Mapping:
- GPIO 17 = IN1 (Left motor forward)
- GPIO 27 = IN2 (Left motor backward)
- GPIO 22 = IN3 (Right motor forward)
- GPIO 23 = IN4 (Right motor backward)
"""

import atexit
from typing import Optional

# GPIO pin assignments
LEFT_FORWARD_PIN = 17   # IN1
LEFT_BACKWARD_PIN = 27  # IN2
RIGHT_FORWARD_PIN = 22  # IN3
RIGHT_BACKWARD_PIN = 23 # IN4

# Default speed (0.0 to 1.0)
DEFAULT_SPEED = 0.7

# Try to import gpiozero, fall back to mock if not available (for development)
try:
    from gpiozero import Motor
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("gpiozero not available - motor control will be simulated")


class MotorController:
    """Controls two DC motors for tank-style movement"""

    def __init__(self, speed: float = DEFAULT_SPEED):
        self.speed = speed
        self._left_motor: Optional[Motor] = None
        self._right_motor: Optional[Motor] = None
        self._initialized = False
        self._last_command = "stop"

        if GPIO_AVAILABLE:
            try:
                self._init_motors()
            except Exception as e:
                print(f"Failed to initialize motors: {e}")
                self._initialized = False
        else:
            print("Running in simulation mode (no GPIO)")

    def _init_motors(self):
        """Initialize the motor objects"""
        self._left_motor = Motor(
            forward=LEFT_FORWARD_PIN,
            backward=LEFT_BACKWARD_PIN
        )
        self._right_motor = Motor(
            forward=RIGHT_FORWARD_PIN,
            backward=RIGHT_BACKWARD_PIN
        )
        self._initialized = True
        atexit.register(self.cleanup)
        print("Motors initialized successfully")

    @property
    def is_available(self) -> bool:
        """Check if motors are available and initialized"""
        return self._initialized

    @property
    def status(self) -> dict:
        """Get current motor status"""
        return {
            "available": self._initialized,
            "gpio_available": GPIO_AVAILABLE,
            "speed": self.speed,
            "last_command": self._last_command
        }

    def set_speed(self, speed: float):
        """Set motor speed (0.0 to 1.0)"""
        self.speed = max(0.0, min(1.0, speed))

    def forward(self, speed: Optional[float] = None):
        """Move forward - both motors forward"""
        s = speed if speed is not None else self.speed
        self._last_command = "forward"

        if self._initialized:
            self._left_motor.forward(s)
            self._right_motor.forward(s)
        print(f"Motors: forward at {s}")

    def backward(self, speed: Optional[float] = None):
        """Move backward - both motors backward"""
        s = speed if speed is not None else self.speed
        self._last_command = "backward"

        if self._initialized:
            self._left_motor.backward(s)
            self._right_motor.backward(s)
        print(f"Motors: backward at {s}")

    def left(self, speed: Optional[float] = None):
        """Turn left - right motor forward, left motor backward (pivot turn)"""
        s = speed if speed is not None else self.speed
        self._last_command = "left"

        if self._initialized:
            self._left_motor.backward(s)
            self._right_motor.forward(s)
        print(f"Motors: left at {s}")

    def right(self, speed: Optional[float] = None):
        """Turn right - left motor forward, right motor backward (pivot turn)"""
        s = speed if speed is not None else self.speed
        self._last_command = "right"

        if self._initialized:
            self._left_motor.forward(s)
            self._right_motor.backward(s)
        print(f"Motors: right at {s}")

    def stop(self):
        """Stop both motors"""
        self._last_command = "stop"

        if self._initialized:
            self._left_motor.stop()
            self._right_motor.stop()
        print("Motors: stopped")

    def cleanup(self):
        """Clean up GPIO resources"""
        self.stop()
        if self._initialized:
            if self._left_motor:
                self._left_motor.close()
            if self._right_motor:
                self._right_motor.close()
            self._initialized = False
        print("Motors: cleaned up")


# Global motor controller instance
_motor_controller: Optional[MotorController] = None


def get_motor_controller() -> MotorController:
    """Get or create the global motor controller instance"""
    global _motor_controller
    if _motor_controller is None:
        _motor_controller = MotorController()
    return _motor_controller


# Convenience functions
def forward(speed: Optional[float] = None):
    """Move forward"""
    get_motor_controller().forward(speed)


def backward(speed: Optional[float] = None):
    """Move backward"""
    get_motor_controller().backward(speed)


def left(speed: Optional[float] = None):
    """Turn left"""
    get_motor_controller().left(speed)


def right(speed: Optional[float] = None):
    """Turn right"""
    get_motor_controller().right(speed)


def stop():
    """Stop all motors"""
    get_motor_controller().stop()


def status() -> dict:
    """Get motor status"""
    return get_motor_controller().status


def cleanup():
    """Clean up motors"""
    global _motor_controller
    if _motor_controller:
        _motor_controller.cleanup()
        _motor_controller = None
