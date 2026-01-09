from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
import json
import os

# Rich opsiyonel: varsa profesyonel TUI, yoksa plain print
USE_RICH = True
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.prompt import Prompt, IntPrompt
except Exception:
    USE_RICH = False

console = Console() if USE_RICH else None


# -------------------------
# 1) ABSTRACT CLASS (ABC)
# -------------------------
class User(ABC):
    def __init__(self, user_id: int, name: str, phone: str):
        self._user_id = user_id          # protected
        self._name = name                # protected
        self.__phone = phone             # private

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def name(self) -> str:
        return self._name

    def get_phone_masked(self) -> str:
        if len(self.__phone) < 4:
            return "***"
        return f"***-***-{self.__phone[-4:]}"

    @abstractmethod
    def get_info(self) -> str:
        raise NotImplementedError


class Student(User):
    def __init__(self, user_id: int, name: str, phone: str, grade_level: str):
        super().__init__(user_id, name, phone)
        self._grade_level = grade_level
        self._appointments: List[int] = []

    def add_appointment(self, appointment_id: int) -> None:
        self._appointments.append(appointment_id)

    def get_info(self) -> str:  # polymorphism
        return f"Öğrenci #{self.user_id} | {self.name} | Seviye: {self._grade_level} | Tel: {self.get_phone_masked()}"

    @property
    def appointments(self) -> List[int]:
        return list(self._appointments)


class Teacher(User):
    def __init__(self, user_id: int, name: str, phone: str, branch: str):
        super().__init__(user_id, name, phone)
        self._branch = branch
        self._lessons: List[int] = []
        self.__rating_sum = 0
        self.__rating_count = 0

    def add_lesson(self, lesson_id: int) -> None:
        self._lessons.append(lesson_id)

    def rate(self, score: int) -> None:
        if not (1 <= score <= 5):
            raise ValueError("Puan 1-5 arasında olmalı.")
        self.__rating_sum += score
        self.__rating_count += 1

    def avg_rating(self) -> float:
        return 0.0 if self.__rating_count == 0 else self.__rating_sum / self.__rating_count

    def get_info(self) -> str:  # polymorphism
        return f"Öğretmen #{self.user_id} | {self.name} | Branş: {self._branch} | Puan: {self.avg_rating():.1f} | Tel: {self.get_phone_masked()}"

    @property
    def lessons(self) -> List[int]:
        return list(self._lessons)


@dataclass
class Lesson:
    lesson_id: int
    title: str
    duration_min: int
    hourly_price: float

    def get_info(self) -> str:
        return f"Ders #{self.lesson_id} | {self.title} | Süre: {self.duration_min} dk | Saatlik: {self.hourly_price}₺"


class Payment:
    def __init__(self, payment_id: int, appointment_id: int, amount: float, method: str):
        self._payment_id = payment_id
        self._appointment_id = appointment_id
        self._amount = amount
        self.__method = method
        self._paid_at = datetime.now()

    def get_info(self) -> str:
        return f"Ödeme #{self._payment_id} | Randevu #{self._appointment_id} | {self._amount:.2f}₺ | Yöntem: {self.__method} | {self._paid_at:%Y-%m-%d %H:%M}"


