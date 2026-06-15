from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)
app.config.from_object("config.Config")

db = SQLAlchemy(app)

PRIORITY_CHOICES = ["low", "medium", "high"]


def clean_priority(value):
    if value in PRIORITY_CHOICES:
        return value

    return "medium"


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    priority = db.Column(db.String(20), default="medium")
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Task {self.id}: {self.title}>"

def task_to_dict(task):
    return {
        "id": task.id,
        "title": task.title,
        "completed": task.completed,
        "priority": task.priority,
        "date_created": task.date_created.isoformat(),
    }

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        priority = clean_priority(request.form.get("priority", "medium"))

        if not title:
            flash("Task title cannot be empty.", "error")
            return redirect(url_for("index"))

        new_task = Task(title=title, priority=priority)

        db.session.add(new_task)
        db.session.commit()

        flash("Task added successfully.", "success")
        return redirect(url_for("index"))

    search = request.args.get("search", "").strip()

    if request.args:
        status_filter = request.args.get("status", "all")
        priority_filter = request.args.get("priority", "all")

        session["status_filter"] = status_filter
        session["priority_filter"] = priority_filter
    else:
        status_filter = session.get("status_filter", "all")
        priority_filter = session.get("priority_filter", "all")

    query = Task.query

    if search:
        query = query.filter(Task.title.ilike(f"%{search}%"))

    if status_filter == "active":
        query = query.filter_by(completed=False)
    elif status_filter == "completed":
        query = query.filter_by(completed=True)

    if priority_filter in PRIORITY_CHOICES:
        query = query.filter_by(priority=priority_filter)

    tasks = query.order_by(Task.date_created.desc()).all()

    return render_template(
        "index.html",
        tasks=tasks,
        search=search,
        status_filter=status_filter,
        priority_filter=priority_filter,
        priority_choices=PRIORITY_CHOICES,
    )


@app.route("/filters/clear")
def clear_filters():
    session.pop("status_filter", None)
    session.pop("priority_filter", None)

    flash("Saved filters cleared.", "success")
    return redirect(url_for("index"))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/health")
def health():
    return "OK"


@app.route("/task/<int:task_id>")
def task_detail(task_id):
    task = Task.query.get_or_404(task_id)
    return render_template("task_detail.html", task=task)


@app.route("/task/<int:task_id>/edit", methods=["GET", "POST"])
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        completed = request.form.get("completed") == "on"
        priority = clean_priority(request.form.get("priority", "medium"))

        if not title:
            flash("Task title cannot be empty.", "error")
            return redirect(url_for("edit_task", task_id=task.id))

        task.title = title
        task.completed = completed
        task.priority = priority

        db.session.commit()

        flash("Task updated successfully.", "success")
        return redirect(url_for("task_detail", task_id=task.id))

    return render_template(
        "edit_task.html",
        task=task,
        priority_choices=PRIORITY_CHOICES,
    )


@app.route("/task/<int:task_id>/toggle", methods=["POST"])
def toggle_task(task_id):
    task = Task.query.get_or_404(task_id)

    task.completed = not task.completed
    db.session.commit()

    if task.completed:
        flash("Task marked as completed.", "success")
    else:
        flash("Task marked as active.", "success")

    return redirect(request.referrer or url_for("index"))


@app.route("/task/<int:task_id>/delete", methods=["POST"])
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)

    db.session.delete(task)
    db.session.commit()

    flash("Task deleted successfully.", "success")
    return redirect(url_for("index"))

@app.route("/api/tasks")
def api_tasks():
    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "all")
    priority_filter = request.args.get("priority", "all")

    query = Task.query

    if search:
        query = query.filter(Task.title.ilike(f"%{search}%"))

    if status_filter == "active":
        query = query.filter_by(completed=False)
    elif status_filter == "completed":
        query = query.filter_by(completed=True)

    if priority_filter in PRIORITY_CHOICES:
        query = query.filter_by(priority=priority_filter)

    tasks = query.order_by(Task.date_created.desc()).all()

    return jsonify({
        "count": len(tasks),
        "tasks": [task_to_dict(task) for task in tasks],
    })

@app.route("/api/tasks/<int:task_id>")
def api_task_detail(task_id):
    task = Task.query.get_or_404(task_id)

    return jsonify({
        "task": task_to_dict(task),
    })

@app.route("/api/tasks", methods=["POST"])
def api_create_task():
    data = request.get_json(silent=True) or {}

    title = data.get("title", "").strip()
    priority = clean_priority(data.get("priority", "medium"))

    if not title:
        return jsonify({
            "error": "Task title is required."
        }), 400

    task = Task(title=title, priority=priority)

    db.session.add(task)
    db.session.commit()

    return jsonify({
        "message": "Task created successfully.",
        "task": task_to_dict(task),
    }), 201

@app.route("/api/tasks/<int:task_id>/toggle", methods=["PATCH"])
def api_toggle_task(task_id):
    task = Task.query.get_or_404(task_id)

    task.completed = not task.completed
    db.session.commit()

    return jsonify({
        "message": "Task status updated successfully.",
        "task": task_to_dict(task),
    })

@app.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def api_delete_task(task_id):
    task = Task.query.get_or_404(task_id)

    db.session.delete(task)
    db.session.commit()

    return jsonify({
        "message": "Task deleted successfully.",
        "deleted_task_id": task_id,
    })

@app.errorhandler(404)
def page_not_found(error):
    return render_template("errors/404.html"), 404

@app.errorhandler(500)
def internal_server_error(error):
    db.session.rollback()
    return render_template("errors/500.html"), 500
