#include <AccelStepper.h>
#define MotorInterfaceType 8 

// ---- CONFIG ----
const long SIDE_STEPS = 4000;   // steps per side of the square
const int  DIR_X = -1;          // X axis direction 
const int  DIR_Y = -1;          // Y axis direction

const float MAX_SPEED = 350.0f; // steps/sec
const float ACCEL     = 1000.0f; // steps/sec^2
const int   SEGMENTS  = 150;    // circle segments 
// ---- motors ----
AccelStepper X(MotorInterfaceType, 8, 10, 9, 11);
AccelStepper Y(MotorInterfaceType, 2,  4, 3,  5);

// Move both axes to absolute targets (tx,ty) and block until both arrive.
void moveToXY_blocking(long tx, long ty) {
  X.moveTo(tx);
  Y.moveTo(ty);
  while (X.distanceToGo() != 0 || Y.distanceToGo() != 0) {
    X.run();
    Y.run();
  }
}

void setup() {
  Serial.begin(9600);
  delay(2000);

  // enable + configure
  X.enableOutputs(); Y.enableOutputs();
  X.setMaxSpeed(MAX_SPEED); Y.setMaxSpeed(MAX_SPEED);
  X.setAcceleration(ACCEL); Y.setAcceleration(ACCEL);
  X.setCurrentPosition(0);  Y.setCurrentPosition(0);

  // ---- Square start at (0,0) ----
  Serial.println(F("Start: draw square"));
  moveToXY_blocking(0, DIR_Y * (SIDE_STEPS / 2.0f)); // (0, -3000)
  moveToXY_blocking(DIR_X * SIDE_STEPS, DIR_Y * (SIDE_STEPS / 2.0f)); // (-6000, -3000)
  moveToXY_blocking(DIR_X * SIDE_STEPS, -DIR_Y * (SIDE_STEPS / 2.0f)); // (-6000, 3000)
  moveToXY_blocking(0, -DIR_Y * (SIDE_STEPS / 2.0f)); // (0, 3000)
  moveToXY_blocking(0,0); // (0, 0)
  Serial.println(F("Square done"));

  // circle center:
  const long cx = DIR_X * (SIDE_STEPS / 2.0f);
  const long cy = 0;

  // Inscribed circle radius 
  const long r = lround(SIDE_STEPS / 2.0f);

  // Draw circle
  Serial.println(F("Drawing circle"));
  const float theta0 = 0;
  for (int i = 0; i <= SEGMENTS; ++i) {
    float theta = theta0 + (TWO_PI * i) / SEGMENTS; 
    long tx = lround(cx + r * cos(theta));
    long ty = lround(cy + r * sin(theta));
    moveToXY_blocking(tx, ty);
  }
    Serial.println(F("Circle done"));
    X.disableOutputs(); Y.disableOutputs();
}

void loop() {
  // nothing: all work performed in setup()
}
