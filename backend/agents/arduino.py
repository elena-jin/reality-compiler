"""Arduino Agent – generates wiring diagrams and code snippets.

Provides pin mappings, wiring instructions, and starter Arduino code
for hardware projects that include electronics.
"""

from __future__ import annotations

import logging
from typing import Optional

from backend.schemas import ArduinoWiring, ArduinoPin, BillOfMaterials

logger = logging.getLogger("reality_compiler.arduino_agent")


async def generate_arduino(
    prompt: str,
    bom: BillOfMaterials,
) -> Optional[ArduinoWiring]:
    """Generate Arduino wiring and code based on prompt and BOM."""
    lp = prompt.lower()

    # Only generate for electronics projects
    has_electronics = any(
        w in lp for w in [
            "robot", "gripper", "servo", "motor", "sensor", "led",
            "drone", "arduino", "car", "rover", "line", "sort",
            "arm", "claw", "grabber", "light", "lamp", "automatic",
        ]
    )
    if not has_electronics:
        return None

    logger.info("Arduino agent: generating wiring for '%s'", prompt[:80])

    if any(w in lp for w in ["gripper", "robot", "claw", "grabber", "arm"]):
        return _robot_arm_wiring()
    if any(w in lp for w in ["drone", "quadcopter", "uav"]):
        return _drone_wiring()
    if any(w in lp for w in ["car", "rover", "wheeled", "line follower"]):
        return _wheeled_robot_wiring()
    if any(w in lp for w in ["sort", "coin"]):
        return _sorter_wiring()
    if any(w in lp for w in ["lamp", "light", "led"]):
        return _lamp_wiring()

    return _generic_wiring()


def _robot_arm_wiring() -> ArduinoWiring:
    return ArduinoWiring(
        board="Arduino Nano",
        pins=[
            ArduinoPin(pin="D3", component="Base Servo (MG996R)", wire_color="orange", note="PWM signal"),
            ArduinoPin(pin="D5", component="Shoulder Servo (MG996R)", wire_color="orange", note="PWM signal"),
            ArduinoPin(pin="D6", component="Elbow Servo (MG996R)", wire_color="orange", note="PWM signal"),
            ArduinoPin(pin="D9", component="Wrist Rotate Servo (SG90)", wire_color="orange", note="PWM signal"),
            ArduinoPin(pin="D10", component="Wrist Pitch Servo (SG90)", wire_color="orange", note="PWM signal"),
            ArduinoPin(pin="D11", component="Gripper Servo (SG90)", wire_color="orange", note="PWM signal"),
            ArduinoPin(pin="5V", component="Servo Power (via PCA9685)", wire_color="red", note="Use external 6V supply for servos"),
            ArduinoPin(pin="GND", component="Common Ground", wire_color="black", note="Shared between Arduino and servo PSU"),
            ArduinoPin(pin="A4", component="PCA9685 SDA", wire_color="blue", note="I2C data"),
            ArduinoPin(pin="A5", component="PCA9685 SCL", wire_color="yellow", note="I2C clock"),
        ],
        libraries=["Servo.h", "Wire.h", "Adafruit_PWMServoDriver.h"],
        code_snippet="""#include <Servo.h>

Servo baseServo, shoulderServo, elbowServo;
Servo wristRotate, wristPitch, gripperServo;

void setup() {
  baseServo.attach(3);
  shoulderServo.attach(5);
  elbowServo.attach(6);
  wristRotate.attach(9);
  wristPitch.attach(10);
  gripperServo.attach(11);

  // Home position
  baseServo.write(90);
  shoulderServo.write(90);
  elbowServo.write(90);
  wristRotate.write(90);
  wristPitch.write(90);
  gripperServo.write(30); // Open gripper
}

void loop() {
  // Example: sweep base servo
  for (int pos = 0; pos <= 180; pos++) {
    baseServo.write(pos);
    delay(15);
  }
  for (int pos = 180; pos >= 0; pos--) {
    baseServo.write(pos);
    delay(15);
  }
}""",
    )


