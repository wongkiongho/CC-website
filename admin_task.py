import hashlib
from flask import Flask, render_template, redirect, url_for, request
from pymysql import connections
import pymysql
import os
import boto3
from config import *
from uuid import uuid4
import json
from flask import jsonify
import mimetypes

app = Flask(__name__)

bucket = "limjiasheng-bucket"
region = customregion

db_conn = connections.Connection(
    host=customhost,
    port=3306,
    user=customuser,
    password=custompass,
    db=customdb
)

db_config = {
    "host": customhost,
    "user": customuser,
    "password": custompass,
    "db": customdb,
}

output = {}

table = 'studentDetails'
table = 'supervisor'

s3 = boto3.resource('s3')
s3_client = boto3.client('s3')
bucket_location = boto3.client('s3').get_bucket_location(Bucket="limjiasheng-bucket")
s3_location = (bucket_location['LocationConstraint'])

if s3_location is None:
    s3_location = ''
else:
    s3_location = '-' + s3_location

@app.route("/", methods=['GET', 'POST'])
def home():
    return render_template('/admin-add-student.html')

# student profile
@app.route("/profile.html", methods=['GET', 'POST'])
def viewStudentProfilePage():
    return render_template('profile.html')

# add student page
@app.route("/admin-add-student.html", methods=['GET', 'POST'])
def viewAddStudentPage():
    return render_template('admin-add-student.html')

# manage student page
@app.route("/admin-manage-student.html", methods=['GET', 'POST'])
def viewManageStudentPage():
    return render_template('admin-manage-student.html')

# add supervisor page
@app.route("/admin-add-supervisor.html", methods=['GET', 'POST'])
def viewAddSupervisorPage():
    return render_template('admin-add-supervisor.html')

# manage supervisor page
@app.route("/admin-manage-supervisor.html", methods=['GET', 'POST'])
def viewManageSupervisorPage():
    return render_template('admin-manage-supervisor.html')

# admin login page
@app.route("/admin-login.html", methods=['GET', 'POST'])
def viewAdminLoginPage():
    return render_template('admin-login.html')

# student login page
@app.route("/student-login.html", methods=['GET', 'POST'])
def viewStudentLoginPage():
    return render_template('student-login.html')

# supervisor login page
@app.route("/supervisor-login.html", methods=['GET', 'POST'])
def viewSupervisorLoginPage():
    return render_template('supervisor-login.html')

# add student (DONE)
@app.route("/addstudent", methods=['POST'])
def Addstudent():
    # Retrieve form fields
    name = request.form.get("name")
    email = request.form.get("email")
    student_id = request.form.get("student_id")
    password = request.form.get("password")
    
    try:
        insert_sql = "INSERT INTO studentDetails (student_id, name, email, password) VALUES (%s, %s, %s, %s)"
        cursor = db_conn.cursor()
        cursor.execute(insert_sql, (student_id, name, email, password))
        db_conn.commit()

        print("Data inserted in MySQL RDS...")
        return jsonify({"message": "Student information added successfully"}), 200

    except Exception as e:
        print(f"Error: {e}")
        return str(e)
    finally:
        cursor.close()

# view list of students
@app.route("/viewstudents", methods=['GET'])
def view_students():
    try:
        # Retrieve company data from the database
        cursor = db_conn.cursor()
        select_sql = "SELECT student_id, name, email FROM studentDetails"
        cursor.execute(select_sql)
        student_data = cursor.fetchall()
        cursor.close()

        # Create a list to store the company details
        studentList = []

        # Loop through the retrieved data and fetch S3 URLs for logos
        for studentDetails in student_data:
            student_id, name, email = studentDetails
            # Assuming you have a naming convention for the logo files
            
            studentList.append({'student_id': student_id, 'name': name, 'email': email})

        return jsonify(studentList)
    except Exception as e:
        return str(e)

