from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate  # 新增导入
from models import db, User, Student, Attendance
from config import Config
from datetime import datetime
import base64
import json
import os
from datetime import datetime, timedelta
import pytz

# 设置中国时区
china_tz = pytz.timezone('Asia/Shanghai')

def get_china_time():
    return datetime.now(china_tz)

# 尝试导入百度AI服务，如果失败则使用模拟服务
try:
    from baidu_face_service import BaiduFaceService

    baidu_face = BaiduFaceService()
    BAIDU_AI_AVAILABLE = True
    print("百度AI服务初始化成功")
except Exception as e:
    print(f"百度AI服务初始化失败: {e}")


    # 创建一个模拟服务类，避免因百度AI配置问题导致整个应用崩溃
    class MockBaiduFaceService:
        def add_face(self, image_path, user_id, user_info):
            return {"error_code": 0, "result": {"face_token": f"mock_face_token_{user_id}"}}

        def search_face(self, image_path):
            return {"error_code": 1, "error_msg": "百度AI服务未正确配置"}

        def create_group(self):
            return {"error_code": 0}


    baidu_face = MockBaiduFaceService()
    BAIDU_AI_AVAILABLE = False

app = Flask(__name__)
app.config.from_object(Config)

# 初始化数据库
db.init_app(app)

# 初始化 Flask-Migrate
migrate = Migrate(app, db)

# 创建上传目录
UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

first_request_done = False


@app.before_request
def initialize():
    global first_request_done
    if not first_request_done:
        try:
            # 不再需要手动创建表，Flask-Migrate 会处理
            # 创建默认管理员用户
            if not User.query.filter_by(username='admin').first():
                admin = User(username='admin', role='admin')
                admin.set_password('admin123')
                db.session.add(admin)
                db.session.commit()

            # 尝试创建百度人脸库分组
            if BAIDU_AI_AVAILABLE:
                baidu_face.create_group()
                print("百度人脸库分组创建成功或已存在")
            else:
                print("百度AI服务未启用，使用模拟模式")

            first_request_done = True
        except Exception as e:
            print(f"初始化错误: {e}")
            first_request_done = True


@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            flash('登录成功!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('用户名或密码错误!', 'error')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('已成功退出登录!', 'success')
    return redirect(url_for('login'))


@app.route('/dashboard')
def dashboard():
    try:
        if 'user_id' not in session:
            return redirect(url_for('login'))

        # 获取统计数据
        total_students = Student.query.count()
        today_attendance = Attendance.query.filter(
            db.func.date(Attendance.timestamp) == datetime.today().date()
        ).count()

        # 获取最近5条考勤记录
        recent_attendance = Attendance.query.order_by(Attendance.timestamp.desc()).limit(5).all()

        return render_template('dashboard.html',
                               total_students=total_students,
                               today_attendance=today_attendance,
                               recent_attendance=recent_attendance,
                               current_date=datetime.now().strftime('%Y年%m月%d日'))
    except Exception as e:
        print(f"仪表盘错误: {e}")
        return render_template('error.html', message="加载仪表盘时发生错误")


@app.route('/attendance')
def attendance_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('attendance.html')


@app.route('/settings')
def settings_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if session.get('role') != 'admin':
        flash('您没有权限访问系统设置', 'error')
        return redirect(url_for('dashboard'))

    return render_template('settings.html')


@app.route('/profile')
def profile_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    return render_template('profile.html', user=user)


@app.route('/api/face_recognition', methods=['POST'])
def face_recognition_api():
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': '请先登录'})

        # 获取前端传来的图片数据
        image_data = request.json.get('image')
        if not image_data:
            return jsonify({'success': False, 'message': '未收到图片数据'})

        # 保存图片
        image_filename = f"attendance_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
        image_path = os.path.join(UPLOAD_FOLDER, image_filename)

        # 处理base64图片数据
        try:
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            image_binary = base64.b64decode(image_data)
            with open(image_path, 'wb') as f:
                f.write(image_binary)
        except Exception as e:
            return jsonify({'success': False, 'message': f'图片处理错误: {str(e)}'})

        # 调用百度AI人脸识别
        try:
            # 搜索人脸库
            result = baidu_face.search_face(image_path)

            if result and result.get('error_code') == 0:
                if result.get('result') and result['result'].get('user_list'):
                    user_info = result['result']['user_list'][0]
                    confidence = user_info.get('score', 0)
                    user_id = user_info.get('user_id')

                    # 设置置信度阈值（百度AI的置信度范围是0-100）
                    if confidence > 80:  # 置信度大于80
                        # 根据user_id查找学生（user_id就是学号）
                        student = Student.query.filter_by(student_id=user_id).first()
                        if student:
                            # 记录考勤
                            attendance = Attendance(
                                student_id=student.id,
                                image_path=image_path,
                                confidence=confidence
                            )
                            db.session.add(attendance)
                            db.session.commit()

                            return jsonify({
                                'success': True,
                                'message': f'打卡成功! 识别到学生: {student.name}',
                                'student_name': student.name,
                                'confidence': confidence
                            })
                        else:
                            return jsonify({
                                'success': False,
                                'message': '识别成功但未找到对应学生信息'
                            })
                    else:
                        return jsonify({
                            'success': False,
                            'message': f'识别置信度不足: {confidence}'
                        })
                else:
                    return jsonify({
                        'success': False,
                        'message': '未识别到人脸或人脸不在库中'
                    })
            else:
                error_msg = result.get('error_msg', '未知错误') if result else '百度AI服务无响应'
                return jsonify({
                    'success': False,
                    'message': f'人脸识别错误: {error_msg}'
                })

        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'人脸识别错误: {str(e)}'
            })
    except Exception as e:
        print(f"人脸识别API错误: {e}")
        return jsonify({'success': False, 'message': '服务器内部错误'})


