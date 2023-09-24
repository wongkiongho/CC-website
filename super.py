from flask import Flask, render_template, request
from pymysql import connections
import os
import boto3
from config import *
from uuid import uuid4
import json
from flask import jsonify



app = Flask(__name__)

bucket = custombucket
region = customregion

db_conn = connections.Connection(
    host=customhost,
    port=3306,
    user=customuser,
    password=custompass,
    db=customdb

)
output = {}
table = 'company'


@app.route("/", methods=['GET', 'POST'])
def home():
    return render_template('supervisor-application.html')

@app.route('/student_list')
def student_list():
    return render_template('supervisor-studentList.html')


@app.route('/application')
def application():
    return render_template('supervisor-application.html')


@app.route('/approve_reject')
def approve_reject():
    return render_template('supervisor-ApproveOrReject.html')


@app.route("/studentlist", methods=['GET'])
def studentList():
    try:
        with db_conn.cursor() as cursor:
            # Fetch all students
            select_students_sql = "SELECT student_id, name, email, programme, cohort FROM studentDetails"
            cursor.execute(select_students_sql)
            student_data = cursor.fetchall()
            
            students = []
            for student in student_data:
                student_id, name, email, programme, cohort = student
                
                # For each student, fetch all corresponding progress reports
                select_reports_sql = """
                SELECT f.file_url, f.file_name 
                FROM studentFile sf 
                JOIN file f ON sf.file_id = f.file_id AND f.file_type = 'ProgressReport'
                WHERE sf.student_id = %s
                """
                cursor.execute(select_reports_sql, (student_id,))
                reports_data = cursor.fetchall()
                
                reports = [{'file_url': url, 'file_name': name} for url, name in reports_data]
                
                students.append({
                    'student_id': student_id,
                    'name': name,
                    'email': email,
                    'programme': programme,
                    'cohort': cohort,
                    'reports': reports
                })

        return render_template('supervisor-studentList.html', students=students)
    except Exception as e:
        return f"An error occurred: {str(e)}"

@app.route("/applications", methods=['GET'])
def applications_page():
    try:
        with db_conn.cursor() as cursor:
            # Start with joining one table first
            select_sql = """
            SELECT a.student_id, a.company_id, a.status, a.details, s.programme
            FROM application a
            JOIN studentDetails s ON a.student_id = s.student_id;
            """
            cursor.execute(select_sql)
            application_data = cursor.fetchall()

        applications = []
        for application in application_data:
            student_id, company_id, status, details, programme = application
            applications.append({
                'student_id': student_id,
                'company_id': company_id,
                'status': status,
                'details': details,
                'programme': programme  
            })

        return render_template('supervisor-application.html', student_applications=applications)
    except Exception as e:
        print("Error: ", str(e))  # print the error to the console
        return f"An error occurred: {str(e)}"

@app.route("/approveOrReject", methods=['GET'])
def approve_or_reject():
    try:
        with db_conn.cursor() as cursor:
            # Example SQL, adjust as necessary
            select_sql = """
            SELECT a.student_id, a.company_id, a.status, a.details, f.file_url
            FROM application a
            LEFT JOIN studentFile sf ON a.student_id = sf.student_id
            LEFT JOIN file f ON sf.file_id = f.file_id
            """
            cursor.execute(select_sql)
            application_data = cursor.fetchall()

        applications = []
        for application in application_data:
            student_id, company_id, status, details, file_url = application
            applications.append({
                'student_id': student_id,
                'company_id': company_id,
                'status': status,
                'details': details,
                'file_url': file_url
            })

        return render_template('supervisor-ApproveOrReject.html', student_applications=applications)
    except Exception as e:
        return f"An error occurred: {str(e)}"

@app.route('/approveApplication', methods=['POST'])
def approve_application():
    try:
        data = request.json
        student_id = data.get('student_id')
        company_id = data.get('company_id')  # Get company_id from the request data
        with db_conn.cursor() as cursor:
            update_sql = "UPDATE application SET status='approved' WHERE student_id=%s AND company_id=%s"
            cursor.execute(update_sql, (student_id, company_id))  # Pass both IDs to the execute method
            db_conn.commit()
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e))


@app.route('/rejectApplication', methods=['POST'])
def reject_application():
    try:
        data = request.json
        student_id = data.get('student_id')
        company_id = data.get('company_id')  # Get company_id from the request data
        with db_conn.cursor() as cursor:
            update_sql = "UPDATE application SET status='rejected' WHERE student_id=%s AND company_id=%s"
            cursor.execute(update_sql, (student_id, company_id))  # Pass both IDs to the execute method
            db_conn.commit()
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e))




if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)

'''
company_logo_file_name_in_s3 = f"company_id-{company_id}_logo_file"
            # Construct the S3 URL
            s3_location = ''  # Replace with the actual S3 location
            logo_url = f"https://s3{s3_location}.amazonaws.com/{custombucket}/{company_logo_file_name_in_s3}"
'''
    
    
    