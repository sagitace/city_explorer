from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
    Flask,
    current_app,
)
from wtforms import Form, StringField, PasswordField, validators, ValidationError
from wtforms.validators import DataRequired
from sqlalchemy.exc import IntegrityError
from .models import *
from app import mail
import json
import os
from sqlalchemy import select, desc
import asyncio
import aiohttp
from flask_mail import Message


bp = Blueprint("schedule", __name__, url_prefix="/schedule")


@bp.route("/", methods=("GET", "POST"))
def index():
    from app.auth import login_required

    @login_required
    async def inner():
        schedules = db.session.execute(
            db.select(Plans).where(Plans.user_id == g.user.id).order_by(Plans.date)
        ).scalars()
        # based on user id
        # schedules = db.session.execute(
        #     db.select(Plans).where(Plans.user_id == g.user.id).order_by(Plans.date)
        # )
        upcoming = []
        visited = []
        missed = []
        cancelled = []
        todaydate = datetime.now().strftime("%Y-%m-%d")

        for schedule in schedules:

            if (
                schedule.date < datetime.now().strftime("%Y-%m-%d")
                and schedule.status == "upcoming"
            ):
                # update status 'missed'
                plan = Plans.query.get(schedule.id)
                # update status
                plan.status = "missed"
                # update db
                db.session.commit()

            # Format date into day and month
            schedule.day = datetime.strptime(schedule.date, "%Y-%m-%d").strftime("%d")
            schedule.month = datetime.strptime(schedule.date, "%Y-%m-%d").strftime("%b")

            if schedule.status == "upcoming":
                upcoming.append(schedule)
            elif schedule.status == "visited":
                visited.append(schedule)
            elif schedule.status == "missed":
                missed.append(schedule)
            elif schedule.status == "cancelled":
                cancelled.append(schedule)

        # sort visited, missed, and cancelled
        visited = sorted(visited, key=lambda x: x.date)
        missed = sorted(missed, key=lambda x: x.date)
        cancelled = sorted(cancelled, key=lambda x: x.date)

        # Query for schedules
        schedules_query = (
            select(Plans)
            .where(Plans.user_id == g.user.id, Plans.status == "upcoming")
            .order_by(Plans.date.asc())
        )
        schedules = db.session.execute(schedules_query).all()

        count_schedule = len(schedules)

        return render_template(
            "user/schedule.html",
            upcoming=upcoming,
            visited=visited,
            missed=missed,
            todaydate=todaydate,
            cancelled=cancelled,
            count_schedule=count_schedule,
        )

    return asyncio.run(inner())


@bp.route("/add_plans", methods=("GET", "POST"))
def add_to_plans():
    from app.auth import login_required

    @login_required
    async def inner():
        if request.method == "POST":
            schedule = Plans(
                user_id=g.user.id,
                fsq_id=request.form["fsq_id"],
                place_name=request.form["place_name"],
                category=request.form["category"],
                address=request.form["address"],
                region=request.form["region"],
                date=request.form["visit-date"],
                notes=request.form["notes"],
            )
            db.session.add(schedule)
            db.session.commit()

            # format date
            date = datetime.strptime(schedule.date, "%Y-%m-%d").strftime("%B %d, %Y")

            # send mail
            msg = Message(
                subject="Your Visit Has Been Scheduled - City Explorer",
                recipients=[g.user.email],
            )
            link = url_for("schedule.index", _external=True)
            msg.body = f"Hi {g.user.firstname},\n\nYour visit at {schedule.place_name} has been successfully scheduled!\n\nVisit Date: {date}\nAddress: {schedule.address}\nNotes: {schedule.notes}\nView all your schedules here: {link}\n\nWe look forward to seeing you there! Thank you for choosing City Explorer, and we hope you have an amazing experience discovering new places!\n\nBest regards,\nCity Explorer Team"

            mail.send(msg)

            return redirect(request.referrer)

    return asyncio.run(inner())


@bp.route("/mark/visited/<int:id>")
def mark_visited(id):
    from app.auth import login_required

    @login_required
    async def inner():

        try:
            # update status into visited
            plan = Plans.query.get(id)
            if plan:
                plan.status = "visited"
                db.session.commit()

                # check if the plan is already visited in the visited table
                visited = (
                    db.session.query(Visited)
                    .filter_by(user_id=g.user.id, fsq_id=plan.fsq_id)
                    .all()
                )
                if not visited:
                    try:
                        new_visited = Visited(
                            user_id=g.user.id,
                            fsq_id=plan.fsq_id,
                        )
                        db.session.add(new_visited)
                        db.session.commit()
                    except IntegrityError:
                        db.session.rollback()
                        flash("Place already in visited")

                flash(
                    f"Hope you like {plan.place_name}! Explore more places!", "success"
                )
            else:
                flash("Schedule not found.", "danger")

        except IntegrityError:
            db.session.rollback()
            flash("An error occurred while updating the schedule.", "danger")
        except Exception as e:
            flash(f"An error occured: {str(e)}", "danger")

        return redirect(request.referrer)

    return asyncio.run(inner())


@bp.route("/mark/cancel/<int:id>")
def mark_cancel(id):
    from app.auth import login_required

    @login_required
    async def inner():
        try:
            # update status into visited
            plan = Plans.query.get(id)
            if plan:
                plan.status = "cancelled"
                db.session.commit()
                flash(f"Schedule at {plan.place_name} has been cancelled!", "success")
            else:
                flash("Schedule not found.", "danger")

        except IntegrityError:
            db.session.rollback()
            flash("An error occurred while updating the schedule.", "danger")
        except Exception as e:
            flash(f"An error occured: {str(e)}", "danger")

        return redirect(request.referrer)

    return asyncio.run(inner())


@bp.route("/update/schedule/<int:id>", methods=("POST", "GET"))
def update_schedule(id):
    from app.auth import login_required

    @login_required
    async def inner():

        if request.method == "POST":
            date = request.form.get("visit-date")
            notes = request.form.get("notes")

            try:
                plan = Plans.query.get(id)
                if plan:
                    plan.date = date
                    plan.notes = notes
                    db.session.commit()
                    flash("Schedule updated successfully!", "success")
                else:
                    flash("Schedule not found.", "danger")
            except IntegrityError:
                db.session.rollback()
                flash("An error occurred while updating the character.", "danger")
            except Exception as e:
                flash(f"An error occured: {str(e)}", "danger")

            return redirect(request.referrer)

        return redirect(request.referrer)

    return asyncio.run(inner())
