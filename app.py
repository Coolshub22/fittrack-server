import os
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_restful import Api, Resource
from models import db, User, Workout, WorkoutType, ExerciseTemplate, WorkoutExercise, PersonalBest
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "a-secure-default-secret-key")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=30)
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://fittrack_db_1nck_user:yAvE12ifRErOeZokwYLK6iogffk1d3Mi@dpg-d1hod87fte5s73ahsfgg-a.virginia-postgres.render.com/fittrack_db_1nck"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.json.compact = False

db.init_app(app=app)
migrate = Migrate(app=app, db=db)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)
CORS(app)
api = Api(app)

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({"error": "Not found"}), 404)

def recalculate_personal_bests(user_id):
    from sqlalchemy import func

    # Clear all existing PBs
    PersonalBest.query.filter_by(user_id=user_id).delete()

    # Aggregate max values per exercise name
    workout_data = (
        db.session.query(
            ExerciseTemplate.name.label("exercise_name"),
            func.max(WorkoutExercise.weight).label("max_weight"),
            func.max(WorkoutExercise.reps).label("max_reps"),
            func.max(WorkoutExercise.duration).label("max_duration"),
            func.max(WorkoutExercise.distance).label("max_distance")
        )
        .join(ExerciseTemplate, WorkoutExercise.exercise_template_id == ExerciseTemplate.id)
        .join(Workout, WorkoutExercise.workout_id == Workout.id)
        .filter(Workout.user_id == user_id)
        .group_by(ExerciseTemplate.name)
        .all()
    )

    for row in workout_data:
        pb = PersonalBest(
            user_id=user_id,
            exercise_name=row.exercise_name,
            max_weight=row.max_weight,
            max_reps=row.max_reps,
            max_duration=row.max_duration,
            max_distance=row.max_distance,
            date_achieved=datetime.now()
        )
        db.session.add(pb)

    db.session.commit()

def update_user_streaks(user_id):
    user = User.query.get(user_id)
    if user:
        user.longest_streak = user.get_longest_streak()
        db.session.commit()

class Index(Resource):
    def get(self):
        body = {"message": "Welcome to FitTrack API!"}
        return body, 200

class Register(Resource):
    def post(self):
        data = request.get_json()
        if not data or not all(k in data for k in ("username", "email", "password")):
            return make_response(jsonify({"error": "Missing required fields: username, email, password"}), 400)

        if User.query.filter_by(username=data["username"]).first():
            return make_response(jsonify({"error": "Username already exists"}), 409)

        if User.query.filter_by(email=data["email"]).first():
            return make_response(jsonify({"error": "Email already exists"}), 409)

        hashed_password = bcrypt.generate_password_hash(data["password"]).decode('utf-8')
        new_user = User(
            username=data["username"], email=data["email"], password_hash=hashed_password
        )

        try:
            db.session.add(new_user)
            db.session.commit()
            access_token = create_access_token(identity=new_user.id)
            return {"access_token": access_token, "user_id": new_user.id}, 201
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({"error": f"An unexpected error occurred: {e}"}), 500)

class Login(Resource):
    def post(self):
        data = request.get_json()
        if not data or not data.get("username") or not data.get("password"):
            return make_response(jsonify({"error": "Missing username or password"}), 400)

        user = User.query.filter_by(username=data["username"]).first()

        if user and bcrypt.check_password_hash(user.password_hash, data["password"]):
            access_token = create_access_token(identity=user.id)
            return {"access_token": access_token, "user_id": user.id}, 200

        return make_response(jsonify({"error": "Invalid credentials"}), 401)

class UserList(Resource):
    @jwt_required()
    def get(self):
        users = User.query.all()
        try:
            return [u.to_dict(include_current_streak=True) for u in users], 200
        except Exception as e:
            return make_response(jsonify({"error": f"Failed to serialize user: {e}"}), 500)

