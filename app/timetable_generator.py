from app import db
from app.models import (
    School, Teacher, Class, Subject, TimeSlot, Lesson, Timetable,
    SubjectAssignment, ConcurrentSubject, StrokedSubjectGroup, StrokedGroupSubject
)
from collections import defaultdict
import random

class TimetableGenerator:
    def __init__(self, school_id):
        self.school_id = school_id
        self.school = School.query.get(school_id)
        self.lessons_needed = defaultdict(list)
        self.assignments = defaultdict(list)
        self.concurrent_subjects = set()
        self.stroked_subjects = set()
        self.allocated_lessons = defaultdict(lambda: defaultdict(lambda: {}))  # class_id -> day -> period -> lesson
        
        # Tracking for constraints
        self.teacher_weekly_load = defaultdict(int)
        self.teacher_daily_load = defaultdict(lambda: defaultdict(int))
        self.class_daily_subjects = defaultdict(lambda: defaultdict(set))
        self.teacher_daily_schedule = defaultdict(lambda: defaultdict(set))  # teacher_id -> day -> period_ids
        self.lab_usage = defaultdict(lambda: defaultdict(set))  # lab_type -> day -> periods
        self.room_usage = defaultdict(lambda: defaultdict(set))
        
        # Subject categories for balancing
        self.science_subjects = {'Physics', 'Chemistry', 'Biology'}
        self.math_heavy = {'Mathematics', 'Physics', 'Chemistry'}
        self.practical_subjects = {'Chemistry', 'Physics', 'Biology', 'Computer Science'}
        
        # Kenyan school schedule
        self.days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        self.assembly_period = 1  # Monday period 1
        self.club_period = (3, 'Wednesday')  # Wednesday afternoon
        self.games_period = (10, 'Friday')  # Friday last period
        
    def generate(self):
        """Generate timetable with comprehensive constraint handling"""
        self._validate_hard_constraints_setup()
        self._load_data()
        self._create_lessons()
        self._allocate_lessons()
        timetable = self._save_timetable()
        return timetable
    
    def _validate_hard_constraints_setup(self):
        """Validate basic setup for hard constraints"""
        if not self.school.teachers:
            raise ValueError("No teachers defined")
        if not self.school.classes:
            raise ValueError("No classes defined")
        if not self.school.subjects:
            raise ValueError("No subjects defined")
        
        time_slots = TimeSlot.query.filter_by(school_id=self.school_id).all()
        if not time_slots:
            raise ValueError("No time slots defined")
        
        # Check teacher load doesn't exceed max from start
        for teacher in self.school.teachers:
            assignments = SubjectAssignment.query.filter_by(teacher_id=teacher.id).all()
            weekly_load = sum(a.subject.max_lessons_per_week for a in assignments)
            if weekly_load > 30:
                raise ValueError(f"Teacher {teacher.name} exceeds max load (30): {weekly_load}")
    
    def _load_data(self):
        """Load all school data"""
        assignments = SubjectAssignment.query.filter_by(school_id=self.school_id).all()
        for assignment in assignments:
            self.assignments[assignment.subject_id].append(assignment.teacher_id)
        
        concurrent = ConcurrentSubject.query.filter_by(school_id=self.school_id).all()
        for c in concurrent:
            self.concurrent_subjects.add((min(c.subject_id, c.concurrent_subject_id),
                                         max(c.subject_id, c.concurrent_subject_id)))
        
        stroked_groups = StrokedSubjectGroup.query.filter_by(school_id=self.school_id).all()
        for group in stroked_groups:
            group_subjects = StrokedGroupSubject.query.filter_by(group_id=group.id).all()
            for gs in group_subjects:
                self.stroked_subjects.add(gs.subject_id)
    
    def _create_lessons(self):
        """Create required lessons for each class-subject"""
        for class_obj in self.school.classes:
            for subject in self.school.subjects:
                if not self._is_subject_offered_for_class(subject, class_obj):
                    continue
                
                teacher_ids = self.assignments.get(subject.id, [])
                if not teacher_ids:
                    continue
                
                teacher_id = random.choice(teacher_ids)
                
                # HC2.3: Respect double lesson requirements
                num_lessons = subject.max_lessons_per_week
                num_double_lessons = subject.double_lessons_per_week
                num_single_lessons = num_lessons - (num_double_lessons * 2)
                
                for _ in range(num_double_lessons):
                    self.lessons_needed[(class_obj.id, subject.id)].append({
                        'class_id': class_obj.id,
                        'subject_id': subject.id,
                        'teacher_id': teacher_id,
                        'is_double': True,
                        'is_practical': subject.name in self.practical_subjects
                    })
                
                for _ in range(num_single_lessons):
                    self.lessons_needed[(class_obj.id, subject.id)].append({
                        'class_id': class_obj.id,
                        'subject_id': subject.id,
                        'teacher_id': teacher_id,
                        'is_double': False,
                        'is_practical': subject.name in self.practical_subjects
                    })
    
    def _is_subject_offered_for_class(self, subject, class_obj):
        """Check if subject is offered for class level"""
        if subject.offered_for == 'both':
            return True
        elif subject.offered_for == 'grade10-12':
            return class_obj.level in ['Grade 10', 'Grade 11', 'Grade 12']
        elif subject.offered_for == 'form3-4':
            return class_obj.level in ['Form 3', 'Form 4']
        return False
    
    def _allocate_lessons(self):
        """Allocate lessons respecting hard constraints with soft optimization"""
        time_slots_by_level = self._get_time_slots_by_level()
        class_to_slot_level = self._map_classes_to_slot_levels()
        
        # Sort by difficulty: prioritize subjects with many required lessons
        sorted_lessons = sorted(
            self.lessons_needed.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )
        
        for (class_id, subject_id), lessons_list in sorted_lessons:
            class_obj = Class.query.get(class_id)
            subject = Subject.query.get(subject_id)
            slot_level = class_to_slot_level.get(class_id)
            time_slots = time_slots_by_level.get(slot_level, [])
            
            if not time_slots:
                raise ValueError(f"No time slots for {class_obj.level}")
            
            # Allocate each lesson
            for lesson in lessons_list:
                allocated = False
                
                # Try to find best slot respecting hard constraints
                slots_by_score = []
                for slot in time_slots:
                    if self._check_hard_constraints(class_id, subject_id, lesson['teacher_id'], slot, lesson['is_double']):
                        # HC2: No lesson during break/lunch
                        if slot.slot_type == 'lesson':
                            score = self._calculate_soft_constraint_score(
                                class_id, subject_id, lesson['teacher_id'], slot, subject, lesson
                            )
                            slots_by_score.append((slot, score))
                
                # Sort by score (higher is better) and try best options
                slots_by_score.sort(key=lambda x: x[1], reverse=True)
                
                for slot, score in slots_by_score[:5]:  # Try top 5 options
                    if self._allocate_to_slot(class_id, subject_id, lesson, slot):
                        allocated = True
                        break
                
                # Fallback: allocate to any valid slot
                if not allocated:
                    for slot in time_slots:
                        if (slot.slot_type == 'lesson' and 
                            self._check_hard_constraints(class_id, subject_id, lesson['teacher_id'], slot, lesson['is_double'])):
                            if self._allocate_to_slot(class_id, subject_id, lesson, slot):
                                allocated = True
                                break
    
    def _check_hard_constraints(self, class_id, subject_id, teacher_id, time_slot, is_double):
        """Check all hard constraints - return False if ANY violated"""
        
        # HC1.1: Teacher cannot teach two classes at same time
        day = self._get_day_for_slot(time_slot)
        period = time_slot.period
        
        if period in self.teacher_daily_schedule[teacher_id][day]:
            return False
        
        # HC2.1: Stream cannot have two subjects in one period
        if self.allocated_lessons[class_id][day].get(period) is not None:
            return False
        
        # HC2.4: No lesson during break or lunch
        if time_slot.slot_type != 'lesson':
            return False
        
        # HC2.5: Assembly period locked (Monday Period 1)
        if day == 'Monday' and period == 1:
            return False
        
        # HC2.5: Wednesday afternoon reserved for clubs
        if day == 'Wednesday' and period >= 7:
            return False
        
        # HC1.3: Teacher cannot exceed load
        if self.teacher_weekly_load[teacher_id] >= 30:
            return False
        
        # HC2.3: Double lesson must be consecutive
        if is_double and period == 10:  # Last period can't start double
            return False
        
        # HC4: Lab constraints - one class at a time per lab
        subject = Subject.query.get(subject_id)
        if subject.name in self.practical_subjects:
            lab_type = self._get_lab_for_subject(subject.name)
            if period in self.lab_usage[lab_type][day]:
                return False
        
        return True
    
    def _calculate_soft_constraint_score(self, class_id, subject_id, teacher_id, time_slot, subject, lesson):
        """Calculate quality score for this allocation"""
        score = 0
        day = self._get_day_for_slot(time_slot)
        period = time_slot.period
        
        # SP1.1: Math preferably in morning (periods 1-4)
        if subject.name == 'Mathematics' and period <= 4:
            score += 10
        
        # SP1.2: Sciences not all in one day
        if subject.name in self.science_subjects:
            science_count = len([s for s in self.class_daily_subjects[class_id][day] 
                               if Subject.query.get(s).name in self.science_subjects])
            if science_count < 2:
                score += 5
        
        # SP1.3: Avoid repeating subject same day
        if subject_id not in self.class_daily_subjects[class_id][day]:
            score += 5
        
        # SP2.1: Avoid teacher gaps
        if day in self.teacher_daily_schedule[teacher_id]:
            periods_taught = sorted(self.teacher_daily_schedule[teacher_id][day])
            if periods_taught and (period == periods_taught[-1] + 1 or period == periods_taught[-1] - 1):
                score += 8
        
        # SP3.1: Avoid heavy subjects last period
        if period != 10 and subject.name in self.math_heavy:
            score += 3
        
        return score
    
    def _allocate_to_slot(self, class_id, subject_id, lesson, time_slot):
        """Attempt to allocate lesson to slot"""
        day = self._get_day_for_slot(time_slot)
        period = time_slot.period
        
        # Allocate single lesson
        self.allocated_lessons[class_id][day][period] = lesson
        self.teacher_daily_schedule[lesson['teacher_id']][day].add(period)
        self.teacher_weekly_load[lesson['teacher_id']] += 1
        self.class_daily_subjects[class_id][day].add(subject_id)
        
        # If double lesson, also allocate next period
        if lesson['is_double']:
            if period + 1 in self.allocated_lessons[class_id][day]:
                return False  # Failed - next period occupied
            
            lesson_copy = lesson.copy()
            self.allocated_lessons[class_id][day][period + 1] = lesson_copy
            self.teacher_daily_schedule[lesson['teacher_id']][day].add(period + 1)
            self.teacher_weekly_load[lesson['teacher_id']] += 1
        
        lesson['time_slot_id'] = time_slot.id
        lesson['day'] = day
        
        # Update lab usage if practical
        if lesson['is_practical']:
            subject = Subject.query.get(subject_id)
            lab = self._get_lab_for_subject(subject.name)
            self.lab_usage[lab][day].add(period)
            if lesson['is_double']:
                self.lab_usage[lab][day].add(period + 1)
        
        return True
    
    def _get_time_slots_by_level(self):
        """Get time slots organized by level"""
        result = {}
        
        for level, level_code in [('Grade 10', 'grade10-12'), ('Form 3', 'form3-4'), ('Form 4', 'form3-4')]:
            slots = TimeSlot.query.filter_by(
                school_id=self.school_id,
                level=level_code,
                slot_type='lesson'
            ).order_by(TimeSlot.period).all()
            result[level_code] = slots
        
        return result
    
    def _map_classes_to_slot_levels(self):
        """Map class to appropriate time slot level"""
        mapping = {}
        for class_obj in self.school.classes:
            if class_obj.level in ['Grade 10', 'Grade 11', 'Grade 12']:
                mapping[class_obj.id] = 'grade10-12'
            elif class_obj.level in ['Form 3', 'Form 4']:
                mapping[class_obj.id] = 'form3-4'
        return mapping
    
    def _get_day_for_slot(self, time_slot):
        """Determine day from time slot"""
        period = time_slot.period
        if period <= 2:
            return 'Monday'
        elif period <= 4:
            return 'Tuesday'
        elif period <= 6:
            return 'Wednesday'
        elif period <= 8:
            return 'Thursday'
        else:
            return 'Friday'
    
    def _get_lab_for_subject(self, subject_name):
        """Get lab type for subject"""
        lab_map = {
            'Chemistry': 'chem_lab',
            'Physics': 'physics_lab',
            'Biology': 'bio_lab',
            'Computer Science': 'computer_lab'
        }
        return lab_map.get(subject_name, 'general')
    
    def _save_timetable(self):
        """Save timetable to database"""
        timetable = Timetable(school_id=self.school_id, is_active=True)
        db.session.add(timetable)
        db.session.flush()
        
        for class_id, days_dict in self.allocated_lessons.items():
            for day, periods_dict in days_dict.items():
                for period, lesson_data in periods_dict.items():
                    lesson = Lesson(
                        school_id=self.school_id,
                        class_id=lesson_data['class_id'],
                        subject_id=lesson_data['subject_id'],
                        teacher_id=lesson_data['teacher_id'],
                        time_slot_id=lesson_data.get('time_slot_id'),
                        timetable_id=timetable.id,
                        is_double_lesson=lesson_data['is_double']
                    )
                    db.session.add(lesson)
        
        db.session.commit()
        return timetable
