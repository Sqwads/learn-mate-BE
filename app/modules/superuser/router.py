from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List, Dict
from datetime import datetime, timedelta, timezone
import logging

from app.db.supabase import supabase
from app.schemas.superuser import (
    SchoolListItem,
    SchoolListResponse,
    SchoolAnalytics,
    PlatformAnalytics,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def _extract_data(resp):
    try:
        # supabase-py may return a dict-like or object with .data
        if resp is None:
            return None
        data = getattr(resp, 'data', None)
        if data is None and isinstance(resp, dict):
            data = resp.get('data')
        return data
    except Exception:
        return None


def require_superuser(user_id: str = Query(...)) -> str:
    try:
        resp = supabase.table('profiles').select('id,role').eq('id', user_id).execute()
        data = _extract_data(resp)
        if not data or len(data) == 0:
            raise HTTPException(status_code=403, detail='User not found or unauthorized')
        profile = data[0]
        if profile.get('role') != 'superuser':
            raise HTTPException(status_code=403, detail='Superuser privileges required')
        return user_id
    except HTTPException:
        raise
    except Exception as e:
        logger.error('Error in require_superuser: %s', str(e))
        raise HTTPException(status_code=500, detail='Authorization failure')


@router.get('/superuser/schools', response_model=SchoolListResponse)
def list_schools(
    status: Optional[str] = Query(None),
    sort_by: Optional[str] = Query('name', pattern='^(name|created_at)$'),
    order: Optional[str] = Query('asc', pattern='^(asc|desc)$'),
    _super: str = Depends(require_superuser),
):
    try:
        query = supabase.table('schools').select('*')
        if status:
            query = query.eq('status', status)

        # basic fetch
        resp = query.execute()
        schools = _extract_data(resp) or []

        # map admin ids and batch fetch admin profiles
        admin_ids = list({s.get('admin_id') for s in schools if s.get('admin_id')})
        admins_map = {}
        if admin_ids:
            admin_resp = supabase.table('profiles').select('id,full_name,email').in_('id', admin_ids).execute()
            admin_data = _extract_data(admin_resp) or []
            admins_map = {a.get('id'): a for a in admin_data}

        items = []
        for s in schools:
            created_at = None
            try:
                created_at = datetime.fromisoformat(s.get('created_at')) if s.get('created_at') else None
            except Exception:
                created_at = None

            admin = admins_map.get(s.get('admin_id'))
            items.append(
                SchoolListItem(
                    id=s.get('id'),
                    school_name=s.get('school_name'),
                    status=s.get('status'),
                    created_at=created_at,
                    admin_id=s.get('admin_id'),
                    admin_name=admin.get('full_name') if admin else None,
                    admin_email=admin.get('email') if admin else None,
                )
            )

        # sort
        reverse = order == 'desc'
        if sort_by == 'name':
            items.sort(key=lambda x: (x.school_name or '').lower(), reverse=reverse)
        else:
            items.sort(key=lambda x: x.created_at or datetime.min, reverse=reverse)

        return SchoolListResponse(total_schools=len(items), schools=items)
    except HTTPException:
        raise
    except Exception as e:
        logger.error('Error listing schools: %s', str(e))
        raise HTTPException(status_code=500, detail='Failed to list schools')


@router.get('/superuser/schools/{school_id}/analytics', response_model=SchoolAnalytics)
def school_analytics(school_id: str, _super: str = Depends(require_superuser)):
    try:
        # FIXED: Use timezone-aware datetime
        now = datetime.now(timezone.utc)
        
        # school info
        school_resp = supabase.table('schools').select('id,school_name').eq('id', school_id).execute()
        school_data = _extract_data(school_resp) or []
        if not school_data:
            raise HTTPException(status_code=404, detail='School not found')
        school_name = school_data[0].get('school_name')

        # profiles for the school
        profiles_resp = supabase.table('profiles').select('id,role,last_login,created_at').eq('school_id', school_id).execute()
        profiles = _extract_data(profiles_resp) or []

        total_users = len(profiles)
        active_users = 0
        users_by_role = {}
        thirty_days = now - timedelta(days=30)
        
        for p in profiles:
            role = p.get('role') or 'unknown'
            users_by_role[role] = users_by_role.get(role, 0) + 1
            
            # Check last_login OR created_at as fallback
            try:
                last_login = p.get('last_login')
                created_at = p.get('created_at')
                
                if last_login:
                    if isinstance(last_login, str):
                        dt = datetime.fromisoformat(last_login.replace('Z', '+00:00'))
                    else:
                        dt = last_login
                    if dt >= thirty_days:
                        active_users += 1
                elif created_at:
                    if isinstance(created_at, str):
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        dt = created_at
                    if dt >= thirty_days:
                        active_users += 1
            except Exception as e:
                logger.debug(f"Error parsing login date for user {p.get('id')}: {e}")
                pass

        # classes
        classes_resp = supabase.table('classes').select('id,updated_at,created_at').eq('school_id', school_id).execute()
        classes = _extract_data(classes_resp) or []
        total_classes = len(classes)
        active_classes = 0
        
        for c in classes:
            try:
                updated = c.get('updated_at')
                created = c.get('created_at')
                
                if updated:
                    if isinstance(updated, str):
                        dt = datetime.fromisoformat(updated.replace('Z', '+00:00'))
                    else:
                        dt = updated
                    if dt >= thirty_days:
                        active_classes += 1
                elif created:
                    if isinstance(created, str):
                        dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    else:
                        dt = created
                    if dt >= thirty_days:
                        active_classes += 1
            except Exception as e:
                logger.debug(f"Error parsing date for class {c.get('id')}: {e}")
                pass

        # attendance for classes in this school
        class_ids = [c.get('id') for c in classes if c.get('id')]
        total_attendance_records = 0
        present_count = 0
        recent_attendance_activity = 0
        
        if class_ids:
            att_resp = supabase.table('attendance').select('id,class_id,date,status').in_('class_id', class_ids).execute()
            atts = _extract_data(att_resp) or []
            total_attendance_records = len(atts)
            seven_days = now - timedelta(days=7)
            
            for a in atts:
                status_val = a.get('status')
                
                # Handle boolean status: true = present, false = absent
                is_present = False
                if isinstance(status_val, bool):
                    is_present = status_val
                elif status_val is not None:
                    status_str = str(status_val).lower().strip()
                    if status_str in ['true', '1', 'present', 'p']:
                        is_present = True
                
                if is_present:
                    present_count += 1
                
                try:
                    date_val = a.get('date')
                    if date_val:
                        if isinstance(date_val, str):
                            dt = datetime.fromisoformat(date_val.replace('Z', '+00:00'))
                        else:
                            dt = date_val
                        if dt >= seven_days:
                            recent_attendance_activity += 1
                except Exception as e:
                    logger.debug(f"Error parsing attendance date: {e}")
                    pass

        attendance_rate = round((present_count / total_attendance_records * 100), 2) if total_attendance_records > 0 else None

        logger.info(f"School {school_id} analytics: active_users={active_users}/{total_users}, active_classes={active_classes}/{total_classes}, attendance_rate={attendance_rate}%")

        return SchoolAnalytics(
            school_id=school_id,
            school_name=school_name,
            total_users=total_users,
            active_users=active_users,
            users_by_role=users_by_role,
            total_classes=total_classes,
            active_classes=active_classes,
            total_attendance_records=total_attendance_records,
            attendance_rate=attendance_rate,
            recent_attendance_activity=recent_attendance_activity,
            generated_at=now,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error('Error generating school analytics for %s: %s', school_id, str(e))
        import traceback
        logger.error('Traceback: %s', traceback.format_exc())
        raise HTTPException(status_code=500, detail='Failed to generate school analytics')


@router.get('/superuser/analytics/platform', response_model=PlatformAnalytics)
def platform_analytics(_super: str = Depends(require_superuser)):
    try:
        # FIXED: Use timezone-aware datetime
        now = datetime.now(timezone.utc)
        
        # schools
        schools_resp = supabase.table('schools').select('id,school_name,status').execute()
        schools = _extract_data(schools_resp) or []
        total_schools = len(schools)
        
        # Handle status field - it might be string, boolean, or None
        active_schools = 0
        for s in schools:
            status_val = s.get('status')
            if status_val is not None:
                status_str = str(status_val).lower()
                if status_str in ['active', 'true', '1']:
                    active_schools += 1
            else:
                # If status is None, assume active
                active_schools += 1

        # users
        users_resp = supabase.table('profiles').select('id,role,school_id,last_login,created_at').execute()
        users = _extract_data(users_resp) or []
        total_users = len(users)
        thirty_days = now - timedelta(days=30)
        active_users = 0
        users_by_role = {}
        users_by_school: Dict[str, int] = {}
        
        for u in users:
            role = u.get('role') or 'unknown'
            users_by_role[role] = users_by_role.get(role, 0) + 1
            
            # Count users per school
            sid = u.get('school_id')
            if sid:
                users_by_school[sid] = users_by_school.get(sid, 0) + 1
            
            # Check last_login OR created_at as fallback
            try:
                last_login = u.get('last_login')
                created_at = u.get('created_at')
                
                # Try last_login first
                if last_login:
                    if isinstance(last_login, str):
                        dt = datetime.fromisoformat(last_login.replace('Z', '+00:00'))
                    else:
                        dt = last_login
                    if dt >= thirty_days:
                        active_users += 1
                # If no last_login, use created_at as fallback (newly created = active)
                elif created_at:
                    if isinstance(created_at, str):
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        dt = created_at
                    if dt >= thirty_days:
                        active_users += 1
            except Exception as e:
                logger.debug(f"Error parsing login date for user {u.get('id')}: {e}")
                pass

        # classes
        classes_resp = supabase.table('classes').select('id,updated_at,created_at,school_id').execute()
        classes = _extract_data(classes_resp) or []
        total_classes = len(classes)
        active_classes = 0
        class_to_school = {}
        
        for c in classes:
            class_id = c.get('id')
            school_id = c.get('school_id')
            if class_id:
                class_to_school[class_id] = school_id
            
            # Check updated_at OR created_at as fallback
            try:
                updated = c.get('updated_at')
                created = c.get('created_at')
                
                # Try updated_at first
                if updated:
                    if isinstance(updated, str):
                        dt = datetime.fromisoformat(updated.replace('Z', '+00:00'))
                    else:
                        dt = updated
                    if dt >= thirty_days:
                        active_classes += 1
                # If no updated_at, use created_at as fallback
                elif created:
                    if isinstance(created, str):
                        dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    else:
                        dt = created
                    if dt >= thirty_days:
                        active_classes += 1
            except Exception as e:
                logger.debug(f"Error parsing date for class {class_id}: {e}")
                pass

        # attendance
        att_resp = supabase.table('attendance').select('id,class_id,date,status').execute()
        atts = _extract_data(att_resp) or []
        total_attendance_records = len(atts)
        present_count = 0
        recent_activity = 0
        seven_days = now - timedelta(days=7)
        attendance_by_school: Dict[str, Dict[str, int]] = {}
        
        for a in atts:
            status_val = a.get('status')
            
            # Handle boolean status: true = present, false = absent
            is_present = False
            if isinstance(status_val, bool):
                is_present = status_val  # Direct boolean check
            elif status_val is not None:
                # Fallback for string values
                status_str = str(status_val).lower().strip()
                if status_str in ['true', '1', 'present', 'p']:
                    is_present = True
            
            if is_present:
                present_count += 1
            
            try:
                date_val = a.get('date')
                if date_val:
                    if isinstance(date_val, str):
                        dt = datetime.fromisoformat(date_val.replace('Z', '+00:00'))
                    else:
                        dt = date_val
                    if dt >= seven_days:
                        recent_activity += 1
            except Exception as e:
                logger.debug(f"Error parsing attendance date: {e}")
                pass
            
            # Track attendance per school
            cid = a.get('class_id')
            sid = class_to_school.get(cid)
            if sid:
                rec = attendance_by_school.setdefault(sid, {'present': 0, 'total': 0})
                rec['total'] += 1
                if is_present:
                    rec['present'] += 1

        overall_attendance_rate = round((present_count / total_attendance_records * 100), 2) if total_attendance_records > 0 else 0.0

        # get school names map
        school_map = {s.get('id'): s for s in schools}

        # top schools by users
        top_schools_by_users = sorted(
            [
                {
                    "school_id": sid,
                    "school_name": (school_map.get(sid) or {}).get('school_name'),
                    "user_count": count
                }
                for sid, count in users_by_school.items()
                if school_map.get(sid)  # Only include if school exists
            ],
            key=lambda x: x['user_count'],
            reverse=True,
        )[:10]

        # top schools by attendance
        top_schools_by_attendance = []
        for sid, rec in attendance_by_school.items():
            if rec['total'] > 0 and school_map.get(sid):
                rate = round((rec['present'] / rec['total'] * 100), 2)
                top_schools_by_attendance.append({
                    'school_id': sid,
                    'school_name': (school_map.get(sid) or {}).get('school_name'),
                    'attendance_rate': rate,
                    'total_records': rec['total'],
                })

        top_schools_by_attendance = sorted(
            top_schools_by_attendance,
            key=lambda x: x['attendance_rate'],
            reverse=True
        )[:10]

        logger.info(f"Platform analytics: active_users={active_users}/{total_users}, active_classes={active_classes}/{total_classes}, present={present_count}/{total_attendance_records}, rate={overall_attendance_rate}%")

        return PlatformAnalytics(
            total_schools=total_schools,
            active_schools=active_schools,
            total_users=total_users,
            active_users=active_users,
            users_by_role=users_by_role,
            total_classes=total_classes,
            active_classes=active_classes,
            total_attendance_records=total_attendance_records,
            overall_attendance_rate=overall_attendance_rate,
            recent_attendance_activity=recent_activity,
            top_schools_by_users=top_schools_by_users,
            top_schools_by_attendance=top_schools_by_attendance,
            generated_at=now,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error('Error generating platform analytics: %s', str(e))
        import traceback
        logger.error('Traceback: %s', traceback.format_exc())
        raise HTTPException(status_code=500, detail='Failed to generate platform analytics')