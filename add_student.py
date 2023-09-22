
from flask import Flask, render_template,redirect, url_for, request
from pymysql import connections
import os
import boto3
from config import *
from uuid import uuid4
import json
from flask import jsonify
from pymysql import MySQLError
import traceback
from datetime import datetime



app = Flask(__name__)

bucket = "yewshuhan-bucket"
region = customregion

db_conn = connections.Connection(
    host=customhost,
    port=3306,
    user=customuser,
    password=custompass,
    db=customdb

)
output = {}
table = 'studentForm'

s3 = boto3.resource('s3')
s3_client = boto3.client('s3')
bucket_location = boto3.client('s3').get_bucket_location(Bucket="yewshuhan-bucket")
s3_location = (bucket_location['LocationConstraint'])

if s3_location is None:
    s3_location = ''
else:
    s3_location = '-' + s3_location

@app.route("/", methods=['GET'])
def home():
    return redirect(url_for('profile', student_id=1))

@app.route("/company-list.html", methods=['GET', 'POST'])
def viewCompanyList():
    return render_template('company-list.html')
@app.route("/edit-profile.html", methods=['GET','POST'])
def edit_profile_view():
    return render_template('edit-profile.html')



@app.route("/addStudent", methods=['POST'])
def Addstudent():
    
    # Retrieve form fields
    student_id = request.form.get("student-id")
    file_url = request.files.get("resume")
    company_id = request.form.get("company-id")
    file_id = str(uuid4())
    application_id = str(uuid4())

    
    # Check if resume file is provided
    if not file_url or file_url.filename == "":
        return "Please upload your resume."

    # Generate a unique name for the resume (using student_id and current timestamp for uniqueness)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    resume_file_name_in_s3 = f"resume_{student_id}_{timestamp}.pdf"

    try:
        # Upload resume to S3
        s3.Bucket("yewshuhan-bucket").put_object(Key=resume_file_name_in_s3, Body=file_url, ContentDisposition=f"attachment; filename={file_url.filename}")
        
        # Construct the S3 URL for the uploaded resume
        file_url = f"https://s3{s3_location}.amazonaws.com/{custombucket}/{resume_file_name_in_s3}"
        
        # Your SQL to insert data into studentForm
        insert_sql = "INSERT INTO application (student_id, company_id) VALUES (%s, %s)"
        insert_sql_application_file = "INSERT INTO applicationFile (file_id, application_id) VALUES (%s, %s)"
        insert_sql_file = "INSERT INTO applicationFile (file_id, file_url) VALUES (%s, %s)"


        cursor = db_conn.cursor()
        cursor.execute(insert_sql, (student_id, company_id))
        cursor.execute(insert_sql_application_file, (file_id, application_id))
        cursor.execute(insert_sql_file, (file_id, file_url))
        db_conn.commit()
        print("Student and resume added successfully!")
        return redirect(url_for('home'))
    except MySQLError as e:
        print(f"Error while inserting into the database: {e}")
        return jsonify(status="error", message=str(e)), 500
    except Exception as e:  # Generic exception for other errors, like S3 upload
        print(f"Error: {e}")
        return str(e)
    finally:
        cursor.close()

@app.route("/viewcompanies", methods=['GET'])
def view_companies():
    try:
        # Retrieve company data from the database
        cursor = db_conn.cursor()
        select_sql = "SELECT company_name,contact_number,email, industry FROM company"
        cursor.execute(select_sql)
        company_data = cursor.fetchall()
        cursor.close()

        # Create a list to store the company details
        companies = []

        # Loop through the retrieved data and fetch S3 URLs for logos
        for company in company_data:
            company_name,contact_number,email, industry = company
            # Assuming you have a naming convention for the logo files
            
            companies.append({'company_name': company_name,'contact_number': contact_number,'email':email, 'industry': industry})

        return jsonify(companies)
    except Exception as e:
        return str(e)
@app.route("/internship-form/<student_id>", methods=['GET'])
def internship_form(student_id):
    try:
        # Set up a cursor for database interaction
        cursor = db_conn.cursor()

        # Retrieve student data from the database for a specific student_id
        select_sql = "SELECT student_id, name, programme, email FROM studentDetails WHERE student_id = %s"
        cursor.execute(select_sql, (student_id,))
        student = cursor.fetchone()

        if not student:
            cursor.close()
            return "Student not found", 404

        student_id, name, programme, email = student
        student_details = {
            'student-id': student_id,
            'student-name': name,
            'programme': programme,
            'email': email
        }

        # Fetch list of companies
        cursor.execute("SELECT company_id, company_name FROM company")

        companies = cursor.fetchall()

        cursor.close()

        return render_template("internship-form.html", student=student_details, companies=companies)
    except Exception as e:
        return str(e), 500

    
@app.route("/profile/<student_id>", methods=['GET'])
def profile(student_id):
    try:
        cursor = db_conn.cursor()

        # Retrieve student data based on student_id
        cursor.execute("SELECT * FROM studentDetails WHERE student_id=%s", (student_id,))

        student = cursor.fetchone()
        cursor.close()
        print(student)
        if student:
            # Extract details from the tuple
            student_id, name, email, programme, cohort = student

            # Pass the student details to the profile template
            return render_template('profile.html', student_id=student_id, name=name, email=email, programme=programme, cohort=cohort)
        else:
            return "Student not found", 404
   

    except Exception as e:
        print(e)
        return "Error occurred while fetching student details", 500
    
@app.route("/edit-profile/<student_id>", methods=['GET', 'POST'])
def edit_profile(student_id):
    try:
        if request.method == 'POST':
            # Handle form submission here
            name = request.form.get('name')
            email = request.form.get('email')
            programme = request.form.get('programme')
            cohort = request.form.get('cohort')
            
            # Update the student data in the database
            update_sql = """
                UPDATE studentDetails
                SET name=%s, email=%s, programme=%s, cohort=%s
                WHERE student_id=%s
            """
            
            with db_conn.cursor() as cursor:
                cursor.execute(update_sql, (name, email, programme, cohort, student_id))
                db_conn.commit()

            # Redirect back to the profile view after successful update
            return redirect(url_for('profile', student_id=student_id))
        
        else:
            # Handle GET request - this is for displaying the form
            with db_conn.cursor() as cursor:
                cursor.execute("SELECT student_id, name, email, programme, cohort FROM studentDetails WHERE student_id=%s", (student_id,))
                print(f"Attempting to fetch data for student_id: {student_id}")
                student = cursor.fetchone()
                print(f"Queried student: {student}")

            if student:
                student_dict = {
                                 'student_id': student[0],
                                 'name': student[1],
                                 'email': student[2],
                                 'programme': student[3],
                                 'cohort': student[4]
                                }
                return render_template('edit-profile.html', student=student_dict)
            else:
                return "Student not found", 404
    
    except MySQLError as e:
        print(f"Database Error: {e}")
        return "Database error occurred", 500
    
    except Exception as e:
        print("Exception occurred:", e)
        traceback.print_exc()
        return "Error occurred while fetching student details", 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)