def _drone_wiring() -> ArduinoWiring:
    return ArduinoWiring(
        board="Arduino Nano (Flight Controller)",
        pins=[
            ArduinoPin(pin="D3", component="ESC Motor 1 (Front-Right)", wire_color="white", note="PWM 1000-2000µs"),
            ArduinoPin(pin="D5", component="ESC Motor 2 (Front-Left)", wire_color="white", note="PWM 1000-2000µs"),
            ArduinoPin(pin="D6", component="ESC Motor 3 (Back-Right)", wire_color="white", note="PWM 1000-2000µs"),
            ArduinoPin(pin="D9", component="ESC Motor 4 (Back-Left)", wire_color="white", note="PWM 1000-2000µs"),
            ArduinoPin(pin="A4", component="MPU6050 SDA", wire_color="blue", note="I2C Gyro/Accel"),
            ArduinoPin(pin="A5", component="MPU6050 SCL", wire_color="yellow", note="I2C Gyro/Accel"),
            ArduinoPin(pin="D2", component="RC Receiver CH1", wire_color="green", note="Throttle"),
            ArduinoPin(pin="D4", component="RC Receiver CH2", wire_color="green", note="Roll"),
            ArduinoPin(pin="D7", component="RC Receiver CH3", wire_color="green", note="Pitch"),
            ArduinoPin(pin="D8", component="RC Receiver CH4", wire_color="green", note="Yaw"),
            ArduinoPin(pin="VIN", component="Battery (3S LiPo 11.1V)", wire_color="red", note="Via voltage regulator"),
            ArduinoPin(pin="GND", component="Common Ground", wire_color="black", note="All grounds tied"),
        ],
        libraries=["Servo.h", "Wire.h", "MPU6050.h"],
        code_snippet="""#include <Servo.h>
#include <Wire.h>
#include <MPU6050.h>

Servo esc[4];
MPU6050 mpu;

void setup() {
  Wire.begin();
  mpu.initialize();

  esc[0].attach(3);  // FR
  esc[1].attach(5);  // FL
  esc[2].attach(6);  // BR
  esc[3].attach(9);  // BL

  // Arm ESCs
  for (int i = 0; i < 4; i++) {
    esc[i].writeMicroseconds(1000);
  }
  delay(2000);
}

void loop() {
  int16_t ax, ay, az, gx, gy, gz;
  mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);

  // Simple stabilization loop
  int throttle = 1200; // Base throttle
  int rollCorrection = map(gy, -32768, 32767, -100, 100);
  int pitchCorrection = map(gx, -32768, 32767, -100, 100);

  esc[0].writeMicroseconds(throttle - rollCorrection + pitchCorrection);
  esc[1].writeMicroseconds(throttle + rollCorrection + pitchCorrection);
  esc[2].writeMicroseconds(throttle - rollCorrection - pitchCorrection);
  esc[3].writeMicroseconds(throttle + rollCorrection - pitchCorrection);

  delay(10);
}""",
    )


def _wheeled_robot_wiring() -> ArduinoWiring:
    return ArduinoWiring(
        board="Arduino Nano",
        pins=[
            ArduinoPin(pin="D5", component="L298N IN1 (Left Motor)", wire_color="orange", note="Direction A"),
            ArduinoPin(pin="D6", component="L298N IN2 (Left Motor)", wire_color="orange", note="Direction B"),
            ArduinoPin(pin="D9", component="L298N IN3 (Right Motor)", wire_color="yellow", note="Direction A"),
            ArduinoPin(pin="D10", component="L298N IN4 (Right Motor)", wire_color="yellow", note="Direction B"),
            ArduinoPin(pin="D3", component="L298N ENA (Left Speed)", wire_color="white", note="PWM speed control"),
            ArduinoPin(pin="D11", component="L298N ENB (Right Speed)", wire_color="white", note="PWM speed control"),
            ArduinoPin(pin="D2", component="HC-SR04 Trig", wire_color="blue", note="Ultrasonic trigger"),
            ArduinoPin(pin="D4", component="HC-SR04 Echo", wire_color="green", note="Ultrasonic echo"),
            ArduinoPin(pin="A0", component="IR Sensor Left", wire_color="purple", note="Line follower"),
            ArduinoPin(pin="A1", component="IR Sensor Right", wire_color="purple", note="Line follower"),
            ArduinoPin(pin="VIN", component="Battery Pack (4x AA)", wire_color="red", note="6V via holder"),
            ArduinoPin(pin="GND", component="Common Ground", wire_color="black", note=""),
        ],
        libraries=["NewPing.h"],
        code_snippet="""#include <NewPing.h>

#define TRIG 2
#define ECHO 4
#define MAX_DIST 200

NewPing sonar(TRIG, ECHO, MAX_DIST);

void setup() {
  pinMode(5, OUTPUT); pinMode(6, OUTPUT);   // Left motor
  pinMode(9, OUTPUT); pinMode(10, OUTPUT);  // Right motor
  pinMode(3, OUTPUT); pinMode(11, OUTPUT);  // Speed
  Serial.begin(9600);
}

void forward(int speed) {
  analogWrite(3, speed); analogWrite(11, speed);
  digitalWrite(5, HIGH); digitalWrite(6, LOW);
  digitalWrite(9, HIGH); digitalWrite(10, LOW);
}

void stop() {
  analogWrite(3, 0); analogWrite(11, 0);
}

void loop() {
  int dist = sonar.ping_cm();
  if (dist > 0 && dist < 20) {
    stop();
    delay(500);
  } else {
    forward(180);
  }
  delay(50);
}""",
    )


