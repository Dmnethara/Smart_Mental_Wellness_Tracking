from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import login_required, current_user
from models import db, User, WellnessLog
from decorators import admin_required
from datetime import datetime, timedelta
from collections import Counter
import json
from wellness import (
    check_high_stress_risk, 
    run_risk_engine, 
    calculate_streak, 
    compute_analytics, 
    generate_static_charts
)

# Create Blueprint
admin = Blueprint('admin', __name__, url_prefix='/admin')

def get_student_risk_status(student):
    """
    Classifies student risk status and returns:
    (status_label, sorting_priority)
    - at-risk (Red, Priority 3)
    - watch (Amber, Priority 2)
    - healthy (Green, Priority 1)
    """
    # 1. Calculate 7-day average stress
    today = datetime.now().date()
    seven_days_ago = today - timedelta(days=7)
    logs_7d = [log for log in student.logs if log.log_date > seven_days_ago]
    
    avg_stress_7d = 0.0
    if logs_7d:
        avg_stress_7d = sum(int(log.stress_level) for log in logs_7d) / len(logs_7d)
        
    # 2. High stress risk check (5 consecutive days >= 4)
    has_high_stress_risk = check_high_stress_risk(student.id)
    
    # 3. Active alerts check from the risk engine
    alerts = run_risk_engine(student.id)
    has_danger_alert = any(a['level'] == 'danger' for a in alerts)
    has_warning_alert = any(a['level'] == 'warning' for a in alerts)
    
    if has_high_stress_risk or avg_stress_7d >= 4.0 or has_danger_alert:
        return 'at-risk', 3
    elif avg_stress_7d >= 3.0 or has_warning_alert:
        return 'watch', 2
    else:
        return 'healthy', 1

@admin.route('/dashboard')
@login_required
@admin_required
def dashboard():
    # 1. Total Students Registered
    total_students = User.query.filter_by(role='student').count()
    
    # 2. Total Logs This Week (last 7 days including today)
    today = datetime.now().date()
    start_of_week = today - timedelta(days=6)
    total_logs_week = WellnessLog.query.filter(WellnessLog.log_date >= start_of_week).count()
    
    # 3. Students At-Risk (stress >= 4 for 5 days)
    students = User.query.filter_by(role='student').all()
    at_risk_count = 0
    for student in students:
        if check_high_stress_risk(student.id):
            at_risk_count += 1
            
    # 4. Average System Wellness Score today
    logs_today = WellnessLog.query.filter_by(log_date=today).all()
    if logs_today:
        avg_wellness_today = sum(float(log.wellness_score) for log in logs_today) / len(logs_today)
    else:
        avg_wellness_today = 0.0
        
    # 5. Recent Alerts for Dashboard Quick View
    recent_alerts = []
    for student in students:
        student_alerts = run_risk_engine(student.id)
        for alert in student_alerts:
            # Skip engagement warnings for quick dashboard to focus on severe/active issues
            if alert['id'] == 'engagement':
                continue
            recent_alerts.append({
                'student': student,
                'alert': alert
            })
    # Sort recent alerts by danger level
    recent_alerts = sorted(recent_alerts, key=lambda x: x['alert']['level'] == 'danger', reverse=True)[:5]
    
    return render_template(
        'admin/dashboard.html',
        total_students=total_students,
        total_logs_week=total_logs_week,
        at_risk_count=at_risk_count,
        avg_wellness_today=round(avg_wellness_today, 1),
        recent_alerts=recent_alerts
    )

