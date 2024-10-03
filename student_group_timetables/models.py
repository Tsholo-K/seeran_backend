# python 
import uuid

# django 
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError


class StudentGroupTimetable(models.Model):
    group_name = models.CharField(max_length=64)
    description = models.TextField(max_length=1024, null=True, blank=True)

    subscribers = models.ManyToManyField('accounts.Student', related_name='timetables')
    
    students_count = models.PositiveIntegerField(default=0)
    timetables_count = models.PositiveIntegerField(default=0)
 
    grade = models.ForeignKey('grades.Grade', on_delete=models.CASCADE, related_name='group_timetables')
    
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, related_name='group_timetables')

    last_updated = models.DateTimeField(auto_now=True)

    timestamp = models.DateTimeField(auto_now_add=True)
    group_timetable_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        ordering = ['group_name']

    def __str__(self):
        return self.group_timetable_id
    
    def update_subscribers(self, student_ids=None, subscribe=False):
        try:
            if student_ids:
                if subscribe:
                    # Check if students are already in this specific group timetable
                    students_in_the_group = self.subscribers.filter(account_id__in=student_ids).values_list('surname', 'name')
                    if students_in_the_group:
                        student_names = [f"{surname} {name}" for surname, name in students_in_the_group]
                        raise ValidationError(f'the following students are already in this group timetable: {", ".join(student_names)}')

                    # Retrieve CustomUser instances corresponding to the account_ids
                    students = self.grade.students.filter(account_id__in=student_ids)

                    if not students.exists():
                        raise ValidationError("Could not proccess your request, no valid students were found in the provided list of student account IDs.")
                    
                    self.subscribers.add(students)

                else:
                    # Check if students to be removed are actually in the class
                    existing_students = self.subscribers.filter(account_id__in=student_ids)
                    if not existing_students.exists():
                        raise ValidationError("could not proccess your request, all the provided students are not part of this classroom")
                    
                    self.subscribers.remove(existing_students)

                # Save the classroom instance first to ensure student changes are persisted
                self.save()

                # Update the students count in the class
                self.student_count = self.subscribers.count()
                self.save()  # Save again to update students_count field
            else:
                raise ValidationError(f"Could not proccess your request, no students were provided to be {'subscribed to' if subscribe else 'unsubscribed from'} the group timetable. please provide a valid list of students and try again")
        except Exception as e:
            raise ValidationError(_(str(e)))  # Catch and raise any exceptions as validation errors
        



