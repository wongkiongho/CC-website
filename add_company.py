from flask import Flask, render_template, redirect, url_for, request, session
from pymysql import connections
import os
import boto3
from config import *
from uuid import uuid4
import json
from flask import jsonify
import mimetypes
from urllib.parse import urlparse
import os
from uuid import uuid4
from pymysql import MySQLError
import traceback
from datetime import datetime
from flask import flash



app = Flask(__name__)
app.secret_key = os.urandom(24)
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
    return render_template('/student-login.html')

@app.route("/student-login.html", methods=['GET', 'POST'])
def viewStudentLoginPage():
    return render_template('student-login.html')

@app.route("/supervisor-login.html", methods=['GET', 'POST'])
def viewSupervisorLoginPage():
    return render_template('supervisor-login.html')

@app.route("/admin-login.html", methods=['GET', 'POST'])
def viewAdminLoginPage():
    return render_template('admin-login.html')

@app.route("/admin-manage-supervisor.html", methods=['GET', 'POST'])
def viewManageSupervisorPage():
    message = request.args.get('message')  # Retrieve the message from query parameters
    return render_template('admin-manage-supervisor.html', message=message)

@app.route("/admin-add-student.html", methods=['GET', 'POST'])
def viewAddStudentPage():
    return redirect(url_for('addStudent'))


@app.route("/admin-manage-company.html", methods=['GET', 'POST'])
def viewManageCompanyPage():
    message = request.args.get('message')  # Retrieve the message from query parameters
    return render_template('admin-manage-company.html', message=message)

@app.route("/admin-add-company.html", methods=['GET', 'POST'])
def viewAddCompanyPage():
    return render_template('admin-add-company.html')

app.route("/admin-edit-company.html", methods=['GET', 'POST'])
def viewEditCompanyPage():
    return render_template('admin-edit-company.html')

@app.route("/viewcompany/<company_id>", methods=['GET'])
def viewCompany(company_id):
    message = request.args.get('message')  # Retrieve the message from query parameters
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
            logo_url=logo_url,
            message=message
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


            cursor.execute("SELECT file_id FROM companyFile WHERE company_id=%s", (company_id,))
            file_ids_to_delete = [row[0] for row in cursor.fetchall()]
            # Handle company logo file
           

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
            cursor.close()

           

            
            
 
    except Exception as e:
        return str(e)

    finally:
        cursor.close()
        return render_template('admin-manage-company.html', message='company_edited')





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
    return render_template('admin-manage-company.html', message='company_added')



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
def view_companies_list():
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
                return render_template('student-login.html', message='login_failed')

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
                return render_template('supervisor-login.html', message='login_failed')

            # Store the supervisor_id in the session
            session['supervisor_id'] = supervisor_id

            # If successful, you can redirect the supervisor to their dashboard with a message
            return redirect(url_for('manageStudent', message="login_successful"))

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
                return render_template('admin-login.html', message='login_failed')

            # Store the admin_id in the session
            session['admin_id'] = admin_id

            # If successful, you can redirect the admin to their management dashboard or appropriate page with a message
            return redirect(url_for('viewManageStudentPage', message='login_successful'))

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
    
@app.route("/admin-manage-student.html", methods=['GET', 'POST'])
def viewManageStudentPage():
    message = request.args.get("message")
    return render_template('admin-manage-student.html', message=message)

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
    resume_file = request.files.get("resume")
    company_id = request.form.get("company-id")
    details = request.form.get("details")
    file_id = str(uuid4())
    application_id = str(uuid4())


    
    # Check if resume file is provided
    if not  resume_file or  resume_file.filename == "":
        return "Please upload your resume."

    # Generate a unique name for the resume (using student_id and current timestamp for uniqueness)
    resume_content_type, _ = mimetypes.guess_type(resume_file.filename)
    resume_extension = resume_content_type.split("/")[1] if resume_content_type else ""
    resume_file_name_in_s3 = f"student_id-{student_id}_resume.{resume_extension}"


    try:
        s3.Bucket(custombucket).put_object(
            Key=resume_file_name_in_s3, 
            Body=resume_file, 
            ContentDisposition=f"attachment; filename={resume_file.filename}"
        )

        
        # Construct the S3 URL for the uploaded resume
        file_url = f"https://s3{s3_location}.amazonaws.com/{custombucket}/{resume_file_name_in_s3}"

        # Your SQL to insert data into studentForm
        insert_sql = "INSERT INTO application (student_id, company_id, details) VALUES (%s, %s, %s)"
        insert_sql_application_file = "INSERT INTO applicationFile (file_id, application_id) VALUES (%s, %s)"
        insert_sql_file ="INSERT INTO file (file_id, file_url, file_type, file_name, file_date) VALUES (%s, %s, %s, %s, NOW())"


        cursor = db_conn.cursor()
        cursor.execute(insert_sql, (student_id, company_id, details))
        cursor.execute(insert_sql_application_file, (file_id, application_id))
        cursor.execute(insert_sql_file, (file_id, file_url, "Resume", resume_file.filename))
        db_conn.commit()
        print("Student and resume edited successfully!")
        return redirect(url_for('profile'))

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
    
