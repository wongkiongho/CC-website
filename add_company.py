from flask import Flask, render_template, redirect, url_for, request
from pymysql import connections
import os
import boto3
from config import *
from uuid import uuid4
import json
from flask import jsonify
import mimetypes
from urllib.parse import urlparse
from flask import session





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

s3 = boto3.resource('s3')
s3_client = boto3.client('s3')
bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
s3_location = (bucket_location['LocationConstraint'])

if s3_location is None:
    s3_location = ''
else:
    s3_location = '-' + s3_location

@app.route("/", methods=['GET', 'POST'])
def home():
    return render_template('/admin-manage-company.html')

@app.route("/student-login.html", methods=['GET', 'POST'])
def viewStudentLoginPage():
    return render_template('student-login.html')

@app.route("/supervisor-login.html", methods=['GET', 'POST'])
def viewSupervisorLoginPage():
    return render_template('supervisor-login.html')

@app.route("/admin-login.html", methods=['GET', 'POST'])
def viewAdminLoginPage():
    return render_template('admin-login.html')

@app.route("/admin-manage-company.html", methods=['GET', 'POST'])
def viewManageCompanyPage():
    return render_template('admin-manage-company.html')

@app.route("/admin-add-company.html", methods=['GET', 'POST'])
def viewAddCompanyPage():
    return render_template('admin-add-company.html')

app.route("/admin-edit-company.html", methods=['GET', 'POST'])
def viewEditCompanyPage():
    return render_template('admin-edit-company.html')

@app.route("/viewcompany/<company_id>", methods=['GET'])
def viewCompany(company_id):
    try:
        cursor = db_conn.cursor()

        # Get company details
        cursor.execute("SELECT * FROM company WHERE company_id=%s", (company_id,))
        company = cursor.fetchone()

        if not company:
            cursor.close()
            return "Company not found", 404

        # Deserialize the positions JSON
        company_positions = json.loads(company[7])

        # Get related files
        cursor.execute("SELECT f.file_id, f.file_url, f.file_type, f.file_name, f.file_date FROM file f INNER JOIN companyFile cf ON f.file_id = cf.file_id WHERE cf.company_id = %s", (company_id,))
        files = cursor.fetchall()
        
        # Prepare the list of files and identify the company logo
        logo_url = None
        files_list = []
        for file in files:
            if file[2] == "logo":
                logo_url = file[1]
            else:
                files_list.append({
                    "file_url": file[1],
                    "file_name": file[3]
                })

        # Close the database cursor
        cursor.close()

        return render_template(
            'admin-view-company.html', 
            company=company, 
            company_positions=company_positions, 
            files_list=files_list,
            logo_url=logo_url
        )
    except Exception as e:
        return str(e)