"""
    dummy data

    [
        {
            "group_name": "Grade 1A Timetable",
            "description": "This timetable covers the daily schedule for Grade 1A, including subjects like Math, Reading, and Art.",
            "subscribers": [student1, student2, student3],
            "students_count": 25,
            "timetables_count": 1,
            "grade": grade_1a,  # Grade 1A instance
            "school": school_instance,
            "last_updated": "2024-09-28T15:24:00Z",
            "timestamp": "2024-09-01T08:00:00Z",
            "group_timetable_id": "b8a9bfc1-3779-45f7-bb92-7cb8e0ec9b6a"
        },
        {
            "group_name": "Grade 1B Timetable",
            "description": "This timetable includes all sessions for Grade 1B students from Monday to Friday, with classes like Science, Social Studies, and Music.",
            "subscribers": [student4, student5, student6],
            "students_count": 28,
            "timetables_count": 1,
            "grade": grade_1b,
            "school": school_instance,
            "last_updated": "2024-09-28T15:24:00Z",
            "timestamp": "2024-09-01T08:00:00Z",
            "group_timetable_id": "cb2d940f-2711-4935-bd1e-6a1740e5b96e"
        },
        {
            "group_name": "Grade 2A Weekly Timetable",
            "description": "A weekly overview of classes for Grade 2A, including Math, Physical Education, and Handwriting practice.",
            "subscribers": [student7, student8, student9],
            "students_count": 27,
            "timetables_count": 1,
            "grade": grade_2a,
            "school": school_instance,
            "last_updated": "2024-09-28T15:24:00Z",
            "timestamp": "2024-09-01T08:00:00Z",
            "group_timetable_id": "da3f4d12-7641-4292-9e25-9f79e0389423"
        },
        {
            "group_name": "Grade 2B Timetable",
            "description": "Grade 2B's schedule includes Math, Reading, Writing, and Music classes, organized for the entire week.",
            "subscribers": [student10, student11, student12],
            "students_count": 30,
            "timetables_count": 1,
            "grade": grade_2b,
            "school": school_instance,
            "last_updated": "2024-09-28T15:24:00Z",
            "timestamp": "2024-09-01T08:00:00Z",
            "group_timetable_id": "ee47ac29-bbfb-4c2e-8d58-809ba848a65f"
        },
        {
            "group_name": "Grade 3A Timetable",
            "description": "The schedule for Grade 3A, including Math, Science, History, and Physical Education.",
            "subscribers": [student13, student14, student15],
            "students_count": 29,
            "timetables_count": 1,
            "grade": grade_3a,
            "school": school_instance,
            "last_updated": "2024-09-28T15:24:00Z",
            "timestamp": "2024-09-01T08:00:00Z",
            "group_timetable_id": "fa891847-36ab-45c8-8619-76fe62f73b2c"
        },
        {
            "group_name": "Grade 3B Timetable",
            "description": "This timetable includes all academic sessions for Grade 3B students, such as Math, Geography, and English.",
            "subscribers": [student16, student17, student18],
            "students_count": 26,
            "timetables_count": 1,
            "grade": grade_3b,
            "school": school_instance,
            "last_updated": "2024-09-28T15:24:00Z",
            "timestamp": "2024-09-01T08:00:00Z",
            "group_timetable_id": "9ac80bc9-dc8b-4994-a6f0-bef79f906374"
        },
        {
            "group_name": "Grade 4A Weekly Timetable",
            "description": "This timetable covers Grade 4A classes like English, Math, Science, and Physical Education for the entire week.",
            "subscribers": [student19, student20, student21],
            "students_count": 31,
            "timetables_count": 1,
            "grade": grade_4a,
            "school": school_instance,
            "last_updated": "2024-09-28T15:24:00Z",
            "timestamp": "2024-09-01T08:00:00Z",
            "group_timetable_id": "c0172b7e-6174-4a84-95ef-0fc7c66584f1"
        },
        {
            "group_name": "Grade 5A Timetable",
            "description": "Grade 5A's weekly timetable with Math, Science, History, and Art classes.",
            "subscribers": [student22, student23, student24],
            "students_count": 30,
            "timetables_count": 1,
            "grade": grade_5a,
            "school": school_instance,
            "last_updated": "2024-09-28T15:24:00Z",
            "timestamp": "2024-09-01T08:00:00Z",
            "group_timetable_id": "e817dcf4-1190-42bc-a3bb-71081b38b660"
        },
        {
            "group_name": "Grade 6A Weekly Timetable",
            "description": "A complete schedule of classes for Grade 6A, including Mathematics, English, and Social Studies.",
            "subscribers": [student25, student26, student27],
            "students_count": 32,
            "timetables_count": 1,
            "grade": grade_6a,
            "school": school_instance,
            "last_updated": "2024-09-28T15:24:00Z",
            "timestamp": "2024-09-01T08:00:00Z",
            "group_timetable_id": "7ecfb017-6a4b-4b66-985e-ddef61efefac"
        },
        {
            "group_name": "Grade 7A Timetable",
            "description": "Grade 7A's complete schedule, including Math, Science, and Physical Education classes.",
            "subscribers": [student28, student29, student30],
            "students_count": 33,
            "timetables_count": 1,
            "grade": grade_7a,
            "school": school_instance,
            "last_updated": "2024-09-28T15:24:00Z",
            "timestamp": "2024-09-01T08:00:00Z",
            "group_timetable_id": "d72f58b9-032b-4b85-9d50-cb1659bba9b9"
        },
        {
            "group_name": "Grade 8A Timetable",
            "description": "Timetable for Grade 8A students, including major subjects like Math and Science, and elective courses.",
            "subscribers": [student31, student32, student33],
            "students_count": 28,
            "timetables_count": 1,
            "grade": grade_8a,
            "school": school_instance,
            "last_updated": "2024-09-28T15:24:00Z",
            "timestamp": "2024-09-01T08:00:00Z",
            "group_timetable_id": "b0cb248e-9011-414d-9733-5d29e4f42bde"
        },
        {
            "group_name": "Grade 9A Timetable",
            "description": "A weekly timetable for Grade 9A, including subjects such as History, Math, Science, and elective courses.",
            "subscribers": [student34, student35, student36],
            "students_count": 30,
            "timetables_count": 1,
            "grade": grade_9a,
            "school": school_instance,
            "last_updated": "2024-09-28T15:24:00Z",
            "timestamp": "2024-09-01T08:00:00Z",
            "group_timetable_id": "6d68f8cc-f4a4-41f1-b83f-3144cb291bc4"
        }
    ]

"""