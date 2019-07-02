
# import scraper
# from functools import wraps

# from mongoengine import *
# from models import *
# from datetime import datetime, timedelta
# from bs4 import BeautifulSoup
# from flask_cors import CORS, cross_origin
# import jwt
# import requests
# import MySQLdb

# CORS(app)
# connect('susun-jadwal')
# db = MySQLdb.connect("localhost", "root", "mau tau aja", "susunjadwal")
# secret_key = '$Zk`^G8"LR<>C9r6D,+W3.}mr8UQ/*aU'


# BASE_PATH = '/susunjadwal/api'


@app.route('/auth/login', methods=['POST'])
def login():
    data = request.json
    if(data['token'] != '8VlGnna26REH6xrh'):
        return jsonify(), 401
    user = User.objects(npm=data['npm']).first()
    if(user == None):
        del data['token']
        user = User(**data)
        user.major = Major.objects(name=data['major']).first()
        user.role = 'user'
        user.save()
    token = jwt.encode({
        'exp': datetime.utcnow() + timedelta(minutes=525600),
        'user_id': str(user.id),
        'major_id': str(user.major.id),
        'role': user.role
    }, secret_key, algorithm='HS256')
    return jsonify({
        'user_id': str(user.id),
        'token': token,
        'major_id': str(user.major.id)
    }), 200


@app.route('/auth/login/admin', methods=['POST'])
def admin_login():
    data = request.json
    if(data['token'] != '8VlGnna26REH6xrh'):
        return jsonify(), 401
    token = jwt.encode({
        'exp': datetime.utcnow() + timedelta(minutes=525600),
        'role': 'admin'
    }, secret_key, algorithm='HS256')
    return jsonify({
        'user_id': 'staff',
        'token': token,
        'major_id': 'staff'
    }), 200


def extract_data(header):
    try:
        header_type, value = tuple(header['Authorization'].split())
        data = jwt.decode(value, secret_key)
    except Exception:
        return None
    return data


@app.route(BASE_PATH + '/auth/validate')
def validate():
    data = extract_data(request.headers)
    status = True
    if(data == None):
        status = False
    return jsonify({
        'status': status
    }), 200


def require_token(func):
    @wraps(func)
    def decorated_func(*args, **kwargs):
        data = extract_data(request.headers)
        if(data == None):
            return jsonify({
                'message': 'There is no token/token is not valid'
            }), 401
        return func(*args, **kwargs)
    return decorated_func


def privilege(role):
    def check_privilege(func):
        @wraps(func)
        def decorated_func(*args, **kwargs):
            data = extract_data(request.headers)
            if(data['role'] == role):
                return func(*args, **kwargs)
            return jsonify({
                'message': 'Unauthorized. Only admin can access this endpoint'
            }), 401
        return decorated_func
    return check_privilege


def same_user_id(func):
    @wraps(func)
    def decorated_func(*args, **kwargs):
        data = extract_data(request.headers)
        if(data['user_id'] == kwargs['user_id']):
            return func(*args, **kwargs)
        return jsonify({
            'message': 'Unauthorized. Only the resource owner can access this endpoint'
        }), 401
    return decorated_func


def protected_resource():
    return jsonify({
        'message': 'Unauthorized. Only the resource owner can access this endpoint'
    }), 401

#                MAJOR MODULE             #
###########################################
@app.route(BASE_PATH + '/majors/<major_id>/courses', methods=['POST'])
@require_token
@privilege('admin')
def save_course(major_id):
    data = request.json
    major = Major.objects(id=major_id).first()
    course = major.create_course(data['name'], data['sks'], data['term'])
    classes = data['classes']
    for class_ in classes:
        jadwals = class_['jadwals']
        class_ = course.create_class(class_['name'], class_['lecturer'])
        for jadwal in jadwals:
            class_.create_jadwal(**jadwal)
    major.save()
    return jsonify(major.get_course()), 201


@app.route(BASE_PATH + '/majors/<major_id>/courses', methods=['GET'])
@require_token
def get_courses(major_id):
    major = Major.objects(id=major_id).first()
    return jsonify(major.get_course()), 200
###########################################

#                USER MODULE              #
###########################################
@app.route(BASE_PATH + '/users/<user_id>/jadwals', methods=['POST'])
@require_token
@same_user_id
def save_jadwal(user_id):
    data = request.json
    jadwal = Jadwal(user_id=user_id)
    for j in data['jadwals']:
        jadwal.add_jadwal(**j)
    primary_jadwal = Jadwal.objects(user_id=user_id, primary=True).first()
    if(primary_jadwal == None):
        jadwal.primary = True
    else:
        jadwal.primary = False
    jadwal.save()
    return jsonify({
        'jadwal_id': str(jadwal.id),
        'primary': jadwal.primary
    }), 201


