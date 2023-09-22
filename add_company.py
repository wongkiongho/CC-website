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

            # Retrieve associated company files
            cursor.execute("SELECT f.file_url, f.file_name FROM companyFile cf JOIN file f ON cf.file_id = f.file_id WHERE cf.company_id=%s", (company_id,))
            files_list = [{'file_url': row[0], 'file_name': row[1]} for row in cursor.fetchall()]

            cursor.close()

            if company:
                # Pass the company data and associated files to the edit form
                company_positions = json.loads(company[7])
                return render_template('admin-edit-company.html', company=company, company_positions=company_positions, files_list=files_list)
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
                # Determine the content type and file extension for logo file
                logo_content_type, _ = mimetypes.guess_type(company_logo_file.filename)
                logo_extension = logo_content_type.split("/")[1] if logo_content_type else ""
                company_logo_file_name_in_s3_with_extension = f"company_id-{str(company_id)}_logo_file.{logo_extension}"

                s3.Bucket(custombucket).put_object(
                    Key=company_logo_file_name_in_s3_with_extension,
                    Body=company_logo_file,
                    ContentDisposition=f"attachment; filename={company_logo_file.filename}"
                )

                # Construct the logo URL with the updated file name including extension
                logo_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                    s3_location,
                    custombucket,
                    company_logo_file_name_in_s3_with_extension
                )

                # Insert or update the logo URL in the database
                cursor.execute("SELECT logo_url FROM company WHERE company_id=%s", (company_id,))
                result = cursor.fetchone()

                if result:
                    # Update the existing logo URL
                    update_sql = "UPDATE company SET company_name=%s, industry=%s, company_desc=%s, location=%s, email=%s, contact_number=%s, positions_json=%s, logo_url=%s WHERE company_id=%s"
                    cursor.execute(
                        update_sql, (company_name, industry, company_desc, location, email, contact_number, positions_json,
                                    logo_url, company_id))
                else:
                    # Insert a new record with the logo URL
                    insert_sql = "INSERT INTO company (company_id, company_name, industry, company_desc, location, email, contact_number, positions_json, logo_url) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
                    cursor.execute(
                        insert_sql, (company_id, company_name, industry, company_desc, location, email, contact_number,
                                    positions_json, logo_url))

            # Handle company files
            if company_files:
                for company_file in company_files:
                    # Determine the content type and file extension for company file
                    file_content_type, _ = mimetypes.guess_type(company_file.filename)
                    file_extension = file_content_type.split("/")[1] if file_content_type else ""
                    company_file_name_in_s3_with_extension = f"company_id-{str(company_id)}_{str(uuid4())}.{file_extension}"

                    s3.Bucket(custombucket).put_object(
                        Key=company_file_name_in_s3_with_extension,
                        Body=company_file,
                        ContentDisposition=f"attachment; filename={company_file.filename}"
                    )

                    # Construct the file URL with the updated file name including extension
                    file_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                        s3_location,
                        custombucket,
                        company_file_name_in_s3_with_extension
                    )

                    # Insert the file record into the database
                    cursor.execute("INSERT INTO file (file_id, file_url, file_type, file_name) VALUES (%s, %s, %s, %s)",
                                   (str(uuid4()), file_url, file_content_type, company_file.filename))

                    # Insert the company-file relationship into the companyFile table
                    cursor.execute("INSERT INTO companyFile (file_id, company_id) VALUES (%s, %s)",
                                   (cursor.lastrowid, company_id))

            # Update other company information in the database without changing the URLs
            update_sql = "UPDATE company SET company_name=%s, industry=%s, company_desc=%s, location=%s, email=%s, contact_number=%s, positions_json=%s WHERE company_id=%s"
            cursor.execute(
                update_sql, (company_name, industry, company_desc, location, email, contact_number, positions_json,
                            company_id))
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
        return "Please upload a company logo "
    
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
        select_sql = "SELECT logo_url, file_url FROM company WHERE company_id = %s"
        cursor.execute(select_sql, (company_id,))
        result = cursor.fetchone()
        if result:
            logo_url, file_url = result

            # Extract object keys from URLs
            parsed_logo_url = urlparse(logo_url)
            parsed_file_url = urlparse(file_url)
            logo_object_key = parsed_logo_url.path.lstrip('/')
            file_object_key = parsed_file_url.path.lstrip('/')

            # Delete objects from S3 using the S3 client
            s3_client.delete_object(Bucket=custombucket, Key=logo_object_key)
            s3_client.delete_object(Bucket=custombucket, Key=file_object_key)

            # Delete the company record from the database
            delete_sql = "DELETE FROM company WHERE company_id = %s"
            cursor.execute(delete_sql, (company_id,))
            db_conn.commit()
            cursor.close()

            return jsonify({"message": "Company and associated objects deleted successfully"}), 200
        else:
            return jsonify({"message": "Company not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500




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
    



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=True)

'''
company_logo_file_name_in_s3 = f"company_id-{company_id}_logo_file"
            # Construct the S3 URL
            s3_location = ''  # Replace with the actual S3 location
            logo_url = f"https://s3{s3_location}.amazonaws.com/{custombucket}/{company_logo_file_name_in_s3}"
'''
    
    
    