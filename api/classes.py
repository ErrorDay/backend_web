"""
api/classes.py
CRUD /classes + PATCH /classes/visibility -- dipanggil Kelas.jsx.

CATATAN mapping: `grade` di frontend awalnya diasumsikan integer
10/11/12 (skema seed default Emergent). Project sekolah kita pakai
tingkat Romawi (X/XI/XII) atau format bebas lain di Kelas.tingkat.
Supaya tidak memaksa migrasi data lama, endpoint ini TIDAK
memvalidasi grade harus 10/11/12 -- Kelas.tingkat dikirim apa
adanya sebagai `grade` (string), dan frontend cukup menampilkannya
tanpa peduli formatnya.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database.session import SessionLocal
from database.models import Kelas, Siswa

router = APIRouter()


class ClassIn(BaseModel):
    name: str
    grade: str  # dikirim apa adanya ke Kelas.tingkat (lihat catatan di atas)


class VisibilityIn(BaseModel):
    grade: str
    visible: bool


def _serialize(kelas: Kelas, db) -> dict:
    student_count = (
        db.query(Siswa)
        .filter(Siswa.kelas_id == kelas.id, Siswa.status == "AKTIF")
        .count()
    )
    return {
        "id": str(kelas.id),
        "name": kelas.nama,
        "grade": kelas.tingkat,
        "visible": kelas.visible,
        "student_count": student_count,
    }


@router.get("")
def list_classes():
    db = SessionLocal()
    try:
        classes = db.query(Kelas).order_by(Kelas.tingkat, Kelas.nama).all()
        return [_serialize(k, db) for k in classes]
    finally:
        db.close()


@router.post("")
def create_class(data: ClassIn):
    db = SessionLocal()
    try:
        exists = db.query(Kelas).filter(Kelas.nama == data.name).first()
        if exists:
            raise HTTPException(400, "Nama kelas sudah ada")

        kelas = Kelas(
            nama=data.name,
            tingkat=data.grade,
            jurusan="",
            tahun_ajaran="2026/2027",
            aktif=True,
            visible=True,
        )
        db.add(kelas)
        db.commit()
        db.refresh(kelas)
        return _serialize(kelas, db)
    finally:
        db.close()


@router.put("/{class_id}")
def update_class(class_id: int, data: ClassIn):
    db = SessionLocal()
    try:
        kelas = db.query(Kelas).filter(Kelas.id == class_id).first()
        if kelas is None:
            raise HTTPException(404, "Kelas tidak ditemukan")

        kelas.nama = data.name
        kelas.tingkat = data.grade
        db.commit()
        db.refresh(kelas)
        return _serialize(kelas, db)
    finally:
        db.close()


@router.delete("/{class_id}")
def delete_class(class_id: int):
    db = SessionLocal()
    try:
        n = db.query(Siswa).filter(Siswa.kelas_id == class_id).count()
        if n:
            raise HTTPException(400, f"Kelas masih memiliki {n} siswa. Pindahkan siswa terlebih dahulu.")

        kelas = db.query(Kelas).filter(Kelas.id == class_id).first()
        if kelas is None:
            raise HTTPException(404, "Kelas tidak ditemukan")

        db.delete(kelas)
        db.commit()
        return {"ok": True}
    finally:
        db.close()


@router.patch("/visibility")
def set_visibility(data: VisibilityIn):
    """Sembunyikan/tampilkan SEMUA kelas dalam satu tingkat sekaligus."""
    db = SessionLocal()
    try:
        db.query(Kelas).filter(Kelas.tingkat == data.grade).update({"visible": data.visible})
        db.commit()
        return {"ok": True, "grade": data.grade, "visible": data.visible}
    finally:
        db.close()
