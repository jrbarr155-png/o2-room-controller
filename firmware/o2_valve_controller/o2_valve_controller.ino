/*
  o2_valve_controller.ino  —  Phase 2: MEASUREMENT + VALVE CONTROL

  Same sensors and same first 8 log columns as o2_chamber_controller.ino,
  so analyze_run.py and old data keep working. Adds a relay-driven 3-way
  valve that sends concentrator O2 either into the ROOM or out the VENT.

  Log columns (every 2 s):
    ms,o2_a,o2_b,temp_c,humidity,door,dp_pa,alarm,o2_avg,valve,mode,reason,o2_smooth
      door   1 = open, 0 = shut
      valve  1 = O2 going to ROOM, 0 = VENT
      mode   v = vent hold, p = room hold (fill run), r = reactive, f = feedforward
      reason why the valve is where it is (start, manual, low, high, door, boost, hold, alarm, sensor)
             door = door open, boost = door shut but boost timer running,
             hold = boost finished, waiting out the switch timer before the band takes over

  Wiring:
    O2 sensor A (0x73), O2 sensor B (0x72) -> I2C (SDA A4, SCL A5)
    DHT22                                  -> pin 2
    Door reed switch                       -> pin 3 + GND
    Relay module IN                        -> pin 4   (module VCC -> 5V, GND -> GND)
    Relay jumper set to H (high-level trigger): pin 4 HIGH = relay ON = valve to ROOM
    Valve wired through relay COM + NO, so no power = VENT (fail-safe)

  Commands (type in Serial Monitor with "Newline", or into log_serial.py):
    v  vent hold (default at power-up)     p  room hold (fill runs)
    r  reactive controller                 f  feedforward controller
    c  click test: relay toggles 5x (only from vent mode)
    x  clear a latched O2 alarm (only once both sensors are below 22.5%)
    ?  print current settings
    L21.45  set low line  (valve to room below this)
    H21.55  set high line (valve to vent above this)
    B120    feedforward boost time after the door shuts, seconds
    S30     minimum time between band switches, seconds

  CONTROL RULES, checked in this order every loop:
    1. Alarm (either sensor >= 23.0%)  -> VENT, latched until you type x
    2. Sensor fault (missing, outside 15-25%, or A/B differ by > 0.5) -> VENT
    3. Mode v -> VENT;  mode p -> ROOM
    4. Mode f only: door opens -> ROOM immediately (skips the switch timer),
       held while the door is open and for B seconds after it shuts
    5. Modes r and f: 60-s average below low line -> ROOM, above high line -> VENT,
       in between -> no change; at least S seconds between these switches
*/

#include "DFRobot_OxygenSensor.h"
#include <DHT.h>
#include <math.h>
#include <stdlib.h>

// ---------- fixed settings ----------
const uint8_t  O2_ADDR_A      = 0x73;
const uint8_t  O2_ADDR_B      = 0x72;
const uint8_t  O2_AVG_SAMPLES = 10;
const uint8_t  DHT_PIN        = 2;
const uint8_t  DOOR_PIN       = 3;
const uint8_t  VALVE_PIN      = 4;
const uint8_t  DP_PIN         = A0;
const unsigned long PERIOD_MS        = 2000;
const unsigned long DOOR_DEBOUNCE_MS = 50;
const float    O2_ALARM_PCT    = 23.0;   // stay well below the 23.5% fire-hazard line
const float    ALARM_CLEAR_PCT = 22.5;
const float    SENSOR_MIN      = 15.0;   // warm-up dip (10-14%) counts as a fault -> vent
const float    SENSOR_MAX      = 25.0;   // top of the sensors' range
const float    SENSOR_MAX_DIFF = 0.5;    // A and B should agree within this

// ---------- settings you can change at runtime ----------
// PLACEHOLDERS until the fill run shows where the room actually levels off.
float lowLine  = 21.45;
float highLine = 21.55;
unsigned long boostMs     = 120000UL;
unsigned long minSwitchMs = 30000UL;

enum Mode { M_VENT, M_ROOM, M_REACTIVE, M_FEEDFORWARD };
Mode mode = M_VENT;

