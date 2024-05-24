-- create_test_db.sql

-- Drop the database if it already exists
DROP DATABASE IF EXISTS test_name_your_poison;

-- Create the test database
CREATE DATABASE test_name_your_poison;

-- Connect to the test database
\c test_name_your_poison;

-- Create tables and initial data (example schema based on your models)

-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    preference VARCHAR DEFAULT 'alcoholic'
);

-- Ingredients table
CREATE TABLE ingredients (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

-- Cocktails table
CREATE TABLE cocktails (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    instructions TEXT,
    strDrinkThumb TEXT,
    image_url TEXT
);

-- Cocktails_Ingredients table
CREATE TABLE cocktails_ingredients (
    id SERIAL PRIMARY KEY,
    cocktail_id INTEGER REFERENCES cocktails(id),
    ingredient_id INTEGER REFERENCES ingredients(id),
    quantity TEXT NOT NULL
);

-- Cocktails_Users table
CREATE TABLE cocktails_users (
    user_id INTEGER REFERENCES users(id),
    cocktail_id INTEGER REFERENCES cocktails(id),
    PRIMARY KEY (user_id, cocktail_id)
);

-- UserFavoriteIngredients table
CREATE TABLE user_favorite_ingredients (
    user_id INTEGER REFERENCES users(id),
    ingredient_id INTEGER REFERENCES ingredients(id),
    PRIMARY KEY (user_id, ingredient_id)
);