@app.route(BASE_PATH + '/users/<user_id>/jadwals/<jadwal_id>/set-utama', methods=['POST'])
@require_token
@same_user_id
def set_to_primary(user_id, jadwal_id):
    data = request.json
    jadwal = Jadwal.objects(user_id=user_id, id=jadwal_id).first()
    primary_jadwal = Jadwal.objects(user_id=user_id, primary=True).first()
    if primary_jadwal is not None:
        primary_jadwal.primary = False
        primary_jadwal.save()
    jadwal.primary = True
    jadwal.save()
    return jsonify(), 204


@app.route(BASE_PATH + '/users/<user_id>/jadwals', methods=['GET'])
@require_token
@same_user_id
def get_jadwal(user_id):
    jadwals = Jadwal.objects(user_id=user_id, deleted=False).all()
    data = []
    for jadwal in jadwals:
        data.append(jadwal.serialize())
    return jsonify({
        'jadwals': data
    }), 200


@app.route(BASE_PATH + '/users/<user_id>/jadwals/<jadwal_id>', methods=['DELETE'])
@require_token
@same_user_id
def delete_jadwal(user_id, jadwal_id):
    jadwal = Jadwal.objects(id=jadwal_id).first()
    jadwal.deleted = True
    jadwal.save()
    return jsonify(), 204


@app.route(BASE_PATH + '/users/<user_id>/jadwals/<jadwal_id>/set-private', methods=['POST'])
@require_token
@same_user_id
def set_to_private(user_id, jadwal_id):
    jadwal = Jadwal.objects(id=jadwal_id).first()
    jadwal.private = True
    jadwal.save()
    return jsonify(), 204
###########################################

#                JADWAL MODULE            #
###########################################
@app.route(BASE_PATH + '/jadwals/<jadwal_id>')
def get_public_jadwal(jadwal_id):
    jadwal = Jadwal.objects(id=jadwal_id).first()
    if(jadwal.private):
        return protected_resource()
    return jsonify({
        'user_id': str(jadwal.user_id),
        'jadwals': jadwal.get_jadwal()
    })


@app.route(BASE_PATH + '/jadwals/join')
def join_jadwal():
    jadwal_ids = request.json['jadwal_ids']
    data = []
    for jadwal_id in jadwal_ids:
        jadwal = Jadwal.objects(id=jadwal_id).first()

        if(jadwal.private):
            return protected_resource()
        data.extend(jadwal.get_jadwal())
    return jsonify({
        'jadwals': data
    })
###########################################


#               SCRAPER MODULE            #
###########################################
###########################################


#             DASHBOARD MODULE            #
###########################################
@app.route(BASE_PATH + '/admin/majors')
@require_token
@privilege('admin')
def get_major_ids():
    majors = Major.objects(
        name__in=['ilmu-komputer', 'sistem-informasi']).all()
    major_ids = []
    for major in majors:
        major_ids.append({
            'id': str(major.id),
            'name': major.name
        })
    return jsonify({
        'majors': major_ids
    })


@app.route(BASE_PATH + '/admin/majors/<major_id>/courses')
@require_token
@privilege('admin')
def get_course_info(major_id):
    cursor = db.cursor()
    sql = """select class.id, class.name, major.name, count(*) from class
         left join course on class.course_id = course.id
         left join major on course.major_id = major.id
         left join user_class on user_class.class_id = class.id
         group by class.id, class.name, major.name
         """
    cursor.execute(sql)

    json_data = []
    for data in cursor.fetchall():
        json_data.append({
            'id': data[0],
            'name': data[1],
            'major': data[2],
            'num_student': data[3]
        })

    return jsonify({
        'courses': json_data
    })


@app.route(BASE_PATH + '/admin/majors/<major_id>/courses/<course_id>')
@require_token
@privilege('admin')
def get_course_detail(major_id, course_id):
    cursor = db.cursor()
    sql = """select class.name, major.name, course.sks, count(*) from class
         left join course on class.course_id = course.id
         left join major on course.major_id = major.id
         left join user_class on user_class.class_id = class.id
         where class.id = {}
         group by class.name, major.name, course.sks
         """.format(course_id)
    cursor.execute(sql)
    data = cursor.fetchone()

    class_info = {
        'name': data[0],
        'major': data[1],
        'sks': data[2],
        'num_student': data[3]
    }

    sql = """select user.npm, user.name, major.name from user_class
             left join user on user.id = user_class.user_id
             left join major on user.major_id = major.id
             where user_class.class_id = {}
             """.format(course_id)
    cursor.execute(sql)

    datas = cursor.fetchall()
    students = []

    for data in datas:
        students.append({
            'npm': data[0],
            'name': data[1],
            'major': data[2]
        })

    return jsonify({
        'class_info': class_info,
        'student_list': students
    })
###########################################