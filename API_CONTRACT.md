# LearnMate Backend API Contract

## Overview
LearnMate is an education platform backend built with FastAPI and Supabase, providing role-based access control for admins, teachers, and students.

## Authentication
All endpoints except `/` require Bearer token authentication via `Authorization: Bearer <token>` header.

**Roles:**
- **Admin**: Full system access, user management, metrics
- **Teacher**: Class management, attendance, assignments, grading
- **Student**: View classes, assignments, submit work, view grades

## Base URL
https://learnmate-backend-ihejirikatochukwudaniel4986-1uwx82iz.leapcell.dev

---

## 1. Root Endpoint

### GET /
**Description:** Health check endpoint

**Authentication:** None required

**Response:**
```json
{
  "message": "Hello World from LearnMate!"
}
```

---

## 2. Authentication Endpoints

### POST /auth/login
**Description:** Login with email and password to get JWT token

**Authentication:** None required

**Request Body:**
```json
{
  "email": "string",
  "password": "string"
}
```

**Response:**
```json
{
  "access_token": "string",
  "token_type": "bearer"
}
```

### POST /auth/me
**Description:** Get user profile information by user ID

**Authentication:** None required

**Request Body:**
```json
{
  "user_id": "string"
}
```

**Response:**
```json
{
  "id": "string",
  "email": "string",
  "role": "string",
  "full_name": "string (optional)"
}
```

---

## 3. Profile Endpoints

### POST /profiles/
**Description:** Create profile on first login

**Authentication:** Required (current user)

**Request Body:**
```json
{
  "full_name": "string (optional)",
  "role": "string (required: 'admin'|'teacher'|'student')"
}
```

**Response:** ProfileResponse (same as below)

### GET /profiles/me
**Description:** Get current user's profile

**Authentication:** Required (current user)

