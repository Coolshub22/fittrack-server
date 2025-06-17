from flask import Flask
from flask_migrate import Migrate
from models import db

# heart of app
app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///fittrack.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


migrate = Migrate(app=app, db=db)

db.init_app(app=app)



# running flask apps

# if __name__ == '__main__':
#     app.run(port=9000, debug=True)
