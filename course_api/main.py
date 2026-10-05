# -*- coding: utf-8 -*-
"""校园选课系统后端 (FastAPI + SQLAlchemy + SQLite)。

为「选课系统接口自动化测试」项目提供本地可运行、可回归的被测系统。

业务能力：
  - 注册 / 登录（发放 token）
  - 查看课程列表
  - 选课（校验角色、容量、重复、时间冲突）
  - 退课（容量回滚）
  - 查看我的课程
  - 管理员：创建课程、查看统计（用于构造精确的边界数据 + 越权 403 场景）

数据库：SQLite（零外部依赖）。
  - 若要切换 MySQL：把下方 DATABASE_URL 改为
      "mysql+pymysql://user:pass@127.0.0.1:3306/course_db?charset=utf8mb4"
    并 `pip install pymysql`；其余代码（SQLAlchemy ORM）无需改动。
"""
from __future__ import annotations

import hashlib
import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker

# ---------------------------------------------------------------------------
# 数据库层
# ---------------------------------------------------------------------------
# 切换 MySQL 示例：
#   DATABASE_URL = "mysql+pymysql://root:123456@127.0.0.1:3306/course_db?charset=utf8mb4"
#   （并 `pip install pymysql`；其余代码无需改动）
# SQLite 使用「相对本文件」的绝对路径，保证测试进程与 uvicorn 子进程读写同一库文件，
# 且不依赖运行 cwd。
_DB_PATH = Path(__file__).resolve().parent.parent / "course.db"
DATABASE_URL = os.environ.get("COURSE_DATABASE_URL", f"sqlite:///{_DB_PATH.as_posix()}")

IS_SQLITE = DATABASE_URL.startswith("sqlite:")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False, "timeout": 30} if IS_SQLITE else {})


from sqlalchemy import event  # noqa: E402


@event.listens_for(engine, "connect")
def _sqlite_pragma(dbapi_conn, _record):
    """WAL 日志模式：并发容量测试 8 线程同时写时降低锁争用残留
    （busy_timeout=30s 仍是兜底；WAL 让读不阻塞写）。"""
    if not IS_SQLITE:
        return
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="student")  # student/teacher/admin
    enrollments = relationship("Enrollment", back_populates="student")


class Course(Base):
    __tablename__ = "courses"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    capacity = Column(Integer, nullable=False)            # 容量上限
    enrolled = Column(Integer, nullable=False, default=0)  # 当前已选人数
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)


class Enrollment(Base):
    __tablename__ = "enrollments"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    enrolled_at = Column(DateTime, default=datetime.utcnow)
    student = relationship("User", back_populates="enrollments")
    __table_args__ = (UniqueConstraint("student_id", "course_id", name="uq_enroll"),)


class AccessToken(Base):
    """服务端持有的不透明 token（只存 SHA-256 摘要，不存原文）。

    2026-09 修复：旧实现签发可预测的 `token-<username>`，知道用户名即可冒充任意人；
    现改为 secrets.token_urlsafe 随机 token + 服务端落库校验 + 7 天过期。
    """
    __tablename__ = "access_tokens"
    token_hash = Column(String(64), primary_key=True, index=True)  # sha256(token)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


TOKEN_TTL = timedelta(days=7)
_PBKDF2_ITERATIONS = 120_000


def hash_password(plain: str) -> str:
    """PBKDF2-HMAC-SHA256 加盐哈希（标准库实现，零额外依赖）。"""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", plain.encode("utf-8"), bytes.fromhex(salt), _PBKDF2_ITERATIONS
    )
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt}${digest.hex()}"


def verify_password(plain: str, stored: str) -> bool:
    """校验密码；兼容旧库遗留明文（由 login 校验通过后透明升级为哈希）。"""
    if stored and stored.startswith("pbkdf2_sha256$"):
        try:
            _, iters, salt, expected = stored.split("$", 3)
            digest = hashlib.pbkdf2_hmac(
                "sha256", plain.encode("utf-8"), bytes.fromhex(salt), int(iters)
            )
            return secrets.compare_digest(digest.hex(), expected)
        except (ValueError, TypeError):
            return False
    try:
        # 旧库遗留明文（compare_digest 仅支持 ASCII，非 ASCII 需先编码）
        return secrets.compare_digest(plain.encode("utf-8"), (stored or "").encode("utf-8"))
    except Exception:
        return False


