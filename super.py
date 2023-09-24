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
        print("Student list page accessed")  # Debugging line
        with db_conn.cursor() as cursor:
            select_sql = "SELECT student_id, name, email, programme, cohort FROM studentDetails"
            cursor.execute(select_sql)
            student_data = cursor.fetchall()
            print("SQL executed, data fetched:", student_data)  # Debugging line

        students = []
        for student in student_data:
            student_id, name, email, programme, cohort = student
            students.append({'student_id': student_id, 'name': name, 'email': email, 'programme': programme, 'cohort': cohort})

        print("Returning response")  # Debugging line
        return render_template('supervisor-studentList.html', students=students)
    except Exception as e:
        print("An error occurred:", e)  # Debugging line
        return f"An error occurred: {str(e)}"
    
@app.route("/applications", methods=['GET'])
def applications_page():
    try:
        with db_conn.cursor() as cursor:
            select_sql = """
            SELECT a.student_id, a.company_id, a.status, a.details, 
                   s.programme, c.company_name
            FROM application a
            JOIN studentDetails s ON a.student_id = s.student_id
            JOIN company c ON a.company_id = c.company_id
            """
            cursor.execute(select_sql)
            application_data = cursor.fetchall()
            
            if not application_data:
                print("No data returned from the SQL query.")
            else:
                print(f"SQL Query returned: {application_data}")
                
        applications = []
        for application in application_data:
            student_id, company_id, status, details, programme, company_name = application
            applications.append({
                'student_id': student_id, 
                'company_id': company_id,
                'status': status,
                'details': details,
                'programme': programme, 
                'company_name': company_name
            })
        
        return render_template('supervisor-application.html', student_applications=applications)
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return f"An error occurred: {str(e)}"

@app.route("/approveOrReject", methods=['GET', 'POST'])
def approveOrReject_page():
    try:
        with db_conn.cursor() as cursor:
            select_sql = "SELECT student_id, company_id, status, details FROM application WHERE status='pending'"
            cursor.execute(select_sql)
            application_data = cursor.fetchall()

        applications = []
        for application in application_data:
            student_id, company_id, status, details = application
            applications.append({
                'student_id': student_id, 
                'company_id': company_id,
                'status': status,
                'details': details
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

@app.route("/viewAddCompanyPage", methods=['GET', 'POST'])
def viewAddCompanyPage():
    return render_template('supervisor-application.html')


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

@app.route("/deletecompany/<int:company_id>", methods=['DELETE'])
def delete_company(company_id):
    try:
        cursor = db_conn.cursor()
        delete_sql = "DELETE FROM company WHERE company_id = %s"
        cursor.execute(delete_sql, (company_id,))
        db_conn.commit()
        cursor.close()
        return jsonify({"message": "Company deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)

'''
company_logo_file_name_in_s3 = f"company_id-{company_id}_logo_file"
            # Construct the S3 URL
            s3_location = ''  # Replace with the actual S3 location
            logo_url = f"https://s3{s3_location}.amazonaws.com/{custombucket}/{company_logo_file_name_in_s3}"
'''
    
    
    