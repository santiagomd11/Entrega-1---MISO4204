from flask import request
from flask import jsonify
from flask_restful import Resource
import hashlib
from datetime import datetime
from moviepy.editor import *
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
import os

from models import (
    db,
    User,
    UserSchema,
    Task,
    TaskSchema,
    FileExtensions,
    ConversionFile
)

user_schema = UserSchema()
task_schema = TaskSchema()

class ViewRegister(Resource):
    def post(self):
        email_request = request.json["email"]
        user_request = request.json["user"]

        exist_email = User.query.filter(
            User.email == email_request
        ).first()

        exist_user = User.query.filter(
            User.user == user_request
        ).first()

        if exist_email is None and exist_user is None:
            password_encrypt = hashlib.sha3_512(
                request.json["password"].encode("utf-8")
            ).hexdigest()
            new_user = User(
                user = user_request,
                email = email_request,
                password = password_encrypt,
            )
            db.session.add(new_user)
            db.session.commit()
            return {"message": "User create successful"}, 201
        else:
            return {"message": "User or email already exist"}, 409
        

class ViewLogin(Resource):
    def post(self):
        password_encrypt = hashlib.sha3_512(
            request.json["password"].encode("utf-8")
        ).hexdigest()

        user_email_request = request.json["user"]

        query_email = User.query.filter(
            User.email == user_email_request,
            User.password == password_encrypt,
        ).first()

        query_user = User.query.filter(
            User.user == user_email_request,
            User.password == password_encrypt,
        ).first()

        if query_email != None:
            token_access = create_access_token(identity = query_email.id)
        elif query_user != None:
            token_access = create_access_token(identity = query_user.id)
        else:
            return {"message": "User not found"}, 404

        return {
            "message": "Login success",
            "token": token_access,
        }, 200
    
class ViewTask(Resource):
    @jwt_required()
    def get(self, id_task):
        task = Task.query.get_or_404(id_task)
        return task_schema.dump(Task.query.get_or_404(task.id))
    
    @jwt_required()
    def delete(self, id_task):
        try:
            task = Task.query.get_or_404(id_task)
            db.session.delete(task)
            db.session.commit()
            return '', 204
        except Exception as e:
            db.session.rollback()
            return jsonify(error=str(e)), 500


class ViewTasks(Resource):
    @jwt_required()
    def get(self):
        current_user_id = get_jwt_identity() 
        tasks = Task.query.filter_by(user_id=current_user_id).all()
        return task_schema.dump(tasks, many=True)
    

class ViewUploadAndConvert(Resource):
    @jwt_required()
    def get(self):
        auth_token = request.headers.get('Authorization')
        current_user_id = get_jwt_identity() 
        if not auth_token:
            return {'message': 'Token de autenticación inválido'}, 401 
        
        file = request.files['file']
        target_format = request.form['target_format']
        
        if target_format.lower() not in [e.value for e in FileExtensions]:
            return {'message': 'Formato de destino no admitido'}, 400 
        
        video = VideoFileClip(file)
        converted_file_name = file.filename.split('.')[0] + '.' + target_format.lower()
        user_download_path = os.path.join(os.path.expanduser('~'), 'Downloads', converted_file_name)
        video.write_videofile(user_download_path)
        
        timestamp = datetime.now()
        file_status = "processed"
        conversion_task = ConversionFile(user_id=current_user_id, file_name=converted_file_name, timestamp=timestamp, status=file_status)
        db.session.add(conversion_task)
        db.session.commit()
      
        return {'message': 'Archivo de video convertido y guardado correctamente'}, 200