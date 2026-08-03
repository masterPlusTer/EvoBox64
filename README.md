# EvoBox64

> **A tiny evolving digital ecosystem running entirely on a Raspberry Pi
> Pico and a 64×64 HUB75 RGB LED matrix.**
<img width="1170" height="1560" alt="IMG_CE6B34BD-2A09-42E9-AEA9-16DB6C803DCD" src="https://github.com/user-attachments/assets/82400406-2a44-46d8-b647-9c8602ef7fb9" />


## Overview

EvoBox64 is an artificial life experiment designed to run continuously
on extremely constrained hardware.

There are:

-   🌱 Food sources
-   🐇 Herbivores
-   🦊 Predators
-   🥚 Eggs
-   🧬 Genetic mutations
-   🌧 Rain events
-   📈 Population balancing
-   🖥 Live console telemetry

Everything is generated procedurally.

There are **no bitmap animations**, **no SD card assets**, and **no
external resources**.

The entire simulation runs from a single `code.py`.

------------------------------------------------------------------------

# Hardware

## Controller

-   Raspberry Pi Pico (RP2040)
-   CircuitPython

## Display

-   HUB75 RGB LED Matrix
-   64 × 64 pixels
-   1/32 scan

## Power

-   External regulated 5 V supply for the LED panel
-   Pico powered through USB

### Rear Wiring

<img width="1152" height="1536" alt="95CA754E-1E0C-48F2-8F0F-C9C4CAEA1A6F" src="https://github.com/user-attachments/assets/1b7c9f9e-1162-4bbe-8dd8-13358e65dbb9" />


The Pico is mounted directly behind the panel using a custom harness.
The HUB75 ribbon cable connects the controller to the display while a
dedicated 5 V supply powers the LEDs.

## Pin Mapping

  HUB75   Pico GPIO
  ------- -----------
  R1      GP2
  G1      GP3
  B1      GP4
  R2      GP5
  G2      GP8
  B2      GP9
  A       GP10
  B       GP16
  C       GP18
  D       GP20
  E       GP22
  CLK     GP11
  LAT     GP12
  OE      GP13

------------------------------------------------------------------------

# Software

The project intentionally lives in a **single Python file**.

Why?

-   Easy to share
-   Easy to understand
-   Easy to modify
-   Copy one file to `CIRCUITPY`
-   Reset the Pico
-   Done.

## Current Features

-   Procedural terrain
-   Food growth
-   Herbivore AI
-   Predator AI
-   Genetic mutation
-   Egg incubation
-   Population balancing
-   Rain events
-   Console statistics
-   Real-time rendering

------------------------------------------------------------------------

# Running



The simulation never follows a scripted sequence.

Each execution creates a different world where populations expand,
collapse, recover and evolve over time.

------------------------------------------------------------------------

# Console Output

Example:

``` text
STATUS frame=12540
Herbivores: 8
Predators : 2
Eggs       : 1
Food       : 93
Rain       : False

EVENT Predator #4 hunted Herbivore #2
```

------------------------------------------------------------------------

# Roadmap

-   [x] Single-file architecture
-   [x] Procedural ecosystem
-   [x] Predator/prey simulation
-   [x] Console telemetry
-   [ ] Persistent world save/load
-   [ ] Seasons
-   [ ] Genealogy
-   [ ] Creature inspection
-   [ ] Web dashboard
-   [ ] Multiple species
-   [ ] Evolution statistics
-   [ ] Remote control API

------------------------------------------------------------------------

# Philosophy

EvoBox64 is not meant to be another LED matrix demo.

The goal is to create a tiny world that can be left running for days,
allowing complex behaviour to emerge from a small set of simple rules.

Sometimes the world flourishes.

<img width="1170" height="1560" alt="IMG_DC69CDAC-C3F6-4537-A513-BE108877E4FC" src="https://github.com/user-attachments/assets/e0e599a8-3863-467a-9683-dacfe64c3058" />
<img width="1170" height="1560" alt="IMG_CE6B34BD-2A09-42E9-AEA9-16DB6C803DCD" src="https://github.com/user-attachments/assets/cd2854c9-53ab-4ece-9a21-087f78161bbb" />


Sometimes everything collapses.

Then it starts all over again.

And that is the interesting part.

