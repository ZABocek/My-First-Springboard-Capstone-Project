CREATE TABLE "user"(
    "id" SERIAL NOT NULL,
    "username" TEXT NOT NULL,
    "password" TEXT NOT NULL,
    "email" TEXT NOT NULL
);
ALTER TABLE
    "user" ADD PRIMARY KEY("id");
ALTER TABLE
    "user" ADD CONSTRAINT "user_username_unique" UNIQUE("username");
ALTER TABLE
    "user" ADD CONSTRAINT "user_password_unique" UNIQUE("password");
CREATE TABLE "cocktails_users"(
    "user_id" SERIAL NOT NULL,
    "cocktail_id" SERIAL NOT NULL
);
ALTER TABLE
    "cocktails_users" ADD CONSTRAINT "cocktails_users_user_id_unique" UNIQUE("user_id");
ALTER TABLE
    "cocktails_users" ADD CONSTRAINT "cocktails_users_cocktail_id_unique" UNIQUE("cocktail_id");
CREATE TABLE "UserFavoriteIngredients"(
    "user_id" SERIAL NOT NULL,
    "ingredient_id" SERIAL NOT NULL
);
ALTER TABLE
    "UserFavoriteIngredients" ADD CONSTRAINT "userfavoriteingredients_user_id_unique" UNIQUE("user_id");
ALTER TABLE
    "UserFavoriteIngredients" ADD CONSTRAINT "userfavoriteingredients_ingredient_id_unique" UNIQUE("ingredient_id");
CREATE TABLE "cocktails_ingredients"(
    "id" SERIAL NOT NULL,
    "cocktail_id" SERIAL NOT NULL,
    "ingredient_id" SERIAL NOT NULL,
    "quantity" DOUBLE PRECISION NOT NULL
);
ALTER TABLE
    "cocktails_ingredients" ADD PRIMARY KEY("id");
ALTER TABLE
    "cocktails_ingredients" ADD CONSTRAINT "cocktails_ingredients_cocktail_id_unique" UNIQUE("cocktail_id");
ALTER TABLE
    "cocktails_ingredients" ADD CONSTRAINT "cocktails_ingredients_ingredient_id_unique" UNIQUE("ingredient_id");
CREATE TABLE "cocktails"(
    "id" SERIAL NOT NULL,
    "name" TEXT NOT NULL,
    "instructions" TEXT NOT NULL,
    "sweet" BOOLEAN NOT NULL
);
ALTER TABLE
    "cocktails" ADD PRIMARY KEY("id");
CREATE TABLE "ingredients"(
    "id" SERIAL NOT NULL,
    "name" TEXT NOT NULL,
    "is_alcohol" BOOLEAN NOT NULL
);
ALTER TABLE
    "ingredients" ADD PRIMARY KEY("id");
ALTER TABLE
    "UserFavoriteIngredients" ADD CONSTRAINT "userfavoriteingredients_user_id_foreign" FOREIGN KEY("user_id") REFERENCES "user"("id");
ALTER TABLE
    "cocktails_users" ADD CONSTRAINT "cocktails_users_user_id_foreign" FOREIGN KEY("user_id") REFERENCES "user"("id");
ALTER TABLE
    "cocktails_ingredients" ADD CONSTRAINT "cocktails_ingredients_cocktail_id_foreign" FOREIGN KEY("cocktail_id") REFERENCES "cocktails"("id");
ALTER TABLE
    "cocktails_users" ADD CONSTRAINT "cocktails_users_cocktail_id_foreign" FOREIGN KEY("cocktail_id") REFERENCES "cocktails"("id");
ALTER TABLE
    "cocktails" ADD CONSTRAINT "cocktails_id_foreign" FOREIGN KEY("id") REFERENCES "user"("id");
ALTER TABLE
    "UserFavoriteIngredients" ADD CONSTRAINT "userfavoriteingredients_ingredient_id_foreign" FOREIGN KEY("ingredient_id") REFERENCES "ingredients"("id");
ALTER TABLE
    "cocktails_ingredients" ADD CONSTRAINT "cocktails_ingredients_ingredient_id_foreign" FOREIGN KEY("ingredient_id") REFERENCES "ingredients"("id");