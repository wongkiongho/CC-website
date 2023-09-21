@app.route("/editcompany/<company_id>", methods=['GET', 'POST'])
def editCompany(company_id):
    try:
        cursor = db_conn.cursor()

        if request.method == 'GET':
            # Retrieve company data based on company_id
            cursor.execute("SELECT * FROM company WHERE company_id=%s", (company_id,))
            company = cursor.fetchone()
            cursor.close()

            if company:
                # Pass the company data to the edit form
                company_positions = json.loads(company[7])
                return render_template('admin-edit-company.html', company=company, company_positions=company_positions)
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
            company_detials_file = request.files.get("companyFile")
            company_logo_file = request.files.get("companyLogo")
            company_id = request.form.get("company_id")  # Retrieve company_id from the hidden input

            # Serialize the positions list to JSON
            positions_json = json.dumps(positions)

            update_sql = "UPDATE company SET company_name=%s, industry=%s, company_desc=%s, location=%s, email=%s, contact_number=%s, positions_json=%s WHERE company_id=%s"
            cursor = db_conn.cursor()

            if company_detials_file.filename == "":
                return "Please upload a company's detail file"
            if company_logo_file.filename == "":
                return "Please upload a company logo"

            print("Data inserted in MySQL RDS... uploading image to S3...")

            # Delete the previous objects from S3
            cursor.execute("SELECT logo_url, file_url FROM company WHERE company_id=%s", (company_id,))
            result = cursor.fetchone()
            if result:
                logo_url, file_url = result
                parsed_logo_url = urlparse(logo_url)
                parsed_file_url = urlparse(file_url)
                logo_object_key = parsed_logo_url.path.lstrip('/')
                file_object_key = parsed_file_url.path.lstrip('/')
                s3.delete_object(Bucket=custombucket, Key=logo_object_key)
                s3.delete_object(Bucket=custombucket, Key=file_object_key)

            # Determine the content type and file extension for details file
            details_content_type, _ = mimetypes.guess_type(company_detials_file.filename)
            details_extension = details_content_type.split("/")[1] if details_content_type else ""
            company_detials_file_name_in_s3_with_extension = f"company_id-{str(company_id)}_details_file.{details_extension}"

            # Determine the content type and file extension for logo file
            logo_content_type, _ = mimetypes.guess_type(company_logo_file.filename)
            logo_extension = logo_content_type.split("/")[1] if logo_content_type else ""
            company_logo_file_name_in_s3_with_extension = f"company_id-{str(company_id)}_logo_file.{logo_extension}"

            s3.Bucket(custombucket).put_object(
                Key=company_detials_file_name_in_s3_with_extension,
                Body=company_detials_file,
                ContentDisposition=f"attachment; filename={company_detials_file.filename}"
            )
            s3.Bucket(custombucket).put_object(
                Key=company_logo_file_name_in_s3_with_extension,
                Body=company_logo_file,
                ContentDisposition=f"attachment; filename={company_logo_file.filename}"
            )

            # Construct the URLs with the updated file names including extensions
            logo_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                s3_location,
                custombucket,
                company_logo_file_name_in_s3_with_extension)

            file_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                s3_location,
                custombucket,
                company_detials_file_name_in_s3_with_extension)

            cursor.execute(
                update_sql, (company_name, industry, company_desc, location, email, contact_number, positions_json,
                             logo_url, file_url, company_id))
            db_conn.commit()

    except Exception as e:
        return str(e)

    finally:
        cursor.close()
    # If it's a GET request, simply render the form
    print("all modification done...")
    return render_template('admin-manage-company.html')