from accounts.decorators import role_required
from accounts.models import User


student_required = role_required(User.Role.STUDENT)
