from celery import shared_task

from apps.recurring.services import generate_due_recurring_entries as _generate_due_recurring_entries


@shared_task(name="apps.recurring.tasks.generate_due_recurring_entries")
def generate_due_recurring_entries():
    _generate_due_recurring_entries()