def get_student_files(student_id):
    try:
        with db_conn.cursor() as cursor:
            # Join studentFile with file to retrieve file_url based on student_id
            query = """
            SELECT f.file_url
            FROM studentFile AS sf
            JOIN file AS f ON sf.file_id = f.file_id
            WHERE sf.student_id = %s
            """
            cursor.execute(query, (student_id,))
            student_files = cursor.fetchall()

            return [file[0] for file in student_files]
    except MySQLError as e:
        print(f"Database Error: {e}")
        return []

@app.route("/internship-form", methods=['GET'])
def internship_form():
    
    student_id=session.get('student_id')
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

#... (All the previous imports and initializations remain unchanged)
@app.route("/profile", methods=['GET'])
def profile():
    student_id=session.get('student_id')
    message = request.args.get('message')  # Retrieve the message from query parameters
    try:
        cursor = db_conn.cursor()
        cursor.execute("SELECT student_id, name, email, programme, cohort FROM studentDetails WHERE student_id=%s", (student_id,))
        student = cursor.fetchone()
        cursor.close()

        if student:
            student_id, name, email, programme, cohort = student
            cursor = db_conn.cursor()
            cursor.execute("SELECT f.file_id, f.file_url, f.file_type, f.file_name, f.file_date FROM file f INNER JOIN studentFile cf ON f.file_id = cf.file_id WHERE cf.student_id = %s", (student_id,))
            files = cursor.fetchall()  # Fetch all records
            # Prepare the list of files and identify the progress report

            logo_url = None
            files_list = []
            for file in files:
                if file[2] == "ProgressReport":
                    files_list.append({
                        "file_url": file[1],
                        "file_name": file[3]
                    })
                else:
                    print("no file")
            cursor.close()



            return render_template('profile.html', student_id=student_id, name=name, email=email, programme=programme, cohort=cohort, files_list=files_list, message = message)
        else:
            return "Student not found", 404
    except Exception as e:
        print(e)
        return "Error occurred while fetching student details", 500

