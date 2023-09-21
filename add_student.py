
from flask import Flask, render_template,redirect, url_for, request
from pymysql import connections
import os
import boto3
from config import *
from uuid import uuid4
import json
from flask import jsonify
from pymysql import MySQLError



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
table = 'studentForm'


@app.route("/", methods=['GET', 'POST'])
def home():
    return render_template('profile.html')


@app.route("/company-list.html", methods=['GET', 'POST'])
def viewCompanyList():
    return render_template('company-list.html')
@app.route("/edit-profile.html", methods=['GET','POST'])
def edit_profile():
    return render_template('edit-profile.html')


@app.route("/internship-form.html", methods=['GET', 'POST'])
def viewInternshipForm():
    cursor = db_conn.cursor()
    select_sql = "SELECT company_name FROM company"
    cursor.execute(select_sql)
    company_data = cursor.fetchall()
    cursor.close()

    return render_template('internship-form.html', companies=company_data)



@app.route("/addStudent", methods=['POST'])
def Addstudent():
    # Retrieve form fields
    student_id = request.form.get("student-id")
    student_name = request.form.get("student-name")
    print("Student ID:", student_id)
    print("Student Name:", student_name)
    student_programme = request.form.get("company")
    student_course = request.form.get("course")
    student_supervisor = request.form.get("supervisor")
   

    insert_sql = "INSERT INTO studentForm (student_id, student_name, student_programme, student_course, student_supervisor) VALUES (%s, %s, %s, %s, %s)"

    cursor = db_conn.cursor()

    try:
        cursor.execute(insert_sql, (student_id, student_name, student_programme, student_course, student_supervisor))
        db_conn.commit()
        print("Student added successfully!")
        return redirect(url_for('home'))
    except MySQLError as e:
        # db_conn.rollback()
        print(f"Error while inserting into the database: {e}")
        return jsonify(status="error", message=str(e)), 500

    finally:
        cursor.close()

@app.route("/insert-dummy-data", methods=['GET'])
def insert_dummy_data():
    try:
        # Insert dummy data into the database
        cursor = db_conn.cursor()
        insert_sql = """INSERT INTO company (company_name, contact_number, email, industry)
                        VALUES (%s, %s, %s, %s)"""
        cursor.execute(insert_sql, ("Dummy Company", "+123456789", "dummy@company.com", "Dummy Industry"))
        db_conn.commit()
        cursor.close()

        return "Dummy data inserted successfully!"
    except Exception as e:
        return str(e)


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
    
@app.route("/insert-student-dummy-data", methods=['GET'])
def insert_student_dummy_data():
    try:
        # Insert dummy data into the studentDetails table
        cursor = db_conn.cursor()
        insert_sql = """INSERT INTO studentDetails (Id, name, email, programme, cohort)
                        VALUES (%s, %s, %s, %s, %s)"""
        cursor.execute(insert_sql, (1, "John Doe", "johndoe@example.com", "RSW3", "2023"))
        db_conn.commit()
        cursor.close()

        return "Dummy student data inserted successfully!"
    except Exception as e:
        return str(e)
    
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)

