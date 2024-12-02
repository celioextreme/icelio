from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from functools import wraps
from database import get_db_connection, init_db, add_project, add_task, update_task_status, delete_task, add_entry, add_exit, add_transaction, get_dashboard_data, delete_entry, delete_exit
from datetime import datetime, timedelta
from utils import get_next_occurrence  # Use absolute import
import threading
import time

app = Flask(__name__)
app.secret_key = 'your_secret_key'

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.template_filter('datetimeformat')
def datetimeformat(value):
    return value.strftime('%d/%m/%Y')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'celio' and password == 'Extreme1#':
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Credenciais inválidas")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/')
@admin_required
def dashboard():
    filter_type = request.args.get('filter')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    project_id = request.args.get('project_id', '')  # Get project_id with empty string as default

    if filter_type == 'today':
        start_date = end_date = datetime.now().strftime('%Y-%m-%d')
    elif filter_type == 'yesterday':
        start_date = end_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    elif filter_type == '7days':
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    elif filter_type == 'this-month':
        start_date = datetime.now().replace(day=1).strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')

    if start_date and " " not in start_date:
        start_date += " 00:00:00"
    if end_date and " " not in end_date:
        end_date += " 23:59:59"

    data = get_dashboard_data(start_date, end_date, project_id)
    revenue_labels = [date.strftime('%d/%m') for date, _ in data['revenue_data']]
    revenue_data = [float(amount) for _, amount in data['revenue_data']]
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM projects ORDER BY name")
    projects = cur.fetchall()
    
    cur.execute("SELECT id, name, due_date, description FROM tasks WHERE completed = FALSE ORDER BY created_at ASC LIMIT 4")
    pending_tasks = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('index.html', 
                         faturamento=data['faturamento'],
                         gastos=data['gastos'],
                         lucro=data['lucro'],
                         total_vendas=data['total_vendas'],
                         faturamento_change=data['faturamento_change'],
                         gastos_change=data['gastos_change'],
                         lucro_change=data['lucro_change'],
                         vendas_change=data['vendas_change'],
                         revenue_labels=revenue_labels,
                         revenue_data=revenue_data,
                         ranking_produtos=data['ranking_produtos'],
                         filter=filter_type,
                         projects=projects,
                         project_id=project_id,
                         pending_tasks=pending_tasks,
                         datetime=datetime)  # Pass datetime to the template

@app.route('/tasks')
@admin_required
def tasks():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM projects")
    projects = cur.fetchall()
    cur.execute("SELECT * FROM tasks WHERE completed = FALSE")
    pending_tasks = cur.fetchall()
    cur.execute("SELECT * FROM tasks WHERE completed = TRUE")
    completed_tasks = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('tasks.html', projects=projects, pending_tasks=pending_tasks, completed_tasks=completed_tasks)

@app.route('/add_project', methods=['POST'])
@admin_required
def add_project_route():
    name = request.form['name']
    add_project(name)
    return redirect(url_for('tasks'))

@app.route('/add_task', methods=['POST'])
@admin_required
def add_task_route():
    name = request.form['name']
    project_id = request.form['project_id']
    due_date = request.form['due_date']
    description = request.form['description']
    add_task(name, project_id, due_date, description)
    return redirect(url_for('tasks'))

@app.route('/update_task_status/<int:task_id>', methods=['POST'])
@admin_required
def update_task_status_route(task_id):
    completed = request.form['completed'] == 'true'
    update_task_status(task_id, completed)
    return '', 204

@app.route('/delete_task/<int:task_id>', methods=['POST'])
@admin_required
def delete_task_route(task_id):
    delete_task(task_id)
    return '', 204

@app.route('/report')
@admin_required
def report():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM projects")
    projects = cur.fetchall()
    cur.execute("""
        SELECT e.id, e.amount, e.date, e.recurrence, e.recurrence_day, e.created_at, p.name as project_name, e.project_id 
        FROM entries e 
        JOIN projects p ON e.project_id = p.id
    """)
    entries = cur.fetchall()
    cur.execute("""
        SELECT ex.id, ex.amount, ex.date, ex.recurrence, ex.recurrence_day, ex.created_at, p.name as project_name, ex.project_id 
        FROM exits ex 
        JOIN projects p ON ex.project_id = p.id
    """)
    exits = cur.fetchall()
    cur.close()
    conn.close()
    current_date = datetime.now().strftime('%Y-%m-%d')
    return render_template('report.html', projects=projects, entries=entries, exits=exits, current_date=current_date)

def is_today(date_str):
    date = datetime.strptime(date_str, '%Y-%m-%d').date()
    return date == datetime.now().date()

def get_next_occurrence(day, reference_date=None):
    if reference_date is None:
        reference_date = datetime.now()
    
    try:
        next_date = datetime(reference_date.year, reference_date.month, day)
        if next_date < reference_date:
            if reference_date.month == 12:
                next_date = datetime(reference_date.year + 1, 1, day)
            else:
                next_date = datetime(reference_date.year, reference_date.month + 1, day)
    except ValueError:
        # Handle invalid dates (e.g., February 30)
        if reference_date.month == 12:
            next_date = datetime(reference_date.year + 1, 1, day)
        else:
            next_date = datetime(reference_date.year, reference_date.month + 1, day)
    
    return next_date

