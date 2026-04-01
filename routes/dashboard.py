from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    jsonify,
    Response,
)
from database import db
from models import Employee, Leave, LeaveType
from flask_security import auth_required, current_user

router = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@router.route("/search-employees")
@auth_required()
def search_employees():
    query = request.args.get("q", "").strip()
    if len(query) < 1:
        return jsonify([])

    is_admin = current_user.has_role("admin")
    base_query = db.select(Employee).where(
        (Employee.name.ilike(f"%{query}%")) | (Employee.id.ilike(f"%{query}%"))
    )

    # Admins can see deleted employees too
    if not is_admin:
        base_query = base_query.where(Employee.is_deleted == False)  # noqa: E712

    employees = (
        db.session.execute(base_query.limit(10))
        .scalars()
        .all()
    )

    return jsonify(
        [
            {
                "id": e.id,
                "name": e.name,
                "casual_leaves": e.casual_leaves,
                "gazzetted_leaves": e.gazzetted_leaves,
                "compensatory_leaves": e.compensatory_leaves,
                "without_pay_leaves": e.without_pay_leaves,
                "half_casual_leaves": e.half_casual_leaves,
                "is_deleted": e.is_deleted,
            }
            for e in employees
        ]
    )


@router.route("/", methods=["GET", "POST"])
@auth_required()
def home():
    is_json = request.headers.get("Accept") == "application/json"
    is_admin = current_user.has_role("admin")

    if request.method == "POST":
        action = request.form.get("action")

        if action == "add_employee":
            # Admin-only action
            if not is_admin:
                if is_json:
                    return (
                        jsonify(
                            {
                                "status": "error",
                                "message": "Permission denied. Only admins can add employees.",
                            }
                        ),
                        403,
                    )
                return redirect(url_for("dashboard.home"))

            employee_id = request.form.get("employee_id")
            employee_name = request.form.get("employee_name")
            casual_leaves = request.form.get("casual_leaves", 0)
            gazzetted_leaves = request.form.get("gazzetted_leaves", 0)

            if employee_id and employee_name:
                try:
                    new_employee = Employee(
                        id=employee_id,
                        name=employee_name,
                        casual_leaves=int(casual_leaves),
                        gazzetted_leaves=int(gazzetted_leaves),
                    )
                    db.session.add(new_employee)
                    db.session.commit()
                    if is_json:
                        return jsonify(
                            {
                                "status": "success",
                                "employee": {
                                    "id": employee_id,
                                    "name": employee_name,
                                    "casual_leaves": 0,
                                    "gazzetted_leaves": 0,
                                    "compensatory_leaves": 0,
                                    "without_pay_leaves": 0,
                                    "half_casual_leaves": 0,
                                },
                            }
                        )
                except Exception as e:
                    db.session.rollback()
                    if is_json:
                        error_msg = str(e)
                        if "UNIQUE constraint failed: employee.id" in error_msg:
                            user_msg = "Cannot add employee: An employee with this ID already exists."
                        else:
                            user_msg = "An unexpected database error occurred while creating the employee."
                        return jsonify({"status": "error", "message": user_msg}), 400

            if is_json:
                return jsonify({"status": "error", "message": "Missing fields"}), 400
            return redirect(url_for("dashboard.home"))

        employee_search = request.form.get("employee_search")
        leave_type_val = request.form.get("leave_type")

        if employee_search and leave_type_val:
            employee = db.session.execute(
                db.select(Employee).where(
                    (Employee.id == employee_search)
                    & (Employee.is_deleted == False)  # noqa: E712
                )
            ).scalar()

            if employee:
                try:
                    leave_type = LeaveType(leave_type_val)
                    leave = Leave(employee_id=employee.id, leave_type=leave_type)
                    db.session.add(leave)
                    db.session.commit()
                    if is_json:
                        return jsonify(
                            {
                                "status": "success",
                                "leave": {
                                    "id": leave.id,
                                    "employee_id": employee.id,
                                    "employee_name": employee.name,
                                    "leave_type": leave_type.value,
                                },
                            }
                        )
                except ValueError:
                    if is_json:
                        return jsonify(
                            {"status": "error", "message": "Invalid leave type."}
                        ), 400
                except Exception as e:
                    db.session.rollback()
                    if is_json:
                        error_msg = str(e)
                        if "Casual leave limit exceeded" in error_msg:
                            user_msg = "Limit Reached: This employee has already exhausted their 8 Casual Leaves."
                        elif "Gazzetted leave limit exceeded" in error_msg:
                            user_msg = "Limit Reached: This employee has already exhausted their 4 Gazzetted Leaves."
                        else:
                            user_msg = "An unexpected error occurred while adding the leave record."
                        return jsonify({"status": "error", "message": user_msg}), 400

            if is_json:
                return jsonify(
                    {"status": "error", "message": "Employee not found"}
                ), 404

    import datetime
    import calendar

    now = datetime.datetime.utcnow()
    start_date = datetime.datetime(now.year, now.month, 1)
    _, last_day = calendar.monthrange(now.year, now.month)
    end_date = datetime.datetime(now.year, now.month, last_day, 23, 59, 59)

    recent_leaves = (
        db.session.execute(
            db.select(Leave)
            .join(Employee)
            .where(Employee.is_deleted == False)  # noqa: E712
            .where(Leave.created_at >= start_date)
            .where(Leave.created_at <= end_date)
            .order_by(Leave.id.desc())
            .limit(10)
        )
        .scalars()
        .all()
    )
    leave_types = [(lt.value, lt.name.replace("_", " ").title()) for lt in LeaveType]
    employees = (
        db.session.execute(
            db.select(Employee)
            .where(Employee.is_deleted == False)  # noqa: E712
            .order_by(Employee.name)
        )
        .scalars()
        .all()
    )

    return render_template(
        "dashboard.html",
        leave_types=leave_types,
        recent_leaves=recent_leaves,
        employees=employees,
        report_start_date=start_date.strftime("%Y-%m-%d"),
        report_end_date=end_date.strftime("%Y-%m-%d"),
        is_admin=is_admin,
    )