def _sorter_wiring() -> ArduinoWiring:
    return ArduinoWiring(
        board="Arduino Nano",
        pins=[
            ArduinoPin(pin="D9", component="Sorting Servo (SG90)", wire_color="orange", note="PWM signal"),
            ArduinoPin(pin="D2", component="IR Break-beam Sensor", wire_color="green", note="Coin detect"),
            ArduinoPin(pin="A0", component="Coin Size Sensor (IR Range)", wire_color="purple", note="Analog distance"),
            ArduinoPin(pin="D3", component="Vibration Motor", wire_color="white", note="Hopper agitation"),
            ArduinoPin(pin="5V", component="Sensors Power", wire_color="red", note=""),
            ArduinoPin(pin="GND", component="Common Ground", wire_color="black", note=""),
        ],
        libraries=["Servo.h"],
        code_snippet="""#include <Servo.h>

Servo sortServo;
const int COIN_SENSOR = 2;
const int SIZE_SENSOR = A0;

void setup() {
  sortServo.attach(9);
  pinMode(COIN_SENSOR, INPUT);
  sortServo.write(90); // Center
  Serial.begin(9600);
}

void loop() {
  if (digitalRead(COIN_SENSOR) == LOW) {
    int size = analogRead(SIZE_SENSOR);

    if (size > 800) sortServo.write(30);       // 1p bin
    else if (size > 600) sortServo.write(70);  // 5p bin
    else if (size > 400) sortServo.write(110); // 10p bin
    else sortServo.write(150);                  // £1 bin

    delay(500);
    sortServo.write(90); // Reset
    delay(200);
  }
}""",
    )


def _lamp_wiring() -> ArduinoWiring:
    return ArduinoWiring(
        board="Arduino Nano",
        pins=[
            ArduinoPin(pin="D9", component="MOSFET Gate (LED Driver)", wire_color="yellow", note="PWM dimming"),
            ArduinoPin(pin="A0", component="Potentiometer (Brightness)", wire_color="white", note="Analog input"),
            ArduinoPin(pin="D2", component="Touch Sensor (On/Off)", wire_color="blue", note="Digital interrupt"),
            ArduinoPin(pin="5V", component="USB-C Power Module", wire_color="red", note="5V input from USB-C"),
            ArduinoPin(pin="GND", component="Common Ground", wire_color="black", note=""),
        ],
        libraries=[],
        code_snippet="""const int LED_PIN = 9;
const int POT_PIN = A0;
const int TOUCH_PIN = 2;
volatile bool isOn = true;

void setup() {
  pinMode(LED_PIN, OUTPUT);
  pinMode(TOUCH_PIN, INPUT);
  attachInterrupt(digitalPinToInterrupt(TOUCH_PIN), toggle, RISING);
}

void toggle() { isOn = !isOn; }

void loop() {
  if (isOn) {
    int brightness = map(analogRead(POT_PIN), 0, 1023, 0, 255);
    analogWrite(LED_PIN, brightness);
  } else {
    analogWrite(LED_PIN, 0);
  }
  delay(20);
}""",
    )


def _generic_wiring() -> ArduinoWiring:
    return ArduinoWiring(
        board="Arduino Nano",
        pins=[
            ArduinoPin(pin="D9", component="Actuator (Servo/Motor)", wire_color="orange", note="PWM output"),
            ArduinoPin(pin="A0", component="Sensor Input", wire_color="green", note="Analog read"),
            ArduinoPin(pin="D2", component="Button / Switch", wire_color="blue", note="Digital input"),
            ArduinoPin(pin="D13", component="Status LED", wire_color="yellow", note="Built-in LED"),
            ArduinoPin(pin="5V", component="Power", wire_color="red", note=""),
            ArduinoPin(pin="GND", component="Ground", wire_color="black", note=""),
        ],
        libraries=["Servo.h"],
        code_snippet="""#include <Servo.h>

Servo actuator;
const int SENSOR = A0;
const int BUTTON = 2;

void setup() {
  actuator.attach(9);
  pinMode(BUTTON, INPUT_PULLUP);
  Serial.begin(9600);
}

void loop() {
  int sensorVal = analogRead(SENSOR);
  int angle = map(sensorVal, 0, 1023, 0, 180);

  if (digitalRead(BUTTON) == LOW) {
    actuator.write(angle);
  }
  delay(20);
}""",
    )
