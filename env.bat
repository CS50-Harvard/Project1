
set FLASK_DEBUG=true
set FLASK_APP=application.py
set DATABASE_URL=postgres://postgres:postgres@localhost:5432/project1

pip install flask
pip install psycopg2
pip install flask_sqlalchemy
pip install requests