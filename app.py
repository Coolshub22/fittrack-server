from flask import Flask, request,jsonify
from flask_cors import CORS
from flask_migrate import Migrate
from models import db, User, Workout,Exercise
from werkzeug.security import generate_password_hash, check_password_hash

# heart of app
app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///fittrack.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


migrate = Migrate(app=app, db=db)

db.init_app(app=app)
CORS(app)


@app.before_request
def create_tables():
    db.create_all
    
    
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404



@app.route('/users', methods=['POST'])
def create_user():
    """Create a new user."""
    data = request.get_json()
    if not data or not data.get('username') or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Missing required fields'}), 400
        
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 409

    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already exists'}), 409

    hashed_password = generate_password_hash(data['password'])
    new_user = User(
        username=data['username'],
        email=data['email'],
        password_hash=hashed_password
    )
    db.session.add(new_user)
    db.session.commit()
    
    user_data = new_user.to_json()
    user_data.pop('password_hash', None) 

    return jsonify(user_data), 201

@app.route('/users', methods=['GET'])
def get_users():
    """Get all users."""
    users = User.query.all()
    return jsonify([user.to_json() for user in users])

@app.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """Get a single user by ID."""
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_json())

@app.route('/users/<int:user_id>', methods=['PATCH'])
def update_user(user_id):
    """Update a user's information."""
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    
    if 'username' in data:
        user.username = data['username']
    if 'email' in data:
        user.email = data['email']
        
    db.session.commit()
    return jsonify(user.to_json())

@app.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Delete a user."""
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': f'User {user_id} deleted successfully.'}), 200



@app.route('/workouts', methods=['POST'])
def create_workout():
    """Create a new workout for a user."""
    data = request.get_json()
    if not data or not data.get('name') or not data.get('date') or not data.get('user_id'):
        return jsonify({'error': 'Missing required fields'}), 400
    
    User.query.get_or_404(data['user_id'])

    new_workout = Workout(
        name=data['name'],
        date=data['date'],
        notes=data.get('notes'),
        user_id=data['user_id']
    )
    db.session.add(new_workout)
    db.session.commit()
    return jsonify(new_workout.to_json()), 201

@app.route('/workouts', methods=['GET'])
def get_workouts():
    """Get all workouts, optionally filtered by user_id."""
    user_id = request.args.get('user_id')
    if user_id:
        workouts = Workout.query.filter_by(user_id=user_id).all()
    else:
        workouts = Workout.query.all()
    return jsonify([workout.to_json() for workout in workouts])

@app.route('/workouts/<int:workout_id>', methods=['GET'])
def get_workout(workout_id):
    """Get a single workout by ID."""
    workout = Workout.query.get_or_404(workout_id)
    return jsonify(workout.to_json())

@app.route('/workouts/<int:workout_id>', methods=['PATCH'])
def update_workout(workout_id):
    """Update a workout's information."""
    workout = Workout.query.get_or_404(workout_id)
    data = request.get_json()
    
    if 'name' in data:
        workout.name = data['name']
    if 'date' in data:
        workout.date = data['date']
    if 'notes' in data:
        workout.notes = data['notes']
        
    db.session.commit()
    return jsonify(workout.to_json())

@app.route('/workouts/<int:workout_id>', methods=['DELETE'])
def delete_workout(workout_id):
    """Delete a workout."""
    workout = Workout.query.get_or_404(workout_id)
    db.session.delete(workout)
    db.session.commit()
    return jsonify({'message': f'Workout {workout_id} deleted successfully.'}), 200



# running flask apps

# if __name__ == '__main__':
#     app.run(port=9000, debug=True)
