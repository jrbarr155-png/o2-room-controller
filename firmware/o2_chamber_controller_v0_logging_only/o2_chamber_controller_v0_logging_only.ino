/*
  o2_chamber_controller.ino  —  Phase 1: MEASUREMENT ONLY (no control yet)

  Reads every 2 seconds and prints one CSV line over USB:
    ms, o2_a, o2_b, temp_c, humidity, door, dp_pa

  Hardware (see README.md for wiring):
    - DFRobot Gravity I2C O2 sensor A  -> I2C address 0x73 (factory default)
    - DFRobot Gravity I2C O2 sensor B  -> I2C address 0x72 (set its dial switch)
    - DHT22 temp/humidity              -> digital pin 2
    - Reed switch (door sensor)        -> digital pin 3 and GND (no resistor)
    - MPXV7002DP differential pressure -> analog pin A0 (optional)

  Libraries to install (Arduino IDE > Tools > Manage Libraries):
    - "DFRobot_OxygenSensor"  by DFRobot
    - "DHT sensor library"     by Adafruit  (accept the prompt to also install Adafruit Unified Sensor)

  SAFETY: if either O2 reading reaches 23.0 %, the built-in LED flashes and
  every line is flagged. Turn the concentrator OFF and open the door.
*/

#include "DFRobot_OxygenSensor.h"
#include <DHT.h>

// ---------- settings ----------/Users/jacksonbarr/Downloads/o2_lab/o2_valve_controller/o2_valve_controller.ino
const uint8_t  O2_ADDR_A      = 0x73;   // ADDRESS_3 (default)
const uint8_t  O2_ADDR_B      = 0x72;   // ADDRESS_2 (set dial on sensor B)
const uint8_t  O2_AVG_SAMPLES = 10;     // library averages this many readings
const uint8_t  DHT_PIN        = 2;
const uint8_t  DOOR_PIN       = 3;
const uint8_t  DP_PIN         = A0;
const unsigned long PERIOD_MS = 2000;   // DHT22 can't be read faster than 2 s
const float    O2_ALARM_PCT   = 23.0;   // stay below the 23.5 % fire-hazard line

DFRobot_OxygenSensor o2a;
DFRobot_OxygenSensor o2b;
DHT dht(DHT_PIN, DHT22);

bool  haveA = false, haveB = false;
float dpZeroVolts = 2.5;                // re-measured at startup
unsigned long lastSample = 0;

float readVolts(uint8_t pin, uint8_t n) {
  long sum = 0;
  for (uint8_t i = 0; i < n; i++) { sum += analogRead(pin); delay(2); }
  return (sum / (float)n) * 5.0 / 1023.0;
}

void setup() {
  Serial.begin(115200);
  pinMode(DOOR_PIN, INPUT_PULLUP);      // closed switch (magnet near) reads LOW
  pinMode(LED_BUILTIN, OUTPUT);
  dht.begin();

  haveA = o2a.begin(O2_ADDR_A);
  haveB = o2b.begin(O2_ADDR_B);

  // Zero the pressure sensor: both ports must be open to the same air at startup.
  dpZeroVolts = readVolts(DP_PIN, 100);

  Serial.print(F("# o2_a sensor: ")); Serial.println(haveA ? F("found") : F("NOT FOUND"));
  Serial.print(F("# o2_b sensor: ")); Serial.println(haveB ? F("found") : F("NOT FOUND"));
  Serial.println(F("# Warm up 3+ minutes before trusting O2 readings."));
  Serial.println(F("ms,o2_a,o2_b,temp_c,humidity,door,dp_pa,alarm"));
}

void loop() {
  unsigned long now = millis();
  if (now - lastSample < PERIOD_MS) return;
  lastSample = now;

  float a  = haveA ? o2a.getOxygenData(O2_AVG_SAMPLES) : NAN;
  float b  = haveB ? o2b.getOxygenData(O2_AVG_SAMPLES) : NAN;
  float t  = dht.readTemperature();
  float h  = dht.readHumidity();
  int door = (digitalRead(DOOR_PIN) == HIGH) ? 1 : 0;   // 1 = door OPEN

  // MPXV7002DP: Vout = 5 * (0.2 * P_kPa + 0.5)  ->  1 V per kPa around the zero point
  float dpPa = (readVolts(DP_PIN, 20) - dpZeroVolts) * 1000.0;

  bool alarm = (a >= O2_ALARM_PCT) || (b >= O2_ALARM_PCT);
  digitalWrite(LED_BUILTIN, alarm ? ((now / 250) % 2) : LOW);

  Serial.print(now);      Serial.print(',');
  Serial.print(a, 2);     Serial.print(',');
  Serial.print(b, 2);     Serial.print(',');
  Serial.print(t, 1);     Serial.print(',');
  Serial.print(h, 1);     Serial.print(',');
  Serial.print(door);     Serial.print(',');
  Serial.print(dpPa, 0);  Serial.print(',');
  Serial.println(alarm ? 1 : 0);
}
