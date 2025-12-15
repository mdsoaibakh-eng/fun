from app import create_app, db
from models import Category

app = create_app()

with app.app_context():
    # Create tables if they don't exist (this will create Category and others in MySQL)
    db.create_all()
    
    # Seed Categories
    categories = ['Academic', 'Sports', 'Culture', 'Workshop', 'Seminar', 'Hostel']
    for cat_name in categories:
        if not Category.query.filter_by(name=cat_name).first():
            db.session.add(Category(name=cat_name))
            print(f"Added category: {cat_name}")
    
    db.session.commit()
    print("Database seeded successfully.")