class Profile(Resource):
    @jwt_required()
    def get(self):
        current_user_id = get_jwt_identity()
        user = User.query.get_or_404(current_user_id)
        return user.to_dict(rules=('-workouts', '-password_hash')), 200

    @jwt_required()
    def patch(self):
        current_user_id = get_jwt_identity()
        user = User.query.get_or_404(current_user_id)
        data = request.get_json()

        if not data:
            return make_response(jsonify({"error": "No data provided for update"}), 400)

        if "username" in data and data["username"] != user.username:
            if User.query.filter_by(username=data["username"]).first():
                return make_response(jsonify({"error": "Username already exists"}), 409)
            user.username = data["username"]

        if "email" in data and data["email"] != user.email:
            if User.query.filter_by(email=data["email"]).first():
                return make_response(jsonify({"error": "Email already exists"}), 409)
            user.email = data["email"]

        try:
            db.session.commit()
            return user.to_dict(rules=('-workouts', '-password_hash')), 200
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({"error": f"An unexpected error occurred: {e}"}), 500)

    @jwt_required()
    def delete(self):
        current_user_id = get_jwt_identity()
        user = User.query.get_or_404(current_user_id)
        try:
            db.session.delete(user)
            db.session.commit()
            return {"message": "User profile deleted successfully."}, 200
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({"error": f"An unexpected error occurred: {e}"}), 500)

class WorkoutTypeList(Resource):
    @jwt_required()
    def get(self):
        types = WorkoutType.query.all()
        return [wt.to_dict() for wt in types], 200

class ExerciseTemplateList(Resource):
    @jwt_required()
    def get(self, workout_type_id):
        workout_type = WorkoutType.query.get(workout_type_id)
        if not workout_type:
            return make_response(jsonify({'error': 'WorkoutType not found'}), 404)
        
        exercises = ExerciseTemplate.query.filter_by(workout_type_id=workout_type_id).all()
        return [et.to_dict() for et in exercises], 200

class WorkoutList(Resource):
    @jwt_required()
    def get(self):
        current_user_id = get_jwt_identity()
        workouts = Workout.query.filter_by(user_id=current_user_id).all()
        return [w.to_dict() for w in workouts], 200

    @jwt_required()
    def post(self):
        current_user_id = get_jwt_identity()
        data = request.get_json()

        try:
            workout_name = data.get('workout_name')
            date_str = data.get('date')
            workout_type_id = data.get('workout_type_id')
            exercises_data = data.get('exercises', [])

            if not all([workout_name, date_str, workout_type_id]):
                return make_response(jsonify({"error": "Missing required fields: workout_name, date, workout_type_id"}), 400)

            workout_date = datetime.fromisoformat(date_str.replace('Z', '+00:00') if date_str.endswith('Z') else date_str)

            workout_type = WorkoutType.query.get(workout_type_id)
            if not workout_type:
                return make_response(jsonify({"error": "Workout type not found"}), 404)

            new_workout = Workout(
                workout_name=workout_name,
                notes=data.get('notes'),
                intensity=float(data.get('intensity')) if data.get('intensity') is not None else None,
                duration=int(data.get('duration')) if data.get('duration') is not None else None,
                date=workout_date,
                user_id=current_user_id,
                workout_type_id=workout_type_id
            )
            
            new_workout.estimated_calories = new_workout.calculate_estimated_calories()

            db.session.add(new_workout)
            db.session.flush()

            for ex_data in exercises_data:
                exercise_template_id = ex_data.get('exercise_template_id')
                
                exercise_template = ExerciseTemplate.query.get(exercise_template_id)
                if not exercise_template:
                    db.session.rollback()
                    return make_response(jsonify({'error': f'Exercise template ID {exercise_template_id} not found.'}), 400)
                
                if exercise_template.workout_type_id != workout_type_id:
                     db.session.rollback()
                     return make_response(jsonify({'error': f'Exercise template ID {exercise_template_id} does not belong to the selected workout type.'}), 400)

                workout_exercise = WorkoutExercise(
                    workout_id=new_workout.id,
                    exercise_template_id=exercise_template_id,
                    sets=int(ex_data.get('sets')) if ex_data.get('sets') is not None else None,
                    reps=int(ex_data.get('reps')) if ex_data.get('reps') is not None else None,
                    weight=float(ex_data.get('weight')) if ex_data.get('weight') is not None else None,
                    duration=int(ex_data.get('duration')) if ex_data.get('duration') is not None else None,
                    distance=float(ex_data.get('distance')) if ex_data.get('distance') is not None else None
                )
                db.session.add(workout_exercise)
            
            db.session.commit()
            recalculate_personal_bests(current_user_id)
            update_user_streaks(current_user_id)
            return new_workout.to_dict(), 201

        except ValueError as ve:
            db.session.rollback()
            return make_response(jsonify({"error": str(ve)}), 400)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({"error": f"An unexpected error occurred: {e}"}), 500)