DFRobot_OxygenSensor o2a;
DFRobot_OxygenSensor o2b;
DHT dht(DHT_PIN, DHT22);

bool  haveA = false, haveB = false;
float dpZeroVolts = 2.5;
unsigned long lastSample = 0;

bool  valveRoom = false;
unsigned long lastSwitch = 0;
const char* reason = "start";

bool  alarmLatched = false;
bool  sensorsOK = false;
float lastA = NAN, lastB = NAN, lastAvg = NAN;

// Band control uses a 60-second moving average (30 readings x 2 s), because the
// sensor noise (about +/-0.04) is close to the width of the control band.
const uint8_t SMOOTH_N = 30;
float smoothBuf[SMOOTH_N];
uint8_t smoothCount = 0, smoothIdx = 0;
float smoothAvg = NAN;

bool  doorOpen = false;
bool  doorRaw = false;
unsigned long doorChangedAt = 0;

bool  boosting = false;
unsigned long boostEndsAt = 0;

char  cmdBuf[16];
uint8_t cmdLen = 0;

// ------------------------------------------------------------------
char modeChar(Mode m) {
  switch (m) {
    case M_ROOM:        return 'p';
    case M_REACTIVE:    return 'r';
    case M_FEEDFORWARD: return 'f';
    default:            return 'v';
  }
}

float readVolts(uint8_t pin, uint8_t n) {
  long sum = 0;
  for (uint8_t i = 0; i < n; i++) { sum += analogRead(pin); delay(2); }
  return (sum / (float)n) * 5.0 / 1023.0;
}

// Move the valve. force = true skips the minimum-switch timer (safety, manual, door).
void setValve(bool room, const char* why, bool force) {
  if (room == valveRoom) return;
  unsigned long now = millis();
  if (!force && (now - lastSwitch) < minSwitchMs) return;
  digitalWrite(VALVE_PIN, room ? HIGH : LOW);
  valveRoom  = room;
  lastSwitch = now;
  reason     = why;
  Serial.print(F("# valve "));
  Serial.print(room ? F("ROOM") : F("VENT"));
  Serial.print(F(" ("));  Serial.print(why);
  Serial.print(F(") at ms=")); Serial.println(now);
}

void printSettings() {
  Serial.print(F("# settings mode="));   Serial.print(modeChar(mode));
  Serial.print(F(" low="));              Serial.print(lowLine, 2);
  Serial.print(F(" high="));             Serial.print(highLine, 2);
  Serial.print(F(" boost_s="));          Serial.print(boostMs / 1000UL);
  Serial.print(F(" min_switch_s="));     Serial.print(minSwitchMs / 1000UL);
  Serial.print(F(" alarm_latched="));    Serial.println(alarmLatched ? 1 : 0);
}

void setMode(Mode m) {
  mode = m;
  boosting = false;
  Serial.print(F("# mode -> ")); Serial.println(modeChar(m));
  printSettings();
}

void clickTest() {
  if (mode != M_VENT) { Serial.println(F("# click test only runs in vent mode (type v first)")); return; }
  Serial.println(F("# click test: 5 toggles"));
  for (uint8_t i = 0; i < 5; i++) {
    digitalWrite(VALVE_PIN, HIGH); digitalWrite(LED_BUILTIN, HIGH); delay(1000);
    digitalWrite(VALVE_PIN, LOW);  digitalWrite(LED_BUILTIN, LOW);  delay(1000);
  }
  valveRoom = false;
  Serial.println(F("# click test done, valve at VENT"));
}

