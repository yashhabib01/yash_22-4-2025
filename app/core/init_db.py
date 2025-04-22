from app.core.database import init_db
from app.models import models  # This import is necessary to register the models

def main():
    print("Creating database tables...")
    init_db()
    print("Database tables created successfully!")

if __name__ == "__main__":
    main() 