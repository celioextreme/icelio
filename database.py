import psycopg2
from psycopg2 import sql
from utils import get_next_occurrence  # Use absolute import
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

def get_db_connection():
    conn = psycopg2.connect(
        host="5.161.76.86",
        port=5432,
        user="postgres",
        password="Extreme123",
        database="icelio"
    )
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            project_id INTEGER REFERENCES projects(id),
            due_date DATE,
            description TEXT,
            completed BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id SERIAL PRIMARY KEY,
            project_id INTEGER REFERENCES projects(id),
            amount NUMERIC(10,2) NOT NULL,
            date DATE,
            recurrence BOOLEAN DEFAULT FALSE,
            recurrence_day INTEGER,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS exits (
            id SERIAL PRIMARY KEY,
            project_id INTEGER REFERENCES projects(id),
            amount NUMERIC(10,2) NOT NULL,
            date DATE,
            recurrence BOOLEAN DEFAULT FALSE,
            recurrence_day INTEGER,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            project_id INTEGER REFERENCES projects(id),
            project_name VARCHAR(100) NOT NULL,
            amount NUMERIC(10,2) NOT NULL,
            date DATE,
            type VARCHAR(10) NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

def add_project(name):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO projects (name) VALUES (%s) RETURNING id", (name,))
    project_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return project_id

def add_task(name, project_id, due_date, description):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO tasks (name, project_id, due_date, description) VALUES (%s, %s, %s, %s) RETURNING id", (name, project_id, due_date, description))
    task_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return task_id

def add_entry(project_id, amount, date, recurrence, recurrence_day):
    conn = get_db_connection()
    cur = conn.cursor()
    if recurrence:
        date = get_next_occurrence(recurrence_day).strftime('%Y-%m-%d')
    cur.execute("INSERT INTO entries (project_id, amount, date, recurrence, recurrence_day) VALUES (%s, %s, %s, %s, %s) RETURNING id", (project_id, amount, date, recurrence, recurrence_day))
    entry_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return entry_id

def add_exit(project_id, amount, date, recurrence, recurrence_day):
    conn = get_db_connection()
    cur = conn.cursor()
    if recurrence:
        date = get_next_occurrence(recurrence_day).strftime('%Y-%m-%d')
    cur.execute("INSERT INTO exits (project_id, amount, date, recurrence, recurrence_day) VALUES (%s, %s, %s, %s, %s) RETURNING id", (project_id, amount, date, recurrence, recurrence_day))
    exit_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return exit_id

def add_transaction(project_id, project_name, amount, date, type):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO transactions (project_id, project_name, amount, date, type) VALUES (%s, %s, %s, %s, %s)", (project_id, project_name, amount, date, type))
    conn.commit()
    cur.close()
    conn.close()

def update_task_status(task_id, completed):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE tasks SET completed = %s WHERE id = %s", (completed, task_id))
    conn.commit()
    cur.close()
    conn.close()

def delete_task(task_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
    conn.commit()
    cur.close()
    conn.close()

def delete_entry(entry_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM entries WHERE id = %s", (entry_id,))
    conn.commit()
    cur.close()
    conn.close()

def delete_exit(exit_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM exits WHERE id = %s", (exit_id,))
    conn.commit()
    cur.close()
    conn.close()

def calculate_percentage_change(current_value, previous_value):
    if previous_value == 0:
        return 100 if current_value > 0 else 0
    return ((current_value - previous_value) / previous_value) * 100

def get_comparison_dates(start_date, end_date):
    if not start_date or not end_date:
        return None, None
    
    start = datetime.strptime(start_date.split()[0], '%Y-%m-%d')
    end = datetime.strptime(end_date.split()[0], '%Y-%m-%d')
    delta = (end - start).days + 1

    if delta == 1:  # Today or specific day
        prev_start = (start - timedelta(days=1)).strftime('%Y-%m-%d 00:00:00')
        prev_end = (start - timedelta(days=1)).strftime('%Y-%m-%d 23:59:59')
    elif delta == 7:  # 7 days
        prev_start = (start - timedelta(days=7)).strftime('%Y-%m-%d 00:00:00')
        prev_end = (start - timedelta(days=1)).strftime('%Y-%m-%d 23:59:59')
    else:  # Month or custom range
        prev_start = (start - relativedelta(months=1)).strftime('%Y-%m-%d 00:00:00')
        prev_end = (end - relativedelta(months=1)).strftime('%Y-%m-%d 23:59:59')
    
    return prev_start, prev_end

def get_dashboard_data(start_date=None, end_date=None, project_id=None):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get previous period dates for comparison
    prev_start, prev_end = get_comparison_dates(start_date, end_date)
    
    # Base filters
    current_filters = ["type = 'entry'"]
    prev_filters = ["type = 'entry'"]
    
    if start_date:
        current_filters.append(f"created_at >= '{start_date}'")
    if end_date:
        current_filters.append(f"created_at <= '{end_date}'")
    if project_id:
        current_filters.append(f"project_id = {project_id}")
        prev_filters.append(f"project_id = {project_id}")
    
    if prev_start and prev_end:
        prev_filters.extend([
            f"created_at >= '{prev_start}'",
            f"created_at <= '{prev_end}'"
        ])
    
    current_filter_query = " AND ".join(current_filters)
    prev_filter_query = " AND ".join(prev_filters)
    
    # Current period calculations
    cur.execute(f"SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE {current_filter_query}")
    faturamento = cur.fetchone()[0] or 0
    
    # Update exit query
    current_filters[0] = "type = 'exit'"
    current_filter_query = " AND ".join(current_filters)
    cur.execute(f"SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE {current_filter_query}")
    gastos = cur.fetchone()[0] or 0
    
    # Update back to entry for count
    current_filters[0] = "type = 'entry'"
    current_filter_query = " AND ".join(current_filters)
    cur.execute(f"SELECT COUNT(*) FROM transactions WHERE {current_filter_query}")
    total_vendas = cur.fetchone()[0] or 0
    
    # Previous period calculations
    cur.execute(f"SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE {prev_filter_query}")
    prev_faturamento = cur.fetchone()[0] or 0
    
    prev_filters[0] = "type = 'exit'"
    prev_filter_query = " AND ".join(prev_filters)
    cur.execute(f"SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE {prev_filter_query}")
    prev_gastos = cur.fetchone()[0] or 0
    
    prev_filters[0] = "type = 'entry'"
    prev_filter_query = " AND ".join(prev_filters)
    cur.execute(f"SELECT COUNT(*) FROM transactions WHERE {prev_filter_query}")
    prev_total_vendas = cur.fetchone()[0] or 0
    
    # Calculate percentages
    faturamento_change = calculate_percentage_change(faturamento, prev_faturamento)
    gastos_change = calculate_percentage_change(gastos, prev_gastos)
    vendas_change = calculate_percentage_change(total_vendas, prev_total_vendas)
    
    # Calculate lucro for both periods
    lucro = faturamento - gastos
    prev_lucro = prev_faturamento - prev_gastos
    lucro_change = calculate_percentage_change(lucro, prev_lucro)
    
    # Faturamento por Dia - fix the query
    revenue_query_filters = []
    if start_date:
        revenue_query_filters.append(f"created_at >= '{start_date}'")
    if end_date:
        revenue_query_filters.append(f"created_at <= '{end_date}'")
    if project_id:
        revenue_query_filters.append(f"project_id = {project_id}")
    
    revenue_where_clause = "WHERE type = 'entry'"
    if revenue_query_filters:
        revenue_where_clause += " AND " + " AND ".join(revenue_query_filters)
    
    cur.execute(f"""
        SELECT DATE(created_at), SUM(amount) 
        FROM transactions 
        {revenue_where_clause}
        GROUP BY DATE(created_at) 
        ORDER BY DATE(created_at)
    """)
    revenue_data = cur.fetchall()
    
    # Ranking de Produtos - use the same where clause
    cur.execute(f"""
        SELECT project_name, COUNT(*) as vendas, SUM(amount) as faturamento 
        FROM transactions 
        {revenue_where_clause}
        GROUP BY project_name 
        ORDER BY faturamento DESC
    """)
    ranking_produtos = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return {
        'faturamento': faturamento,
        'gastos': gastos,
        'lucro': lucro,
        'total_vendas': total_vendas,
        'faturamento_change': faturamento_change,
        'gastos_change': gastos_change,
        'lucro_change': lucro_change,
        'vendas_change': vendas_change,
        'revenue_data': revenue_data,
        'ranking_produtos': ranking_produtos
    }
