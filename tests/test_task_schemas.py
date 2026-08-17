from datetime import datetime

import pytest
from pydantic import ValidationError

from app.tasks.schemas import TaskCreate, TaskPreferenceUpdate, TaskUpdate


def test_task_due_date_requires_timezone() -> None:
    with pytest.raises(ValidationError, match="timezone offset"):
        TaskCreate(title="Test", due_at=datetime(2026, 8, 18, 12, 0))


@pytest.mark.parametrize("field", ["title", "priority", "visibility"])
def test_task_update_rejects_null_required_fields(field: str) -> None:
    with pytest.raises(ValidationError, match="cannot be null"):
        TaskUpdate.model_validate({field: None})


def test_task_preference_cannot_be_hidden_and_pinned() -> None:
    with pytest.raises(ValidationError, match="hidden and pinned"):
        TaskPreferenceUpdate(is_hidden=True, is_pinned=True)
