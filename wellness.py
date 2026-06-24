import json
import re
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from models import db, WellnessLog, User

# Create Blueprint
wellness = Blueprint('wellness', __name__)

# Helper algorithms for Data Science & Risk Engine

def calculate_streak(user_id):
    """
    Calculates the consecutive logging streak for a user in days.
    A streak is active if the user logged today or yesterday and continues
    consecutively backwards in time.
    """
    # Fetch all logs for the user, ordered by log_date descending
    logs = WellnessLog.query.filter_by(user_id=user_id).order_by(WellnessLog.log_date.desc()).all()
    if not logs:
        return 0
        
    # Extract unique dates in descending order
    dates = sorted(list(set(log.log_date for log in logs)), reverse=True)
    
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    
    # If the most recent log is neither today nor yesterday, the streak is broken (0 days)
    if dates[0] not in (today, yesterday):
        return 0
        
    streak = 1
    for i in range(len(dates) - 1):
        # Check if the difference between adjacent dates is exactly 1 day
        if (dates[i] - dates[i+1]).days == 1:
            streak += 1
        else:
            break
            
    return streak

def check_high_stress_risk(user_id):
    """
    Rule-Based Risk Engine:
    Triggers an alert if there is any sequence of 5 consecutive calendar days
    in the user's logs where the stress level was 4 or 5.
    """
    # Fetch all logs for the user, ordered by log_date ascending (chronological)
    logs = WellnessLog.query.filter_by(user_id=user_id).order_by(WellnessLog.log_date.asc()).all()
    if len(logs) < 5:
        return False
        
    # Check for any window of 5 consecutive logs
    for i in range(len(logs) - 4):
        window = logs[i:i+5]
        
        # Verify that the 5 logs are on 5 consecutive calendar days
        is_consecutive = all((window[j+1].log_date - window[j].log_date).days == 1 for j in range(4))
        
        # Verify that all 5 logs in this window have a stress level of 4 or 5
        all_high_stress = all(int(log.stress_level) >= 4 for log in window)
        
        if is_consecutive and all_high_stress:
            return True
            
    return False

# CRUD Operations