def schedule_recurring_transaction(project_id, amount, day, type):
    def add_recurring_transaction():
        while True:
            now = datetime.now()
            next_date = get_next_occurrence(day)
            
            # Calcular tempo de espera até a próxima data
            wait_seconds = (next_date - now).total_seconds()
            if wait_seconds > 0:
                time.sleep(wait_seconds)
            
            project_name = get_project_name(project_id)
            add_transaction(project_id, project_name, amount, next_date.strftime('%Y-%m-%d'), type)
            
            # Aguardar alguns segundos para evitar duplicatas
            time.sleep(2)
    
    thread = threading.Thread(target=add_recurring_transaction, daemon=True)
    thread.start()

def schedule_one_time_transaction(project_id, amount, date, type):
    def add_one_time_transaction():
        now = datetime.now()
        transaction_date = datetime.strptime(date, '%Y-%m-%d')
        
        # Calcular tempo de espera até a data
        wait_seconds = (transaction_date - now).total_seconds()
        if wait_seconds > 0:
            time.sleep(wait_seconds)
            project_name = get_project_name(project_id)
            add_transaction(project_id, project_name, amount, date, type)
    
    if not is_today(date):
        thread = threading.Thread(target=add_one_time_transaction, daemon=True)
        thread.start()

@app.route('/add_entry', methods=['POST'])
@admin_required
def add_entry_route():
    project_id = request.form['project_id']
    amount = request.form['amount']
    date = request.form['date']
    recurrence = 'recurrence' in request.form
    recurrence_day = int(request.form['recurrence_day']) if recurrence else None
    
    entry_id = add_entry(project_id, amount, date, recurrence, recurrence_day)
    
    if recurrence:
        schedule_recurring_transaction(project_id, amount, recurrence_day, 'entry')
    elif is_today(date):
        project_name = get_project_name(project_id)
        add_transaction(project_id, project_name, amount, date, 'entry')
    else:
        schedule_one_time_transaction(project_id, amount, date, 'entry')
    
    return redirect(url_for('report'))

@app.route('/add_exit', methods=['POST'])
@admin_required
def add_exit_route():
    project_id = request.form['project_id']
    amount = request.form['amount']
    date = request.form['date']
    recurrence = 'recurrence' in request.form
    recurrence_day = int(request.form['recurrence_day']) if recurrence else None
    
    exit_id = add_exit(project_id, amount, date, recurrence, recurrence_day)
    
    if recurrence:
        schedule_recurring_transaction(project_id, amount, recurrence_day, 'exit')
    elif is_today(date):
        project_name = get_project_name(project_id)
        add_transaction(project_id, project_name, amount, date, 'exit')
    else:
        schedule_one_time_transaction(project_id, amount, date, 'exit')
    
    return redirect(url_for('report'))

@app.route('/next_date')
@admin_required
def next_date():
    day = int(request.args.get('day'))
    today = datetime.now()
    next_date = datetime(today.year, today.month, day, today.hour, today.minute, today.second)
    if next_date < today:
        if today.month == 12:
            next_date = datetime(today.year + 1, 1, day, today.hour, today.minute, today.second)
        else:
            next_date = datetime(today.year, today.month + 1, day, today.hour, today.minute, today.second)
    return jsonify({'next_date': next_date.strftime('%d/%m/%Y')})

@app.route('/add', methods=['POST'])
def add_transaction_route():
    data = request.get_json()
    project_id = data.get('project_id')
    amount = data.get('amount')
    date = data.get('date')
    type = data.get('type')
    
    if not project_id or not amount or not date or not type:
        return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400
    
    project_name = get_project_name(project_id)
    add_transaction(project_id, project_name, amount, date, type)
    
    return jsonify({'status': 'success'}), 201

@app.route('/delete_entry/<int:entry_id>', methods=['DELETE'])
@admin_required
def delete_entry_route(entry_id):
    delete_entry(entry_id)
    return '', 204

@app.route('/delete_exit/<int:exit_id>', methods=['DELETE'])
@admin_required
def delete_exit_route(exit_id):
    delete_exit(exit_id)
    return '', 204

@app.route('/edit_entry', methods=['POST'])
@admin_required
def edit_entry_route():
    entry_id = request.form['entry_id']
    project_id = request.form['project_id']
    amount = request.form['amount']
    date = request.form['date']
    recurrence = 'recurrence' in request.form
    recurrence_day = int(request.form['recurrence_day']) if recurrence else None
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE entries 
        SET project_id = %s, amount = %s, date = %s, recurrence = %s, recurrence_day = %s 
        WHERE id = %s
    """, (project_id, amount, date, recurrence, recurrence_day, entry_id))
    conn.commit()
    cur.close()
    conn.close()
    
    return redirect(url_for('report'))

@app.route('/edit_exit', methods=['POST'])
@admin_required
def edit_exit_route():
    exit_id = request.form['exit_id']
    project_id = request.form['project_id']
    amount = request.form['amount']
    date = request.form['date']
    recurrence = 'recurrence' in request.form
    recurrence_day = int(request.form['recurrence_day']) if recurrence else None
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE exits 
        SET project_id = %s, amount = %s, date = %s, recurrence = %s, recurrence_day = %s 
        WHERE id = %s
    """, (project_id, amount, date, recurrence, recurrence_day, exit_id))
    conn.commit()
    cur.close()
    conn.close()
    
    return redirect(url_for('report'))

def get_project_name(project_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT name FROM projects WHERE id = %s", (project_id,))
    project_name = cur.fetchone()[0]
    cur.close()
    conn.close()
    return project_name

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
