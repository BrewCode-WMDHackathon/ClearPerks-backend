import os
import socket
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.engine.url import make_url
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in the environment variables")

# Try to resolve hostname to IPv4 to avoid IPv6 issues in some environments (like HF Spaces)
engine_args = {}
try:
    url = make_url(DATABASE_URL)
    if url.host:
        # Resolve hostname to IPv4
        ip_address = socket.gethostbyname(url.host)
        print(f"Resolved {url.host} to {ip_address}")
        # Pass hostaddr to libpq via connect_args to force IPv4 connection
        # while keeping the original hostname for SNI/SSL verification.
        engine_args["connect_args"] = {"hostaddr": ip_address}
except Exception as e:
    print(f"Failed to resolve hostname or configure IPv4: {e}")

engine = create_engine(DATABASE_URL, echo=False, **engine_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