void handleCommand(char* s) {
  char c = s[0];
  float val = atof(s + 1);
  switch (c) {
    case 'v': setMode(M_VENT);        break;
    case 'p': setMode(M_ROOM);        break;
    case 'r': setMode(M_REACTIVE);    break;
    case 'f': setMode(M_FEEDFORWARD); break;
    case 'c': clickTest();            break;
    case '?': printSettings();        break;
    case 'x':
      if ((!haveA || lastA < ALARM_CLEAR_PCT) && (!haveB || lastB < ALARM_CLEAR_PCT)) {
        alarmLatched = false;
        Serial.println(F("# alarm cleared"));
      } else {
        Serial.println(F("# O2 still too high to clear the alarm"));
      }
      break;
    case 'L':
      if (val >= 19.0 && val < highLine) { lowLine = val; printSettings(); }
      else Serial.println(F("# rejected: low line must be >= 19.0 and below the high line"));
      break;
    case 'H':
      if (val > lowLine && val <= 22.8) { highLine = val; printSettings(); }
      else Serial.println(F("# rejected: high line must be above the low line and <= 22.8"));
      break;
    case 'B':
      if (val >= 0 && val <= 900) { boostMs = (unsigned long)(val * 1000.0); printSettings(); }
      else Serial.println(F("# rejected: boost must be 0-900 s"));
      break;
    case 'S':
      if (val >= 5 && val <= 300) { minSwitchMs = (unsigned long)(val * 1000.0); printSettings(); }
      else Serial.println(F("# rejected: min switch must be 5-300 s"));
      break;
    default:
      Serial.println(F("# unknown command (v p r f c x ? L H B S)"));
  }
}

void readCommands() {
  while (Serial.available()) {
    char ch = Serial.read();
    if (ch == '\n' || ch == '\r') {
      if (cmdLen > 0) { cmdBuf[cmdLen] = '\0'; handleCommand(cmdBuf); cmdLen = 0; }
    } else if (cmdLen < sizeof(cmdBuf) - 1) {
      cmdBuf[cmdLen++] = ch;
    }
  }
}

void onDoorChange(unsigned long now) {
  Serial.print(F("# door ")); Serial.print(doorOpen ? F("OPEN") : F("SHUT"));
  Serial.print(F(" at ms=")); Serial.println(now);
  if (mode != M_FEEDFORWARD) return;
  if (doorOpen) {
    if (!alarmLatched && sensorsOK) {
      boosting = true;
      setValve(true, "door", true);          // the feedforward move: act before O2 drops
    }
  } else if (boosting) {
    boostEndsAt = now + boostMs;             // keep boosting for B seconds after it shuts
  }
}

void pollDoor(unsigned long now) {
  bool r = (digitalRead(DOOR_PIN) == HIGH);  // INPUT_PULLUP: HIGH = magnet away = open
  if (r != doorRaw) { doorRaw = r; doorChangedAt = now; }
  if ((now - doorChangedAt) >= DOOR_DEBOUNCE_MS && r != doorOpen) {
    doorOpen = r;
    onDoorChange(now);
  }
}

void bandControl() {
  if (isnan(smoothAvg) || smoothCount < SMOOTH_N) return;   // wait for a full minute of data
  if (smoothAvg < lowLine)       setValve(true,  "low",  false);
  else if (smoothAvg > highLine) setValve(false, "high", false);
  // in between: hold (hysteresis keeps the valve from chattering)
}

void control(unsigned long now) {
  if (alarmLatched) { boosting = false; setValve(false, "alarm",  true); return; }
  if (!sensorsOK)   { boosting = false; setValve(false, "sensor", true); return; }

  switch (mode) {
    case M_VENT: setValve(false, "manual", true); return;
    case M_ROOM: setValve(true,  "manual", true); return;
    case M_FEEDFORWARD:
      if (boosting) {
        if (doorOpen || (long)(now - boostEndsAt) < 0) {
          setValve(true, "door", true);
          reason = doorOpen ? "door" : "boost";   // label the phase even when the valve is already at ROOM
          return;
        }
        boosting = false;
        reason = "hold";    // boost over; band logic takes over after the S-second timer
        Serial.print(F("# boost ended at ms=")); Serial.println(now);
        lastSwitch = now;   // band logic waits S seconds before overriding the boost
      }
      bandControl();
      return;
    case M_REACTIVE:
      bandControl();
      return;
  }
}

