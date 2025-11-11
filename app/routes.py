import io
import json
import secrets
import uuid
import zipfile
from datetime import datetime
from typing import List
from pathlib import Path

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)

from .constants import GROUP_A_DOCUMENTS, GROUP_B_DOCUMENTS
from .database import close_db, get_db
from .storage import load_decrypted, save_encrypted


bp = Blueprint("main", __name__)


@bp.before_app_request
def ensure_session_security():
    session.permanent = False


@bp.teardown_app_request
def teardown_db(exception):
    close_db()


@bp.route("/")
def index():
    return render_template(
        "index.html",
        group_a=GROUP_A_DOCUMENTS,
        group_b=GROUP_B_DOCUMENTS,
    )


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name")
        email = request.form.get("email")
        if not email:
            flash("Email address is required to create an account.", "danger")
            return redirect(url_for("main.register"))

        user_id = uuid.uuid4().hex
        verification_code = secrets.token_hex(3).upper()

        db = get_db()
        db.execute(
            "INSERT INTO users (id, verification_code, full_name, email) VALUES (?, ?, ?, ?)",
            (user_id, verification_code, full_name, email),
        )
        db.commit()

        session["user_id"] = user_id
        flash("Director profile created. Save your User ID and verification code.", "success")
        return redirect(url_for("main.director_portal", user_id=user_id))

    return render_template("register.html")


@bp.route("/start", methods=["GET", "POST"])
def start_existing():
    if request.method == "POST":
        user_id = request.form.get("user_id", "").strip()
        if not user_id:
            flash("Enter your assigned user ID.", "danger")
            return redirect(url_for("main.start_existing"))

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            flash("User ID not found. Double-check with your ACSP.", "danger")
            return redirect(url_for("main.start_existing"))

        session["user_id"] = user_id
        return redirect(url_for("main.director_portal", user_id=user_id))

    return render_template("start.html")


def _get_user_or_404(user_id):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        abort(404)
    return user


def _validate_document_mix(total_docs: List[dict]) -> bool:
    group_a = sum(1 for doc in total_docs if doc["document_group"] == "A")
    group_b = sum(1 for doc in total_docs if doc["document_group"] == "B")
    if group_a >= 2:
        return True
    if group_a >= 1 and group_b >= 1:
        return True
    return False


@bp.route("/director/<user_id>", methods=["GET", "POST"])
def director_portal(user_id):
    user = _get_user_or_404(user_id)

    if session.get("user_id") != user_id:
        flash("Access restricted. Provide your user ID again.", "danger")
        return redirect(url_for("main.start_existing"))

    db = get_db()

    if request.method == "POST":
        full_name = request.form.get("full_name")
        former_names = request.form.get("former_names")
        date_of_birth = request.form.get("date_of_birth")
        home_address = request.form.get("home_address")
        address_history = request.form.get("address_history")
        email = request.form.get("email")

        if not all([full_name, date_of_birth, home_address, address_history, email]):
            flash("Complete all mandatory personal details before saving.", "danger")
            return redirect(url_for("main.director_portal", user_id=user_id))

        db.execute(
            "UPDATE users SET full_name=?, former_names=?, date_of_birth=?, home_address=?, address_history=?, email=? WHERE id=?",
            (
                full_name,
                former_names,
                date_of_birth,
                home_address,
                address_history,
                email,
                user_id,
            ),
        )

        pending_documents = []
        for idx in range(1, 4):
            file_field = f"document_file_{idx}"
            doc_file = request.files.get(file_field)
            if not doc_file or not doc_file.filename:
                continue

            doc_type = request.form.get(f"document_type_{idx}")
            doc_group = request.form.get(f"document_group_{idx}")
            if doc_group not in {"A", "B"}:
                flash("Select a valid document group for each upload.", "danger")
                return redirect(url_for("main.director_portal", user_id=user_id))
            if not doc_type:
                flash("Describe the document type (e.g. Passport, Utility bill).", "danger")
                return redirect(url_for("main.director_portal", user_id=user_id))

            pending_documents.append(
                {
                    "file": doc_file,
                    "document_type": doc_type,
                    "document_group": doc_group,
                    "original_filename": doc_file.filename,
                }
            )

        selfie_mode = request.form.get("selfie_mode")
        selfie_upload = request.files.get("selfie_file")
        selfie_capture_data = request.form.get("selfie_capture_data")

        if selfie_capture_data:
            header, _, b64data = selfie_capture_data.partition(",")
            if b64data:
                import base64

                data = base64.b64decode(b64data)
                from werkzeug.datastructures import FileStorage
                from io import BytesIO

                selfie_upload = FileStorage(
                    stream=BytesIO(data),
                    filename="selfie_capture.png",
                    content_type="image/png",
                )
        pending_selfie = None
        if selfie_upload and selfie_upload.filename:
            media_type = "video" if (selfie_mode == "video" or selfie_upload.mimetype.startswith("video")) else "photo"
            pending_selfie = {
                "file": selfie_upload,
                "media_type": media_type,
                "original_filename": selfie_upload.filename,
            }

        existing_docs = db.execute(
            "SELECT document_group FROM documents WHERE user_id = ?",
            (user_id,),
        ).fetchall()
        combined = [dict(row) for row in existing_docs]
        combined.extend({"document_group": doc["document_group"]} for doc in pending_documents)

        if combined and not _validate_document_mix(combined):
            flash(
                "Uploads must include either two Group A documents or one Group A and one Group B document.",
                "danger",
            )
            return redirect(url_for("main.director_portal", user_id=user_id))

        for pending in pending_documents:
            try:
                stored_filename, _ = save_encrypted(pending["file"], user_id, "document")
            except RuntimeError as exc:
                flash(str(exc), "danger")
                return redirect(url_for("main.director_portal", user_id=user_id))
            metadata = {
                "uploaded_by": email or user["email"],
                "uploaded_at": datetime.utcnow().isoformat(),
            }
            db.execute(
                "INSERT INTO documents (user_id, original_filename, stored_filename, document_type, document_group, metadata) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    user_id,
                    pending["original_filename"],
                    stored_filename,
                    pending["document_type"],
                    pending["document_group"],
                    json.dumps(metadata),
                ),
            )

        if pending_selfie:
            try:
                stored_filename, _ = save_encrypted(pending_selfie["file"], user_id, "selfie")
            except RuntimeError as exc:
                flash(str(exc), "danger")
                return redirect(url_for("main.director_portal", user_id=user_id))
            db.execute(
                "INSERT INTO media (user_id, original_filename, stored_filename, media_type) VALUES (?, ?, ?, ?)",
                (
                    user_id,
                    pending_selfie["original_filename"],
                    stored_filename,
                    pending_selfie["media_type"],
                ),
            )

        db.commit()
        flash("Information saved securely.", "success")
        return redirect(url_for("main.director_portal", user_id=user_id))

    documents = db.execute(
        "SELECT id, original_filename, document_type, document_group, uploaded_at FROM documents WHERE user_id = ? ORDER BY uploaded_at DESC",
        (user_id,),
    ).fetchall()
    media_entries = db.execute(
        "SELECT id, original_filename, media_type, uploaded_at FROM media WHERE user_id = ? ORDER BY uploaded_at DESC",
        (user_id,),
    ).fetchall()

    total_docs = [dict(row) for row in documents]
    doc_requirements_met = _validate_document_mix(total_docs) if total_docs else False

    return render_template(
        "director_portal.html",
        user=user,
        documents=documents,
        media_entries=media_entries,
        group_a=GROUP_A_DOCUMENTS,
        group_b=GROUP_B_DOCUMENTS,
        doc_requirements_met=doc_requirements_met,
    )