@router.route("/employee/<employee_id>/delete", methods=["POST"])
@auth_required()
def delete_employee(employee_id):
    if not current_user.has_role("admin"):
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Permission denied. Only admins can delete employees.",
                }
            ),
            403,
        )

    employee = db.session.execute(
        db.select(Employee).where(
            (Employee.id == employee_id)
            & (Employee.is_deleted == False)  # noqa: E712
        )
    ).scalar()

    if not employee:
        return jsonify({"status": "error", "message": "Employee not found"}), 404

    employee.is_deleted = True
    db.session.commit()

    return jsonify(
        {"status": "success", "message": f"Employee {employee.name} has been removed."}
    )


@router.route("/employee/<employee_id>/edit", methods=["POST"])
@auth_required()
def edit_employee(employee_id):
    if not current_user.has_role("admin"):
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Permission denied. Only admins can edit employees.",
                }
            ),
            403,
        )

    employee = db.session.execute(
        db.select(Employee).where(Employee.id == employee_id)
    ).scalar()

    if not employee:
        return jsonify({"status": "error", "message": "Employee not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No data provided"}), 400

    if "name" in data and data["name"].strip():
        employee.name = data["name"].strip()

    db.session.commit()

    return jsonify(
        {
            "status": "success",
            "message": f"Employee {employee.name} updated.",
            "employee": {
                "id": employee.id,
                "name": employee.name,
                "casual_leaves": employee.casual_leaves,
                "gazzetted_leaves": employee.gazzetted_leaves,
                "compensatory_leaves": employee.compensatory_leaves,
                "without_pay_leaves": employee.without_pay_leaves,
                "half_casual_leaves": employee.half_casual_leaves,
                "is_deleted": employee.is_deleted,
            },
        }
    )


@router.route("/employee/<employee_id>/reactivate", methods=["POST"])
@auth_required()
def reactivate_employee(employee_id):
    if not current_user.has_role("admin"):
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Permission denied. Only admins can reactivate employees.",
                }
            ),
            403,
        )

    employee = db.session.execute(
        db.select(Employee).where(
            (Employee.id == employee_id)
            & (Employee.is_deleted == True)  # noqa: E712
        )
    ).scalar()

    if not employee:
        return (
            jsonify(
                {"status": "error", "message": "Employee not found or already active"}
            ),
            404,
        )

    employee.is_deleted = False
    db.session.commit()

    return jsonify(
        {
            "status": "success",
            "message": f"Employee {employee.name} has been reactivated.",
        }
    )


