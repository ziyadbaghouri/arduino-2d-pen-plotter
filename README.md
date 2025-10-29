# 🖊️ Arduino 2D Pen Plotter

A compact two-axis **Arduino-driven pen plotter** that draws shapes and text on paper using two stepper motors, timing belts, and a servo-controlled pen-lifting mechanism.

This project was developed as the **Individual Project** for the EPFL “Making Intelligent Things” course (Spring 2025).  
It combines **mechanical design (CAD + laser cutting + 3D printing)** with **embedded control programming** on Arduino.

---

## ✨ Overview

The 2D Plotter translates digital drawings into physical motion through:
- **Two orthogonal linear axes** (X and Y) driven by 28BYJ-48 stepper motors via GT2 belts,  
- A **servo-actuated pen holder** for lift/lower control, and  
- An **Arduino Uno** that synchronizes both movements using the AccelStepper library.

---

## 🧠 Hardware Architecture

| Category | Component | Function |
|-----------|------------|-----------|
| **Microcontroller** | Arduino Uno | Central controller for motion and servo commands |
| **Motors** | 2 × 28BYJ-48 5 V steppers | Drive X- and Y-axis movement |
| **Motor Drivers** | 2 × ULN2003 boards | Control signals from the Uno to the stepper coils |
| **Servo** | SG90 9 g servo | Raises and lowers the pen |
| **Transmission** | 2 × GT2 belts (40 cm & 62 cm) + 2 × GT2 pulleys (5 mm) | Belt-driven linear motion |
| **Structure** | Combination of laser-cut MDF parts and 3D-printed PETG components | Provides a stable and lightweight frame |
| **Power** | 5 V USB breakout board + micro-USB cable | Dedicated supply for motors and servo |

All grounds are common between Arduino, stepper drivers, and servo.  
External 5 V power avoids overloading the Arduino’s regulator.

---

## 🧱 Mechanical Design

The complete mechanical assembly is provided in [`/cad/design.step`](cad/design.step).

The pen holder uses a **spring-loaded sliding design**:  
when the servo moves down, the pen holder can **slide backward slightly** against the spring tension.  
This prevents excessive pressure on the pen tip and protects the servo gears from overload, ensuring smoother contact with the paper surface and more consistent line thickness during plotting.

---

## 🧩 Electronics Diagram

![Wiring diagram](images/Circuit_Diagram.png)  
---
