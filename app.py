import calendar
from sched import scheduler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response, jsonify
import mysql.connector
import logging
import pywhatkit as kit
from decimal import Decimal
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
from datetime import datetime, date, timedelta

app = Flask(__name__)
app.secret_key = 'myS3cr3tK3y@1#2$3'
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Ajay@123',
    'database': 'miniproject',
}

# Create a MySQL connection
mysql_connection = mysql.connector.connect(**db_config)

# Create a cursor object for executing queries
cursor = mysql_connection.cursor()


# Routes
@app.route('/')
def home():
    return render_template('home.html')


@app.route('/user', methods=['GET', 'POST'])
def user():
    if request.method == 'POST':
        user_type = request.form['user_type']
        if user_type == 'student':
            return redirect('/login/student')
        elif user_type == 'faculty':
            return redirect('/login/faculty')
        elif user_type == 'admin':
            # Add logic to handle admin login if needed
            pass
        else:
            # Handle invalid user_type selection
            flash('Invalid user type selected', 'error')
    return render_template('user.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/signup/student', methods=['GET', 'POST'])
def student_signup():
    if request.method == 'POST':
        # Get the form data
        name = request.form['name']
        username = request.form['username']
        password = request.form['password']
        branch = request.form['branch']
        year = request.form['year']
        semester = request.form['semester']
        section = request.form['section']
        rollno = request.form['rollno']
        mobile = request.form['mobileno']

        # Check if the username is already taken (you may want to add additional checks)
        cursor.execute("SELECT username FROM students WHERE username=%s", (username,))
        existing_student = cursor.fetchone()

        if existing_student:
            message = "Username already taken. Please choose a different one."
            return render_template('student_signup.html', message=message)

        # Insert the student details into the database
        cursor.execute("INSERT INTO students (name, username, password, branch, year, semester, section, rollno, "
                       "mobile) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                       (name, username, password, branch, year, semester, section, rollno, mobile))
        mysql_connection.commit()

        # Redirect to the student login page after successful signup
        return redirect('/login/student')

    return render_template('student_signup.html', message='')


@app.route('/signup/faculty', methods=['GET', 'POST'])
def faculty_signup():
    if request.method == 'POST':
        # Get the form data
        username = request.form['username']
        password = request.form['password']
        fullname = request.form['fullname']
        mobile = request.form['mobileno']

        # Check if the username is already taken (you may want to add additional checks)
        cursor.execute("SELECT username FROM faculty WHERE username=%s", (username,))
        existing_faculty = cursor.fetchone()

        if existing_faculty:
            message = "Username already taken. Please choose a different one."
            return render_template('faculty_signup.html', message=message)

        # Insert the faculty details into the database
        cursor.execute("INSERT INTO faculty (username, password, fullname, mobile) VALUES (%s, %s, %s, %s)",
                       (username, password, fullname, mobile))
        mysql_connection.commit()

        # Redirect to the faculty login page after successful signup
        return redirect('/login/faculty')

    return render_template('faculty_signup.html', message='')


@app.route('/login/student', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check credentials in the database for students
        cursor.execute("SELECT username, password FROM students WHERE username=%s", (username,))
        student = cursor.fetchone()

        if student and student[1] == password:
            # Redirect to student dashboard upon successful login
            session['user_type'] = 'student'
            session['username'] = username
            return redirect('/student_dashboard')
        else:
            message = "Wrong credentials. Please try again."
            return render_template('student_login.html', message=message)
    return render_template('student_login.html', message='')


@app.route('/login/faculty', methods=['GET', 'POST'])
def faculty_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check credentials in the database for faculty
        cursor.execute("SELECT username, password FROM faculty WHERE username=%s", (username,))
        faculty = cursor.fetchone()

        if faculty and faculty[1] == password:
            # Set user_type to 'faculty' upon successful login
            session['user_type'] = 'faculty'
            session['username'] = username
            return redirect('/faculty_dashboard')
        else:
            message = "Wrong credentials. Please try again."
            return render_template('faculty_login.html', message=message)
    return render_template('faculty_login.html', message='')


@app.route('/student_dashboard')
def student_dashboard():
    # Check if the user is logged in and is of type 'student'
    if 'username' in session and session.get('user_type') == 'student':
        username = session['username']

        # Fetch student details from the database based on the username
        query = "SELECT name, rollno, branch, year, semester, section, mobile FROM students WHERE username = %s"
        cursor.execute(query, (username,))
        student = cursor.fetchone()
        if student:
            student_name, rollno, branch, year, semester, section, student_mobile = student

            # Calculate overall attendance
            query = "SELECT COUNT(*) FROM attendance WHERE rollno = %s AND status = %s"
            cursor.execute(query, (rollno, "p"))
            total_attended = cursor.fetchone()[0]

            query = "SELECT COUNT(*) FROM attendance WHERE rollno = %s"
            cursor.execute(query, (rollno,))
            total_classes = cursor.fetchone()[0]

            overall_attendance = (total_attended / total_classes) * 100 if total_classes > 0 else 0

            # Calculate cumulative attendance
            today = date.today()
            if today.day <= 15:
                start_day, end_day = 1, 15
            else:
                end_day = calendar.monthrange(today.year, today.month)[1]
                start_day = 16

            query = "SELECT COUNT(*) FROM attendance WHERE rollno = %s AND status = %s AND date BETWEEN %s AND %s"
            cursor.execute(query, (
                rollno, "p", f"{today.year}-{today.month:02d}-{start_day}",
                f"{today.year}-{today.month:02d}-{end_day}"))
            attended_last_15_days = cursor.fetchone()[0]

            query = "SELECT COUNT(*) FROM attendance WHERE rollno = %s AND date BETWEEN %s AND %s"
            cursor.execute(query, (
                rollno, f"{today.year}-{today.month:02d}-{start_day}", f"{today.year}-{today.month:02d}-{end_day}"))
            total_last_15_days = cursor.fetchone()[0]

            cumulative_attendance = (attended_last_15_days / total_last_15_days) * 100 if total_last_15_days > 0 else 0

            # Check if today is the 1st day of the month or the 16th day of the month
            if today.day == 1 or today.day == 16:
                # Check cumulative attendance and send WhatsApp message if needed
                if cumulative_attendance <= 65:
                    message = f"attendance alert ----------------------\nYour cumulative attendance is less than 65%. " \
                              f"If you continue the same, you will be detained for writing end semester exams. So, " \
                              f"kindly attend the classes and improve your attendance and do well in the " \
                              f"exams.\n-with regards from college management "
                    # Send the WhatsApp message using the student's mobile number
                    student_mobile = "+91" + student_mobile
                    # kit.sendwhatmsg(student_mobile, message, 21, 37)

            return render_template('student_dashboard.html', student_name=student_name, rollno=rollno,
                                   branch=branch, year=year, semester=semester, section=section, username=username,
                                   overall_attendance=overall_attendance, cumulative_attendance=cumulative_attendance)

    # Redirect to the appropriate login page if not logged in as a student
    return redirect(url_for('student_login'))


# Route for the faculty dashboard
@app.route('/faculty_dashboard')
def faculty_dashboard():
    # Check if the user is logged in and is of type 'faculty'
    if 'username' in session and session.get('user_type') == 'faculty':
        username = session['username']

        # Fetch faculty details from the database based on the username
        query = "SELECT fullname, mobile FROM faculty WHERE username = %s"
        cursor.execute(query, (username,))
        faculty = cursor.fetchone()

        if faculty:
            faculty_name, faculty_mobile = faculty

            # Store the faculty_mobile number in the session
            session['faculty_mobile'] = faculty_mobile

            # Add additional logic to fetch faculty-specific data if needed

            return render_template('faculty_dashboard.html', faculty_name=faculty_name)

    # Redirect to the appropriate login page if not logged in as a faculty
    return redirect(url_for('faculty_login'))


@app.route('/mark_attendance', methods=['GET', 'POST'])
def mark_attendance():
    if request.method == 'POST':
        faculty_name = request.args.get('faculty_name')
        branch = request.form['branch']
        year = request.form['year']
        semester = request.form['semester']
        section = request.form['section']

        # Store these values in the session
        session['branch'] = branch
        session['year'] = year
        session['semester'] = semester
        session['section'] = section

        # Redirect to student_list with selected parameters
        return redirect(url_for('student_list', faculty_name=faculty_name))

    return render_template('mark_attendance.html')


@app.route('/student_list', methods=['GET', 'POST'])
def student_list():
    # Retrieve the stored values from the session
    branch = request.form['branch']
    year = request.form['year']
    semester = request.form['semester']
    section = request.form['section']

    # Fetch students based on the stored parameters
    query = "SELECT rollno, name FROM students WHERE branch = %s AND year = %s AND semester = %s AND section = %s"
    cursor.execute(query, (branch, year, semester, section))
    students = cursor.fetchall()
    students.sort()
    print(students)
    print(f"Debug: Branch={branch}, Year={year}, Semester={semester}, Section={section}")
    # Pass the students and other values to the template

    if 'username' in session and session.get('user_type') == 'faculty':
        username = session['username']

        # Fetch faculty details from the database based on the username
        query = "SELECT fullname, mobile FROM faculty WHERE username = %s"
        cursor.execute(query, (username,))
        faculty = cursor.fetchone()

        if faculty:
            faculty_name, faculty_mobile = faculty

            # Store the faculty_mobile number in the session
            session['faculty_mobile'] = faculty_mobile

    return render_template('student_list.html', students=students, branch=branch, year=year, semester=semester,
                           section=section, faculty_name=faculty_name)


# ...

# Route to process and save attendance
@app.route('/process_attendance', methods=['POST'])
def process_attendance():
    if request.method == 'POST':
        # Get the date, course, and faculty mobile number
        date = request.form['date']
        course = request.form['course']
        faculty_username = session.get('username')  # Assuming you have faculty username in the session

        # Fetch the faculty's mobile number from the database
        cursor.execute("SELECT mobile FROM faculty WHERE username = %s", (faculty_username,))
        faculty_mobile = "+91" + cursor.fetchone()[0]  # Assuming mobile is in the first column
        cursor.execute("SELECT fullname FROM faculty WHERE username = %s", (faculty_username,))
        faculty_name = cursor.fetchone()[0]

        # Process the attendance data and insert/update the attendance table
        attendance_data = []
        for key, value in request.form.items():
            if key.startswith('status_'):
                rollno = key.split('_')[1]
                status = value

                # Retrieve the year, semester, and section of the student
                cursor.execute("SELECT name, year, semester, section FROM students WHERE rollno = %s", (rollno,))
                name, year, semester, section = cursor.fetchone()

                # Check if there is an existing attendance record for this student, date, and course
                cursor.execute("SELECT * FROM attendance WHERE rollno = %s AND date = %s AND course = %s",
                               (rollno, date, course))
                existing_record = cursor.fetchone()

                if existing_record:
                    # Update the existing attendance record
                    cursor.execute(
                        "UPDATE attendance SET status = %s WHERE rollno = %s AND date = %s AND course = %s",
                        (status, rollno, date, course))
                else:
                    # Insert a new attendance record with faculty username
                    cursor.execute(
                        "INSERT INTO attendance (rollno, student_name, date, faculty_username, course, year, sem, section,status) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                        (rollno, name, date, faculty_username, course, year, semester, section, status))

                attendance_data.append(
                    {'rollno': rollno, 'name': name, 'section': section, 'status': status, 'year': year,
                     'semester': semester})

        mysql_connection.commit()

        # Send attendance report to faculty mobile number (you can use your preferred method)
        # Here, we'll just print it for demonstration purposes
        print(attendance_data)
        p_Count = 0
        a_Count = 0
        absent_names = []
        for entry in attendance_data:
            if entry['status'] == 'p':
                p_Count += 1
            else:
                a_Count += 1
                absent_names.append(entry['rollno'])
        print(f"Attendance Report for Date: {date}, Course: {course}")
        for entry in attendance_data:
            print(f"Roll No: {entry['rollno']}, Status: {entry['status']}")

        message = f"Attendance Report for Date: {date}, Faculty name: {faculty_name} Course: {course}\n" \
                  f"No of students present : {p_Count}\n" \
                  f"No of students absent  : {a_Count}\n" \
                  f"Roll No of absent students : {', '.join(absent_names)}"

        current_time = datetime.now()
        time_hour = current_time.hour
        time_minute = current_time.minute

        kit.sendwhatmsg(faculty_mobile, message, 14, 2)

        return render_template('attendance_report.html', date=date, course=course, attendance_data=attendance_data,
                               faculty_mobile=faculty_mobile, p_Count=p_Count, a_Count=a_Count,
                               absent_names=absent_names, faculty_username=faculty_username, faculty_name=faculty_name)


ADMIN_USERNAME = "Admin"
ADMIN_PASSWORD = "Admin@gcet"

# Variable to track admin login status
admin_logged_in = False


# Route for the admin login page
@app.route('/login/admin', methods=['GET', 'POST'])
def admin_login():
    global admin_logged_in
    if admin_logged_in:
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            admin_logged_in = True
            return redirect(url_for('admin_dashboard'))

    return render_template('admin_login.html')


# Create a scheduler instance
scheduler = BackgroundScheduler()
# Configure logging
logging.basicConfig(filename='attendance_alerts.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s: %(message)s')


# Function to send attendance alerts
def send_attendance_alerts():
    # Connect to the database and fetch student attendance
    # Replace with your database connection code
    cursor = mysql_connection.cursor()

    # Fetch students
    query = "SELECT name, mobile, rollno FROM students"
    cursor.execute(query)
    students = cursor.fetchall()

    for student in students:
        student_name, student_mobile, rollno = student

        # Calculate the student's attendance percentage
        query = """
        SELECT COUNT(*) AS total_classes, SUM(CASE WHEN status = 'p' THEN 1 ELSE 0 END) AS attended_classes
        FROM attendance
        WHERE rollno = %s
        """
        cursor.execute(query, (rollno,))
        result = cursor.fetchone()

        if result and result[0] > 0:
            total_classes = result[0]
            attended_classes = result[1]
            attendance_percentage = (attended_classes / total_classes) * 100
        else:
            attendance_percentage = 0
        # Log the attendance percentage
        logging.info(f"Student {student_name} (Roll No: {rollno}) has {attendance_percentage:.2f}% attendance.")
        # Check if attendance percentage is less than 65
        if attendance_percentage < 65:
            # Send WhatsApp message to the student using pywhatkit
            message = f"Hello {student_name}, your attendance is {attendance_percentage:.2f}%. Please attend classes regularly."
            student_mobile = "+91" + student_mobile  # Add the country code
            # kit.sendwhatmsg(student_mobile, message, 21, 37)  # Schedule the message

    # Close the database cursor
    cursor.close()


# Schedule the function to run for every 15 days at a specific time (e.g., 9:00 AM)
scheduler.add_job(send_attendance_alerts, CronTrigger(day="1,16", hour=9, minute=0))

# Start the scheduler
scheduler.start()


# Route for the admin dashboard page
@app.route('/admin-dashboard')
def admin_dashboard():
    global admin_logged_in
    if not admin_logged_in:
        return redirect(url_for('admin_login'))

    return render_template('admin_dashboard.html')


@app.route('/add_student', methods=['POST', 'GET'])
def add_student():
    if request.method == 'POST':
        # Get the form data
        name = request.form['name']
        username = request.form['username']
        password = request.form['password']
        branch = request.form['branch']
        year = request.form['year']
        semester = request.form['semester']
        section = request.form['section']
        rollno = request.form['rollno']
        mobile = request.form['mobileno']

        # Check if the username is already taken (you may want to add additional checks)
        cursor.execute("SELECT username FROM students WHERE username=%s", (username,))
        existing_student = cursor.fetchone()

        if existing_student:
            message = "Username already taken. Please choose a different one."
            return render_template('add_student.html', message=message)

        # Insert the student details into the database
        cursor.execute("INSERT INTO students (name, username, password, branch, year, semester, section, rollno, "
                       "mobile) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                       (name, username, password, branch, year, semester, section, rollno, mobile))
        mysql_connection.commit()

        return render_template('student_added.html')  # You can define a success route

    return render_template('add_student.html', message='')


@app.route('/add_faculty', methods=['POST', 'GET'])
def add_faculty():
    if request.method == 'POST':
        # Get the form data
        username = request.form['username']
        password = request.form['password']
        fullname = request.form['fullname']
        mobile = request.form['mobileno']

        # Check if the username is already taken (you may want to add additional checks)
        cursor.execute("SELECT username FROM faculty WHERE username=%s", (username,))
        existing_faculty = cursor.fetchone()

        if existing_faculty:
            message = "Username already taken. Please choose a different one."
            return render_template('add_faculty.html', message=message)

        # Insert the faculty details into the database
        cursor.execute("INSERT INTO faculty (username, password, fullname, mobile) VALUES (%s, %s, %s, %s)",
                       (username, password, fullname, mobile))
        mysql_connection.commit()

        # Display a success message

        return render_template('faculty_added.html')

    return render_template('add_faculty.html', message='')


# Route for the update attendance page
@app.route('/update_attendance', methods=['GET'])
def update_attendance():
    return render_template('update_attendance.html')


# Define a route to display the attendance list page
@app.route('/attendance_list', methods=['GET', 'POST'])
def attendance_list():
    rollno = ''
    date = ''
    attendance_data = []

    if request.method == 'POST':
        rollno = request.form.get('rollno')
        date = request.form.get('date')

        # Fetch attendance records from the database based on rollno and date
        query = "SELECT id, date, faculty_username, course, status FROM attendance WHERE rollno = %s AND date = %s"
        cursor.execute(query, (rollno, date))
        attendance_data = cursor.fetchall()

    return render_template('attendance_list.html', rollno=rollno, date=date, attendance_data=attendance_data)


# Define a route to update attendance status
@app.route('/update_attendance_status', methods=['POST'])
def update_attendance_status():
    record_id = request.form.get('record_id')
    status = request.form.get('status')

    if status in ('p', 'a'):
        # Update the attendance record with the new status
        update_query = "UPDATE attendance SET status = %s WHERE id = %s"
        cursor.execute(update_query, (status, record_id))

        # Commit the update to the database
        mysql_connection.commit()

    return "Success"  # Return a success message


# Route for the update attendance page
@app.route('/get_attendance', methods=['GET'])
def get_attendance():
    return render_template('get_attendance.html')


@app.route('/get_student', methods=['GET', 'POST'])
def student_page():
    return render_template('student.html')


@app.route('/get_attendance_student', methods=['POST'])
def get_attendance_student():
    rollno = request.form['rollno']
    session['rollno'] = rollno
    # Fetch attendance records including faculty names based on rollno from the database
    query = "SELECT A.date, A.faculty_username, A.course, A.status, F.fullname " \
            "FROM attendance A " \
            "INNER JOIN faculty F ON A.faculty_username = F.username " \
            "WHERE A.rollno = %s"
    cursor.execute(query, (rollno,))
    attendance_data = cursor.fetchall()

    # Create a list of dictionaries to store attendance data
    attendance_list = []
    for record in attendance_data:
        date, faculty_username, course, status, faculty_name = record
        attendance_list.append(
            {'date': date.strftime('%Y-%m-%d'), 'faculty_name': faculty_name, 'course': course, 'status': status})

    session['attendance_data'] = attendance_list
    # Return the attendance details as JSON
    return jsonify({'rollno': rollno, 'attendance_data': attendance_list})


# Create a new route to generate PDF data
@app.route('/generate_pdf', methods=['POST', 'GET'])
def generate_pdf():
    # Retrieve the attendance data from the session
    attendance_data = session.get('attendance_data', [])
    rollno = session.get('rollno', '')
    # Create a PDF
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=(800, 600))  # Customize the page size as needed

    # Define the table headers

    title_text = f"Attendance records of student roll {rollno}"
    title_width = p.stringWidth(title_text, "Helvetica-Bold", 12)

    # Calculate the x-coordinate to center the title horizontally
    x = (800 - title_width) / 2

    # Draw the title
    p.drawString(x, 370, title_text)
    table_headers = ["Date", "Faculty Name", "Course", "Status"]

    # Set the font for the headers
    p.setFont("Helvetica-Bold", 12)

    # Draw the headers
    header_text = "Attendance records for student rollno"
    p.drawString(100, 370, header_text)

    # Create a table to display the attendance data
    table_data = [table_headers]

    for record in attendance_data:
        table_data.append([record["date"], record["faculty_name"], record["course"], record["status"]])

    # Create the table
    width, height = 600, 400
    table_height = height - 50
    from reportlab.platypus import Table, TableStyle
    from reportlab.lib import colors

    table = Table(table_data, colWidths=[width / len(table_headers)] * len(table_headers), rowHeights=30)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    # Create the PDF with the table
    table.wrapOn(p, width, table_height)
    table.drawOn(p, 50, table_height)

    # Save the PDF to the buffer
    p.showPage()
    p.save()
    buffer.seek(0)

    # Return the PDF as a response
    return Response(buffer, mimetype='application/pdf')


@app.route('/faculty')
def faculty():
    return render_template('faculty.html')


# Route to get student list based on branch, year, semester, and section
@app.route('/get_student_list', methods=['POST'])
def get_student_list():
    try:
        # Get form data
        branch = request.form.get('branch')
        year = request.form.get('year')
        sem = request.form.get('sem')
        section = request.form.get('section')
        date = request.form.get('date')
        course = request.form.get('course')

        # Fetch student data based on branch, year, sem, and section
        cursor.execute("""
            SELECT rollNo, name FROM students
            WHERE branch = %s AND year = %s AND semester = %s AND section = %s
        """, (branch, year, sem, section))

        student_data = cursor.fetchall()

        # Fetch attendance data based on date and course
        cursor.execute("""
            SELECT rollNo, status FROM attendance
            WHERE date = %s AND course = %s
        """, (date, course))

        attendance_data = cursor.fetchall()

        # Combine student data with attendance data
        student_list = []
        for student in student_data:
            rollNo, name = student
            status = next((status for (rollNo, status) in attendance_data if rollNo == student[0]), None)
            student_list.append({'rollNo': rollNo, 'name': name, 'status': status})

        return jsonify(student_list)

    except Exception as e:
        return jsonify({'error': str(e)})


# Route to get student attendance records
@app.route('/get_student_attendance', methods=['POST'])
def get_student_attendance():
    data = request.json
    rollno = data['rollno']
    date = data['date']
    course = data['course']
    year = data['year']
    semester = data['semester']
    section = data['section']

    # Fetch attendance records for the given student and criteria
    cursor.execute(
        "SELECT date, faculty_name, course, status FROM attendance WHERE rollno=%s AND date=%s AND course=%s AND year=%s AND semester=%s AND section=%s",
        (rollno, date, course, year, semester, section))
    attendance_data = cursor.fetchall()

    return jsonify(attendance_data)


@app.route('/update_faculty_attendance', methods=['GET', 'POST'])
def update_faculty_attendance():
    return render_template('update_faculty_attendance.html')


@app.route('/fetch_attendance_records', methods=['POST'])
def fetch_attendance_records():
    # Get input data from the form
    branch = request.form['branch']
    year = request.form['year']
    semester = request.form['semester']
    section = request.form['section']
    date = request.form['date']
    course = request.form['course']

    # Create a MySQL connection
    mysql_connection = mysql.connector.connect(**db_config)

    # Create a cursor object for executing queries
    cursor = mysql_connection.cursor()

    # Query to fetch attendance records based on input data
    query = """
    SELECT s.rollno, s.name, a.status
    FROM students s
    LEFT JOIN attendance a ON s.rollno = a.rollno
    WHERE s.branch = %s
    AND s.year = %s
    AND s.semester = %s
    AND s.section = %s
    AND a.date = %s
    AND a.course = %s
    """
    cursor.execute(query, (branch, year, semester, section, date, course))

    # Fetch all records
    records = cursor.fetchall()

    # Close the database connection
    mysql_connection.close()

    # Prepare the data for JSON response
    data = []
    for record in records:
        data.append({
            'rollno': record[0],
            'name': record[1],
            'status': record[2] if record[2] else 'N/A',  # Handle NULL values
        })

    sorted_data = sorted(data, key=lambda x: x['rollno'])

    return jsonify(sorted_data)


@app.route('/update_status', methods=['POST'])
def update_status():
    # Get data from the AJAX request
    record_id = request.form['record_id']
    status = request.form['status']

    # Create a MySQL connection
    mysql_connection = mysql.connector.connect(**db_config)

    # Create a cursor object for executing queries
    cursor = mysql_connection.cursor()

    # Update the attendance status in the database
    query = "UPDATE attendance SET status = %s WHERE rollno = %s"
    cursor.execute(query, (status, record_id))

    # Commit the changes
    mysql_connection.commit()

    # Close the database connection
    mysql_connection.close()

    return "OK"


@app.route('/logout')
def logout():
    session.pop('user_type', None)
    session.pop('username', None)
    global admin_logged_in
    admin_logged_in = False
    return redirect('/')


# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)
