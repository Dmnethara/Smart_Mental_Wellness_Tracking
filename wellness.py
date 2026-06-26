import json
import re
import os
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import login_required, current_user
from models import db, WellnessLog, User
import pandas as pd
import numpy as np
import scipy.stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

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
    Rule-Based Risk Engine (Legacy):
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

def compute_analytics(logs):
    """
    Day 6 Data Science Analytics:
    1. Statistical analysis (pandas): mean, median, std deviation for each metric.
    2. Pearson correlation: scipy.stats.pearsonr(sleep_hours, stress_level).
    3. Day-of-week pattern analysis: groupby weekday, avg stress.
    """
    if not logs:
        metrics = ['mood_score', 'stress_level', 'sleep_hours', 'sleep_quality', 'academic_workload', 'wellness_score']
        empty_stats = {m: {'mean': 0.0, 'median': 0.0, 'std': 0.0} for m in metrics}
        return empty_stats, "N/A (Requires at least 2 logs)", "N/A (No logs recorded yet)"
        
    # Convert logs to pandas DataFrame
    data = []
    for log in logs:
        data.append({
            'date': log.log_date,
            'mood_score': int(log.mood_score),
            'stress_level': int(log.stress_level),
            'sleep_hours': float(log.sleep_hours),
            'sleep_quality': int(log.sleep_quality),
            'academic_workload': int(log.academic_workload),
            'wellness_score': float(log.wellness_score)
        })
    df = pd.DataFrame(data)
    
    # 1. Statistical Analysis
    metrics = ['mood_score', 'stress_level', 'sleep_hours', 'sleep_quality', 'academic_workload', 'wellness_score']
    stats = {}
    for metric in metrics:
        mean_val = df[metric].mean()
        median_val = df[metric].median()
        std_val = df[metric].std() if len(df) > 1 else 0.0
        
        stats[metric] = {
            'mean': round(mean_val, 2) if not pd.isna(mean_val) else 0.0,
            'median': round(median_val, 2) if not pd.isna(median_val) else 0.0,
            'std': round(std_val, 2) if not pd.isna(std_val) else 0.0
        }
        
    # 2. Pearson Correlation
    correlation_msg = "N/A (Requires more logs or variation in sleep/stress values)"
    if len(df) >= 2:
        sleep_hours_list = df['sleep_hours'].tolist()
        stress_list = df['stress_level'].tolist()
        std_sleep = df['sleep_hours'].std()
        std_stress = df['stress_level'].std()
        if std_sleep > 0 and std_stress > 0:
            try:
                r, p = scipy.stats.pearsonr(sleep_hours_list, stress_list)
                direction = "positive" if r > 0 else "negative"
                abs_r = abs(r)
                if abs_r >= 0.7:
                    strength = "strong"
                elif abs_r >= 0.4:
                    strength = "moderate"
                elif abs_r >= 0.1:
                    strength = "weak"
                else:
                    strength = "negligible"
                
                if not pd.isna(r):
                    correlation_msg = f"Sleep hours and stress level show r={round(r, 2)} ({strength} {direction} correlation)"
            except Exception:
                pass
                
    # 3. Day-of-week pattern analysis
    weekday_msg = "N/A (No logs recorded yet)"
    try:
        df['weekday'] = pd.to_datetime(df['date']).dt.day_name()
        weekday_stress = df.groupby('weekday')['stress_level'].mean()
        if not weekday_stress.empty:
            highest_stress_day = weekday_stress.idxmax()
            highest_stress_val = round(weekday_stress.max(), 1)
            weekday_msg = f"Your highest stress day is {highest_stress_day} (avg {highest_stress_val}/5)"
    except Exception:
        pass
        
    return stats, correlation_msg, weekday_msg