@app.route("/editcompany/<company_id>", methods=['GET', 'POST'])
def editCompany(company_id):
    try:
        cursor = db_conn.cursor()

        if request.method == 'GET':
            # Retrieve company data based on company_id
            cursor.execute("SELECT * FROM company WHERE company_id=%s", (company_id,))
            company = cursor.fetchone()

            # Get related files
            cursor.execute("SELECT f.file_id, f.file_url, f.file_type, f.file_name, f.file_date FROM file f INNER JOIN companyFile cf ON f.file_id = cf.file_id WHERE cf.company_id = %s", (company_id,))
            files = cursor.fetchall()
            # Prepare the list of files and identify the company logo
            logo_url = None
            files_list = []
            for file in files:
                if file[2] == "logo":
                    logo_url = file[1]
                else:
                    files_list.append({
                        "file_url": file[1],
                        "file_name": file[3]
                    })

            # Close the database cursor
            cursor.close()

            if company:
                # Pass the company data and associated files to the edit form
                company_positions = json.loads(company[7])
                return render_template('admin-edit-company.html', company=company, company_positions=company_positions, files_list=files_list, logo_url=logo_url)
            else:
                return "Company not found", 404

        elif request.method == 'POST':
            # Retrieve form fields
            company_name = request.form.get("companyName")
            industry = request.form.get("industry")
            company_desc = request.form.get("companyDesc")
            location = request.form.get("location")
            email = request.form.get("email")
            contact_number = request.form.get("contactNumber")
            positions = request.form.getlist("position[]")
            company_files = request.files.getlist("companyFile")
            company_logo_file = request.files.get("companyLogo")

            # Serialize the positions list to JSON
            positions_json = json.dumps(positions)

            # Insert company details into the company table
            update_company_sql = "UPDATE company SET company_name=%s, industry=%s, company_desc=%s, location=%s, email=%s, contact_number=%s, position_json=%s WHERE company_id=%s"
            cursor.execute(update_company_sql, (company_name, industry, company_desc, location, email, contact_number, positions_json, company_id))
            db_conn.commit()

            # Delete previous company files from S3 and database
            cursor.execute("SELECT file_id FROM companyFile WHERE company_id=%s", (company_id,))
            file_ids_to_delete = [row[0] for row in cursor.fetchall()]

            if file_ids_to_delete:
                # Delete files from S3 and database
                cursor.execute("SELECT file_url FROM file WHERE file_id IN %s", (tuple(file_ids_to_delete),))
                urls_to_delete = [row[0] for row in cursor.fetchall()]

                for url in urls_to_delete:
                    parsed_url = urlparse(url)
                    object_key = parsed_url.path.lstrip('/')
                    s3_client.delete_object(Bucket=custombucket, Key=object_key)

                # Delete records from companyFile and file tables
                cursor.execute("DELETE FROM companyFile WHERE company_id=%s", (company_id,))
                cursor.execute("DELETE FROM file WHERE file_id IN %s", (tuple(file_ids_to_delete),))

            # Handle company logo file
            if company_logo_file:
                # Process company logo
                logo_content_type, _ = mimetypes.guess_type(company_logo_file.filename)
                logo_extension = logo_content_type.split("/")[1] if logo_content_type else ""
                company_logo_file_name_in_s3 = f"company_id-{company_id}_logo.{logo_extension}"

                s3.Bucket(custombucket).put_object(
                    Key=company_logo_file_name_in_s3, 
                    Body=company_logo_file, 
                    ContentDisposition=f"attachment; filename={company_logo_file.filename}"
                )
                logo_url = f"https://s3{s3_location}.amazonaws.com/{custombucket}/{company_logo_file_name_in_s3}"
                logo_file_id = str(uuid4())
                cursor.execute("INSERT INTO companyFile (file_id, company_id) VALUES (%s, %s)", (logo_file_id, company_id))
                cursor.execute("INSERT INTO file (file_id, file_url, file_type, file_name, file_date) VALUES (%s, %s, %s, %s, NOW())", (logo_file_id, logo_url, "logo", company_logo_file.filename))
                db_conn.commit()

                # Process company detail files
                for detail_file in company_files:
                    if detail_file.filename != "":
                        details_content_type, _ = mimetypes.guess_type(detail_file.filename)
                        details_extension = details_content_type.split("/")[1] if details_content_type else ""
                        detail_file_name_in_s3 = f"company_id-{company_id}_file.{details_extension}"

                        s3.Bucket(custombucket).put_object(
                            Key=detail_file_name_in_s3, 
                            Body=detail_file, 
                            ContentDisposition=f"attachment; filename={detail_file.filename}"
                        )
                        file_url = f"https://s3{s3_location}.amazonaws.com/{custombucket}/{detail_file_name_in_s3}"
                        file_id = str(uuid4())
                        cursor.execute("INSERT INTO companyFile (file_id, company_id) VALUES (%s, %s)", (file_id, company_id))
                        cursor.execute("INSERT INTO file (file_id, file_url, file_type, file_name, file_date) VALUES (%s, %s, %s, %s, NOW())", (file_id, file_url, "details", detail_file.filename))
                        db_conn.commit()

    except Exception as e:
        return str(e)

    finally:
        cursor.close()

    return render_template('admin-manage-company.html')




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
    company_files = request.files.getlist("companyFile")
    company_logo_file = request.files.get("companyLogo")
    
    # Serialize the positions list to JSON
    positions_json = json.dumps(positions)

    cursor = db_conn.cursor()
    
    if not company_logo_file or company_logo_file.filename == "":
        return "Please upload company logo "
    
    if not company_files:
        return "Please upload information file "
    
    try:
        # Insert company details into the company table
        insert_company_sql = "INSERT INTO company VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(insert_company_sql, (company_id, company_name, industry, company_desc, location, email, contact_number, positions_json))
        db_conn.commit()

        # Process company logo
        logo_content_type, _ = mimetypes.guess_type(company_logo_file.filename)
        logo_extension = logo_content_type.split("/")[1] if logo_content_type else ""
        company_logo_file_name_in_s3 = f"company_id-{company_id}_logo.{logo_extension}"

        s3.Bucket(custombucket).put_object(
            Key=company_logo_file_name_in_s3, 
            Body=company_logo_file, 
            ContentDisposition=f"attachment; filename={company_logo_file.filename}"
        )
        logo_url = f"https://s3{s3_location}.amazonaws.com/{custombucket}/{company_logo_file_name_in_s3}"
        logo_file_id = str(uuid4())
        cursor.execute("INSERT INTO companyFile (file_id, company_id) VALUES (%s, %s)", (logo_file_id, company_id))
        cursor.execute("INSERT INTO file (file_id, file_url, file_type, file_name, file_date) VALUES (%s, %s, %s, %s, NOW())", (logo_file_id, logo_url, "logo", company_logo_file.filename))
        db_conn.commit()

        # Process company detail files
        for detail_file in company_files:
            if detail_file.filename != "":
                details_content_type, _ = mimetypes.guess_type(detail_file.filename)
                details_extension = details_content_type.split("/")[1] if details_content_type else ""
                detail_file_name_in_s3 = f"company_id-{company_id}_file.{details_extension}"

                s3.Bucket(custombucket).put_object(
                    Key=detail_file_name_in_s3, 
                    Body=detail_file, 
                    ContentDisposition=f"attachment; filename={detail_file.filename}"
                )
                file_url = f"https://s3{s3_location}.amazonaws.com/{custombucket}/{detail_file_name_in_s3}"
                file_id = str(uuid4())
                cursor.execute("INSERT INTO companyFile (file_id, company_id) VALUES (%s, %s)", (file_id, company_id))
                cursor.execute("INSERT INTO file (file_id, file_url, file_type, file_name, file_date) VALUES (%s, %s, %s, %s, NOW())", (file_id, file_url, "details", detail_file.filename))
                db_conn.commit()

    except Exception as e:
        return str(e)
       
    finally:
        cursor.close()
    
    print("All modifications done...")
    return render_template('admin-manage-company.html')



