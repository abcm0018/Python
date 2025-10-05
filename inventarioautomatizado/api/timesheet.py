from datetime import datetime, timedelta
from config.db import get_connection  

def get_shift_for_time(time, shifts):
    """
    Determina a qué turno pertenece una hora concreta.
    :param time: objeto datetime.time
    :param shifts: lista de turnos [(id, shift_type, start_time, end_time), ...]
    :return: shift_id
    """
    for shift_id, shift_type, start_time, end_time in shifts:
        # Convertir timedelta a time si es necesario
        if isinstance(start_time, timedelta):
            start_time = (datetime.min + start_time).time()
        if isinstance(end_time, timedelta):
            end_time = (datetime.min + end_time).time()
        if start_time < end_time:
            # Turno normal (ej: 06:00 - 14:00, 14:00 - 22:00)
            if start_time <= time < end_time:
                return shift_id
        else:
            # Turno nocturno (ej: 22:00 - 06:00)
            if time >= start_time or time < end_time:
                return shift_id
    return None


def save_signing(employee_number, name):
    conn = get_connection()
    cursor = conn.cursor()

    now = datetime.now()
    today = now.date()

    # Obtenemos todos los turnos
    cursor.execute("SELECT id, shift_type, start_time, end_time FROM shift")
    shifts = cursor.fetchall()

    # Determinamos el turno según la hora actual
    current_shift_id = get_shift_for_time(now.time(), shifts)

    # Buscar el workshift_id exacto para ese turno y ese usuario
    cursor.execute("""
        SELECT w.id
        FROM workshift w
        JOIN `user` u ON u.id = w.user_id
        WHERE u.employee_number = %s AND w.date = %s AND w.shift_id = %s
        LIMIT 1
    """, (employee_number, today, current_shift_id))
    row = cursor.fetchone()
    workshift_id = row[0] if row else None

    # Guardamos entrada con shift_id y workshift_id
    sql = """
        INSERT INTO timesheet (name, check_in_at, employee_number, shift_id, workshift_id)
        VALUES (%s, %s, %s, %s, %s)
    """
    values = (name, now, employee_number, current_shift_id, workshift_id)

    cursor.execute(sql, values)
    conn.commit()

    cursor.close()
    conn.close()


def save_check_out(employee_number: str):
    conn = get_connection()
    cursor = conn.cursor()

    now = datetime.now()

    # Obtenemos el último registro del usuario
    cursor.execute("""
        SELECT id, check_in_at, workshift_id 
        FROM timesheet
        WHERE employee_number = %s AND check_out_at IS NULL 
        ORDER BY id DESC
        LIMIT 1
    """, (employee_number,))
    last_record = cursor.fetchone()

    if not last_record:
        print("⚠️ No hay fichaje abierto para este empleado")
        cursor.close()
        conn.close()
        return

    timesheet_id, check_in_at, workshift_id = last_record
    check_out_at = now

    # Obtenemos todos los turnos
    cursor.execute("SELECT id, shift_type, start_time, end_time FROM shift")
    shifts = cursor.fetchall()

    # Determinamos el turno de entrada y salida
    check_in_shift = get_shift_for_time(check_in_at.time(), shifts)
    check_out_shift = get_shift_for_time(check_out_at.time(), shifts)

    def get_workshift_id(employee_number, date, shift_id):
        cursor.execute("""
            SELECT w.id
            FROM workshift w
            JOIN `user` u ON u.id = w.user_id
            WHERE u.employee_number = %s AND w.date = %s AND w.shift_id = %s
            LIMIT 1
        """, (employee_number, date, shift_id))
        row = cursor.fetchone()
        return row[0] if row else None

    if check_in_shift == check_out_shift:
        # ✅ Caso mismo turno: actualizamos el registro existente
        correct_workshift_id = get_workshift_id(employee_number, check_in_at.date(), check_in_shift)

        sql = """
            UPDATE timesheet
            SET check_out_at = %s, shift_id = %s, workshift_id = %s
            WHERE id = %s
        """
        values = (check_out_at, check_in_shift, correct_workshift_id, timesheet_id)
        cursor.execute(sql, values)

    else:
        # ⚠️ Caso cruzar de turno (ej: entra de noche y sale por la mañana)
        cursor.execute("SELECT end_time FROM shift WHERE id = %s", (check_in_shift,))
        shift_end_time = cursor.fetchone()[0]

        if shift_end_time > check_in_at.time():
            shift_end_datetime = datetime.combine(check_in_at.date(), shift_end_time)
        else:
            shift_end_datetime = datetime.combine(check_in_at.date(), shift_end_time) + timedelta(days=1)   

        # Cerrar el primer registro con su workshift real
        correct_workshift_id_in = get_workshift_id(employee_number, check_in_at.date(), check_in_shift)

        cursor.execute("""
            UPDATE timesheet
            SET check_out_at = %s, shift_id = %s, workshift_id = %s
            WHERE id = %s
        """, (shift_end_datetime, check_in_shift, correct_workshift_id_in, timesheet_id))

        # Crear nuevo registro con el workshift real del turno de salida
        correct_workshift_id_out = get_workshift_id(employee_number, check_out_at.date(), check_out_shift)

        sql = """
            INSERT INTO timesheet (employee_number, check_in_at, check_out_at, shift_id, workshift_id)
            VALUES (%s, %s, %s, %s, %s)
        """
        values = (employee_number, shift_end_datetime, check_out_at, check_out_shift, correct_workshift_id_out)
        cursor.execute(sql, values)

    conn.commit()
    cursor.close()
    conn.close()