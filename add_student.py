
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
table = 'student'


@app.route("/", methods=['GET', 'POST'])
def home():
    return render_template('profile.html')

@app.route("/viewCompanyList", methods=['GET', 'POST'])
def viewCompanyList():
    return render_template('company-list.html')

@app.route("/viewInternshipForm", methods=['GET', 'POST'])
def viewInternshipForm():
    return render_template('internship-form.html')


@app.route("/addStudent", methods=['POST'])
def Addstudent():
    # Retrieve form fields
    student_id = request.form.get("student_Id")
    student_name = request.form.get("student_name")
    student_programme = request.form.get("company")
    student_course = request.form.get("course")
    student_supervisor = request.form.get("supervisor")
   

    insert_sql = "INSERT INTO student VALUES (%s, %s, %s, %s, %s)"
    cursor = db_conn.cursor()

     try:
        cursor.execute(insert_sql, (student_id, student_name, student_programme, student_course, student_supervisor))
        db_conn.commit()
        print("Student added successfully!")
        return redirect(url_for('viewCompanyList'))

    except MySQLError as e:
        db_conn.rollback()
        print(f"Error while inserting into the database: {e}")
        return jsonify(status="error", message=str(e)), 500

    finally:
        cursor.close()
