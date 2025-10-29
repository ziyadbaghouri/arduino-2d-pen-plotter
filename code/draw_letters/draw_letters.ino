#include <math.h>           // for NAN, isnan()
#include <ctype.h>          // for tolower()
#include <AccelStepper.h>
#include <Servo.h>
#include <avr/pgmspace.h>   // for progmem()


#include "letters_all.h"

#define MotorInterfaceType 8

// ---- CONFIG ----
const float LETTER_SCALE               = 12.0f;   // overall size scaler (steps per SVG unit)
const long  SPACE_STEPS                = 400;     // gap between words
const long  LINE_SPACE_STEPS           = 800;     // gap between lines
const int   NUM_CHAR_PER_LINE          = 7;      

const int DIR_X = -1;
const int DIR_Y = -1;

const float MAX_SPEED = 350.0f;      // steps/s
const float ACCEL     = 1000.0f;     // steps/s^2

const int SERVO_PIN       = 12;
const int PEN_UP_ANGLE    = 30;      
const int PEN_DOWN_ANGLE  = 0;       
const int PEN_SETTLE_MS   = 600;     

// ---- MOTORS ----
AccelStepper X(MotorInterfaceType, 8, 10, 9, 11);
AccelStepper Y(MotorInterfaceType, 2,  4, 3,  5);
Servo pen;

// Track where a line starts so we can wrap cleanly
long g_lineStartX = 0;
long g_lineStartY = 0;
int  g_charsOnLine = 0;

static bool  g_haveRef = false;
float g_refOx = 0.0f;   // fixed glyph-space origin X 
float g_refOy = 0.0f;   // fixed glyph-space origin Y


// ---- PEN ----
void penUp(){
   pen.write(PEN_UP_ANGLE);
   delay(PEN_SETTLE_MS); 
}

void penDown(){ 
  pen.write(PEN_DOWN_ANGLE);
  delay(PEN_SETTLE_MS); 
}

// ---- Move the pen ----
void moveToXY(long tx, long ty) {
  X.moveTo(tx);
  Y.moveTo(ty);
  while (X.distanceToGo() != 0 || Y.distanceToGo() != 0) {
    X.run();
    Y.run();
  }
}


// ---- Draw the letters ----
void drawLetter_P(const float (*letter)[2], int len, float SCALE) {
  // 1) Read this glyph's first point
  int i0 = 0;

  const float ox = pgm_read_float(&letter[i0][0]);
  const float oy = pgm_read_float(&letter[i0][1]);

  // 2) Lock a global glyph-space origin once (first letter only)
  if (!g_haveRef) {
    g_refOx = ox;
    g_refOy = oy;
    g_haveRef = true;
  }

  // 3) Compute per-glyph alignment so that THIS glyph's first point maps
  const long curX = X.currentPosition();
  const long curY = Y.currentPosition();
  const long startXAligned = curX - (long)lroundf((ox - g_refOx) * SCALE * DIR_X);
  const long startYAligned = curY - (long)lroundf((oy - g_refOy) * SCALE * DIR_Y);

  // 4) Draw all points with the fixed origin + aligned starts.
  bool needPenDown = false;

  // First point maps exactly to current position; the first move is a no-op.
  for (int i = i0; i < len; i++) {
    float px = pgm_read_float(&letter[i][0]);
    float py = pgm_read_float(&letter[i][1]);

    if (isnan(px) || isnan(py)) {
      // subpath break: lift; next valid point will move & pen back down
      penUp();
      needPenDown = true;
      continue;
    }

    const long tx = startXAligned + (long)lroundf((px - g_refOx) * SCALE * DIR_X);
    const long ty = startYAligned + (long)lroundf((py - g_refOy) * SCALE * DIR_Y);

    if (needPenDown) {
      moveToXY(tx, ty); // reposition to the new subpath start
      penDown();
      needPenDown = false;
    } else {
      penDown();
      moveToXY(tx, ty);
    }
  }
}



// ---- Make a space ----
void spaceStep() {
  moveToXY(X.currentPosition() + (long)(SPACE_STEPS) * DIR_X, Y.currentPosition());
}

// ---- Return to the line ----
void newLine() {
  penUp();
  moveToXY(X.currentPosition(), g_lineStartY + (long)LINE_SPACE_STEPS * (-1 * DIR_Y));
  moveToXY(g_lineStartX, Y.currentPosition());
  g_lineStartY = Y.currentPosition();    
  g_charsOnLine = 0;
}


// ---- Get coordinates from letter_all.h, to use letter switch to return true ----
bool getCoordinates(char c, const float (*&pts)[2], uint16_t &len) {
  c = tolower((unsigned char)c);
  switch (c) {
    case 'd': pts = letter_d; len = letter_d_len; return true;
    case 'e': pts = letter_e; len = letter_e_len; return true;
    case 'f': pts = letter_f; len = letter_f_len; return true;
    case 'h': pts = letter_h; len = letter_h_len; return true;
    case 'k': pts = letter_k; len = letter_k_len; return true;
    case 'l': pts = letter_l; len = letter_l_len; return true;
    case 'm': pts = letter_m; len = letter_m_len; return true;
    case 'n': pts = letter_n; len = letter_n_len; return true;
    case 'p': pts = letter_p; len = letter_p_len; return true;
    case 'r': pts = letter_r; len = letter_r_len; return true;
    case 't': pts = letter_t; len = letter_t_len; return true;
    case 'u': pts = letter_u; len = letter_u_len; return true;
    case 'v': pts = letter_v; len = letter_v_len; return true;
    case 'w': pts = letter_w; len = letter_w_len; return true;
    case 'x': pts = letter_x; len = letter_x_len; return true;
    default: return false;
  }
}

// ---- Serial Monitor input reader ----
void serialDrawHandler(float letterSize) {
  while (Serial.available() > 0) {
    char c = Serial.read();

    // Space is typed
    if (c == ' ') {
      spaceStep();
      if (++g_charsOnLine >= NUM_CHAR_PER_LINE) newLine();
      continue;
    }

    const float (*pts)[2]; uint16_t len;;
    if (getCoordinates(c, pts, len)) {
      drawLetter_P(pts, len, letterSize);
      if (++g_charsOnLine >= NUM_CHAR_PER_LINE) newLine();
    }
  }
}

// ---- SETUP ----
void setup() {
  Serial.begin(9600);

  X.enableOutputs(); Y.enableOutputs();
  X.setMaxSpeed(MAX_SPEED); Y.setMaxSpeed(MAX_SPEED);
  X.setAcceleration(ACCEL); Y.setAcceleration(ACCEL);
  X.setCurrentPosition(0);  Y.setCurrentPosition(0);

  pen.attach(SERVO_PIN);
  penUp();

  g_lineStartX = X.currentPosition();  // 0
  g_lineStartY = Y.currentPosition();  // 0       // baseline Y = 0
}

// ---- LOOP ----
void loop() {
  serialDrawHandler(LETTER_SCALE);
}
