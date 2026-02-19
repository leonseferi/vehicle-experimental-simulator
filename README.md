# Vehicle Experimental Simulator 🚗

This is a project i've worked on for a while - finally came round to publishing.

A modular physics-driven vehicle simulation engine built using Python and Pygame.

## Overview

This project implements a full interactive vehicle simulation environment with:

- Real-time physics modelling
- Vehicle parameter tuning system
- User authentication with custom multi-pass hashing
- SQLite-backed persistence layer
- Modular UI state-machine architecture
- Leaderboard and performance tracking

## Architecture

The project follows a modular separation of concerns:

- `main.py` – Application entry and state machine
- `config.py` – Centralised simulation constants
- `database.py` – SQLite data layer and schema management
- `hashing.py` – Custom iterative password hashing implementation
- `ui/` – Menu and interface modules
- `game/` – Core simulation logic

## Features

- Config-driven physics constants
- Adjustable torque, drag, gear ratio, suspension and more
- Secure user registration & login
- Persistent vehicle customisation
- Score storage via JSON
- Optimised rendering loop (200 FPS cap)

## Tech Stack

- Python
- Pygame
- SQLite3
- Object-Oriented Design
- Modular Software Architecture

