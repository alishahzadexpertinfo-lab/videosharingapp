

import os
from datetime import datetime
from uuid import uuid4

from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from werkzeug.utils import secure_filename

from azure_cosmos_client import (
    get_cosmos_client,
    get_container_videos,
    get_container_users,
    get_container_comments,
)
from azure_storage_client import get_blob_service_client, upload_video_file
from utils import hash_password, verify_password, login_required

COSMOS_DB_NAME = os.getenv("COSMOS_DB_NAME", "videosharingapp")
COSMOS_CONTAINER_VIDEOS = os.getenv("COSMOS_CONTAINER_VIDEOS", "videos")
COSMOS_CONTAINER_USERS = os.getenv("COSMOS_CONTAINER_USERS", "users")
COSMOS_CONTAINER_COMMENTS = os.getenv("COSMOS_CONTAINER_COMMENTS", "comments")

AZURE_STORAGE_CONTAINER = os.getenv("AZURE_STORAGE_CONTAINER", "videos")

ALLOWED_EXTENSIONS = {"mp4", "mov", "avi", "mkv"}

def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")

    # Initialize Azure clients once per app
    app.cosmos_client = get_cosmos_client()
    app.videos_container = get_container_videos(app.cosmos_client, COSMOS_DB_NAME, COSMOS_CONTAINER_VIDEOS)
    app.users_container = get_container_users(app.cosmos_client, COSMOS_DB_NAME, COSMOS_CONTAINER_USERS)
    app.comments_container = get_container_comments(app.cosmos_client, COSMOS_DB_NAME, COSMOS_CONTAINER_COMMENTS)

    app.blob_service_client = get_blob_service_client()
    return app


