# University Timetable Generator

This application generates optimized course timetables for multiple student groups using Constraint Satisfaction Problem (CSP) techniques. It creates schedules that satisfy various constraints while optimizing teacher workloads.

## Features

- Generates timetables for 6 student groups simultaneously
- Shares lecture sessions across all groups, with group-specific TD and TP sessions
- Enforces hard constraints:
  - Maximum of three successive teaching slots
  - No overlapping sessions for the same course
  - Tuesday limited to 3 morning slots
  - Different courses must have different slot allocations
- Attempts to optimize soft constraints:
  - Each teacher should have a maximum of two workdays

## Technical Implementation

The system uses:
- Flask for the web application backend
- Python-constraint package for CSP implementation
- Bootstrap and custom CSS for the UI
- Constraint propagation techniques (AC3)
- Variable ordering heuristics (MRV)

## Setup and Running

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the application:
   ```bash
   python app.py
   ```

3. Open your browser and navigate to `http://127.0.0.1:5000`

## Project Structure

- `app.py`: Main application file with CSP implementation
- `templates/`: HTML templates
- `static/`: CSS and JavaScript files
- `requirements.txt`: Required Python packages

## How It Works

1. The system formulates the timetable generation as a CSP
2. Variables represent course sessions (lectures, TDs, TPs)
3. Domains are the available time slots
4. Constraints ensure schedule feasibility
5. A hybrid backtracking algorithm with AC3 pre-processing finds solutions
6. The solution is displayed as interactive timetables