@wellness.route('/log', methods=['GET', 'POST'])
@login_required
def log_entry():
    if request.method == 'POST':
        date_str = request.form.get('log_date')
        mood = request.form.get('mood_score')
        stress = request.form.get('stress_level')
        sleep_h = request.form.get('sleep_hours')
        sleep_q = request.form.get('sleep_quality')
        workload = request.form.get('academic_workload')
        notes = request.form.get('notes', '').strip()
        
        # 1. Server-side Presence Validation
        if not all([date_str, mood, stress, sleep_h, sleep_q, workload]):
            flash("All fields except notes are required.", "danger")
            return render_template('log.html', today=datetime.now().date().isoformat())
            
        try:
            log_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            mood_val = int(mood)
            stress_val = int(stress)
            sleep_h_val = float(sleep_h)
            sleep_q_val = int(sleep_q)
            workload_val = int(workload)
        except (ValueError, TypeError):
            flash("Invalid data format submitted.", "danger")
            return render_template('log.html', today=datetime.now().date().isoformat())
            
        # 2. Range & Boundary Validation
        if not (1 <= mood_val <= 5) or not (1 <= stress_val <= 5) or not (1 <= sleep_q_val <= 5) or not (1 <= workload_val <= 5):
            flash("Wellness scores must be between 1 and 5.", "danger")
            return render_template('log.html', today=datetime.now().date().isoformat())
            
        if not (0.0 <= sleep_h_val <= 16.0):
            flash("Sleep hours must be between 0 and 16 hours.", "danger")
            return render_template('log.html', today=datetime.now().date().isoformat())
            
        # 3. Future Date Validation
        today = datetime.now().date()
        if log_date > today:
            flash("Cannot record wellness logs for future dates.", "danger")
            return render_template('log.html', today=datetime.now().date().isoformat())
            
        # 4. Duplicate Log Date Check
        existing_log = WellnessLog.query.filter_by(user_id=current_user.id, log_date=log_date).first()
        if existing_log:
            flash(f"You have already recorded a wellness log for {date_str}.", "danger")
            return render_template('log.html', today=datetime.now().date().isoformat())
            
        # Create and save new log (Wellness Score will be computed automatically by model listener)
        new_log = WellnessLog(
            user_id=current_user.id,
            log_date=log_date,
            mood_score=mood_val,
            stress_level=stress_val,
            sleep_hours=sleep_h_val,
            sleep_quality=sleep_q_val,
            academic_workload=workload_val,
            notes=notes if notes else None
        )
        
        try:
            db.session.add(new_log)
            db.session.commit()
            flash("Wellness entry successfully recorded.", "success")
            return redirect(url_for('wellness.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash("An error occurred while saving. Please try again.", "danger")
            
    return render_template('log.html', today=datetime.now().date().isoformat())

@wellness.route('/history')
@login_required
def history():
    # Paginate 10 logs per page
    page = request.args.get('page', 1, type=int)
    pagination = WellnessLog.query.filter_by(user_id=current_user.id)\
                                  .order_by(WellnessLog.log_date.desc())\
                                  .paginate(page=page, per_page=10, error_out=False)
    
    logs = pagination.items
    return render_template('history.html', pagination=pagination, logs=logs)

@wellness.route('/log/edit/<int:log_id>', methods=['GET', 'POST'])
@login_required
def edit_entry(log_id):
    log = WellnessLog.query.get_or_404(log_id)
    
    # Ownership Check
    if log.user_id != current_user.id:
        abort(403)
        
    if request.method == 'POST':
        date_str = request.form.get('log_date')
        mood = request.form.get('mood_score')
        stress = request.form.get('stress_level')
        sleep_h = request.form.get('sleep_hours')
        sleep_q = request.form.get('sleep_quality')
        workload = request.form.get('academic_workload')
        notes = request.form.get('notes', '').strip()
        
        if not all([date_str, mood, stress, sleep_h, sleep_q, workload]):
            flash("All fields except notes are required.", "danger")
            return render_template('edit_log.html', log=log)
            
        try:
            log_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            mood_val = int(mood)
            stress_val = int(stress)
            sleep_h_val = float(sleep_h)
            sleep_q_val = int(sleep_q)
            workload_val = int(workload)
        except (ValueError, TypeError):
            flash("Invalid data format submitted.", "danger")
            return render_template('edit_log.html', log=log)
            
        # Range & Boundary Validation
        if not (1 <= mood_val <= 5) or not (1 <= stress_val <= 5) or not (1 <= sleep_q_val <= 5) or not (1 <= workload_val <= 5):
            flash("Wellness scores must be between 1 and 5.", "danger")
            return render_template('edit_log.html', log=log)
            
        if not (0.0 <= sleep_h_val <= 16.0):
            flash("Sleep hours must be between 0 and 16 hours.", "danger")
            return render_template('edit_log.html', log=log)
            
        # Future Date Validation
        today = datetime.now().date()
        if log_date > today:
            flash("Cannot record wellness logs for future dates.", "danger")
            return render_template('edit_log.html', log=log)
            
        # Duplicate Date Check (excluding the current log being edited)
        duplicate = WellnessLog.query.filter(
            WellnessLog.user_id == current_user.id,
            WellnessLog.log_date == log_date,
            WellnessLog.id != log.id
        ).first()
        if duplicate:
            flash(f"You already have a wellness log for {date_str}.", "danger")
            return render_template('edit_log.html', log=log)
            
        # Update values
        log.log_date = log_date
        log.mood_score = mood_val
        log.stress_level = stress_val
        log.sleep_hours = sleep_h_val
        log.sleep_quality = sleep_q_val
        log.academic_workload = workload_val
        log.notes = notes if notes else None
        
        try:
            db.session.commit()
            flash("Wellness entry successfully updated.", "success")
            return redirect(url_for('wellness.history'))
        except Exception as e:
            db.session.rollback()
            flash("An error occurred while updating. Please try again.", "danger")
            
    return render_template('edit_log.html', log=log)

@wellness.route('/log/delete/<int:log_id>', methods=['POST'])
@login_required
def delete_entry(log_id):
    log = WellnessLog.query.get_or_404(log_id)
    
    # Ownership Check
    if log.user_id != current_user.id:
        abort(403)
        
    try:
        db.session.delete(log)
        db.session.commit()
        flash("Wellness entry successfully deleted.", "success")
    except Exception as e:
        db.session.rollback()
        flash("An error occurred while deleting. Please try again.", "danger")
        
    return redirect(url_for('wellness.history'))

# Dashboard & Interactive Charts

@wellness.route('/dashboard')
@login_required
def dashboard():
    # 1. Query last 30 days of wellness logs for the user (ordered ascending for chronological charts)
    thirty_days_ago = datetime.now().date() - timedelta(days=30)
    logs_30d = WellnessLog.query.filter_by(user_id=current_user.id)\
                                 .filter(WellnessLog.log_date >= thirty_days_ago)\
                                 .order_by(WellnessLog.log_date.asc())\
                                 .all()
                                 
    # 2. Query last 7 days of wellness logs for week-based statistics
    seven_days_ago = datetime.now().date() - timedelta(days=7)
    logs_7d = [log for log in logs_30d if log.log_date >= seven_days_ago]
    
    # 3. Calculate Summary Statistics in Python
    # Average Mood This Week
    if logs_7d:
        avg_mood = sum(log.mood_score for log in logs_7d) / len(logs_7d)
        # Determine emoji based on rating
        if avg_mood >= 4.5:
            mood_emoji = "😄"
        elif avg_mood >= 3.5:
            mood_emoji = "🙂"
        elif avg_mood >= 2.5:
            mood_emoji = "😐"
        elif avg_mood >= 1.5:
            mood_emoji = "🙁"
        else:
            mood_emoji = "😢"
        avg_mood_display = f"{round(avg_mood, 1)} {mood_emoji}"
    else:
        avg_mood_display = "N/A"
        
    # Average Stress This Week
    if logs_7d:
        avg_stress = sum(log.stress_level for log in logs_7d) / len(logs_7d)
        if avg_stress < 2.5:
            stress_class = "text-success"  # Low Stress
            stress_text = "Low"
        elif avg_stress < 3.5:
            stress_class = "text-warning"  # Moderate Stress
            stress_text = "Moderate"
        else:
            stress_class = "text-danger"  # High Stress
            stress_text = "High"
        avg_stress_display = f"{round(avg_stress, 1)} ({stress_text})"
    else:
        avg_stress_display = "N/A"
        stress_class = "text-muted"
        
    # Streak Calculation (runs over all logs)
    streak_days = calculate_streak(current_user.id)
    
    # Overall Wellness Score (Average over last 30 days)
    if logs_30d:
        avg_wellness = sum(float(log.wellness_score) for log in logs_30d) / len(logs_30d)
        avg_wellness_display = round(avg_wellness, 1)
    else:
        avg_wellness_display = 0.0
        
    # 4. Rule-Based Risk Engine Check
    show_risk_banner = check_high_stress_risk(current_user.id)
    
    # 5. Prepare Chart.js Data Packets (JSON)
    # Chart 1: Mood Trend (Line)
    mood_chart = {
        "labels": [log.log_date.strftime("%b %d") for log in logs_30d],
        "data": [log.mood_score for log in logs_30d]
    }
    
    # Chart 2: Stress Weekly Averages (Bar)
    # Group the logs into four 7-day intervals counting backwards from today
    today = datetime.now().date()
    week1_logs = [log for log in logs_30d if today - timedelta(days=28) <= log.log_date < today - timedelta(days=21)]
    week2_logs = [log for log in logs_30d if today - timedelta(days=21) <= log.log_date < today - timedelta(days=14)]
    week3_logs = [log for log in logs_30d if today - timedelta(days=14) <= log.log_date < today - timedelta(days=7)]
    week4_logs = [log for log in logs_30d if today - timedelta(days=7) <= log.log_date <= today]
    
    def get_avg_stress(log_list):
        if not log_list:
            return 0.0
        return round(sum(int(log.stress_level) for log in log_list) / len(log_list), 2)
        
    stress_chart = {
        "labels": ["Week 1 (22-28d ago)", "Week 2 (15-21d ago)", "Week 3 (8-14d ago)", "Week 4 (1-7d ago)"],
        "data": [get_avg_stress(week1_logs), get_avg_stress(week2_logs), get_avg_stress(week3_logs), get_avg_stress(week4_logs)]
    }
    
    # Chart 3: Sleep Dual-Axis (Bar + Line)
    sleep_chart = {
        "labels": [log.log_date.strftime("%b %d") for log in logs_30d],
        "hours": [float(log.sleep_hours) for log in logs_30d],
        "quality": [log.sleep_quality for log in logs_30d]
    }
    
    # Chart 4: Wellness Score Trend (Line)
    wellness_chart = {
        "labels": [log.log_date.strftime("%b %d") for log in logs_30d],
        "data": [float(log.wellness_score) for log in logs_30d]
    }
    
    # Package into JSON strings for template inclusion
    chart_data = {
        "mood": json.dumps(mood_chart),
        "stress": json.dumps(stress_chart),
        "sleep": json.dumps(sleep_chart),
        "wellness": json.dumps(wellness_chart)
    }
    
    # local time string
    local_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    return render_template(
        'dashboard.html',
        avg_mood=avg_mood_display,
        avg_stress=avg_stress_display,
        stress_class=stress_class,
        streak=streak_days,
        avg_wellness=avg_wellness_display,
        show_risk_banner=show_risk_banner,
        chart_data=chart_data,
        local_time=local_time
    )
