#!/usr/bin/env python
"""Development-only database initialiser.

WARNING: This script calls db.drop_all() which DESTROYS ALL DATA.
It exists only for local development resets.  For all other environments
(staging, production, or any environment with real data) use:

    flask db upgrade

to apply migrations safely without data loss.
"""
import sys

from app import app
from models import db

if __name__ == '__main__':
    confirm = input(
        "WARNING: This will DROP and recreate all tables, deleting all data.\n"
        "Type 'yes' to continue, anything else to abort: "
    )
    if confirm.strip().lower() != 'yes':
        print("Aborted.")
        sys.exit(0)

    with app.app_context():
        db.drop_all()
        db.create_all()
        print("Database reset complete.")