@app.route("/deletecompany/<string:company_id>", methods=['DELETE'])
def delete_company(company_id):
    try:
        cursor = db_conn.cursor()
        
        # 1. Delete files associated with the company from the S3 bucket
        cursor.execute("SELECT file_url FROM file f INNER JOIN companyFile cf ON f.file_id = cf.file_id WHERE cf.company_id=%s", (company_id,))
        urls_to_delete = [row[0] for row in cursor.fetchall()]

        for url in urls_to_delete:
            parsed_url = urlparse(url)
            object_key = parsed_url.path.lstrip('/')
            s3_client.delete_object(Bucket=custombucket, Key=object_key)

        # 2. Delete records from `companyFile` and `file` tables
        cursor.execute("DELETE FROM companyFile WHERE company_id=%s", (company_id,))
        cursor.execute("DELETE FROM file WHERE file_id IN (SELECT file_id FROM companyFile WHERE company_id=%s)", (company_id,))
        
        # 3. Delete company record
        cursor.execute("DELETE FROM company WHERE company_id=%s", (company_id,))
        
        db_conn.commit()

        return jsonify({"message": "Company and associated objects deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()





@app.route("/searchcompanies", methods=['POST'])
def search_companies():
    try:
        cursor = db_conn.cursor()

        search_query = request.json.get("searchQuery")  # Get the search query from the JSON request    

        # Modify your SQL query to search for companies by name or industry
        search_sql = "SELECT company_id, company_name, industry FROM company WHERE company_name LIKE %s"
        
        cursor.execute(search_sql, (f"%{search_query}%",))

        company_data = cursor.fetchall()
        cursor.close()

        # Create a list to store the company details
        companies = []

        # Loop through the retrieved data and fetch 2S3 URLs for logos
        for company in company_data:
            company_id, company_name, industry = company
            # Assuming you have a naming convention for the logo files
            
            companies.append({'company_id': company_id,'company_name': company_name, 'industry': industry})
        print("search_query =" + search_query)
        # Return the search results as JSON
        return jsonify(companies)

    except Exception as e:
        return str(e)

    # No need to close the cursor here



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
    
@app.route("/student-login", methods=['GET', 'POST'])
def studentLogin():
    try:
        cursor = db_conn.cursor()

        if request.method == 'POST':
            student_id = request.form.get("student_id")
            password = request.form.get("password")
            print("student_id="+ student_id)
            print("password="+ password)

            # Fetch student based on ID
            cursor.execute("SELECT password FROM studentDetails WHERE student_id=%s", (student_id,))
            result = cursor.fetchone()

            # If student does not exist or password doesn't match
            if not result or result[0] != password:
                return "Invalid student ID or password!", 401

            # Store the student_id in the session
            session['student_id'] = student_id

            # If successful, you can redirect the student to their dashboard with a message
            return redirect(url_for('profile', message="login_successful"))

        # If it's a GET request, render the login form
        return render_template('student-login.html', )

    except Exception as e:
        return str(e)

    finally:
        cursor.close()
@app.route("/profile")
def profile():
    message = request.args.get("message")
    return render_template('profile.html', message=message)
@app.route("/supervisor-login", methods=['GET', 'POST'])
def supervisorLogin():
    try:
        cursor = db_conn.cursor()

        if request.method == 'POST':
            supervisor_id = request.form.get("supervisor_id")
            password = request.form.get("password")
            print("supervisor_id="+ supervisor_id)
            print("password="+ password)

            # Fetch supervisor based on ID
            cursor.execute("SELECT password FROM supervisor WHERE supervisor_id=%s", (supervisor_id,))
            result = cursor.fetchone()

            # If supervisor does not exist or password doesn't match
            if not result or result[0] != password:
                return "Invalid supervisor ID or password!", 401

            # Store the supervisor_id in the session
            session['supervisor_id'] = supervisor_id

            # If successful, you can redirect the supervisor to their dashboard with a message
            return redirect(url_for('studentList', message="login_successful"))

        # If it's a GET request, render the login form
        return render_template('supervisor-login.html', )

    except Exception as e:
        return str(e)

    finally:
        cursor.close()


@app.route("/supervisor-studentList.html")
def studentList():
    message = request.args.get("message")
    return render_template('supervisor-studentList.html', message=message)

@app.route("/admin-login", methods=['GET', 'POST'])
def adminLogin():
    try:
        cursor = db_conn.cursor()

        if request.method == 'POST':
            admin_id = request.form.get("admin_id")
            password = request.form.get("password")
            print("admin_id="+ admin_id)
            print("password="+ password)

            # Fetch admin based on ID
            cursor.execute("SELECT password FROM admin WHERE admin_id=%s", (admin_id,))
            result = cursor.fetchone()

            # If admin does not exist or password doesn't match
            if not result or result[0] != password:
                return "Invalid admin ID or password!", 401

            # Store the admin_id in the session
            session['admin_id'] = admin_id

            # If successful, you can redirect the admin to their management dashboard or appropriate page with a message
            return redirect(url_for('manageStudent', message="login_successful"))

        # If it's a GET request, render the login form
        # Note: Ensure you have a template named 'admin-login.html' for this purpose, 
        # because using 'supervisor-login.html' for admins might be misleading.
        return render_template('admin-login.html', )

    except Exception as e:
        return str(e)

    finally:
        cursor.close()

@app.route("/supervisor-studentList.html")
def manageStudent():
    message = request.args.get("message")
    return render_template('supervisor-studentList.html', message=message)
    
@app.route('/logoutStudent')
def logoutStudent():
    session.clear()  # This will clear all session variables
    return render_template('student-login.html', message="logout_successful")

@app.route('/logoutAdmin')
def logoutAdmin():
    session.clear()  # This will clear all session variables
    return render_template('admin-login.html', message="logout_successful")

@app.route('/logoutSupervisor')
def logoutSupervisor():
    session.clear()  # This will clear all session variables
    return render_template('supervisor-login.html', message="logout_successful")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)


    
    