# ---------------------------------------------------------------------------
# 应用生命周期：建表 + 初始化确定性种子数据
# ---------------------------------------------------------------------------
def seed_data() -> None:
    """写入确定性种子数据（幂等：仅当表为空时写入）。"""
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            db.add_all([
                User(username="alice", password=hash_password("pass123"), role="student"),
                User(username="bob", password=hash_password("pass123"), role="student"),
                User(username="teacher1", password=hash_password("pass123"), role="teacher"),
                User(username="admin", password=hash_password("pass123"), role="admin"),
            ])
        if db.query(Course).count() == 0:
            db.add_all([
                # id=1: 已满课程（enrolled == capacity），用于「容量已满」边界
                Course(name="数据结构", capacity=30, enrolled=30, start_time=datetime(2026, 3, 1, 9, 0), end_time=datetime(2026, 3, 1, 10, 0)),
                # id=2: 容量 2，9:00-10:00（与 id=1 同时段，用于时间冲突）
                Course(name="操作系统", capacity=2, enrolled=0, start_time=datetime(2026, 3, 1, 9, 0), end_time=datetime(2026, 3, 1, 10, 0)),
                # id=3: 空闲大容量课程（正常选课）
                Course(name="计算机网络", capacity=50, enrolled=0, start_time=datetime(2026, 3, 1, 11, 0), end_time=datetime(2026, 3, 1, 12, 0)),
            ])
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_data()
    yield


app = FastAPI(title="校园选课系统", lifespan=lifespan)
security = HTTPBearer(auto_error=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 鉴权：随机不透明 token（服务端落库校验 + 7 天过期）
# 生产环境建议替换为 JWT（签发/验签/过期/吊销），此处保持零额外依赖的确定性回归。
# ---------------------------------------------------------------------------
def _token_digest(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def issue_token(user: User, db: Session) -> str:
    """签发随机 token：原文只返回一次，库里只存 SHA-256 摘要。"""
    # 顺手清理该用户的过期 token 行：access_tokens 只增不减会无限膨胀
    db.query(AccessToken).filter(
        AccessToken.user_id == user.id,
        AccessToken.created_at < datetime.utcnow() - TOKEN_TTL,
    ).delete(synchronize_session=False)
    raw = secrets.token_urlsafe(32)
    db.add(AccessToken(token_hash=_token_digest(raw), user_id=user.id))
    db.commit()
    return raw


def current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="缺少有效 Bearer token")
    row = (
        db.query(AccessToken)
        .filter(AccessToken.token_hash == _token_digest(credentials.credentials))
        .first()
    )
    if row is None or datetime.utcnow() - row.created_at > TOKEN_TTL:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="无效或过期 token")
    user = db.query(User).filter(User.id == row.user_id).first()
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    return user


def require_role(user: User, *roles: str) -> User:
    if user.role not in roles:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="权限不足")
    return user


# ---------------------------------------------------------------------------
# 请求/响应模型
# ---------------------------------------------------------------------------
class RegisterReq(BaseModel):
    username: str
    password: str
    role: str = "student"


class LoginReq(BaseModel):
    username: str
    password: str


class TokenResp(BaseModel):
    token: str
    role: str


class EnrollReq(BaseModel):
    course_id: int


class CreateCourseReq(BaseModel):
    name: str
    capacity: int = Field(..., ge=1, description="容量 >= 1")
    start_time: datetime
    end_time: datetime


def _course_dict(c: Course) -> dict:
    return {
        "id": c.id, "name": c.name, "capacity": c.capacity,
        "enrolled": c.enrolled,
        "start_time": c.start_time.isoformat(), "end_time": c.end_time.isoformat(),
    }


# ---------------------------------------------------------------------------
# 公开接口
# ---------------------------------------------------------------------------
@app.post("/api/register", response_model=TokenResp)
def register(req: RegisterReq, db: Session = Depends(get_db)):
    # 2026-09 二次审计：先拦截角色再查重名——"已存在用户名 + role=admin" 应返回
    # 403（明确拒绝提权），而不是 409（顺带向探测者确认该用户名存在）
    if req.role == "admin":
        # 2026-09 修复：任何人可自注册 admin 是提权漏洞；admin 角色只能由管理员授予
        raise HTTPException(403, detail="admin 角色需由管理员授予")
    if req.role not in ("student", "teacher"):
        raise HTTPException(400, detail="非法角色")
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(409, detail="用户名已存在")
    user = User(username=req.username, password=hash_password(req.password), role=req.role)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # 并发同名注册：唯一键兜底（2026-09 复审补充，原先会 500）
        db.rollback()
        raise HTTPException(409, detail="用户名已存在")
    db.refresh(user)
    return TokenResp(token=issue_token(user, db), role=user.role)