class WorkoutResource(Resource):
    @jwt_required()
    def get(self, workout_id):
        current_user_id = get_jwt_identity()
        workout = Workout.query.filter_by(id=workout_id, user_id=current_user_id).first_or_404()
        return workout.to_dict(), 200

    @jwt_required()
    def patch(self, workout_id):
        current_user_id = get_jwt_identity()
        workout = Workout.query.filter_by(id=workout_id, user_id=current_user_id).first_or_404()
        data = request.get_json()

        if not data:
            return make_response(jsonify({"error": "No data provided for update"}), 400)

        try:
            # Update main workout fields
            workout.workout_name = data.get('workout_name', workout.workout_name)
            workout.notes = data.get('notes', workout.notes)
            
            workout.intensity = float(data.get('intensity')) if data.get('intensity') is not None else workout.intensity
            workout.duration = int(data.get('duration')) if data.get('duration') is not None else workout.duration
            
            date_str = data.get('date')
            if date_str:
                workout.date = datetime.fromisoformat(date_str.replace('Z', '+00:00') if date_str.endswith('Z') else date_str)

            new_workout_type_id = data.get('workout_type_id')
            if new_workout_type_id is not None and new_workout_type_id != workout.workout_type_id:
                workout_type = WorkoutType.query.get(new_workout_type_id)
                if not workout_type:
                    return make_response(jsonify({'error': 'New workout type not found'}), 404)
                workout.workout_type_id = new_workout_type_id
                # If workout type changes, it's safer to clear existing WorkoutExercises
                # as they might not be valid for the new type.
                WorkoutExercise.query.filter_by(workout_id=workout.id).delete()
                # If workout type changes, we assume all old exercises are gone and new ones will be provided
                # So we continue to the exercise update logic below.
            
            exercises_data = data.get('exercises')
            if exercises_data is not None:
                # Get current exercise IDs for this workout
                current_exercise_ids = {we.id for we in workout.workout_exercises}
                updated_or_new_exercise_ids = set()

                for ex_data in exercises_data:
                    exercise_template_id = ex_data.get('exercise_template_id')
                    exercise_template = ExerciseTemplate.query.get(exercise_template_id)
                    if not exercise_template:
                        db.session.rollback()
                        return make_response(jsonify({'error': f'Exercise template ID {exercise_template_id} not found for update.'}), 400)
                    
                    if exercise_template.workout_type_id != workout.workout_type_id:
                         db.session.rollback()
                         return make_response(jsonify({'error': f'Exercise template ID {exercise_template_id} does not belong to the updated workout type.'}), 400)

                    # Check if this is an existing exercise (by id, if provided from frontend)
                    workout_exercise_id = ex_data.get('id')
                    if workout_exercise_id:
                        # Find the existing WorkoutExercise instance
                        existing_we = WorkoutExercise.query.get(workout_exercise_id)
                        if existing_we and existing_we.workout_id == workout.id:
                            # Update existing exercise
                            existing_we.sets = int(ex_data.get('sets')) if ex_data.get('sets') is not None else existing_we.sets
                            existing_we.reps = int(ex_data.get('reps')) if ex_data.get('reps') is not None else existing_we.reps
                            existing_we.weight = float(ex_data.get('weight')) if ex_data.get('weight') is not None else existing_we.weight
                            existing_we.duration = int(ex_data.get('duration')) if ex_data.get('duration') is not None else existing_we.duration
                            existing_we.distance = float(ex_data.get('distance')) if ex_data.get('distance') is not None else existing_we.distance
                            updated_or_new_exercise_ids.add(existing_we.id)
                        else:
                            # If ID provided but not found or doesn't belong to this workout, treat as new
                            workout_exercise = WorkoutExercise(
                                workout_id=workout.id,
                                exercise_template_id=exercise_template_id,
                                sets=int(ex_data.get('sets')) if ex_data.get('sets') is not None else None,
                                reps=int(ex_data.get('reps')) if ex_data.get('reps') is not None else None,
                                weight=float(ex_data.get('weight')) if ex_data.get('weight') is not None else None,
                                duration=int(ex_data.get('duration')) if ex_data.get('duration') is not None else None,
                                distance=float(ex_data.get('distance')) if ex_data.get('distance') is not None else None
                            )
                            db.session.add(workout_exercise)
                            db.session.flush() # To get ID for tracking
                            updated_or_new_exercise_ids.add(workout_exercise.id)
                    else:
                        # Add new exercise
                        workout_exercise = WorkoutExercise(
                            workout_id=workout.id,
                            exercise_template_id=exercise_template_id,
                            sets=int(ex_data.get('sets')) if ex_data.get('sets') is not None else None,
                            reps=int(ex_data.get('reps')) if ex_data.get('reps') is not None else None,
                            weight=float(ex_data.get('weight')) if ex_data.get('weight') is not None else None,
                            duration=int(ex_data.get('duration')) if ex_data.get('duration') is not None else None,
                            distance=float(ex_data.get('distance')) if ex_data.get('distance') is not None else None
                        )
                        db.session.add(workout_exercise)
                        db.session.flush() # To get ID for tracking
                        updated_or_new_exercise_ids.add(workout_exercise.id)

                # Delete exercises that are no longer present in the updated list
                exercises_to_delete = current_exercise_ids - updated_or_new_exercise_ids
                for we_id in exercises_to_delete:
                    we_to_delete = WorkoutExercise.query.get(we_id)
                    if we_to_delete:
                        db.session.delete(we_to_delete)
            
            workout.estimated_calories = workout.calculate_estimated_calories()
            db.session.commit()
            recalculate_personal_bests(current_user_id)
            update_user_streaks(current_user_id)
            return workout.to_dict(), 200

        except ValueError as ve:
            db.session.rollback()
            return make_response(jsonify({"error": str(ve)}), 400)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500)

    @jwt_required()
    def delete(self, workout_id):
        current_user_id = get_jwt_identity()
        workout = Workout.query.filter_by(id=workout_id, user_id=current_user_id).first_or_404()
        try:
            db.session.delete(workout)
            recalculate_personal_bests(current_user_id)
            update_user_streaks(current_user_id)
            db.session.commit()
            return make_response(jsonify({"message": f"Workout {workout_id} deleted successfully."}), 200)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({"error": f"An unexpected error occurred: {e}"}), 500)


