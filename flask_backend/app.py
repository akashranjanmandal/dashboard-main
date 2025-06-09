# app.py
from binascii import Error
import csv
import io
import math
from flask import Flask, Response, json, jsonify, request
from flask_cors import CORS
import pymysql.cursors
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Union
import logging
from werkzeug.utils import secure_filename
from flask import session
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from pathlib import Path
app = Flask(__name__)
CORS(app)

# Configure CORS to allow requests from http://localhost:3000 with credentials
# CORS(app, resources={r"/*": {"origins":"*"}}, supports_credentials=True)

import os
from dotenv import load_dotenv
import uuid
import boto3

# Load environment variables from .env file
env_path = Path('.') / '.local.env'
load_dotenv()
# def get_db_connection():
#     return pymysql.connect(
#         host='localhost',  # Your MySQL host
#         port=3306,             # MySQL port
#         user='root',           # MySQL username
#         password='Diamond0606***',  # MySQL password
#         database='lifeapp',    # Database name
#         cursorclass=pymysql.cursors.DictCursor
#     )

# DigitalOcean Spaces Config
DO_SPACES_KEY = os.getenv('DO_SPACES_KEY')
DO_SPACES_SECRET = os.getenv('DO_SPACES_SECRET')
DO_SPACES_REGION = os.getenv('DO_SPACES_REGION')
DO_SPACES_BUCKET = os.getenv('DO_SPACES_BUCKET')
DO_SPACES_ENDPOINT = os.getenv('DO_SPACES_ENDPOINT')


# Initialize Boto3 Client
# s3_client = boto3.client(
#     "s3",
#     endpoint_url=DO_SPACES_ENDPOINT,
#     aws_access_key_id=DO_SPACES_KEY,
#     aws_secret_access_key=DO_SPACES_SECRET,
# )


def get_db_connection():
    host=os.getenv('DB_HOST', '139.59.84.157')
    port=int(os.getenv('DB_PORT', 3306))
    user=os.getenv('DB_USERNAME', 'root')
    password=os.getenv('DB_PASSWORD', 'LIFELAB@1server')
    database=os.getenv('DB_DATABASE', 'lifeapp')
    # print(host,port,user,password,database)
    return pymysql.connect(
        host = host,  # Fallback to 'localhost'
        port = port,     # Fallback to 3306
        user = user,        # Fallback to 'root'
        password=password,    # Fallback to empty
        database=database,
        cursorclass=pymysql.cursors.DictCursor
    )

# def get_db_connection():
#     return pymysql.connect(
#         host=os.getenv('DB_HOST', 'localhost'),
#         port=int(os.getenv('DB_PORT', 3306)),
#         user=os.getenv('DB_USERNAME', 'root'),
#         password=os.getenv('DB_PASSWORD', ''),
#         database=os.getenv('DB_DATABASE', 'lifeapp'),
#         cursorclass=pymysql.cursors.DictCursor
#     )


@app.route('/api/login', methods=['POST'])
def admin_login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    cursor = get_db_connection().cursor(pymysql.cursors.DictCursor)

    cursor.execute("SELECT id, email, password, type FROM users WHERE email=%s AND type=1", (email,))
    user = cursor.fetchone()

    if not user:
        return jsonify({
            'errors': {
                'title': 'Login Failed!',
                'icon': 'AlertCircleIcon',
                'type': 'warning',
                'message': 'Admin not exist'
            }
        }), 401

    if password != user['password']:
        return jsonify({
            'errors': {
                'title': 'Login Failed!',
                'icon': 'EyeOffIcon',
                'type': 'warning',
                'message': 'Admin wrong password'
            }
        }), 401

    # Dummy response (token generation skipped)
    admin = {
        'id': user['id'],
        'email': user['email'],
        'role': 'admin',
        'ability': [{'action': 'manage', 'subject': 'all'}]
    }

    return jsonify({
        'accessToken': 'test-token',  # Optional, just for frontend compatibility
        'message': 'Login Success Full',
        'res': True,
        'admin': admin
    }), 200

@app.route('/api/logout', methods=['POST'])
def admin_logout():
    # For stateless token-based login, logout is usually handled on frontend
    # But we return a success response for frontend compatibility
    return jsonify({
        'message': 'Logout successful',
        'res': True
    }), 200


@app.route('/debug-env', methods = ['GET'])
def debug_env():
    host = os.getenv('DB_HOST')
    user = os.getenv('DB_USERNAME')
    password = os.getenv('DB_PASSWORD')
    return jsonify({
        'host': host,
        'user': user,
        'password': password
    })

@app.route('/')
def backup():
    return "Heya, thanks for checking"

def upload_media(file):
    original_filename = file.filename
    ext = os.path.splitext(original_filename)[1]
    unique_filename = str(uuid.uuid4()) + ext
    key = f"media/{unique_filename}"

    s3 = boto3.client(
        's3',
        region_name=DO_SPACES_REGION,
        endpoint_url=DO_SPACES_ENDPOINT,
        aws_access_key_id=DO_SPACES_KEY,
        aws_secret_access_key=DO_SPACES_SECRET
    )

    s3.upload_fileobj(file, DO_SPACES_BUCKET, key, ExtraArgs={'ACL': 'public-read'})

    # Save into media table (MySQL connection)
    conn = get_db_connection()
    cur = conn.cursor()

    sql = """
        INSERT INTO media (name, path)
        VALUES (%s, %s)
    """
    cur.execute(sql, (original_filename, key))
    conn.commit()

    media_id = cur.lastrowid  # Auto-increment ID of inserted media

    cur.close()
    conn.close()
    BASE_URL = os.getenv('BASE_URL', '')
    # Return Media Object
    return {
        'id': media_id,
        'name': original_filename,
        'path': key,
        'url': BASE_URL + key
    }

###################################################################################
###################################################################################
######################## HOME DASHBOARD APIs ######################################
###################################################################################
###################################################################################

def execute_query(query: str, params: tuple = None) -> List[Dict[str, Any]]:
    """
    Execute a database query and return results.
    
    Args:
        query (str): SQL query to execute
        params (tuple, optional): Query parameters
        
    Returns:
        List[Dict[str, Any]]: Query results
    """
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Query execution error: {str(e)}")
        raise
    finally:
        if connection:
            connection.close()

