"""Service layer for cocktail storage and image handling.

Extracted from app.py to keep route handlers thin and testable.
"""
import io
import os
import logging
import uuid
import warnings

from PIL import Image
from flask import current_app, url_for

from models import db, Cocktail, Cocktails_Users, Cocktails_Ingredients, Ingredient


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Cap total pixels to ~10 MP — well above any reasonable cocktail photo,
# well below a decompression-bomb payload.  Pillow raises
# DecompressionBombWarning (which we promote to an error inside
# save_uploaded_image) when this limit is exceeded.
Image.MAX_IMAGE_PIXELS = 10_000_000

# Issue #6: Use full magic-byte signatures for robust content-type validation.
# PNG: 8-byte signature.  JPEG: 3-byte FF D8 FF prefix.
_IMAGE_SIGNATURES = (
    b'\x89PNG\r\n\x1a\n',  # PNG — full 8-byte signature
    b'\xff\xd8\xff',        # JPEG — first three bytes
)


def _is_valid_image_content(file_stream) -> bool:
    """Return True if the stream starts with a recognised image signature."""
    # Read enough bytes to cover the longest signature (8 bytes for PNG).
    header = file_stream.read(8)
    file_stream.seek(0)
    return any(header.startswith(sig) for sig in _IMAGE_SIGNATURES)