class ProgressSummary(Resource):
    @jwt_required()
    def get(self):
        current_user_id = get_jwt_identity()

        try:
            user = User.query.get_or_404(current_user_id) 
            current_streak_value = user.get_current_streak() 
            longest_streak_value = user.longest_streak
            db.session.commit() 
        except Exception as e:
            return make_response(jsonify({"error": f"Failed to get user data or calculate streak: {e}"}), 500)
        
        workouts = Workout.query.filter_by(user_id=current_user_id).all()
        total_workouts = len(workouts)
        
        total_exercises = sum(len(w.workout_exercises) for w in workouts)
        calories_burned = sum(w.estimated_calories or 0 for w in workouts)
        total_duration = sum(w.duration or 0 for w in workouts)
        
        total_distance = sum(
            we.distance or 0 
            for w in workouts 
            for we in w.workout_exercises 
            if we.distance is not None
        )

        pb_squat = (
            PersonalBest.query
            .filter_by(user_id=current_user_id, exercise_name="Squats")
            .order_by(PersonalBest.max_weight.desc())
            .first()
        )

        pb_run = (
            PersonalBest.query
            .filter_by(user_id=current_user_id, exercise_name="Running")
            .order_by(PersonalBest.max_distance.desc())
            .first()
        )
        
        summary = {
            "totalWorkouts": total_workouts,
            "totalExercises": total_exercises,
            "caloriesBurned": int(calories_burned),
            "avgWorkoutDuration": f"{int(total_duration / total_workouts)} minutes" if total_workouts else "0 minutes",
            "currentStreak": current_streak_value,
            "personalBestSquat": f"{pb_squat.max_weight} kg" if pb_squat and pb_squat.max_weight else "N/A",
            "longestRun": f"{pb_run.max_distance} km" if pb_run and pb_run.max_distance else "N/A",
            "totalDistance": f"{total_distance} km",
            "longestStreak": longest_streak_value,
        }

        return summary, 200