@router.route("/leave/<int:leave_id>/delete", methods=["POST"])
@auth_required()
def delete_leave(leave_id):
    if not current_user.has_role("admin"):
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Permission denied. Only admins can delete leave records.",
                }
            ),
            403,
        )

    leave = db.session.execute(
        db.select(Leave).where(Leave.id == leave_id)
    ).scalar()

    if not leave:
        return jsonify({"status": "error", "message": "Leave record not found"}), 404

    # Decrement the employee's leave counter
    employee = leave.employee
    leave_type = leave.leave_type
    if leave_type == LeaveType.CASUAL and employee.casual_leaves > 0:
        employee.casual_leaves -= 1
    elif leave_type == LeaveType.GAZZETTED and employee.gazzetted_leaves > 0:
        employee.gazzetted_leaves -= 1
    elif leave_type == LeaveType.COMPENSATORY and employee.compensatory_leaves > 0:
        employee.compensatory_leaves -= 1
    elif leave_type == LeaveType.WITHOUT_PAY and employee.without_pay_leaves > 0:
        employee.without_pay_leaves -= 1
    elif leave_type == LeaveType.HALF_CL and employee.half_casual_leaves > 0:
        employee.half_casual_leaves -= 1

    db.session.delete(leave)
    db.session.commit()

    return jsonify(
        {"status": "success", "message": "Leave record deleted."}
    )


@router.route("/report")
@auth_required()
def report():
    import datetime
    import calendar
    import csv
    import io

    now = datetime.datetime.utcnow()

    start_str = request.args.get("start_date", "")
    end_str = request.args.get("end_date", "")

    try:
        start_date = datetime.datetime.strptime(start_str, "%Y-%m-%d")
    except ValueError:
        start_date = datetime.datetime(now.year, now.month, 1)

    try:
        end_date = datetime.datetime.strptime(end_str, "%Y-%m-%d")
        end_date = end_date.replace(hour=23, minute=59, second=59)
    except ValueError:
        _, last_day = calendar.monthrange(now.year, now.month)
        end_date = datetime.datetime(now.year, now.month, last_day, 23, 59, 59)

    # Only include leaves from active (non-deleted) employees
    leaves = (
        db.session.execute(
            db.select(Leave)
            .join(Employee)
            .where(Employee.is_deleted == False)  # noqa: E712
            .where(Leave.created_at >= start_date)
            .where(Leave.created_at <= end_date)
            .order_by(Leave.created_at.asc())
        )
        .scalars()
        .all()
    )

    # Group leaves by employee, sorted by employee.id
    employee_leaves = {}
    for leave in leaves:
        emp_id = leave.employee_id
        if emp_id not in employee_leaves:
            employee_leaves[emp_id] = {
                "name": leave.employee.name,
                "leaves": [],
            }
        employee_leaves[emp_id]["leaves"].append(leave)

    # Sort by employee id
    sorted_employees = sorted(employee_leaves.items(), key=lambda x: x[0])

    # Find the max number of leaves any single employee has (for CSV columns)
    max_leaves = max((len(v["leaves"]) for _, v in sorted_employees), default=0)

    output = io.StringIO()
    writer = csv.writer(output)

    header = ["Employee ID", "Employee Name"] + [""] * max_leaves
    writer.writerow(header)

    for emp_id, data in sorted_employees:
        # Sort leaves by date
        sorted_leaves = sorted(data["leaves"], key=lambda lv: lv.created_at)
        leave_entries = [
            f"{lv.created_at.strftime('%B')} {lv.created_at.day} ({lv.leave_type.value})"
            for lv in sorted_leaves
        ]
        writer.writerow([emp_id, data["name"]] + leave_entries)

    csv_content = output.getvalue()
    output.close()

    filename = f"leave_report_{start_date.strftime('%Y-%m-%d')}_to_{end_date.strftime('%Y-%m-%d')}.csv"

    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