@app.post("/api/login", response_model=TokenResp)
def login(req: LoginReq, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if user is None or not verify_password(req.password, user.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    if not user.password.startswith("pbkdf2_sha256$"):
        # 旧库遗留明文：校验通过后透明升级为哈希
        user.password = hash_password(req.password)
        db.commit()
    return TokenResp(token=issue_token(user, db), role=user.role)


@app.get("/api/courses")
def list_courses(db: Session = Depends(get_db)):
    return [_course_dict(c) for c in db.query(Course).order_by(Course.id).all()]


@app.get("/api/courses/{course_id}")
def get_course(course_id: int, db: Session = Depends(get_db)):
    c = db.query(Course).filter(Course.id == course_id).first()
    if c is None:
        raise HTTPException(404, detail="课程不存在")
    return _course_dict(c)


# ---------------------------------------------------------------------------
# 选课 / 退课
# ---------------------------------------------------------------------------
@app.post("/api/enroll")
def enroll(req: EnrollReq, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_role(user, "student")
    course = db.query(Course).filter(Course.id == req.course_id).first()
    if course is None:
        raise HTTPException(404, detail="课程不存在")
    # 2026-09 二次审计：重复选课检查提到容量预检之前——重选一门已满课程时，
    # 语义应是「已选过」而不是误导性的「容量已满」
    if db.query(Enrollment).filter(
        Enrollment.student_id == user.id, Enrollment.course_id == course.id
    ).first():
        raise HTTPException(409, detail="已选过该课程")
    if course.enrolled >= course.capacity:
        raise HTTPException(409, detail="课程容量已满")

    # 时间冲突：与已选课程时间有重叠即拒绝
    conflict = (
        db.query(Enrollment)
        .join(Course, Enrollment.course_id == Course.id)
        .filter(
            Enrollment.student_id == user.id,
            Course.start_time < course.end_time,
            Course.end_time > course.start_time,
        )
        .first()
    )
    if conflict:
        raise HTTPException(409, detail="选课时间与其他课程冲突")

    # 容量并发安全：原子条件更新（enrolled < capacity 才 +1），0 行受影响即已满。
    # 2026-09 修复：原先"先查容量再 +1"是 check-then-act，并发下会超卖。
    updated = (
        db.query(Course)
        .filter(Course.id == course.id, Course.enrolled < Course.capacity)
        .update({Course.enrolled: Course.enrolled + 1}, synchronize_session=False)
    )
    if updated == 0:
        db.rollback()
        raise HTTPException(409, detail="课程容量已满")
    db.add(Enrollment(student_id=user.id, course_id=course.id))
    try:
        db.commit()
    except IntegrityError:
        # 并发重复选课：唯一键 uq_enroll 兜底
        db.rollback()
        raise HTTPException(409, detail="已选过该课程")
    db.refresh(course)
    return {"message": "选课成功", "course_id": course.id, "enrolled": course.enrolled}


@app.post("/api/unenroll")
def unenroll(req: EnrollReq, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_role(user, "student")
    e = db.query(Enrollment).filter(
        Enrollment.student_id == user.id, Enrollment.course_id == req.course_id
    ).first()
    if e is None:
        raise HTTPException(404, detail="未选该课程")
    # 先原子删除报名行，再回补容量。两个并发退课请求只能有一个删除成功。
    deleted = db.query(Enrollment).filter(Enrollment.id == e.id).delete(synchronize_session=False)
    if deleted != 1:
        db.rollback()
        raise HTTPException(404, detail="未选该课程")
    course = db.query(Course).filter(Course.id == req.course_id).first()
    if course is not None:
        # 2026-09 二次审计：容量回滚改为与 enroll 对称的原子条件更新。
        # 原先"读 enrolled → 内存减一 → 写回"在并发下会丢失回滚量
        # （退课读到 5，他人原子 +1 到 6，写回 4 → 座位泄漏）。
        db.query(Course).filter(Course.id == course.id, Course.enrolled > 0).update(
            {Course.enrolled: Course.enrolled - 1}, synchronize_session=False
        )
    db.commit()
    if course is not None:
        db.refresh(course)   # 原子更新未同步会话内对象，刷新取真实值用于响应
    return {"message": "退课成功", "course_id": req.course_id,
            "enrolled": course.enrolled if course else 0}


@app.get("/api/my-courses")
def my_courses(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(Course)
        .join(Enrollment, Enrollment.course_id == Course.id)
        .filter(Enrollment.student_id == user.id)
        .order_by(Course.id)
        .all()
    )
    return [{"id": c.id, "name": c.name} for c in rows]


# ---------------------------------------------------------------------------
# 管理员接口（构造边界数据 + 越权 403 场景）
# ---------------------------------------------------------------------------
@app.post("/api/admin/courses", status_code=201)
def admin_create_course(req: CreateCourseReq, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_role(user, "admin")
    if req.end_time <= req.start_time:
        raise HTTPException(400, detail="结束时间必须晚于开始时间")
    c = Course(name=req.name, capacity=req.capacity, enrolled=0,
               start_time=req.start_time, end_time=req.end_time)
    db.add(c)
    db.commit()
    db.refresh(c)
    return _course_dict(c)


@app.get("/api/admin/stats")
def admin_stats(user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_role(user, "admin")
    return {
        "users": db.query(User).count(),
        "courses": db.query(Course).count(),
        "enrollments": db.query(Enrollment).count(),
    }


class RoleReq(BaseModel):
    role: str


@app.patch("/api/admin/users/{username}/role")
def admin_grant_role(username: str, req: RoleReq,
                     user: User = Depends(current_user), db: Session = Depends(get_db)):
    """授予/变更角色（admin 专属）。配合注册端点：自助注册只能拿 student/teacher。"""
    require_role(user, "admin")
    if req.role not in ("student", "teacher", "admin"):
        raise HTTPException(400, detail="非法角色")
    target = db.query(User).filter(User.username == username).first()
    if target is None:
        raise HTTPException(404, detail="用户不存在")
    target.role = req.role
    db.commit()
    return {"username": target.username, "role": target.role}
