# django
from django.db import transaction

# models 
from audit_logs.models import AuditLog


@transaction.atomic()
def log_audit(actor, action, target_model, outcome, server_response, school, target_object_id='N/A'):
    """Helper function to create an audit log entry."""
    AuditLog.objects.create(
        actor=actor, 
        action=action, 
        target_model=target_model, 
        target_object_id=target_object_id, 
        outcome=outcome, 
        server_response=server_response, 
        school=school
    )