@app.route("/edit-profile", methods=['GET', 'POST'])
def edit_profile():
    student_id=session.get('student_id')

    try:
        if request.method == 'POST':
            # Handling form submission
            name = request.form.get('name')
            email = request.form.get('email')
            programme = request.form.get('programme')
            cohort = request.form.get('cohort')
            password = request.form.get('password')
            
            # Update the student data in the database
            update_sql = """
                UPDATE studentDetails
                SET name=%s, email=%s, programme=%s, cohort=%s, password=%s
                WHERE student_id=%s
            """
            
            with db_conn.cursor() as cursor:
                cursor.execute(update_sql, (name, email, programme, cohort, password, student_id))
                db_conn.commit()

            # If the progress file is uploaded, save it to S3 and the database.
            progress_file = request.files.get('progress')
            if progress_file and progress_file.filename:
                resume_content_type, _ = mimetypes.guess_type(progress_file.filename)
                resume_extension = resume_content_type.split("/")[1] if resume_content_type else ""
                resume_file_name_in_s3 = f"student_id-{student_id}_progressreport.{resume_extension}"
                s3.Bucket(custombucket).put_object(
                    Key=resume_file_name_in_s3, 
                    Body=progress_file, 
                    ContentDisposition=f"attachment; filename={progress_file.filename}"
                )

                file_url = f"https://s3{s3_location}.amazonaws.com/{custombucket}/{resume_file_name_in_s3}"


                # Insert file_url into the `file` table
                file_id = str(uuid4())
              
                insert_file_sql = "INSERT INTO file (file_id, file_url, file_type, file_name, file_date) VALUES (%s, %s, %s, %s, NOW())"
                with db_conn.cursor() as cursor:
                    cursor.execute(insert_file_sql, (file_id, file_url, "ProgressReport", progress_file.filename))
                           
                    db_conn.commit()

                # Now, link the student with the file_id in the `studentFile` table
                insert_student_file_sql = "INSERT INTO studentFile (student_id, file_id) VALUES (%s, %s)"
                with db_conn.cursor() as cursor:
                    cursor.execute(insert_student_file_sql, (student_id, file_id))
                    db_conn.commit()

            # Redirect to profile after successful update
            return redirect(url_for('profile', student_id=student_id))
        
        else:
            with db_conn.cursor() as cursor:
                cursor.execute("SELECT student_id, name, email, programme, cohort, password FROM studentDetails WHERE student_id=%s", (student_id,))
                student = cursor.fetchone()

            if student:
                student_dict = {
                    'student_id': student[0],
                    'name': student[1],
                    'email': student[2],
                    'programme': student[3],
                    'cohort': student[4],
                    'password': student[5]
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
        return "Error occurred while fetching or updating student details", 500
@app.route("/application-status", methods=['GET'])
def application_status():
    student_id=session.get('student_id')
    try:
        cursor = db_conn.cursor()
        
        # SQL query to fetch application details
        query = """
        SELECT 
            s.name, 
            a.details, 
            c.company_name, 
            c.email, 
            a.status
        FROM 
            application AS a
        JOIN 
            studentDetails AS s ON a.student_id = s.student_id
        JOIN 
            company AS c ON a.company_id = c.company_id
        WHERE 
            a.student_id = %s;
        """
        #run in db
        cursor.execute(query, (student_id,))
        raw_applications = cursor.fetchall()
        cursor.close()

        # Convert the fetched data into a list of dictionaries
        applications_list = []
        for app in raw_applications:
            app_dict = {
                "student_name": app[0],
                "internship_details": app[1] if app[1] else "N/A",  # Handle None values
                "company_name": app[2],
                "company_email": app[3],
                "status": app[4] if app[4] else "Pending"  # Handle None values
            }
            applications_list.append(app_dict)

        return render_template('application-status.html', applications=applications_list)

    except Exception as e:
        print(e)
        return "Error occurred while fetching application status", 500

@app.route("/admin-add-supervisor.html", methods=['GET', 'POST'])
def viewAddSupervisorPage():
    message = request.args.get('message')  # Retrieve the message from query parameters
    return render_template('admin-add-supervisor.html', message=message)




# add student (DONE)
@app.route("/addstudentandassigntosupervisor", methods=['GET','POST'])
def addStudent():
    message = request.args.get('message')  # Retrieve the message from query parameters
    try:
        if request.method == 'GET':
            cursor = db_conn.cursor()
            cursor.execute("SELECT supervisor_id, name FROM supervisor")
            supervisors = cursor.fetchall()
            cursor.close()
            return render_template("admin-add-student.html", supervisors=supervisors,message=message)

        elif request.method == 'POST':
            # Retrieve form fields
            name = request.form.get("name")
            email = request.form.get("email")
            student_id = request.form.get("student_id")
            password = request.form.get("password")
            programme = request.form.get("programme")
            cohort = request.form.get("cohort")
            supervisor_id = request.form.get("supervisor_id")

            
            insert_sql = "INSERT INTO studentDetails (student_id, name, email, password, programme,  cohort, supervisor_id) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            cursor = db_conn.cursor()
            cursor.execute(insert_sql, (student_id, name, email, password, programme, cohort, supervisor_id))
            db_conn.commit()


            print("Data inserted in MySQL RDS...")
            return render_template("admin-manage-student.html", message='student_added')

    except Exception as e:
        print(f"Error: {e}")
        return str(e)
    finally:
        cursor.close()

# update number of student
@app.route("/getStudentCount", methods=['GET'])
def get_student_count():
    try:
        cursor = db_conn.cursor()
        fetch_count_sql = "SELECT COUNT(*) FROM studentDetails"
        cursor.execute(fetch_count_sql)
        student_count = cursor.fetchone()[0]

        return jsonify({"studentCount": student_count}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
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
    
# add supervisor
@app.route("/addsupervisor", methods=['POST'])
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
        return render_template("admin-manage-supervisor.html", message='supervisor_added')


    except Exception as e:
        print(f"Error: {e}")
        return str(e)
    finally:
        cursor.close()

# update number of student
@app.route("/getSupervisorCount", methods=['GET'])
def get_supervisor_count():
    try:
        cursor = db_conn.cursor()
        fetch_count_sql = "SELECT COUNT(*) FROM supervisor"
        cursor.execute(fetch_count_sql)
        supervisor_count = cursor.fetchone()[0]

        return jsonify({"supervisorCount": supervisor_count}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
    
# view list of supervisor
@app.route("/viewsupervisors", methods=['GET'])
def view_supervisors():
    try:
        # Retrieve company data from the database
        cursor = db_conn.cursor()
        select_sql = "SELECT supervisor_id, name, email FROM supervisor"
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)


    
    