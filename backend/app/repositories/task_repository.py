"""
Repository pattern: isolates SQLAlchemy queries from business logic (services).
"""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.workflow import Task, TaskStatus


class TaskRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, task_id: uuid.UUID) -> Task | None:
        return self.db.get(Task, task_id)

    def list_tasks(
        self,
        *,
        assigned_to_id: uuid.UUID | None = None,
        status: TaskStatus | None = None,
        client_id: uuid.UUID | None = None,
        firm_id: uuid.UUID | None = None,
    ) -> list[Task]:
        stmt = select(Task)
        if firm_id is not None:
            # Firm-scoping (staff, non-super-admin): Task.firm_id is a direct
            # column (denormalized, see models/workflow.py), so this is a
            # plain filter, not a join, unlike documents' Client join.
            stmt = stmt.where(Task.firm_id == firm_id)
        if assigned_to_id is not None:
            stmt = stmt.where(Task.assigned_to_id == assigned_to_id)
        if status is not None:
            stmt = stmt.where(Task.status == status)
        if client_id is not None:
            stmt = stmt.where(Task.client_id == client_id)
        stmt = stmt.order_by(Task.created_at.desc())
        return list(self.db.scalars(stmt).all())

    def create(self, task: Task) -> Task:
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def update(self, task: Task) -> Task:
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def delete(self, task: Task) -> None:
        self.db.delete(task)
        self.db.commit()