@admin.route('/students')
@login_required
@admin_required
def students():
    students_raw = User.query.filter_by(role='student').all()
    students_list = []
    
    today = datetime.now().date()
    seven_days_ago = today - timedelta(days=7)
    thirty_days_ago = today - timedelta(days=30)
    
    for s in students_raw:
        total_logs = len(s.logs)
        last_log = None
        avg_stress_7d = 0.0
        avg_wellness_30d = 0.0
        
        if total_logs > 0:
            last_log = max(log.log_date for log in s.logs)
            
            # 7-day stress average
            logs_7d = [log for log in s.logs if log.log_date > seven_days_ago]
            if logs_7d:
                avg_stress_7d = sum(int(log.stress_level) for log in logs_7d) / len(logs_7d)
                
            # 30-day wellness index average
            logs_30d = [log for log in s.logs if log.log_date >= thirty_days_ago]
            if logs_30d:
                avg_wellness_30d = sum(float(log.wellness_score) for log in logs_30d) / len(logs_30d)
        
        risk_status, risk_priority = get_student_risk_status(s)
        
        students_list.append({
            'student': s,
            'total_logs': total_logs,
            'last_log_date': last_log.strftime('%Y-%m-%d') if last_log else 'N/A',
            'avg_stress_7d': round(avg_stress_7d, 2) if total_logs > 0 else 'N/A',
            'avg_wellness_30d': round(avg_wellness_30d, 1) if total_logs > 0 else 0.0,
            'risk_status': risk_status,
            'risk_priority': risk_priority,
            'is_flagged': s.is_flagged
        })
        
    # Sort by risk priority (worst first, i.e., 3, 2, 1)
    students_list = sorted(students_list, key=lambda x: x['risk_priority'], reverse=True)
    
    return render_template('admin/students.html', students=students_list)

@admin.route('/student/<int:student_id>')
@login_required
@admin_required
def student_detail(student_id):
    student = User.query.get_or_404(student_id)
    if student.role != 'student':
        abort(404)
        
    # Generate charts for this student
    generate_static_charts(student.id)
    
    # Replicate student's dashboard data
    thirty_days_ago = datetime.now().date() - timedelta(days=30)
    logs_30d = WellnessLog.query.filter_by(user_id=student.id)\
                                 .filter(WellnessLog.log_date >= thirty_days_ago)\
                                 .order_by(WellnessLog.log_date.asc())\
                                 .all()
                                 
    seven_days_ago = datetime.now().date() - timedelta(days=7)
    logs_7d = [log for log in logs_30d if log.log_date >= seven_days_ago]
    
    # Calculate Weekly Stats
    if logs_7d:
        avg_mood = sum(log.mood_score for log in logs_7d) / len(logs_7d)
        avg_stress = sum(log.stress_level for log in logs_7d) / len(logs_7d)
        
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
        
        if avg_stress < 2.5:
            stress_class = "text-success"
            stress_text = "Low"
        elif avg_stress < 3.5:
            stress_class = "text-warning"
            stress_text = "Moderate"
        else:
            stress_class = "text-danger"
            stress_text = "High"
        avg_stress_display = f"{round(avg_stress, 1)} ({stress_text})"
    else:
        avg_mood_display = "N/A"
        avg_stress_display = "N/A"
        stress_class = "text-muted"
        
    streak_days = calculate_streak(student.id)
    
    if logs_30d:
        avg_wellness = sum(float(log.wellness_score) for log in logs_30d) / len(logs_30d)
        avg_wellness_display = round(avg_wellness, 1)
    else:
        avg_wellness_display = 0.0
        
    show_risk_banner = check_high_stress_risk(student.id)
    active_alerts = run_risk_engine(student.id)
    
    logs_all = WellnessLog.query.filter_by(user_id=student.id).order_by(WellnessLog.log_date.desc()).all()
    stats, correlation_msg, weekday_msg = compute_analytics(logs_all)
    
    # Generate Chart.js structures
    mood_chart = {
        "labels": [log.log_date.strftime("%b %d") for log in logs_30d],
        "data": [log.mood_score for log in logs_30d]
    }
    
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
        "labels": ["Week 1", "Week 2", "Week 3", "Week 4"],
        "data": [get_avg_stress(week1_logs), get_avg_stress(week2_logs), get_avg_stress(week3_logs), get_avg_stress(week4_logs)]
    }
    
    sleep_chart = {
        "labels": [log.log_date.strftime("%b %d") for log in logs_30d],
        "hours": [float(log.sleep_hours) for log in logs_30d],
        "quality": [log.sleep_quality for log in logs_30d]
    }
    
    wellness_chart = {
        "labels": [log.log_date.strftime("%b %d") for log in logs_30d],
        "data": [float(log.wellness_score) for log in logs_30d]
    }
    
    chart_data = {
        "mood": json.dumps(mood_chart),
        "stress": json.dumps(stress_chart),
        "sleep": json.dumps(sleep_chart),
        "wellness": json.dumps(wellness_chart)
    }
    
    return render_template(
        'admin/student_detail.html',
        student=student,
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
        logs=logs_all
    )