void sampleAndLog(unsigned long now) {
  float a  = haveA ? o2a.getOxygenData(O2_AVG_SAMPLES) : NAN;
  float b  = haveB ? o2b.getOxygenData(O2_AVG_SAMPLES) : NAN;
  float t  = dht.readTemperature();
  float h  = dht.readHumidity();
  float dpPa = (readVolts(DP_PIN, 20) - dpZeroVolts) * 1000.0;
  lastA = a; lastB = b;

  // alarm latches on either sensor
  if ((haveA && a >= O2_ALARM_PCT) || (haveB && b >= O2_ALARM_PCT)) {
    if (!alarmLatched) Serial.println(F("# O2 ALARM: valve forced to VENT. Turn the unit OFF and open the door."));
    alarmLatched = true;
  }

  // sensor sanity: every sensor found at boot must read in range, and they must agree
  bool okA = !haveA || (!isnan(a) && a >= SENSOR_MIN && a <= SENSOR_MAX);
  bool okB = !haveB || (!isnan(b) && b >= SENSOR_MIN && b <= SENSOR_MAX);
  bool agree = !(haveA && haveB) || fabs(a - b) <= SENSOR_MAX_DIFF;
  sensorsOK = (haveA || haveB) && okA && okB && agree;
  if (haveA && haveB)  lastAvg = (a + b) / 2.0;
  else if (haveA)      lastAvg = a;
  else if (haveB)      lastAvg = b;
  else                 lastAvg = NAN;

  if (sensorsOK && !isnan(lastAvg)) {
    smoothBuf[smoothIdx] = lastAvg;
    smoothIdx = (smoothIdx + 1) % SMOOTH_N;
    if (smoothCount < SMOOTH_N) smoothCount++;
    float s = 0;
    for (uint8_t i = 0; i < smoothCount; i++) s += smoothBuf[i];
    smoothAvg = s / smoothCount;
  }

  control(now);   // react to the new reading right away

  Serial.print(now);      Serial.print(',');
  Serial.print(a, 2);     Serial.print(',');
  Serial.print(b, 2);     Serial.print(',');
  Serial.print(t, 1);     Serial.print(',');
  Serial.print(h, 1);     Serial.print(',');
  Serial.print(doorOpen ? 1 : 0); Serial.print(',');
  Serial.print(dpPa, 0);  Serial.print(',');
  Serial.print(alarmLatched ? 1 : 0); Serial.print(',');
  Serial.print(lastAvg, 3); Serial.print(',');
  Serial.print(valveRoom ? 1 : 0); Serial.print(',');
  Serial.print(modeChar(mode)); Serial.print(',');
  Serial.print(reason);     Serial.print(',');
  Serial.println(smoothAvg, 3);
}

// ------------------------------------------------------------------
void setup() {
  // Valve OFF (vent) before anything else happens.
  digitalWrite(VALVE_PIN, LOW);
  pinMode(VALVE_PIN, OUTPUT);
  digitalWrite(VALVE_PIN, LOW);

  Serial.begin(115200);
  pinMode(DOOR_PIN, INPUT_PULLUP);
  pinMode(LED_BUILTIN, OUTPUT);
  dht.begin();

  haveA = o2a.begin(O2_ADDR_A);
  haveB = o2b.begin(O2_ADDR_B);
  dpZeroVolts = readVolts(DP_PIN, 100);

  doorRaw = doorOpen = (digitalRead(DOOR_PIN) == HIGH);
  lastSwitch = millis();

  Serial.println(F("# o2_valve_controller v2 (60-s smoothing for band control)"));
  Serial.print(F("# o2_a sensor: ")); Serial.println(haveA ? F("found") : F("NOT FOUND"));
  Serial.print(F("# o2_b sensor: ")); Serial.println(haveB ? F("found") : F("NOT FOUND"));
  Serial.println(F("# Warm up 10+ minutes; the valve stays at VENT until readings are in range."));
  Serial.println(F("# Commands: v p r f c x ? L<pct> H<pct> B<sec> S<sec>"));
  printSettings();
  Serial.println(F("ms,o2_a,o2_b,temp_c,humidity,door,dp_pa,alarm,o2_avg,valve,mode,reason,o2_smooth"));
}

void loop() {
  unsigned long now = millis();
  readCommands();
  pollDoor(now);       // checked every pass so feedforward reacts right away
  control(now);

  // LED: fast flash = alarm, solid = valve at ROOM, off = VENT
  digitalWrite(LED_BUILTIN, alarmLatched ? ((now / 250) % 2) : (valveRoom ? HIGH : LOW));

  if (now - lastSample >= PERIOD_MS) {
    lastSample = now;
    sampleAndLog(now);
  }
}
