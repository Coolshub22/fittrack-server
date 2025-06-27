# app.py
import os
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_restful import Api, Resource
from models import db, User, Workout, Exercise, PersonalBest
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()  # Load environment variables from .env

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "a-secure-default-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///fittrack.db"
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
    """Handles 404 Not Found errors."""
    return jsonify({"error": "Not found"}), 404

class Index(Resource):
    def get(self):
        """Welcome endpoint for the API."""
        body = {"message": "Welcome to FitTrack API!"}
        return make_response(body, 200)

class Register(Resource):
    def post(self):
        """Create a new user."""
        data = request.get_json()
        if not data or not all(k in data for k in ("username", "email", "password")):
            return jsonify({"error": "Missing required fields: username, email, password"}), 400

        if User.query.filter_by(username=data["username"]).first():
            return jsonify({"error": "Username already exists"}), 409

        if User.query.filter_by(email=data["email"]).first():
            return jsonify({"error": "Email already exists"}), 409

        hashed_password = bcrypt.generate_password_hash(data["password"]).decode('utf-8')
        new_user = User(
            username=data["username"], email=data["email"], password_hash=hashed_password
        )

        try:
            db.session.add(new_user)
            db.session.commit()
            access_token = create_access_token(identity=new_user.id)
            return make_response(jsonify(access_token=access_token, user_id=new_user.id), 201)
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"An unexpected error occurred: {e}"}), 500

class Login(Resource):
    def post(self):
        """Authenticate a user and return an access token."""
        data = request.get_json()
        if not data or not data.get("username") or not data.get("password"):
            return jsonify({"error": "Missing username or password"}), 400

        user = User.query.filter_by(username=data["username"]).first()

        if user and bcrypt.check_password_hash(user.password_hash, data["password"]):
            access_token = create_access_token(identity=user.id)
            return make_response(jsonify(access_token=access_token, user_id=user.id), 200)

        return jsonify({"error": "Invalid credentials"}), 401

class UserList(Resource):
    @jwt_required()
    def get(self):
        """Get all users (for admin purposes)."""
        users = User.query.all()
        return make_response(jsonify([user.to_dict(rules=('-workouts', '-password_hash')) for user in users]))

class Profile(Resource):
    @jwt_required()
    def get(self):
        """Get the profile of the currently logged-in user."""
        current_user_id = get_jwt_identity()
        user = User.query.get_or_404(current_user_id)
        return make_response(jsonify(user.to_dict(rules=('-workouts', '-password_hash'))))

    @jwt_required()
    def patch(self):
        """Update the profile of the currently logged-in user."""
        current_user_id = get_jwt_identity()
        user = User.query.get_or_404(current_user_id)
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided for update"}), 400

        if "username" in data and data["username"] != user.username:
            if User.query.filter_by(username=data["username"]).first():
                return jsonify({"error": "Username already exists"}), 409
            user.username = data["username"]

        if "email" in data and data["email"] != user.email:
            if User.query.filter_by(email=data["email"]).first():
                return jsonify({"error": "Email already exists"}), 409
            user.email = data["email"]

        try:
            db.session.commit()
            return make_response(jsonify(user.to_dict(rules=('-workouts', '-password_hash'))))
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"An unexpected error occurred: {e}"}), 500

    @jwt_required()
    def delete(self):
        """Delete the profile of the currently logged-in user."""
        current_user_id = get_jwt_identity()
        user = User.query.get_or_404(current_user_id)
        try:
            db.session.delete(user)
            db.session.commit()
            return make_response(jsonify({"message": "User profile deleted successfully."}), 200)
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"An unexpected error occurred: {e}"}), 500

class WorkoutList(Resource):
    @jwt_required()
    def get(self):
        workouts = Workout.query.all()
        return [w.to_dict() for w in workouts], 200

    @jwt_required()
    def post(self):
        current_user_id = get_jwt_identity()
        data = request.get_json()

        try:
            # Ensure required fields are present
            if 'workout_name' not in data or 'date' not in data:
                return {"error": "Missing required fields: workout_name and date"}, 400

            # Cast and parse values safely
            workout_name = data['workout_name']
            date = datetime.fromisoformat(data['date'])
            notes = data.get('notes')

            intensity = float(data.get('intensity', 0)) if data.get('intensity') else None
            duration = int(data.get('duration', 0)) if data.get('duration') else None

            # Create workout
            workout = Workout(
                workout_name=workout_name,
                date=date,
                notes=notes,
                intensity=intensity,
                duration=duration,
                user_id=current_user_id
            )

            # Estimate calories
            workout.estimated_calories = workout.calculate_estimated_calories()

            db.session.add(workout)
            db.session.commit()
            return workout.to_dict(), 201

        except Exception as e:
            db.session.rollback()
            return {"error": str(e)}, 400