def run_risk_engine(user_id, check_date=None):
    """
    Rule-Based Risk Engine:
    Rule 1: avg_stress >= 4.0 last 7 days -> "Chronic Stress Alert"
    Rule 2: sleep_hours < 6.0 for 3+ consecutive days -> "Sleep Deprivation Alert"
    Rule 3: wellness_score dropping >20 points in a week -> "Wellness Decline Alert"
    Rule 4: no log entry for 5 days -> "Engagement Alert"
    """
    if check_date is None:
        check_date = datetime.now().date()
    elif isinstance(check_date, datetime):
        check_date = check_date.date()
        
    alerts = []
    
    # Query all logs chronologically up to check_date
    logs_all = WellnessLog.query.filter_by(user_id=user_id)\
                                .filter(WellnessLog.log_date <= check_date)\
                                .order_by(WellnessLog.log_date.asc())\
                                .all()
                                
    if not logs_all:
        alerts.append({
            'id': 'engagement',
            'title': 'Engagement Alert',
            'description': 'You have not recorded any wellness logs yet. Consistent tracking helps you identify mental health trends.',
            'level': 'warning',
            'icon': 'calendar-x',
            'action_text': 'Log your first day',
            'action_url': url_for('wellness.log_entry')
        })
        return alerts
        
    # Rule 4: Engagement Alert (no log entry for 5 days)
    if check_date == datetime.now().date():
        most_recent_log = logs_all[-1]
        days_since_last_log = (check_date - most_recent_log.log_date).days
        if days_since_last_log >= 5:
            alerts.append({
                'id': 'engagement',
                'title': 'Engagement Alert',
                'description': f'No wellness log entry has been recorded for {days_since_last_log} days. Consistent tracking is key to self-care.',
                'level': 'warning',
                'icon': 'calendar-x',
                'action_text': 'Record a new entry',
                'action_url': url_for('wellness.log_entry')
            })
            
    # Get logs in the 7-day window ending at check_date
    seven_days_ago = check_date - timedelta(days=7)
    logs_7d = [log for log in logs_all if log.log_date > seven_days_ago]
    
    # Rule 1: Chronic Stress Alert (avg_stress >= 4.0 last 7 days)
    if logs_7d:
        avg_stress_7d = sum(int(log.stress_level) for log in logs_7d) / len(logs_7d)
        if avg_stress_7d >= 4.0:
            alerts.append({
                'id': 'chronic_stress',
                'title': 'Chronic Stress Alert',
                'description': f'Your average stress level over the last 7 days is high ({round(avg_stress_7d, 1)}/5). Please consider speaking to a counselor.',
                'level': 'danger',
                'icon': 'exclamation-triangle',
                'action_text': 'Contact Student Counselor',
                'action_url': 'mailto:counselor@susl.lk'
            })
            
    # Rule 2: Sleep Deprivation Alert (sleep_hours < 6.0 for 3+ consecutive days)
    sleep_deprivation_triggered = False
    if len(logs_all) >= 3:
        for i in range(len(logs_all) - 2):
            window = logs_all[i:i+3]
            is_consecutive = (window[1].log_date - window[0].log_date).days == 1 and \
                             (window[2].log_date - window[1].log_date).days == 1
            all_low_sleep = all(float(log.sleep_hours) < 6.0 for log in window)
            if is_consecutive and all_low_sleep:
                sleep_deprivation_triggered = True
                break
    if sleep_deprivation_triggered:
        alerts.append({
            'id': 'sleep_deprivation',
            'title': 'Sleep Deprivation Alert',
            'description': 'You have recorded less than 6 hours of sleep for 3 or more consecutive days. Try to establish a regular bedtime routine.',
            'level': 'danger',
            'icon': 'moon',
            'action_text': 'Improve sleep hygiene',
            'action_url': '#'
        })
        
    # Rule 3: Wellness Decline Alert (wellness_score dropping >20 points in a week)
    wellness_decline_triggered = False
    if len(logs_7d) >= 2:
        logs_7d_sorted = sorted(logs_7d, key=lambda x: x.log_date)
        for i in range(len(logs_7d_sorted)):
            for j in range(i+1, len(logs_7d_sorted)):
                score_drop = float(logs_7d_sorted[i].wellness_score) - float(logs_7d_sorted[j].wellness_score)
                if score_drop > 20.0:
                    wellness_decline_triggered = True
                    break
            if wellness_decline_triggered:
                break
    if wellness_decline_triggered:
        alerts.append({
            'id': 'wellness_decline',
            'title': 'Wellness Decline Alert',
            'description': 'Your overall wellness score dropped by more than 20 points within a single week. Take some time to reflect and prioritize self-care.',
            'level': 'danger',
            'icon': 'graph-down',
            'action_text': 'Prioritize self-care',
            'action_url': '#'
        })
        
    return alerts

