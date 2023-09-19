from flask import Flask, render_template, request, redirect, url_for
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
table = 'employee'

@app.route("/", methods=['GET', 'POST'])
def home():
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
    company_file = request.files.get("companyFile")
    company_logo = request.files.get("companyLogo")
    
    # Serialize the positions list to JSON
    positions_json = json.dumps(positions)

    insert_sql = "INSERT INTO company VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
    cursor = db_conn.cursor()

    if company_file.filename == "":
        return "Please upload a company's detail file"
    if company_logo.filename == "":
        return "Please upload a company logo"

    try:
        # Read the file contents
        company_details_file_data = company_file.read()
        company_logo_file_data = company_logo.read()

        cursor.execute(insert_sql, (company_id, company_name, industry, company_desc, location, email, contact_number, positions_json))
        db_conn.commit()
        
        s3 = boto3.resource('s3')
        s3_location = s3.meta.client.get_bucket_location(Bucket=custombucket)['LocationConstraint'] or ''
        
        # Upload company details file
        company_details_file_name_in_s3 = f"company_id-{company_id}_details_file"
        s3.Bucket(custombucket).put_object(Key=company_details_file_name_in_s3, Body=company_details_file_data)
        
        # Upload company logo file
        company_logo_file_name_in_s3 = f"company_id-{company_id}_logo_file"
        s3.Bucket(custombucket).put_object(Key=company_logo_file_name_in_s3, Body=company_logo_file_data)

        # Get URLs for uploaded files
        company_details_url = f"https://s3{s3_location}.amazonaws.com/{custombucket}/{company_details_file_name_in_s3}"
        company_logo_url = f"https://s3{s3_location}.amazonaws.com/{custombucket}/{company_logo_file_name_in_s3}"

    except Exception as e:
        return str(e)

    finally:
        cursor.close()
        print("all modification done...")
    # Redirect to the manage company page with the URLs
    return render_template('AddEmpOutput.html')

@app.route("/managecompany", methods=['GET'])
def manage_company():
    # Retrieve URLs from query parameters
    company_name = request.args.get("company_name")
    company_details_url = request.args.get("company_details_url")
    company_logo_url = request.args.get("company_logo_url")

    return render_template('admin-manage-company.html', name=company_name, details_url=company_details_url, logo_url=company_logo_url)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)
