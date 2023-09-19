from flask import Flask, render_template, request
from pymysql import connections
import os
import boto3
from config import *
from uuid import uuid4
import json


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
    print("all modification done...")
    return render_template('admin-add-company.html')



@app.route("/addcompany", methods=['POST'])
def Addcompany():
    # Retrieve form fields
    company_id = str(uuid4())
    company_name = request.form.get("companyName")
    industry = request.form.get("industry")
    company_desc = request.form.get("companyDesc")
    location = request.form.get("location")
    email = request.form.get("email")
    contact_number = request.form.get("contactNumber")
    positions = request.form.getlist("position[]")
    company_detials_file = request.files.get("companyFile")
    company_logo_file  = request.files.get("companyLogo")
    # Serialize the positions list to JSON
    positions_json = json.dumps(positions)

    insert_sql = "INSERT INTO company VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
    cursor = db_conn.cursor()

    if company_detials_file.filename == "":
        return "Please upload a company's detail file"
    if company_logo_file.filename == "":
        return "Please upload a company logo "

    try:

        cursor.execute(insert_sql, (company_id, company_name, industry, company_desc, location, email, contact_number, positions_json))
        db_conn.commit()
        company_detials_file_name_in_s3 = "company_id-" + str(company_id) + "_details_file"
        company_logo_file_name_in_s3 = "company_id-" + str(company_id) + "_logo_file"
        s3 = boto3.resource('s3')
        try:
            print("Data inserted in MySQL RDS... uploading image to S3...")
            s3.Bucket(custombucket).put_object(Key=company_detials_file_name_in_s3, Body=company_detials_file)
            s3.Bucket(custombucket).put_object(Key=company_logo_file_name_in_s3, Body=company_logo_file)
            bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
            s3_location = (bucket_location['LocationConstraint'])

            if s3_location is None:
                s3_location = ''
            else:
                s3_location = '-' + s3_location

            object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                s3_location,
                custombucket,
                company_detials_file_name_in_s3)

            object_url2 = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                s3_location,
                custombucket,
                company_logo_file_name_in_s3)

        except Exception as e:
            return str(e)

    finally:
        cursor.close()
    # If it's a GET request, simply render the form
    print("all modification done...")
    return render_template('admin-manage-company.html')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)