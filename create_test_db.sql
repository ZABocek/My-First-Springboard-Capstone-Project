-- create_test_db.sql
-- Test database schema kept in sync with models.py / Alembic migrations.
-- For production and staging environments always use: flask db upgrade

-- Drop the database if it already exists
DROP DATABASE IF EXISTS test_cocktail_chronicles;

-- Create the test database
CREATE DATABASE test_cocktail_chronicles;

-- Connect to the test database
\c test_cocktail_chronicles;

-- Ingredients table
CREATE TABLE ingredient (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

-- Users table
CREATE TABLE "user" (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    preference VARCHAR DEFAULT 'alcoholic',
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    ban_until TIMESTAMP,
    is_permanently_banned BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    is_email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    email_verified_at TIMESTAMP
);

-- Admin messages (user → admin communication)
CREATE TABLE admin_message (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    subject VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    message_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    admin_response TEXT,
    admin_response_date TIMESTAMP
);

-- Cocktails table
-- api_cocktail_id stores the stable idDrink value from TheCocktailDB so that
-- shared API rows can be deduplicated without relying on the drink name.
CREATE TABLE cocktails (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    instructions TEXT,
    "strDrinkThumb" TEXT,
    image_url TEXT,
    is_api_cocktail BOOLEAN NOT NULL DEFAULT FALSE,
    api_cocktail_id VARCHAR,
    owner_id INTEGER REFERENCES "user"(id)
);

CREATE INDEX ix_cocktails_api_cocktail_id ON cocktails (api_cocktail_id);

-- User appeals (ban appeal workflow)
CREATE TABLE user_appeal (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    appeal_text TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    admin_response TEXT,
    admin_response_date TIMESTAMP
);

-- Favorite ingredients (user → ingredient many-to-many)
CREATE TABLE user_favorite_ingredients (
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    ingredient_id INTEGER NOT NULL REFERENCES ingredient(id),
    PRIMARY KEY (user_id, ingredient_id)
);

-- Cocktail ingredients (cocktail → ingredient many-to-many with measure)
CREATE TABLE cocktails_ingredients (
    id SERIAL PRIMARY KEY,
    cocktail_id INTEGER REFERENCES cocktails(id),
    ingredient_id INTEGER REFERENCES ingredient(id),
    quantity TEXT NOT NULL
);

-- Cocktail ownership / saved collection (user → cocktail many-to-many)
CREATE TABLE cocktails_users (
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    cocktail_id INTEGER NOT NULL REFERENCES cocktails(id),
    PRIMARY KEY (user_id, cocktail_id)
);

-- Admin audit log (immutable record of moderation actions)
CREATE TABLE admin_audit_log (
    id SERIAL PRIMARY KEY,
    admin_id INTEGER NOT NULL REFERENCES "user"(id),
    action VARCHAR(100) NOT NULL,
    target_user_id INTEGER REFERENCES "user"(id),
    details TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