def generate_static_charts(user_id):
    """
    Generates mood_trend.png, stress_chart.png, sleep_chart.png in static/charts/[user_id]/
    """
    logs = WellnessLog.query.filter_by(user_id=user_id).order_by(WellnessLog.log_date.asc()).all()
    if not logs:
        return
        
    # Ensure directory exists
    charts_dir = os.path.join(current_app.root_path, 'static', 'charts', str(user_id))
    os.makedirs(charts_dir, exist_ok=True)
    
    dates = [log.log_date for log in logs]
    moods = [int(log.mood_score) for log in logs]
    stresses = [int(log.stress_level) for log in logs]
    sleeps = [float(log.sleep_hours) for log in logs]
    sleep_qs = [int(log.sleep_quality) for log in logs]
    
    # Chart 1: mood_trend.png
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(dates, moods, color='#14b8a6', marker='o', linewidth=2.5, label='Mood Score')
    ax.set_title('Daily Mood Trend', fontsize=12, fontweight='bold', pad=15)
    ax.set_xlabel('Date', fontsize=10, labelpad=10)
    ax.set_ylabel('Mood Score (1-5)', fontsize=10, labelpad=10)
    ax.set_ylim(0.8, 5.2)
    ax.set_yticks([1, 2, 3, 4, 5])
    ax.grid(True, linestyle='--', alpha=0.5)
    fig.autofmt_xdate()
    plt.tight_layout()
    plt.savefig(os.path.join(charts_dir, 'mood_trend.png'), dpi=150)
    plt.close(fig)
    
    # Chart 2: stress_chart.png
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(dates, stresses, color='#ef4444', alpha=0.75, width=0.6, label='Stress Level')
    ax.set_title('Daily Stress Levels', fontsize=12, fontweight='bold', pad=15)
    ax.set_xlabel('Date', fontsize=10, labelpad=10)
    ax.set_ylabel('Stress Level (1-5)', fontsize=10, labelpad=10)
    ax.set_ylim(0, 5.5)
    ax.set_yticks([1, 2, 3, 4, 5])
    ax.grid(True, linestyle='--', alpha=0.5, axis='y')
    fig.autofmt_xdate()
    plt.tight_layout()
    plt.savefig(os.path.join(charts_dir, 'stress_chart.png'), dpi=150)
    plt.close(fig)
    
    # Chart 3: sleep_chart.png (Sleep Hours and Quality)
    fig, ax1 = plt.subplots(figsize=(8, 4))
    
    color = '#6366f1'
    ax1.set_xlabel('Date', fontsize=10, labelpad=10)
    ax1.set_ylabel('Sleep Hours', color=color, fontsize=10, labelpad=10)
    ax1.bar(dates, sleeps, color=color, alpha=0.6, width=0.6, label='Sleep Hours')
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.set_ylim(0, 16.5)
    
    ax2 = ax1.twinx()
    color = '#f43f5e'
    ax2.set_ylabel('Sleep Quality (1-5)', color=color, fontsize=10, labelpad=10)
    ax2.plot(dates, sleep_qs, color=color, marker='s', linewidth=2, label='Sleep Quality')
    ax2.tick_params(axis='y', labelcolor=color)
    ax2.set_ylim(0.8, 5.2)
    ax2.set_yticks([1, 2, 3, 4, 5])
    
    plt.title('Sleep Duration & Quality', fontsize=12, fontweight='bold', pad=15)
    fig.autofmt_xdate()
    plt.tight_layout()
    plt.savefig(os.path.join(charts_dir, 'sleep_chart.png'), dpi=150)
    plt.close(fig)

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
            generate_static_charts(current_user.id)
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
            generate_static_charts(current_user.id)
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
        generate_static_charts(current_user.id)
        flash("Wellness entry successfully deleted.", "success")
    except Exception as e:
        db.session.rollback()
        flash("An error occurred while deleting. Please try again.", "danger")
        
    return redirect(url_for('wellness.history'))

# Dashboard & Interactive Charts