class PersonalBestList(Resource):
    @jwt_required()
    def get(self):
        current_user_id = get_jwt_identity()
        personal_bests = PersonalBest.query.filter_by(user_id=current_user_id).all()
        return [pb.to_dict() for pb in personal_bests], 200

    @jwt_required()
    def post(self):
        current_user_id = get_jwt_identity()
        data = request.get_json()

        if not data or not data.get("exercise_name"):
            return make_response(jsonify({"error": "Missing required field: exercise_name"}), 400)

        new_pb = PersonalBest(
            user_id=current_user_id,
            exercise_name=data["exercise_name"],
            max_weight=data.get("max_weight"),
            max_reps=data.get("max_reps"),
            max_duration=data.get("max_duration"),
            max_distance=data.get("max_distance"),
            date_achieved=datetime.now()
        )

        try:
            db.session.add(new_pb)
            db.session.commit()
            return new_pb.to_dict(), 201
        except ValueError as ve:
            db.session.rollback()
            return make_response(jsonify({"error": str(ve)}), 400)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({"error": f"Unexpected error: {e}"}), 500)

class PersonalBestResource(Resource):
    @jwt_required()
    def patch(self, pb_id):
        current_user_id = get_jwt_identity()
        pb = PersonalBest.query.filter_by(id=pb_id, user_id=current_user_id).first_or_404()
        data = request.get_json()

        try:
            for key, value in data.items():
                if hasattr(pb, key):
                    if key in ['max_weight', 'max_distance'] and value is not None:
                        setattr(pb, key, float(value))
                    elif key in ['max_reps', 'max_duration'] and value is not None:
                        setattr(pb, key, int(value))
                    else:
                        setattr(pb, key, value)
            pb.date_achieved = datetime.now()

            db.session.commit()
            return pb.to_dict(), 200
        except ValueError as ve:
            db.session.rollback()
            return make_response(jsonify({"error": str(ve)}), 400)
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({"error": f"Unexpected error: {e}"}), 500)

    @jwt_required()
    def delete(self, pb_id):
        current_user_id = get_jwt_identity()
        pb = PersonalBest.query.filter_by(id=pb_id, user_id=current_user_id).first_or_404()

        try:
            db.session.delete(pb)
            db.session.commit()
            return {"message": "Personal best deleted."}, 200
        except Exception as e:
            db.session.rollback()
            return make_response(jsonify({"error": f"An unexpected error occurred: {e}"}), 500)

api.add_resource(Index, "/")
api.add_resource(Register, "/register")
api.add_resource(Login, "/login")
api.add_resource(UserList, "/users")
api.add_resource(Profile, "/profile")
api.add_resource(WorkoutTypeList, "/workout_types")
api.add_resource(ExerciseTemplateList, "/workout_types/<int:workout_type_id>/exercises")
api.add_resource(WorkoutList, "/workouts")
api.add_resource(WorkoutResource, "/workouts/<int:workout_id>")
api.add_resource(ProgressSummary, "/progress")
api.add_resource(PersonalBestList, "/personal-bests")
api.add_resource(PersonalBestResource, "/personal-bests/<int:pb_id>")

if __name__ == "__main__":
    app.run(port=5000, debug=True)