from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import School, Teacher, Class, Subject, SubjectAssignment, TimeSlot, Lesson, Timetable, StrokedSubjectGroup, StrokedGroupSubject, ConcurrentSubject
from app.timetable_generator import TimetableGenerator

main_bp = Blueprint('main', __name__)
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
school_bp = Blueprint('school', __name__, url_prefix='/school')
timetable_bp = Blueprint('timetable', __name__, url_prefix='/timetable')

# Main routes
@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/about')
def about():
    return render_template('about.html')

# Authentication routes
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('school_name')
        email = request.form.get('email')
        password = request.form.get('password')
        location = request.form.get('location')
        
        if School.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('auth.register'))
        
        school = School(name=name, email=email, location=location)
        school.set_password(password)
        db.session.add(school)
        db.session.commit()
        
        flash('Registration successful. Please login.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        school = School.query.filter_by(email=email).first()
        
        if school and school.check_password(password):
            login_user(school)
            return redirect(url_for('school.dashboard'))
        else:
            flash('Invalid email or password', 'danger')
    
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

# School dashboard routes
@school_bp.route('/dashboard')
@login_required
def dashboard():
    school = current_user
    stats = {
        'teachers': len(school.teachers),
        'classes': len(school.classes),
        'subjects': len(school.subjects),
        'timetables': len(school.timetables)
    }
    return render_template('dashboard.html', stats=stats)

# Teacher management
@school_bp.route('/teachers', methods=['GET', 'POST'])
@login_required
def teachers():
    if request.method == 'POST':
        name = request.form.get('name')
        employee_id = request.form.get('employee_id')
        
        try:
            teacher = Teacher(school_id=current_user.id, name=name, employee_id=employee_id)
            db.session.add(teacher)
            db.session.commit()
            
            flash('Teacher added successfully', 'success')
        except Exception as e:
            db.session.rollback()
            if 'UNIQUE' in str(e):
                flash(f'A teacher with employee ID "{employee_id}" already exists', 'danger')
            else:
                flash('Error adding teacher: ' + str(e), 'danger')
        
        return redirect(url_for('school.teachers'))
    
    teachers = Teacher.query.filter_by(school_id=current_user.id).all()
    return render_template('teachers.html', teachers=teachers)

@school_bp.route('/teacher/<int:teacher_id>/delete', methods=['POST'])
@login_required
def delete_teacher(teacher_id):
    teacher = Teacher.query.get(teacher_id)
    if teacher and teacher.school_id == current_user.id:
        db.session.delete(teacher)
        db.session.commit()
        flash('Teacher deleted', 'success')
    return redirect(url_for('school.teachers'))

# Subject management
@school_bp.route('/subjects', methods=['GET', 'POST'])
@login_required
def subjects():
    if request.method == 'POST':
        name = request.form.get('name')
        code = request.form.get('code')
        max_lessons_str = request.form.get('max_lessons_per_week', '4').strip() or '4'
        double_lessons_str = request.form.get('double_lessons_per_week', '0').strip() or '0'
        max_lessons = int(max_lessons_str)
        double_lessons = int(double_lessons_str)
        level = request.form.get('level')  # 'grade10-12' or 'form3-4'
        
        try:
            subject = Subject(
                school_id=current_user.id,
                name=name,
                code=code,
                max_lessons_per_week=max_lessons,
                double_lessons_per_week=double_lessons,
                offered_for=level
            )
            db.session.add(subject)
            db.session.commit()
            
            flash('Subject added successfully', 'success')
        except Exception as e:
            db.session.rollback()
            if 'UNIQUE' in str(e):
                flash('A subject with this code already exists', 'danger')
            else:
                flash('Error adding subject: ' + str(e), 'danger')
        
        return redirect(url_for('school.subjects'))
    
    # Get subjects separated by level
    grade_subjects = Subject.query.filter_by(school_id=current_user.id, offered_for='grade10-12').all()
    form_subjects = Subject.query.filter_by(school_id=current_user.id, offered_for='form3-4').all()
    
    return render_template('subjects.html', grade_subjects=grade_subjects, form_subjects=form_subjects)

@school_bp.route('/subject/<int:subject_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_subject(subject_id):
    subject = Subject.query.get(subject_id)
    if not subject or subject.school_id != current_user.id:
        flash('Subject not found', 'danger')
        return redirect(url_for('school.subjects'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        code = request.form.get('code')
        max_lessons_str = request.form.get('max_lessons_per_week', '4').strip() or '4'
        double_lessons_str = request.form.get('double_lessons_per_week', '0').strip() or '0'
        max_lessons = int(max_lessons_str)
        double_lessons = int(double_lessons_str)
        
        try:
            subject.name = name
            subject.code = code
            subject.max_lessons_per_week = max_lessons
            subject.double_lessons_per_week = double_lessons
            
            db.session.commit()
            flash('Subject updated successfully', 'success')
            return redirect(url_for('school.subjects'))
        except Exception as e:
            db.session.rollback()
            if 'UNIQUE' in str(e):
                flash('A subject with this code already exists', 'danger')
            else:
                flash('Error updating subject: ' + str(e), 'danger')
    
    return render_template('edit_subject.html', subject=subject)

@school_bp.route('/subject/<int:subject_id>/delete', methods=['POST'])
@login_required
def delete_subject(subject_id):
    subject = Subject.query.get(subject_id)
    if subject and subject.school_id == current_user.id:
        db.session.delete(subject)
        db.session.commit()
        flash('Subject deleted', 'success')
    return redirect(url_for('school.subjects'))

# Class management
@school_bp.route('/classes', methods=['GET', 'POST'])
@login_required
def classes():
    if request.method == 'POST':
        name = request.form.get('name')
        level = request.form.get('level')
        
        try:
            class_obj = Class(
                school_id=current_user.id,
                name=name,
                level=level
            )
            db.session.add(class_obj)
            db.session.commit()
            
            flash('Class added successfully', 'success')
        except Exception as e:
            db.session.rollback()
            if 'UNIQUE' in str(e):
                flash('A class with this name and level already exists', 'danger')
            else:
                flash('Error adding class: ' + str(e), 'danger')
        
        return redirect(url_for('school.classes'))
    
    classes = Class.query.filter_by(school_id=current_user.id).all()
    return render_template('classes.html', classes=classes)

@school_bp.route('/class/<int:class_id>/delete', methods=['POST'])
@login_required
def delete_class(class_id):
    class_obj = Class.query.get(class_id)
    if class_obj and class_obj.school_id == current_user.id:
        db.session.delete(class_obj)
        db.session.commit()
        flash('Class deleted', 'success')
    return redirect(url_for('school.classes'))

# Subject assignment (teacher to subject to class)
@school_bp.route('/assignments', methods=['GET', 'POST'])
@login_required
def assignments():
    if request.method == 'POST':
        teacher_id = request.form.get('teacher_id')
        subject_id = request.form.get('subject_id')
        class_id = request.form.get('class_id')
        
        try:
            existing = SubjectAssignment.query.filter_by(
                teacher_id=teacher_id, subject_id=subject_id, class_id=class_id
            ).first()
            
            if not existing:
                assignment = SubjectAssignment(
                    teacher_id=teacher_id,
                    subject_id=subject_id,
                    class_id=class_id,
                    school_id=current_user.id
                )
                db.session.add(assignment)
                db.session.commit()
                flash('Assignment created successfully', 'success')
            else:
                flash('This assignment already exists', 'warning')
        except Exception as e:
            db.session.rollback()
            flash('Error creating assignment: ' + str(e), 'danger')
        
        return redirect(url_for('school.assignments'))
    
    teachers = Teacher.query.filter_by(school_id=current_user.id).all()
    subjects = Subject.query.filter_by(school_id=current_user.id).all()
    classes = Class.query.filter_by(school_id=current_user.id).all()
    assignments = SubjectAssignment.query.filter_by(school_id=current_user.id).all()
    
    return render_template('assignments.html', teachers=teachers, subjects=subjects, classes=classes, assignments=assignments)

@school_bp.route('/assignment/<int:assignment_id>/delete', methods=['POST'])
@login_required
def delete_assignment(assignment_id):
    assignment = SubjectAssignment.query.get(assignment_id)
    if assignment and assignment.school_id == current_user.id:
        db.session.delete(assignment)
        db.session.commit()
        flash('Assignment deleted', 'success')
    return redirect(url_for('school.assignments'))

@school_bp.route('/assignments/delete-all', methods=['POST'])
@login_required
def delete_all_assignments():
    try:
        deleted_count = SubjectAssignment.query.filter_by(school_id=current_user.id).delete()
        db.session.commit()
        flash(f'Deleted {deleted_count} assignments', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting assignments: {str(e)}', 'danger')
    return redirect(url_for('school.assignments'))

# Time slots
@school_bp.route('/timeslots', methods=['GET', 'POST'])
@login_required
def timeslots():
    if request.method == 'POST':
        period_str = request.form.get('period', '').strip()
        if not period_str:
            flash('Period number is required', 'danger')
            return redirect(url_for('school.timeslots'))
        period = int(period_str)
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        level = request.form.get('level')  # 'grade10-12' or 'form3-4'
        slot_type = request.form.get('slot_type', 'lesson')  # 'lesson', 'break', 'tea_break', 'lunch_break'
        
        try:
            slot = TimeSlot(
                school_id=current_user.id,
                period=period,
                start_time=start_time,
                end_time=end_time,
                level=level,
                slot_type=slot_type
            )
            db.session.add(slot)
            db.session.commit()
            
            flash('Time slot added successfully', 'success')
        except Exception as e:
            db.session.rollback()
            if 'UNIQUE' in str(e):
                flash(f'A time slot for period {period} already exists for this level', 'danger')
            else:
                flash('Error adding time slot: ' + str(e), 'danger')
        
        return redirect(url_for('school.timeslots'))
    
    # Get time slots separated by level
    grade_timeslots = TimeSlot.query.filter_by(school_id=current_user.id, level='grade10-12').order_by(TimeSlot.period).all()
    form_timeslots = TimeSlot.query.filter_by(school_id=current_user.id, level='form3-4').order_by(TimeSlot.period).all()
    
    return render_template('timeslots.html', grade_timeslots=grade_timeslots, form_timeslots=form_timeslots)

@school_bp.route('/timeslot/<int:slot_id>/delete', methods=['POST'])
@login_required
def delete_timeslot(slot_id):
    slot = TimeSlot.query.get(slot_id)
    if slot and slot.school_id == current_user.id:
        db.session.delete(slot)
        db.session.commit()
        flash('Time slot deleted', 'success')
    return redirect(url_for('school.timeslots'))

# Stroked subject groups
@school_bp.route('/stroked', methods=['GET', 'POST'])
@login_required
def stroked():
    if request.method == 'POST':
        group_name = request.form.get('group_name')
        level = request.form.get('level')  # 'grade10-12' or 'form3-4'
        subject_ids = request.form.getlist('subject_ids')
        
        try:
            # Create the group
            group = StrokedSubjectGroup(
                school_id=current_user.id,
                group_name=group_name,
                level=level
            )
            db.session.add(group)
            db.session.flush()
            
            # Convert to integers and filter empty values
            subject_ids_int = [int(sid) for sid in subject_ids if sid]
            
            # Add subjects to the group
            for subject_id in subject_ids_int:
                group_subject = StrokedGroupSubject(
                    group_id=group.id,
                    subject_id=subject_id
                )
                db.session.add(group_subject)
            
            # Mark all subjects in the group as concurrent with each other
            # This is because students choose ONE from the group, so different subjects can run at same time
            for i, subject_id1 in enumerate(subject_ids_int):
                for subject_id2 in subject_ids_int[i+1:]:
                    # Check if this concurrent relationship already exists
                    existing = ConcurrentSubject.query.filter(
                        db.or_(
                            db.and_(
                                ConcurrentSubject.subject_id == subject_id1,
                                ConcurrentSubject.concurrent_subject_id == subject_id2
                            ),
                            db.and_(
                                ConcurrentSubject.subject_id == subject_id2,
                                ConcurrentSubject.concurrent_subject_id == subject_id1
                            )
                        )
                    ).first()
                    
                    if not existing:
                        concurrent = ConcurrentSubject(
                            subject_id=subject_id1,
                            concurrent_subject_id=subject_id2,
                            school_id=current_user.id
                        )
                        db.session.add(concurrent)
            
            db.session.commit()
            flash('Stroked subject group created successfully. All subjects in this group are now marked as concurrent.', 'success')
        except Exception as e:
            db.session.rollback()
            if 'UNIQUE' in str(e):
                flash('A stroked group with this name already exists for this level', 'danger')
            else:
                flash('Error creating stroked group: ' + str(e), 'danger')
        
        return redirect(url_for('school.stroked'))
    
    # Get stroked groups separated by level
    grade_groups = StrokedSubjectGroup.query.filter_by(school_id=current_user.id, level='grade10-12').all()
    form_groups = StrokedSubjectGroup.query.filter_by(school_id=current_user.id, level='form3-4').all()
    
    grade_subjects = Subject.query.filter_by(school_id=current_user.id, offered_for='grade10-12').all()
    form_subjects = Subject.query.filter_by(school_id=current_user.id, offered_for='form3-4').all()
    
    return render_template('stroked.html', 
                         grade_groups=grade_groups, 
                         form_groups=form_groups,
                         grade_subjects=grade_subjects,
                         form_subjects=form_subjects)

@school_bp.route('/stroked/<int:group_id>/delete', methods=['POST'])
@login_required
def delete_stroked_group(group_id):
    from app.models import StrokedGroupSubject, ConcurrentSubject
    group = StrokedSubjectGroup.query.get(group_id)
    if group and group.school_id == current_user.id:
        try:
            # Delete child records (stroked group subjects)
            StrokedGroupSubject.query.filter_by(group_id=group_id).delete()
            db.session.commit()
            
            # Now delete the group
            db.session.delete(group)
            db.session.commit()
            flash('Stroked group deleted', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error deleting stroked group: {str(e)}', 'danger')
    return redirect(url_for('school.stroked'))

# Timetable generation
@timetable_bp.route('/generate', methods=['GET', 'POST'])
@login_required
def generate():
    if request.method == 'POST':
        try:
            generator = TimetableGenerator(current_user.id)
            timetable = generator.generate()
            flash('Timetable generated successfully', 'success')
            return redirect(url_for('timetable.view_timetable', timetable_id=timetable.id))
        except Exception as e:
            flash(f'Error generating timetable: {str(e)}', 'danger')
            return redirect(url_for('timetable.generate'))
    
    return render_template('generate_timetable.html')

@timetable_bp.route('/<int:timetable_id>/view')
@login_required
def view_timetable(timetable_id):
    timetable = Timetable.query.get(timetable_id)
    if not timetable or timetable.school_id != current_user.id:
        flash('Timetable not found', 'danger')
        return redirect(url_for('school.dashboard'))
    
    return render_template('view_timetable.html', timetable=timetable)

@timetable_bp.route('/<int:timetable_id>/teacher/<int:teacher_id>')
@login_required
def teacher_timetable(timetable_id, teacher_id):
    timetable = Timetable.query.get(timetable_id)
    teacher = Teacher.query.get(teacher_id)
    
    if not timetable or timetable.school_id != current_user.id or teacher.school_id != current_user.id:
        flash('Not found', 'danger')
        return redirect(url_for('school.dashboard'))
    
    lessons = Lesson.query.filter_by(timetable_id=timetable_id, teacher_id=teacher_id).all()
    return render_template('teacher_timetable.html', teacher=teacher, lessons=lessons, timetable=timetable)

@timetable_bp.route('/<int:timetable_id>/class/<int:class_id>')
@login_required
def class_timetable(timetable_id, class_id):
    timetable = Timetable.query.get(timetable_id)
    class_obj = Class.query.get(class_id)
    
    if not timetable or timetable.school_id != current_user.id or class_obj.school_id != current_user.id:
        flash('Not found', 'danger')
        return redirect(url_for('school.dashboard'))
    
    lessons = Lesson.query.filter_by(timetable_id=timetable_id, class_id=class_id).all()
    return render_template('class_timetable.html', class_obj=class_obj, lessons=lessons, timetable=timetable)

@timetable_bp.route('/list')
@login_required
def list_timetables():
    timetables = Timetable.query.filter_by(school_id=current_user.id).order_by(Timetable.generated_at.desc()).all()
    return render_template('timetable_list.html', timetables=timetables)