@wellness.route('/dashboard')
@login_required
def dashboard():
    # Generate Matplotlib static charts for this user
    generate_static_charts(current_user.id)
    
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
        
    # 4. Rule-Based Risk Engine Check (Legacy and Comprehensive)
    show_risk_banner = check_high_stress_risk(current_user.id)
    active_alerts = run_risk_engine(current_user.id)
    
    # Query all logs of the user for comprehensive stats
    logs_all = WellnessLog.query.filter_by(user_id=current_user.id).order_by(WellnessLog.log_date.desc()).all()
    stats, correlation_msg, weekday_msg = compute_analytics(logs_all)
    
    # 5. Prepare Chart.js Data Packets (JSON)
    # Chart 1: Mood Trend (Line)
    mood_chart = {
        "labels": [log.log_date.strftime("%b %d") for log in logs_30d],
        "data": [log.mood_score for log in logs_30d]
    }
    
    # Chart 2: Stress Weekly Averages (Bar)
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
        active_alerts=active_alerts,
        stats=stats,
        correlation_msg=correlation_msg,
        weekday_msg=weekday_msg,
        chart_data=chart_data,
        local_time=local_time
    )

@wellness.route('/report')
@login_required
def report():
    # Generate Matplotlib static charts for this user
    generate_static_charts(current_user.id)
    
    # 1. Fetch all logs for this user to extract unique weeks
    logs_all = WellnessLog.query.filter_by(user_id=current_user.id).order_by(WellnessLog.log_date.desc()).all()
    if not logs_all:
        flash("You need to record at least one wellness log to view reports.", "info")
        return redirect(url_for('wellness.dashboard'))
        
    weeks = []
    seen_weeks = set()
    for log in logs_all:
        year, week, weekday = log.log_date.isocalendar()
        week_key = f"{year}-W{week:02d}"
        if week_key not in seen_weeks:
            seen_weeks.add(week_key)
            # Find start and end date
            monday = datetime.fromisocalendar(year, week, 1).date()
            sunday = datetime.fromisocalendar(year, week, 7).date()
            weeks.append({
                'key': week_key,
                'label': f"Week {week} ({monday.strftime('%b %d')} - {sunday.strftime('%b %d')}, {year})"
            })
            
    # Sort weeks reverse chronologically
    weeks = sorted(weeks, key=lambda x: x['key'], reverse=True)
    
    # 2. Determine selected week
    selected_week_key = request.args.get('week')
    if not selected_week_key or selected_week_key not in seen_weeks:
        # Default to the most recent week with logs
        selected_week_key = weeks[0]['key']
        
    # Find label for selected week
    selected_week_label = next(w['label'] for w in weeks if w['key'] == selected_week_key)
    
    # Parse selected week key
    year_str, week_str = selected_week_key.split('-W')
    sel_year = int(year_str)
    sel_week = int(week_str)
    
    # Calculate Monday and Sunday of selected week
    monday = datetime.fromisocalendar(sel_year, sel_week, 1).date()
    sunday = datetime.fromisocalendar(sel_year, sel_week, 7).date()
    
    # 3. Query logs for the selected week
    logs_week = WellnessLog.query.filter_by(user_id=current_user.id)\
                                 .filter(WellnessLog.log_date >= monday, WellnessLog.log_date <= sunday)\
                                 .order_by(WellnessLog.log_date.asc())\
                                 .all()
                                 
    # 4. Query logs for the previous week
    prev_monday = monday - timedelta(days=7)
    prev_sunday = sunday - timedelta(days=7)
    logs_prev = WellnessLog.query.filter_by(user_id=current_user.id)\
                                 .filter(WellnessLog.log_date >= prev_monday, WellnessLog.log_date <= prev_sunday)\
                                 .all()
                                 
    # 5. Calculate averages and percentage change
    metrics = {
        'mood_score': {'name': 'Mood Score (1-5)', 'higher_is_better': True},
        'stress_level': {'name': 'Stress Level (1-5)', 'higher_is_better': False},
        'sleep_hours': {'name': 'Sleep Duration (Hrs)', 'higher_is_better': True},
        'sleep_quality': {'name': 'Sleep Quality (1-5)', 'higher_is_better': True},
        'academic_workload': {'name': 'Academic Workload (1-5)', 'higher_is_better': False},
        'wellness_score': {'name': 'Wellness Index (0-100)', 'higher_is_better': True}
    }
    
    averages = {}
    for key, info in metrics.items():
        # This week's average
        if logs_week:
            if key == 'sleep_hours' or key == 'wellness_score':
                curr_avg = sum(float(getattr(l, key)) for l in logs_week) / len(logs_week)
            else:
                curr_avg = sum(int(getattr(l, key)) for l in logs_week) / len(logs_week)
        else:
            curr_avg = 0.0
            
        # Previous week's average
        if logs_prev:
            if key == 'sleep_hours' or key == 'wellness_score':
                prev_avg = sum(float(getattr(l, key)) for l in logs_prev) / len(logs_prev)
            else:
                prev_avg = sum(int(getattr(l, key)) for l in logs_prev) / len(logs_prev)
        else:
            prev_avg = 0.0
            
        # Percentage change
        pct_change = None
        arrow = ""
        css_class = "text-muted"
        
        if prev_avg > 0:
            pct_change = ((curr_avg - prev_avg) / prev_avg) * 100
            if abs(pct_change) < 0.01:
                pct_change = 0.0
                arrow = "➔"
                css_class = "text-secondary"
            elif pct_change > 0:
                arrow = "▲"
                css_class = "text-success" if info['higher_is_better'] else "text-danger"
            else:
                arrow = "▼"
                css_class = "text-danger" if info['higher_is_better'] else "text-success"
                
        averages[key] = {
            'name': info['name'],
            'current': round(curr_avg, 2),
            'previous': round(prev_avg, 2) if prev_avg > 0 else "N/A",
            'pct_change': f"{round(pct_change, 1)}%" if pct_change is not None else "N/A",
            'arrow': arrow,
            'class': css_class
        }
        
    # 6. Run Risk Engine for the selected week ending at Sunday
    active_alerts = run_risk_engine(current_user.id, check_date=sunday)
    
    # 7. Personalized clinical text recommendations
    recommendations = []
    has_alert = False
    for alert in active_alerts:
        if alert['id'] == 'chronic_stress':
            has_alert = True
            recommendations.append(
                "Your stress levels are consistently high. Please consider taking regular breaks, "
                "setting realistic daily goals, and scheduling a session with our university counselor "
                "(counselor@susl.lk) or speaking to a trusted mentor. Prioritize time management to ease academic pressure."
            )
        elif alert['id'] == 'sleep_deprivation':
            has_alert = True
            recommendations.append(
                "Chronic sleep deprivation severely impacts your emotional resilience and academic focus. "
                "Try to maintain a consistent sleep schedule by going to bed and waking up at the same time daily, "
                "avoiding screens 30 minutes before bed, and creating a quiet, dark sleeping environment."
            )
        elif alert['id'] == 'wellness_decline':
            has_alert = True
            recommendations.append(
                "Your wellness index has dropped sharply this week. This is a clear indicator that your current "
                "workload or life events are taking a toll. Take a proactive self-care day, reduce non-essential commitments, "
                "and ensure you are eating nutritious meals and connecting with friends."
            )
        elif alert['id'] == 'engagement':
            has_alert = True
            recommendations.append(
                "We notice a gap in your daily tracking. Logging your wellness indicators consistently is a powerful "
                "habit that builds self-awareness and allows the system to provide accurate, timely feedback for your mental health journey."
            )
            
    if not has_alert or (len(active_alerts) == 1 and active_alerts[0]['id'] == 'engagement' and logs_week):
        recommendations.append(
            "Excellent work! Your wellness indicators are balanced and within a healthy range this week. "
            "Continue tracking your metrics daily, practicing mindfulness, and maintaining your positive sleep and stress habits to sustain this equilibrium."
        )
        
    return render_template(
        'report.html',
        weeks=weeks,
        selected_week=selected_week_key,
        selected_week_label=selected_week_label,
        logs=logs_week,
        averages=averages,
        active_alerts=active_alerts,
        recommendations=recommendations,
        user_id=current_user.id
    )

