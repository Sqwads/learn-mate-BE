# LearnMate Backend 🚀

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Supabase](https://img.shields.io/badge/Supabase-1.0+-orange.svg)](https://supabase.com/)

**LearnMate Backend MVP** - A complete education platform backend built with FastAPI and Supabase, featuring role-based access control for admins, teachers, and students.

## 📋 Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Database Schema](#database-schema)
- [Installation](#installation)
- [Setup](#setup)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Development](#development)

## ✨ Features

### **Phase 1: Authentication & Roles** ✅
- 🔐 **Supabase JWT Integration** - Secure authentication with role-based access
- 👥 **Role-based Access Control** - Admin, Teacher, Student permissions
- 🛡️ **Dependency Guards** - Automatic permission checking per endpoint

### **Phase 2: Profiles** ✅
- 👤 **User Profiles** - Extended user information management
- 📝 **Profile Creation** - Automatic profile setup on first login
- 🔄 **Profile Updates** - Self-service profile management

### **Phase 3: Classes** ✅
- 📚 **Class Management** - Create and manage classes
- 👨‍🏫 **Teacher Assignment** - Assign teachers to classes
- 👨‍🎓 **Student Enrollment** - Add/remove students from classes

### **Phase 4: Attendance** ✅
- 📊 **Attendance Tracking** - Mark daily attendance per student
- 📅 **Bulk Attendance** - Mark attendance for entire classes
- 📈 **Attendance Reports** - View attendance by class or student

### **Phase 5: Assignments** ✅
- 📝 **Assignment Creation** - Create assignments with due dates
- 📎 **File Attachments** - Support for assignment files (Supabase Storage ready)
- 📋 **Assignment Management** - Update and delete assignments

### **Phase 6: Submissions** ✅
- 📤 **Student Submissions** - Submit assignments with files and notes
- 🔄 **Submission Updates** - Edit submissions before grading
- 📂 **Submission Management** - View all submissions per assignment

### **Phase 7: Grades** ✅
- ✅ **Grade Assignment** - Teachers can grade submissions
- 💬 **Feedback System** - Add feedback with grades
- 📊 **Grade History** - Track grading history and updates

### **Phase 8: Admin Metrics** ✅
- 📈 **Dashboard Metrics** - Total users, classes, attendance, grades
- 👥 **User Management** - View all users and profiles
- 📋 **Activity Logs** - Track system activity (infrastructure ready)

## 🛠 Tech Stack

- **Backend Framework**: FastAPI
- **Database**: Supabase (PostgreSQL)
- **Authentication**: JWT with PyJWT
- **API Documentation**: Auto-generated Swagger UI
- **Environment Management**: python-dotenv
- **Data Validation**: Pydantic
- **ASGI Server**: Uvicorn

## 🏗 Project Structure

```
learnmate-backend/
├── 📁 app/
│   ├── main.py                 # FastAPI app & router includes
│   ├── core/
│   │   ├── config.py          # Pydantic settings
│   │   ├── security.py        # JWT auth & Supabase integration
│   │   └── dependencies.py    # Role-based dependency guards
│   ├── db/
│   │   ├── models.py          # Pydantic data models
│   │   └── supabase.py        # Supabase client setup
│   ├── modules/                # Feature-specific modules
│   │   ├── auth/              # Authentication endpoints
│   │   ├── profiles/          # User profile management
│   │   ├── classes/           # Class & enrollment management
│   │   ├── attendance/        # Attendance tracking
│   │   ├── assignments/       # Assignment management
│   │   ├── submissions/       # Student submissions
│   │   ├── grades/            # Grading system
│   │   └── admin/             # Admin dashboard & metrics
│   └── schemas/               # Request/Response Pydantic schemas
├── 📄 API_CONTRACT.md         # Complete API documentation
├── 📄 requirements.txt        # Python dependencies
├── 📄 .env.example           # Environment variables template
├── 🐳 Dockerfile             # Docker container config
├── 🐳 docker-compose.yml     # Docker Compose setup
└── 📄 README.md              # This file
```

## 📊 Database Schema

The application uses **Supabase PostgreSQL** with the following core tables:

### **Core Tables**
- **`profiles`** (extends `auth.users`)
  - `id` (uuid, FK to auth.users)
  - `email` (string)
  - `full_name` (string, optional)
  - `role` (string: 'admin'|'teacher'|'student')
  - `created_at`, `updated_at` (timestamps)

### **Education Tables**
- **`classes`**
  - `id` (integer, PK)
  - `name`, `description` (strings)
  - `teacher_id` (uuid, FK to profiles)
  - `created_at`, `updated_at` (timestamps)

- **`class_students`** (junction table)
  - `class_id` (integer, FK to classes)
  - `student_id` (uuid, FK to profiles)
  - `enrolled_at` (timestamp)

### **Assignment System**
- **`assignments`**
  - `id` (integer, PK)
  - `class_id` (integer, FK to classes)
  - `title`, `description` (strings)
  - `due_date` (date, optional)
  - `file_url` (string, optional)
  - `created_by` (uuid, FK to profiles)
  - `created_at`, `updated_at` (timestamps)

- **`submissions`**
  - `id` (integer, PK)
  - `assignment_id` (integer, FK to assignments)
  - `student_id` (uuid, FK to profiles)
  - `file_url`, `notes` (strings, optional)
  - `submitted_at` (timestamp)

### **Grading & Attendance**
- **`grades`**
  - `id` (integer, PK)
  - `submission_id` (integer, FK to submissions)
  - `grade` (string)
  - `feedback` (string, optional)
  - `graded_by` (uuid, FK to profiles)
  - `graded_at` (timestamp)

- **`attendance`**
  - `id` (integer, PK)
  - `class_id` (integer, FK to classes)
  - `student_id` (uuid, FK to profiles)
  - `date` (date)
  - `status` (string: 'present'|'absent'|'late')
  - `marked_by` (uuid, FK to profiles)
  - `created_at` (timestamp)

### **Activity Tracking**
- **`activity_logs`** (future implementation)
  - `id` (integer, PK)
  - `user_id` (uuid, FK to profiles)
  - `action`, `resource_type` (strings)
  - `resource_id` (integer, optional)
  - `details` (json, optional)
  - `created_at` (timestamp)

## 🚀 Installation

### Prerequisites

- Python 3.8+
- Supabase account and project
- Git

### Clone the Repository

```bash
git clone https://github.com/your-username/learnmate-backend.git
cd learnmate-backend
```

### Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Docker Setup (Recommended)

If you prefer using Docker:

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or build and run separately
docker build -t learnmate-backend .
docker run -p 8000:8000 --env-file .env learnmate-backend
```

## ⚙️ Setup

### Environment Configuration

1. Copy the environment template:
```bash
cp .env.example .env
```

2. Fill in your Supabase credentials in `.env`:
```env
SUPABASE_URL=your-supabase-project-url
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key
SUPABASE_JWT_SECRET=your-jwt-secret
```

### Database Setup

Ensure your Supabase project has the following tables:
- `users` - User accounts
- `profiles` - Extended user information
- `classes` - Course/class data
- `assignments` - Assignment definitions
- `submissions` - Student submissions
- `grades` - Grading records
- `attendance` - Attendance logs

## 🎯 Usage

### Development Server

Start the development server with auto-reload:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Visit `http://localhost:8000` to see the API documentation.

### API Documentation

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI Schema**: `http://localhost:8000/openapi.json`

## 📡 API Endpoints

### **Core Endpoints**
- `GET /` - Health check endpoint
- `GET /auth/me` - Get current authenticated user info

### **Profile Management** 👤
- `POST /profiles/` - Create user profile (first login)
- `GET /profiles/me` - Get own profile
- `PUT /profiles/me` - Update own profile
- `GET /profiles/` - List all profiles (admin only)
- `GET /profiles/{user_id}` - Get specific profile (admin only)

### **Class Management** 📚
- `POST /classes/` - Create new class (admin only)
- `GET /classes/` - List accessible classes (role-based)
- `GET /classes/{class_id}` - Get class details
- `PUT /classes/{class_id}` - Update class (admin only)
- `DELETE /classes/{class_id}` - Delete class (admin only)
- `POST /classes/{class_id}/students` - Enroll student (admin/teacher)
- `GET /classes/{class_id}/students` - List enrolled students (admin/teacher)
- `DELETE /classes/{class_id}/students/{student_id}` - Unenroll student (admin/teacher)

### **Attendance Tracking** 📊
- `POST /attendance/` - Mark individual attendance (admin/teacher)
- `POST /attendance/bulk` - Bulk attendance marking (admin/teacher)
- `GET /attendance/class/{class_id}` - Get class attendance (admin/teacher)
- `GET /attendance/student/{student_id}` - Get student attendance (own or teacher)
- `PUT /attendance/{attendance_id}` - Update attendance record (admin/teacher)
- `DELETE /attendance/{attendance_id}` - Delete attendance record (admin/teacher)

### **Assignment System** 📝
- `POST /assignments/` - Create assignment (admin/teacher)
- `GET /assignments/class/{class_id}` - List class assignments (class members)
- `GET /assignments/{assignment_id}` - Get assignment details (class members)
- `PUT /assignments/{assignment_id}` - Update assignment (admin/teacher)
- `DELETE /assignments/{assignment_id}` - Delete assignment (admin/teacher)

### **Submission Handling** 📤
- `POST /submissions/` - Submit assignment (students only)
- `GET /submissions/assignment/{assignment_id}` - View submissions (admin/teacher)
- `GET /submissions/my` - Get own submissions (students only)
- `GET /submissions/{submission_id}` - Get submission details
- `PUT /submissions/{submission_id}` - Update submission (own only)
- `DELETE /submissions/{submission_id}` - Delete submission (admin/teacher)

### **Grading System** ✅
- `POST /grades/` - Grade submission (admin/teacher)
- `GET /grades/submission/{submission_id}` - Get grade (student/teacher)
- `GET /grades/my` - Get own grades (students only)
- `GET /grades/assignment/{assignment_id}` - Get assignment grades (admin/teacher)
- `PUT /grades/{grade_id}` - Update grade (admin/teacher who graded)
- `DELETE /grades/{grade_id}` - Delete grade (admin/teacher who graded)

### **Admin Dashboard** 👨‍💼
- `GET /admin/metrics` - System metrics and statistics
- `GET /admin/users` - List all users and profiles
- `GET /admin/activity` - Recent activity logs

### **📄 Complete API Documentation**
For detailed request/response schemas, authentication requirements, and examples, see **[API_CONTRACT.md](API_CONTRACT.md)**

## 🔧 Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black .
isort .
```

### Linting

```bash
flake8 .
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**LearnMate Backend** - Built with ❤️ using FastAPI and Supabase