def _require_admin():
    if not session.get("is_admin"):
        flash("Admin login required.", "danger")
        return redirect(url_for("main.admin_login"))
    return None


@bp.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        password = request.form.get("password")
        if password == current_app.config["ADMIN_PASSWORD"]:
            session["is_admin"] = True
            return redirect(url_for("main.admin_dashboard"))
        flash("Incorrect password.", "danger")

    return render_template("admin_login.html")


@bp.route("/admin/dashboard")
def admin_dashboard():
    response = _require_admin()
    if response:
        return response

    db = get_db()
    users = db.execute(
        "SELECT id, full_name, email, verification_code, created_at FROM users ORDER BY created_at DESC"
    ).fetchall()

    submissions = []
    for user in users:
        doc_count = db.execute(
            "SELECT COUNT(*) as count FROM documents WHERE user_id = ?",
            (user["id"],),
        ).fetchone()["count"]
        media_count = db.execute(
            "SELECT COUNT(*) as count FROM media WHERE user_id = ?",
            (user["id"],),
        ).fetchone()["count"]
        submissions.append(
            {
                "user": user,
                "doc_count": doc_count,
                "media_count": media_count,
            }
        )

    return render_template("admin_dashboard.html", submissions=submissions)


@bp.route("/admin/download/<user_id>")
def admin_download(user_id):
    response = _require_admin()
    if response:
        return response

    user = _get_user_or_404(user_id)
    db = get_db()
    documents = db.execute(
        "SELECT original_filename, stored_filename FROM documents WHERE user_id = ?",
        (user_id,),
    ).fetchall()
    media_entries = db.execute(
        "SELECT original_filename, stored_filename FROM media WHERE user_id = ?",
        (user_id,),
    ).fetchall()

    if not documents and not media_entries:
        flash("No files uploaded yet.", "info")
        return redirect(url_for("main.admin_dashboard"))

    memory_file = io.BytesIO()
    uploads_root = current_app.config["UPLOAD_FOLDER"]
    with zipfile.ZipFile(memory_file, "w", zipfile.ZIP_DEFLATED) as zf:
        for row in documents:
            path = Path(uploads_root) / user_id / row["stored_filename"]
            data = load_decrypted(str(path))
            zf.writestr(f"{user_id}/documents/{row['original_filename']}", data)
        for row in media_entries:
            path = Path(uploads_root) / user_id / row["stored_filename"]
            data = load_decrypted(str(path))
            zf.writestr(f"{user_id}/media/{row['original_filename']}", data)

    memory_file.seek(0)
    filename = f"{user_id}_submission.zip"
    return send_file(
        memory_file,
        mimetype="application/zip",
        as_attachment=True,
        download_name=filename,
    )


@bp.route("/govuk-verify")
def govuk_verify():
    return redirect("https://www.gov.uk/verify-your-identity")