@admin.route('/student/<int:student_id>/flag', methods=['POST'])
@login_required
@admin_required
def flag_student(student_id):
    student = User.query.get_or_404(student_id)
    if student.role != 'student':
        abort(404)
        
    # Toggle flag status
    student.is_flagged = not student.is_flagged
    db.session.commit()
    
    status_str = "flagged for counseling" if student.is_flagged else "unflagged"
    flash(f"Student {student.name} was successfully {status_str}.", "success")
    return redirect(url_for('admin.student_detail', student_id=student.id))

@admin.route('/analytics')
@login_required
@admin_required
def analytics():
    # 1. Average Wellness Score over time (all students combined)
    # Query all logs grouped by date
    all_logs = WellnessLog.query.order_by(WellnessLog.log_date.asc()).all()
    
    date_wellness = {}
    date_stress = {}
    
    for log in all_logs:
        date_str = log.log_date.strftime("%Y-%m-%d")
        if date_str not in date_wellness:
            date_wellness[date_str] = []
            date_stress[date_str] = []
        date_wellness[date_str].append(float(log.wellness_score))
        date_stress[date_str].append(int(log.stress_level))
        
    avg_wellness_over_time = {
        "labels": sorted(list(date_wellness.keys())),
        "data": [round(sum(date_wellness[d])/len(date_wellness[d]), 2) for d in sorted(list(date_wellness.keys()))]
    }
    
    # 2. Stress Distribution Histogram (Frequency of 1-5 levels)
    stress_levels = [int(log.stress_level) for log in all_logs]
    stress_counts = Counter(stress_levels)
    stress_dist = {
        "labels": ["1 (Low)", "2", "3 (Medium)", "4", "5 (High)"],
        "data": [stress_counts.get(1, 0), stress_counts.get(2, 0), stress_counts.get(3, 0), stress_counts.get(4, 0), stress_counts.get(5, 0)]
    }
    
    # 3. Most Common Risk Alerts Triggered
    # Run risk engine for all students
    students = User.query.filter_by(role='student').all()
    alert_counts = Counter()
    for student in students:
        alerts = run_risk_engine(student.id)
        for alert in alerts:
            alert_counts[alert['title']] += 1
            
    alerts_triggered = {
        "labels": list(alert_counts.keys()),
        "data": list(alert_counts.values())
    }
    
    # 4. Day-of-Week Stress averages (Heatmap/Bar chart representation)
    # Convert dates to day names
    weekday_stress = {d: [] for d in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]}
    for log in all_logs:
        weekday_name = log.log_date.strftime("%A")
        if weekday_name in weekday_stress:
            weekday_stress[weekday_name].append(int(log.stress_level))
            
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekday_stress_avg = {
        "labels": day_order,
        "data": [round(sum(weekday_stress[d])/len(weekday_stress[d]), 2) if weekday_stress[d] else 0.0 for d in day_order]
    }
    
    chart_data = {
        "wellness_trend": json.dumps(avg_wellness_over_time),
        "stress_dist": json.dumps(stress_dist),
        "alerts_triggered": json.dumps(alerts_triggered),
        "weekday_stress": json.dumps(weekday_stress_avg)
    }
    
    return render_template('admin/analytics.html', chart_data=chart_data)

@admin.route('/alerts')
@login_required
@admin_required
def alerts():
    students = User.query.filter_by(role='student').all()
    active_alerts_list = []
    
    for student in students:
        student_alerts = run_risk_engine(student.id)
        for alert in student_alerts:
            # Find the date this alert applies to (default to last log date)
            last_log = WellnessLog.query.filter_by(user_id=student.id).order_by(WellnessLog.log_date.desc()).first()
            log_date_str = last_log.log_date.strftime("%Y-%m-%d") if last_log else "N/A"
            
            active_alerts_list.append({
                'student': student,
                'title': alert['title'],
                'description': alert['description'],
                'level': alert['level'],
                'icon': alert['icon'],
                'date_triggered': log_date_str
            })
            
    # Sort alerts: danger level first
    active_alerts_list = sorted(active_alerts_list, key=lambda x: x['level'] == 'danger', reverse=True)
    
    return render_template('admin/alerts.html', alerts=active_alerts_list)
