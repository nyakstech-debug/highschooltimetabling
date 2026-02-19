# SchoolTimetable - Intelligent Timetabling System

A web-based timetabling system designed specifically for Kenyan high schools. The system automatically generates fair and conflict-free timetables while respecting all constraints and preferences.

## Features

- **School Registration & Authentication**: Secure login system for schools
- **Teacher Management**: Add and manage teachers with multi-subject support
- **Class Configuration**: Define classes by form level and stream
- **Subject Management**: Configure subjects with:
  - Maximum lessons per week
  - Double lesson requirements (consecutive periods)
  - Subject codes
- **Time Slot Configuration**: Define lesson periods with start/end times for each day
- **Teacher-Subject Assignments**: Assign teachers to teach specific subjects
- **Concurrent Subject Handling**: Mark subjects that can be taught at the same time
- **Automatic Timetable Generation**: 
  - Fair distribution of lessons
  - Conflict-free scheduling
  - Respect for all constraints
  - Load balancing across the week
- **Multiple Views**:
  - Block timetable (entire school)
  - Individual teacher timetables
  - Individual class timetables
- **Timetable History**: Track and manage generated timetables

## Tech Stack

- **Backend**: Flask (Python)
- **Database**: SQLite
- **Frontend**: Bootstrap 4, HTML5, CSS3
- **Authentication**: Flask-Login

## Installation

### Prerequisites
- Python 3.7+
- pip (Python package manager)

### Setup

1. **Clone or download the project**
   ```bash
   cd timetabling
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment**
   
   On Windows:
   ```bash
   venv\Scripts\activate
   ```
   
   On macOS/Linux:
   ```bash
   source venv/bin/activate
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Access the application**
   Open your web browser and navigate to:
   ```
   http://localhost:5000
   ```

## Usage

### Getting Started

1. **Register a School Account**
   - Click "Register" on the home page
   - Enter school name, email, location, and password
   - Click "Register"

2. **Add School Data**
   - Go to Dashboard
   - Add Teachers: Click "Manage" under Teachers
   - Add Classes: Click "Manage" under Classes
   - Add Subjects: Click "Manage" under Subjects

3. **Configure Time Slots**
   - Go to Settings → Time Slots
   - Add time periods for each day (Monday-Friday)
   - Define start and end times for each period

4. **Assign Teachers to Subjects**
   - Go to Settings → Assignments
   - Select a teacher and a subject
   - Click "Assign"
   - A teacher can teach multiple subjects

5. **Optional: Configure Constraints**
   - Go to Settings → Concurrent Subjects
   - Mark subjects that can be taught at the same time
   - This handles cases where students choose alternative subjects

6. **Generate Timetable**
   - Go to Timetable → Generate
   - Click "Generate Timetable"
   - The system will create a fair schedule

7. **View Results**
   - Go to Timetable → View History
   - Click "View" to see the generated timetable
   - Use the quick access panel to view:
     - Individual class timetables
     - Individual teacher timetables

## Data Structure

### Schools
- Name, Email, Location
- Password for authentication

### Teachers
- Name
- Employee ID
- Can teach multiple subjects

### Subjects
- Name, Code
- Maximum lessons per week
- Double lesson requirement flag

### Classes
- Name
- Form Level (Form 1-4)
- Stream (Science, Arts, etc.)

### Time Slots
- Day of week (Monday-Friday)
- Period number
- Start and end times

### Lessons
- Class
- Subject
- Teacher
- Time slot
- Double lesson flag

## Algorithm Overview

The timetable generation uses a fair allocation algorithm:

1. **Lesson Creation**: Creates lesson requirements based on:
   - Each class needs each subject
   - Number of lessons = subject's max_lessons_per_week
   - Double lessons are paired up

2. **Teacher Assignment**: 
   - Randomly selects a teacher from those assigned to each subject
   - Ensures load balancing

3. **Slot Allocation**:
   - Iterates through available time slots
   - Places lessons while respecting:
     - No class has two lessons in same slot
     - Concurrent subjects are handled correctly
     - Double lessons have consecutive slots

4. **Conflict Resolution**:
   - Checks for teacher conflicts
   - Ensures class availability
   - Validates concurrent subject constraints

## Database Schema

- `schools`: School accounts
- `teachers`: School teachers
- `subjects`: School subjects
- `classes`: School classes
- `subject_assignments`: Teacher-Subject relationships
- `time_slots`: Available lesson periods
- `concurrent_subjects`: Subject pairs that can run together
- `lessons`: Individual lesson assignments
- `timetables`: Timetable generation records

## File Structure

```
timetabling/
├── app/
│   ├── __init__.py              # Flask app initialization
│   ├── models.py                # Database models
│   ├── routes.py                # API routes and views
│   ├── timetable_generator.py   # Scheduling algorithm
│   ├── templates/               # HTML templates
│   └── static/                  # CSS and JavaScript
├── app.py                       # Application entry point
├── config.py                    # Configuration
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## Troubleshooting

### Port Already in Use
If port 5000 is already in use, modify `app.py`:
```python
app.run(debug=True, port=5001)
```

### Database Errors
To reset the database:
```bash
rm timetable.db
python app.py
```

### Import Errors
Ensure all packages are installed:
```bash
pip install -r requirements.txt
```

## Future Enhancements

- Teacher availability/preferences
- Room assignment
- Subject capacity limits
- Student preference handling
- Timetable export (PDF/Excel)
- Web-based editing of generated timetables
- Conflict detection and resolution UI
- Multi-school support

## License

Educational use only. Designed for Kenyan high schools.

## Support

For issues or questions, please check the application logs and ensure all setup steps were followed correctly.
