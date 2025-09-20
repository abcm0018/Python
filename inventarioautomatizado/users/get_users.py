from config.db import get_connection

def fetch_all_users():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT name, surname, email, employee_number, job_position, role 
        FROM user
    """)
    users = cursor.fetchall()
    cursor.close()
    conn.close()
    return users