@app.route('/api/signing-user', methods=['POST'])
def get_user_signups2():
    """
    Get user signup statistics grouped by different time periods.
    Query parameters:
        grouping: str - Time grouping (daily, weekly, monthly, quarterly, yearly, lifetime)
        start_date: str - Start date for filtering (YYYY-MM-DD)
        end_date: str - End date for filtering (YYYY-MM-DD)
    """
    try:
        filters = request.get_json() or {}
        grouping = filters.get('grouping', 'monthly')
        user_type = filters.get('user_type', 'All')  # Get user_type from request
        start_date = filters.get('start_date')
        end_date = filters.get('end_date')

        # Base query with date filtering
        base_query = """
            SELECT 
                {date_format} AS period,
                COUNT(*) AS count,
                CASE 
                    WHEN `type` = 1 THEN 'Admin'
                    WHEN `type` = 3 THEN 'Student'
                    WHEN `type` = 4 THEN 'Mentor'
                    WHEN `type` = 5 THEN 'Teacher'
                    ELSE 'Unspecified'
                END AS user_type 
            FROM lifeapp.users 
            WHERE 1=1
        """
        params = []

        # Add user_type filter
        if user_type and user_type != 'All':
            type_map = {
                'Admin': 1,
                'Student': 3,
                'Mentor': 4,
                'Teacher': 5,
                'Unspecified': 'NOT IN (1,3,4,5)'
            }
            if user_type in type_map:
                if user_type == 'Unspecified':
                    base_query += " AND (type NOT IN (1,3,4,5) OR type IS NULL)"
                else:
                    base_query += " AND type = %s"
                    params.append(type_map[user_type])

        # Add date range filters if provided
        if start_date:
            base_query += " AND created_at >= %s"
            params.append(start_date)
        if end_date:
            base_query += " AND created_at <= %s"
            params.append(end_date)

        # Define date format based on grouping
        date_formats = {
            'daily': "DATE_FORMAT(created_at, '%%Y-%%m-%%d')",
            'weekly': "DATE_FORMAT(created_at, '%%Y-%%u')",  # ISO week number
            'monthly': "DATE_FORMAT(created_at, '%%Y-%%m')",
            'quarterly': "CONCAT(YEAR(created_at), '-Q', QUARTER(created_at))",
            'yearly': "YEAR(created_at)",
            'lifetime': "'Lifetime'"
        }

        if grouping not in date_formats:
            return jsonify({"error": "Invalid grouping parameter"}), 400

        # Format query with appropriate date format
        query = base_query.format(date_format=date_formats[grouping])
        
        # Add grouping and ordering
        if grouping != 'lifetime':
            query += f" GROUP BY period, user_type HAVING period IS NOT NULL ORDER BY period"
        else:
            query += " GROUP BY period, user_type"

        result = execute_query(query, tuple(params))

        # Add additional metadata for better client-side handling
        response = {
            "data": result,
            "grouping": grouping,
            "start_date": start_date,
            "end_date": end_date,
            "total_count": sum(row['count'] for row in result)
        }

        return jsonify(response)
    except Exception as e:
        logger.error(f"Error in get_user_signups: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/user-signups', methods=['GET'])
def get_user_signups():
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Execute the SQL query
            sql = """
                SELECT 
                    DATE_FORMAT(created_at, '%Y-%m') AS month,
                    COUNT(*) AS count 
                FROM lifeapp.users 
                GROUP BY month
                HAVING month is not null
                ORDER BY month
            """
            cursor.execute(sql)
            result = cursor.fetchall()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/user-count', methods=['GET'])
def get_user_count():
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Execute the SQL query
            sql = """
                SELECT count(*) as count from lifeapp.users
            """
            cursor.execute(sql)
            result = cursor.fetchall()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/active-user-count', methods = ['GET'])
def get_active_user_count():
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            #execute sql query
            sql = """
                SELECT COUNT(DISTINCT user_id) AS active_users
                    FROM lifeapp.la_mission_completes
                    WHERE points > 0 OR approved_at IS NOT NULL;
                """
            cursor.execute(sql)
            result = cursor.fetchall()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/new-signups', methods=['GET'])
def get_new_signups():
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Execute the SQL query
            sql = """
                SELECT 
                    DATE_FORMAT(created_at, '%Y-%m') AS month,
                    COUNT(*) AS count 
                FROM lifeapp.users 
                GROUP BY month
                HAVING month is not null
                ORDER BY month DESC
                LIMIT 1
            """
            cursor.execute(sql)
            result = cursor.fetchall()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/approval-rate', methods= ['GET'])
def get_approval_rate():
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            #execute sql query
            sql = """
            select round(sum(case 
                            when approved_at is null
                             then 0 
                            else 1 
                        end)/count(*) * 100,2) 
            as Approval_Rate from lifeapp.la_mission_completes;

            """
            cursor.execute(sql)
            result = cursor.fetchall()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/coupons-used-count', methods=['GET'])
def get_coupons_used_count():
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = """
            select -amount as amount, count(*) as coupon_count from lifeapp.coin_transactions group by coinable_type,amount having amount < 0 order by amount asc ;
            """
            cursor.execute(sql)
            result = cursor.fetchall()
            print("Query Result:", result)  # Debugging statement
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/teacher-assign-count', methods= ['GET'])
def get_teacher_assign_count():
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            #execute sql query
            sql = """
            select teacher_id, count(*) as assign_count from lifeapp.la_mission_assigns group by teacher_id;
            """
            cursor.execute(sql)
            result = cursor.fetchall()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/count-school-state', methods= ['GET'])
def get_count_school_rate():
    connection = get_db_connection()
    try:
       
        with connection.cursor() as cursor:
            #execute sql query
            sql = """
            select state, count(*) as count_state from lifeapp.schools 
            where state != 'null' and state != '2' group by state order by count_state desc limit 5;
            """
            cursor.execute(sql)
            result = cursor.fetchall()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/user-type-chart',methods = ['GET'])
def get_user_type_fetch():
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Execute the SQL query
            sql = """
                select count(*) as count,
                case 
                when type = 1
                    then 'Admin'
                when type = 3
                    then 'Student'
                when type = 5
                    then 'Teacher'
                when type = 4
                    then 'Mentor'
                else 'Default'
                end as
                userType from lifeapp.users group by type;
            """
            cursor.execute(sql)
            result = cursor.fetchall()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/students-by-grade-over-time', methods=['POST'])
def get_students_by_grade_over_time():
    req = request.get_json()
    grouping = req.get('grouping', 'monthly')
    
    # Choose the appropriate time expression for grouping
    if grouping == 'daily':
        period_expr = "DATE(created_at)"
    elif grouping == 'weekly':
        period_expr = "CONCAT(YEAR(created_at), '-', LPAD(WEEK(created_at, 3), 2, '0'))"
    elif grouping == 'monthly':
        period_expr = "DATE_FORMAT(created_at, '%Y-%m')"
    elif grouping == 'quarterly':
        period_expr = "CONCAT(YEAR(created_at), '-Q', QUARTER(created_at))"
    elif grouping == 'yearly':
        period_expr = "YEAR(created_at)"
    elif grouping == 'lifetime':
        period_expr = "'Lifetime'"
    else:
        period_expr = "DATE_FORMAT(created_at, '%Y-%m')"

    sql = f"""
        SELECT {period_expr} AS period, 
               IFNULL(grade, 'Unspecified') AS grade,
               COUNT(*) AS count
        FROM lifeapp.users 
        WHERE `type` = 3 
        GROUP BY period, grade
        ORDER BY period, grade;
    """
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchall()  
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        connection.close()

@app.route('/api/total-student-count', methods=['GET'])
def get_total_student_count():
    connection = None  # Initialize connection to None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = """
                SELECT count(*) as count from lifeapp.users where `type` = 3;
            """
            cursor.execute(sql)
            result = cursor.fetchall()
            print("Query Result:", result)  # Debugging statement
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if connection:  # Only close connection if it was established
            connection.close()
    
@app.route('/api/teachers-by-grade-over-time', methods=['POST'])
def get_teachers_by_grade_over_time():
    req = request.get_json()
    grouping = req.get('grouping', 'monthly')
    
    # Set the time period expression based on the grouping option.
    if grouping == 'daily':
        period_expr = "DATE(created_at)"
    elif grouping == 'weekly':
        period_expr = "CONCAT(YEAR(created_at), '-', LPAD(WEEK(created_at, 3), 2, '0'))"
    elif grouping == 'monthly':
        period_expr = "DATE_FORMAT(created_at, '%Y-%m')"
    elif grouping == 'quarterly':
        period_expr = "CONCAT(YEAR(created_at), '-Q', QUARTER(created_at))"
    elif grouping == 'yearly':
        period_expr = "YEAR(created_at)"
    elif grouping == 'lifetime':
        period_expr = "'Lifetime'"
    else:
        period_expr = "DATE_FORMAT(created_at, '%Y-%m')"

    sql = f"""
        SELECT {period_expr} AS period,
               la_grade_id AS grade,
               COUNT(DISTINCT user_id) AS count
        FROM lifeapp.la_teacher_grades
        GROUP BY period, grade
        ORDER BY period, grade;
    """
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchall()  
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        connection.close()

@app.route('/api/teacher-count', methods = ['POST'])
def get_teacher_count():
    # select count(*) as total_count from lifeapp.users where `type` = 5;
    sql = """
        
        select sum(total_count) as total_count from (
            select count(distinct user_id) as total_count, la_grade_id
                from lifeapp.la_teacher_grades
                group by la_grade_id
        ) as teacher_count; 
    """
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchall()  
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        connection.close()

@app.route('/api/demograph-students', methods=['POST'])
def get_demograph_students():
    """
    Returns Count of students in each state with normalized state names.
    Ensures unique state entries and consistent naming.
    """
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Normalize state names and aggregate counts
            sql = """
            SELECT 
                CASE 
                    WHEN state IN ('Gujrat', 'Gujarat') THEN 'Gujarat'
                    WHEN state IN ('Tamilnadu', 'Tamil Nadu') THEN 'Tamil Nadu'
                    ELSE state 
                END AS normalized_state,
                SUM(count) as total_count
            FROM (
                SELECT state, COUNT(*) as count 
                FROM lifeapp.users 
                WHERE `type` = 3 AND state != 2 
                GROUP BY state
            ) AS subquery
            GROUP BY normalized_state
            ORDER BY total_count DESC
            """
            cursor.execute(sql)
            result = cursor.fetchall()
            
            # Convert to list of dictionaries with consistent keys
            normalized_result = [
                {"count": row['total_count'], "state": row['normalized_state']} 
                for row in result
            ]
            
            return jsonify(normalized_result), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        connection.close()

@app.route('/api/demograph-teachers' , methods = ['POST'])
def get_teacher_demograph():
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Normalize state names and aggregate counts
            sql = """
            SELECT 
                CASE 
                    WHEN state IN ('Gujrat', 'Gujarat') THEN 'Gujarat'
                    WHEN state IN ('Tamilnadu', 'Tamil Nadu') THEN 'Tamil Nadu'
                    ELSE state 
                END AS normalized_state,
                SUM(count) as total_count
            FROM (
                SELECT state, COUNT(*) as count 
                FROM lifeapp.users 
                WHERE `type` = 5 AND state != 2 
                GROUP BY state
            ) AS subquery
            GROUP BY normalized_state
            ORDER BY total_count DESC
            """
            cursor.execute(sql)
            result = cursor.fetchall()
            
            # Convert to list of dictionaries with consistent keys
            normalized_result = [
                {"count": row['total_count'], "state": row['normalized_state']} 
                for row in result
            ]
            
            return jsonify(normalized_result), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        connection.close()

@app.route('/api/total-points-earned', methods=['POST'])
def get_total_points_earned():
    sql1 = """
        SELECT COALESCE(SUM(points), 0) AS total_points 
        FROM lifeapp.la_mission_completes;
    """
    sql2 = """
        SELECT COALESCE(SUM(coins), 0) AS total_coins 
        FROM lifeapp.la_quiz_game_results;
    """
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Execute first query to get points sum
            cursor.execute(sql1)
            result_points = cursor.fetchone()
            total_points = result_points['total_points']

            # Execute second query to get coins sum
            cursor.execute(sql2)
            result_coins = cursor.fetchone()
            total_coins = result_coins['total_coins']

            # Calculate combined total
            combined_total = total_points + total_coins

        return jsonify({"total_points": combined_total}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'connection' in locals():
            connection.close()

@app.route('/api/total-points-redeemed', methods = ['POST'])
def get_total_points_redeemed():
    sql  = """
        select sum(coins) as total_coins_redeemed from lifeapp.coupon_redeems;
    """
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchall()  
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        connection.close()

@app.route('/api/histogram_level_subject_challenges_complete', methods=['POST'])
def get_histogram_data_level_subject_challenges_complete():
    try:
        data = request.get_json() or {}
        grouping = data.get('grouping', 'monthly').lower()
        status_filter = data.get('status', 'all').lower()
        subject_filter = data.get('subject')  # New subject filter
        
        # Validate grouping
        allowed_groupings = ['daily', 'weekly', 'monthly', 'quarterly', 'yearly', 'lifetime']
        grouping = grouping if grouping in allowed_groupings else 'monthly'

        # Status conditions
        status_conditions = {
            'submitted': "lamc.approved_at IS NULL AND lamc.rejected_at IS NULL",
            'rejected': "lamc.approved_at IS NULL AND lamc.rejected_at IS NOT NULL",
            'approved': "lamc.approved_at IS NOT NULL",
            'all': "1=1"
        }
        status_condition = status_conditions.get(status_filter, "1=1")

        # Period expression
        period_expressions = {
            'daily': "DATE(lamc.created_at)",
            'weekly': "CONCAT(YEAR(lamc.created_at), '-W', WEEK(lamc.created_at, 1))",
            'monthly': "DATE_FORMAT(lamc.created_at, '%%Y-%%m')",
            'quarterly': "CONCAT(YEAR(lamc.created_at), '-Q', QUARTER(lamc.created_at))",
            'yearly': "CAST(YEAR(lamc.created_at) AS CHAR)",
            'lifetime': "'lifetime'"
        }
        period_expr = period_expressions[grouping]

        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = f"""
                SELECT 
                    {period_expr} AS period,
                    COUNT(*) AS count, 
                    las.title AS subject_title, 
                    lal.title AS level_title
                FROM lifeapp.la_mission_completes lamc 
                INNER JOIN lifeapp.la_missions lam ON lam.id = lamc.la_mission_id
                INNER JOIN lifeapp.la_subjects las ON lam.la_subject_id = las.id
                INNER JOIN lifeapp.la_levels lal ON lam.la_level_id = lal.id
                WHERE lam.type = 1
                AND {status_condition}
                {"AND JSON_CONTAINS(las.title, %s, '$')" if subject_filter else ""}
                GROUP BY period, lam.la_subject_id, lam.la_level_id
                ORDER BY period, lam.la_subject_id, lam.la_level_id;
            """
            params = ()
            if subject_filter:
                # Create JSON string for subject filter
                subject_json = json.dumps({"en": subject_filter})
                params = (subject_json,)
            
            cursor.execute(sql, params)
            results = cursor.fetchall()
        return jsonify(results), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if connection:
            connection.close()

@app.route('/api/histogram_level_subject_jigyasa_complete', methods=['POST'])
def get_histogram_data_level_subject_jigyasa_complete():
    try:
        data = request.get_json() or {}
        grouping = data.get('grouping', 'monthly').lower()
        status_filter = data.get('status', 'all').lower()
        subject_filter = data.get('subject')  # New subject filter
        
        allowed_groupings = ['daily', 'weekly', 'monthly', 'quarterly', 'yearly', 'lifetime']
        grouping = grouping if grouping in allowed_groupings else 'monthly'

        status_conditions = {
            'submitted': "lamc.approved_at IS NULL AND lamc.rejected_at IS NULL",
            'rejected': "lamc.approved_at IS NULL AND lamc.rejected_at IS NOT NULL",
            'approved': "lamc.approved_at IS NOT NULL",
            'all': "1=1"
        }
        status_condition = status_conditions.get(status_filter, "1=1")

        period_expressions = {
            'daily': "DATE(lamc.created_at)",
            'weekly': "CONCAT(YEAR(lamc.created_at), '-W', WEEK(lamc.created_at, 1))",
            'monthly': "DATE_FORMAT(lamc.created_at, '%%Y-%%m')",
            'quarterly': "CONCAT(YEAR(lamc.created_at), '-Q', QUARTER(lamc.created_at))",
            'yearly': "CAST(YEAR(lamc.created_at) AS CHAR)",
            'lifetime': "'lifetime'"
        }
        period_expr = period_expressions[grouping]

        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = f"""
                SELECT 
                    {period_expr} AS period,
                    COUNT(*) AS count, 
                    las.title AS subject_title, 
                    lal.title AS level_title
                FROM lifeapp.la_mission_completes lamc 
                INNER JOIN lifeapp.la_missions lam ON lam.id = lamc.la_mission_id
                INNER JOIN lifeapp.la_subjects las ON lam.la_subject_id = las.id
                INNER JOIN lifeapp.la_levels lal ON lam.la_level_id = lal.id
                WHERE lam.type = 5
                AND {status_condition}
                {"AND JSON_CONTAINS(las.title, %s, '$')" if subject_filter else ""}
                GROUP BY period, lam.la_subject_id, lam.la_level_id
                ORDER BY period, lam.la_subject_id, lam.la_level_id;
            """
            params = ()
            if subject_filter:
                subject_json = json.dumps({"en": subject_filter})
                params = (subject_json,)
            
            cursor.execute(sql, params)
            results = cursor.fetchall()
        return jsonify(results), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if connection:
            connection.close()

@app.route('/api/histogram_level_subject_pragya_complete', methods=['POST'])
def get_histogram_data_level_subject_pragya_complete():
    try:
        data = request.get_json() or {}
        grouping = data.get('grouping', 'monthly').lower()
        status_filter = data.get('status', 'all').lower()
        subject_filter = data.get('subject')  # New subject filter
        
        allowed_groupings = ['daily', 'weekly', 'monthly', 'quarterly', 'yearly', 'lifetime']
        grouping = grouping if grouping in allowed_groupings else 'monthly'

        status_conditions = {
            'submitted': "lamc.approved_at IS NULL AND lamc.rejected_at IS NULL",
            'rejected': "lamc.approved_at IS NULL AND lamc.rejected_at IS NOT NULL",
            'approved': "lamc.approved_at IS NOT NULL",
            'all': "1=1"
        }
        status_condition = status_conditions.get(status_filter, "1=1")

        period_expressions = {
            'daily': "DATE(lamc.created_at)",
            'weekly': "CONCAT(YEAR(lamc.created_at), '-W', WEEK(lamc.created_at, 1))",
            'monthly': "DATE_FORMAT(lamc.created_at, '%%Y-%%m')",
            'quarterly': "CONCAT(YEAR(lamc.created_at), '-Q', QUARTER(lamc.created_at))",
            'yearly': "CAST(YEAR(lamc.created_at) AS CHAR)",
            'lifetime': "'lifetime'"
        }
        period_expr = period_expressions[grouping]

        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = f"""
                SELECT 
                    {period_expr} AS period,
                    COUNT(*) AS count, 
                    las.title AS subject_title, 
                    lal.title AS level_title
                FROM lifeapp.la_mission_completes lamc 
                INNER JOIN lifeapp.la_missions lam ON lam.id = lamc.la_mission_id
                INNER JOIN lifeapp.la_subjects las ON lam.la_subject_id = las.id
                INNER JOIN lifeapp.la_levels lal ON lam.la_level_id = lal.id
                WHERE lam.type = 6
                AND {status_condition}
                {"AND JSON_CONTAINS(las.title, %s, '$')" if subject_filter else ""}
                GROUP BY period, lam.la_subject_id, lam.la_level_id
                ORDER BY period, lam.la_subject_id, lam.la_level_id;
            """
            params = ()
            if subject_filter:
                subject_json = json.dumps({"en": subject_filter})
                params = (subject_json,)
            
            cursor.execute(sql, params)
            results = cursor.fetchall()
        return jsonify(results), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if connection:
            connection.close()

@app.route('/api/histogram_topic_level_subject_quizgames_2', methods=['POST'])
def get_histogram_topic_level_subject_quizgames_2():
    connection = None
    try:
        data = request.get_json() or {}
        grouping = data.get('grouping', 'monthly').lower()
        subject_filter = data.get('subject')  # Get subject filter from request
        
        allowed_groupings = ['daily', 'weekly', 'monthly', 'quarterly', 'yearly', 'lifetime']
        grouping = grouping if grouping in allowed_groupings else 'monthly'

        # Build period expression
        period_exprs = {
            'daily': "DATE(laqg.completed_at)",
            'weekly': "CONCAT(YEAR(laqg.completed_at), '-W', WEEK(laqg.completed_at, 1))",
            'monthly': "DATE_FORMAT(laqg.completed_at, '%%Y-%%m')",
            'quarterly': "CONCAT(YEAR(laqg.completed_at), '-Q', QUARTER(laqg.completed_at))",
            'yearly': "CAST(YEAR(laqg.completed_at) AS CHAR)",
            'lifetime': "'lifetime'"
        }
        period_expr = period_exprs[grouping]

        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = f"""
                SELECT 
                    {period_expr} AS period,
                    COUNT(*) AS count,
                    las.title AS subject_title,
                    lal.title AS level_title
                FROM lifeapp.la_quiz_games laqg
                INNER JOIN lifeapp.la_subjects las ON laqg.la_subject_id = las.id
                INNER JOIN lifeapp.la_topics lat ON lat.id = laqg.la_topic_id
                INNER JOIN lifeapp.la_levels lal ON lat.la_level_id = lal.id
                WHERE las.status = 1 
                    AND laqg.completed_at IS NOT NULL
                    {"AND JSON_CONTAINS(las.title, %s, '$')" if subject_filter else ""}
                GROUP BY period, laqg.la_subject_id, lat.la_level_id
                ORDER BY period, las.title, lal.title;
            """
            params = ()
            if subject_filter:
                # Create JSON string for subject filter
                subject_json = json.dumps({"en": subject_filter})
                params = (subject_json,)
            
            cursor.execute(sql, params)
            result = cursor.fetchall()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if connection:
            connection.close()

@app.route('/api/mission-points-over-time', methods=['POST'])
def mission_points_over_time():
    """
    Returns total mission points grouped by the requested time period.
    Expects JSON payload: { "grouping": "daily" | "weekly" | "monthly" | "quarterly" | "yearly" | "lifetime" }
    """
    req = request.get_json() or {}
    grouping = req.get('grouping', 'monthly')

    # Determine SQL expressions based on grouping
    if grouping == 'daily':
        expr = "DATE(lamc.created_at)"
    elif grouping == 'weekly':
        expr = "CONCAT(YEAR(lamc.created_at), '-', LPAD(WEEK(lamc.created_at, 1), 2, '0'))"
    elif grouping == 'monthly':
        expr = "DATE_FORMAT(lamc.created_at, '%Y-%m')"
    elif grouping == 'quarterly':
        expr = "CONCAT(YEAR(lamc.created_at), '-Q', QUARTER(lamc.created_at))"
    elif grouping == 'yearly':
        # cast to CHAR so period is a string
        expr = "CAST(YEAR(lamc.created_at) AS CHAR)"
    else:  # lifetime
        expr = "'Lifetime'"

    # Build SQL with join and grouping
    sql = [
        f"SELECT {expr} AS period, SUM(lamc.points) AS points",
        "FROM lifeapp.la_mission_completes lamc",
        "INNER JOIN lifeapp.la_missions lam",
        "  ON lamc.la_mission_id = lam.id",
        "  AND lam.type = 1"
    ]
    # Only add GROUP BY if not lifetime
    if grouping != 'lifetime':
        sql.append(f"GROUP BY {expr}")
        sql.append("ORDER BY period ASC")

    query = ' '.join(sql)

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
    finally:
        conn.close()

    return jsonify({ 'data': rows })

@app.route('/api/quiz-points-over-time', methods=['POST'])
def quiz_points_over_time():
    """
    Returns total mission points grouped by the requested time period.
    Expects JSON payload: { "grouping": "daily" | "weekly" | "monthly" | "quarterly" | "yearly" | "lifetime" }
    """
    req = request.get_json() or {}
    grouping = req.get('grouping', 'monthly')

    # Determine SQL expressions based on grouping
    if grouping == 'daily':
        expr = "DATE(created_at)"
    elif grouping == 'weekly':
        expr = "CONCAT(YEAR(created_at), '-', LPAD(WEEK(created_at, 1), 2, '0'))"
    elif grouping == 'monthly':
        expr = "DATE_FORMAT(created_at, '%Y-%m')"
    elif grouping == 'quarterly':
        expr = "CONCAT(YEAR(created_at), '-Q', QUARTER(created_at))"
    elif grouping == 'yearly':
        # cast to CHAR so period is a string
        expr = "CAST(YEAR(created_at) AS CHAR)"
    else:  # lifetime
        expr = "'Lifetime'"

    # Build SQL with join and grouping
    sql = [
        f"SELECT {expr} AS period, sum(coins) as points",
        "from lifeapp.la_quiz_game_results",
    ]
    # Only add GROUP BY if not lifetime
    if grouping != 'lifetime':
        sql.append(f"GROUP BY {expr}")
        sql.append("ORDER BY period ASC")

    query = ' '.join(sql)

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
    finally:
        conn.close()

    return jsonify({ 'data': rows })

@app.route('/api/jigyasa-points-over-time', methods=['POST'])
def jigyasa_points_over_time():
    """
    Returns total mission points grouped by the requested time period.
    Expects JSON payload: { "grouping": "daily" | "weekly" | "monthly" | "quarterly" | "yearly" | "lifetime" }
    """
    req = request.get_json() or {}
    grouping = req.get('grouping', 'monthly')

    # Determine SQL expressions based on grouping
    if grouping == 'daily':
        expr = "DATE(lamc.created_at)"
    elif grouping == 'weekly':
        expr = "CONCAT(YEAR(lamc.created_at), '-', LPAD(WEEK(lamc.created_at, 1), 2, '0'))"
    elif grouping == 'monthly':
        expr = "DATE_FORMAT(lamc.created_at, '%Y-%m')"
    elif grouping == 'quarterly':
        expr = "CONCAT(YEAR(lamc.created_at), '-Q', QUARTER(lamc.created_at))"
    elif grouping == 'yearly':
        # cast to CHAR so period is a string
        expr = "CAST(YEAR(lamc.created_at) AS CHAR)"
    else:  # lifetime
        expr = "'Lifetime'"

    # Build SQL with join and grouping
    sql = [
        f"SELECT {expr} AS period, SUM(lamc.points) AS points",
        "FROM lifeapp.la_mission_completes lamc",
        "INNER JOIN lifeapp.la_missions lam",
        "  ON lamc.la_mission_id = lam.id",
        "  AND lam.type = 5"
    ]
    # Only add GROUP BY if not lifetime
    if grouping != 'lifetime':
        sql.append(f"GROUP BY {expr}")
        sql.append("ORDER BY period ASC")

    query = ' '.join(sql)

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

    return jsonify({ 'data': rows })

@app.route('/api/pragya-points-over-time', methods=['POST'])
def pragya_points_over_time():
    """
    Returns total mission points grouped by the requested time period.
    Expects JSON payload: { "grouping": "daily" | "weekly" | "monthly" | "quarterly" | "yearly" | "lifetime" }
    """
    req = request.get_json() or {}
    grouping = req.get('grouping', 'monthly')

    # Determine SQL expressions based on grouping
    if grouping == 'daily':
        expr = "DATE(lamc.created_at)"
    elif grouping == 'weekly':
        expr = "CONCAT(YEAR(lamc.created_at), '-', LPAD(WEEK(lamc.created_at, 1), 2, '0'))"
    elif grouping == 'monthly':
        expr = "DATE_FORMAT(lamc.created_at, '%Y-%m')"
    elif grouping == 'quarterly':
        expr = "CONCAT(YEAR(lamc.created_at), '-Q', QUARTER(lamc.created_at))"
    elif grouping == 'yearly':
        # cast to CHAR so period is a string
        expr = "CAST(YEAR(lamc.created_at) AS CHAR)"
    else:  # lifetime
        expr = "'Lifetime'"

    # Build SQL with join and grouping
    sql = [
        f"SELECT {expr} AS period, SUM(lamc.points) AS points",
        "FROM lifeapp.la_mission_completes lamc",
        "INNER JOIN lifeapp.la_missions lam",
        "  ON lamc.la_mission_id = lam.id",
        "  AND lam.type = 6"
    ]
    # Only add GROUP BY if not lifetime
    if grouping != 'lifetime':
        sql.append(f"GROUP BY {expr}")
        sql.append("ORDER BY period ASC")

    query = ' '.join(sql)

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

    return jsonify({ 'data': rows })

@app.route('/api/coupon-redeems-over-time', methods=['POST'])
def coupon_redeems_over_time():
    req = request.get_json() or {}
    grouping = req.get('grouping', 'monthly')

    if grouping == 'daily':
        expr = "DATE(created_at)"
    elif grouping == 'weekly':
        expr = "CONCAT(YEAR(created_at), '-', LPAD(WEEK(created_at, 1), 2, '0'))"
    elif grouping == 'monthly':
        expr = "DATE_FORMAT(created_at, '%Y-%m')"
    elif grouping == 'quarterly':
        expr = "CONCAT(YEAR(created_at), '-Q', QUARTER(created_at))"
    elif grouping == 'yearly':
        expr = "CAST(YEAR(created_at) AS CHAR)"
    else:
        expr = "'Lifetime'"

    sql_parts = [
        f"SELECT {expr} AS period, SUM(coins) AS coins",
        "FROM lifeapp.coupon_redeems"
    ]
    if grouping != 'lifetime':
        sql_parts.append(f"GROUP BY {expr}")
        sql_parts.append("ORDER BY period ASC")

    query = ' '.join(sql_parts)
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

    return jsonify({'data': rows})

@app.route('/api/get-all-states', methods=['GET'])
def get_all_states():
    """
    Returns a JSON payload with all distinct normalized_state values
    for users of type 3 (students).
    """
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT normalized_state
                FROM (
                  SELECT
                    CASE
                      WHEN state IN ('Gujrat','Gujarat') THEN 'Gujarat'
                      WHEN state IN ('Tamilnadu','Tamil Nadu') THEN 'Tamil Nadu'
                      ELSE state
                    END AS normalized_state
                  FROM lifeapp.users
                ) AS subquery
                WHERE normalized_state IS NOT NULL AND normalized_state !=2
                ORDER BY normalized_state;
            """)
            rows = cursor.fetchall()
        # Extract into a simple list of strings
        states = [row['normalized_state'] for row in rows]
        return jsonify({'states': states}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/demograph-students-2', methods=['POST'])
def get_demograph_students_2():
    """
    Returns the count of students (type = 3) in each normalized state 
    grouped by a time period derived from the created_at column.
    Accepts a JSON payload with key "grouping" (daily, weekly, monthly, quarterly, yearly, lifetime)
    """
    try:
        data = request.get_json() or {}
        grouping = data.get('grouping', 'monthly').lower()
        allowed_groupings = ['daily', 'weekly', 'monthly', 'quarterly', 'yearly', 'lifetime']
        if grouping not in allowed_groupings:
            grouping = 'monthly'
        
        # Build the period expression based on the grouping value using created_at
        if grouping == 'daily':
            period_expr = "DATE(created_at)"
        elif grouping == 'weekly':
            period_expr = "CONCAT(YEAR(created_at), '-W', WEEK(created_at, 1))"
        elif grouping == 'monthly':
            period_expr = "DATE_FORMAT(created_at, '%%Y-%%m')"
        elif grouping == 'quarterly':
            period_expr = "CONCAT(YEAR(created_at), '-Q', QUARTER(created_at))"
        elif grouping == 'yearly':
            period_expr = "YEAR(created_at)"
        else:  # lifetime grouping: all rows in one group
            period_expr = "'lifetime'"
        
        # pull out the single state filter (if any)
        state = data.get('state', '').strip()
        where_clause = "`type` = 3 AND state != 2"
        params = []
        if state:
            # only include rows where the normalized_state = the supplied state
            where_clause += """
              AND CASE
                    WHEN state IN ('Gujrat','Gujarat') THEN 'Gujarat'
                    WHEN state IN ('Tamilnadu','Tamil Nadu') THEN 'Tamil Nadu'
                    ELSE state
                  END = %s
            """
            params.append(state)

        connection = get_db_connection()
        with connection.cursor() as cursor:
            # First, group by state and created_at (so each row represents one state on a given day, week, etc.)
            # Then, in an outer query, group by the computed period and state.
            sql = f"""
                SELECT 
                    {period_expr} AS period,
                    normalized_state,
                    SUM(student_count) AS total_count
                FROM (
                    SELECT 
                        created_at,
                        CASE 
                            WHEN state IN ('Gujrat', 'Gujarat') THEN 'Gujarat'
                            WHEN state IN ('Tamilnadu', 'Tamil Nadu') THEN 'Tamil Nadu'
                            ELSE state 
                        END AS normalized_state,
                        COUNT(*) AS student_count
                    FROM lifeapp.users
                    WHERE {where_clause}
                    GROUP BY normalized_state, created_at
                ) AS subquery
                GROUP BY period, normalized_state
                ORDER BY period, total_count DESC;
            """
            cursor.execute(sql, params)
            result = cursor.fetchall()
            
            formatted_result = [
                {"period": row['period'], "state": row['normalized_state'], "count": row['total_count']}
                for row in result
            ]
        return jsonify(formatted_result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        connection.close()

@app.route('/api/demograph-teachers-2', methods=['POST'])
def get_teacher_demograph_2():
    """
    Returns count of teachers (type = 5) in each normalized state grouped by time period,
    based on the created_at column. Accepts a JSON payload with the key "grouping", which 
    can be daily, weekly, monthly, quarterly, yearly, or lifetime.
    """
    try:
        data = request.get_json() or {}
        grouping = data.get('grouping', 'monthly').lower()
        allowed_groupings = ['daily', 'weekly', 'monthly', 'quarterly', 'yearly', 'lifetime']
        if grouping not in allowed_groupings:
            grouping = 'monthly'
        
        # Build the period expression using created_at
        if grouping == 'daily':
            period_expr = "DATE(created_at)"
        elif grouping == 'weekly':
            period_expr = "CONCAT(YEAR(created_at), '-W', WEEK(created_at, 1))"
        elif grouping == 'monthly':
            period_expr = "DATE_FORMAT(created_at, '%%Y-%%m')"
        elif grouping == 'quarterly':
            period_expr = "CONCAT(YEAR(created_at), '-Q', QUARTER(created_at))"
        elif grouping == 'yearly':
            period_expr = "YEAR(created_at)"
        else:  # lifetime
            period_expr = "'lifetime'"
        
        # 2) initialize WHERE + params, then add state filter if provided
        state = data.get('state', '').strip()
        where_clause = "`type` = 5 AND state != 2"
        params = []
        if state:
            where_clause += """
              AND CASE
                    WHEN state IN ('Gujrat','Gujarat') THEN 'Gujarat'
                    WHEN state IN ('Tamilnadu','Tamil Nadu') THEN 'Tamil Nadu'
                    ELSE state
                  END = %s
            """
            params.append(state)

        connection = get_db_connection()
        with connection.cursor() as cursor:
            # First group by state and the individual created_at date, then in an outer query group by the computed period.
            sql = f"""
                SELECT 
                    {period_expr} AS period,
                    normalized_state,
                    SUM(teacher_count) AS total_count
                FROM (
                    SELECT 
                        created_at,
                        CASE 
                            WHEN state IN ('Gujrat', 'Gujarat') THEN 'Gujarat'
                            WHEN state IN ('Tamilnadu', 'Tamil Nadu') THEN 'Tamil Nadu'
                            ELSE state 
                        END AS normalized_state,
                        COUNT(*) AS teacher_count
                    FROM lifeapp.users 
                    WHERE {where_clause}
                    GROUP BY normalized_state, created_at
                ) AS subquery
                GROUP BY period, normalized_state
                ORDER BY period, total_count DESC;
            """
            cursor.execute(sql, params)
            result = cursor.fetchall()
            
            formatted_result = [
                {"period": row['period'], "state": row['normalized_state'], "count": row['total_count']}
                for row in result
            ]
            
        return jsonify(formatted_result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        connection.close()

@app.route('/api/school_count', methods = ['POST'])
def get_school_count():
    sql = """
        select count(distinct name) as count from lifeapp.schools where is_life_lab = 1 and deleted_at is null;
    """
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchall()  
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        connection.close()

@app.route('/api/quiz_completes', methods= ['POST'])
def get_quiz_completes():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = """
                select count(*) as count from lifeapp.la_quiz_games where completed_at is not null;
            """
            cursor.execute(sql)
            count = cursor.fetchall()
        return jsonify(count)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/total-missions-completed-assigned-by-teacher', methods = ['POST'])
def get_total_missions_completed_assigned_by_teacher():
    sql  = """
        SELECT count(*) as count FROM lifeapp.la_mission_assigns lama INNER JOIN lifeapp.la_mission_completes lamc 
            ON lamc.la_mission_id = lama.la_mission_id
                and lamc.user_id =lama.user_id;
    """
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchall()  
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        connection.close()

@app.route('/api/total_missions_completes', methods= ['POST'])
def get_total_missions_completes() :
    sql  = """
        select count(*) as count from lifeapp.la_mission_completes lamc inner join lifeapp.la_missions lam on lam.id = lamc.la_mission_id where lam.type = 1;
    """
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchall()  
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        connection.close()

@app.route('/api/total_jigyasa_completes', methods= ['POST'])
def get_total_jigyasa_completes() :
    sql  = """
        select count(*) as count from lifeapp.la_mission_completes lamc inner join lifeapp.la_missions lam on lam.id = lamc.la_mission_id where lam.type = 5;
    """
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchall()  
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        connection.close()

@app.route('/api/total_pragya_completes', methods= ['POST'])
def get_total_pragya_completes() :
    sql  = """
        select count(*) as count from lifeapp.la_mission_completes lamc inner join lifeapp.la_missions lam on lam.id = lamc.la_mission_id where lam.type = 6;
    """
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchall()  
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        connection.close()

@app.route('/api/total_riddle_completes', methods= ['POST'])
def get_total_riddle_completes() :
    sql  = """
        select count(*) as count from lifeapp.la_mission_completes lamc inner join lifeapp.la_missions lam on lam.id = lamc.la_mission_id where lam.type = 3;
    """
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchall()  
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        connection.close()

@app.route('/api/total_puzzle_completes', methods= ['POST'])
def get_total_puzzle_completes() :
    sql  = """
        select count(*) as count from lifeapp.la_mission_completes lamc inner join lifeapp.la_missions lam on lam.id = lamc.la_mission_id where lam.type = 4;
    """
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchall()  
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        connection.close()

@app.route('/api/total_quiz_completes', methods= ['POST'])
def get_total_quiz_completes() :
    sql = """
        select count(*) as count from lifeapp.la_quiz_game_results;
    """
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchone()['count']
        return jsonify({'count': result}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()
    
@app.route('/api/mission_participation_rate', methods=['POST'])
def get_mission_participation_rate():
    sql_total_students = """
        SELECT COUNT(*) AS count FROM lifeapp.users WHERE `type` = 3;
    """
    sql_mission_complete = """
        SELECT COUNT(DISTINCT lamc.user_id) AS count FROM lifeapp.la_mission_completes lamc inner join lifeapp.la_missions lam on lam.id = lamc.la_mission_id where lam.type = 1;
    """
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(sql_total_students)
            total_students = cursor.fetchone()['count']

            cursor.execute(sql_mission_complete)
            mission_complete_user = cursor.fetchone()['count']

            participation_rate = (mission_complete_user / total_students) * 100 if total_students > 0 else 0

        return jsonify({"participation_rate": round(participation_rate, 2)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        connection.close()

@app.route('/api/jigyasa_participation_rate', methods=['POST'])
def get_jigyasa_participation_rate():
    sql_total_students = """
        SELECT COUNT(*) AS count FROM lifeapp.users WHERE `type` = 3;
    """
    sql_jigyasa_complete = """
        SELECT COUNT(DISTINCT lamc.user_id) AS count FROM lifeapp.la_mission_completes lamc inner join lifeapp.la_missions lam on lam.id = lamc.la_mission_id where lam.type = 5;
    """
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(sql_total_students)
            total_students = cursor.fetchone()['count']

            cursor.execute(sql_jigyasa_complete)
            jigyasa_complete_user = cursor.fetchone()['count']

            participation_rate = (jigyasa_complete_user / total_students) * 100 if total_students > 0 else 0

        return jsonify({"participation_rate": round(participation_rate, 2)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        connection.close()

@app.route('/api/pragya_participation_rate', methods=['POST'])
def get_pragya_participation_rate():
    sql_total_students = """
        SELECT COUNT(*) AS count FROM lifeapp.users WHERE `type` = 3;
    """
    sql_pragya_complete = """
        SELECT COUNT(DISTINCT lamc.user_id) AS count FROM lifeapp.la_mission_completes lamc inner join lifeapp.la_missions lam on lam.id = lamc.la_mission_id where lam.type = 6;
    """
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(sql_total_students)
            total_students = cursor.fetchone()['count']

            cursor.execute(sql_pragya_complete)
            pragya_complete_user = cursor.fetchone()['count']

            participation_rate = (pragya_complete_user / total_students) * 100 if total_students > 0 else 0

        return jsonify({"participation_rate": round(participation_rate, 2)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        connection.close()

@app.route('/api/quiz_participation_rate', methods=['POST'])
def get_quiz_participation_rate():
    sql_total_students = """
        SELECT COUNT(*) AS count FROM lifeapp.users WHERE `type` = 3;
    """
    sql_quiz_complete = """
        select count(distinct user_id) as count from lifeapp.la_quiz_game_results;
    """
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(sql_total_students)
            total_students = cursor.fetchone()['count']

            cursor.execute(sql_quiz_complete)
            quiz_complete_user = cursor.fetchone()['count']

            participation_rate = (quiz_complete_user / total_students) * 100 if total_students > 0 else 0

        return jsonify({"participation_rate": round(participation_rate, 2)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        connection.close()

@app.route('/api/student-count-by-level-over-time', methods=['POST'])
def student_count_by_level_over_time():
    req = request.get_json() or {}
    grouping = req.get('grouping', 'monthly')
    selected_levels = req.get('levels', ['level1', 'level2', 'level3', 'level4'])
    
    # Level definitions based on grade ranges
    level_conditions = {
        'level1': "grade >= 1",  # Available to all students from class 1
        'level2': "grade >= 6",  # Available from class 6
        'level3': "grade >= 7",  # Available from class 7
        'level4': "grade >= 8"   # Available from class 8
    }

    # Validate and filter levels
    valid_levels = [lvl for lvl in selected_levels if lvl in level_conditions]
    if not valid_levels:
        valid_levels = ['level1', 'level2', 'level3', 'level4']

    # Build SQL CASE statements
    level_columns = []
    for level in valid_levels:
        col_name = f"{level}_count"
        condition = level_conditions[level]
        level_columns.append(
            f"SUM(CASE WHEN {condition} THEN 1 ELSE 0 END) AS {col_name}"
        )

    # Period expression mapping (same as before)
    period_expressions = {
        'daily': "DATE(created_at)",
        'weekly': "CONCAT(YEAR(created_at), '-', LPAD(WEEK(created_at, 3), 2, '0'))",
        'monthly': "DATE_FORMAT(created_at, '%Y-%m')",
        'quarterly': "CONCAT(YEAR(created_at), '-Q', QUARTER(created_at))",
        'yearly': "YEAR(created_at)",
        'lifetime': "'Lifetime'"
    }
    period_expr = period_expressions.get(grouping, "DATE_FORMAT(created_at, '%Y-%m')")

    sql = f"""
    SELECT 
        {period_expr} AS period,
        {', '.join(level_columns)}
    FROM lifeapp.users
    WHERE type = 3  # Students only
    GROUP BY period
    ORDER BY period;
    """

    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchall()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if connection:
            connection.close()
    
@app.route('/api/signing-user-gender', methods=['POST'])
def signing_user_gender():
    # Get grouping and user_type from the request; default grouping is 'monthly'
    req = request.get_json()
    grouping = req.get('grouping', 'monthly')
    user_type = req.get('user_type', 'All')  # Add the user_type parameter
    
    # Choose the SQL expression for grouping based on the given filter,
    # doubling the percent signs to escape them for the query execution.
    if grouping == 'daily':
        period_expr = "DATE(created_at)"
    elif grouping == 'weekly':
        period_expr = "CONCAT(YEAR(created_at), '-', LPAD(WEEK(created_at, 3), 2, '0'))"
    elif grouping == 'monthly':
        period_expr = "DATE_FORMAT(created_at, '%%Y-%%m')"
    elif grouping == 'quarterly':
        period_expr = "CONCAT(YEAR(created_at), '-Q', QUARTER(created_at))"
    elif grouping == 'yearly':
        period_expr = "YEAR(created_at)"
    elif grouping == 'lifetime':
        period_expr = "'Lifetime'"
    else:
        period_expr = "DATE_FORMAT(created_at, '%%Y-%%m')"
    
    # Build the base query with a WHERE clause that always evaluates to true
    where_clause = "WHERE 1=1"
    params = []
    
    # Add the user type filter if it's not 'All'
    if user_type and user_type != 'All':
        type_map = {
            'Admin': 1,
            'Student': 3,
            'Mentor': 4,
            'Teacher': 5,
            # For 'Unspecified', we capture those not matching known types or NULL.
            'Unspecified': None
        }
        if user_type in type_map:
            if user_type == 'Unspecified':
                where_clause += " AND (type NOT IN (1,3,4,5) OR type IS NULL)"
            else:
                where_clause += " AND type = %s"
                params.append(type_map[user_type])
    
    # Build the final SQL query with the user type filter in place.
    sql = f"""
        SELECT {period_expr} AS period,
               CASE
                 WHEN gender = 0 THEN 'Male'
                 WHEN gender = 1 THEN 'Female'
                 ELSE 'Unspecified'
               END as gender_label,
               COUNT(*) AS count
        FROM lifeapp.users
        {where_clause}
        GROUP BY period, gender_label
        ORDER BY period
    """
    
    db = get_db_connection()
    try:
        with db.cursor() as cursor:
            cursor.execute(sql, tuple(params))
            results = cursor.fetchall()
    finally:
        db.close()
    
    # Transform the result into an array of objects where each record is:
    # { period: ..., Male: <count>, Female: <count>, Unspecified: <count> }
    data_by_period = {}
    for row in results:
        period = row['period']
        gender = row['gender_label']
        count = row['count']
        if period not in data_by_period:
            data_by_period[period] = {'period': period, 'Male': 0, 'Female': 0, 'Unspecified': 0}
        data_by_period[period][gender] = count
    
    return jsonify({'data': list(data_by_period.values())})

@app.route('/api/PBLsubmissions', methods=['POST'])
def get_PBLsubmissions():
    payload = request.get_json() or {}
    grouping = payload.get('grouping', 'monthly')
    status = payload.get('status', 'all')

    # Mapping of grouping keys to SQL expressions
    GROUPING_SQL = {
        'daily':     "DATE(lamc.created_at)",
        'weekly':    "DATE_FORMAT(lamc.created_at, '%x-%v')",
        'monthly':   "DATE_FORMAT(lamc.created_at, '%Y-%m')",
        'quarterly': "CONCAT(YEAR(lamc.created_at), '-Q', QUARTER(lamc.created_at))",
        'yearly':    "YEAR(lamc.created_at)",
        'lifetime':  "'All Time'"
    }

    # Status filters
    STATUS_CONDITIONS = {
        'submitted': "lamc.approved_at IS NULL AND lamc.rejected_at IS NULL",
        'approved':  "lamc.approved_at IS NOT NULL",
        'rejected':  "lamc.rejected_at IS NOT NULL",
        'all':       "1"
    }

    # Validate inputs
    if grouping not in GROUPING_SQL or status not in STATUS_CONDITIONS:
        return jsonify(error='Invalid grouping or status'), 400

    period_expr = GROUPING_SQL[grouping]
    status_where = STATUS_CONDITIONS[status]

    sql = f"""
    SELECT
        {period_expr} AS period,
        COUNT(*) AS count
    FROM lifeapp.la_mission_assigns lama
    INNER JOIN lifeapp.la_missions lam
        ON lam.id = lama.la_mission_id
    INNER JOIN lifeapp.la_mission_completes lamc
        ON lama.user_id = lamc.user_id
        AND lama.la_mission_id = lamc.la_mission_id
    WHERE lam.allow_for = 2
      AND {status_where}
    GROUP BY period
    ORDER BY period;
    """

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            results = cursor.fetchall()
    finally:
        conn.close()

    return jsonify(data=results)

@app.route('/api/PBLsubmissions/total', methods=['GET'])
def get_total_PBLsubmissions():
    # Returns the total count for a given status (default 'all')
    # status = request.args.get('status', 'all')
    # if status not in STATUS_CONDITIONS:
    #     return jsonify(error='Invalid status'), 400

    # status_where = STATUS_CONDITIONS[status]
    sql = f"""
    SELECT
        COUNT(*) AS total
    FROM lifeapp.la_mission_assigns lama
    INNER JOIN lifeapp.la_missions lam
        ON lam.id = lama.la_mission_id
    INNER JOIN lifeapp.la_mission_completes lamc
        ON lama.user_id = lamc.user_id
        AND lama.la_mission_id = lamc.la_mission_id
    WHERE lam.allow_for = 2;
    """

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchone()
            total = result.get('total', 0) if result else 0
    finally:
        conn.close()

    return jsonify(total=total)
    
@app.route('/api/vision-completion-stats', methods=['GET'])
def vision_completion_stats():
    # Query params
    grouping    = request.args.get('grouping', 'daily')
    subject_id  = request.args.get('subject_id', type=int)
    assigned_by = request.args.get('assigned_by')  # 'teacher' or 'self'

    # Map grouping to SQL
    fmt_map = {
        'daily':     "DATE(a.created_at)",
        'weekly':    "DATE_FORMAT(a.created_at, '%x-%v')",
        'monthly':   "DATE_FORMAT(a.created_at, '%Y-%m')",
        'quarterly': "CONCAT(YEAR(a.created_at), '-Q', QUARTER(a.created_at))",
        'yearly':    "YEAR(a.created_at)",
        'lifetime':  "'lifetime'"
    }
    period_expr = fmt_map.get(grouping, fmt_map['daily'])

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Fetch counts grouped by period, level, subject
            sql = f"""
            SELECT
              {period_expr} AS period,
              JSON_UNQUOTE(JSON_EXTRACT(l.title, '$.en')) AS level_title,
              JSON_UNQUOTE(JSON_EXTRACT(s.title, '$.en')) AS subject_title,
              COUNT(DISTINCT a.user_id) AS user_count
            FROM vision_question_answers a
            JOIN visions v      ON v.id = a.vision_id
            JOIN la_levels l    ON l.id = v.la_level_id
            JOIN la_subjects s  ON s.id = v.la_subject_id
            LEFT JOIN vision_assigns vs
              ON vs.vision_id = a.vision_id AND vs.student_id = a.user_id
            WHERE 1=1
            """
            params = []

            if subject_id:
                sql += " AND v.la_subject_id = %s"; params.append(subject_id)
            if assigned_by == 'teacher':
                sql += " AND vs.teacher_id IS NOT NULL"
            elif assigned_by == 'self':
                sql += " AND vs.teacher_id IS NULL"

            sql += " GROUP BY period, l.title, s.title ORDER BY period"
            cursor.execute(sql, params)
            rows = cursor.fetchall()

        # Nest data per period
        data = {}
        for r in rows:
            period = r['period']
            lvl    = r['level_title']
            subj   = r['subject_title']
            cnt    = r['user_count']
            data.setdefault(period, {}).setdefault(lvl, {'count': 0, 'subjects': {}})
            data[period][lvl]['count'] += cnt
            data[period][lvl]['subjects'][subj] = cnt

        # Format array
        formatted = []
        for period, levels in data.items():
            formatted.append({
                'period': period,
                'levels': [
                    {
                      'level': lvl,
                      'count': info['count'],
                      'subjects': [{'subject': sub, 'count': c} for sub, c in info['subjects'].items()]
                    }
                    for lvl, info in levels.items()
                ]
            })
        return jsonify({'data': formatted}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        conn.close()

@app.route('/api/vision-score-stats', methods=['GET'])
def vision_score_stats():
    # Query params
    grouping = request.args.get('grouping', 'daily')  # daily, weekly, monthly, quarterly, yearly, lifetime

    # Map grouping to SQL
    fmt_map = {
        'daily':     "DATE(a.created_at)",
        'weekly':    "DATE_FORMAT(a.created_at, '%x-%v')",
        'monthly':   "DATE_FORMAT(a.created_at, '%Y-%m')",
        'quarterly': "CONCAT(YEAR(a.created_at), '-Q', QUARTER(a.created_at))",
        'yearly':    "YEAR(a.created_at)",
        'lifetime':  "'lifetime'"
    }
    period_expr = fmt_map.get(grouping, fmt_map['daily'])

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = f"""
            SELECT
              {period_expr} AS period,
              COALESCE(SUM(a.score), 0) AS total_score
            FROM vision_question_answers a
            WHERE a.score IS NOT NULL
            GROUP BY period
            ORDER BY period
            """
            cursor.execute(sql)
            rows = cursor.fetchall()

        data = [{'period': r['period'], 'total_score': r['total_score']} for r in rows]
        return jsonify({'data': data}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        conn.close()

@app.route('/api/vision-answer-summary', methods=['GET'])
def vision_answer_summary():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Total sum of scores (ignore NULLs)
            cursor.execute("SELECT COALESCE(SUM(score),0) AS total_score FROM vision_question_answers")
            total_score = cursor.fetchone()['total_score']

            # Total number of rows
            cursor.execute("SELECT COUNT(*) AS total_answers FROM vision_question_answers")
            total_answers = cursor.fetchone()['total_answers']

        return jsonify({
            'total_score': int(total_score),
            'total_vision_answers': total_answers
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        conn.close()

@app.route('/api/vision-teacher-completions-summary', methods=['GET'])
def vision_teacher_completions_summary():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Count only answers where there was a teacher assignment
            sql = '''
                SELECT COUNT(*) AS teacher_assigned_completions
                FROM lifeapp.vision_question_answers a
                JOIN lifeapp.vision_assigns vs
                  ON vs.vision_id = a.vision_id
                 AND vs.student_id = a.user_id
                WHERE vs.teacher_id IS NOT NULL
            '''
            cursor.execute(sql)
            total = cursor.fetchone()['teacher_assigned_completions']

        return jsonify({'total_teacher_assigned_completions': total}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        conn.close()
        
###################################################################################
###################################################################################
######################## STUDENT/ DASHBOARD APIs ##################################
###################################################################################
###################################################################################

@app.route('/api/state_list', methods=['GET'])
def get_state_list():
    connection = get_db_connection()
    try:
        
        with connection.cursor() as cursor:
            sql = """
                select distinct(state) from lifeapp.users where state != 'null' and state != '2';
            """
            cursor.execute(sql)
            result = cursor.fetchall()
            
            # print("Query Result:", result)  # Debugging statement
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/city_list_teachers', methods=['POST'])
def get_city_list_teachers():
    filters = request.get_json() or {}
    state = filters.get('state')
    if not state:
        return jsonify({"error": "Query param 'state' is required"}), 400
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = """
                SELECT DISTINCT city 
                FROM lifeapp.users
                WHERE state = %s 
                  AND city IS NOT NULL AND city != ''
            """
            cursor.execute(sql, (state))
            result = cursor.fetchall()
            cities = [row['city'] for row in result]
        return jsonify(cities), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        connection.close()

@app.route('/api/school_list', methods=['GET'])
def get_school_list():
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = """
                select distinct(name) from lifeapp.schools;
            """
            cursor.execute(sql)
            result = cursor.fetchall()
            
            # print("Query Result:", result)  # Debugging statement
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/new_school_list', methods=['GET'])
def get_new_school_list():
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = """
                select distinct(name), id, code from lifeapp.schools;
            """
            cursor.execute(sql)
            result = cursor.fetchall()
            
            # print("Query Result:", result)  # Debugging statement
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

# New endpoint for filtering/searching the mission completes data
@app.route('/api/student_dashboard_search', methods=['POST'])
def search():
    filters = request.get_json() or {}
    state = filters.get('state')
    school = filters.get('school')
    city = filters.get('city')
    grade = filters.get('grade')
    mission_type = filters.get('mission_type')
    mission_acceptance = filters.get('mission_acceptance')
    requested_count = filters.get('mission_requested_no')
    accepted_count = filters.get('mission_accepted_no')
    earn_coins = filters.get('earn_coins')  # Add this line
    from_date = filters.get('from_date')  # New filter: starting date
    to_date = filters.get('to_date')      # New filter: ending date
    mobile_no = filters.get('mobile_no')
    schoolCodes = filters.get('schoolCode')
    
    # Build the base query with the CTE, including mission count aggregations
    sql = """
    WITH user_mission_stats AS (
        SELECT 
            user_id,
            COUNT(*) AS total_missions_requested,
            SUM(CASE WHEN approved_at IS NOT NULL THEN 1 ELSE 0 END) AS total_missions_accepted
        FROM lifeapp.la_mission_completes
        GROUP BY user_id
    ),
    cte AS (
        SELECT 
            u.id, u.name, ls.name AS school_name, u.guardian_name, u.email, u.username, 
            u.mobile_no, u.dob, u.type AS user_type, u.grade, u.city, u.state, 
            u.address, u.earn_coins, u.heart_coins, u.brain_coins, u.school_id, u.school_code, u.created_at as registered_at, 
            ums.total_missions_requested, ums.total_missions_accepted
        FROM lifeapp.users u
        INNER JOIN lifeapp.schools ls ON ls.id = u.school_id
        LEFT JOIN user_mission_stats ums ON ums.user_id = u.id
        WHERE u.type = 3 
    """
    params = []
    
    # Append additional filter conditions if provided.
    if state:
        sql += " AND u.state = %s"
        params.append(state)
    if school:
        if isinstance(school, list):
            if len(school) == 1:
                sql += " AND ls.name = %s"
                params.append(school[0])
            else:
                sql += " AND ls.name IN %s"
                params.append(tuple(school))
        else:
            sql += " AND ls.name = %s"
            params.append(school)
    if city:
        sql += " AND u.city = %s"
        params.append(city)
    if grade:
        sql += " AND u.grade = %s"
        params.append(grade)
    if mission_type:
        sql += " AND m.type = %s"
        if mission_type == 'Mission':
            params.append(1)
        elif mission_type == 'Pragya':
            params.append(6)
        else:
            params.append(5)
    if mission_acceptance:
        if mission_acceptance == 'accepted':
            sql += " AND ums.total_missions_accepted > 0 "
        else :
            sql += " AND ums.total_missions_accepted = 0 "
    
    # Add filters for mission counts if provided
    if requested_count:
        sql += " AND ums.total_missions_requested = %s"
        params.append(int(requested_count))
    if accepted_count:
        sql += " AND ums.total_missions_accepted = %s"
        params.append(int(accepted_count))

    if earn_coins:
        if earn_coins == "0-100":
            sql += " AND u.earn_coins BETWEEN 0 AND 100"
        elif earn_coins == "101-500":
            sql += " AND u.earn_coins BETWEEN 101 AND 500"
        elif earn_coins == "501-1000":
            sql += " AND u.earn_coins BETWEEN 501 AND 1000"
        elif earn_coins == "1000+":
            sql += " AND u.earn_coins > 1000"

    if schoolCodes:
        # 1. Make sure it’s a Python list
        codes = schoolCodes if isinstance(schoolCodes, list) else [schoolCodes]

        # 2. Create “%s,%s,…,%s” with one %s per code
        placeholders = ",".join(["%s"] * len(codes))

        # 3. Inject both IN‑lists into your SQL
        sql += f"""
        AND (
            u.school_code IN ({placeholders})
        
        )
        """
        # OR u.school_id   IN ({placeholders})
        # 4a. Bind for u.school_code → cast each code to int()
        params.extend([int(c) for c in codes])

        # 4b. Bind for u.school_id   → use the raw codes (or ints if your IDs are numeric)
        # params.extend(codes)

        
    if mobile_no:
        sql+= " AND u.mobile_no = %s"
        params.append(mobile_no)
    # Add date range filters
    if from_date:
        sql += " AND u.created_at >= %s"
        params.append(from_date)
    if to_date:
        sql += " AND u.created_at <= %s"
        params.append(to_date)

    sql += " ) SELECT * FROM cte ORDER BY registered_at DESC;"
    
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(sql, tuple(params))
            result = cursor.fetchall()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/add_student', methods=['POST'])
def add_student():
    data = request.get_json() or {}

    # Basic student fields
    name         = data.get('name')
    guardian     = data.get('guardian_name')
    email        = data.get('email')
    username     = data.get('username')
    mobile_no    = data.get('mobile_no')
    dob          = data.get('dob')
    grade        = data.get('grade')
    city         = data.get('city')
    state        = data.get('state')
    school_id    = data.get('school_id')
    school_name  = data.get('school_name')
    school_code  = data.get('school_code')

    # Validate required
    if not all([name, email, username, mobile_no]):
        return jsonify({'error': 'Missing required fields'}), 400

    conn = get_db_connection()
    try:
        # If user passed school_name instead of ID, look it up
        if not school_id and school_name:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM lifeapp.schools WHERE name = %s", (school_name,))
                row = cur.fetchone()
                if not row:
                    return jsonify({'error': f"Unknown school '{school_name}'"}), 400
                school_id = row['id']

        sql = """
          INSERT INTO lifeapp.users
            (name, guardian_name, email, username, mobile_no, dob,
             grade, city, state, school_id, school_code, type, created_at)
          VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,3,NOW())
        """
        params = (
          name, guardian, email, username, mobile_no, dob,
          grade, city, state, school_id, school_code
        )
        with conn.cursor() as cur:
            cur.execute(sql, params)
            conn.commit()
            new_id = cur.lastrowid

        return jsonify({'success': True, 'id': new_id}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        conn.close()

@app.route('/api/edit_student/<int:user_id>', methods=['PUT'])
def edit_student(user_id):
    data = request.get_json() or {}
    # Fields we allow editing
    name         = data.get('name')
    guardian     = data.get('guardian_name')
    email        = data.get('email')
    username     = data.get('username')
    mobile_no    = data.get('mobile_no')
    dob          = data.get('dob')
    grade        = data.get('grade')
    city         = data.get('city')
    state        = data.get('state')
    school_id    = data.get('school_id')
    school_name  = data.get('school_name')
    school_code  = data.get('school_code')

    conn = get_db_connection()
    try:
        # resolve school_name → school_id if needed
        if not school_id and school_name:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM lifeapp.schools WHERE name = %s", (school_name,))
                row = cur.fetchone()
                if not row:
                    return jsonify({'error': f"Unknown school '{school_name}'"}), 400
                school_id = row['id']

        # Build dynamic SET clause
        updates = []
        params = []
        for field, val in [
            ('name', name), ('guardian_name', guardian),
            ('email', email), ('username', username),
            ('mobile_no', mobile_no), ('dob', dob),
            ('grade', grade), ('city', city), ('state', state),
            ('school_id', school_id), ('school_code', school_code)
        ]:
            if val is not None:
                updates.append(f"{field} = %s")
                params.append(val)
        if not updates:
            return jsonify({'error': 'No fields to update'}), 400

        sql = f"""
          UPDATE lifeapp.users
             SET {', '.join(updates)}
           WHERE id = %s
        """
        params.append(user_id)

        with conn.cursor() as cur:
            cur.execute(sql, tuple(params))
            conn.commit()

        return jsonify({'success': True}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        conn.close()

@app.route('/api/delete_student', methods=['POST'])
def delete_student():
    data = request.get_json() or {}
    user_id = data.get('id')
    if not user_id:
        return jsonify({'error': 'Missing student ID'}), 400

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM lifeapp.users WHERE id = %s", (user_id,))
            conn.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/students-by-grade', methods = ['POST'])
def get_students_by_grade():
    sql = """
        select count(*) as count, grade 
	        from lifeapp.users 
		    where `type` = 3 
            group by grade 
            order by grade;

    """
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchall()  
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        connection.close()

@app.route('/api/challenges-completed-per-mission', methods= ['POST'])
def get_challenges_completed_per_mission():
    sql = """
        select count(*) as count , lac.la_mission_id, lam.title, lev.description  
            from lifeapp.la_mission_completes lac 
                inner join lifeapp.la_missions lam 
                on 
                lam.id = lac.la_mission_id 
                inner join lifeapp.la_levels lev
                on
                lam.la_level_id = lev.id
        group by lac.la_mission_id 
        order by lac.la_mission_id;

    """
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchall()  
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        connection.close()
        
@app.route('/api/mission-status-graph', methods=['POST'])
def get_mission_status_graph():
    """
    Get mission completion statistics grouped by period and status.
    """
    try:
        filters = request.get_json() or {}
        grouping = filters.get('grouping', 'monthly')
        start_date = filters.get('start_date')
        end_date = filters.get('end_date')

        # Define date format based on grouping
        date_formats = {
            'daily': "DATE_FORMAT(created_at, '%%Y-%%m-%%d')",
            'weekly': "CONCAT(YEAR(created_at), '-', WEEK(created_at))",
            'monthly': "DATE_FORMAT(created_at, '%%Y-%%m')",
            'quarterly': "CONCAT(YEAR(created_at), '-Q', QUARTER(created_at))",
            'yearly': "CAST(YEAR(created_at) AS CHAR)",
            'lifetime': "'Lifetime'"
        }

        if grouping not in date_formats:
            return jsonify({"error": "Invalid grouping parameter"}), 400

        date_format = date_formats[grouping]

        # SQL Query for mission status breakdown
        query = f"""
            SELECT 
                {date_format} AS period,
                COUNT(*) AS count,
                CASE 
                    WHEN approved_at IS NULL AND rejected_at IS NULL THEN 'Mission Requested'
                    WHEN approved_at IS NULL AND rejected_at IS NOT NULL THEN 'Mission Rejected'
                    WHEN approved_at IS NOT NULL THEN 'Mission Approved'
                END AS mission_status
            FROM lifeapp.la_mission_completes
            WHERE 1=1
        """

        # Apply date filtering if provided
        if start_date:
            query += f" AND created_at >= '{start_date}'"
        if end_date:
            query += f" AND created_at <= '{end_date}'"

        query += """
            GROUP BY period, mission_status
            HAVING period IS NOT NULL
            ORDER BY period
        """

        result = execute_query(query)

        return jsonify({"data": result, "grouping": grouping})
    except Exception as e:
        logger.error(f"Error in get_mission_status: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/histogram_topic_level_subject_quizgames', methods=['POST'])
def get_histogram_topic_level_subject_quizgames():
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = """
                SELECT 
                    COUNT(*) AS count,
                    las.title AS subject_title,
                    lal.title AS level_title
                FROM lifeapp.la_quiz_games laqg
                INNER JOIN lifeapp.la_subjects las ON laqg.la_subject_id = las.id
                INNER JOIN lifeapp.la_topics lat ON lat.id = laqg.la_topic_id
                INNER JOIN lifeapp.la_levels lal ON lat.la_level_id = lal.id  -- use topic’s level
                WHERE las.status = 1
                GROUP BY laqg.la_subject_id, lat.la_level_id
                ORDER BY las.title, lal.title;
                """

            cursor.execute(sql)
            result = cursor.fetchall()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()


###################################################################################
###################################################################################
######################## STUDENT/ COUPON REDEEMED APIs ############################
###################################################################################
###################################################################################

@app.route('/api/coupon_titles', methods=['GET'])
def get_coupon_titles():
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT DISTINCT title FROM lifeapp.coupons ORDER BY title")
            result = cursor.fetchall()
            titles = [item['title'] for item in result]
        return jsonify(titles)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/coupon_redeem_search', methods=['POST'])
def fetch_coupon_redeem_list():
    data = request.get_json() or {}
    search = data.get('search', '')
    state = data.get('state', '')
    city = data.get('city', '')
    school = data.get('school', '')
    grade = data.get('grade', '')
    coupon_title = data.get('coupon_title', '')
    mobile = data.get('mobile', '')
    start_date = data.get('start_date', '')
    end_date = data.get('end_date', '')
    
    # Base SQL query - note the aliasing for coupon title if needed.
    sql = """
        SELECT 
            u.name AS 'Student Name', 
            ls.name AS 'School Name', 
            u.mobile_no AS 'Mobile Number', 
            u.state, 
            u.city, 
            u.grade,
            lc.title as 'Coupon Title', 
            cr.coins AS 'Coins Redeemed', 
            cr.user_id, 
            cr.created_at AS 'Coupon Redeemed Date' 
        FROM lifeapp.coupon_redeems cr 
        INNER JOIN lifeapp.users u ON u.id = cr.user_id 
        INNER JOIN lifeapp.schools ls ON ls.id = u.school_id
        INNER JOIN lifeapp.coupons lc ON lc.id = cr.coupon_id
    """
    filters = []
    params = []

    # General search filter (if provided)
    # if search:
    #     filters.append("(u.name LIKE %s OR ls.name LIKE %s OR u.state LIKE %s OR u.city LIKE %s)")
    #     params.extend([f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"])

    if search:
        search_terms = search.strip().split()
        if search_terms:
            name_conditions = []
            for term in search_terms:
                name_conditions.append("u.name LIKE %s")
                params.append(f"%{term}%")
            filters.append(f"({' AND '.join(name_conditions)})")
    # Additional filters – add only if parameter exists so that NULL or empty values do not interfere.
    if state:
        filters.append("u.state = %s")
        params.append(state)
    if city:
        filters.append("u.city = %s")
        params.append(city)
    if school:
        filters.append("ls.name = %s")
        params.append(school)

    if grade:
        filters.append("u.grade = %s")
        params.append(grade)
        
    # Add to existing filters
    if coupon_title:
        filters.append("lc.title = %s")
        params.append(coupon_title)   

    # Sanitize mobile number - remove all non-numeric characters
    sanitized_mobile = ''.join(filter(str.isdigit, mobile))

    if sanitized_mobile:
        # Use exact match if full length (adjust 10 to your mobile number length)
        if len(sanitized_mobile) == 10:
            filters.append("u.mobile_no = %s")
            params.append(sanitized_mobile)
        else:
            filters.append("u.mobile_no LIKE %s")
            params.append(f"%{sanitized_mobile}%")
        
    # Date validation
    if start_date and end_date and start_date > end_date:
        return jsonify({'error': 'Start date cannot be after end date'}), 400

    # Add date filter
    if start_date and end_date:
        filters.append("cr.created_at BETWEEN %s AND %s")
        params.extend([start_date, end_date])
    elif start_date:
        filters.append("cr.created_at >= %s")
        params.append(start_date)
    elif end_date:
        filters.append("cr.created_at <= %s")
        params.append(end_date)

    # If any filters are applied, append a WHERE clause.
    if filters:
        sql += " WHERE " + " AND ".join(filters)
        
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(sql, tuple(params))
            result = cursor.fetchall()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

###################################################################################
###################################################################################
######################## STUDENT/ MISSION APIs ####################################
###################################################################################
###################################################################################

@app.route('/api/student_mission_search', methods=['POST'])
def mission_search():
    filters = request.get_json() or {}
    mission_acceptance = filters.get('mission_acceptance')
    assigned_by = filters.get('assigned_by')
    from_date = filters.get('from_date')  # New filter: starting date
    to_date = filters.get('to_date')      # New filter: ending date
    page     = int(filters.get('page', 1))
    per_page = int(filters.get('per_page', 50))
    offset   = (page - 1) * per_page
    connection = get_db_connection()
    # Build the base query with the CTE, including mission count aggregations
    sql = """
            WITH cte AS (
                SELECT 
                    mc.id as Row_ID,
                    m.id AS Mission_ID,
                    m.title AS Mission_Title,
                    CASE 
                        WHEN ma.teacher_id IS NULL OR ma.teacher_id = u.id THEN 'Self'
                        ELSE t.name 
                    END AS Assigned_By,
                    u.id AS Student_ID,
                    u.name AS Student_Name,
                    u.school_code AS school_code,
                    s.name AS School_Name,
                    CASE 
                        WHEN mc.approved_at IS NOT NULL THEN 'Approved'
                        WHEN mc.rejected_at IS NOT NULL THEN 'Rejected'
                        ELSE 'Requested'
                    END AS Status,
                    mc.created_at AS Requested_At,
                    mc.points AS Total_Points,
                    mc.timing AS Each_Mission_Timing,
                    u.mobile_no,
                    u.dob,
                    u.grade,
                    u.city,
                    u.state,
                    u.address,
                    u.earn_coins,
                    u.heart_coins,
                    u.brain_coins,
                    mc.media_id,
                    mia.path as media_path
                FROM lifeapp.la_mission_completes mc
                LEFT JOIN lifeapp.users u ON mc.user_id = u.id
                INNER JOIN lifeapp.la_missions m 
                    ON m.id = mc.la_mission_id AND mc.user_id = u.id
                LEFT JOIN lifeapp.la_mission_assigns ma ON m.id = ma.la_mission_id
                LEFT JOIN lifeapp.users t ON ma.teacher_id = t.id
                LEFT JOIN lifeapp.schools s ON u.school_id = s.id
                LEFT JOIN lifeapp.media mia on mia.id = mc.media_id
            )
            SELECT * FROM cte
            WHERE 1=1

    """
    params = []
    
    if mission_acceptance and mission_acceptance in ("Approved", "Requested", "Rejected"):
        sql += " AND cte.Status = %s"
        params.append(mission_acceptance)

    if assigned_by:
        if assigned_by.lower() == "self":
            sql += " AND cte.Assigned_By = 'Self'"
        elif assigned_by.lower() == "teacher":
            sql += " AND cte.Assigned_By <> 'Self'"

    # Filter for creation date range
    if from_date:
        sql += " AND cte.Requested_At >= %s"
        params.append(from_date)
    if to_date:
        sql += " AND cte.Requested_At <= %s"
        params.append(to_date)

    # NEW: Add filter for School ID and Mobile No.
    schoolCodes = filters.get('school_code')
    if schoolCodes:
        # 1. Make sure it’s a Python list
        codes = schoolCodes if isinstance(schoolCodes, list) else [schoolCodes]

        # 2. Create “%s,%s,…,%s” with one %s per code
        placeholders = ",".join(["%s"] * len(codes))

        # 3. Inject both IN‑lists into your SQL
        sql += f"""
        AND (
            cte.school_code IN ({placeholders})
        
        )
        """
        # OR u.school_id   IN ({placeholders})
        # 4a. Bind for u.school_code → cast each code to int()
        params.extend([int(c) for c in codes])

        # 4b. Bind for u.school_id   → use the raw codes (or ints if your IDs are numeric)
        # params.extend(codes)
        
    mobile_no = filters.get('mobile_no')
    if mobile_no:
        sql += " AND cte.mobile_no = %s"
        params.append(mobile_no)

    # sql += " ORDER BY cte.Requested_At DESC ;"
    
    # First: get total count for pagination metadata
    count_sql = f"SELECT COUNT(*) AS total FROM ({sql}) AS sub"
    try:
      connection = get_db_connection()
      with connection.cursor() as cursor:
        cursor.execute(count_sql, tuple(params))
        total = cursor.fetchone()['total']

      # Now fetch just the one page:
      page_sql = sql + " ORDER BY cte.Requested_At DESC LIMIT %s OFFSET %s"
      page_params = params + [per_page, offset]

      with connection.cursor() as cursor:
        cursor.execute(page_sql, tuple(page_params))
        rows = cursor.fetchall()

        # build media_url as before…
        base_url = os.getenv('BASE_URL')
        for r in rows:
          r['media_url'] = f"{base_url}/{r['media_path']}" if r.get('media_path') else None

      # return both the page of data _and_ pagination info
      return jsonify({
        'data': rows,
        'pagination': {
          'total': total,
          'page': page,
          'per_page': per_page,
          'total_pages': math.ceil(total / per_page)
        }
      })

    except Exception as e:
      return jsonify({'error': str(e)}), 500
    finally:
      connection.close()

@app.route('/api/update_mission_status', methods=['POST'])
def update_mission_status():
    data = request.get_json()
    row_id = data.get('row_id')
    mission_id = data.get('mission_id')
    student_id = data.get('student_id')
    action = data.get('action')

    if not all([row_id, student_id, action]):
        return jsonify({'error': 'Missing parameters'}), 400

    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            if action == 'approve':
                sql = """
                    UPDATE lifeapp.la_mission_completes
                    SET approved_at = NOW(), rejected_at = NULL
                    WHERE id = %s AND user_id = %s
                """
            elif action == 'reject':
                sql = """
                    UPDATE lifeapp.la_mission_completes
                    SET rejected_at = NOW(), approved_at = NULL
                    WHERE id = %s AND user_id = %s
                """
            else:
                return jsonify({'error': 'Invalid action'}), 400
            
            cursor.execute(sql, (row_id, student_id))
            connection.commit()
            
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

###################################################################################
###################################################################################
######################## STUDENT/ VISION APIs ####################################
###################################################################################
###################################################################################

# 5. Fetch Vision Session Answers with Pagination & Filters
@app.route('/api/vision_sessions', methods=['GET'])
def fetch_vision_sessions():
    qs          = request.args
    page        = int(qs.get('page', 1))
    per_page    = int(qs.get('per_page', 25))
    offset      = (page - 1) * per_page
    qtype       = qs.get('question_type')
    assigned_by = qs.get('assigned_by')
    date_start  = qs.get('date_start')
    date_end    = qs.get('date_end')
    school_codes = qs.getlist('school_codes')
    status_filt = qs.get('status')   # NEW: 'requested'|'accepted'|'rejected'

    base_sql = '''
    SELECT
      a.id           AS answer_id,
      v.title        AS vision_title,
      JSON_UNQUOTE(JSON_EXTRACT(q.question, '$.en')) AS question_title,
      u.name         AS user_name,
      COALESCE(t.name,'self') AS teacher_name,
      a.answer_text,
      a.answer_option,
      m.id           AS media_id,
      m.path         AS media_path,
      a.score,
      a.answer_type,
      a.status,             -- NEW
      a.approved_at,        -- NEW
      a.rejected_at,        -- NEW
      a.created_at
    FROM vision_question_answers a
    JOIN visions v          ON v.id = a.vision_id
    JOIN vision_questions q ON q.id = a.question_id
    JOIN users u            ON u.id = a.user_id
    LEFT JOIN vision_assigns vs 
      ON vs.vision_id = a.vision_id 
     AND vs.student_id = a.user_id
    LEFT JOIN users t       ON t.id = vs.teacher_id
    LEFT JOIN media m       ON m.id = a.media_id
    LEFT JOIN lifeapp.schools s ON s.id = u.school_id
    WHERE 1=1
    '''
    params = []

    if qtype:
        base_sql += ' AND a.answer_type = %s';    params.append(qtype)
    if assigned_by=='teacher':
        base_sql += ' AND vs.teacher_id IS NOT NULL'
    elif assigned_by=='self':
        base_sql += ' AND vs.teacher_id IS NULL'
    if date_start:
        base_sql += ' AND DATE(a.created_at) >= %s'; params.append(date_start)
    if date_end:
        base_sql += ' AND DATE(a.created_at) <= %s'; params.append(date_end)
    if school_codes:
        ph = ','.join(['%s']*len(school_codes))
        base_sql += f' AND u.school_code IN ({ph})'; params += school_codes

    # NEW: filter by status column
    if status_filt in ('requested','accepted','rejected'):
        base_sql += ' AND a.status = %s'; params.append(status_filt)

    base_sql += ' ORDER BY a.created_at DESC LIMIT %s OFFSET %s'
    params += [per_page, offset]

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(base_sql, params)
            rows = cursor.fetchall()

        base_url = os.getenv('BASE_URL','').rstrip('/')
        for r in rows:
            r['media_url'] = f"{base_url}/{r['media_path']}" if r.get('media_path') else None

        return jsonify({
            'page': page,
            'per_page': per_page,
            'data': rows
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# 6. Update Score Endpoint
@app.route('/api/vision_sessions/<int:answer_id>/score', methods=['PUT'])
def update_vision_session_score(answer_id):
    data = request.get_json() or {}
    if 'score' not in data:
        return jsonify({'error': 'Missing score'}), 400
    score = data['score']

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE vision_question_answers SET score = %s, updated_at = NOW() WHERE id = %s",
                (score, answer_id)
            )
            conn.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/vision_sessions/<int:answer_id>/status', methods=['PUT'])
def update_vision_session_status(answer_id):
    data = request.get_json() or {}
    new_status = data.get('status')
    if new_status not in ('accepted','rejected'):
        return jsonify({'error':'Invalid status'}), 400

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if new_status == 'accepted':
        sql = "UPDATE vision_question_answers SET status=%s, approved_at=%s WHERE id=%s"
        params = (new_status, now, answer_id)
    else:  # rejected
        sql = "UPDATE vision_question_answers SET status=%s, rejected_at=%s WHERE id=%s"
        params = (new_status, now, answer_id)

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            conn.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

###################################################################################
###################################################################################
######################## STUDENT/ QUIZ SESSIONS APIs ##############################
###################################################################################
###################################################################################

@app.route('/api/quiz_sessions', methods=['POST'])
def get_quiz_sessions():
    data = request.get_json() or {}
    start_date = data.get('start_date')
    end_date   = data.get('end_date')
    la_subject_id  = data.get('la_subject_id')
    la_level_id    = data.get('la_level_id')
    la_topic_id    = data.get('la_topic_id')

    # ── Pagination params ──
    try:
        page     = max(int(data.get('page', 1)), 1)
        per_page = min(int(data.get('per_page', 50)), 200)  # cap at 200
    except (ValueError, TypeError):
        page, per_page = 1, 50
    offset = (page - 1) * per_page

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # base query with filters
            base_sql = """
                SELECT 
                    laqg.id,
                    laqg.user_id,
                    laqg.game_code     AS game_id,
                    las.title          AS subject_title,
                    lal.title          AS level_title,
                    lat.title          AS topic_title,
                    laqg.time          AS time_taken,
                    laqgr.total_questions,
                    laqgr.total_correct_answers,
                    laqgr.created_at,
                    laqgr.coins,
                    u.name             AS user_name,
                    ls.name            AS school_name,
                    u.earn_coins,
                    u.heart_coins,
                    u.brain_coins
                FROM lifeapp.la_quiz_games laqg
                INNER JOIN lifeapp.la_quiz_game_results laqgr 
                    ON laqg.game_code = laqgr.la_quiz_game_id
                    AND laqg.user_id   = laqgr.user_id
                INNER JOIN lifeapp.users u 
                    ON u.id = laqg.user_id
                INNER JOIN lifeapp.la_subjects las 
                    ON las.id = laqg.la_subject_id
                INNER JOIN lifeapp.la_levels lal 
                    ON lal.id = laqg.la_level_id
                INNER JOIN lifeapp.la_topics lat 
                    ON lat.id = laqg.la_topic_id
                INNER JOIN lifeapp.schools ls 
                    ON ls.id = u.school_id
                WHERE 1=1
            """
            params = []

            if start_date:
                base_sql += " AND laqgr.created_at >= %s"
                params.append(start_date)
            if end_date:
                base_sql += " AND laqgr.created_at <= %s"
                params.append(end_date)

            if la_subject_id:
                base_sql += " AND laqg.la_subject_id = %s"
                params.append(la_subject_id)
            if la_level_id:
                base_sql += " AND laqg.la_level_id = %s"
                params.append(la_level_id)
            if la_topic_id:
                base_sql += " AND laqg.la_topic_id = %s"
                params.append(la_topic_id)
            # 1) total count
            count_sql = f"SELECT COUNT(*) AS total FROM ({base_sql}) AS sub"
            cursor.execute(count_sql, tuple(params))
            total = cursor.fetchone()['total']
            
            # 2) unique users
            user_sql = f"""
                SELECT COUNT(DISTINCT laqg.user_id) AS unique_user_count
                FROM lifeapp.la_quiz_games laqg
                INNER JOIN lifeapp.la_quiz_game_results laqgr
                    ON laqg.game_code = laqgr.la_quiz_game_id
                    AND laqg.user_id   = laqgr.user_id
                INNER JOIN lifeapp.users u
                    ON u.id = laqg.user_id
                WHERE 1=1
                { ' AND laqgr.created_at >= %s' if start_date else '' }
                { ' AND laqgr.created_at <= %s' if end_date else '' }
                { ' AND laqg.la_subject_id = %s' if la_subject_id else '' }
                { ' AND laqg.la_level_id = %s' if la_level_id else '' }
                { ' AND laqg.la_topic_id = %s' if la_topic_id else '' }
            """
            cursor.execute(user_sql, tuple(params))
            unique_user_count = cursor.fetchone()['unique_user_count']

            # 3) unique schools
            school_sql = f"""
                SELECT COUNT(DISTINCT u.school_id) AS unique_school_count
                FROM lifeapp.la_quiz_games laqg
                INNER JOIN lifeapp.la_quiz_game_results laqgr
                    ON laqg.game_code = laqgr.la_quiz_game_id
                    AND laqg.user_id   = laqgr.user_id
                INNER JOIN lifeapp.users u
                    ON u.id = laqg.user_id
                WHERE 1=1
                { ' AND laqgr.created_at >= %s' if start_date else '' }
                { ' AND laqgr.created_at <= %s' if end_date else '' }
                { ' AND laqg.la_subject_id = %s' if la_subject_id else '' }
                { ' AND laqg.la_level_id = %s' if la_level_id else '' }
                { ' AND laqg.la_topic_id = %s' if la_topic_id else '' }
            """
            cursor.execute(school_sql, tuple(params))
            unique_school_count = cursor.fetchone()['unique_school_count']


            # 2) page of results
            page_sql = base_sql + " ORDER BY laqgr.created_at DESC LIMIT %s OFFSET %s"
            cursor.execute(page_sql, tuple(params) + (per_page, offset))
            rows = cursor.fetchall()

        return jsonify({
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": math.ceil(total / per_page),
            "unique_user_count": unique_user_count,
            "unique_school_count": unique_school_count,
            "data": rows
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        connection.close()

        
@app.route('/api/game_questions', methods=['POST'])
def get_game_questions():
    try:
        data = request.get_json()
        game_code = data.get("game_code")

        connection = get_db_connection()
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            sql = """
            WITH RECURSIVE split_questions AS (
                SELECT 
                    game_code,
                    TRIM(BOTH '[]' FROM questions) AS cleaned_questions,
                    1 AS pos,
                    SUBSTRING_INDEX(TRIM(BOTH '[]' FROM questions), ',', 1) AS question_id,
                    SUBSTRING(TRIM(BOTH '[]' FROM questions), LENGTH(SUBSTRING_INDEX(TRIM(BOTH '[]' FROM questions), ',', 1)) + 2) AS remaining
                FROM lifeapp.la_quiz_games
                WHERE questions != '0' AND game_code = %s

                UNION ALL

                SELECT 
                    game_code,
                    cleaned_questions,
                    pos + 1,
                    SUBSTRING_INDEX(remaining, ',', 1),
                    SUBSTRING(remaining, LENGTH(SUBSTRING_INDEX(remaining, ',', 1)) + 2)
                FROM split_questions
                WHERE remaining != ''
            )

            SELECT 
                sq.game_code,
                laq.id AS question_id,
                laq.title AS question_title,
                laq.la_level_id,
                laq.la_topic_id,
                CASE 
                    WHEN laq.type = 2 THEN 'Quiz'
                    WHEN laq.type = 3 THEN 'Riddle'
                    WHEN laq.type = 4 THEN 'Puzzle'
                    ELSE 'Default'
                END AS game_type,
                CASE
                    WHEN laq.question_type = 1 THEN 'Text'
                    WHEN laq.question_type = 2 THEN 'Image'
                    ELSE 'Default'
                END AS question_type,
                CASE
                    WHEN laq.answer_option_id = laqo.id THEN 1
                    ELSE 0
                END AS is_answer,
                laqo.title AS answer_option
            FROM split_questions sq
            INNER JOIN lifeapp.la_questions laq ON laq.id = CAST(TRIM(sq.question_id) AS UNSIGNED)
            INNER JOIN lifeapp.la_question_options laqo ON laq.id = laqo.question_id
            ORDER BY sq.game_code, sq.pos;
            """
            cursor.execute(sql, (game_code,))
            questions = cursor.fetchall()

        return jsonify(questions), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/game_questions_with_answers', methods=['POST'])
def get_game_questions_with_answers():
    try:
        data = request.get_json()
        game_id = data.get("game_id")
        user_id = data.get("user_id")

        connection = get_db_connection()
        with connection.cursor(pymysql.cursors.DictCursor) as cursor:
            sql = """
            WITH RECURSIVE split_questions AS (
                SELECT 
                    game_code,
                    TRIM(BOTH '[]' FROM questions) AS cleaned_questions,
                    1 AS pos,
                    SUBSTRING_INDEX(TRIM(BOTH '[]' FROM questions), ',', 1) AS question_id,
                    SUBSTRING(TRIM(BOTH '[]' FROM questions), LENGTH(SUBSTRING_INDEX(TRIM(BOTH '[]' FROM questions), ',', 1)) + 2) AS remaining
                FROM lifeapp.la_quiz_games
                WHERE questions != '0' AND game_code = %s

                UNION ALL

                SELECT 
                    game_code,
                    cleaned_questions,
                    pos + 1,
                    SUBSTRING_INDEX(remaining, ',', 1),
                    SUBSTRING(remaining, LENGTH(SUBSTRING_INDEX(remaining, ',', 1)) + 2)
                FROM split_questions
                WHERE remaining != ''
            )

            SELECT 
                sq.pos                                  AS question_position,
                sq.question_id                          AS question_id,
                laq.title                               AS question_title,
                laqo.id                                 AS option_id,
                laqo.title                              AS option_text,
                laqo.id = laq.answer_option_id          AS is_correct_option,
                ans.la_question_option_id = laqo.id     AS selected_by_user,
                COALESCE(ans.is_correct, 0)             AS user_is_correct,
                ans.coins                               AS coins_awarded
            FROM split_questions sq
            JOIN lifeapp.la_questions laq 
              ON laq.id = CAST(TRIM(sq.question_id) AS UNSIGNED)
            JOIN lifeapp.la_question_options laqo 
              ON laq.id = laqo.question_id
            LEFT JOIN lifeapp.la_quiz_game_question_answers ans
              ON ans.la_quiz_game_id = %s
             AND ans.user_id = %s
             AND ans.la_question_id = laq.id
            ORDER BY sq.pos, laqo.id;
            """
            cursor.execute(sql, (game_id, game_id, user_id))
            rows = cursor.fetchall()

        return jsonify(rows), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()


# @app.route('/api/quiz_sessions', methods=['POST'])
# def get_quiz_sessions():
#     try:
#         data = request.get_json()
#         page = int(data.get('page', 1))
#         limit = int(data.get('limit', 10))
#         offset = (page - 1) * limit

#         connection = get_db_connection()
#         with connection.cursor() as cursor:
#             # Main paginated data
#             cursor.execute(f"""
#                 WITH sessionized_data AS (
#                     SELECT 
#                         *,
#                         @session_group := CASE 
#                             WHEN TIMESTAMPDIFF(SECOND, @prev_created_at, created_at) > 5 
#                                  OR @prev_user_id != user_id 
#                                  OR @prev_game_id != la_quiz_game_id 
#                             THEN @session_group + 1 
#                             ELSE @session_group 
#                         END AS session_group,
#                         @prev_created_at := created_at,
#                         @prev_user_id := user_id,
#                         @prev_game_id := la_quiz_game_id
#                     FROM 
#                         lifeapp.la_quiz_game_results,
#                         (SELECT @prev_created_at := NULL, @prev_user_id := NULL, @prev_game_id := NULL, @session_group := 0) vars
#                     ORDER BY 
#                         user_id, la_quiz_game_id, created_at
#                 ),
#                 ranked_entries AS (
#                     SELECT 
#                         *,
#                         ROW_NUMBER() OVER (
#                             PARTITION BY user_id, la_quiz_game_id, session_group 
#                             ORDER BY created_at
#                         ) AS session_rank
#                     FROM sessionized_data
#                 )
#                 SELECT 
#                     id,
#                     la_quiz_game_id,
#                     user_id,
#                     total_questions,
#                     total_correct_answers,
#                     coins,
#                     created_at,
#                     updated_at
#                 FROM ranked_entries
#                 WHERE session_rank = 1
#                 ORDER BY user_id, la_quiz_game_id, created_at
#                 LIMIT %s OFFSET %s;
#             """, (limit, offset))
#             results = cursor.fetchall()

#             # Total count of grouped sessions
#             cursor.execute("""
#                 WITH sessionized_data AS (
#                     SELECT 
#                         *,
#                         @session_group := CASE 
#                             WHEN TIMESTAMPDIFF(SECOND, @prev_created_at, created_at) > 5 
#                                  OR @prev_user_id != user_id 
#                                  OR @prev_game_id != la_quiz_game_id 
#                             THEN @session_group + 1 
#                             ELSE @session_group 
#                         END AS session_group,
#                         @prev_created_at := created_at,
#                         @prev_user_id := user_id,
#                         @prev_game_id := la_quiz_game_id
#                     FROM 
#                         lifeapp.la_quiz_game_results,
#                         (SELECT @prev_created_at := NULL, @prev_user_id := NULL, @prev_game_id := NULL, @session_group := 0) vars
#                     ORDER BY 
#                         user_id, la_quiz_game_id, created_at
#                 ),
#                 ranked_entries AS (
#                     SELECT 
#                         *,
#                         ROW_NUMBER() OVER (
#                             PARTITION BY user_id, la_quiz_game_id, session_group 
#                             ORDER BY created_at
#                         ) AS session_rank
#                     FROM sessionized_data
#                 )
#                 SELECT COUNT(*) AS total FROM ranked_entries WHERE session_rank = 1;
#             """)
#             total = cursor.fetchone()['total']

#         return jsonify({'data': results, 'total': total}), 200

#     except Exception as e:
#         return jsonify({'error': str(e)}), 500
#     finally:
#         connection.close()


###################################################################################
###################################################################################
######################## TEACHER / DASHBOARD APIs #################################
###################################################################################
###################################################################################

@app.route('/api/state_list_teachers', methods=['GET'])
def get_state_list_teachers():
    connection = get_db_connection()
    try:
        
        with connection.cursor() as cursor:
            sql = """
                select distinct(state) from lifeapp.users where state != 'null' and state != '2';
            """
            cursor.execute(sql)
            result = cursor.fetchall()
            
            # print("Query Result:", result)  # Debugging statement
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/city_list', methods=['GET'])
def get_city_list():
    state = request.args.get('state')
    if not state:
        return jsonify({"error": "Query param 'state' is required"}), 400
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = """
                SELECT DISTINCT city 
                FROM lifeapp.schools
                WHERE state = %s 
                  AND deleted_at IS NULL
                  AND city IS NOT NULL AND city != ''
            """
            cursor.execute(sql, (state,))
            result = cursor.fetchall()
            cities = [row['city'] for row in result]
        return jsonify(cities), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        connection.close()

@app.route('/api/teacher_schools', methods = ['POST'])
def get_teacher_states():
    sql = """
        select distinct ls.name as school from lifeapp.schools ls inner join lifeapp.users u on u.school_id = ls.id where u.type = 5;
    """
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchall()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/teacher_dashboard_search', methods=['POST'])
def fetch_teacher_dashboard():
    filters = request.get_json() or {}
    state = filters.get('state')
    city = filters.get('city')
    is_life_lab = filters.get('is_life_lab')
    school = filters.get('school')
    from_date = filters.get('from_date')  # Starting date filter
    to_date = filters.get('to_date')      # Ending date filter
    # New filters for teacher subject and grade:
    teacher_subject = filters.get('teacher_subject')
    teacher_grade = filters.get('teacher_grade')
    board = filters.get('board')
    # Start with base SQL. We join to la_teacher_grades (ltg), la_grades (lgr), and la_sections (lsct)
    sql = """
        WITH cte AS (
            SELECT count(*) as mission_assign_count, teacher_id 
            FROM lifeapp.la_mission_assigns 
            GROUP BY teacher_id
        )
        SELECT 
            u.id, u.name, u.email,
            u.mobile_no, u.state, 
            u.city, ls.name as school_name, u.school_code, 
            cte.mission_assign_count,
            CASE 
                WHEN ls.is_life_lab = 1 THEN 'Yes' 
                ELSE 'No' 
            END AS is_life_lab,
            u.created_at, u.updated_at,
            las.title,
            lgr.name as grade_name, 
            lsct.name as section_name,
            lab.name as board_name
        FROM lifeapp.users u
        INNER JOIN lifeapp.schools ls ON ls.id = u.school_id
        LEFT JOIN cte ON cte.teacher_id = u.id
        LEFT JOIN lifeapp.la_teacher_grades ltg ON ltg.user_id = u.id
        LEFT JOIN lifeapp.la_subjects las on las.id = ltg.la_subject_id
        LEFT JOIN lifeapp.la_grades lgr ON ltg.la_grade_id = lgr.id
        LEFT JOIN lifeapp.la_sections lsct ON ltg.la_section_id = lsct.id
        LEFT JOIN lifeapp.la_boards lab on u.la_board_id = lab.id
        WHERE u.type = 5
    """
    params = []
    
    if state and state.strip():
        sql += " AND u.state = %s"
        params.append(state)
    # NEW: Add filter for School ID and Mobile No.
    schoolCodes = filters.get('school_code')
    if schoolCodes:
        # 1. Make sure it’s a Python list
        codes = schoolCodes if isinstance(schoolCodes, list) else [schoolCodes]

        # 2. Create “%s,%s,…,%s” with one %s per code
        placeholders = ",".join(["%s"] * len(codes))

        # 3. Inject both IN‑lists into your SQL
        sql += f"""
        AND (
            u.school_code IN ({placeholders})
        
        )
        """
        # OR u.school_id   IN ({placeholders})
        # 4a. Bind for u.school_code → cast each code to int()
        params.extend([int(c) for c in codes])

        # 4b. Bind for u.school_id   → use the raw codes (or ints if your IDs are numeric)
        # params.extend(codes)

    if city and city.strip():
        sql += " AND u.city = %s"
        params.append(city)
    if is_life_lab:
        if is_life_lab == "Yes":
            sql += " AND ls.is_life_lab = 1"
        elif is_life_lab == "No":
            sql += " AND ls.is_life_lab = 0"
    if school:
        sql += " AND ls.name = %s"
        params.append(school)
    if teacher_subject:
        # Filter by teacher subject using la_teacher_grades table join.
        sql += " AND ltg.la_subject_id = %s"
        params.append(teacher_subject)
    if teacher_grade:
        # Filter by teacher grade using la_teacher_grades and la_grades join.
        sql += " AND ltg.la_grade_id = %s"
        params.append(int(teacher_grade))
    if from_date:
        sql += " AND u.created_at >= %s"
        params.append(from_date)
    if to_date:
        sql += " AND u.created_at <= %s"
        params.append(to_date)
    if board and board.strip():
        sql += " AND lab.id = %s"
        params.append(board)
    sql += " ORDER by u.id DESC"
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(sql, tuple(params))
            result = cursor.fetchall()
        return jsonify(result if result else [])
    except Exception as e:
        print("Error in teacher_dashboard_search:", str(e))
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/teachers-by-grade', methods = ['POST'])
def get_teachers_by_grade() :
    sql= """
        select count(distinct user_id) as count, la_grade_id as grade 
            from lifeapp.la_teacher_grades 
            group by la_grade_id 
            order by la_grade_id;

    """
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchall()  
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        connection.close()

@app.route('/api/teachers-by-grade-subject-section', methods=['POST'])
def teachers_by_grade_subject_section():
    """
    Returns teacher counts broken down by grade, subject, section, and board.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT 
                   lgr.id   AS grade_id,
                   lgr.name AS grade_name,
                   las.id   AS subject_id,
                   las.title,
                   lsct.id  AS section_id,
                   lsct.name AS section_name,
                   lab.id   AS board_id,
                   lab.name AS board_name,
                   COUNT(u.id) AS count
                FROM lifeapp.users u
                LEFT JOIN lifeapp.la_teacher_grades ltg ON ltg.user_id        = u.id
                LEFT JOIN lifeapp.la_grades         lgr ON ltg.la_grade_id    = lgr.id
                LEFT JOIN lifeapp.la_subjects       las ON las.id             = ltg.la_subject_id
                LEFT JOIN lifeapp.la_sections       lsct ON lsct.id            = ltg.la_section_id
                LEFT JOIN lifeapp.la_boards         lab ON u.la_board_id       = lab.id
                WHERE u.type = 5
                  AND las.status = 1
                GROUP BY lgr.id, las.id, lsct.id, lab.id
                ORDER BY lgr.id, las.id, lsct.id, lab.id;
            """
            cursor.execute(sql)
            rows = cursor.fetchall()

            # decode JSON titles into plain text
            for r in rows:
                try:
                    title_obj = json.loads(r['title'])
                    r['subject'] = title_obj.get('en', title_obj)
                except Exception:
                    r['subject'] = r['title']

            result = []
            for r in rows:
                result.append({
                    'grade':   r['grade_id'],
                    'subject': r['subject'],
                    'section': r['section_name'],
                    'board':   r['board_name'] or 'Unspecified',
                    'count':   r['count']
                })

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        conn.close()

@app.route('/api/add_teacher', methods=['POST'])
def add_teacher():
    """
    Expects a JSON payload with teacher details.
    Example payload:
    {
        "name": "John Doe",
        "email": "john@example.com",
        "mobile_no": "9876543210",
        "state": "SomeState",
        "city": "SomeCity",
        "school_id": "1234",
        "school_code" : "3467",
        "teacher_subject": "1",       # subject id (as string or number)
        "teacher_grade": "3",         # grade number (as string, will be converted)
        "teacher_section": "3"        # section id
        "teacher_board" : "2"         # board id
    }
    Inserts a new teacher record (with u.type = 5) in lifeapp.users using
    the current datetime for created_at and updated_at, and if teacher_subject, teacher_grade,
    and teacher_section are provided, inserts an entry into la_teacher_grades.
    """
    data = request.get_json() or {}
    try:
        name = data.get("name")
        email = data.get("email")
        mobile_no = data.get("mobile_no")
        state = data.get("state")
        city = data.get("city")
        school_id = data.get("school_id")
        school_code = data.get('school_code')
        
        # New fields for teacher_grade details:
        teacher_subject = data.get("teacher_subject")
        teacher_grade = data.get("teacher_grade")
        teacher_section = data.get("teacher_section")
        teacher_board = data.get('teacher_board')
        # Basic validation
        if not name or not mobile_no or not school_id:
            return jsonify({"error": "Name, mobile_no, and school_id are required"}), 400

        # Use datetime.now() with the desired format
        datetime_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        connection = get_db_connection()
        with connection:
            with connection.cursor() as cursor:
                # Insert teacher record into lifeapp.users (u.type = 5 for teachers)
                sql = """
                INSERT INTO lifeapp.users
                (name, email, mobile_no, state, city, school_id, school_code, type, la_section_id, la_grade_id, la_board_id, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 5, %s,%s, %s, NOW(), NOW())
                """
                params = (name, email, mobile_no, state, city, school_id, school_code, teacher_section, teacher_grade, teacher_board)
                cursor.execute(sql, params)
                teacher_id = cursor.lastrowid

                # If teacher_subject, teacher_grade and teacher_section are provided, insert into la_teacher_grades.
                if teacher_subject and teacher_grade and teacher_section:
                    sql2 = """
                    INSERT INTO lifeapp.la_teacher_grades
                    (user_id, la_subject_id, la_grade_id, la_section_id, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    params2 = (
                        teacher_id, 
                        teacher_subject, 
                        int(teacher_grade), 
                        teacher_section, 
                        datetime_str, 
                        datetime_str
                    )
                    cursor.execute(sql2, params2)
                connection.commit()
        return jsonify({"message": "Teacher added successfully", "id": teacher_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/teacher_update', methods=['POST'])
def update_teacher():
    """
    Expects a JSON payload:
    {
      "id": 43253,
      "name": "Updated Name",
      "email": "updated@example.com",
      "mobile_no": "9876543210",
      "state": "NewState",
      "city": "NewCity",
      "school_id": "1234",
      "school_code" : "3467",
      "teacher_subject": "1",      # subject id
      "teacher_grade": "3",        # grade (will be converted to int)
      "teacher_section": "3"        # section id
       "teacher_board" : "2"         # board id
    }
    
    Updates the teacher (users.type = 5) record and then
    updates or inserts into la_teacher_grades.
    """
    data = request.get_json() or {}
    try:
        teacher_id = data.get("id")
        if not teacher_id:
            return jsonify({"error": "Teacher id is required."}), 400

        # Extract updated teacher fields
        name = data.get("name")
        email = data.get("email")
        mobile_no = data.get("mobile_no")
        state = data.get("state")
        city = data.get("city")
        school_id = data.get("school_id")
        school_code = data.get('school_code')

        teacher_subject = data.get("teacher_subject")
        teacher_grade = data.get("teacher_grade")
        teacher_section = data.get("teacher_section")
        teacher_board = data.get('teacher_board')

        # Use current datetime for updates
        datetime_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        connection = get_db_connection()
        with connection:
            with connection.cursor() as cursor:
                # Update the teacher record in users
                sql = """
                UPDATE lifeapp.users
                SET name = %s, email = %s, mobile_no = %s, state = %s, city = %s, school_id = %s, school_code = %s, la_section_id =%s , la_grade_id = %s, la_board_id = %s,  updated_at = %s
                WHERE id = %s AND type = 5
                """
                params = (name, email, mobile_no, state, city, school_id, school_code, teacher_section, teacher_grade, teacher_board, datetime_str, teacher_id)
                cursor.execute(sql, params)
                
                # Update the la_teacher_grades record if grade-related fields are provided.
                if teacher_subject and teacher_grade and teacher_section:
                    # Check if a record already exists for this teacher
                    cursor.execute("SELECT id FROM lifeapp.la_teacher_grades WHERE user_id = %s", (teacher_id,))
                    existing = cursor.fetchone()
                    if existing:
                        # Update the existing record
                        sql2 = """
                        UPDATE lifeapp.la_teacher_grades
                        SET la_subject_id = %s, la_grade_id = %s, la_section_id = %s, updated_at = %s
                        WHERE user_id = %s
                        """
                        params2 = (teacher_subject, int(teacher_grade), teacher_section, datetime_str, teacher_id)
                        cursor.execute(sql2, params2)
                    else:
                        # Insert a new record if none exists
                        sql2 = """
                        INSERT INTO lifeapp.la_teacher_grades
                        (user_id, la_subject_id, la_grade_id, la_section_id, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """
                        params2 = (teacher_id, teacher_subject, int(teacher_grade), teacher_section, datetime_str, datetime_str)
                        cursor.execute(sql2, params2)
                connection.commit()
        return jsonify({"message": "Teacher updated successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/teacher_delete', methods=['POST'])
def delete_teacher():
    """
    Expects a JSON payload:
    {
      "id": 43253
    }
    Deletes the teacher from lifeapp.users (type 5) and optionally its record from la_teacher_grades.
    """
    data = request.get_json() or {}
    try:
        teacher_id = data.get("id")
        if not teacher_id:
            return jsonify({"error": "Teacher id is required."}), 400
        
        connection = get_db_connection()
        with connection:
            with connection.cursor() as cursor:
                # Delete from la_teacher_grades first if exists.
                sql2 = "DELETE FROM lifeapp.la_teacher_grades WHERE user_id = %s"
                cursor.execute(sql2, (teacher_id,))
                
                # Delete from users table
                sql = "DELETE FROM lifeapp.users WHERE id = %s AND type = 5"
                cursor.execute(sql, (teacher_id,))
                connection.commit()
        return jsonify({"message": "Teacher deleted successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/grades_list', methods=['POST'])
def get_grades_list():
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Fetch active grades from the la_grades table
            sql = """
                SELECT id, name, status, created_at, updated_at
                FROM lifeapp.la_grades
                WHERE status = 1
            """
            cursor.execute(sql)
            result = cursor.fetchall()
        return jsonify(result)
    except Exception as e:
        print("Error in get_grades_list:", str(e))
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/vision-teacher-completion-rate', methods=['GET'])
def vision_teacher_completion_rate():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # Total number of visions assigned by teachers
            cursor.execute(
                "SELECT COUNT(*) AS total_assigned FROM vision_assigns WHERE teacher_id IS NOT NULL"
            )
            total_assigned = cursor.fetchone()['total_assigned'] or 0

            # Count how many of these assignments have at least one answer (i.e., completed)
            cursor.execute(
                '''
                SELECT COUNT(DISTINCT a.vision_id, a.user_id) AS completed_count
                FROM vision_question_answers a
                JOIN vision_assigns vs
                  ON vs.vision_id = a.vision_id
                 AND vs.student_id = a.user_id
                WHERE vs.teacher_id IS NOT NULL
                '''
            )
            completed_count = cursor.fetchone()['completed_count'] or 0

        # Calculate percentage
        percentage = (completed_count / total_assigned * 100) if total_assigned > 0 else 0
        return jsonify({
            'total_assigned': total_assigned,
            'completed_count': completed_count,
            'percentage': round(percentage, 2)
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        conn.close()

###################################################################################
###################################################################################
######################## TEACHER / CONCEPT CARTOON APIs ###########################
###################################################################################
###################################################################################

@app.route('/api/teacher_concept_cartoons', methods=['POST'])
def fetch_teacher_concept_cartoons():
    filters = request.get_json() or {}
    subject = filters.get('subject')
    status = filters.get('status')

    # Start with base SQL without WHERE clause
    sql = """
            SELECT
                h.id,
                CASE WHEN h.la_subject_id = 1 THEN 'Science'
                    WHEN h.la_subject_id = 2 THEN 'Maths' END AS la_subject,
                h.la_level_id,
                h.title,
                h.document AS media_id,
                m.path          AS media_path,
                CASE WHEN h.status = 1 THEN 'Published' ELSE 'Drafted' END AS status
            FROM lifeapp.la_concept_cartoons h
            LEFT JOIN lifeapp.media m ON m.id = h.document
        """
    params = []
    conditions = []
    if subject:
        conditions.append("CASE WHEN h.la_subject_id=1 THEN 'Science' WHEN h.la_subject_id=2 THEN 'Maths' END = %s")
        params.append(subject)
    if status:
        conditions.append("CASE WHEN h.status=1 THEN 'Published' ELSE 'Drafted' END = %s")
        params.append(status)
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += ";"

    try:
        conn = get_db_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()

        base_url = os.getenv('BASE_URL')
        for r in rows:
            r['media_url'] = f"{base_url}/{r['media_path']}" if r.get('media_path') else None
        return jsonify(rows), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/update_concept_cartoon', methods=['POST'])
def update_concept_cartoon():
    form = request.form
    file = request.files.get('media')
    media_id = None

    # If there’s a new file, upload it first
    if file and file.filename:
        media = upload_media(file)
        media_id = media['id']

    # Build SQL & params in the right order
    if media_id:
        sql = """
            UPDATE lifeapp.la_concept_cartoons
            SET la_subject_id = %s,
                la_level_id   = %s,
                title         = %s,
                status        = %s,
                document      = %s,
                updated_at    = NOW()
            WHERE id = %s
        """
        params = [
            form.get('la_subject_id'),
            form.get('la_level_id'),
            form.get('title'),
            int(form.get('status')),
            media_id,
            int(form.get('id'))
        ]
    else:
        sql = """
            UPDATE lifeapp.la_concept_cartoons
            SET la_subject_id = %s,
                la_level_id   = %s,
                title         = %s,
                status        = %s,
                updated_at    = NOW()
            WHERE id = %s
        """
        params = [
            form.get('la_subject_id'),
            form.get('la_level_id'),
            form.get('title'),
            int(form.get('status')),
            int(form.get('id'))
        ]

    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(sql, tuple(params))
        conn.commit()
        return jsonify({'message': 'Concept cartoon updated successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        conn.close()

@app.route('/api/add_concept_cartoon', methods=['POST'])
def add_concept_cartoon():
    form = request.form
    file = request.files.get('media')
    media_id = None
    if file and file.filename:
        media = upload_media(file)
        media_id = media['id']

    sql = '''
        INSERT INTO lifeapp.la_concept_cartoons
          (la_subject_id, la_level_id, title, document, status, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
    '''
    params = [
        form.get('la_subject_id'),
        form.get('la_level_id'),
        form.get('title'),
        media_id,
        int(form.get('status'))
    ]

    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(sql, tuple(params))
            new_id = cursor.lastrowid
        conn.commit()
        return jsonify({'id': new_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/delete_concept_cartoon/<int:id>', methods=['DELETE'])
def delete_concept_cartoon(id):
    try:
        conn = get_db_connection()

        # Optionally: fetch and delete the media row & S3 object
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("""
                SELECT document AS media_id, m.path AS media_path
                FROM lifeapp.la_concept_cartoons c
                LEFT JOIN lifeapp.media m ON c.document = m.id
                WHERE c.id = %s
            """, (id,))
            existing = cursor.fetchone()

        # 1) Delete the cartoon
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM lifeapp.la_concept_cartoons WHERE id = %s", (id,))

        # 2) Delete media record + S3 object if present
        if existing and existing['media_id']:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM lifeapp.media WHERE id = %s", (existing['media_id'],))
            conn.commit()

            if existing['media_path']:
                s3 = boto3.client(
                    's3',
                    region_name=DO_SPACES_REGION,
                    endpoint_url=DO_SPACES_ENDPOINT,
                    aws_access_key_id=DO_SPACES_KEY,
                    aws_secret_access_key=DO_SPACES_SECRET
                )
                try:
                    s3.delete_object(Bucket=DO_SPACES_BUCKET, Key=existing['media_path'])
                except Exception:
                    pass

        conn.commit()
        return jsonify({'message': 'Concept cartoon deleted'}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500

    finally:
        conn.close()

###################################################################################
###################################################################################
################# TEACHER / CONCEPT CARTOON HEADER APIs ###########################
###################################################################################
###################################################################################

# ─── LIST ─────────────────────────────────────────────
@app.route('/api/concept-cartoon-headers', methods=['GET'])
def list_concept_cartoon_headers():
    conn = get_db_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("""
                SELECT
                  h.id,
                  h.heading,
                  h.description,
                  h.button_one_text,
                  h.button_one_link,
                  h.button_two_text,
                  h.button_two_link,
                  h.media_id,
                  m.path    AS media_path,
                  h.created_at,
                  h.updated_at
                FROM lifeapp.la_concept_cartoon_headers h
                LEFT JOIN lifeapp.media m ON m.id = h.media_id
                ORDER BY h.id DESC
            """)
            rows = cursor.fetchall()
        BASE_URL = os.getenv('BASE_URL')
        for r in rows:
            r['media_url'] = f"{BASE_URL}/{r['media_path']}" if r.get('media_path') else None
        return jsonify(rows), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ─── CREATE ────────────────────────────────────────────
@app.route('/api/concept-cartoon-headers', methods=['POST'])
def create_concept_cartoon_header():
    conn = get_db_connection()
    try:
        form = request.form
        file = request.files.get('media')
        media_id = None
        if file and file.filename:
            media = upload_media(file)
            media_id = media['id']

        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO lifeapp.la_concept_cartoon_headers
                  (heading, description,
                   button_one_text, button_one_link,
                   button_two_text, button_two_link,
                   media_id,
                   created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """, (
                form.get('heading'),
                form.get('description'),
                form.get('button_one_text'),
                form.get('button_one_link'),
                form.get('button_two_text'),
                form.get('button_two_link'),
                media_id
            ))
            conn.commit()
            new_id = cursor.lastrowid

        return jsonify({'id': new_id}), 201

    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ─── UPDATE ────────────────────────────────────────────
@app.route('/api/concept-cartoon-headers/<int:header_id>', methods=['PUT'])
def update_concept_cartoon_header(header_id):
    conn = get_db_connection()
    try:
        form = request.form
        file = request.files.get('media')
        new_media_id = None

        # fetch existing media info
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("""
                SELECT media_id, m.path AS media_path
                FROM lifeapp.la_concept_cartoon_headers h
                LEFT JOIN lifeapp.media m ON m.id = h.media_id
                WHERE h.id = %s
            """, (header_id,))
            existing = cursor.fetchone()

        # if new media, delete old then upload
        if file and file.filename:
            s3 = boto3.client(
                's3',
                region_name=DO_SPACES_REGION,
                endpoint_url=DO_SPACES_ENDPOINT,
                aws_access_key_id=DO_SPACES_KEY,
                aws_secret_access_key=DO_SPACES_SECRET
            )
            # delete old S3
            if existing and existing['media_path']:
                try:
                    s3.delete_object(Bucket=DO_SPACES_BUCKET, Key=existing['media_path'])
                except: pass
            # delete old DB
            if existing and existing['media_id']:
                with conn.cursor() as c:
                    c.execute("DELETE FROM media WHERE id = %s", (existing['media_id'],))
                    conn.commit()
            # upload new
            media = upload_media(file)
            new_media_id = media['id']

        # build update SQL
        sql = """
            UPDATE lifeapp.la_concept_cartoon_headers
            SET heading=%s, description=%s,
                button_one_text=%s, button_one_link=%s,
                button_two_text=%s, button_two_link=%s,
                updated_at=NOW()
        """
        params = [
            form.get('heading'),
            form.get('description'),
            form.get('button_one_text'),
            form.get('button_one_link'),
            form.get('button_two_text'),
            form.get('button_two_link'),
        ]
        if new_media_id is not None:
            sql += ", media_id=%s"
            params.append(new_media_id)
        sql += " WHERE id=%s"
        params.append(header_id)

        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            conn.commit()

        return jsonify({'message': 'Header updated'}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ─── DELETE ────────────────────────────────────────────
@app.route('/api/concept-cartoon-headers/<int:header_id>', methods=['DELETE'])
def delete_concept_cartoon_header(header_id):
    conn = get_db_connection()
    try:
        # fetch existing media info
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("""
                SELECT media_id, m.path AS media_path
                FROM lifeapp.la_concept_cartoon_headers h
                LEFT JOIN lifeapp.media m ON m.id = h.media_id
                WHERE h.id = %s
            """, (header_id,))
            existing = cursor.fetchone()

        # delete header
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM lifeapp.la_concept_cartoon_headers WHERE id = %s", (header_id,))

        # delete media record + S3 object
        if existing and existing['media_id']:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM media WHERE id = %s", (existing['media_id'],))
            if existing['media_path']:
                s3 = boto3.client(
                    's3',
                    region_name=DO_SPACES_REGION,
                    endpoint_url=DO_SPACES_ENDPOINT,
                    aws_access_key_id=DO_SPACES_KEY,
                    aws_secret_access_key=DO_SPACES_SECRET
                )
                try:
                    s3.delete_object(Bucket=DO_SPACES_BUCKET, Key=existing['media_path'])
                except: pass

        conn.commit()
        return jsonify({'message': 'Header and media deleted'}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

###################################################################################
###################################################################################
################# TEACHER / LESSON PLAN LANGUAGES APIs ############################
###################################################################################
###################################################################################
@app.route('/api/lesson_plan_language', methods=["GET"])
def fetch_lesson_plan_language():
    sql = """
        SELECT id, name as title,
            CASE WHEN status = 1
                THEN 'Publish' 
            ELSE 'Draft'
            END as status
        FROM lifeapp.la_lession_plan_languages 
        ORDER BY created_at DESC;    
    """
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchall()
            return jsonify(result if result else [])
    except Exception as e:
        print("Error in lesson_plan_language:", str(e))
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/update_lesson_plan_language', methods=['POST'])
def update_lesson_plan_language():
    data = request.get_json() or {}
    try:
        # assume the front end now sends status as 1 or 0
        status_value = int(data.get("status", 0))
    except ValueError:
        # fallback if it's still a string
        status_value = 1 if data.get("status") == "Publish" else 0

    sql = """
        UPDATE lifeapp.la_lession_plan_languages
        SET name = %s,
            status = %s,
            updated_at = NOW()
        WHERE id = %s
    """
    params = (data.get("title"), status_value, data.get("id"))
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
        conn.commit()
        return jsonify({'message': 'Updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/add_lesson_plan_language', methods=['POST'])
def add_lesson_plan_language():
    data = request.get_json()
    status_value = 1 if data["status"] == "Publish" else 0
    
    sql = "INSERT INTO lifeapp.la_lession_plan_languages (name, status, created_at, updated_at) VALUES (%s, %s, NOW(), NOW())"
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(sql, (data["title"], status_value))
        connection.commit()
        return jsonify({'message': 'Added successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/delete_lesson_plan_language/<int:id>', methods=['DELETE'])
def delete_lesson_plan_language(id):
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM lifeapp.la_lession_plan_languages WHERE id = %s", (id,))
        connection.commit()
        return jsonify({'message': 'Deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

###################################################################################
###################################################################################
######################## TEACHER / LESSON PLAN APIs ###############################
###################################################################################
###################################################################################

@app.route('/api/lesson_plan_languages_2', methods =['GET'])
def get_lesson_plan_langauges_2():
    sql = """
    select id, name from lifeapp.la_lession_plan_languages;
    """
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchall()
            return jsonify(result if result else [])
    except Exception as e:
        print("Error in lesson_plan_language:", str(e))
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/lesson_plans_search', methods=['POST'])
def fetch_lesson_plans_search():
    filters = request.get_json() or {}
    language = filters.get('language')
    status = filters.get('status')
    title = filters.get('title')

    sql = """
        SELECT 
            lalp.id,
            lall.name AS language,
            CASE
                WHEN lalp.type = 1 THEN 'Life Lab - Demo Models'
                WHEN lalp.type = 2 THEN 'Jigyasa - Self DIY Activities'
                WHEN lalp.type = 3 THEN 'Pragya - DIY Activities With Life Lab KITS'
                WHEN lalp.type = 4 THEN 'Life Lab - Activities Lesson Plans'
                ELSE 'Default type (None Mentioned)'
            END AS type,
            lalp.title AS title,
            CASE
                WHEN lalp.status = 1 THEN 'Published'
                ELSE 'Drafted'
            END AS status,
            lalp.document AS media_id,
            m.path          AS media_path
        FROM lifeapp.la_lession_plans lalp
        INNER JOIN lifeapp.la_lession_plan_languages lall 
            ON lall.id = lalp.la_lession_plan_language_id
        LEFT JOIN lifeapp.media m 
            on m.id = lalp.document
        """

    # Build WHERE clause if filters are provided
    where_clauses = []
    params = []

    if language and language.strip():
        where_clauses.append("lall.name = %s")
        params.append(language)
    if status and status.strip():
        # Convert 'Published'/'Drafted' to numeric
        where_clauses.append("lalp.status = %s")
        params.append(1 if status == "Published" else 0)
    if title and title.strip():
        where_clauses.append("lalp.title LIKE %s")
        params.append(f"%{title}%")

    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)

    # Order by most recently updated
    sql += " ORDER BY lalp.updated_at DESC"

    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(sql, tuple(params))
            result = cursor.fetchall()
        base_url = os.getenv('BASE_URL')
        for r in result:
            r['media_url'] = f"{base_url}/{r['media_path']}" if r.get('media_path') else None
        return jsonify(result if result else []), 200
    except Exception as e:
        print("Error in fetch_lesson_plans_search:", str(e))
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/update_lesson_plan', methods=['POST'])
def update_lesson_plan():
    form = request.form
    file = request.files.get('media')
    media_id = None
    if file and file.filename:
        media = upload_media(file)
        media_id = media['id']

    try:
        lp_id      = int(form['id'])
        language_id= int(form['language_id'])
        plan_type  = int(form['type'])
        status_val = int(form['status'])
    except:
        return jsonify({'error':'Missing or invalid IDs'}),400

    # build query dynamically if new media provided
    if media_id:
        sql = """
          UPDATE lifeapp.la_lession_plans
          SET la_lession_plan_language_id=%s,
              title=%s,
              document=%s,
              `type`=%s,
              status=%s,
              updated_at=NOW()
          WHERE id=%s
        """
        params = (language_id, form.get('title'), media_id, plan_type, status_val, lp_id)
    else:
        sql = """
          UPDATE lifeapp.la_lession_plans
          SET la_lession_plan_language_id=%s,
              title=%s,
              `type`=%s,
              status=%s,
              updated_at=NOW()
          WHERE id=%s
        """
        params = (language_id, form.get('title'), plan_type, status_val, lp_id)

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()
        return jsonify({'message':'Lesson Plan updated'}),200
    finally:
        conn.close()

@app.route('/api/add_lesson_plan', methods=['POST'])
def add_lesson_plan():
    form = request.form
    file = request.files.get('media')
    media_id = None
    if file and file.filename:
        media = upload_media(file)
        media_id = media['id']

    try:
        language_id = int(form['language_id'])
        plan_type   = int(form['type'])
        status_val  = int(form['status'])
    except:
        return jsonify({'error':'Invalid form data'}), 400

    sql = """
      INSERT INTO lifeapp.la_lession_plans
        (la_lession_plan_language_id, title, document, `type`, status, created_at, updated_at)
      VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
    """
    params = (
      language_id,
      form.get('title','').strip(),
      media_id,
      plan_type,
      status_val
    )
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(sql, params)
            new_id = cur.lastrowid
        conn.commit()
        return jsonify({'id': new_id}), 201
    finally:
        conn.close()

@app.route('/api/delete_lesson_plan/<int:lp_id>', methods=['DELETE'])
def delete_lesson_plan(lp_id):
    try:
        conn = get_db_connection()
        # fetch media record
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute("""
              SELECT document AS media_id, m.path AS media_path
              FROM lifeapp.la_lession_plans lp
              LEFT JOIN lifeapp.media m ON lp.document=m.id
              WHERE lp.id=%s
            """, (lp_id,))
            row = cur.fetchone()

        # delete lesson plan
        with conn.cursor() as cur:
            cur.execute("DELETE FROM lifeapp.la_lession_plans WHERE id=%s", (lp_id,))

        # delete media record + S3 object
        if row and row['media_id']:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM lifeapp.media WHERE id=%s", (row['media_id'],))
            conn.commit()
            s3 = boto3.client(
              's3',
              region_name=DO_SPACES_REGION,
              endpoint_url=DO_SPACES_ENDPOINT,
              aws_access_key_id=DO_SPACES_KEY,
              aws_secret_access_key=DO_SPACES_SECRET
            )
            try:
                s3.delete_object(Bucket=DO_SPACES_BUCKET, Key=row['media_path'])
            except:
                pass

        conn.commit()
        return jsonify({'message':'Deleted successfully'}),200
    finally:
        conn.close()

###################################################################################
###################################################################################
######################## TEACHER / WORKSHEET APIs ###############################$#
###################################################################################
###################################################################################

# 1) SEARCH / FILTER Worksheets
@app.route('/api/work_sheets_search', methods=['POST'])
def fetch_work_sheets_search():
    filters = request.get_json() or {}
    subject_filter = filters.get('subject', '').strip()
    grade_filter   = filters.get('grade',   '').strip()
    status_filter  = filters.get('status',  '').strip()
    title_filter   = filters.get('title',   '').strip()

    sql = """
        SELECT
            w.id,
            s.title        AS subject_title,
            w.la_grade_id  AS grade,
            w.title,
            w.document     AS media_id,
            m.path         AS media_path,
            CASE WHEN w.status = 1 THEN 'Published' ELSE 'Drafted' END AS status
        FROM lifeapp.la_work_sheets w
        INNER JOIN lifeapp.la_subjects s
            ON w.la_subject_id = s.id
        LEFT JOIN lifeapp.media m
            ON w.document = m.id
        WHERE 1=1
    """
    params = []

    # subject dropdown now holds the subject ID
    if subject_filter:
        sql += " AND w.la_subject_id = %s"
        params.append(int(subject_filter))

    if grade_filter:
        try:
            params.append(int(grade_filter))
            sql += " AND w.la_grade_id = %s"
        except ValueError:
            pass

    if status_filter:
        sql += " AND w.status = %s"
        params.append(1 if status_filter == 'Published' else 0)

    if title_filter:
        sql += " AND w.title LIKE %s"
        params.append(f"%{title_filter}%")

    sql += " ORDER BY w.updated_at DESC;"

    try:
        conn = get_db_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()

        base = os.getenv('BASE_URL', '')
        for r in rows:
            r['document_url'] = r['media_path'] and f"{base}/{r['media_path']}" or None

        return jsonify(rows), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        conn.close()

# 2) ADD a new Worksheet
@app.route('/api/add_work_sheet', methods=['POST'])
def add_work_sheet():
    form = request.form
    file = request.files.get('media')
    media_id = None
    if file and file.filename:
        media = upload_media(file)
        media_id = media['id']

    # Use the subject ID directly from the form instead of hardcoding
    try:
        la_subject_id = int(form.get('subject'))
    except:
        return jsonify({'error':'Invalid subject ID'}), 400

    try:
        la_grade_id = int(form.get('grade'))
    except:
        return jsonify({'error':'Invalid grade'}), 400
        
    title = form.get('title','').strip()
    status_val = 1 if form.get('status')=='Published' else 0

    sql = """
      INSERT INTO lifeapp.la_work_sheets
        (la_subject_id, la_grade_id, title, document, status, created_at, updated_at)
      VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
    """
    params = (la_subject_id, la_grade_id, title, media_id, status_val)
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            new_id = cursor.lastrowid
        conn.commit()
        return jsonify({'id': new_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# 3) UPDATE an existing Worksheet
@app.route('/api/update_work_sheet', methods=['POST'])
def update_work_sheet():
    form = request.form
    file = request.files.get('media')
    media_id = None
    if file and file.filename:
        media = upload_media(file)
        media_id = media['id']

    try:
        ws_id = int(form.get('id'))
    except:
        return jsonify({'error':'Missing or invalid ID'}), 400

    # Use the subject ID directly from the form instead of hardcoding
    try:
        la_subject_id = int(form.get('subject'))
    except:
        return jsonify({'error':'Invalid subject ID'}), 400
        
    try:
        la_grade_id = int(form.get('grade'))
    except:
        return jsonify({'error':'Invalid grade'}), 400
        
    title = form.get('title','').strip()
    status_val = 1 if form.get('status')=='Published' else 0

    if media_id:
        sql = """
          UPDATE lifeapp.la_work_sheets
          SET la_subject_id=%s, la_grade_id=%s, title=%s, document=%s, status=%s, updated_at=NOW()
          WHERE id=%s
        """
        params = (la_subject_id, la_grade_id, title, media_id, status_val, ws_id)
    else:
        sql = """
          UPDATE lifeapp.la_work_sheets
          SET la_subject_id=%s, la_grade_id=%s, title=%s, status=%s, updated_at=NOW()
          WHERE id=%s
        """
        params = (la_subject_id, la_grade_id, title, status_val, ws_id)

    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
        conn.commit()
        return jsonify({'message':'Worksheet updated'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# 4) DELETE an existing Worksheet
@app.route('/api/delete_work_sheet/<int:ws_id>', methods=['DELETE'])
def delete_work_sheet(ws_id):
    try:
        conn = get_db_connection()
        # fetch media info
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute("""
              SELECT w.document AS media_id, m.path AS media_path
              FROM lifeapp.la_work_sheets w
              LEFT JOIN lifeapp.media m ON w.document = m.id
              WHERE w.id=%s
            """, (ws_id,))
            row = cur.fetchone()

        # delete worksheet
        with conn.cursor() as cur:
            cur.execute("DELETE FROM lifeapp.la_work_sheets WHERE id=%s", (ws_id,))

        # delete media record + S3 object
        if row and row['media_id']:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM lifeapp.media WHERE id=%s", (row['media_id'],))
            conn.commit()
            s3 = boto3.client(
                's3',
                region_name=DO_SPACES_REGION,
                endpoint_url=DO_SPACES_ENDPOINT,
                aws_access_key_id=DO_SPACES_KEY,
                aws_secret_access_key=DO_SPACES_SECRET
            )
            try:
                s3.delete_object(Bucket=DO_SPACES_BUCKET, Key=row['media_path'])
            except:
                pass

        conn.commit()
        return jsonify({'message':'Worksheet deleted'}),200
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}),500
    finally:
        conn.close()

###################################################################################
###################################################################################
######################## TEACHER / ASSESSMENT APIs ################################
###################################################################################
###################################################################################

@app.route('/api/assessments_search', methods=['POST'])
def assessments_search():
    filters = request.get_json() or {}
    subject_id = filters.get('subject_id', '').strip()
    grade = filters.get('grade', '').strip()
    title = filters.get('title', '').strip()
    status = filters.get('status', '').strip()

    sql = """
        SELECT
            a.id,
            CASE WHEN a.la_subject_id = 1 THEN 'Science' ELSE 'Maths' END AS subject,
            a.la_grade_id AS grade,
            a.title,
            a.document AS media_id,
            m.path        AS media_path,
            CASE WHEN a.status = 1 THEN 'Published' ELSE 'Drafted' END AS status
        FROM lifeapp.la_assessments a
        LEFT JOIN lifeapp.media m ON a.document = m.id
        WHERE 1=1
    """
    params = []

    if subject_id:
        try:
            params.append(int(subject_id))
            sql += " AND a.la_subject_id = %s"
        except ValueError:
            pass

    if grade:
        try:
            params.append(int(grade))
            sql += " AND a.la_grade_id = %s"
        except ValueError:
            pass

    if title:
        params.append(f"%{title}%")
        sql += " AND a.title LIKE %s"

    if status:
        sql += " AND a.status = %s"
        params.append(1 if status == "Published" else 0)

    sql += " ORDER BY a.updated_at DESC;"

    try:
        conn = get_db_connection()
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall()

        # build full media_url
        BASE_URL = os.getenv('BASE_URL')
        for r in rows:
            r['document_url'] = (
                f"{BASE_URL}/{r['media_path']}" if r.get('media_path') else None
            )
        return jsonify(rows), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        conn.close()

@app.route('/api/add_assessment', methods=['POST'])
def add_assessment():
    """
    Expects multipart/form-data:
      - subject: "Science" or "Maths"
      - grade: integer
      - title: string
      - media: file upload (optional)
      - status: "Published" or "Drafted"
    """
    form = request.form
    file = request.files.get('media')
    media_id = None

    # 1) If a file was uploaded, push to S3 and media table
    if file and file.filename:
        media = upload_media(file)
        media_id = media['id']

    # 2) Map inputs to IDs/values
    try:
        la_subject_id = int(form.get('subject_id', '0'))
    except ValueError:
        return jsonify({'error': 'Invalid subject ID'}), 400
    
    try:
        la_grade_id = int(form.get('grade', '0'))
    except ValueError:
        return jsonify({'error': 'Invalid grade'}), 400

    title = form.get('title', '').strip()
    status_str = form.get('status', 'Drafted')
    status_val = 1 if status_str == 'Published' else 0

    # 3) Insert into DB
    sql = """
        INSERT INTO lifeapp.la_assessments
          (la_subject_id, la_grade_id, title, document, status, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
    """
    params = (la_subject_id, la_grade_id, title, media_id, status_val)

    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            new_id = cursor.lastrowid
        conn.commit()

        # 4) Return the new record’s ID
        return jsonify({'id': new_id}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        conn.close()

@app.route('/api/update_assessment', methods=['POST'])
def update_assessment():
    form = request.form
    file = request.files.get('media')
    media_id = None

    if file and file.filename:
        media = upload_media(file)
        media_id = media['id']

    # required
    try:
        assessment_id = int(form.get('id'))
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid or missing assessment ID'}), 400

    try:
        la_subject_id = int(form.get('subject_id', '0'))
    except ValueError:
        return jsonify({'error': 'Invalid subject ID'}), 400
    
    try:
        la_grade_id = int(form.get('grade', 0))
    except ValueError:
        return jsonify({'error': 'Invalid grade'}), 400
    title = form.get('title', '').strip()
    status_val = 1 if form.get('status') == 'Published' else 0

    # build SQL
    if media_id:
        sql = """
            UPDATE lifeapp.la_assessments
            SET la_subject_id = %s,
                la_grade_id   = %s,
                title         = %s,
                document      = %s,
                status        = %s,
                updated_at    = NOW()
            WHERE id = %s
        """
        params = (la_subject_id, la_grade_id, title, media_id, status_val, assessment_id)
    else:
        sql = """
            UPDATE lifeapp.la_assessments
            SET la_subject_id = %s,
                la_grade_id   = %s,
                title         = %s,
                status        = %s,
                updated_at    = NOW()
            WHERE id = %s
        """
        params = (la_subject_id, la_grade_id, title, status_val, assessment_id)

    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
        conn.commit()
        return jsonify({'message': 'Assessment updated successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        conn.close()

@app.route('/api/delete_assessment/<int:assessment_id>', methods=['DELETE'])
def delete_assessment(assessment_id):
    try:
        conn = get_db_connection()
        # 1) Fetch the media ID & path so we can delete the S3 file too
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute("""
                SELECT a.document AS media_id, m.path AS media_path
                FROM lifeapp.la_assessments a
                LEFT JOIN lifeapp.media m ON a.document = m.id
                WHERE a.id = %s
            """, (assessment_id,))
            row = cursor.fetchone()

        # 2) Delete the assessment row
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM lifeapp.la_assessments WHERE id = %s", (assessment_id,))

        # 3) If there was linked media, delete both DB row and S3 object
        if row and row['media_id']:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM lifeapp.media WHERE id = %s", (row['media_id'],))
            conn.commit()

            # Delete from your S3/DigitalOcean Space
            s3 = boto3.client(
                's3',
                region_name=DO_SPACES_REGION,
                endpoint_url=DO_SPACES_ENDPOINT,
                aws_access_key_id=DO_SPACES_KEY,
                aws_secret_access_key=DO_SPACES_SECRET
            )
            try:
                s3.delete_object(Bucket=DO_SPACES_BUCKET, Key=row['media_path'])
            except Exception as e:
                app.logger.warning(f"Failed to delete S3 object {row['media_path']}: {e}")

        conn.commit()
        return jsonify({'message': 'Assessment and media deleted successfully'}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500

    finally:
        conn.close()

###################################################################################
###################################################################################
####################### TEACHER/COMPETENCIES APIs #################################
###################################################################################
###################################################################################
@app.route('/admin/competencies', methods=['GET'])
def get_competencies():
    """
    Fetch competencies along with subject and level information.
    Optional query parameters:
      - la_subject_id (filter by subject)
      - status (filter by competency status; e.g. 1 for ACTIVE, 0 for DEACTIVE)
      - page (for pagination, default: 1)
    """
    try:
        # Get filters from query string (or use defaults)
        la_subject_id = request.args.get('la_subject_id')
        status = request.args.get('status')  # expected as a string, e.g. "1" or "0"
        page = int(request.args.get('page', 1))
        per_page = 25
        offset = (page - 1) * per_page

        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Build the SQL with JOINs:
            sql = """
            SELECT 
              comp.id,
              comp.title AS competency_title,
              comp.document,
              comp.status,
              comp.created_at,
              comp.la_subject_id,
              comp.la_level_id,
              s.title AS subject_title,
              l.title AS level_title,
              -- raw media id
              comp.document        AS document_id,

              -- pull path from media
              mdoc.path            AS document_path
            FROM lifeapp.la_competencies comp
            INNER JOIN lifeapp.la_subjects s ON comp.la_subject_id = s.id
            INNER JOIN lifeapp.la_levels l ON comp.la_level_id = l.id
            LEFT JOIN lifeapp.media mdoc ON mdoc.id = comp.document
            WHERE 1 = 1 
            """
            params = []
            if la_subject_id:
                sql += " AND comp.la_subject_id = %s"
                params.append(la_subject_id)
            if status is not None and status != "":
                sql += " AND comp.status = %s"
                params.append(int(status))
            sql += " ORDER BY comp.id DESC LIMIT %s OFFSET %s"
            params.extend([per_page, offset])
            cursor.execute(sql, params)
            competencies = cursor.fetchall()

        # Also fetch the subjects list (for filter dropdowns)
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, title FROM lifeapp.la_subjects WHERE status = 1 ORDER BY id;")
            subjects = cursor.fetchall()

        connection.close()
        # build full URL
        base_url = os.getenv('BASE_URL', '')
        for r in competencies:
            r['document_url'] = (
                f"{base_url}/{r['document_path']}" if r.get('document_path') else None
            )
        # Return both competencies and subjects
        return jsonify({"competencies": competencies, "subjects": subjects})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/competencies', methods=['POST'])
def create_competency():
    """
    Expects a multipart/form-data POST request (for file upload) and other fields in form data.
    Required fields: name (for competency title), la_subject_id, la_level_id, status
    Document is expected as a file input named 'document'
    """
    form = request.form
    document_file = request.files.get('document')
    if not document_file or not document_file.filename:
        return jsonify({'error': 'Document file required'}), 400

    media = upload_media(document_file)
    document_id = media['id']

    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        sql = """
            INSERT INTO lifeapp.la_competencies 
            (title, la_subject_id, la_level_id, status, document, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
        """
        # Here 'title' is the competency title.
        cursor.execute(sql, (
            form.get('name'),
            form.get('la_subject_id'),
            form.get('la_level_id'),
            form.get('status', 'ACTIVE'),
            document_id
        ))
        connection.commit()
        return jsonify({'message': 'Competency created successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()

# Update an existing competency (Edit)
@app.route('/admin/competencies/<int:competency_id>', methods=['PUT', 'POST'])
def update_competency(competency_id):
    connection = None
    try:
        form = request.form
        document_file = request.files.get('document')
        connection = get_db_connection()
        
        with connection.cursor() as cursor:
            # Fetch existing document info
            cursor.execute("""
                SELECT m.id as media_id, m.path 
                FROM lifeapp.la_competencies c
                LEFT JOIN lifeapp.media m ON c.document = m.id
                WHERE c.id = %s
            """, (competency_id,))
            existing = cursor.fetchone()
            existing_media_id = existing['media_id'] if existing else None
            existing_s3_key = existing['path'] if existing else None

            new_doc_id = None
            if document_file and document_file.filename:
                # Initialize S3 client
                s3 = boto3.client(
                    's3',
                    region_name=DO_SPACES_REGION,
                    endpoint_url=DO_SPACES_ENDPOINT,
                    aws_access_key_id=DO_SPACES_KEY,
                    aws_secret_access_key=DO_SPACES_SECRET
                )

                # Delete old media if exists
                if existing_media_id:
                    # Delete from S3
                    if existing_s3_key:
                        try:
                            s3.delete_object(Bucket=DO_SPACES_BUCKET, Key=existing_s3_key)
                        except Exception as s3_error:
                            print(f"Error deleting S3 object: {s3_error}")

                    # Delete from database
                    cursor.execute("DELETE FROM lifeapp.media WHERE id = %s", (existing_media_id,))

                # Upload new document
                media = upload_media(document_file)
                new_doc_id = media['id']

            # Build the update query
            update_sql = """
                UPDATE lifeapp.la_competencies 
                SET title = %s, la_subject_id = %s, la_level_id = %s, 
                    status = %s, updated_at = NOW()
            """
            params = [
                form.get('name'),
                form.get('la_subject_id'),
                form.get('la_level_id'),
                form.get('status')
            ]

            if new_doc_id is not None:
                update_sql += ", document = %s"
                params.append(new_doc_id)

            update_sql += " WHERE id = %s"
            params.append(competency_id)

            cursor.execute(update_sql, params)
            connection.commit()
            
        return jsonify({'message': 'Competency updated successfully'}), 200

    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        if connection:
            connection.close()

# Delete a competency
@app.route('/admin/competencies/<int:competency_id>', methods=['DELETE'])
def delete_competency(competency_id):
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Get the document ID from the competency
            cursor.execute("SELECT document FROM lifeapp.la_competencies WHERE id = %s", (competency_id,))
            result = cursor.fetchone()
            document_id = result['document'] if result else None

            # Delete the competency
            cursor.execute("DELETE FROM lifeapp.la_competencies WHERE id = %s", (competency_id,))

            # Delete associated media if exists
            if document_id:
                cursor.execute("DELETE FROM lifeapp.media WHERE id = %s", (document_id,))

            connection.commit()
        return jsonify({'message': 'Competency and associated media deleted successfully'}), 200
    except Exception as e:
        connection.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

###################################################################################
###################################################################################
####################### SCHOOLS/SCHOOL-DATA APIs ##################################
###################################################################################
###################################################################################

@app.route('/api/get_schools_data', methods=['POST'])
def get_schools_data():
    """
    Returns paginated rows from lifeapp.schools with columns:
    id, name, state, city, district, block, cluster, pin_code, code,
    app_visible, is_life_lab, status.
    Numeric flags are converted to user-friendly text.
    Accepts JSON body with optional filters *and* pagination params:
      - page:        (int) 1-based page number, default=1
      - per_page:    (int) rows per page, default=50
    """
    data = request.get_json() or {}
    # --- Filters ---
    name     = data.get('name')
    state    = data.get('state')
    city     = data.get('city')
    district = data.get('district')
    status   = data.get('status')
    cluster  = data.get('cluster')
    block    = data.get('block')
    codes    = data.get('code')

    # --- Pagination params ---
    try:
        page     = max(int(data.get('page', 1)), 1)
        per_page = min(int(data.get('per_page', 50)), 200)  # cap per_page to 200
    except ValueError:
        page, per_page = 1, 50

    offset = (page - 1) * per_page

    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Build base WHERE clause
            where_clauses = ["deleted_at IS NULL"]
            params = []

            if status:
                where_clauses.append("status = %s")
                params.append(1 if status == "Active" else 0)

            if district:
                where_clauses.append("(district = %s OR district LIKE %s)")
                params.extend([district, f"%{district}%"])

            if city:
                where_clauses.append("city = %s")
                params.append(city)

            if state:
                where_clauses.append("state = %s")
                params.append(state)

            if name:
                where_clauses.append("(name = %s OR name LIKE %s)")
                params.extend([name, f"%{name}%"])

            if cluster:
                where_clauses.append("(cluster = %s OR cluster LIKE %s)")
                params.extend([cluster, f"%{cluster}%"])

            if block:
                where_clauses.append("(block = %s OR block LIKE %s)")
                params.extend([block, f"%{block}%"])

            if codes:
                # ensure list
                code_list = codes if isinstance(codes, list) else [codes]
                placeholders = ",".join(["%s"] * len(code_list))
                where_clauses.append(f"code IN ({placeholders})")
                # cast codes to int when needed
                params.extend([int(c) for c in code_list])

            where_sql = " AND ".join(where_clauses)

            # 1) get total count
            count_sql = f"SELECT COUNT(*) AS total FROM lifeapp.schools WHERE {where_sql}"
            cursor.execute(count_sql, tuple(params))
            total = cursor.fetchone()["total"]

            # 2) fetch just this page
            data_sql = f"""
                SELECT
                  id, name, state, city, district, block, cluster,
                  pin_code, code, app_visible, is_life_lab, status, donor_name
                FROM lifeapp.schools
                WHERE {where_sql}
                ORDER BY id DESC
                LIMIT %s OFFSET %s
            """
            cursor.execute(data_sql, tuple(params) + (per_page, offset))
            rows = cursor.fetchall()

            # convert flags
            for row in rows:
                row["app_visible"] = "Yes" if row["app_visible"] == 1 else "No"
                row["is_life_lab"] = "Yes" if row["is_life_lab"] == 1 else "No"
                row["status"]      = "Active" if row["status"] == 1 else "Inactive"

        # wrap in pagination envelope
        return jsonify({
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": math.ceil(total / per_page),
            "data": rows
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        conn.close()

@app.route('/api/schools_data', methods=['POST'])
def add_school_data():
    """
    Adds a new school row.
    Expected JSON keys: name, state, city, district, pin_code, app_visible, is_life_lab, status.
    app_visible and is_life_lab are "Yes"/"No", and status "Active"/"Inactive".
    """
    data = request.get_json() or {}
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            name = data.get("name")
            state = data.get("state")
            city = data.get("city")
            district = data.get("district")
            block = data.get('block')
            cluster = data.get('cluster')
            code = data.get('code')
            pin_code = data.get("pin_code")
            donor_name = data.get("donor_name")  # ← new line
            app_visible_val = 1 if data.get("app_visible") == "Yes" else 0
            is_life_lab_val = 1 if data.get("is_life_lab") == "Yes" else 0
            status_val = 1 if data.get("status") == "Active" else 0
            sql = """
                INSERT INTO lifeapp.schools 
                (name, state, city, district, pin_code, donor_name, app_visible, is_life_lab, status, created_at, updated_at, block, cluster, code)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), %s, %s, %s)
            """
            cursor.execute(sql, (name, state, city, district, pin_code, donor_name, app_visible_val, is_life_lab_val, status_val, block, cluster, code))
            connection.commit()
        return jsonify({"message": "School added successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        connection.close()

@app.route('/api/schools_data/<int:school_id>', methods=['PUT'])
def update_school_data(school_id):
    """
    Updates an existing school row.
    Expected JSON keys: name, state, city, district, pin_code, app_visible, is_life_lab, status.
    """
    data = request.get_json() or {}
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            name = data.get("name")
            state = data.get("state")
            city = data.get("city")
            district = data.get("district")
            cluster = data.get('cluster')
            block = data.get('block')
            code = data.get('code')
            pin_code = data.get("pin_code")
            donor_name = data.get("donor_name")  # ← new line
            app_visible_val = 1 if data.get("app_visible") == "Yes" else 0
            is_life_lab_val = 1 if data.get("is_life_lab") == "Yes" else 0
            status_val = 1 if data.get("status") == "Active" else 0
            sql = """
                UPDATE lifeapp.schools
                SET 
                    name = %s,
                    state = %s,
                    city = %s,
                    district = %s,
                    cluster = %s,
                    block = %s,
                    pin_code = %s,
                    code = %s,
                    app_visible = %s,
                    is_life_lab = %s,
                    status = %s,
                    donor_name = %s,     -- add this line
                    updated_at = NOW()
                WHERE id = %s
            """
            cursor.execute(sql, (name, state, city, district, cluster, block, pin_code, code, app_visible_val, is_life_lab_val, status_val, donor_name, school_id))
            connection.commit()
        return jsonify({"message": "School updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        connection.close()

@app.route('/api/schools_data/<int:school_id>', methods=['DELETE'])
def delete_school_data(school_id):
    """
    Soft-deletes a school row by setting deleted_at.
    """
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = """
                UPDATE lifeapp.schools
                SET deleted_at = NOW()
                WHERE id = %s
            """
            cursor.execute(sql, (school_id,))
            connection.commit()
        return jsonify({"message": "School deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        connection.close()

@app.route('/api/upload_schools_csv', methods=['POST'])
def upload_schools_csv():
    if 'csv' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
        
    file = request.files['csv']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    if not file.filename.endswith('.csv'):
        return jsonify({"error": "File must be a CSV"}), 400

    try:
        # Read CSV file
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.DictReader(stream)
        
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = """
                INSERT INTO lifeapp.schools 
                (name, state, city, district, block, cluster, 
                 pin_code, code, donor_name, app_visible, is_life_lab, status, 
                 created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """
            
            count = 0
            for row in csv_reader:
                # Map Excel columns to database fields
                mapped_data = {
                    'name': row.get('school_name', '').strip(),
                    'state': row.get('state_name', '').strip(),
                    'city': row.get('city_name', '').strip(),
                    'district': row.get('district_name', '').strip(),
                    'block': row.get('block_name', '').strip(),
                    'cluster': row.get('cluster_name', '').strip(),
                    'pin_code': row.get('pin_code', '').strip(),
                    'code': row.get('school_code', '').strip(),
                    'donor_name': row.get('donor_name', '').strip(),            # ← new
                    'app_visible': row.get('app_visible', 'No').strip().lower(),
                    'is_life_lab': row.get('is_life_lab', 'No').strip().lower(),
                    'status': row.get('status', 'Active').strip().lower()
                }

                # Validate required fields
                required_fields = ['name', 'state', 'city', 'district', 'pin_code']
                if not all(mapped_data[field] for field in required_fields):
                    continue  # Skip invalid rows

                # Convert values
                app_visible_val = 1 if mapped_data['app_visible'] == 'yes' else 0
                is_life_lab_val = 1 if mapped_data['is_life_lab'] == 'yes' else 0
                status_val = 1 if mapped_data['status'] == 'active' else 0

                cursor.execute(sql, (
                    mapped_data['name'],
                    mapped_data['state'],
                    mapped_data['city'],
                    mapped_data['district'],
                    mapped_data['block'],
                    mapped_data['cluster'],
                    mapped_data['pin_code'],
                    mapped_data['code'],
                    mapped_data['donor_name'],    # ← pass donor_name
                    app_visible_val,
                    is_life_lab_val,
                    status_val
                ))
                count += 1
            
            connection.commit()
            return jsonify({"message": f"Successfully uploaded {count} schools"}), 201
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'connection' in locals():
            connection.close()

# @app.route('/api/state_list', methods=['GET'])
# def get_state_list():
#     """
#     Returns distinct states from the schools table.
#     """
#     try:
#         connection = get_db_connection()
#         with connection.cursor() as cursor:
#             sql = """
#                 SELECT DISTINCT(state) 
#                 FROM lifeapp.schools 
#                 WHERE state IS NOT NULL AND state != '' AND state != '2'
#             """
#             cursor.execute(sql)
#             result = cursor.fetchall()
#             states = [row['state'] for row in result]
#         return jsonify(states)
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500
#     finally:
#         connection.close()

@app.route('/api/cities_for_state', methods=['GET'])
def get_cities_for_state():
    """
    Returns distinct city values for the given state.
    Example: GET /api/cities_for_state?state=Maharashtra
    """
    state = request.args.get('state')
    if not state:
        return jsonify({"error": "Query param 'state' is required"}), 400
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = """
                SELECT DISTINCT city 
                FROM lifeapp.schools
                WHERE state = %s 
                  AND deleted_at IS NULL
                  AND city IS NOT NULL AND city != ''
            """
            cursor.execute(sql, (state,))
            result = cursor.fetchall()
            cities = [row['city'] for row in result]
        return jsonify(cities), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        connection.close()

###################################################################################
###################################################################################
######################## SCHOOLS/DASHBOARD APIs ###################################
###################################################################################
###################################################################################
@app.route('/api/count_school_state_dashboard', methods= ['POST'])
def get_count_school_rate_dashboard():
    connection = get_db_connection()
    try:
       
        with connection.cursor() as cursor:
            #execute sql query
            sql = """
            select state, count(*) as count from lifeapp.schools 
            where state != 'null' and state != '2' group by state order by count desc;
            """
            cursor.execute(sql)
            result = cursor.fetchall()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/demograph-schools', methods=['POST'])
def get_schools_demograph():
    try:
        data = request.get_json() or {}
        grouping = data.get('grouping', 'monthly').lower()
        state_filter = data.get('state', '').strip()
        
        # Validate and normalize grouping
        allowed_groupings = ['daily', 'weekly', 'monthly', 'quarterly', 'yearly', 'lifetime']
        grouping = grouping if grouping in allowed_groupings else 'monthly'

        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Build period expression
            period_expr = {
                'daily': "DATE(created_at)",
                'weekly': "CONCAT(YEAR(created_at), '-W', LPAD(WEEK(created_at, 3), 2, '0'))",
                'monthly': "DATE_FORMAT(created_at, '%%Y-%%m')",
                'quarterly': "CONCAT(YEAR(created_at), '-Q', QUARTER(created_at))",
                'yearly': "YEAR(created_at)",
                'lifetime': "'lifetime'"
            }[grouping]

            # State filter condition
            state_condition = ""
            if state_filter and state_filter.lower() != 'all':
                state_condition = "AND normalized_state = %(state_filter)s"

            sql = f"""
                SELECT 
                    period,
                    normalized_state as state,
                    SUM(school_count) as count
                FROM (
                    SELECT 
                        {period_expr} AS period,
                        CASE
                            WHEN LOWER(state) IN ('gujrat', 'gujarat') THEN 'Gujarat'
                            WHEN LOWER(state) IN ('tamilnadu', 'tamil nadu') THEN 'Tamil Nadu'
                            WHEN LOWER(state) = 'nct of delhi' THEN 'Delhi'
                            ELSE TRIM(LOWER(state))
                        END AS normalized_state,
                        COUNT(*) AS school_count
                    FROM lifeapp.schools
                    WHERE state IS NOT NULL 
                        AND state != 'null'
                        AND state != ''
                    GROUP BY period, state
                ) AS normalized
                WHERE 1=1 {state_condition}
                GROUP BY period, normalized_state
                ORDER BY period, count DESC
            """

            params = {'state_filter': state_filter.title()} if state_condition else {}
            cursor.execute(sql, params)
            result = cursor.fetchall()

            # Convert datetime objects to strings and format state names
            formatted_result = []
            for row in result:
                period = str(row['period'])  # Convert potential datetime to string
                formatted_result.append({
                    'period': period,
                    'state': row['state'].title() if row['state'] else 'Unknown',
                    'count': row['count']
                })

            return jsonify(formatted_result), 200

    except Exception as e:
        app.logger.error(f"Error fetching school demographics: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        if 'connection' in locals() and connection:
            connection.close()


###################################################################################
###################################################################################
######################## MENTORS/DASHBOARD APIs ###################################
###################################################################################
###################################################################################
@app.route('/api/mentors', methods=['POST'])
def get_mentors():
    """Fetch list of mentors with optional filters for state, mobile number, and mentor_code."""
    try:
        filters = request.get_json() or {}
        state_filter = filters.get('state')
        mobile_filter = filters.get('mobile_no')
        mentor_code_filter = filters.get('mentor_code')
        
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Base query: selecting mentors (type 4)
            sql = """
                SELECT id, name, email, mobile_no, pin, gender, dob, state, city 
                FROM lifeapp.users 
                WHERE `type` = 4
            """
            conditions = []
            params = []
            if state_filter:
                conditions.append(" state = %s")
                params.append(state_filter)
            if mobile_filter:
                conditions.append(" mobile_no = %s")
                params.append(mobile_filter)
            if mentor_code_filter:
                conditions.append(" pin = %s")
                params.append(mentor_code_filter)
            if conditions:
                sql += " AND " + " AND ".join(conditions)
            sql += " order by id desc"
            cursor.execute(sql, tuple(params))
            result = cursor.fetchall()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/add_mentor', methods=['POST'])
def add_mentor():
    data = request.get_json() or {}

    # Required fields
    name      = data.get('name')
    mobile_no = data.get('mobile_no')
    pin       = data.get('pin')

    if not all([name, mobile_no, pin]):
        return jsonify({"error": "name, mobile_no and pin are required"}), 400

    # Optional fields
    email = data.get('email') or None
    state = data.get('state') or None
    city  = data.get('city') or None

    # Convert gender to int or None
    gender_raw = data.get('gender')
    try:
        gender = int(gender_raw) if gender_raw is not None and gender_raw != "" else None
    except ValueError:
        return jsonify({"error": f"Invalid gender value: {gender_raw}"}), 400

    # DOB can stay as string or None
    dob = data.get('dob') or None

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
            INSERT INTO lifeapp.users
              (name, email, mobile_no, pin,
               state, city, gender, dob,
               `type`, created_at, updated_at)
            VALUES
              (%s,    %s,    %s,        %s,
               %s,     %s,     %s,     %s,
               4,       NOW(),   NOW())
            """
            cursor.execute(sql, (
                name, email, mobile_no, pin,
                state, city, gender, dob
            ))
        conn.commit()
        return jsonify({"message": "Mentor added successfully"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        conn.close()       

@app.route('/api/update_mentor', methods=['POST'])
def do_update_mentor():
    data = request.get_json() or {}
    mentor_id = data.get('id')
    if not mentor_id:
        return jsonify({'error': 'Mentor ID is required.'}), 400

    # Pull out all fields
    name      = data.get('name')      or None
    email     = data.get('email')     or None
    mobile_no = data.get('mobile_no') or None
    pin       = data.get('pin')       or None
    state     = data.get('state')     or None
    city      = data.get('city')      or None

    # Convert gender to int or None
    gender_raw = data.get('gender')
    try:
        gender = int(gender_raw) if gender_raw not in (None, '') else None
    except ValueError:
        return jsonify({'error': f'Invalid gender value: {gender_raw}'}), 400

    # DOB as string or None
    dob = data.get('dob') or None

    # Timestamp for updated_at
    updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                UPDATE lifeapp.users
                   SET name      = %s,
                       email     = %s,
                       mobile_no = %s,
                       pin       = %s,
                       state     = %s,
                       city      = %s,
                       gender    = %s,
                       dob       = %s,
                       updated_at= %s
                 WHERE id = %s
                   AND `type` = 4
            """
            params = (
                name,
                email,
                mobile_no,
                pin,
                state,
                city,
                gender,
                dob,
                updated_at,
                mentor_id
            )
            cursor.execute(sql, params)
            conn.commit()

        return jsonify({'message': 'Mentor updated successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        conn.close()

@app.route('/api/delete_mentor', methods=['POST'])
def do_delete_mentor():
    """Delete a mentor from the database."""
    try:
        data = request.get_json()
        mentor_id = data.get('id')

        if not mentor_id:
            return jsonify({'error': 'Mentor ID is required'}), 400

        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = "DELETE FROM lifeapp.users WHERE id = %s AND `type` = 4"
            cursor.execute(sql, (mentor_id,))
            connection.commit()

        return jsonify({'message': 'Mentor deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/upload_mentors_csv', methods=['POST'])
def upload_mentors_csv():
    if 'csv' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['csv']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if not file.filename.lower().endswith('.csv'):
        return jsonify({"error": "File must be a CSV"}), 400

    try:
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        reader = csv.DictReader(stream)
        required = ['name', 'email', 'mobile_no', 'mentor_code']

        conn = get_db_connection()
        count = 0
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO lifeapp.users
                  (name, email, mobile_no, pin,
                   `type`, created_at, updated_at)
                VALUES (%s, %s, %s, %s,
                        4, NOW(), NOW())
            """

            normalized_rows = []
            for raw in reader:
                # strip anything after a space in the header
                norm = { k.split(' ')[0].strip(): v for k, v in raw.items() }
                normalized_rows.append(norm)
            for row in normalized_rows:
                # skip rows missing required fields
                if not all(row.get(f) for f in required):
                    continue

                # clean & convert
                name      = row['name']
                email     = row.get('email') or None
                mobile_no = row['mobile_no']
                pin       = row.get('pin') or row.get('mentor_code')

                # state = row.get('state') or None
                # city  = row.get('city') or None

                # # gender: turn "0"/"1" into int, blank→None
                # raw = row.get('gender') 
                # raw = 0 if raw.lower() == 'male' else 1
                # try:
                #     gender = int(raw) if raw not in (None, '') else None
                # except ValueError:
                #     return jsonify({"error": f"Invalid gender value: {raw}"}), 400

                # dob = row.get('dob') or None

                cursor.execute(sql, (
                    name, email, mobile_no, pin
                ))
                count += 1

            conn.commit()
        return jsonify({"message": f"Successfully uploaded {count} mentors"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if 'conn' in locals():
            conn.close()


###################################################################################
###################################################################################
######################## MENTORS/SESSIONS APIs ###################################
###################################################################################
###################################################################################
@app.route('/api/sessions', methods=['POST'])
def get_sessions():
    """Fetch all mentor sessions with user name and status."""
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = """
                SELECT 
                    las.id,
                    u.name,
                    las.heading,
                    las.zoom_link,
                    las.zoom_password,
                    las.date_time,
                    las.status
                FROM 
                    lifeapp.la_sessions las
                INNER JOIN 
                    lifeapp.users u ON las.user_id = u.id
                ORDER BY las.date_time DESC
            """
            cursor.execute(sql)
            sessions = cursor.fetchall()

        return jsonify(sessions), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/update_session', methods=['POST'])
def update_session():
    """Update an existing session's heading, description, and status."""
    try:
        data = request.get_json()
        session_id = data.get('id')
        heading = data.get('heading')
        description = data.get('description')
        status = data.get('status')

        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = """
                UPDATE lifeapp.la_sessions
                SET heading = %s, description = %s, status = %s
                WHERE id = %s
            """
            cursor.execute(sql, (heading, description, status, session_id))
            connection.commit()
        return jsonify({'message': 'Session updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/session_participants', methods=['POST'])
def get_session_participants():
    """Get all participants of a given session ID."""
    try:
        data = request.get_json()
        session_id = data.get('session_id')

        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = """
                SELECT 
                    u.school_id, 
                    u.name, 
                    u.mobile_no, 
                    u.grade, 
                    u.city, 
                    u.state,
                    lasp.la_session_id 
                FROM 
                    lifeapp.users u 
                INNER JOIN 
                    lifeapp.la_session_participants lasp 
                ON 
                    u.id = lasp.user_id
                WHERE
                    lasp.la_session_id = %s;
            """
            cursor.execute(sql, (session_id,))
            participants = cursor.fetchall()
        return jsonify(participants), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/session_participants_total', methods = ['POST'])
def get_session_participants_total():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = """
                select count(*) as count from lifeapp.la_session_participants;
            """
            cursor.execute(sql)
            count = cursor.fetchall()
        return jsonify(count), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/mentor_participated_in_sessions_total', methods = ['POST'])
def get_mentor_participated_in_sessions_total():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = """
                select count(*) as count from lifeapp.la_session_participants lasp 
                inner join lifeapp.users u on u.id = lasp.user_id where u.type = 4 or u.type = 5;
            """
            cursor.execute(sql)
            count = cursor.fetchall()
        return jsonify(count), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()
    

###################################################################################
###################################################################################
################# MENTOR DASHBOARD AND SESSION APIs (UNUSED) ######################
###################################################################################
###################################################################################
@app.route('/api/mentor_dashboard_table', methods = ['POST'])
def get_mentor_dashboard_table():
    sql = """
        select id, name, email, mobile_no, pin as mentor_code from lifeapp.users where `type` = 4;
    """
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchall()  
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        connection.close()

# @app.route('/api/update_mentor', methods=['POST'])
# def update_mentor():
#     filters = request.get_json()
#     mentor_id = filters.get('id')

#     if not mentor_id:
#         return jsonify({'error': 'Mentor ID is required'}), 400

#     # Extracting fields to update
#     name = filters.get('name')
#     email = filters.get('email')
#     mobile_no = filters.get('mobile_no')
#     city = filters.get('city')
#     state = filters.get('state')
#     pin = filters.get('pin')
#     updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Get current timestamp

#     try:
#         connection = get_db_connection()
#         cursor = connection.cursor()

#         query = """
#             UPDATE lifeapp.users
#             SET name = %s, email = %s, mobile_no = %s, city = %s, state = %s, pin = %s, updated_at = %s
#             WHERE id = %s
#         """
#         values = (name, email, mobile_no, city, state, pin, updated_at, mentor_id)
        
#         cursor.execute(query, values)
#         connection.commit()
#         cursor.close()
#         connection.close()
        
#         return jsonify({'success': True, 'message': 'Mentor updated successfully'}), 200
#     except Error as e:
#         print("Error updating mentor:", e)
#         return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

# @app.route('/api/delete_mentor', methods=['DELETE'])
# def delete_mentor():
#     filters = request.get_json()
#     mentor_id = filters.get('id')

#     if not mentor_id:
#         return jsonify({'error': 'Mentor ID is required'}), 400

#     try:
#         connection = get_db_connection()
#         cursor = connection.cursor()

#         query = "DELETE FROM lifeapp.users WHERE id = %s"
#         cursor.execute(query, (mentor_id,))
#         connection.commit()
#         cursor.close()
#         connection.close()
        
#         return jsonify({'success': True, 'message': 'Mentor deleted successfully'}), 200
#     except Error as e:
#         print("Error deleting mentor:", e)
#         return jsonify({'error': 'Internal server error', 'details': str(e)}), 500




###################################################################################
@app.route('/api/student_count_by_level_778', methods=['POST'])
def student_count_by_level_778():
    """
    POST body (JSON) can include an optional "level" filter.
    If level is not provided or is 'all', then return counts for all levels:
      level1: type=3 and grade >= 1
      level2: type=3 and grade >= 6
      level3: type=3 and grade >= 7
      level4: type=3 and grade >= 8

    If level is specified (as "1", "2", "3" or "4"), then return:
      for level 1: count of students with type=3 and grade>=1,
      for level 2: count of students with type=3 and grade>=6,
      for level 3: count of students with type=3 and grade>=7,
      for level 4: count of students with type=3 and grade>=8.
    """
    level = None
    # if request.method == 'POST':
    data = request.get_json() or {}
    level = data.get('level', 'all')  # default to all

    try:
        connection = get_db_connection()
        with connection:
            with connection.cursor() as cursor:
                if level in [None, '', 'all']:
                    # Return counts for all levels
                    query = """
                    SELECT 
                        SUM(CASE WHEN type = 3 AND grade >= 1 THEN 1 ELSE 0 END) AS level1_count,
                        SUM(CASE WHEN type = 3 AND grade >= 6 THEN 1 ELSE 0 END) AS level2_count,
                        SUM(CASE WHEN type = 3 AND grade >= 7 THEN 1 ELSE 0 END) AS level3_count,
                        SUM(CASE WHEN type = 3 AND grade >= 8 THEN 1 ELSE 0 END) AS level4_count
                    FROM lifeapp.users;
                    """
                    cursor.execute(query)
                    result = cursor.fetchone()
                    return jsonify(result)
                else:
                    # For a specified level, choose condition accordingly.
                    if level == "1":
                        cond = "grade >= 1"
                    elif level == "2":
                        cond = "grade >= 6"
                    elif level == "3":
                        cond = "grade >= 7"
                    elif level == "4":
                        cond = "grade >= 8"
                    else:
                        return jsonify({"error": "Invalid level parameter"}), 400

                    query = f"""
                    SELECT COUNT(*) AS count 
                    FROM lifeapp.users
                    WHERE type = 3 AND {cond};
                    """
                    cursor.execute(query)
                    result = cursor.fetchone()
                    return jsonify({
                        'level1_count': result[0],
                        'level2_count': result[1],
                        'level3_count': result[2],
                        'level4_count': result[3]
                    })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
#### permission denied in digital ocean,
@app.route('/api/correct-tamil-nadu-users', methods=['POST'])
def correction_tamil_nadu_users():
    sql = """
        UPDATE lifeapp.users 
        SET state = 'Tamil Nadu' 
        WHERE state = 'Tamilnadu';
    """
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(sql)
            connection.commit()  # Commit the transaction
        return jsonify({"message": "Success in correcting the name"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        connection.close()

###################################################################################
###################################################################################
###################################################################################
##################### RESOURCES/STUDENT_RELATED/MISSION APIs ######################
###################################################################################
###################################################################################
@app.route('/api/missions_resource', methods=['POST'])
def get_missions_resource():
    try:
        filters = request.json
        connection = get_db_connection()
        with connection.cursor() as cursor:
            base_query = """
                SELECT
                    lam.id,
                    lam.title,
                    lam.description,
                    lam.question,
                    lam.type,
                    CASE WHEN lam.allow_for=1 THEN 'All' ELSE 'Teacher' END AS allow_for,
                    lam.la_subject_id AS subject_id,
                    las.title         AS subject,
                    lam.la_level_id   AS level_id,
                    lal.title         AS level,
                    lam.status        AS status,
                    JSON_UNQUOTE(JSON_EXTRACT(lam.image, '$.en'))         AS image_id,
                    mimg.path         AS image_path,
                    lamr.id 		  AS resource_id,
                    document.id       AS media_id,
                    document.path     AS resource_path,
                    lamr.`index`      AS idx
                FROM lifeapp.la_missions lam
                JOIN lifeapp.la_subjects las ON las.id = lam.la_subject_id
                JOIN lifeapp.la_levels   lal ON lal.id = lam.la_level_id
                LEFT JOIN lifeapp.media mimg ON mimg.id = JSON_UNQUOTE(JSON_EXTRACT(lam.image, '$.en'))
                LEFT JOIN lifeapp.la_mission_resources lamr ON lamr.la_mission_id = lam.id
                LEFT JOIN lifeapp.media document ON document.id = lamr.media_id
                WHERE 1=1
            """

            params = []
            
            if filters.get('status'):
                base_query += " AND lam.status = %s"
                params.append(filters['status'])
            if filters.get('type'):
                base_query += " AND lam.type = %s"
                params.append(filters['type'])
            if filters.get('subject'):
                # Match subject ID instead of title
                base_query += " AND lam.la_subject_id = %s"
                params.append(filters['subject'])
            if filters.get('level'):
                # Match level ID instead of title
                base_query += " AND lam.la_level_id = %s"
                params.append(filters['level'])

             # Order by mission then resource index
            base_query += " ORDER BY lam.id, lamr.`index`"
            cursor.execute(base_query, params)
            rows = cursor.fetchall() 
            # cursor.execute(base_query, params)
            # data = cursor.fetchall()
            # Build full URLs
            base_url = os.getenv('BASE_URL', '')  # e.g. 'https://cdn.example.com'
            missions = {}
            for row in rows:
                mid = row['id']
                if mid not in missions:
                    missions[mid] = {
                        'id':           row['id'],
                        'title':        row['title'],
                        'description':  row['description'],
                        'question':     row['question'],
                        'type':         row['type'],
                        'allow_for':    row['allow_for'],
                        'subject_id':   row['subject_id'],
                        'subject':      row['subject'],
                        'level_id':     row['level_id'],
                        'level':        row['level'],
                        'status':       row['status'],
                        'image_id':     row['image_id'],
                        'image_url':    f"{base_url}/{row['image_path']}" if row.get('image_path') else None,
                        'resources':    []
                    }
                # Append resource if exists
                if row.get('resource_id'):
                    missions[mid]['resources'].append({
                        'resource_id': row['resource_id'],
                        'media_id':    row['media_id'],
                        'url':         f"{base_url}/{row['resource_path']}"
                    })

            return jsonify(list(missions.values())), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/add_mission', methods=['POST'])
def add_mission():
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            form = request.form

            # Read normal fields
            subject    = form.get('subject')
            level      = form.get('level')
            type_id    = form.get('type')
            allow_for  = form.get('allow_for')
            status     = int(form.get('status', 0))
            raw_title  = form.get('title', '')
            raw_desc   = form.get('description', '')
            raw_ques   = form.get('question', '')

            # Wrap text fields inside {"en": "text"}
            title_json       = json.dumps({"en": raw_title})
            description_json = json.dumps({"en": raw_desc})
            question_json    = json.dumps({"en": raw_ques})

            # Initialize
            image_json = None
            document_json = None

            # Handle image upload
            image_file = request.files.get('image')
            if image_file and image_file.filename:
                media = upload_media(image_file)
                image_json = json.dumps({"en": media['id']})

            # Handle document upload
            # doc_file = request.files.get('document')
            # if doc_file and doc_file.filename:
            #     media = upload_media(doc_file)
            document_json = json.dumps({"en": None})

            # Prepare SQL
            sql = """
                INSERT INTO lifeapp.la_missions
                  (la_subject_id, la_level_id, `type`, allow_for,
                   title, description, question,
                   image, document,
                   created_at, updated_at, status)
                VALUES
                  (%s, %s, %s, %s,
                   %s, %s, %s,
                   %s, %s,
                   NOW(), NOW(), %s)
            """
            params = (
                subject, level, type_id, allow_for,
                title_json, description_json, question_json,
                image_json, document_json,
                status
            )

            cursor.execute(sql, params)
            mission_id = cursor.lastrowid

            files = request.files.getlist('documents')
            for idx, file in enumerate(files[:4], start=1):
                media = upload_media(file)
                cursor.execute("""
                    INSERT INTO lifeapp.la_mission_resources
                      (la_mission_id, title, media_id, `index`, created_at, updated_at, locale)
                    VALUES (%s, %s, %s, %s, NOW(), NOW(), %s)
                """, (mission_id, file.filename, media['id'], idx, 'en'))

            
            connection.commit()

            return jsonify({"id": mission_id}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        connection.close()


@app.route('/api/delete_mission', methods=['POST'])
def delete_mission():
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            mission_id = request.json.get('id')

            if not mission_id:
                return jsonify({'error': 'Missing mission id'}), 400

            # 1) Delete all resource‐media rows
            cursor.execute(
              "SELECT media_id FROM lifeapp.la_mission_resources WHERE la_mission_id = %s",
              (mission_id,)
            )
            for row in cursor.fetchall():
                rid = row.get('media_id')
                if rid:
                    cursor.execute("DELETE FROM lifeapp.media WHERE id = %s", (rid,))
            cursor.execute(
              "DELETE FROM lifeapp.la_mission_resources WHERE la_mission_id = %s",
              (mission_id,)
            )

            # 2) Delete thumbnail media
            cursor.execute("""
                SELECT 
                    JSON_UNQUOTE(JSON_EXTRACT(image, '$.en')) AS image_id,
                    JSON_UNQUOTE(JSON_EXTRACT(document, '$.en')) AS document_id
                FROM lifeapp.la_missions
                WHERE id = %s
            """, (mission_id,))
            mission = cursor.fetchone()

            if not mission:
                return jsonify({'error': 'Mission not found'}), 404

            image_id = mission.get('image_id')
            # document_id = mission.get('document_id')

            # 2.a. Delete associated media entries
            if image_id:
                cursor.execute("DELETE FROM lifeapp.media WHERE id = %s", (image_id,))
            # if document_id:
            #     cursor.execute("DELETE FROM lifeapp.media WHERE id = %s", (document_id,))

            # 3. Delete the mission itself
            cursor.execute("DELETE FROM lifeapp.la_missions WHERE id = %s", (mission_id,))

            connection.commit()

        return jsonify({'success': True}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/update_mission', methods=['POST'])
def update_mission():
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            form = request.form

            # Read normal fields
            mission_id = form.get('id')
            subject    = form.get('subject')
            level      = form.get('level')
            type_id    = form.get('type')
            allow_for  = form.get('allow_for')
            status     = int(form.get('status', 0))
            raw_title  = form.get('title', '')
            raw_desc   = form.get('description', '')
            raw_ques   = form.get('question', '')

            # Wrap text fields
            title_json       = json.dumps({"en": raw_title})
            description_json = json.dumps({"en": raw_desc})
            question_json    = json.dumps({"en": raw_ques})

            # 2) Fetch old image_id so we can delete it if replaced
            cursor.execute(
              "SELECT image FROM lifeapp.la_missions WHERE id = %s", (mission_id,)
            )
            old_img = cursor.fetchone().get('image')
            # # Handle image upload
            # image_file = request.files.get('image')
            # if image_file:
            #     media = upload_media(image_file)
            #     image_json = json.dumps({"en": media['id']})
            # else:
            #     image_json = json.dumps({"en": None})

            # # Handle document upload
            # doc_file = request.files.get('document')
            # if doc_file:
            #     media = upload_media(doc_file)
            #     document_json = json.dumps({"en": media['id']})
            # else:
            #     document_json = json.dumps({"en": None})

            # Build dynamic UPDATE SQL
            update_sql = """
                UPDATE lifeapp.la_missions
                SET
                  la_subject_id = %s,
                  la_level_id   = %s,
                  `type`        = %s,
                  allow_for     = %s,
                  title         = %s,
                  description   = %s,
                  question      = %s,
                  status        = %s,
                  updated_at    = NOW()
            """
            params = [
                subject, level, type_id, allow_for,
                title_json, description_json, question_json,
                status
            ]

            # Only add image/document if provided
            # Conditionally overwrite only if a new file arrives
            image_file = request.files.get('image')
            if image_file and image_file.filename:
                media = upload_media(image_file)
                update_sql += ", image = %s"
                params.append(json.dumps({'en': media['id']}))
                if old_img:
                    cursor.execute("DELETE FROM lifeapp.media WHERE id = JSON_UNQUOTE(JSON_EXTRACT(%s, '$.en'))", (old_img,))


            update_sql += " WHERE id = %s"
            params.append(mission_id)

            cursor.execute(update_sql, tuple(params))

            # doc_file = request.files.get('document')
            # if doc_file and doc_file.filename:
            #     media = upload_media(doc_file)
            #     update_sql += ", document = %s"
            #     params.append(json.dumps({'en': media['id']}))

            files = request.files.getlist('documents')
            if files:
                # fetch & delete old document media
                cursor.execute(
                  "SELECT media_id FROM lifeapp.la_mission_resources WHERE la_mission_id = %s",
                  (mission_id,)
                )
                for row in cursor.fetchall():
                    old_res_mid = row.get('media_id')
                    if old_res_mid:
                        cursor.execute("DELETE FROM lifeapp.media WHERE id = %s", (old_res_mid,))
                # delete old resource rows
                cursor.execute(
                  "DELETE FROM lifeapp.la_mission_resources WHERE la_mission_id = %s",
                  (mission_id,)
                )
                # insert new ones
                for idx, file in enumerate(files[:4], start=1):
                    media = upload_media(file)
                    cursor.execute("""
                        INSERT INTO lifeapp.la_mission_resources
                          (la_mission_id, title, media_id, `index`, created_at, updated_at, locale)
                        VALUES (%s, %s, %s, %s, NOW(), NOW(), 'en')
                    """, (mission_id, file.filename, media['id'], idx))

            connection.commit()

            return jsonify({"success": True}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        connection.close()

###################################################################################
###################################################################################
############## RESOURCES/STUDENT_RELATED/QUIZ questions APIs ######################
###################################################################################
###################################################################################

# @app.route('/api/quiz_questions', methods=['POST'])
# def get_quiz_questions():
#     data =  request.get_json() or {}
#     subject_id = data.get('subject_id')
#     level_id = data.get('level_id')
#     status = data.get('status')

#     connection = get_db_connection()
#     try: 
#         with connection.cursor() as cursor:

#             base_query = """
#                 SELECT laq.id, laq.title as question_title, lal.title as level_title, las.title as subject_title,
#                     CASE WHEN laq.status = 0 THEN 'Inactive' ELSE 'Active' END as status,
#                     laq.la_topic_id,
#                     CASE 
#                         WHEN laq.type = 2 THEN 'Quiz'
#                         WHEN laq.type = 3 THEN 'Riddle'
#                         WHEN laq.type = 4 THEN 'Puzzle'
#                         ELSE 'Default'
#                     END as game_type,
#                     CASE 
#                         WHEN laq.question_type = 1 THEN 'Text'
#                         WHEN laq.question_type = 2 THEN 'Image'
#                         ELSE 'Default'
#                     END as question_type,
#                     CASE 
#                         WHEN laq.answer_option_id = laqo.id THEN 1 ELSE 0
#                     END as is_answer,
#                     laqo.title as answer_option
#                 FROM lifeapp.la_question_options laqo
#                 INNER JOIN lifeapp.la_questions laq ON laq.id = laqo.question_id
#                 INNER JOIN lifeapp.la_levels lal ON lal.id = laq.la_level_id
#                 INNER JOIN lifeapp.la_subjects las ON las.id = laq.la_subject_id
#                 WHERE 1 = 1
#             """
#             filters = []
#             if subject_id:
#                 base_query += " AND laq.la_subject_id = %s"
#                 filters.append(subject_id)
#             if level_id:
#                 base_query += " AND laq.la_level_id = %s"
#                 filters.append(level_id)

#             if status in ('0', '1'):
#                 base_query += " AND laq.status = %s"
#                 filters.append(int(status))

#             cursor.execute(base_query, filters)
#             results = cursor.fetchall()

#             return jsonify(results)
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500
#     finally:
#         connection.close()

@app.route('/api/quiz_questions', methods=['POST'])
def get_quiz_questions():
    data = request.get_json() or {}
    subject_id = data.get('subject_id')
    level_id = data.get('level_id')
    status = data.get('status')
    topic_id = data.get('topic_id')
    game_type_filter = data.get('type')
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            base_query = """
                SELECT laq.id, laq.title as question_title, lal.title as level_title, las.title as subject_title,
                    CASE WHEN laq.status = 0 THEN 'Inactive' ELSE 'Active' END as status, laq.index,
                    laq.la_topic_id,
                    lat.title as topic_title,
                    CASE 
                        WHEN laq.type = 2 THEN 'Quiz'
                        WHEN laq.type = 3 THEN 'Riddle'
                        WHEN laq.type = 4 THEN 'Puzzle'
                        ELSE 'Default'
                    END as game_type,
                    CASE 
                        WHEN laq.question_type = 1 THEN 'Text'
                        WHEN laq.question_type = 2 THEN 'Image'
                        ELSE 'Default'
                    END as question_type,
                    CASE 
                        WHEN laq.answer_option_id = laqo.id THEN 1 ELSE 0
                    END as is_answer,
                    laqo.title as answer_option
                FROM lifeapp.la_question_options laqo
                INNER JOIN lifeapp.la_questions laq ON laq.id = laqo.question_id
                INNER JOIN lifeapp.la_levels lal ON lal.id = laq.la_level_id
                INNER JOIN lifeapp.la_subjects las ON las.id = laq.la_subject_id
                LEFT JOIN lifeapp.la_topics lat ON laq.la_topic_id = lat.id
                WHERE 1 = 1
            """
            filters = []
            if subject_id:
                base_query += " AND laq.la_subject_id = %s"
                filters.append(subject_id)
            if level_id:
                base_query += " AND laq.la_level_id = %s"
                filters.append(level_id)
            if status is not None and status != "" and status.lower() != "all":
                base_query += " AND laq.status = %s"
                filters.append(status)
            if topic_id:
                base_query += " AND laq.la_topic_id = %s"
                filters.append(topic_id)
            if game_type_filter:
                base_query += " AND laq.type = %s"
                filters.append(game_type_filter) 
            cursor.execute(base_query, filters)
            results = cursor.fetchall()
            return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/add_quiz_question', methods=['POST'])
def add_quiz_question():
    """
    Expects JSON payload, where:
    - question_title is a JSON string (e.g. "{\"en\":\"...\"}")
    - options[].title is a JSON string (e.g. "{\"en\":\"Option 1\"}")
    """
    data = request.get_json() or {}

    # Required
    try:
        question_json = data['question_title']
        subject_id    = data['subject_id']
        level_id      = data['level_id']
        options       = data['options']
    except KeyError as e:
        return jsonify({"error": f"Missing field: {e}"}), 400

    # Optional / defaults
    topic_id      = data.get('topic_id', 1)
    created_by    = data.get('created_by', 1)
    question_type = data.get('question_type', 1)
    game_type     = data.get('type', 2)
    status        = data.get('status', 1)
    now           = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1) Insert question
            sql_q = """
                INSERT INTO lifeapp.la_questions
                  (title, la_subject_id, la_level_id, la_topic_id,
                   created_by, question_type, `type`, status,
                   created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql_q, (
                question_json,
                subject_id,
                level_id,
                topic_id,
                created_by,
                question_type,
                game_type,
                status,
                now,
                now
            ))
            question_id = cursor.lastrowid

            # 2) Insert options
            sql_o = """
                INSERT INTO lifeapp.la_question_options
                  (question_id, title, created_at, updated_at)
                VALUES (%s, %s, %s, %s)
            """
            answer_option_id = None
            for opt in options:
                title_json = opt['title']
                cursor.execute(sql_o, (question_id, title_json, now, now))
                opt_id = cursor.lastrowid
                if opt.get('is_correct'):
                    answer_option_id = opt_id

            # 3) Link correct answer
            if answer_option_id is not None:
                cursor.execute(
                    "UPDATE lifeapp.la_questions SET answer_option_id = %s WHERE id = %s",
                    (answer_option_id, question_id)
                )

            conn.commit()
        return jsonify({"success": True, "question_id": question_id}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        conn.close()

@app.route('/api/update_quiz_question/<int:question_id>', methods=['PUT'])
def update_quiz_question(question_id):
    data = request.get_json() or {}

    # required
    qt_raw    = data.get('question_title', '')
    subject   = data.get('subject_id')
    level     = data.get('level_id')
    options   = data.get('options', [])

    # optional
    topic     = data.get('topic_id', 1)

    # Fix for status: handle both string formats
    status_val = data.get('status')
    if status_val == 'Active':
        status = 1
    elif status_val == 'Inactive':
        status = 0
    else:
        # Handle numeric strings like "1" or "0"
        status = int(status_val) if status_val is not None else 1

    q_type    = int(data.get('question_type', 1))
    game_type = int(data.get('type', 2))
    now       = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Check if question_title is already a JSON string
    if isinstance(qt_raw, str) and (qt_raw.startswith('{') or not qt_raw):
        question_json = qt_raw if qt_raw else json.dumps({"en": ""})
    else:
        question_json = json.dumps({"en": qt_raw})

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1) update question row
            cursor.execute("""
                UPDATE lifeapp.la_questions
                SET
                  title         = %s,
                  la_subject_id = %s,
                  la_level_id   = %s,
                  la_topic_id   = %s,
                  status        = %s,
                  question_type = %s,
                  `type`        = %s,
                  updated_at    = %s
                WHERE id = %s
            """, (
                question_json,
                subject, level, topic,
                status, q_type, game_type,
                now, question_id
            ))
            conn.commit()

            # 2) delete old options
            cursor.execute(
                "DELETE FROM lifeapp.la_question_options WHERE question_id = %s",
                (question_id,)
            )
            conn.commit()

            # 3) re-insert options, wrapping each title
            answer_option_id = None
            for opt in options:
                # Handle option title
                opt_title = opt.get('title', '')
                
                # Check if it's already a JSON string
                if isinstance(opt_title, str) and (opt_title.startswith('{') or not opt_title):
                    opt_json = opt_title if opt_title else json.dumps({"en": ""})
                else:
                    opt_json = json.dumps({"en": opt_title})
                
                cursor.execute("""
                    INSERT INTO lifeapp.la_question_options
                      (question_id, title, created_at, updated_at)
                    VALUES (%s, %s, %s, %s)
                """, (question_id, opt_json, now, now))
                oid = cursor.lastrowid
                
                # Check if this is the correct answer
                is_correct = False
                if 'is_correct' in opt and opt['is_correct']:
                    is_correct = True
                elif 'is_answer' in opt and opt['is_answer'] == 1:
                    is_correct = True
                    
                if is_correct:
                    answer_option_id = oid

            # 4) link correct answer
            if answer_option_id is not None:
                cursor.execute("""
                    UPDATE lifeapp.la_questions
                    SET answer_option_id = %s
                    WHERE id = %s
                """, (answer_option_id, question_id))
                conn.commit()

        return jsonify({"success": True}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        conn.close()

@app.route('/api/delete_quiz_question/<int:question_id>', methods=['DELETE'])
def delete_quiz_question(question_id):
    """
    Deletes the question with the given ID and all its options.
    """
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # 1) Remove all options for this question
            cursor.execute(
                "DELETE FROM lifeapp.la_question_options WHERE question_id = %s",
                (question_id,)
            )

            # 2) Remove the question itself
            cursor.execute(
                "DELETE FROM lifeapp.la_questions WHERE id = %s",
                (question_id,)
            )

            connection.commit()

        return jsonify({"success": True, "message": "Question deleted successfully"}), 200

    except Exception as e:
        # Log the error if you have a logging setup, then return
        return jsonify({"error": str(e)}), 500

    finally:
        connection.close()

@app.route('/api/download_quiz_template', methods=['GET'])
def download_quiz_template():
    # a simple 2‑row example; you can expand it if you like
    csv_content = """questions,option1,option2,option3,option4,answer
how are you?,good,bad,worst,ok,option1
how old are you?,ten,eleven,twelve,thirteen,option3
"""
    return Response(
        csv_content,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=quiz_template.csv'}
    )

@app.route('/api/import_quiz_questions_csv', methods=['POST'])
def import_quiz_questions_csv():
    subject_id = request.form.get('subject_id')
    level_id   = request.form.get('level_id')
    topic_id   = request.form.get('topic_id')
    f          = request.files.get('file')
    if not (subject_id and level_id and topic_id and f):
        return jsonify({'error':'Missing subject_id, level_id, topic_id or file'}),400

    # read CSV
    stream = io.StringIO(f.stream.read().decode('utf‑8'))
    reader = csv.DictReader(stream)
    inserted = 0
    now = datetime.now().strftime('%Y‑%m‑%d %H:%M:%S')

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            for row in reader:
                q_text = row.get('questions','').strip()
                if not q_text:
                    continue

                # 1) insert question
                q_json = json.dumps({'en': q_text})
                cursor.execute("""
                    INSERT INTO lifeapp.la_questions
                      (title, la_subject_id, la_level_id, la_topic_id,
                       created_by, question_type, `type`, status,
                       created_at, updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    q_json,
                    subject_id,
                    level_id,
                    topic_id,
                    1,      # created_by
                    1,      # question_type = Text
                    2,      # game_type = Quiz
                    1,      # status = Active
                    now,
                    now
                ))
                qid = cursor.lastrowid

                # 2) insert options
                answer_key = row.get('answer','').strip().lower()  # e.g. 'option1'
                correct_idx = None
                if answer_key.startswith('option'):
                    try:
                        correct_idx = int(answer_key.replace('option','')) - 1
                    except:
                        correct_idx = None

                answer_option_id = None
                for idx, col in enumerate(['option1','option2','option3','option4']):
                    txt = row.get(col,'').strip()
                    opt_json = json.dumps({'en': txt})
                    cursor.execute("""
                        INSERT INTO lifeapp.la_question_options
                          (question_id, title, created_at, updated_at)
                        VALUES (%s,%s,%s,%s)
                    """, (qid, opt_json, now, now))
                    oid = cursor.lastrowid
                    if correct_idx is not None and idx == correct_idx:
                        answer_option_id = oid

                # 3) link correct answer
                if answer_option_id:
                    cursor.execute("""
                        UPDATE lifeapp.la_questions
                           SET answer_option_id = %s
                         WHERE id = %s
                    """, (answer_option_id, qid))

                inserted += 1

            conn.commit()
        return jsonify({'success': True, 'inserted': inserted}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/updated_today', methods=['POST'])
def get_questions_updated_today():
    """
    Returns a list of question IDs that were updated today.
    Optional filters: subject_id, level_id, topic_id, type
    """
    data = request.get_json() or {}
    subject_id = data.get('subject_id')
    level_id   = data.get('level_id')
    topic_id   = data.get('topic_id')
    game_type  = data.get('type')

    today = datetime.now().strftime('%Y-%m-%d')

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            query = """
                SELECT id, title, updated_at
                FROM lifeapp.la_questions
                WHERE DATE(updated_at) = %s
            """
            filters = [today]

            if subject_id:
                query += " AND la_subject_id = %s"
                filters.append(subject_id)
            if level_id:
                query += " AND la_level_id = %s"
                filters.append(level_id)
            if topic_id:
                query += " AND la_topic_id = %s"
                filters.append(topic_id)
            if game_type:
                query += " AND `type` = %s"
                filters.append(game_type)

            cursor.execute(query, filters)
            rows = cursor.fetchall()
            return jsonify(rows), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/options_updated_today', methods=['POST'])
def get_options_updated_today():
    """
    Returns list of question options that were updated today.
    Optional filters: question_id, subject_id, level_id, topic_id, type
    """
    data = request.get_json() or {}
    question_id = data.get('question_id')
    subject_id  = data.get('subject_id')
    level_id    = data.get('level_id')
    topic_id    = data.get('topic_id')
    game_type   = data.get('type')

    today = datetime.now().strftime('%Y-%m-%d')

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            query = """
                SELECT laqo.id, laqo.title, laqo.updated_at,
                       laqo.question_id, laq.title AS question_title
                FROM lifeapp.la_question_options laqo
                JOIN lifeapp.la_questions laq ON laqo.question_id = laq.id
                WHERE DATE(laqo.updated_at) = %s
            """
            filters = [today]

            if question_id:
                query += " AND laqo.question_id = %s"
                filters.append(question_id)
            if subject_id:
                query += " AND laq.la_subject_id = %s"
                filters.append(subject_id)
            if level_id:
                query += " AND laq.la_level_id = %s"
                filters.append(level_id)
            if topic_id:
                query += " AND laq.la_topic_id = %s"
                filters.append(topic_id)
            if game_type:
                query += " AND laq.type = %s"
                filters.append(game_type)

            cursor.execute(query, filters)
            rows = cursor.fetchall()
            return jsonify(rows), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/delete_today_questions', methods=['DELETE'])
def delete_today_questions_and_options():
    """
    Deletes all questions and their options that were created or updated today.
    """
    today = datetime.now().strftime('%Y-%m-%d')
    conn = get_db_connection()
    
    try:
        with conn.cursor() as cursor:
            # 1. Get all question IDs updated or created today
            cursor.execute("""
                SELECT id FROM lifeapp.la_questions
                WHERE DATE(created_at) = %s OR DATE(updated_at) = %s
            """, (today, today))
            question_ids = [row['id'] for row in cursor.fetchall()]

            if not question_ids:
                return jsonify({"message": "No questions found for today"}), 200

            # 2. Delete their options
            cursor.execute("""
                DELETE FROM lifeapp.la_question_options
                WHERE question_id IN %s
            """, (tuple(question_ids),))

            # 3. Delete the questions
            cursor.execute("""
                DELETE FROM lifeapp.la_questions
                WHERE id IN %s
            """, (tuple(question_ids),))

            conn.commit()
            return jsonify({
                "success": True,
                "message": f"Deleted {len(question_ids)} question(s) and their options"
            }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        conn.close()

###################################################################################
###################################################################################
############## RESOURCES/STUDENT_RELATED/VISIONS APIs ######################
###################################################################################
###################################################################################
# 1. Fetch Visions + Questions (with filters)
@app.route('/api/visions', methods=['GET'])
def fetch_visions():
    # URL query params: status, subject_id, level_id
    qs      = request.args
    status  = qs.get('status')       # '1','0' or None
    subject = qs.get('subject_id')
    level   = qs.get('level_id')

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # fetch vision + question rows
            sql = """
            SELECT
              v.id            AS vision_id,
              JSON_UNQUOTE(JSON_EXTRACT(v.title,'$.en'))       AS title,
              JSON_UNQUOTE(JSON_EXTRACT(v.description,'$.en')) AS description,
              v.youtube_url,
              v.allow_for,
              JSON_UNQUOTE(JSON_EXTRACT(s.title,'$.en'))       AS subject,
              JSON_UNQUOTE(JSON_EXTRACT(l.title,'$.en'))       AS level,
              v.status,
              q.id            AS question_id,
              q.question_type,
              JSON_UNQUOTE(JSON_EXTRACT(q.question,'$.en'))    AS question,
              q.options,
              q.correct_answer
            FROM lifeapp.visions v
            LEFT JOIN lifeapp.la_subjects s ON s.id = v.la_subject_id
            LEFT JOIN lifeapp.la_levels   l ON l.id = v.la_level_id
            LEFT JOIN lifeapp.vision_questions q ON q.vision_id = v.id
            WHERE 1=1
            """
            params = []
            if status in ('0','1'):
                sql += " AND v.status=%s";    params.append(int(status))
            if subject:
                sql += " AND v.la_subject_id=%s"; params.append(subject)
            if level:
                sql += " AND v.la_level_id=%s";   params.append(level)

            sql += " ORDER BY v.id DESC"
            cursor.execute(sql, params)
            rows = cursor.fetchall()

            # group per vision
            visions = {}
            for r in rows:
                vid = r['vision_id']
                if vid not in visions:
                    visions[vid] = {
                      'vision_id': vid,
                      'title':     r['title'],
                      'description': r['description'],
                      'youtube_url': r['youtube_url'],
                      'allow_for':   r['allow_for'],
                      'subject':     r['subject'],
                      'level':       r['level'],
                      'status':      r['status'],
                      'questions': []
                    }
                # append each question
                visions[vid]['questions'].append({
                  'question_id':    r['question_id'],
                  'question_type':  r['question_type'],
                  'question':       r['question'],
                  'options':        r['options'] and json.loads(r['options']),
                  'correct_answer': r['correct_answer']
                })
            return jsonify(list(visions.values())), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# 2. Add Vision + Question
@app.route('/api/visions', methods=['POST'])
def add_vision():
    data = request.get_json() or {}
    required = ['title','description','allow_for','subject_id','level_id','status','questions']
    for f in required:
        if f not in data:
            return jsonify({'error': f'Missing field {f}'}), 400

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # vision fields
    vsql = """INSERT INTO lifeapp.visions
      (title,description,youtube_url,allow_for,la_subject_id,la_level_id,status,created_at,updated_at)
      VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
    vparams = (
      json.dumps({'en':data['title']}),
      json.dumps({'en':data['description']}),
      data.get('youtube_url'),
      int(data['allow_for']),
      data['subject_id'],
      data['level_id'],
      int(data['status']),
      now, now
    )
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(vsql, vparams)
            vid = cur.lastrowid

            # insert each question object
            for q in data['questions']:
                qsql = """INSERT INTO lifeapp.vision_questions
                  (vision_id,question,question_type,options,correct_answer,created_at,updated_at)
                  VALUES(%s,%s,%s,%s,%s,%s,%s)"""
                qparams = (
                  vid,
                  json.dumps({'en': q['question']}),
                  q['question_type'],
                  json.dumps(q.get('options')) if q.get('options') else None,
                  q.get('correct_answer'),
                  now, now
                )
                cur.execute(qsql, qparams)

            conn.commit()
            return jsonify({'vision_id': vid}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# 3. Update Vision + All Questions
@app.route('/api/visions/<int:vision_id>', methods=['PUT'])
def update_vision(vision_id):
    data = request.get_json() or {}
    # ensure all required fields are present
    required = [
        'title','description','youtube_url',
        'allow_for','subject_id','level_id','status',
        'questions'
    ]
    for f in required:
        if f not in data:
            return jsonify({'error': f'Missing field {f}'}), 400

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1) update the parent vision row
            cursor.execute("""
                UPDATE lifeapp.visions
                SET
                  title         = %s,
                  description   = %s,
                  youtube_url   = %s,
                  allow_for     = %s,
                  la_subject_id = %s,
                  la_level_id   = %s,
                  status        = %s,
                  updated_at    = %s
                WHERE id = %s
            """, (
                json.dumps({'en': data['title']}),
                json.dumps({'en': data['description']}),
                data.get('youtube_url'),
                int(data['allow_for']),
                data['subject_id'],
                data['level_id'],
                int(data['status']),
                now,
                vision_id
            ))

            # 2) remove *all* existing questions for this vision
            cursor.execute(
                "DELETE FROM lifeapp.vision_questions WHERE vision_id = %s",
                (vision_id,)
            )

            # 3) re‑insert exactly the questions array from the payload
            for q in data['questions']:
                cursor.execute("""
                    INSERT INTO lifeapp.vision_questions
                      (vision_id, question, question_type,
                       options, correct_answer,
                       created_at, updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                """, (
                    vision_id,
                    json.dumps({'en': q['question']}),
                    q['question_type'],
                    json.dumps(q.get('options')) if q.get('options') else None,
                    q.get('correct_answer'),
                    now, now
                ))

            conn.commit()
            return jsonify({'success': True}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        conn.close()

# 4. Delete Vision + All Questions
@app.route('/api/visions/<int:vision_id>', methods=['DELETE'])
def delete_vision(vision_id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # delete all questions for this vision
            cursor.execute("DELETE FROM lifeapp.vision_questions WHERE vision_id=%s", (vision_id,))
            # then delete the vision record
            cursor.execute("DELETE FROM lifeapp.visions WHERE id=%s", (vision_id,))
            conn.commit()
            return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

###################################################################################
###################################################################################
######################## SETTINGS/SUBJECTS APIs ###################################
###################################################################################
###################################################################################

# @app.route('/api/subjects_list', methods=['POST'])
# def get_subjects():
#     """Fetch all subjects."""
#     try:
#         connection = get_db_connection()
#         with connection.cursor() as cursor:
#             sql = "SELECT id, title, heading, image, status FROM lifeapp.la_subjects ORDER BY id;"
#             cursor.execute(sql)
#             subjects = cursor.fetchall()
#         return jsonify(subjects)
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500
#     finally:
#         connection.close()

@app.route('/api/subjects_list', methods=['POST'])
def get_subjects():
    """Fetch subjects with an optional status filter.
       Expects a JSON payload with key 'status' that can be "1", "0", or "all".
       "all" returns all subjects.
    """
    try:
        data = request.get_json() or {}
        status = data.get('status', 'all')  # Default to "all" if not provided

        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = """
                SELECT s.id, s.title, s.heading, 
                JSON_EXTRACT(s.image, '$.en') AS media_id, 
                m.path AS media_path,
                s.status 
                FROM lifeapp.la_subjects s 
                LEFT JOIN lifeapp.media m
                    on m.id = JSON_EXTRACT(s.image, '$.en')
                WHERE 1=1
            """
            filters = []
            if status != "all":
                sql += " AND status = %s"
                filters.append(int(status))
            sql += " ORDER BY id;"
            cursor.execute(sql, filters)
            subjects = cursor.fetchall()
            base_url = os.getenv('BASE_URL')
            for r in subjects:
                r['media_url'] = f"{base_url}/{r['media_path']}" if r.get('media_path') else None
        
        return jsonify(subjects)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/subjects_new', methods=['POST'])
def create_subject():
    """
    Expects multipart/form-data:
      - title: valid JSON string, e.g. '{"en":"Science"}'
      - heading: valid JSON string
      - created_by: integer user ID
      - image: file upload (optional)
    """
    form = request.form
    file = request.files.get('image')
    image_id = None

    # 1) If an image file was uploaded, store it and record its media ID
    if file and file.filename:
        media = upload_media(file)
        image_id = media['id']

    title      = form.get('title', '').strip()
    heading    = form.get('heading', '').strip()
    created_by = form.get('created_by')
    status = form.get('status',0)

    # Validate required fields
    if not title or not created_by:
        return jsonify({'error': 'title and created_by are required'}), 400

    # Validate that title and heading are proper JSON
    try:
        # Ensure they're valid JSON
        json.loads(title)
        json.loads(heading)
    except json.JSONDecodeError:
        return jsonify({'error': 'title and heading must be valid JSON objects'}), 400
    
    # Map created_by from role name to user ID if needed
    # This example assumes you have a simple mapping, but you might need
    # to look up actual IDs from a users table
    role_to_id = {"Admin": 1, "Mentor": 4, "Teacher": 5}
    user_id = role_to_id.get(created_by, 1)  # Default to 1 if not found

    try:
        created_by = int(user_id)
    except ValueError:
        return jsonify({'error': 'created_by must be an integer'}), 400

    sql = """
        INSERT INTO lifeapp.la_subjects
          (created_by, title, heading, image, status, `index`, created_at, updated_at)
        VALUES
          (%s,
           %s,         -- title JSON
           %s,         -- heading JSON
           JSON_OBJECT('en', %s),  -- image as JSON {"en": media_id}
           %s,          -- default active
           1,          -- default index
           NOW(),
           NOW()
          )
    """
    params = (
        created_by,
        title,
        heading,
        image_id,
        status
    )

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()
        return jsonify({'message': 'Subject created successfully'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/subjects/<int:subject_id>', methods=['PUT'])
def update_subject(subject_id):
    """
    Expects multipart/form-data:
      - title: valid JSON string
      - heading: valid JSON string
      - created_by: integer user ID (foreign key)
      - image: file upload (optional)
    """
    form = request.form
    file = request.files.get('image')
    new_image_id = None

    if file and file.filename:
        media = upload_media(file)
        new_image_id = media['id']

    title      = form.get('title', '').strip()
    heading    = form.get('heading', '').strip()
    created_by = form.get('created_by')
    status = form.get('status',0)

    if not title or not created_by:
        return jsonify({'error': 'title and created_by are required'}), 400

    # ————————————————————————————————————————————
    # Map role‐name → user ID (same as in create_subject)
    role_to_id = {"Admin": 1, "Mentor": 4, "Teacher": 5}
    if created_by in role_to_id:
        created_by = role_to_id[created_by]
    else:
        # if it wasn’t one of the roles, try to parse it as an integer
        try:
            created_by = int(created_by)
        except (ValueError, TypeError):
            return jsonify({'error': 'created_by must be an integer or valid role name'}), 400
    # ————————————————————————————————————————————

    try:
        created_by = int(created_by)
    except ValueError:
        return jsonify({'error': 'created_by must be an integer'}), 400

    # Build an UPDATE that only replaces image if a new file was provided
    sql = """
        UPDATE lifeapp.la_subjects
        SET
          created_by = %s,
          title      = %s,
          heading    = %s,
          status     = %s
    """
    params = [
        created_by,
        title,
        heading,
        status,
    ]

    if new_image_id is not None:
        sql += ", image = JSON_OBJECT('en', %s)"
        params.append(new_image_id)

    sql += ", updated_at = NOW() WHERE id = %s"
    params.append(subject_id)

    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()
        return jsonify({'message': 'Subject updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/subjects/<int:subject_id>', methods=['DELETE'])
def delete_subject(subject_id):
    try:
        conn = get_db_connection()
        # 1) Fetch the media ID (from JSON) and S3 key
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute("""
                SELECT 
                  JSON_UNQUOTE(JSON_EXTRACT(s.image, '$.en')) AS media_id,
                  m.path AS media_path
                FROM lifeapp.la_subjects s
                LEFT JOIN lifeapp.media m 
                  ON m.id = JSON_UNQUOTE(JSON_EXTRACT(s.image, '$.en'))
                WHERE s.id = %s
            """, (subject_id,))
            row = cur.fetchone()

        # 2) Delete the subject row
        with conn.cursor() as cur:
            cur.execute("DELETE FROM lifeapp.la_subjects WHERE id = %s", (subject_id,))

        # 3) If there was an image, delete its media record & S3 file
        if row and row.get('media_id'):
            media_id = int(row['media_id'])
            s3_key   = row.get('media_path')
            # remove media DB entry
            with conn.cursor() as cur:
                cur.execute("DELETE FROM lifeapp.media WHERE id = %s", (media_id,))
            conn.commit()
            # remove from S3/Spaces
            s3 = boto3.client(
                's3',
                region_name=DO_SPACES_REGION,
                endpoint_url=DO_SPACES_ENDPOINT,
                aws_access_key_id=DO_SPACES_KEY,
                aws_secret_access_key=DO_SPACES_SECRET
            )
            try:
                s3.delete_object(Bucket=DO_SPACES_BUCKET, Key=s3_key)
            except Exception:
                pass

        conn.commit()
        return jsonify({'message': 'Subject and its media deleted successfully'}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500

    finally:
        conn.close()

@app.route('/api/subjects/<int:subject_id>/status', methods=['PATCH'])
def change_subject_status(subject_id):
    """Change the status of a subject."""
    try:
        filters =  request.get_json() or {}
        status  = filters.get('status')
        if status == 'ACTIVE':
            status_no = 1
        else:
            status_no = 0
        connection = get_db_connection()

        with connection.cursor() as cursor:
            sql = "UPDATE lifeapp.la_subjects SET status = IF(%s=1, 0, 1) WHERE id = %s"
            cursor.execute(sql, (status_no,subject_id,))
            connection.commit()
        return jsonify({'message': 'Subject Status Changed'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()


###################################################################################
###################################################################################
######################## SETTINGS/LEVELS APIs ###################################
###################################################################################
###################################################################################
@app.route('/api/levels', methods=['POST'])
def get_levels():
    """Fetch all levels with pagination."""
    connection = None
    try:
        filters = request.get_json() or {}
        page = filters.get('page', 1)
        per_page = 25  # Default pagination limit
        offset = (page - 1) * per_page

        connection = get_db_connection()
        if connection is None:
            raise Exception("Database connection failed")

        with connection.cursor() as cursor:
            sql = "SELECT * FROM lifeapp.la_levels ORDER BY id ASC LIMIT %s OFFSET %s"
            cursor.execute(sql, (per_page, offset))
            levels = cursor.fetchall()
        
        return jsonify(levels)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        if connection:  # Check if connection is not None
            connection.close()

@app.route('/api/levels_new', methods=['POST'])
def create_level():
    """Create a new level."""
    try:
        data = request.get_json() or {}
        title_data = data.get('title', {})
        description_data = data.get('description', {})
        jigyasa_points= data.get('jigyasa_points')
        mission_points= data.get('mission_points')
        pragya_points=data.get('pragya_points')
        puzzle_points= data.get('puzzle_points')
        puzzle_time =data.get('puzzle_time')
        quiz_points=  data.get('quiz_points')
        quiz_time= data.get('quiz_time')
        riddle_points= data.get('riddle_points')
        riddle_time= data.get('riddle_time')
        status = data.get('status', 1)
        datetime_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sql = """
            INSERT INTO lifeapp.la_levels
              (title, description,
               jigyasa_points, mission_points, pragya_points,
               puzzle_points, puzzle_time,
               quiz_points, quiz_time,
               riddle_points, riddle_time,
               status,
               created_at)
            VALUES
              (%s,      %s,
               %s,      %s,      %s,
               %s,      %s,
               %s,      %s,
               %s,      %s,
              %s,
               NOW()
              )
        """
        params = [
            json.dumps(title_data),
            json.dumps(description_data),
            jigyasa_points,
            mission_points,
            pragya_points,
            puzzle_points,
            puzzle_time,
            quiz_points,
            quiz_time,
            riddle_points,
           riddle_time,
            status
        ]

        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            conn.commit()
            return jsonify({'message': 'Level Created'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/levels_update', methods=['POST'])
def update_level():
    """Update a level."""
    try:
        data = request.get_json() or {}
        level_id = data.get('id')
        if not level_id:
            return jsonify({'error': 'Missing level ID'}), 400
        title_data = data.get('title', {})
        description_data = data.get('description', {})
        jigyasa_points= data.get('jigyasa_points')
        mission_points= data.get('mission_points')
        pragya_points=data.get('pragya_points')
        puzzle_points= data.get('puzzle_points')
        puzzle_time =data.get('puzzle_time')
        quiz_points=  data.get('quiz_points')
        quiz_time= data.get('quiz_time')
        riddle_points= data.get('riddle_points')
        riddle_time= data.get('riddle_time')
        status= data.get('status',1)
        datetime_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        sql = """
            UPDATE lifeapp.la_levels
            SET
                title           = %s,
                description     = %s,
                jigyasa_points  = %s,
                mission_points  = %s,
                pragya_points   = %s,
                puzzle_points   = %s,
               puzzle_time     = %s,
                quiz_points     = %s,
                quiz_time       = %s,
                riddle_points   = %s,
                riddle_time     = %s,
                status          = %s,
                updated_at      = NOW()
            WHERE id = %s
        """
        params = [
            json.dumps(title_data),
            json.dumps(description_data),
            jigyasa_points,
            mission_points,
            pragya_points,
            puzzle_points,
            puzzle_time,
            quiz_points,
            quiz_time,
           riddle_points,
            riddle_time,
            status,
            level_id
        ]

        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            connection.commit()
        return jsonify({'message': 'Level Updated'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/levels_delete', methods=['POST'])
def delete_level():
    """Delete a level."""
    try:
        data = request.get_json() or {}
        level_id = data.get('id')

        if not level_id:
            return jsonify({'error': 'Missing level ID'}), 400

        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = "DELETE FROM lifeapp.la_levels WHERE id = %s"
            cursor.execute(sql, (level_id,))
            connection.commit()

        return jsonify({'message': 'Level deleted successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

###################################################################################
###################################################################################
######################## SETTINGS/LANGUAGES APIs ###################################
###################################################################################
###################################################################################

@app.route('/api/languages', methods=['POST'])
def get_languages():
    """Fetch all languages with pagination."""
    try:
        filters = request.get_json() or {}
        page = filters.get('page', 1)
        per_page = 25  # Default pagination limit
        offset = (page - 1) * per_page

        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = "SELECT * FROM lifeapp.languages ORDER BY title LIMIT %s OFFSET %s"
            cursor.execute(sql, (per_page, offset))
            languages = cursor.fetchall()
        return jsonify(languages)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/languages_new', methods=['POST'])
def create_language():
    """Create a new language with improved error handling."""
    try:
        # Get request data and validate
        data = request.get_json() or {}
        print(f"Received data: {data}")  # Debugging
        
        title = data.get('title', '').strip()
        slug = data.get('slug', '').strip().lower()
        status = data.get('status', 1)
        
        # Validate inputs
        if not slug:
            return jsonify({'error': 'Slug is required'}), 400
        
        if not title:
            return jsonify({'error': 'Title is required'}), 400
            
        try:
            status = int(status)
            if status not in [0, 1]:
                return jsonify({'error': 'Status must be 0 or 1'}), 400
        except (TypeError, ValueError):
            return jsonify({'error': 'Invalid status value'}), 400
        
        # Connect to database    
        conn = get_db_connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500
            
        try:
            with conn.cursor() as cursor:
                # Check for duplicate slug
                cursor.execute(
                    "SELECT COUNT(*) FROM lifeapp.languages WHERE slug = %s",
                    (slug,)
                )
                count = cursor.fetchone()[0]
                if count > 0:
                    return jsonify({'error': 'Slug already exists'}), 400
                
                # Insert new language
                print(f"Inserting: slug={slug}, title={title}, status={status}")  # Debugging
                cursor.execute(
                    "INSERT INTO lifeapp.languages (slug, title, status, created_at, updated_at) "
                    "VALUES (%s, %s, %s, NOW(), NOW())",
                    (slug, title, status)
                )
                conn.commit()
                
                # Get the ID of the newly created language
                cursor.execute("SELECT LAST_INSERT_ID()")
                new_id = cursor.fetchone()[0]
                
            return jsonify({
                'message': 'Language Created Successfully',
                'language_id': new_id
            }), 201
            
        except Exception as e:
            conn.rollback()
            print(f"Database error: {str(e)}")  # Debugging
            return jsonify({'error': f'Database error: {str(e)}'}), 500
            
    except Exception as e:
        print(f"Unexpected error: {str(e)}")  # Debugging
        return jsonify({'error': f'Server error: {str(e)}'}), 500
        
    finally:
        if 'conn' in locals() and conn:
            conn.close()

@app.route('/api/languages_update', methods=['POST'])
def update_language():
    """Update a language."""
    try:
        data = request.get_json() or {}
        language_id = data.get('id')
        title = data.get('title', '').strip()
        status      = data.get('status')
        try:
            status = int(status)
        except (TypeError, ValueError):
            return jsonify({'error': 'Invalid status value'}), 400

        slug = data.get('slug', '').strip().lower()

        if not language_id or not slug:
            return jsonify({'error': 'ID and Slug are required'}), 400

        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Check if slug already exists for another language
            cursor.execute("SELECT COUNT(*) FROM lifeapp.languages WHERE slug = %s AND id != %s", (slug, language_id))
            exists = cursor.fetchone()
            if exists and exists[0] > 0:
                return jsonify({'error': 'Slug already exists'}), 400

            sql = """
                        UPDATE lifeapp.languages
                        SET
                            slug       = %s,
                            title      = %s,
                            status     = %s,
                            updated_at = NOW()
                        WHERE id = %s
                """
            cursor.execute(sql, (slug, title, status, language_id))
            connection.commit()
        return jsonify({'message': 'Language Updated'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/languages_delete/<int:language_id>', methods=['DELETE'])
def delete_language(language_id):
    """Delete a language."""
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = "DELETE FROM lifeapp.languages WHERE id = %s"
            cursor.execute(sql, (language_id,))
            connection.commit()
        return jsonify({'message': 'Language Deleted'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/languages/<int:language_id>/status', methods=['PATCH'])
def change_language_status(language_id):
    """Change the status of a language."""
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = "UPDATE languages SET status = IF(status='ACTIVE', 'DEACTIVE', 'ACTIVE') WHERE id = %s"
            cursor.execute(sql, (language_id,))
            connection.commit()
        return jsonify({'message': 'Language Status Changed'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

###################################################################################
###################################################################################
######################## SETTINGS/SECTIONS APIs ###################################
###################################################################################
###################################################################################

@app.route('/api/sections', methods=['POST'])
def get_sections():
    """Fetch list of sections."""
    try:
        filters = request.get_json() or {}
        status = filters.get('status')
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = "SELECT * FROM lifeapp.la_sections"
            if status is not None:  # Ensure status=0 is also considered
                sql += " WHERE status = %s"
                cursor.execute(sql, (status,))
            else:
                cursor.execute(sql)

            result = cursor.fetchall()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/sections_new', methods=['POST'])
def create_section():
    """Create a new section."""
    try:
        data = request.get_json() or {}
        status = data.get('status')
        name = data.get('name')
        datetime_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if not name:
            return jsonify({'error': 'Name is required'}), 400
            
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # Fixed SQL statement with correct number of placeholders
            cursor.execute(
                "INSERT INTO lifeapp.la_sections (name, status, created_at, updated_at) VALUES (%s, %s, %s, %s)", 
                (name, status, datetime_str, datetime_str)
            )
            connection.commit()
        return jsonify({'message': 'Section created successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/sections_update', methods=['POST'])
def update_section():
    """Update section details."""
    try:
        data = request.get_json() or {}
        section_id = data.get('id')  # Getting id from request body
        name = data.get('name')
        status = data.get('status')
        datetime_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if not name:
            return jsonify({'error': 'Name is required'}), 400
        if not section_id:
            return jsonify({'error': 'Section ID is required'}), 400
            
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE lifeapp.la_sections SET name = %s, status = %s, updated_at = %s WHERE id = %s", 
                (name, status, datetime_str, section_id)
            )
            connection.commit()
        return jsonify({'message': 'Section updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/sections_delete', methods=['POST'])
def delete_section():
    """Delete a section."""
    try:
        data = request.get_json() or {}
        section_id = data.get('id')

        if not section_id:
            return jsonify({'error': 'Section ID is required'}), 400

        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM lifeapp.la_sections WHERE id = %s", (section_id,))
            connection.commit()

        return jsonify({'message': 'Section deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/sections/<int:section_id>/status', methods=['PATCH'])
def toggle_section_status(section_id):
    """Toggle the status of a section."""
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT status FROM la_sections WHERE id = %s", (section_id,))
            section = cursor.fetchone()
            if not section:
                return jsonify({'error': 'Section not found'}), 404
            new_status = 'inactive' if section['status'] == 'active' else 'active'
            cursor.execute("UPDATE la_sections SET status = %s WHERE id = %s", (new_status, section_id))
            connection.commit()
        return jsonify({'message': 'Section status changed', 'status': new_status})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()


###################################################################################
###################################################################################
####################### SETTINGS/TOPICS APIs ######################################
###################################################################################
###################################################################################

@app.route('/api/topics', methods=['POST'])
def get_topics():
    data = request.get_json() or {}
    la_subject_id = data.get('la_subject_id')
    la_level_id = data.get('la_level_id')
    status = data.get('status', '')  # Expect "1", "0", or "all"

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = """
                SELECT 
                    t.id,
                    t.title,
                    t.status,
                    -- t.created_at,
                    -- t.updated_at,
                    t.image,
                    t.allow_for,
                    t.type,
                    t.la_subject_id,
                    t.la_level_id,
                    m.id as media_id,
                    m.path as media_path
                from lifeapp.la_topics t left join lifeapp.media m on m.id = JSON_EXTRACT(t.image,'$.en')
                WHERE 1=1
            """
            filters = []
            if la_subject_id:
                sql += " AND t.la_subject_id = %s"
                filters.append(la_subject_id)
            if la_level_id:
                sql += " AND t.la_level_id = %s"
                filters.append(la_level_id)
            if status and status.lower() != "all":
                sql += " AND t.status = %s"
                filters.append(status)
            sql += " ORDER BY t.id"
            cursor.execute(sql, filters)
            topics = cursor.fetchall()
            base_url = os.getenv('BASE_URL')
            for r in topics:
                r['media_url'] = f"{base_url}/{r['media_path']}" if r.get('media_path') else None
        
        return jsonify(topics)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/add_topic', methods=['POST'])
def add_topic():
    form       = request.form
    file       = request.files.get('media')
    media_id   = None

    # 1) upload the file if provided
    if file and file.filename:
        media = upload_media(file)
        media_id = media['id']

    # 2) pull other fields
    title_raw        = form.get('title', '').strip()
    la_subject   = form.get('la_subject_id')
    la_level     = form.get('la_level_id')
    status       = int(form.get('status', 1))
    allow_for    = int(form.get('allow_for', 1))
    topic_type   = int(form.get('type', 2))

    sql = """
      INSERT INTO lifeapp.la_topics
        (title, status, created_at, updated_at, image, allow_for, type, la_subject_id, la_level_id)
      VALUES (
        JSON_OBJECT('en', %s),
        %s, NOW(), NOW(),
        JSON_OBJECT('en', %s),
        %s, %s, %s, %s
      )
    """
    params = (
      title_raw,
      status,
      media_id,
      allow_for,
      topic_type,
      la_subject,
      la_level
    )

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            new_id = cur.lastrowid
        conn.commit()
        return jsonify({"success": True, "topic_id": new_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# Similarly, you can create update_topic and delete_topic endpoints.

@app.route('/api/update_topic/<int:topic_id>', methods=['POST'])
def update_topic(topic_id):
    form       = request.form
    file       = request.files.get('media')
    new_media  = None

    if file and file.filename:
        m = upload_media(file)
        new_media = m['id']

    title      = form.get('title', '').strip()
    la_subject = int(form.get('la_subject_id'))
    la_level   = int(form.get('la_level_id'))
    status     = int(form.get('status', 1))
    allow_for  = int(form.get('allow_for', 1))
    topic_type = int(form.get('type', 2))

    # only overwrite image if new_media is not None
    if new_media is not None:
        sql = """
          UPDATE lifeapp.la_topics
          SET title=%s, status=%s, updated_at=NOW(),
              image=JSON_OBJECT('en', %s),
              allow_for=%s, type=%s, la_subject_id=%s, la_level_id=%s
          WHERE id=%s
        """
        params = (title, status, new_media,
                  allow_for, topic_type,
                  la_subject, la_level,
                  topic_id)
    else:
        sql = """
          UPDATE lifeapp.la_topics
          SET title=%s, status=%s, updated_at=NOW(),
              allow_for=%s, type=%s, la_subject_id=%s, la_level_id=%s
          WHERE id=%s
        """
        params = (title, status,
                  allow_for, topic_type,
                  la_subject, la_level,
                  topic_id)

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()
        return jsonify({"success": True, "topic_id": topic_id}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/delete_topic/<int:topic_id>', methods=['DELETE'])
def delete_topic(topic_id):
    conn = get_db_connection()
    try:
        # fetch media id & path
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute("""
              SELECT JSON_UNQUOTE(JSON_EXTRACT(image,'$.en')) AS media_id,
                     m.path AS media_path
                FROM lifeapp.la_topics t
                LEFT JOIN lifeapp.media m 
                  ON m.id = JSON_UNQUOTE(JSON_EXTRACT(t.image,'$.en'))
               WHERE t.id=%s
            """, (topic_id,))
            row = cur.fetchone()

        # delete topic
        with conn.cursor() as cur:
            cur.execute("DELETE FROM lifeapp.la_topics WHERE id=%s", (topic_id,))

        # delete media record + S3 object
        if row and row['media_id']:
            media_id = int(row['media_id'])
            key = row['media_path']
            with conn.cursor() as cur:
                cur.execute("DELETE FROM lifeapp.media WHERE id=%s", (media_id,))
            conn.commit()

            # delete from S3
            s3 = boto3.client(
              's3',
              region_name=DO_SPACES_REGION,
              endpoint_url=DO_SPACES_ENDPOINT,
              aws_access_key_id=DO_SPACES_KEY,
              aws_secret_access_key=DO_SPACES_SECRET
            )
            try:
                s3.delete_object(Bucket=DO_SPACES_BUCKET, Key=key)
            except:
                pass

        conn.commit()
        return jsonify({"success": True, "topic_id": topic_id}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


###################################################################################
###################################################################################
####################### SETTINGS/BOARDS APIs ######################################
###################################################################################
###################################################################################

@app.route('/api/boards', methods=['POST'])
def get_boards():
    """Return all boards."""
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT id, name, status, created_at, updated_at FROM lifeapp.la_boards ORDER BY id;"
            cursor.execute(sql)
            boards = cursor.fetchall()
        return jsonify(boards)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/add_board', methods=['POST'])
def add_board():
    """Add a new board."""
    data = request.get_json() or {}
    name = data.get("name")
    status = data.get("status", 1)
    datetime_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = """
                INSERT INTO lifeapp.la_boards (name, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (name, status, datetime_str, datetime_str))
            board_id = cursor.lastrowid
            connection.commit()
        return jsonify({"success": True, "board_id": board_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/update_board/<int:board_id>', methods=['PUT'])
def update_board(board_id):
    """Update an existing board."""
    data = request.get_json() or {}
    name = data.get("name")
    status = data.get("status", 1)
    datetime_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = """
                UPDATE lifeapp.la_boards
                SET name = %s,
                    status = %s,
                    updated_at = %s
                WHERE id = %s
            """
            cursor.execute(sql, (name, status, datetime_str, board_id))
            connection.commit()
        return jsonify({"success": True, "board_id": board_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

@app.route('/api/delete_board/<int:board_id>', methods=['DELETE'])
def delete_board(board_id):
    """Delete a board."""
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "DELETE FROM lifeapp.la_boards WHERE id = %s"
            cursor.execute(sql, (board_id,))
            connection.commit()
        return jsonify({"success": True, "board_id": board_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()


###################################################################################
###################################################################################
####################### SETTINGS/GAME ENROLLMENTS APIs ############################
###################################################################################
###################################################################################

# 1. List Enrollments - GET /enrollments
@app.route('/api/enrollments', methods=['GET'])
def list_enrollments():
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            query = "SELECT * FROM lifeapp.la_game_enrollments"
            cursor.execute(query)
            enrollments = cursor.fetchall()
        connection.close()
        return jsonify(enrollments), 200
    except Exception as e:
        logger.error("Error listing enrollments: %s", e)
        return jsonify({"error": str(e)}), 500

# 2. Add Enrollment - POST /enrollments
@app.route('/api/enrollments', methods=['POST'])
def add_enrollment():
    try:
        data = request.get_json() or {}
        # Now accepting enrollment_code from frontend, but will override it
        enrollment_code = data.get('enrollment_code', '7789')  # Use provided or default to TEMP
        type_val = data.get('type')
        user_id = data.get('user_id')
        unlock_enrollment_at = data.get('unlock_enrollment_at')  # Expecting ISO datetime string if provided

        if type_val is None or not user_id:
            return jsonify({"error": "Missing required fields: type and user_id"}), 400

        # Parse unlock_enrollment_at if provided
        unlock_time = None
        if unlock_enrollment_at:
            try:
                unlock_time = datetime.fromisoformat(unlock_enrollment_at)
            except ValueError:
                return jsonify({"error": "Incorrect date format for unlock_enrollment_at. Use ISO format."}), 400

        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        updated_at = created_at

        connection = get_db_connection()
        try:
            cursor = connection.cursor()
            # Insert with temporary enrollment_code
            sql = """
                INSERT INTO lifeapp.la_game_enrollments 
                (enrollment_code, type, user_id, unlock_enrollment_at, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (enrollment_code, type_val, user_id, unlock_time, created_at, updated_at))
            enrollment_id = cursor.lastrowid

            # Generate real enrollment_code as a 4-digit string (with leading zeroes)
            real_enrollment_code = f"{enrollment_id:04d}"
            # Update the same record with the real enrollment_code
            cursor.execute(
                "UPDATE lifeapp.la_game_enrollments SET enrollment_code = %s WHERE id = %s",
                (real_enrollment_code, enrollment_id)
            )
            connection.commit()
            
            return jsonify({
                "success": True,
                "message": "Enrollment created", 
                "id": enrollment_id, 
                "enrollment_code": real_enrollment_code
            }), 201

        finally:
            connection.close()

    except Exception as e:
        logger.error("Error adding enrollment: %s", e)
        return jsonify({"error": str(e), "success": False}), 500
# 3. Edit Enrollment - PUT /enrollments/<id>
@app.route('/api/enrollments/<int:enrollment_id>', methods=['PUT'])
def edit_enrollment(enrollment_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No input data provided"}), 400

        update_fields = []
        params = []

        if "enrollment_code" in data:
            update_fields.append("enrollment_code = %s")
            params.append(data["enrollment_code"])
        if "type" in data:
            update_fields.append("`type` = %s")
            params.append(data["type"])
        if "user_id" in data:
            update_fields.append("user_id = %s")
            params.append(data["user_id"])
        if "unlock_enrollment_at" in data:
            unlock_enrollment_at = data["unlock_enrollment_at"]
            if unlock_enrollment_at:
                try:
                    unlock_dt = datetime.fromisoformat(unlock_enrollment_at)
                except ValueError:
                    return jsonify({"error": "Incorrect date format for unlock_enrollment_at. Use ISO format."}), 400
            else:
                unlock_dt = None
            update_fields.append("unlock_enrollment_at = %s")
            params.append(unlock_dt)

        if not update_fields:
            return jsonify({"error": "No valid fields provided for update"}), 400

        # Always update the updated_at column
        updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        update_fields.append("updated_at = %s")
        params.append(updated_at)

        # Add enrollment id to the parameters for WHERE clause
        params.append(enrollment_id)

        set_clause = ", ".join(update_fields)
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = f"UPDATE lifeapp.la_game_enrollments SET {set_clause} WHERE id = %s"
            cursor.execute(sql, tuple(params))
        connection.commit()
        connection.close()

        return jsonify({"message": "Enrollment updated"}), 200

    except Exception as e:
        logger.error("Error editing enrollment: %s", e)
        return jsonify({"error": str(e)}), 500

# 4. Delete Enrollment - DELETE /enrollments/<id>
@app.route('/api/enrollments/<int:enrollment_id>', methods=['DELETE'])
def delete_enrollment(enrollment_id):
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = "DELETE FROM lifeapp.la_game_enrollments WHERE id = %s"
            cursor.execute(sql, (enrollment_id,))
        connection.commit()
        connection.close()
        return jsonify({"message": "Enrollment deleted"}), 200
    except Exception as e:
        logger.error("Error deleting enrollment: %s", e)
        return jsonify({"error": str(e)}), 500
    

###################################################################################
###################################################################################
####################### SETTINGS/GAME ENROLLMENTS REQUEST APIs ####################
###################################################################################
###################################################################################
# ===============================================
# 1. List Enrollment Requests with Filters
# ===============================================
@app.route('/api/game_enrollment_requests', methods=['POST'])
def list_game_enrollment_requests():
    data = request.get_json() or {}
    # Filter by status: "approved", "not_approved", "all"
    status = data.get('status', 'all').lower()
    # Filter by type: "1", "2", "3", "4", "5", "6", or "all"
    req_type = data.get('type', 'all')
    
    sql = "SELECT * FROM lifeapp.la_request_game_enrollments WHERE 1=1"
    params = []
    
    if status != "all":
        if status == "approved":
            sql += " AND approved_at IS NOT NULL"
        elif status == "not_approved":
            sql += " AND approved_at IS NULL"
    
    if req_type != "all" and req_type:
        sql += " AND type = %s"
        params.append(req_type)
    
    sql += " ORDER BY created_at DESC"
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, tuple(params))
            result = cursor.fetchall()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

# ===============================================
# 2. Add a New Enrollment Request
# ===============================================
@app.route('/api/game_enrollment_requests/add', methods=['POST'])
def add_game_enrollment_request():
    data = request.get_json() or {}
    user_id = data.get('user_id')
    req_type = data.get('type')
    la_game_enrollment_id = data.get('la_game_enrollment_id')
    # approved_at can be provided (if approved) or None for pending request.
    approved_at = data.get('approved_at', None)
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = """
            INSERT INTO lifeapp.la_request_game_enrollments 
            (user_id, type, la_game_enrollment_id, approved_at, created_at, updated_at)
            VALUES (%s, %s, %s, %s, NOW(), NOW())
            """
            cursor.execute(sql, (user_id, req_type, la_game_enrollment_id, approved_at))
            connection.commit()
        return jsonify({'message': 'Request added successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

# ===============================================
# 3. Edit an Existing Enrollment Request
# ===============================================
@app.route('/api/game_enrollment_requests/<int:request_id>', methods=['PUT'])
def edit_game_enrollment_request(request_id):
    data = request.get_json() or {}
    user_id = data.get('user_id')
    req_type = data.get('type')
    la_game_enrollment_id = data.get('la_game_enrollment_id')
    approved_at = data.get('approved_at')  # may be null if not approved
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = """
            UPDATE lifeapp.la_request_game_enrollments
            SET user_id = %s, type = %s, la_game_enrollment_id = %s, approved_at = %s, updated_at = NOW()
            WHERE id = %s
            """
            cursor.execute(sql, (user_id, req_type, la_game_enrollment_id, approved_at, request_id))
            connection.commit()
        return jsonify({'message': 'Request updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()

# ===============================================
# 4. Delete an Enrollment Request
# ===============================================
@app.route('/api/game_enrollment_requests/<int:request_id>', methods=['DELETE'])
def delete_game_enrollment_request(request_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "DELETE FROM lifeapp.la_request_game_enrollments WHERE id = %s"
            cursor.execute(sql, (request_id,))
            connection.commit()
        return jsonify({'message': 'Request deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        connection.close()



###################################################################################
###################################################################################
####################### SETTINGS/COUPONS APIs #################################
###################################################################################
###################################################################################
def delete_s3_object(key):
    s3 = boto3.client(
        's3',
        region_name=DO_SPACES_REGION,
        endpoint_url=DO_SPACES_ENDPOINT,
        aws_access_key_id=DO_SPACES_KEY,
        aws_secret_access_key=DO_SPACES_SECRET
    )
    try:
        s3.delete_object(Bucket=DO_SPACES_BUCKET, Key=key)
    except Exception:
        pass

# GET coupons with filters
@app.route('/api/coupons', methods=['GET'])
def get_coupons():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            
            base_query = '''
            SELECT 
                c.id, c.title, c.category_id, 
                c.coin, c.link, c.details, 
                c.index, c.coupon_media_id as media_id, c.created_at, c.updated_at,
                m.path as media_path
            FROM lifeapp.coupons c
                left join lifeapp.media m on c.coupon_media_id = m.id
            '''
            conditions = []
            params = []
            
            # Check and apply the start_date filter if provided
            if start_date:
                conditions.append('c.created_at >= %s')
                params.append(start_date)
            
            # Check and apply the end_date filter if provided
            if end_date:
                conditions.append('c.created_at <= %s')
                params.append(end_date)
            
            # Append the conditions if there are any filters
            if conditions:
                base_query += ' WHERE ' + ' AND '.join(conditions)
            
            cursor.execute(base_query, params)
            coupons = cursor.fetchall()
            base_url = os.getenv('BASE_URL')
            for r in coupons:
                r['media_url'] = f"{base_url}/{r['media_path']}" if r.get('media_path') else None
        
            return jsonify({'count': len(coupons), 'data': coupons})
    finally:
        conn.close()

# POST add coupon
@app.route('/api/coupons', methods=['POST'])
def add_coupon():
    # We're expecting multipart/form-data
    form = request.form
    file = request.files.get('media')
    media_id = None

    # 1) upload the file if provided
    if file and file.filename:
        media = upload_media(file)       # your existing helper
        media_id = media['id']

    # 2) pull other fields
    title        = form.get('title')
    category_id  = form.get('category_id')
    coin         = form.get('coin')
    link         = form.get('link')
    details      = form.get('details')
    idx          = form.get('index')

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
              """
              INSERT INTO lifeapp.coupons
                (title, category_id, coin, link, details, `index`, coupon_media_id, created_at, updated_at)
              VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
              """,
              (title, category_id, coin, link, details, idx, media_id)
            )
            conn.commit()
            return jsonify({'success': True}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# PUT update coupon
@app.route('/api/coupons/<int:id>', methods=['PUT'])
def update_coupon(id):
    form = request.form
    file = request.files.get('media')
    new_media_id = None

    # if a new file is uploaded, store it & plan to delete old
    if file and file.filename:
        media = upload_media(file)
        new_media_id = media['id']

    # pull other fields
    title       = form.get('title')
    category_id = form.get('category_id')
    coin        = form.get('coin')
    link        = form.get('link')
    details     = form.get('details')
    idx         = form.get('index')

    conn = get_db_connection()
    try:
        # if replacing media, fetch old key so we can delete from S3/db
        if new_media_id is not None:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                cur.execute("SELECT coupon_media_id, m.path AS media_path FROM coupons c LEFT JOIN media m ON c.coupon_media_id=m.id WHERE c.id=%s", (id,))
                old = cur.fetchone()
            # delete old media row + S3
            if old and old['coupon_media_id']:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM media WHERE id=%s", (old['coupon_media_id'],))
                delete_s3_object(old['media_path'])

        # build update
        if new_media_id is not None:
            sql = """
              UPDATE lifeapp.coupons
                SET title=%s, category_id=%s, coin=%s, link=%s,
                    details=%s, `index`=%s, coupon_media_id=%s,
                    updated_at=NOW()
              WHERE id=%s
            """
            params = (title, category_id, coin, link, details, idx, new_media_id, id)
        else:
            sql = """
              UPDATE lifeapp.coupons
                SET title=%s, category_id=%s, coin=%s, link=%s,
                    details=%s, `index`=%s,
                    updated_at=NOW()
              WHERE id=%s
            """
            params = (title, category_id, coin, link, details, idx, id)

        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# DELETE coupon
@app.route('/api/coupons/<int:id>', methods=['DELETE'])
def delete_coupon(id):
    conn = get_db_connection()
    try:
        # fetch the media id + path
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            cur.execute("""
              SELECT coupon_media_id, m.path AS media_path
                FROM lifeapp.coupons c
                LEFT JOIN media m ON c.coupon_media_id=m.id
               WHERE c.id=%s
            """, (id,))
            row = cur.fetchone()

        # delete the coupon row
        with conn.cursor() as cur:
            cur.execute("DELETE FROM lifeapp.coupons WHERE id=%s", (id,))

        # delete media record + S3 object if exists
        if row and row['coupon_media_id']:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM media WHERE id=%s", (row['coupon_media_id'],))
            delete_s3_object(row['media_path'])

        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()



###################################################################################
###################################################################################
####################### CAMPAIGNS APIs ############################################
###################################################################################
###################################################################################

@app.route('/api/campaigns', methods=['GET'])
def list_campaigns():
    qs       = request.args
    page     = int(qs.get('page', 1))
    per_page = int(qs.get('per_page', 25))
    offset   = (page - 1) * per_page

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 1) total count
            cursor.execute("SELECT COUNT(*) AS total FROM la_campaigns")
            total = cursor.fetchone()['total']

            # 2) paginated fetch with conditional joins
            sql = """
            SELECT
              c.id,
              c.game_type,
              CASE 
                WHEN c.game_type = 1
                    THEN 'Mission'
                WHEN c.game_type = 2
                    THEN 'Quiz'
                ELSE 'Vision'
              END AS game_type_title,
              c.reference_id,

              -- pull the right title from the right table:
              COALESCE(
                JSON_UNQUOTE(JSON_EXTRACT(m.title, '$.en')),                -- mission title
                JSON_UNQUOTE(JSON_EXTRACT(q.title, '$.en')),                -- quiz question title
                JSON_UNQUOTE(JSON_EXTRACT(v.title,'$.en'))  -- vision title (your JSON column)
              ) AS reference_title,

              c.title        AS campaign_title,
              c.description,
              c.scheduled_for,
              c.created_at,
              c.updated_at
            FROM la_campaigns c

            -- only join missions when game_type=1
            LEFT JOIN lifeapp.la_missions m
              ON c.game_type = 1
             AND m.id        = c.reference_id

            -- only join quiz questions when game_type=2
            LEFT JOIN lifeapp.la_questions q
              ON c.game_type = 2
             AND q.id        = c.reference_id

            -- only join visions when game_type=7
            LEFT JOIN lifeapp.visions v
              ON c.game_type = 7
             AND v.id        = c.reference_id

            ORDER BY c.scheduled_for DESC
            LIMIT %s OFFSET %s
            """
            cursor.execute(sql, (per_page, offset))
            camps = cursor.fetchall()

        return jsonify({
            'page': page,
            'per_page': per_page,
            'total': total,
            'data': camps
        }), 200

    finally:
        conn.close()


@app.route('/api/campaigns', methods=['POST'])
def create_campaign():
    data = request.get_json() or {}
    sql = """
        INSERT INTO lifeapp.la_campaigns
          (game_type, reference_id, title, description, scheduled_for, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
    """
    params = (
        data['game_type'],
        data['reference_id'],
        data['title'],
        data['description'],
        data['scheduled_for']
    )
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            conn.commit()
            return jsonify({'id': cursor.lastrowid}), 201
    finally:
        conn.close()

@app.route('/api/campaigns/<int:id>', methods=['PUT'])
def update_campaign(id):
    data = request.get_json() or {}
    sql = """
      UPDATE lifeapp.la_campaigns
         SET game_type=%s,
             reference_id=%s,
             title=%s,
             description=%s,
             scheduled_for=%s,
             updated_at=NOW()
       WHERE id=%s
    """
    params = (
        data['game_type'],
        data['reference_id'],
        data['title'],
        data['description'],
        data['scheduled_for'],
        id
    )
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            conn.commit()
        return jsonify({'success': True}), 200
    finally:
        conn.close()

@app.route('/api/campaigns/<int:id>', methods=['DELETE'])
def delete_campaign(id):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM lifeapp.la_campaigns WHERE id=%s", (id,))
            conn.commit()
        return jsonify({'success': True}), 200
    finally:
        conn.close()

# ————— Reference Lists —————

@app.route('/api/mission_list', methods=['POST'])
def mission_list():
    data       = request.get_json() or {}
    subject_id = data.get('subject_id')
    level_id   = data.get('level_id')
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT id, JSON_UNQUOTE(JSON_EXTRACT(title, '$.en')) as title FROM lifeapp.la_missions WHERE status=1"
            params = []
            if subject_id:
                sql += " AND la_subject_id=%s"; params.append(subject_id)
            if level_id:
                sql += " AND la_level_id=%s";   params.append(level_id)
            cursor.execute(sql, params)
            items = cursor.fetchall()
        return jsonify(items), 200
    finally:
        conn.close()


@app.route('/api/quiz_list', methods=['POST'])
def quiz_list():
    data       = request.get_json() or {}
    subject_id = data.get('subject_id')
    level_id   = data.get('level_id')
    topic_id   = data.get('topic_id')
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT id, JSON_UNQUOTE(JSON_EXTRACT(title, '$.en')) AS title FROM lifeapp.la_questions WHERE status=1"
            params = []
            if subject_id:
                sql += " AND la_subject_id=%s"; params.append(subject_id)
            if level_id:
                sql += " AND la_level_id=%s";   params.append(level_id)
            if topic_id:
                sql += " AND la_topic_id=%s";   params.append(topic_id)
            cursor.execute(sql, params)
            items = cursor.fetchall()
        return jsonify(items), 200
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(debug=True,  use_reloader=True)
