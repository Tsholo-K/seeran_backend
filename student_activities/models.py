# python 
import uuid

# django 
from django.db import models
from django.utils.translation import gettext_lazy as _


class StudentActivity(models.Model):
    # In case the logger is deleted, we keep the log but set the logger to null
    auditor = models.ForeignKey('accounts.BaseAccount', on_delete=models.SET_NULL, related_name='logged_activities', null=True, blank=True)
    recipient = models.ForeignKey('accounts.Student', on_delete=models.CASCADE, related_name='my_activities')

    activity_summary = models.CharField(_('offence'), max_length=124)
    activity_details = models.TextField(_('more details about the offence'), max_length=1024)

    classroom = models.ForeignKey('classrooms.Classroom', on_delete=models.SET_NULL, related_name='student_activities', null=True, blank=True)

    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, related_name='student_activities')

    timestamp = models.DateTimeField(auto_now_add=True)
    # Prevent the activity ID from being edited after creation
    student_activity_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.activity_summary} logged by {self.auditor} for {self.recipient}"


# dummy data
"""
    # Example 1
    StudentActivity.objects.create(
        activity_summary="Late Submission",
        activity_details="The student submitted the assignment three days after the deadline. Despite several reminders, there was no communication explaining the delay."
    )

    # Example 2
    StudentActivity.objects.create(
        activity_summary="Disruptive Behavior",
        activity_details="The student was repeatedly interrupting the class, talking loudly, and ignoring the teacher's requests to stay focused."
    )

    # Example 3
    StudentActivity.objects.create(
        activity_summary="Excellent Participation",
        activity_details="The student actively participated in all class discussions, providing insightful comments and helping peers with their assignments."
    )

    # Example 4
    StudentActivity.objects.create(
        activity_summary="Incomplete Homework",
        activity_details="The student failed to complete the assigned homework for the third consecutive week, and no valid reason was provided."
    )

    # Example 5
    StudentActivity.objects.create(
        activity_summary="Cheating During Exam",
        activity_details="The student was caught using unauthorized materials during the mid-term exam. The invigilator documented the incident and reported it to the school administration."
    )

    # Example 6
    StudentActivity.objects.create(
        activity_summary="Library Fine",
        activity_details="The student incurred a fine for returning library books 10 days past the due date. The fine was settled immediately."
    )

"""