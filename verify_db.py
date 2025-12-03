from app import create_app
from models import db, Event, Registration, Student, Admin

app = create_app()

with app.app_context():
    print("Checking database tables...")
    inspector = db.inspect(db.engine)
    tables = inspector.get_table_names()
    print(f"Tables found: {tables}")
    
    expected_tables = ['events', 'registrations', 'students', 'admins']
    missing_tables = [t for t in expected_tables if t not in tables]
    
    if missing_tables:
        print(f"ERROR: Missing tables: {missing_tables}")
    else:
        print("SUCCESS: All expected tables found.")
        
    # Check Event columns
    columns = [c['name'] for c in inspector.get_columns('events')]
    print(f"Event columns: {columns}")
    if 'date' in columns and 'location' in columns:
        print("SUCCESS: Event table has new columns.")
    else:
        print("ERROR: Event table missing new columns.")