# delete student
@app.route("/deletestudent/<string:student_id>", methods=['DELETE'])
def delete_student(student_id):
    try:
        cursor = db_conn.cursor()
        delete_sql = "DELETE FROM studentDetails WHERE student_id = %s"
        cursor.execute(delete_sql, (student_id,))
        db_conn.commit()
        cursor.close()
        return jsonify({"message": "Student information deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

# verify student login
@app.route("/verifyStudentLogin", methods=['POST'])
def VerifyStudentLogin():
    # Retrieve form fields
    student_id = request.form.get("student_id")
    password = request.form.get("password")

    

    db_conn = None  # Initialize the variable outside the try block

    try:
        # Connect to the database
        db_conn = pymysql.connect(**db_config)
        cursor = db_conn.cursor()

        # Query the database to retrieve the hashed password for the given student_id
        select_sql = "SELECT password FROM studentDetails WHERE student_id = %s"
        cursor.execute(select_sql, (student_id,))
        result = cursor.fetchone()

        if result:
            # Compare the hashed password with the input password
            stored_password = result[0]  # Assuming the password is in the first column
            hashed_input_password = hashlib.sha256(password.encode()).hexdigest()

            if hashed_input_password == stored_password:
                # Passwords match, login successful, navigate to the admin page
                return redirect(url_for('/profile.html'))
            else:
                # Passwords do not match, login failed
                return jsonify({"error": "Invalid credentials"}), 401
        else:
            # Student not found in the database
            return jsonify({"error": "Student not found"}), 404

    except Exception as e:
        print(f"Received student_id: {student_id}")
        print(f"Received password: {password}")
        print(f"Stored hashed password: {stored_password}")
        print(f"Computed hashed password: {hashed_input_password}")
        return jsonify({"error": str(e)}), 500
    finally:
        if db_conn:
            cursor.close()
            db_conn.close()

    
# add supervisor
@app.route("/addsupervisor", methods=['GET'])
def Addsupervisor():
    # Retrieve form fields
    supervisor_id = request.form.get("supervisor_id")
    name = request.form.get("name")
    email = request.form.get("email")
    contact_number = request.form.get("contact_number")
    password = request.form.get("password")

    try:
        insert_sql = "INSERT INTO supervisor (supervisor_id, name, email, contact_number, password) VALUES (%s, %s, %s, %s, %s)"
        cursor = db_conn.cursor()
        cursor.execute(insert_sql, (supervisor_id, name, email, contact_number, password))
        db_conn.commit()

        print("Data inserted in MySQL RDS...")
        # return redirect(url_for('viewAddSupervisorPage'))
        return jsonify({"message": "Student information added successfully"}), 200

    except Exception as e:
        print(f"Error: {e}")
        return str(e)
    finally:
        cursor.close()
    
# view supervisor
@app.route("/viewsupervisors", methods=['GET'])
def view_supervisors():
    try:
        # Retrieve company data from the database
        cursor = db_conn.cursor()
        select_sql = "SELECT supervisor_id, full_name, email FROM supervisor"
        cursor.execute(select_sql)
        supervisor_data = cursor.fetchall()
        cursor.close()

        # Create a list to store the company details
        supervisorList = []

        # Loop through the retrieved data and fetch S3 URLs for logos
        for supervisor in supervisor_data:
            supervisor_id, name, email = supervisor
            # Assuming you have a naming convention for the logo files
            
            supervisorList.append({'supervisor_id': supervisor_id, 'name': name, 'email': email})

        return jsonify(supervisorList)
    except Exception as e:
        return str(e)
    
# delete supervisor
@app.route("/deletesupervisor/<string:supervisor_id>", methods=['DELETE'])
def delete_supervisor(supervisor_id):
    try:
        cursor = db_conn.cursor()
        delete_sql = "DELETE FROM supervisor WHERE supervisor_id = %s"
        cursor.execute(delete_sql, (supervisor_id,))
        db_conn.commit()
        cursor.close()
        return jsonify({"message": "Supervisor information deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# verify supervisor login
@app.route("/verifySupervisorLogin", methods=['POST'])
def VerifySupervisorLogin():
    # Retrieve form fields
    supervisor_id = request.form.get("supervisor_id")
    password = request.form.get("password")

    try:
        # Connect to the database
        db_conn = pymysql.connect(**db_config)
        cursor = db_conn.cursor()

        # Query the database to retrieve the hashed password for the given student_id
        select_sql = "SELECT password FROM supervisor WHERE supervisor_id = %s"
        cursor.execute(select_sql, (supervisor_id,))
        result = cursor.fetchone()

        if result:
            # Compare the hashed password with the input password
            stored_password = result[0]  # Assuming the password is in the first column
            hashed_input_password = hashlib.sha256(password.encode()).hexdigest()

            if hashed_input_password == stored_password:
                # Passwords match, login successful, navigate to student profile
                return redirect(url_for('viewStudentProfilePage')) #OTW
            else:
                # Passwords do not match, login failed
                return jsonify({"error": "Invalid credentials"}), 401
        else:
            # Student not found in the database
            return jsonify({"error": "Student not found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        db_conn.close()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)