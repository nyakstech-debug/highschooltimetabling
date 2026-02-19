from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class School(UserMixin, db.Model):
    __tablename__ = 'schools'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    teachers = db.relationship('Teacher', backref='school', lazy=True, cascade='all, delete-orphan')
    classes = db.relationship('Class', backref='school', lazy=True, cascade='all, delete-orphan')
    subjects = db.relationship('Subject', backref='school', lazy=True, cascade='all, delete-orphan')
    timetables = db.relationship('Timetable', backref='school', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(school_id):
    return School.query.get(int(school_id))

class Teacher(db.Model):
    __tablename__ = 'teachers'
    
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    employee_id = db.Column(db.String(100))
    
    subject_assignments = db.relationship('SubjectAssignment', backref='teacher', lazy=True, cascade='all, delete-orphan')
    lessons = db.relationship('Lesson', backref='teacher', lazy=True)
    
    __table_args__ = (db.UniqueConstraint('school_id', 'employee_id'),)

class Subject(db.Model):
    __tablename__ = 'subjects'
    
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(50))
    max_lessons_per_week = db.Column(db.Integer, default=4)
    double_lessons_per_week = db.Column(db.Integer, default=0)  # Number of double lessons required
    offered_for = db.Column(db.String(50), nullable=False)  # 'grade10-12', 'form3-4', or 'both'
    
    subject_assignments = db.relationship('SubjectAssignment', backref='subject', lazy=True, cascade='all, delete-orphan')
    
    __table_args__ = (db.UniqueConstraint('school_id', 'code'),)

class SubjectAssignment(db.Model):
    __tablename__ = 'subject_assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    
    # Relationships - backrefs are created by the parent models
    # Access the related objects via the foreign keys
    @property
    def teacher(self):
        return Teacher.query.get(self.teacher_id)
    
    @property
    def subject(self):
        return Subject.query.get(self.subject_id)
    
    @property
    def class_(self):
        return Class.query.get(self.class_id)
    
    __table_args__ = (db.UniqueConstraint('teacher_id', 'subject_id', 'class_id'),)

class ConcurrentSubject(db.Model):
    __tablename__ = 'concurrent_subjects'
    
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    concurrent_subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    
    subject = db.relationship('Subject', foreign_keys=[subject_id])
    concurrent_subject = db.relationship('Subject', foreign_keys=[concurrent_subject_id])
    
    __table_args__ = (db.UniqueConstraint('subject_id', 'concurrent_subject_id'),)

class StrokedSubjectGroup(db.Model):
    """Groups of alternative/stroked subjects - students choose ONE from each group"""
    __tablename__ = 'stroked_subject_groups'
    
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    group_name = db.Column(db.String(200), nullable=False)  # e.g., "History/Geography Group"
    level = db.Column(db.String(50), nullable=False)  # 'grade10-12' or 'form3-4'
    
    subjects = db.relationship('Subject', secondary='stroked_group_subjects', backref='stroked_groups')
    
    __table_args__ = (db.UniqueConstraint('school_id', 'group_name', 'level'),)

class StrokedGroupSubject(db.Model):
    """Association table for subjects in stroked groups"""
    __tablename__ = 'stroked_group_subjects'
    
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('stroked_subject_groups.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    
    group = db.relationship('StrokedSubjectGroup', backref='group_subjects')
    subject = db.relationship('Subject', backref='group_subjects')
    
    __table_args__ = (db.UniqueConstraint('group_id', 'subject_id'),)

class Class(db.Model):
    __tablename__ = 'classes'
    
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    level = db.Column(db.String(50), nullable=False)  # Grade 1-10, Form 3, Form 4
    
    lessons = db.relationship('Lesson', backref='class_', lazy=True, cascade='all, delete-orphan')
    
    __table_args__ = (db.UniqueConstraint('school_id', 'name', 'level'),)

class TimeSlot(db.Model):
    __tablename__ = 'time_slots'
    
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    period = db.Column(db.Integer, nullable=False)  # 1, 2, 3, etc.
    start_time = db.Column(db.String(10), nullable=False)  # HH:MM
    end_time = db.Column(db.String(10), nullable=False)  # HH:MM
    level = db.Column(db.String(50), nullable=False)  # 'grade10-12' or 'form3-4' - same schedule applies to all days Mon-Fri
    slot_type = db.Column(db.String(50), default='lesson')  # 'lesson', 'break', 'tea_break', 'lunch_break'
    
    lessons = db.relationship('Lesson', backref='time_slot', lazy=True)
    
    __table_args__ = (db.UniqueConstraint('school_id', 'level', 'period'),)

class Lesson(db.Model):
    __tablename__ = 'lessons'
    
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    time_slot_id = db.Column(db.Integer, db.ForeignKey('time_slots.id'))
    timetable_id = db.Column(db.Integer, db.ForeignKey('timetables.id'))
    is_double_lesson = db.Column(db.Boolean, default=False)
    
    subject = db.relationship('Subject', backref='lessons')

class Timetable(db.Model):
    __tablename__ = 'timetables'
    
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    generated_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    is_active = db.Column(db.Boolean, default=True)
    
    lessons = db.relationship('Lesson', backref='timetable', lazy=True)
