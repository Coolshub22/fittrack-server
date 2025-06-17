from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
from datetime import datetime


metadata = MetaData()

db = SQLAlchemy(metadata=metadata)