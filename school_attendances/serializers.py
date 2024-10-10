# rest framework
from rest_framework import serializers

# models
from .models import ClassroomAttendanceRegister

# serilializers
from accounts.serializers.students.serializers import LeastAccountDetailsSerializer


class ClassroomAttendanceSerializer(serializers.ModelSerializer):

    absent_students = LeastAccountDetailsSerializer(many=True)
    late_students = LeastAccountDetailsSerializer(many=True)

    class Meta:
        model = ClassroomAttendanceRegister
        fields = ['timestamp', 'absent_students', 'late_students']
    


class StudentAttendanceSerializer(serializers.ModelSerializer):

    absent = serializers.SerializerMethodField()

    class Meta:
        model = ClassroomAttendanceRegister
        fields = ['timestamp', 'absent']
    
    def get_absent(self, obj):
        student = self.context.get('student')
        return obj.absent_students.filter(account_id=student).exists()