@wellness.route('/export/pdf')
@login_required
def export_pdf():
    # 1. Security check: only allow current_user to download their own report, or admin/counselor
    user_id_param = request.args.get('user_id')
    if user_id_param:
        try:
            target_user_id = int(user_id_param)
        except (ValueError, TypeError):
            abort(400)
            
        if current_user.id != target_user_id and current_user.role not in ('admin', 'counselor'):
            abort(403)
        user = User.query.get_or_404(target_user_id)
    else:
        user = current_user
        
    # 2. Get period parameters (week or month)
    week_param = request.args.get('week')
    month_param = request.args.get('month')
    
    import datetime
    today_date = datetime.date.today()
    
    if week_param:
        try:
            year_str, week_str = week_param.split('-W')
            year = int(year_str)
            week = int(week_str)
            start_date = datetime.date.fromisocalendar(year, week, 1)
            end_date = datetime.date.fromisocalendar(year, week, 7)
            report_period_str = f"Week {week} ({start_date.strftime('%b %d')} - {end_date.strftime('%b %d')}, {year})"
        except Exception:
            abort(400)
    elif month_param:
        try:
            year_str, month_str = month_param.split('-')
            year = int(year_str)
            month = int(month_str)
            start_date = datetime.date(year, month, 1)
            next_month = month + 1 if month < 12 else 1
            next_year = year if month < 12 else year + 1
            end_date = datetime.date(next_year, next_month, 1) - datetime.timedelta(days=1)
            report_period_str = start_date.strftime("%B %Y")
        except Exception:
            abort(400)
    else:
        # Default to current week
        year, week, day = today_date.isocalendar()
        start_date = datetime.date.fromisocalendar(year, week, 1)
        end_date = datetime.date.fromisocalendar(year, week, 7)
        report_period_str = f"Week {week} ({start_date.strftime('%b %d')} - {end_date.strftime('%b %d')}, {year})"

    # 3. Query logs in range
    logs = WellnessLog.query.filter_by(user_id=user.id)\
                            .filter(WellnessLog.log_date >= start_date, WellnessLog.log_date <= end_date)\
                            .order_by(WellnessLog.log_date.asc())\
                            .all()
                            
    # Ensure charts are generated
    generate_static_charts(user.id)
    
    # 4. ReportLab Imports
    import io
    from flask import send_file
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    
    pdf_buffer = io.BytesIO()
    
    # 0.5 inch margin = 36 points
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    # Primary navy, secondary teal
    navy_color = colors.HexColor('#1e3a8a')
    teal_color = colors.HexColor('#0d9488')
    slate_dark = colors.HexColor('#1e293b')
    
    # Modify default body text
    styles['Normal'].textColor = slate_dark
    styles['Normal'].fontSize = 10
    styles['Normal'].leading = 14
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=navy_color,
        spaceAfter=12
    )
    
    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=navy_color,
        spaceBefore=12,
        spaceAfter=8
    )
    
    header_title_style = ParagraphStyle(
        'HeaderTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.white,
        alignment=1 # Center
    )
    
    header_subtitle_style = ParagraphStyle(
        'HeaderSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#93c5fd'),
        alignment=1 # Center
    )
    
    header_desc_style = ParagraphStyle(
        'HeaderDesc',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=15,
        textColor=colors.white,
        alignment=1 # Center
    )
    
    story = []
    
    # ================= PAGE 1 =================
    # University Style Header Banner
    header_html = [
        [Paragraph("SABARAGAMUWA UNIVERSITY OF SRI LANKA", header_title_style)],
        [Paragraph("Department of Computing and Information Systems", header_subtitle_style)],
        [Paragraph("Smart Student Mental Wellness Tracking System", header_desc_style)]
    ]
    header_table = Table(header_html, colWidths=[523])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), navy_color),
        ('PADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (0,0), 14),
        ('BOTTOMPADDING', (0,2), (0,2), 14),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 15))
    
    # Document Title
    story.append(Paragraph("STUDENT WELLNESS REPORT", title_style))
    
    # Student details table
    details_data = [
        [Paragraph("<b>Student Name:</b>", styles['Normal']), Paragraph(user.name, styles['Normal']),
         Paragraph("<b>Registration No:</b>", styles['Normal']), Paragraph(user.reg_number, styles['Normal'])],
        [Paragraph("<b>Account Role:</b>", styles['Normal']), Paragraph(user.role.capitalize(), styles['Normal']),
         Paragraph("<b>Report Period:</b>", styles['Normal']), Paragraph(report_period_str, styles['Normal'])],
        [Paragraph("<b>Generated On:</b>", styles['Normal']), Paragraph(datetime.datetime.now().strftime("%B %d, %Y %H:%M"), styles['Normal']),
         Paragraph("", styles['Normal']), Paragraph("", styles['Normal'])]
    ]
    details_table = Table(details_data, colWidths=[100, 160, 110, 153])
    details_table.setStyle(TableStyle([
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LINEBELOW', (0,2), (-1,2), 1, colors.HexColor('#cbd5e1')),
    ]))
    story.append(details_table)
    story.append(Spacer(1, 20))
    
    # Summary Statistics heading
    story.append(Paragraph("Wellness Period Summary", section_heading))
    
    # Compute summary statistics
    if logs:
        avg_wellness = sum(float(l.wellness_score) for l in logs) / len(logs)
        avg_mood = sum(int(l.mood_score) for l in logs) / len(logs)
        avg_stress = sum(int(l.stress_level) for l in logs) / len(logs)
        avg_sleep = sum(float(l.sleep_hours) for l in logs) / len(logs)
    else:
        avg_wellness = avg_mood = avg_stress = avg_sleep = 0.0
        
    # Build 2x2 grid of stat boxes
    stat_data = [
        [
            Paragraph("<font size=10 color='#64748b'><b>Average Wellness Index</b></font><br/><font size=22 color='#0d9488'><b>{:.1f}%</b></font>".format(avg_wellness), styles['Normal']),
            Paragraph("<font size=10 color='#64748b'><b>Average Mood Rating</b></font><br/><font size=22 color='#3b82f6'><b>{:.1f}/5</b></font>".format(avg_mood), styles['Normal'])
        ],
        [
            Paragraph("<font size=10 color='#64748b'><b>Average Stress Level</b></font><br/><font size=22 color='#ef4444'><b>{:.1f}/5</b></font>".format(avg_stress), styles['Normal']),
            Paragraph("<font size=10 color='#64748b'><b>Average Sleep Duration</b></font><br/><font size=22 color='#6366f1'><b>{:.1f} hrs</b></font>".format(avg_sleep), styles['Normal'])
        ]
    ]
    stat_table = Table(stat_data, colWidths=[255, 255], rowHeights=[75, 75])
    stat_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (0,0), 1, colors.HexColor('#e2e8f0')),
        ('BOX', (1,0), (1,0), 1, colors.HexColor('#e2e8f0')),
        ('BOX', (0,1), (0,1), 1, colors.HexColor('#e2e8f0')),
        ('BOX', (1,1), (1,1), 1, colors.HexColor('#e2e8f0')),
        ('PADDING', (0,0), (-1,-1), 15),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(stat_table)
    
    # Add a brief clinical summary note
    story.append(Spacer(1, 25))
    story.append(Paragraph("<b>Clinical Notes & Interpretation:</b>", styles['Normal']))
    
    # Find active alerts for Page 1 footer
    alerts = run_risk_engine(user.id, check_date=end_date)
    if alerts:
        alert_desc = "The clinical risk engine has flagged the following alerts: " + ", ".join([a['title'] for a in alerts]) + ". Please refer to the online dashboard for personalized counselor-backed self-care recommendations."
    else:
        alert_desc = "Overall mental wellness metrics are stable and within healthy baseline ranges for this period. Continue logging daily to build emotional self-awareness and track ongoing trends."
        
    story.append(Paragraph(alert_desc, styles['Normal']))
    
    # Page 1 Footer branding
    story.append(Spacer(1, 40))
    story.append(Paragraph("<font size=8 color='#94a3b8'>This document is generated by the Smart Mental Wellness Tracking System under the Faculty of Applied Sciences, Sabaragamuwa University of Sri Lanka. Confidentiality is preserved. © 2026 SUSL.</font>", styles['Normal']))
    
    story.append(PageBreak())
    
    # ================= PAGE 2 =================
    story.append(Paragraph("Wellness Analytics & Visual Trends", title_style))
    story.append(Paragraph("Detailed longitudinal analysis of your recorded wellness parameters across mood, stress, and sleep duration.", styles['Normal']))
    story.append(Spacer(1, 15))
    
    # Chart image paths
    charts_dir = os.path.join(current_app.root_path, 'static', 'charts', str(user.id))
    mood_img = os.path.join(charts_dir, 'mood_trend.png')
    stress_img = os.path.join(charts_dir, 'stress_chart.png')
    sleep_img = os.path.join(charts_dir, 'sleep_chart.png')
    
    # Flowable chart inclusions
    for img_path, img_label in [(mood_img, "Mood Trend Chart"), (stress_img, "Stress Levels Chart"), (sleep_img, "Sleep Analysis Chart")]:
        if os.path.exists(img_path):
            try:
                story.append(Image(img_path, width=440, height=190))
                story.append(Spacer(1, 10))
            except Exception:
                story.append(Paragraph(f"[Error rendering {img_label}]", styles['Normal']))
                story.append(Spacer(1, 15))
        else:
            story.append(Paragraph(f"[{img_label} not available for this period]", styles['Normal']))
            story.append(Spacer(1, 15))
            
    story.append(PageBreak())
    
    # ================= PAGE 3 =================
    story.append(Paragraph("Daily Metrics Breakdown", title_style))
    story.append(Paragraph(f"Chronological listing of all recorded self-care indicators for the period of <b>{report_period_str}</b>.", styles['Normal']))
    story.append(Spacer(1, 15))
    
    # Table header
    table_data = [[
        Paragraph("<b>Date</b>", ParagraphStyle('WH', parent=styles['Normal'], fontName='Helvetica-Bold', textColor=colors.white)),
        Paragraph("<b>Mood</b>", ParagraphStyle('WH', parent=styles['Normal'], fontName='Helvetica-Bold', textColor=colors.white, alignment=1)),
        Paragraph("<b>Stress</b>", ParagraphStyle('WH', parent=styles['Normal'], fontName='Helvetica-Bold', textColor=colors.white, alignment=1)),
        Paragraph("<b>Sleep (Hrs)</b>", ParagraphStyle('WH', parent=styles['Normal'], fontName='Helvetica-Bold', textColor=colors.white, alignment=1)),
        Paragraph("<b>Sleep Quality</b>", ParagraphStyle('WH', parent=styles['Normal'], fontName='Helvetica-Bold', textColor=colors.white, alignment=1)),
        Paragraph("<b>Workload</b>", ParagraphStyle('WH', parent=styles['Normal'], fontName='Helvetica-Bold', textColor=colors.white, alignment=1)),
        Paragraph("<b>Wellness Index</b>", ParagraphStyle('WH', parent=styles['Normal'], fontName='Helvetica-Bold', textColor=colors.white, alignment=1))
    ]]
    
    # Style helper for table cell text
    cell_center = ParagraphStyle('CC', parent=styles['Normal'], alignment=1)
    
    for log in logs:
        score_val = float(log.wellness_score)
        if score_val >= 70.0:
            score_color = '#10b981'  # Green
        elif score_val >= 50.0:
            score_color = '#f59e0b'  # Amber
        else:
            score_color = '#ef4444'  # Red
            
        score_p = Paragraph(f"<font color='{score_color}'><b>{score_val:.1f}%</b></font>", cell_center)
        
        table_data.append([
            Paragraph(log.log_date.strftime("%a, %b %d"), styles['Normal']),
            Paragraph(f"{log.mood_score}/5", cell_center),
            Paragraph(f"{log.stress_level}/5", cell_center),
            Paragraph(f"{log.sleep_hours:.1f}", cell_center),
            Paragraph(f"{log.sleep_quality}/5", cell_center),
            Paragraph(f"{log.academic_workload}/5", cell_center),
            score_p
        ])
        
    if not logs:
        # Placeholder row if empty
        table_data.append([
            Paragraph("No logs recorded in this date range.", styles['Normal']),
            "", "", "", "", "", ""
        ])
        
    metrics_table = Table(
        table_data, 
        colWidths=[95, 55, 55, 65, 65, 90, 98]
    )
    
    # Build TableStyle
    t_style = [
        ('BACKGROUND', (0,0), (-1,0), navy_color),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 7),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
    ]
    
    # Add zebra striping for data rows
    for r in range(1, len(table_data)):
        bg_color = colors.HexColor('#f8fafc') if r % 2 == 0 else colors.white
        t_style.append(('BACKGROUND', (0, r), (-1, r), bg_color))
        
    metrics_table.setStyle(TableStyle(t_style))
    story.append(metrics_table)
    
    # Notes Section at the bottom of Page 3
    story.append(Spacer(1, 25))
    story.append(Paragraph("<b>Log Notes & Context:</b>", styles['Normal']))
    
    has_notes = False
    for log in logs:
        if log.notes:
            has_notes = True
            story.append(Paragraph(f"• <b>{log.log_date.strftime('%b %d')}</b>: {log.notes}", styles['Normal']))
            story.append(Spacer(1, 4))
            
    if not has_notes:
        story.append(Paragraph("<font color='#94a3b8'>No qualitative notes were recorded during this period.</font>", styles['Normal']))
        
    # Build the document
    doc.build(story)
    
    pdf_buffer.seek(0)
    
    date_str = end_date.strftime("%Y%m%d")
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f"wellness_{user.reg_number}_{date_str}.pdf",
        mimetype='application/pdf'
    )
