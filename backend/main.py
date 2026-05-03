from datetime import datetime, timedelta
from io import BytesIO
import re
from typing import List

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from pypdf import PdfReader
from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

SECRET_KEY = "change-this-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
DATABASE_URL = "sqlite:///./resume_analyzer.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

COMMON_SKILLS = {
    "python", "java", "javascript", "typescript", "react", "node", "sql", "aws", "docker",
    "kubernetes", "fastapi", "django", "flask", "git", "ci/cd", "linux", "tensorflow", "pytorch",
    "nlp", "machine learning", "data analysis", "power bi", "tableau", "excel", "mongodb", "postgresql"
}

ACTION_VERBS = {
    "built", "designed", "implemented", "optimized", "led", "developed", "improved", "automated",
    "delivered", "managed", "created", "launched", "deployed", "analyzed", "architected"
}

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String)
    hashed_password: Mapped[str] = mapped_column(String)
    resumes: Mapped[List["ResumeAnalysis"]] = relationship(back_populates="owner")

class ResumeAnalysis(Base):
    __tablename__ = "resume_analyses"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    filename: Mapped[str] = mapped_column(String)
    ats_score: Mapped[int] = mapped_column(Integer)
    word_count: Mapped[int] = mapped_column(Integer)
    extracted_skills: Mapped[list] = mapped_column(JSON)
    strengths: Mapped[list] = mapped_column(JSON)
    improvements: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    raw_text: Mapped[str] = mapped_column(Text)
    owner: Mapped[User] = relationship(back_populates="resumes")

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Resume Analyzer API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UserCreate(BaseModel):
    email: str
    full_name: str
    password: str

class UserOut(BaseModel):
    id: int
    email: str
    full_name: str

class AnalysisOut(BaseModel):
    id: int
    filename: str
    ats_score: int
    word_count: int
    extracted_skills: list
    strengths: list
    improvements: list
    created_at: datetime


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str):
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(status_code=401, detail="Could not validate credentials")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise credentials_exception
    return user


def extract_text_from_pdf(contents: bytes) -> str:
    reader = PdfReader(BytesIO(contents))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extract_skills(text: str) -> List[str]:
    lower = text.lower()
    return sorted([skill for skill in COMMON_SKILLS if skill in lower])


def compute_ats_score(text: str, skills: List[str], target_keywords: List[str]) -> tuple[int, list, list]:
    words = re.findall(r"\w+", text)
    word_count = len(words)
    score = 40
    strengths = []
    improvements = []

    if 350 <= word_count <= 900:
        score += 15
        strengths.append("Resume length is in the recommended range.")
    else:
        improvements.append("Target 350-900 words for better ATS readability.")

    if len(skills) >= 8:
        score += 20
        strengths.append("Strong technical keyword coverage.")
    else:
        improvements.append("Add more relevant technical skills and tools.")

    bullet_count = len(re.findall(r"(^\s*[-•])", text, flags=re.MULTILINE))
    if bullet_count >= 8:
        score += 10
        strengths.append("Bullet-point structure improves scanability.")
    else:
        improvements.append("Use more bullet points for achievements.")

    verbs_found = sum(1 for v in ACTION_VERBS if v in text.lower())
    if verbs_found >= 6:
        score += 10
        strengths.append("Uses strong action verbs.")
    else:
        improvements.append("Add impact-driven action verbs (Built, Led, Optimized, etc.).")

    keyword_hits = [k for k in target_keywords if k.lower() in text.lower()]
    if target_keywords:
        alignment = int((len(keyword_hits) / len(target_keywords)) * 20)
        score += alignment
        if alignment >= 12:
            strengths.append("Good alignment with target job keywords.")
        else:
            improvements.append("Increase alignment with job-specific keywords.")

    return min(score, 100), strengths, improvements


@app.post("/auth/register", response_model=UserOut)
def register(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = User(email=user.email, full_name=user.full_name, hashed_password=hash_password(user.password))
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.post("/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": token, "token_type": "bearer"}


@app.post("/analyze", response_model=AnalysisOut)
def analyze_resume(
    file: UploadFile = File(...),
    target_keywords: str = Form(default=""),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    content = file.file.read()
    text = extract_text_from_pdf(content)
    if not text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from PDF")

    keyword_list = [k.strip() for k in target_keywords.split(",") if k.strip()]
    skills = extract_skills(text)
    ats_score, strengths, improvements = compute_ats_score(text, skills, keyword_list)

    analysis = ResumeAnalysis(
        user_id=current_user.id,
        filename=file.filename,
        ats_score=ats_score,
        word_count=len(re.findall(r"\w+", text)),
        extracted_skills=skills,
        strengths=strengths,
        improvements=improvements,
        raw_text=text[:10000],
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


@app.get("/dashboard")
def get_dashboard(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    analyses = db.query(ResumeAnalysis).filter(ResumeAnalysis.user_id == current_user.id).all()
    if not analyses:
        return {"total_resumes": 0, "average_ats_score": 0, "top_skills": [], "recent_analyses": []}

    skill_freq = {}
    for analysis in analyses:
        for skill in analysis.extracted_skills:
            skill_freq[skill] = skill_freq.get(skill, 0) + 1

    top_skills = sorted(skill_freq.items(), key=lambda x: x[1], reverse=True)[:10]
    return {
        "total_resumes": len(analyses),
        "average_ats_score": round(sum(a.ats_score for a in analyses) / len(analyses), 2),
        "top_skills": [{"skill": s, "count": c} for s, c in top_skills],
        "recent_analyses": [
            {
                "id": a.id,
                "filename": a.filename,
                "ats_score": a.ats_score,
                "created_at": a.created_at,
            }
            for a in sorted(analyses, key=lambda x: x.created_at, reverse=True)[:5]
        ],
    }


@app.get("/analyses", response_model=List[AnalysisOut])
def list_analyses(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(ResumeAnalysis).filter(ResumeAnalysis.user_id == current_user.id).order_by(ResumeAnalysis.created_at.desc()).all()