class WorkoutResource(Resource):
    @jwt_required()
    def get(self, workout_id):
        """Get a single workout by ID."""
        current_user_id = get_jwt_identity()
        workout = Workout.query.filter_by(id=workout_id, user_id=current_user_id).first_or_404()
        return make_response(jsonify(workout.to_dict()))

    @jwt_required()
    def patch(self, workout_id):
        """Update a single workout by ID."""
        current_user_id = get_jwt_identity()
        workout = Workout.query.filter_by(id=workout_id, user_id=current_user_id).first_or_404()
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided for update"}), 400

        try:
            for key, value in data.items():
                if hasattr(workout, key):
                    if key == "intensity" and value is not None:
                        workout.intensity = float(value)
                    elif key == "duration" and value is not None:
                        workout.duration = int(value)
                    elif key == "date" and value:
                        workout.date = datetime.fromisoformat(value)
                    else:
                        setattr(workout, key, value)

            # Recalculate estimated calories only if both values are present
            if workout.duration and workout.intensity:
                workout.estimated_calories = workout.calculate_estimated_calories()

            db.session.commit()
            return make_response(jsonify(workout.to_dict()), 200)

        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

    
    @jwt_required()
    def delete(self, workout_id):
        """Delete a single workout by ID."""
        current_user_id = get_jwt_identity()
        workout = Workout.query.filter_by(id=workout_id, user_id=current_user_id).first_or_404()
        try:
            db.session.delete(workout)
            db.session.commit()
            return make_response(jsonify({"message": f"Workout {workout_id} deleted successfully."}), 200)
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"An unexpected error occurred: {e}"}), 500

class ExerciseList(Resource):
    @jwt_required()
    def post(self):
        """Create a new exercise for a workout owned by the logged-in user."""
        current_user_id = get_jwt_identity()
        data = request.get_json()
        if not data or not data.get("workout_id") or not data.get("name"):
            return jsonify({"error": "Missing required fields: workout_id and name"}), 400

        workout = Workout.query.filter_by(id=data["workout_id"], user_id=current_user_id).first_or_404()

        new_exercise = Exercise(
            name=data["name"],
            type=data.get("type"),
            sets=data.get("sets"),
            reps=data.get("reps"),
            weight=data.get("weight"),
            duration=data.get("duration"),
            workout_id=workout.id,
        )
        try:
            db.session.add(new_exercise)
            db.session.commit()
            return make_response(jsonify(new_exercise.to_dict()), 201)
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"An unexpected error occurred: {e}"}), 500

class ProgressSummary(Resource):
    @jwt_required()
    def get(self):
        """Get progress summary for the logged-in user."""
        current_user_id = get_jwt_identity()

        workouts = Workout.query.filter_by(user_id=current_user_id).all()
        total_workouts = len(workouts)
        total_exercises = sum(len(w.exercises) for w in workouts)
        calories_burned = sum(w.estimated_calories or 0 for w in workouts)
        total_duration = sum(w.duration or 0 for w in workouts)
        total_distance = sum(getattr(w, "distance", 0) or 0 for w in workouts)

        # Fetch personal bests
        pb_squat = (
            PersonalBest.query
            .filter_by(user_id=current_user_id, exercise_name="Squat")
            .order_by(PersonalBest.max_weight.desc())
            .first()
        )

        pb_run = (
            PersonalBest.query
            .filter_by(user_id=current_user_id, exercise_name="Run")
            .order_by(PersonalBest.max_duration.desc())
            .first()
        )

        user = User.query.get(current_user_id)
        current_streak = user.get_current_streak() if user else 0

        summary = {
            "totalWorkouts": total_workouts,
            "totalExercises": total_exercises,
            "caloriesBurned": int(calories_burned),
            "avgWorkoutDuration": f"{int(total_duration / total_workouts)} minutes" if total_workouts else "0 minutes",
            "currentStreak": current_streak,
            "personalBestSquat": f"{pb_squat.max_weight} kg" if pb_squat and pb_squat.max_weight else "N/A",
            "longestRun": f"{pb_run.max_duration} min" if pb_run and pb_run.max_duration else "N/A",
            "totalDistance": f"{total_distance} km",
            "longestStreak": user.longest_streak,

        }

        return make_response(jsonify(summary), 200)