app = create_app()


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    # List videos ordered by created_at desc
    query = "SELECT * FROM c ORDER BY c.created_at DESC"
    videos = list(app.videos_container.query_items(query=query, enable_cross_partition_query=True))
    return render_template("index.html", videos=videos, current_user=session.get("user"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not username or not email or not password:
            flash("All fields are required.", "error")
            return redirect(url_for("register"))

        # Check if user exists
        query = "SELECT * FROM c WHERE c.email = @email"
        params = [{"name": "@email", "value": email}]
        existing = list(app.users_container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
        if existing:
            flash("A user with that email already exists.", "error")
            return redirect(url_for("register"))

        user_id = str(uuid4())
        user_doc = {
            "id": user_id,
            "username": username,
            "email": email,
            "password_hash": hash_password(password),
            "created_at": datetime.utcnow().isoformat(),
        }
        app.users_container.create_item(body=user_doc)
        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Email and password are required.", "error")
            return redirect(url_for("login"))

        query = "SELECT * FROM c WHERE c.email = @email"
        params = [{"name": "@email", "value": email}]
        users = list(app.users_container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
        if not users:
            flash("Invalid credentials.", "error")
            return redirect(url_for("login"))

        user = users[0]
        if not verify_password(password, user.get("password_hash", "")):
            flash("Invalid credentials.", "error")
            return redirect(url_for("login"))

        session["user"] = {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
        }
        flash(f"Welcome back, {user['username']}!", "success")
        return redirect(url_for("index"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


@app.route("/video/new", methods=["GET", "POST"])
@login_required
def new_video():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        file = request.files.get("video_file")

        if not title or not file:
            flash("Title and video file are required.", "error")
            return redirect(url_for("new_video"))

        if not allowed_file(file.filename):
            flash("Unsupported file type.", "error")
            return redirect(url_for("new_video"))

        filename = secure_filename(file.filename)
        unique_name = f"{uuid4()}_{filename}"

        try:
            video_url = upload_video_file(
                blob_service_client=app.blob_service_client,
                container_name=AZURE_STORAGE_CONTAINER,
                file_stream=file,
                blob_name=unique_name,
                content_type=file.mimetype or "video/mp4",
            )
        except Exception as e:
            print(f"Error uploading video: {e}")
            flash("Failed to upload video. Please try again.", "error")
            return redirect(url_for("new_video"))

        video_id = str(uuid4())
        now = datetime.utcnow().isoformat()
        user = session.get("user")

        video_doc = {
            "id": video_id,
            "title": title,
            "description": description,
            "video_url": video_url,
            "user_id": user["id"],
            "username": user["username"],
            "created_at": now,
            "updated_at": now,
        }
        app.videos_container.create_item(body=video_doc)
        flash("Video uploaded!", "success")
        return redirect(url_for("index"))

    return render_template("new_video.html", current_user=session.get("user"))


@app.route("/video/<video_id>")
def video_detail(video_id):
    try:
        video = app.videos_container.read_item(item=video_id, partition_key=video_id)
    except Exception:
        # Fallback if using a different partition key (e.g. user_id) or not found
        query = "SELECT * FROM c WHERE c.id = @id"
        params = [{"name": "@id", "value": video_id}]
        items = list(app.videos_container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
        if not items:
            flash("Video not found.", "error")
            return redirect(url_for("index"))
        video = items[0]

    query_comments = "SELECT * FROM c WHERE c.video_id = @video_id ORDER BY c.created_at ASC"
    params = [{"name": "@video_id", "value": video_id}]
    comments = list(app.comments_container.query_items(query=query_comments, parameters=params, enable_cross_partition_query=True))

    return render_template(
        "video_detail.html",
        video=video,
        comments=comments,
        current_user=session.get("user"),
    )


@app.route("/video/<video_id>/edit", methods=["GET", "POST"])
@login_required
def edit_video(video_id):
    query = "SELECT * FROM c WHERE c.id = @id"
    params = [{"name": "@id", "value": video_id}]
    items = list(app.videos_container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
    if not items:
        flash("Video not found.", "error")
        return redirect(url_for("index"))

    video = items[0]
    user = session.get("user")
    if video["user_id"] != user["id"]:
        flash("You are not allowed to edit this video.", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()

        if not title:
            flash("Title is required.", "error")
            return redirect(url_for("edit_video", video_id=video_id))

        video["title"] = title
        video["description"] = description
        video["updated_at"] = datetime.utcnow().isoformat()
        app.videos_container.replace_item(item=video, body=video)
        flash("Video updated.", "success")
        return redirect(url_for("video_detail", video_id=video_id))

    return render_template("edit_video.html", video=video, current_user=user)


@app.route("/video/<video_id>/delete", methods=["POST"])
@login_required
def delete_video(video_id):
    query = "SELECT * FROM c WHERE c.id = @id"
    params = [{"name": "@id", "value": video_id}]
    items = list(app.videos_container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
    if not items:
        flash("Video not found.", "error")
        return redirect(url_for("index"))

    video = items[0]
    user = session.get("user")
    if video["user_id"] != user["id"]:
        flash("You are not allowed to delete this video.", "error")
        return redirect(url_for("index"))

    app.videos_container.delete_item(item=video["id"], partition_key=video["id"])
    flash("Video deleted.", "info")
    return redirect(url_for("index"))


@app.route("/video/<video_id>/comments", methods=["POST"])
@login_required
def add_comment(video_id):
    text = request.form.get("text", "").strip()
    if not text:
        flash("Comment cannot be empty.", "error")
        return redirect(url_for("video_detail", video_id=video_id))

    user = session.get("user")
    comment_id = str(uuid4())
    now = datetime.utcnow().isoformat()
    comment_doc = {
        "id": comment_id,
        "video_id": video_id,
        "user_id": user["id"],
        "username": user["username"],
        "text": text,
        "created_at": now,
    }
    app.comments_container.create_item(body=comment_doc)
    flash("Comment added.", "success")
    return redirect(url_for("video_detail", video_id=video_id))


@app.route("/comment/<comment_id>/delete", methods=["POST"])
@login_required
def delete_comment(comment_id):
    # Load comment
    query = "SELECT * FROM c WHERE c.id = @id"
    params = [{"name": "@id", "value": comment_id}]
    items = list(app.comments_container.query_items(query=query, parameters=params, enable_cross_partition_query=True))
    if not items:
        flash("Comment not found.", "error")
        return redirect(url_for("index"))

    comment = items[0]
    user = session.get("user")
    if comment["user_id"] != user["id"]:
        flash("You are not allowed to delete this comment.", "error")
        return redirect(url_for("video_detail", video_id=comment["video_id"]))

    app.comments_container.delete_item(item=comment["id"], partition_key=comment["id"])
    flash("Comment deleted.", "info")
    return redirect(url_for("video_detail", video_id=comment["video_id"]))


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
