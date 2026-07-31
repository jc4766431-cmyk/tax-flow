"""
Business logic for the Tasks/Kanban module. Staff-only across the board (this
is the accountant workflow board from §3e of HANDOFF.md, not a client-facing
feature) — kept separate from the API layer so it is independently
unit-testable, matching the repository/service/thin-endpoint pattern used by
auth_service.py and document_service.py.
"""
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.deps import assert_firm_scoped
from app.models.client import Client
from app.models.user import User, UserRole
from app.models.workflow import Task, TaskStatus
from app.repositories.task_repository import TaskRepository
from app.schemas.task import KanbanBoard, TaskCreate, TaskStatusUpdate, TaskUpdate

# Fixed column order the frontend Kanban board renders, per HANDOFF.md §2b:
# New Client → Waiting for Documents → Review → Approval → Filed → Completed
KANBAN_COLUMN_ORDER: list[TaskStatus] = [
    TaskStatus.NEW,
    TaskStatus.WAITING_FOR_DOCUMENTS,
    TaskStatus.REVIEW,
    TaskStatus.APPROVAL,
    TaskStatus.FILED,
    TaskStatus.COMPLETED,
]


class TaskService:
    def __init__(self, db: Session):
        self.db = db
        self.tasks = TaskRepository(db)

    def _get_or_404(self, task_id: uuid.UUID) -> Task:
        task = self.tasks.get_by_id(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return task

    # --- Access control helpers ---------------------------------------
    # Mirrors document_service.py's _assert_can_write/_assert_can_read: staff
    # (non-super-admin) are scoped to their own firm. Tasks are staff-only at
    # the router level already (require_staff), so there's no client-role
    # branch to handle here the way document_service.py has one.

    def _assert_can_access(self, current_user: User, task: Task) -> None:
        # A NULL firm_id means a pre-fix row from before this column existed
        # (see the migration note in models/workflow.py) — assert_firm_scoped
        # already treats "current_user.firm_id != target_firm_id" as a 403
        # for anyone but super_admin, and None != a real firm_id, so this
        # correctly locks pre-fix rows to super_admin only until backfilled.
        assert_firm_scoped(current_user, task.firm_id)

    def _resolve_firm_id(self, current_user: User, client_id: uuid.UUID | None) -> uuid.UUID:
        """Determines which firm a new task belongs to. Prefers the firm of
        the client the task is attached to (and, for non-super-admins,
        confirms that client is actually in their own firm — reusing
        assert_firm_scoped rather than a bespoke check) and falls back to the
        creating user's own firm_id for tasks with no client_id. A
        super_admin creating a client-less task has no firm to fall back to
        (they're platform-level, not attached to one), so that combination is
        rejected with a clear 400 rather than silently guessing."""
        if client_id is not None:
            client = self.db.get(Client, client_id)
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
            assert_firm_scoped(current_user, client.firm_id)
            return client.firm_id

        if current_user.firm_id is not None:
            return current_user.firm_id

        raise HTTPException(
            status_code=400,
            detail="Cannot determine which firm this task belongs to — "
            "provide a client_id, or create it as a firm-scoped user.",
        )

    def _assert_assignee_in_firm(self, firm_id: uuid.UUID, assigned_to_id: uuid.UUID | None) -> None:
        if assigned_to_id is None:
            return
        assignee = self.db.get(User, assigned_to_id)
        if not assignee:
            raise HTTPException(status_code=404, detail="Assignee not found")
        if assignee.role != UserRole.SUPER_ADMIN and assignee.firm_id != firm_id:
            raise HTTPException(
                status_code=400,
                detail="Cannot assign a task to a user outside this task's firm",
            )
        if assignee.role == UserRole.CLIENT:
            raise HTTPException(
                status_code=400,
                detail="Cannot assign a task to a client-role user",
            )

    def create_task(self, payload: TaskCreate, current_user: User) -> Task:
        firm_id = self._resolve_firm_id(current_user, payload.client_id)
        self._assert_assignee_in_firm(firm_id, payload.assigned_to_id)
        task = Task(**payload.model_dump(), firm_id=firm_id)
        return self.tasks.create(task)

    def get_task(self, task_id: uuid.UUID, current_user: User) -> Task:
        task = self._get_or_404(task_id)
        self._assert_can_access(current_user, task)
        return task

    def list_tasks(
        self,
        *,
        current_user: User,
        assigned_to_id: uuid.UUID | None,
        status: TaskStatus | None,
        client_id: uuid.UUID | None,
    ) -> list[Task]:
        firm_id = None if current_user.role == UserRole.SUPER_ADMIN else current_user.firm_id
        return self.tasks.list_tasks(
            assigned_to_id=assigned_to_id, status=status, client_id=client_id, firm_id=firm_id
        )

    def get_board(self, *, current_user: User, assigned_to_id: uuid.UUID | None) -> KanbanBoard:
        """Same query as list_tasks, pre-grouped into the six fixed columns so
        the frontend Kanban board (§3e) can render straight off the response
        without re-sorting client-side."""
        firm_id = None if current_user.role == UserRole.SUPER_ADMIN else current_user.firm_id
        tasks = self.tasks.list_tasks(assigned_to_id=assigned_to_id, firm_id=firm_id)
        columns: dict[TaskStatus, list[Task]] = {status: [] for status in KANBAN_COLUMN_ORDER}
        for task in tasks:
            columns[task.status].append(task)
        return KanbanBoard(columns=columns)

    def update_task(self, task_id: uuid.UUID, payload: TaskUpdate, current_user: User) -> Task:
        task = self._get_or_404(task_id)
        self._assert_can_access(current_user, task)
        data = payload.model_dump(exclude_unset=True)
        # A task's firm is fixed at creation; if the edit reassigns it to a
        # different client, that client must still be in the task's own firm
        # (moving a task to another firm's client entirely isn't supported).
        if "client_id" in data and data["client_id"] is not None:
            client = self.db.get(Client, data["client_id"])
            if not client:
                raise HTTPException(status_code=404, detail="Client not found")
            if client.firm_id != task.firm_id:
                raise HTTPException(
                    status_code=400, detail="Cannot reassign a task to another firm's client"
                )
        if "assigned_to_id" in data:
            self._assert_assignee_in_firm(task.firm_id, data["assigned_to_id"])
        for field, value in data.items():
            setattr(task, field, value)
        return self.tasks.update(task)

    def update_status(self, task_id: uuid.UUID, payload: TaskStatusUpdate, current_user: User) -> Task:
        """Drag-and-drop column move on the Kanban board."""
        task = self._get_or_404(task_id)
        self._assert_can_access(current_user, task)
        task.status = payload.status
        return self.tasks.update(task)

    def delete_task(self, task_id: uuid.UUID, current_user: User) -> None:
        task = self._get_or_404(task_id)
        self._assert_can_access(current_user, task)
        self.tasks.delete(task)