class PersonalBestList(Resource):
    @jwt_required()
    def get(self):
        current_user_id = get_jwt_identity()
        personal_bests = PersonalBest.query.filter_by(user_id=current_user_id).all()
        return make_response(jsonify([pb.to_dict() for pb in personal_bests]), 200)

    @jwt_required()
    def post(self):
        current_user_id = get_jwt_identity()
        data = request.get_json()

        if not data or not data.get("exercise_name"):
            return jsonify({"error": "Missing required field: exercise_name"}), 400

        new_pb = PersonalBest(
            user_id=current_user_id,
            exercise_name=data["exercise_name"],
            max_weight=data.get("max_weight"),
            max_reps=data.get("max_reps"),
            max_duration=data.get("max_duration"),
        )

        try:
            db.session.add(new_pb)
            db.session.commit()
            return make_response(jsonify(new_pb.to_dict()), 201)
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"Unexpected error: {e}"}), 500

class PersonalBestResource(Resource):
    @jwt_required()
    def patch(self, pb_id):
        current_user_id = get_jwt_identity()
        pb = PersonalBest.query.filter_by(id=pb_id, user_id=current_user_id).first_or_404()
        data = request.get_json()

        for key, value in data.items():
            if hasattr(pb, key):
                setattr(pb, key, value)

        try:
            db.session.commit()
            return make_response(jsonify(pb.to_dict()), 200)
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"Unexpected error: {e}"}), 500

    @jwt_required()
    def delete(self, pb_id):
        current_user_id = get_jwt_identity()
        pb = PersonalBest.query.filter_by(id=pb_id, user_id=current_user_id).first_or_404()

        try:
            db.session.delete(pb)
            db.session.commit()
            return make_response(jsonify({"message": "Personal best deleted."}), 200)
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"Unexpected error: {e}"}), 500


class ExerciseResource(Resource):
    @jwt_required()
    def patch(self, exercise_id):
        """Update a single exercise by ID."""
        current_user_id = get_jwt_identity()
        exercise = (
            db.session.query(Exercise)
            .join(Workout)
            .filter(Exercise.id == exercise_id, Workout.user_id == current_user_id)
            .first_or_404()
        )
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided for update"}), 400

        for key, value in data.items():
            if hasattr(exercise, key):
                setattr(exercise, key, value)

        try:
            db.session.commit()
            return make_response(jsonify(exercise.to_dict()))
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"An unexpected error occurred: {e}"}), 500

    @jwt_required()
    def delete(self, exercise_id):
        """Delete a single exercise by ID."""
        current_user_id = get_jwt_identity()
        exercise = (
            db.session.query(Exercise)
            .join(Workout)
            .filter(Exercise.id == exercise_id, Workout.user_id == current_user_id)
            .first_or_404()
        )
        try:
            db.session.delete(exercise)
            db.session.commit()
            return make_response(jsonify({"message": f"Exercise {exercise_id} deleted successfully."}), 200)
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"An unexpected error occurred: {e}"}), 500

# Add resources to the API
api.add_resource(Index, "/")
api.add_resource(Register, "/register")
api.add_resource(Login, "/login")
api.add_resource(UserList, "/users")
api.add_resource(Profile, "/profile")
api.add_resource(WorkoutList, "/workouts")
api.add_resource(WorkoutResource, "/workouts/<int:workout_id>")
api.add_resource(ExerciseList, "/exercises")
api.add_resource(ExerciseResource, "/exercises/<int:exercise_id>")
api.add_resource(ProgressSummary, "/progress")
api.add_resource(PersonalBestList, "/personal-bests")
api.add_resource(PersonalBestResource, "/personal-bests/<int:pb_id>")

if __name__ == "__main__":
    app.run(port=5000, debug=True)
