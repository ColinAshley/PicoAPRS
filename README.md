# PicoAPRS - Amateur Radio APRS Position Display

Displays last recorded APRS Position for Callsign.
Requires Pi Pico W & OLED 1.3" DriIsplay

## Table of Contents

* [Features](#features)
* [Installation](#installation)
* [Usage](#usage)

## Features

- OLED Displayed information
  - Date/Time of last postion logged
  - Current action status while operating
  - Lat/Lng coordinates
  - Altitude
  - Maidenhead Locator

- Console Logging
  - Logs all operations performed.

- Hardware indicators
  - Green LED on during Network Access

## Installation

Download all the files to your local machine.

- git clone https://github.com/ColinAshley/PicoAPRS
- cd PicoAPRS
- Edit main.py to add your Callsign, Wifi Details and APRS API Key
- Use Thonny Editor/Interface to load to Pi Pico

## Usage

Autoruns on Power Up of Pi Pico
## License

Distributed under the MIT license.
