"""
api/students.py
CRUD /students + POST /students/{id}/migrate -- dipanggil Kelas.jsx.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database.session import SessionLocal
from database.models import Siswa, Kelas

router = APIRouter()


class StudentIn(BaseModel):
    nisn: str
    name: str
    gender: str = "L"
    class_id: str
    status: str = "AKTIF"


class MigrateIn(BaseModel):
    class_id: str


class AssignBulkIn(BaseModel):
    class_id: str
    student_ids: list[str]


def _serialize(siswa: Siswa, kelas: Kelas | None = None) -> dict:
    kelas = kelas or siswa.kelas
    return {
        "id": str(siswa.id),
        "nisn": siswa.nis or "",
        "name": siswa.nama,
        "gender": siswa.jenis_kelamin or "L",
        "class_id": str(siswa.kelas_id),
        "class_name": kelas.nama if kelas else "",
        "grade": kelas.tingkat if kelas else "",
        "status": siswa.status,
    }


@router.get("")
def list_students(class_id: str | None = None, q: str | None = None):
    db = SessionLocal()
    try:
        query = db.query(Siswa)
        if class_id:
            query = query.filter(Siswa.kelas_id == int(class_id))
        if q:
            query = query.filter(Siswa.nama.ilike(f"%{q}%"))
        siswa_list = query.order_by(Siswa.nama).all()
        return [_serialize(s) for s in siswa_list]
    finally:
        db.close()


@router.post("")
def create_student(data: StudentIn):
    db = SessionLocal()
    try:
        kelas = db.query(Kelas).filter(Kelas.id == int(data.class_id)).first()
        if kelas is None:
            raise HTTPException(404, "Kelas tidak ditemukan")

        if data.nisn and db.query(Siswa).filter(Siswa.nis == data.nisn).first():
            raise HTTPException(400, "NIS/NISN sudah terdaftar")

        siswa = Siswa(
            nis=data.nisn or None,
            nama=data.name,
            kelas_id=kelas.id,
            jenis_kelamin=data.gender,
            status=data.status,
        )
        db.add(siswa)
        db.commit()
        db.refresh(siswa)
        return _serialize(siswa, kelas)
    finally:
        db.close()


@router.post("/assign-bulk")
def assign_students_bulk(data: AssignBulkIn):
    """
    Masukkan banyak siswa YANG SUDAH TERDAFTAR ke satu kelas sekaligus
    (dipakai Kelas.jsx saat admin pilih dari daftar siswa existing,
    beda dari POST /students yang untuk siswa benar-benar baru).
    """
    db = SessionLocal()
    try:
        kelas = db.query(Kelas).filter(Kelas.id == int(data.class_id)).first()
        if kelas is None:
            raise HTTPException(404, "Kelas tidak ditemukan")

        ids = [int(sid) for sid in data.student_ids]
        moved = (
            db.query(Siswa)
            .filter(Siswa.id.in_(ids))
            .update({"kelas_id": kelas.id}, synchronize_session=False)
        )
        db.commit()

        return {"ok": True, "moved": moved, "class_id": str(kelas.id)}
    finally:
        db.close()


@router.put("/{student_id}")
def update_student(student_id: int, data: StudentIn):
    db = SessionLocal()
    try:
        kelas = db.query(Kelas).filter(Kelas.id == int(data.class_id)).first()
        if kelas is None:
            raise HTTPException(404, "Kelas tidak ditemukan")

        siswa = db.query(Siswa).filter(Siswa.id == student_id).first()
        if siswa is None:
            raise HTTPException(404, "Siswa tidak ditemukan")

        siswa.nis = data.nisn or None
        siswa.nama = data.name
        siswa.kelas_id = kelas.id
        siswa.jenis_kelamin = data.gender
        siswa.status = data.status
        db.commit()
        db.refresh(siswa)
        return _serialize(siswa, kelas)
    finally:
        db.close()


@router.delete("/{student_id}")
def delete_student(student_id: int):
    db = SessionLocal()
    try:
        siswa = db.query(Siswa).filter(Siswa.id == student_id).first()
        if siswa is None:
            raise HTTPException(404, "Siswa tidak ditemukan")
        db.delete(siswa)
        db.commit()
        return {"ok": True}
    finally:
        db.close()


@router.post("/{student_id}/migrate")
def migrate_student(student_id: int, data: MigrateIn):
    db = SessionLocal()
    try:
        kelas = db.query(Kelas).filter(Kelas.id == int(data.class_id)).first()
        if kelas is None:
            raise HTTPException(404, "Kelas tujuan tidak ditemukan")

        siswa = db.query(Siswa).filter(Siswa.id == student_id).first()
        if siswa is None:
            raise HTTPException(404, "Siswa tidak ditemukan")

        siswa.kelas_id = kelas.id
        db.commit()
        db.refresh(siswa)
        return _serialize(siswa, kelas)
    finally:
        db.close()