@app.route('/students')
def students_page():
    try:
        if 'user_id' not in session:
            return redirect(url_for('login'))

        students = Student.query.all()
        return render_template('students.html', students=students)
    except Exception as e:
        print(f"学生页面错误: {e}")
        return render_template('error.html', message="加载学生页面时发生错误")


@app.route('/api/students', methods=['POST'])
def add_student():
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': '请先登录'})

        student_id = request.json.get('student_id')
        name = request.json.get('name')
        image_data = request.json.get('image')

        if not all([student_id, name, image_data]):
            return jsonify({'success': False, 'message': '请填写完整信息'})

        # 检查学号是否已存在
        if Student.query.filter_by(student_id=student_id).first():
            return jsonify({'success': False, 'message': '该学号已存在'})

        # 保存图片
        image_filename = f"student_{student_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
        image_path = os.path.join(UPLOAD_FOLDER, image_filename)

        try:
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            image_binary = base64.b64decode(image_data)
            with open(image_path, 'wb') as f:
                f.write(image_binary)
        except Exception as e:
            return jsonify({'success': False, 'message': f'图片处理错误: {str(e)}'})

        # 添加人脸到百度AI人脸库
        try:
            print(f"开始添加人脸到百度AI，学号: {student_id}, 姓名: {name}")

            # 检查图片文件是否存在
            if not os.path.exists(image_path):
                return jsonify({'success': False, 'message': '图片文件不存在'})

            face_result = baidu_face.add_face(image_path, student_id, name)
            print(f"百度AI人脸添加结果: {face_result}")

            if face_result and face_result.get('error_code') == 0:
                # 百度AI人脸注册成功，获取face_token
                face_token = face_result.get('result', {}).get('face_token')

                # 创建学生记录
                student = Student(
                    student_id=student_id,
                    name=name,
                    face_id=face_token  # 存储百度AI返回的face_token
                )
                db.session.add(student)
                db.session.commit()

                return jsonify({'success': True, 'message': '学生添加成功'})
            else:
                # 更详细的错误信息
                error_msg = '人脸注册失败'
                if face_result:
                    error_msg = f"百度AI错误: {face_result.get('error_msg', '未知错误')} (代码: {face_result.get('error_code', '未知')})"
                return jsonify({'success': False, 'message': error_msg})

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"添加学生异常详情: {error_details}")
            return jsonify({'success': False, 'message': f'人脸注册错误: {str(e)}'})
    except Exception as e:
        print(f"添加学生API错误: {e}")
        return jsonify({'success': False, 'message': '服务器内部错误'})


@app.route('/api/attendance_records')
def get_attendance_records():
    try:
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': '请先登录'})

        # 获取考勤记录（最近7天），使用中国时区
        seven_days_ago = get_china_time().date() - timedelta(days=7)
        records = Attendance.query.filter(
            Attendance.timestamp >= seven_days_ago
        ).order_by(Attendance.timestamp.desc()).all()

        records_data = []
        for record in records:
            # 将UTC时间转换为中国时间
            if record.timestamp.tzinfo is None:
                # 如果时间没有时区信息，假设是UTC
                china_time = record.timestamp.replace(tzinfo=pytz.utc).astimezone(china_tz)
            else:
                china_time = record.timestamp.astimezone(china_tz)

            records_data.append({
                'id': record.id,
                'student_name': record.student.name,
                'student_id': record.student.student_id,
                'timestamp': china_time.strftime('%Y-%m-%d %H:%M:%S'),
                'status': record.status,
                'confidence': record.confidence
            })

        return jsonify({'success': True, 'records': records_data})
    except Exception as e:
        print(f"获取考勤记录错误: {e}")
        return jsonify({'success': False, 'message': '获取考勤记录时发生错误'})


# 错误处理
@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', message="页面未找到"), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', message="服务器内部错误"), 500


if __name__ == '__main__':
    app.run(debug=True,threaded=True)