from flask import Flask, render_template, redirect, url_for, request
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
table = 'internCompany'

s3 = boto3.resource('s3')
bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
s3_location = (bucket_location['LocationConstraint'])

if s3_location is None:
    s3_location = ''
else:
    s3_location = '-' + s3_location

@app.route("/", methods=['GET', 'POST'])
def home():
    return render_template('admin-manage-company.html')

@app.route("/viewManageCompanyPage", methods=['GET', 'POST'])
def viewManageCompanyPage():
    return render_template('admin-manage-company.html')

@app.route("/viewcompany/<company_id>", methods=['GET'])
def viewCompany(company_id):
    try:
        cursor = db_conn.cursor()
        cursor.execute("SELECT * FROM internCompany WHERE company_id=%s", (company_id,))
        company = cursor.fetchone()
        cursor.close()
        if company:
        # Deserialize the positions JSON before sending to template
            company_positions = json.loads(company['positions_json'])
            
            return render_template('admin-view-company.html', company=company, company_positions=company_positions)
        else:
            return "Company not found", 404
    except Exception as e:
        return str(e)


@app.route("/viewAddCompanyPage", methods=['GET', 'POST'])
def viewAddCompanyPage():
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

    insert_sql = "INSERT INTO internCompany VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    cursor = db_conn.cursor()

    if company_detials_file.filename == "":
        return "Please upload a company's detail file"
    if company_logo_file.filename == "":
        return "Please upload a company logo "

    try:
        print("Data inserted in MySQL RDS... uploading image to S3...")
        
        company_detials_file_name_in_s3 = "company_id-" + str(company_id) + "_details_file"
        company_logo_file_name_in_s3 = "company_id-" + str(company_id) + "_logo_file"
        s3.Bucket(custombucket).put_object(Key=company_detials_file_name_in_s3, Body=company_detials_file)
        s3.Bucket(custombucket).put_object(Key=company_logo_file_name_in_s3, Body=company_logo_file)
        
        logo_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
            s3_location,
            custombucket,
            company_detials_file_name_in_s3)

        file_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
            s3_location,
            custombucket,
            company_logo_file_name_in_s3)

        cursor.execute(insert_sql, (company_id, company_name, industry, company_desc, location, email, contact_number, positions_json, logo_url, file_url))
        db_conn.commit()
    except Exception as e:
        return str(e)
       
    finally:
        cursor.close()
    # If it's a GET request, simply render the form
    print("all modification done...")
    return redirect(url_for('viewManageCompanyPage'))

@app.route("/deletecompany/<string:company_id>", methods=['DELETE'])
def delete_company(company_id):
    try:
        cursor = db_conn.cursor()
        delete_sql = "DELETE FROM internCompany WHERE company_id = %s"
        cursor.execute(delete_sql, (company_id,))
        db_conn.commit()
        cursor.close()
        return jsonify({"message": "Company deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/viewcompanies", methods=['GET'])
def view_companies():
    try:
        # Retrieve company data from the database
        cursor = db_conn.cursor()
        select_sql = "SELECT company_id, company_name, industry FROM company"
        cursor.execute(select_sql)
        company_data = cursor.fetchall()
        cursor.close()

        # Create a list to store the company details
        companies = []

        # Loop through the retrieved data and fetch S3 URLs for logos
        for company in company_data:
            company_id, company_name, industry = company
            # Assuming you have a naming convention for the logo files
            
            companies.append({'company_id': company_id,'company_name': company_name, 'industry': industry})

        return jsonify(companies)
    except Exception as e:
        return str(e)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)

'''
company_logo_file_name_in_s3 = f"company_id-{company_id}_logo_file"
            # Construct the S3 URL
            s3_location = ''  # Replace with the actual S3 location
            logo_url = f"https://s3{s3_location}.amazonaws.com/{custombucket}/{company_logo_file_name_in_s3}"
'''
    
    
    