def allowed_file(filename: str) -> bool:
    """Return True if the filename has an allowed image extension."""
    return (
        '.' in filename
        and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def save_uploaded_image(image_file) -> str | None:
    """Validate and persist an uploaded image file.

    Returns the stored filename (not the full path), or ``None`` when no file
    was provided.  Raises ``ValueError`` for invalid or disallowed files.

    Three-layer defence against malicious uploads:

    1. **Extension allow-list** — fast first gate that rejects obviously wrong
       file types before any further processing.
    2. **Magic-byte check** — inspects the first bytes of the stream to catch
       extension spoofing (e.g. a PHP shell renamed to ``evil.jpg``).
    3. **Pillow re-encode** — opens the file, forces a full pixel decode
       (``img.load()``), then writes a brand-new image to a clean buffer.
       This strips *all* metadata (EXIF, ICC profiles, comments, thumbnails)
       and destroys any polyglot payload (files that are simultaneously valid
       images and executable scripts).  Decompression-bomb files and corrupt
       /truncated data are also caught here before touching the filesystem.
    """
    if not image_file or not image_file.filename:
        return None

    # Gate 1: allow-list based on file extension.
    if not allowed_file(image_file.filename):
        raise ValueError(
            "File type not allowed. Please upload a PNG, JPG, or JPEG image."
        )

    # Gate 2: inspect actual file content to prevent extension spoofing.
    if not _is_valid_image_content(image_file.stream):
        raise ValueError(
            "Uploaded file does not appear to be a valid image."
        )

    # Gate 3: Re-encode through Pillow to neutralise any embedded payload.
    # ``warnings.catch_warnings`` promotes DecompressionBombWarning to an
    # exception so oversized images are rejected before Pillow allocates RAM.
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            img = Image.open(image_file.stream)
            img.load()  # force full pixel decode — catches corrupt data
    except Image.DecompressionBombWarning as exc:
        raise ValueError(
            "Image is too large to process safely."
        ) from exc
    except OSError as exc:
        # Covers PIL.UnidentifiedImageError (not a real image) and any
        # other I/O or decoding failure; UnidentifiedImageError derives
        # from OSError so one clause handles both.
        raise ValueError(
            "Uploaded file is not a valid or supported image."
        ) from exc

    # Re-encode to a clean buffer.  Preserve transparency with PNG; use JPEG
    # for everything else to keep file sizes reasonable.
    output_format = "PNG" if img.mode in ("RGBA", "P") else "JPEG"
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")

    clean_buffer = io.BytesIO()
    img.save(clean_buffer, format=output_format)
    clean_buffer.seek(0)

    # Build a collision-resistant filename from a UUID only.  The original
    # user-supplied name is intentionally discarded — it is never safe to
    # preserve attacker-controlled input as a filesystem path component.
    ext = "png" if output_format == "PNG" else "jpg"
    filename = f"{uuid.uuid4().hex}.{ext}"
    uploads_dir = os.path.join(
        current_app.root_path,
        current_app.config['UPLOADED_PHOTOS_DEST'],
    )
    os.makedirs(uploads_dir, exist_ok=True)
    with open(os.path.join(uploads_dir, filename), "wb") as f:
        f.write(clean_buffer.read())
    return filename


def get_cocktail_image_url(cocktail) -> str | None:
    """Return the resolved public URL for a cocktail image, or ``None``.

    ``image_url`` (user uploads) takes priority over ``strDrinkThumb``
    (API URLs or legacy user-edit filenames).
    """
    if cocktail.image_url:
        return url_for('cocktails.uploaded_file', filename=cocktail.image_url)
    if cocktail.strDrinkThumb:
        if cocktail.strDrinkThumb.startswith('http'):
            return cocktail.strDrinkThumb
        return url_for('cocktails.uploaded_file', filename=cocktail.strDrinkThumb)
    return None


def store_or_get_ingredient(name: str) -> Ingredient:
    """Return the ``Ingredient`` row for *name*, creating it if absent.

    The name is normalised (stripped and title-cased) before lookup so that
    case and whitespace variants ("vodka", " Vodka ", "VODKA") all resolve to
    the same canonical row.  The caller is responsible for committing the session.
    """
    # Canonicalise: remove leading/trailing whitespace, collapse internal
    # whitespace, then apply title-case so "dry gin" and "Dry Gin" are equal.
    canonical = " ".join(name.strip().split()).title()
    ingredient = Ingredient.query.filter_by(name=canonical).first()
    if not ingredient:
        ingredient = Ingredient(name=canonical)
        db.session.add(ingredient)
    return ingredient


def delete_uploaded_image(filename: str) -> None:
    """Delete a locally stored upload by filename; silently ignores missing files.

    Only plain filenames (no directory separators) are accepted to prevent
    path-traversal attacks.
    """
    if not filename:
        return
    # Reject filenames that contain path components (path-traversal guard).
    if filename != os.path.basename(filename):
        return
    try:
        upload_dir = os.path.join(
            current_app.root_path,
            current_app.config['UPLOADED_PHOTOS_DEST'],
        )
        path = os.path.join(upload_dir, filename)
        if os.path.isfile(path):
            os.remove(path)
    except Exception as exc:
        logging.warning("Could not delete uploaded image %r: %s", filename, exc)


def _find_existing_api_cocktail(external_id: str | None, name: str) -> Cocktail | None:
    """Return an existing shared API cocktail row, or ``None`` if absent.

    Prefers matching on the stable ``api_cocktail_id``; falls back to the
    drink name for rows created before that column was added, and back-fills
    the ID in that case.
    """
    if external_id:
        existing = Cocktail.query.filter_by(
            api_cocktail_id=external_id, is_api_cocktail=True
        ).first()
        if existing:
            return existing

    # Name-based fallback for legacy rows.
    existing = Cocktail.query.filter_by(name=name, is_api_cocktail=True).first()
    if existing and external_id and not existing.api_cocktail_id:
        existing.api_cocktail_id = external_id  # back-fill stable ID
    return existing


def process_and_store_new_cocktail(cocktail_api: dict, user_id: int) -> None:
    """Store an API cocktail and associate it with a user (single commit).

    Re-uses the shared API cocktail row when it already exists so that
    multiple users reference the same record instead of creating duplicates.
    Deduplication uses the stable ``idDrink`` field from TheCocktailDB as the
    primary key; the drink name is used only as a fallback for older rows that
    pre-date the ``api_cocktail_id`` column.
    Raises on DB error after rolling back.
    """
    try:
        external_id = str(cocktail_api.get('idDrink', '')) or None
        existing = _find_existing_api_cocktail(external_id, cocktail_api['strDrink'])

        if existing:
            new_cocktail = existing
        else:
            new_cocktail = Cocktail(
                name=cocktail_api['strDrink'],
                instructions=cocktail_api.get('strInstructions'),
                strDrinkThumb=cocktail_api.get('strDrinkThumb'),
                is_api_cocktail=True,
                api_cocktail_id=external_id,
            )
            db.session.add(new_cocktail)
            # Flush to obtain new_cocktail.id before building FK rows.
            db.session.flush()

            # The CocktailDB API returns ingredients as strIngredient1–15.
            for i in range(1, 16):
                name = cocktail_api.get(f'strIngredient{i}')
                measure = cocktail_api.get(f'strMeasure{i}')
                if name:
                    ingredient = store_or_get_ingredient(name)
                    # Flush so ingredient.id is available for the association row.
                    db.session.flush()
                    db.session.add(
                        Cocktails_Ingredients(
                            cocktail_id=new_cocktail.id,
                            ingredient_id=ingredient.id,
                            quantity=measure or '',
                        )
                    )

        # Link the cocktail to the user only if they don't already have it.
        # Also guard against the case where the user previously edited this
        # API cocktail (creating a personal copy) which swapped the
        # Cocktails_Users link away from the shared API record.  Without this
        # check the guard below would miss the personal copy and create a
        # duplicate entry in the user's profile.
        already_linked = Cocktails_Users.query.filter_by(
            user_id=user_id, cocktail_id=new_cocktail.id
        ).first()
        has_personal_copy = (
            Cocktail.query
            .join(Cocktails_Users, Cocktails_Users.cocktail_id == Cocktail.id)
            .filter(
                Cocktails_Users.user_id == user_id,
                Cocktail.is_api_cocktail == False,
                Cocktail.name == new_cocktail.name,
            )
            .first()
        ) if not already_linked else None

        newly_added = False
        if not already_linked and not has_personal_copy:
            db.session.add(
                Cocktails_Users(user_id=user_id, cocktail_id=new_cocktail.id)
            )
            newly_added = True

        # Single commit covers all rows prepared above.
        db.session.commit()
        return newly_added

    except Exception:
        db.session.rollback()
        raise
