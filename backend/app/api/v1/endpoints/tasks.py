import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_staff
from app.db.session import get_db
from app.models.user import User
from app.models.workflow import TaskStatus
from app.schemas.task import (
    KanbanBoard,
    TaskCreate,
    TaskRead,
    TaskStatusUpdate,
    TaskUpdate,
)
from app.services.task_service import TaskService

# Staff-only module: this is the accountant workflow board (§3e), not a
# client-facing feature, so every route here requires a staff role.
router = APIRouter(prefix="/tasks", tags=["tasks"], dependencies=[Depends(require_staff)])


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return TaskService(db).create_task(payload, current_user)


@router.get("", response_model=list[TaskRead])
def list_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    assigned_to_id: uuid.UUID | None = Query(default=None),
    status_: TaskStatus | None = Query(default=None, alias="status"),
    client_id: uuid.UUID | None = Query(default=None),
):
    return TaskService(db).list_tasks(
        current_user=current_user,
        assigned_to_id=assigned_to_id,
        status=status_,
        client_id=client_id,
    )


@router.get("/board", response_model=KanbanBoard)
def get_board(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    assigned_to_id: uuid.UUID | None = Query(default=None),
):
    """Same tasks as GET /tasks, pre-grouped into the six fixed Kanban columns
    (New Client → Waiting for Documents → Review → Approval → Filed →
    Completed) so the board can render straight off the response."""
    return TaskService(db).get_board(current_user=current_user, assigned_to_id=assigned_to_id)


@router.get("/{task_id}", response_model=TaskRead)
def get_task(
    task_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return TaskService(db).get_task(task_id, current_user)


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(
    task_id: uuid.UUID,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return TaskService(db).update_task(task_id, payload, current_user)


@router.patch("/{task_id}/status", response_model=TaskRead)
def update_task_status(
    task_id: uuid.UUID,
    payload: TaskStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Drag-and-drop column move on the Kanban board."""
    return TaskService(db).update_status(task_id, payload, current_user)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    TaskService(db).delete_task(task_id, current_user)