**Response:**
```json
{
  "id": "string",
  "email": "string",
  "full_name": "string (optional)",
  "role": "string",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### PUT /profiles/me
**Description:** Update current user's profile

**Authentication:** Required (current user)

**Request Body:**
```json
{
  "full_name": "string (optional)",
  "role": "string (optional)"
}
```

**Response:** ProfileResponse

### GET /profiles/
**Description:** Get all profiles

**Authentication:** Admin only

**Response:** Array of ProfileResponse

### GET /profiles/{user_id}
**Description:** Get specific profile by user ID

**Authentication:** Admin only

**Response:** ProfileResponse

---

## 4. Class Endpoints

### POST /classes/
**Description:** Create a new class

**Authentication:** Admin only

**Request Body:**
```json
{
  "name": "string",
  "description": "string (optional)",
  "teacher_id": "string"
}
```

**Response:**
```json
{
  "id": "integer",
  "name": "string",
  "description": "string (optional)",
  "teacher_id": "string",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### GET /classes/
**Description:** Get all accessible classes
- Admin: All classes
- Teacher: Their classes
- Student: Enrolled classes

**Authentication:** Required (any role)

**Response:** Array of ClassResponse

### GET /classes/{class_id}
**Description:** Get specific class details

**Authentication:** Required (role-based access)

**Response:** ClassResponse

### PUT /classes/{class_id}
**Description:** Update class

**Authentication:** Admin only

**Request Body:**
```json
{
  "name": "string (optional)",
  "description": "string (optional)",
  "teacher_id": "string (optional)"
}
```

**Response:** ClassResponse

### DELETE /classes/{class_id}
**Description:** Delete class

**Authentication:** Admin only

**Response:**
```json
{
  "message": "Class deleted successfully"
}
```

### POST /classes/{class_id}/students
**Description:** Add student to class

**Authentication:** Admin or class teacher

**Request Body:**
```json
{
  "student_id": "string"
}
```

**Response:**
```json
{
  "class_id": "integer",
  "student_id": "string",
  "enrolled_at": "datetime"
}
```

### GET /classes/{class_id}/students
**Description:** Get students enrolled in class

**Authentication:** Admin or class teacher

**Response:** Array of ClassStudentResponse

### DELETE /classes/{class_id}/students/{student_id}
**Description:** Remove student from class

**Authentication:** Admin or class teacher

**Response:**
```json
{
  "message": "Student removed from class"
}
```

---

## 5. Attendance Endpoints

### POST /attendance/
**Description:** Mark attendance for a student

**Authentication:** Admin or class teacher

**Request Body:**
```json
{
  "class_id": "integer",
  "student_id": "string",
  "date": "date (YYYY-MM-DD)",
  "status": "string ('present'|'absent'|'late')"
}
```

**Response:**
```json
{
  "id": "integer",
  "class_id": "integer",
  "student_id": "string",
  "date": "date",
  "status": "string",
  "marked_by": "string",
  "created_at": "datetime"
}
```

### POST /attendance/bulk
**Description:** Mark attendance for multiple students

**Authentication:** Admin or class teacher

**Request Body:**
```json
{
  "attendances": [
    {
      "class_id": "integer",
      "student_id": "string",
      "date": "date",
      "status": "string"
    }
  ]
}
```

**Response:** Array of AttendanceResponse

### GET /attendance/class/{class_id}
**Description:** Get attendance for a class

**Query Parameters:**
- `date` (optional): Filter by date (YYYY-MM-DD)

**Authentication:** Admin or class teacher

**Response:** Array of AttendanceResponse

### GET /attendance/student/{student_id}
**Description:** Get attendance for a student

**Authentication:** Student (own) or Teacher (their students)

**Response:** Array of AttendanceResponse

### PUT /attendance/{attendance_id}
**Description:** Update attendance record

**Authentication:** Admin or class teacher

**Request Body:**
```json
{
  "status": "string ('present'|'absent'|'late')"
}
```

**Response:** AttendanceResponse

### DELETE /attendance/{attendance_id}
**Description:** Delete attendance record

**Authentication:** Admin or class teacher

**Response:**
```json
{
  "message": "Attendance record deleted"
}
```

### GET /attendance/class/{class_id}/summary
**Description:** Get attendance summary for a class

**Query Parameters:**
- `date` (optional): Date to get summary for (YYYY-MM-DD, defaults to today)

**Authentication:** Admin or class teacher

**Response:**
```json
{
  "class_id": "integer",
  "date": "date",
  "total_students": "integer",
  "present_count": "integer",
  "absent_count": "integer",
  "attendance_percentage": "number"
}
```

---

## 6. Assignment Endpoints

### POST /assignments/
**Description:** Create a new assignment

**Authentication:** Admin or class teacher

**Request Body:**
```json
{
  "class_id": "integer",
  "title": "string",
  "description": "string (optional)",
  "due_date": "date (optional)",
  "file_url": "string (optional)"
}
```

**Response:**
```json
{
  "id": "integer",
  "class_id": "integer",
  "title": "string",
  "description": "string (optional)",
  "due_date": "date (optional)",
  "file_url": "string (optional)",
  "created_by": "string",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### GET /assignments/class/{class_id}
**Description:** Get assignments for a class

**Authentication:** Class members (students enrolled, teachers assigned)

**Response:** Array of AssignmentResponse

### GET /assignments/{assignment_id}
**Description:** Get specific assignment

**Authentication:** Class members

**Response:** AssignmentResponse

### PUT /assignments/{assignment_id}
**Description:** Update assignment

**Authentication:** Admin or class teacher

**Request Body:** Same as create (all optional)

**Response:** AssignmentResponse

### DELETE /assignments/{assignment_id}
**Description:** Delete assignment

**Authentication:** Admin or class teacher

**Response:**
```json
{
  "message": "Assignment deleted successfully"
}
```

---

## 7. Submission Endpoints

### POST /submissions/
**Description:** Submit assignment

**Authentication:** Student enrolled in class

**Request Body:**
```json
{
  "assignment_id": "integer",
  "file_url": "string (optional)",
  "notes": "string (optional)"
}
```

**Response:**
```json
{
  "id": "integer",
  "assignment_id": "integer",
  "student_id": "string",
  "submitted_at": "datetime",
  "file_url": "string (optional)",
  "notes": "string (optional)"
}
```

### GET /submissions/assignment/{assignment_id}
**Description:** Get all submissions for assignment

**Authentication:** Admin or class teacher

**Response:** Array of SubmissionResponse

### GET /submissions/my
**Description:** Get current student's submissions

**Authentication:** Student only

**Response:** Array of SubmissionResponse

### GET /submissions/{submission_id}
**Description:** Get specific submission

**Authentication:** Student (own) or Teacher (their class)

**Response:** SubmissionResponse

### PUT /submissions/{submission_id}
**Description:** Update submission

**Authentication:** Student (own submission)

**Request Body:**
```json
{
  "file_url": "string (optional)",
  "notes": "string (optional)"
}
```

**Response:** SubmissionResponse

### DELETE /submissions/{submission_id}
**Description:** Delete submission

**Authentication:** Admin or class teacher

**Response:**
```json
{
  "message": "Submission deleted successfully"
}
```

---

## 8. Grade Endpoints

### POST /grades/
**Description:** Grade a submission

**Authentication:** Admin or class teacher

**Request Body:**
```json
{
  "submission_id": "integer",
  "grade": "string",
  "feedback": "string (optional)"
}
```

**Response:**
```json
{
  "id": "integer",
  "submission_id": "integer",
  "grade": "string",
  "feedback": "string (optional)",
  "graded_by": "string",
  "graded_at": "datetime"
}
```

### GET /grades/submission/{submission_id}
**Description:** Get grade for a submission

**Authentication:** Student (own) or Teacher (their class)

**Response:** GradeResponse

### GET /grades/my
**Description:** Get current student's grades

**Authentication:** Student only

**Response:** Array of GradeResponse

### GET /grades/assignment/{assignment_id}
**Description:** Get all grades for assignment

**Authentication:** Admin or class teacher

**Response:** Array of GradeResponse

### PUT /grades/{grade_id}
**Description:** Update grade

**Authentication:** Admin or teacher who graded

**Request Body:**
```json
{
  "grade": "string (optional)",
  "feedback": "string (optional)"
}
```

**Response:** GradeResponse

### DELETE /grades/{grade_id}
**Description:** Delete grade

**Authentication:** Admin or teacher who graded

**Response:**
```json
{
  "message": "Grade deleted successfully"
}
```

---

## 9. Admin Endpoints

### GET /admin/metrics
**Description:** Get admin dashboard metrics

**Authentication:** Admin only

**Response:**
```json
{
  "total_users": "integer",
  "active_users": "integer",
  "total_classes": "integer",
  "students_enrolled": "integer",
  "attendance_records": "integer",
  "assignments_created": "integer",
  "grades_entered": "integer"
}
```

### POST /admin/users
**Description:** Create a new user (teacher or student)

**Authentication:** UUID-based admin verification (query parameter)

**Query Parameters:**
- `admin_uuid`: UUID of the admin user (required)

**Request Body:**
```json
{
  "firstName": "string",
  "lastName": "string",
  "email": "string",
  "role": "string ('teacher'|'student')",
  "password": "string (optional)"
}
```

**Response:**
```json
{
  "message": "Teacher/Student user created successfully",
  "user_id": "string",
  "email": "string",
  "role": "string",
  "first_name": "string",
  "last_name": "string",
  "generated_password": "string (if not provided)"
}
```

### GET /admin/users
**Description:** Get all users with profiles

**Authentication:** Admin only

**Response:** Array of user profile objects

### POST /admin/bootstrap-admin
**Description:** Bootstrap the first admin user (no authentication required)

**Authentication:** None required (only works when no users exist)

**Request Body:**
```json
{
  "firstName": "string",
  "lastName": "string",
  "email": "string",
  "role": "string",
  "password": "string (optional)"
}
```

**Response:**
```json
{
  "message": "Admin user created successfully (bootstrap)",
  "user_id": "string",
  "email": "string",
  "role": "string",
  "generated_password": "string (if not provided)"
}
```

### GET /admin/activity
**Description:** Get recent activity logs

**Query Parameters:**
- `limit` (optional): Number of records (default: 50)

**Authentication:** Admin only

**Response:** Array of activity log objects

---

## Error Responses

All endpoints return consistent error responses:

```json
{
  "detail": "Error message string"
}
```

**Common HTTP Status Codes:**
- `200`: Success
- `400`: Bad Request
- `401`: Unauthorized (invalid/missing token)
- `403`: Forbidden (insufficient permissions)
- `404`: Not Found
- `500`: Internal Server Error

## Data Types

- **string**: Text data
- **integer**: Whole numbers
- **date**: ISO format date (YYYY-MM-DD)
- **datetime**: ISO format datetime with timezone
- **boolean**: true/false

## Rate Limiting

No explicit rate limiting implemented in MVP.

## File Uploads

File upload endpoints are prepared but require Supabase Storage configuration for full implementation.