class Appointment:
    # COMPOSITION: Appointment içinde Student/Teacher/Lesson nesneleri
    def __init__(self, appointment_id: int, student: Student, teacher: Teacher, lesson: Lesson, date_str: str, time_str: str):
        self._appointment_id = appointment_id
        self._student = student
        self._teacher = teacher
        self._lesson = lesson
        self._date_str = date_str
        self._time_str = time_str
        self.__is_paid = False
        self.__payment_id: Optional[int] = None

    @property
    def appointment_id(self) -> int:
        return self._appointment_id

    @property
    def is_paid(self) -> bool:
        return self.__is_paid

    def mark_paid(self, payment_id: int) -> None:
        self.__is_paid = True
        self.__payment_id = payment_id

    def calculate_total(self) -> float:
        hours = self._lesson.duration_min / 60
        return self._lesson.hourly_price * hours

    def slot_key(self) -> str:
        # öğretmenin aynı gün-saat çakışmasını yakalamak için
        return f"{self._teacher.user_id}:{self._date_str}:{self._time_str}"

    def get_info(self) -> str:
        status = "ÖDENDİ" if self.__is_paid else "ÖDENMEDİ"
        return (
            f"Randevu #{self._appointment_id} | {self._date_str} {self._time_str} | {status}\n"
            f"  Öğrenci: {self._student.name} (#{self._student.user_id})\n"
            f"  Öğretmen: {self._teacher.name} (#{self._teacher.user_id})\n"
            f"  Ders: {self._lesson.title} (#{self._lesson.lesson_id}) | Tutar: {self.calculate_total():.2f}₺"
        )


