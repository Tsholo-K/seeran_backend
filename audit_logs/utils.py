# django
from django.core.exceptions import ValidationError

# models 
from audit_logs.models import AuditLog


def log_audit(actor, action, target_model, outcome, server_response, school, target_object_id='N/A'):
    """Helper function to create an audit log entry."""
    try:
        AuditLog.objects.create(
            actor=actor, 
            action=action, 
            target_model=target_model, 
            target_object_id=target_object_id, 
            outcome=outcome, 
            server_response=server_response, 
            school=school
        )

    except Exception as e:
        raise ValidationError(_(str(e)))

