from extensions import db
from models import Department, DepartmentResource


DEPARTMENTS = [
    {
        "code": "HR",
        "name": "Human Resources",
        "client_role": "hr-data-viewer",
        "resources": [
            "Employee Directory",
            "Leave Management",
            "HR Policies",
        ],
    },
    {
        "code": "FIN",
        "name": "Finance",
        "client_role": "finance-data-viewer",
        "resources": [
            "Financial Reports",
            "Budget Dashboard",
            "Expense Management",
        ],
    },
    {
        "code": "IT",
        "name": "Information Technology",
        "client_role": "it-data-viewer",
        "resources": [
            "IT Service Catalog",
            "Infrastructure Dashboard",
            "Asset Inventory",
        ],
    },
    {
        "code": "OPS",
        "name": "Operations",
        "client_role": "operations-data-viewer",
        "resources": [
            "Operations Dashboard",
            "Process Documentation",
            "Service Metrics",
        ],
    },
    {
        "code": "SEC",
        "name": "Security",
        "client_role": "security-data-viewer",
        "resources": [
            "Security Dashboard",
            "Incident Reports",
            "Security Policies",
        ],
    },
]

def seed_departments():
    for department_data in DEPARTMENTS:
        department = db.session.execute(
            db.select(Department).where(
                Department.code == department_data["code"]
            )
        ).scalar_one_or_none()

        if department is not None :
            continue

        department = Department(
            code = department_data["code"],
            name = department_data["name"],
            client_role = department_data["client_role"]
            
        )

        department.resources = [
            DepartmentResource(name = resource_name ) for resource_name in department_data["resources"]
        ]

        db.session.add(department)
    db.session.commit()