class TutoringSystem:
    def __init__(self, db_path: str = "db.json"):
        self._students: Dict[int, Student] = {}
        self._teachers: Dict[int, Teacher] = {}
        self._lessons: Dict[int, Lesson] = {}
        self._appointments: Dict[int, Appointment] = {}
        self._payments: Dict[int, Payment] = {}
        self._occupied_slots: set[str] = set()   # çakışma kontrolü

        self._next_student_id = 1
        self._next_teacher_id = 1
        self._next_lesson_id = 1
        self._next_appointment_id = 1
        self._next_payment_id = 1

        self._db_path = db_path
        self.load()

    @staticmethod
    def _validate_date(date_str: str) -> None:
        datetime.strptime(date_str, "%Y-%m-%d")

    @staticmethod
    def _validate_time(time_str: str) -> None:
        datetime.strptime(time_str, "%H:%M")

    # ---------- persistence ----------
    def save(self) -> None:
        data = {
            "next_ids": {
                "student": self._next_student_id,
                "teacher": self._next_teacher_id,
                "lesson": self._next_lesson_id,
                "appointment": self._next_appointment_id,
                "payment": self._next_payment_id,
            },
            "students": [
                {"id": s.user_id, "name": s.name, "phone_masked": s.get_phone_masked(), "grade": s._grade_level, "appointments": s.appointments}
                for s in self._students.values()
            ],
            "teachers": [
                {"id": t.user_id, "name": t.name, "branch": t._branch, "lessons": t.lessons}
                for t in self._teachers.values()
            ],
            "lessons": [
                {"id": l.lesson_id, "title": l.title, "duration": l.duration_min, "hourly": l.hourly_price}
                for l in self._lessons.values()
            ],
            "appointments": [
                {
                    "id": a.appointment_id,
                    "student_id": a._student.user_id,
                    "teacher_id": a._teacher.user_id,
                    "lesson_id": a._lesson.lesson_id,
                    "date": a._date_str,
                    "time": a._time_str,
                    "paid": a.is_paid,
                }
                for a in self._appointments.values()
            ],
        }
        with open(self._db_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self) -> None:
        if not os.path.exists(self._db_path):
            return
        try:
            with open(self._db_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            ids = data.get("next_ids", {})
            self._next_student_id = ids.get("student", 1)
            self._next_teacher_id = ids.get("teacher", 1)
            self._next_lesson_id = ids.get("lesson", 1)
            self._next_appointment_id = ids.get("appointment", 1)
            self._next_payment_id = ids.get("payment", 1)

            # Yeniden nesne üretimi (basit)
            for s in data.get("students", []):
                st = Student(s["id"], s["name"], "0000", s.get("grade", ""))
                for ap in s.get("appointments", []):
                    st.add_appointment(ap)
                self._students[st.user_id] = st

            for t in data.get("teachers", []):
                te = Teacher(t["id"], t["name"], "0000", t.get("branch", ""))
                for lid in t.get("lessons", []):
                    te.add_lesson(lid)
                self._teachers[te.user_id] = te

            for l in data.get("lessons", []):
                le = Lesson(l["id"], l["title"], l["duration"], l["hourly"])
                self._lessons[le.lesson_id] = le

            # appointments: composition olduğu için id'lerle bağla
            for a in data.get("appointments", []):
                ap = Appointment(
                    a["id"],
                    self._students[a["student_id"]],
                    self._teachers[a["teacher_id"]],
                    self._lessons[a["lesson_id"]],
                    a["date"],
                    a["time"],
                )
                self._appointments[ap.appointment_id] = ap
                self._occupied_slots.add(ap.slot_key())
        except Exception:
            # bozuk json vs. olursa sistemi açmaya engel olmasın
            pass

    # ---------- create entities ----------
    def add_student(self, name: str, phone: str, grade_level: str) -> Student:
        s = Student(self._next_student_id, name, phone, grade_level)
        self._students[s.user_id] = s
        self._next_student_id += 1
        self.save()
        return s

    def add_teacher(self, name: str, phone: str, branch: str) -> Teacher:
        t = Teacher(self._next_teacher_id, name, phone, branch)
        self._teachers[t.user_id] = t
        self._next_teacher_id += 1
        self.save()
        return t

    def add_lesson(self, teacher_id: int, title: str, duration_min: int, hourly_price: float) -> Lesson:
        if teacher_id not in self._teachers:
            raise KeyError("Öğretmen bulunamadı.")
        lesson = Lesson(self._next_lesson_id, title, duration_min, hourly_price)
        self._lessons[lesson.lesson_id] = lesson
        self._teachers[teacher_id].add_lesson(lesson.lesson_id)
        self._next_lesson_id += 1
        self.save()
        return lesson

    def create_appointment(self, student_id: int, teacher_id: int, lesson_id: int, date_str: str, time_str: str) -> Appointment:
        if student_id not in self._students:
            raise KeyError("Öğrenci bulunamadı.")
        if teacher_id not in self._teachers:
            raise KeyError("Öğretmen bulunamadı.")
        if lesson_id not in self._lessons:
            raise KeyError("Ders bulunamadı.")
        teacher = self._teachers[teacher_id]
        if lesson_id not in teacher.lessons:
            raise ValueError("Bu ders seçilen öğretmene ait değil.")

        self._validate_date(date_str)
        self._validate_time(time_str)

        appt = Appointment(self._next_appointment_id, self._students[student_id], teacher, self._lessons[lesson_id], date_str, time_str)

        # ÇAKIŞMA kontrolü (profesyonel dokunuş)
        key = appt.slot_key()
        if key in self._occupied_slots:
            raise ValueError("Bu öğretmen için bu tarih/saat dolu. Başka saat seçin.")
        self._occupied_slots.add(key)

        self._appointments[appt.appointment_id] = appt
        self._students[student_id].add_appointment(appt.appointment_id)
        self._next_appointment_id += 1
        self.save()
        return appt

    def pay(self, appointment_id: int, method: str) -> Payment:
        if appointment_id not in self._appointments:
            raise KeyError("Randevu bulunamadı.")
        appt = self._appointments[appointment_id]
        if appt.is_paid:
            raise ValueError("Bu randevu zaten ödenmiş.")
        payment = Payment(self._next_payment_id, appointment_id, appt.calculate_total(), method)
        self._payments[self._next_payment_id] = payment
        appt.mark_paid(self._next_payment_id)
        self._next_payment_id += 1
        self.save()
        return payment

    def rate_teacher(self, teacher_id: int, score: int) -> None:
        if teacher_id not in self._teachers:
            raise KeyError("Öğretmen bulunamadı.")
        self._teachers[teacher_id].rate(score)
        self.save()

    # ---------- list ----------
    def students(self) -> List[Student]:
        return list(self._students.values())

    def teachers(self) -> List[Teacher]:
        return list(self._teachers.values())

    def lessons(self) -> List[Lesson]:
        return list(self._lessons.values())

    def appointments(self) -> List[Appointment]:
        return list(self._appointments.values())

    def payments(self) -> List[Payment]:
        return list(self._payments.values())


# -------------------------
# Terminal UI helpers
# -------------------------
def ui_title():
    if USE_RICH:
        console.print(Panel.fit("ÖZEL DERS & ÖĞRETMEN EŞLEŞTİRME SİSTEMİ", title="TutorMatch", subtitle="Terminal Uygulaması", style="bold cyan"))
    else:
        print("\n" + "="*60)
        print("ÖZEL DERS & ÖĞRETMEN EŞLEŞTİRME SİSTEMİ")
        print("="*60)


def ui_menu():
    if USE_RICH:
        table = Table(title="Menü", show_lines=True)
        table.add_column("Seçim", justify="center")
        table.add_column("İşlem")
        for k, v in [
            ("1", "Öğrenci ekle"),
            ("2", "Öğretmen ekle"),
            ("3", "Öğretmene ders ekle"),
            ("4", "Randevu oluştur"),
            ("5", "Randevu ödemesi yap"),
            ("6", "Öğretmeni puanla"),
            ("7", "Listele"),
            ("0", "Çıkış"),
        ]:
            table.add_row(k, v)
        console.print(table)
        return Prompt.ask("Seçiminiz", default="7")
    else:
        print("1) Öğrenci ekle")
        print("2) Öğretmen ekle")
        print("3) Öğretmene ders ekle")
        print("4) Randevu oluştur")
        print("5) Randevu ödemesi yap")
        print("6) Öğretmeni puanla")
        print("7) Listele")
        print("0) Çıkış")
        return input("Seçiminiz: ").strip()


def list_menu():
    if USE_RICH:
        return Prompt.ask("Liste (1-Öğrenci, 2-Öğretmen, 3-Ders, 4-Randevu, 5-Ödeme)", default="2")
    else:
        print("1) Öğrenciler")
        print("2) Öğretmenler")
        print("3) Dersler")
        print("4) Randevular")
        print("5) Ödemeler")
        return input("Seçim: ").strip()


def info(msg: str):
    if USE_RICH:
        console.print(f"[green]✅ {msg}[/green]")
    else:
        print("✅", msg)


def error(msg: str):
    if USE_RICH:
        console.print(f"[red]❌ {msg}[/red]")
    else:
        print("❌", msg)


def main():
    system = TutoringSystem()

    while True:
        ui_title()
        choice = ui_menu()

        try:
            if choice == "1":
                name = Prompt.ask("Öğrenci adı") if USE_RICH else input("Öğrenci adı: ")
                phone = Prompt.ask("Telefon") if USE_RICH else input("Telefon: ")
                grade = Prompt.ask("Seviye (Lise/Üniversite)") if USE_RICH else input("Seviye: ")
                s = system.add_student(name.strip(), phone.strip(), grade.strip())
                info(s.get_info())

            elif choice == "2":
                name = Prompt.ask("Öğretmen adı") if USE_RICH else input("Öğretmen adı: ")
                phone = Prompt.ask("Telefon") if USE_RICH else input("Telefon: ")
                branch = Prompt.ask("Branş") if USE_RICH else input("Branş: ")
                t = system.add_teacher(name.strip(), phone.strip(), branch.strip())
                info(t.get_info())

            elif choice == "3":
                teacher_id = IntPrompt.ask("Öğretmen ID") if USE_RICH else int(input("Öğretmen ID: "))
                title = Prompt.ask("Ders adı") if USE_RICH else input("Ders adı: ")
                duration = IntPrompt.ask("Süre (dk)") if USE_RICH else int(input("Süre (dk): "))
                hourly = float(Prompt.ask("Saatlik ücret (₺)", default="400").replace(",", ".")) if USE_RICH else float(input("Saatlik ücret: ").replace(",", "."))
                l = system.add_lesson(teacher_id, title.strip(), duration, hourly)
                info(l.get_info())

            elif choice == "4":
                student_id = IntPrompt.ask("Öğrenci ID") if USE_RICH else int(input("Öğrenci ID: "))
                teacher_id = IntPrompt.ask("Öğretmen ID") if USE_RICH else int(input("Öğretmen ID: "))
                lesson_id = IntPrompt.ask("Ders ID") if USE_RICH else int(input("Ders ID: "))
                date_str = Prompt.ask("Tarih (YYYY-MM-DD)") if USE_RICH else input("Tarih (YYYY-MM-DD): ")
                time_str = Prompt.ask("Saat (HH:MM)") if USE_RICH else input("Saat (HH:MM): ")
                a = system.create_appointment(student_id, teacher_id, lesson_id, date_str.strip(), time_str.strip())
                info("Randevu oluşturuldu.")
                if USE_RICH:
                    console.print(Panel(a.get_info(), title="Randevu", style="cyan"))
                else:
                    print(a.get_info())

            elif choice == "5":
                appointment_id = IntPrompt.ask("Randevu ID") if USE_RICH else int(input("Randevu ID: "))
                method = Prompt.ask("Ödeme yöntemi (Kart/Havale/Nakit)", default="Kart") if USE_RICH else input("Ödeme yöntemi: ")
                p = system.pay(appointment_id, method.strip())
                info(p.get_info())

            elif choice == "6":
                teacher_id = IntPrompt.ask("Öğretmen ID") if USE_RICH else int(input("Öğretmen ID: "))
                score = IntPrompt.ask("Puan (1-5)") if USE_RICH else int(input("Puan (1-5): "))
                system.rate_teacher(teacher_id, score)
                info("Puan verildi.")

            elif choice == "7":
                sub = list_menu()
                if sub == "1":
                    if USE_RICH:
                        t = Table(title="Öğrenciler")
                        t.add_column("ID"); t.add_column("Ad"); t.add_column("Seviye")
                        for s in system.students():
                            t.add_row(str(s.user_id), s.name, s._grade_level)
                        console.print(t)
                    else:
                        for s in system.students():
                            print(s.get_info())

                elif sub == "2":
                    if USE_RICH:
                        t = Table(title="Öğretmenler")
                        t.add_column("ID"); t.add_column("Ad"); t.add_column("Branş"); t.add_column("Puan")
                        for te in system.teachers():
                            t.add_row(str(te.user_id), te.name, te._branch, f"{te.avg_rating():.1f}")
                        console.print(t)
                    else:
                        for te in system.teachers():
                            print(te.get_info())

                elif sub == "3":
                    if USE_RICH:
                        t = Table(title="Dersler")
                        t.add_column("ID"); t.add_column("Başlık"); t.add_column("Süre"); t.add_column("Saatlik")
                        for l in system.lessons():
                            t.add_row(str(l.lesson_id), l.title, str(l.duration_min), f"{l.hourly_price}")
                        console.print(t)
                    else:
                        for l in system.lessons():
                            print(l.get_info())

                elif sub == "4":
                    if USE_RICH:
                        for a in system.appointments():
                            console.print(Panel(a.get_info(), style="cyan"))
                    else:
                        for a in system.appointments():
                            print(a.get_info(), "\n")

                elif sub == "5":
                    if USE_RICH:
                        t = Table(title="Ödemeler")
                        t.add_column("Bilgi")
                        for p in system.payments():
                            t.add_row(p.get_info())
                        console.print(t)
                    else:
                        for p in system.payments():
                            print(p.get_info())
                else:
                    error("Geçersiz seçim.")

            elif choice == "0":
                info("Çıkılıyor...")
                break
            else:
                error("Geçersiz seçim.")

        except Exception as e:
            # try-except şartı
            error(str(e))


if __name__ == "__main__":
    main() 
