# main.py
# Özel Ders & Öğretmen Eşleştirme Sistemi (Terminal)
# OOP Gereksinimleri: 5+ class, __init__, encapsulation, inheritance, polymorphism, abstraction (ABC),
# composition, list/dict, try-except, terminal app

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional


# -------------------------
# 1) ABSTRACT CLASS (ABC)
# -------------------------
class User(ABC):
    def __init__(self, user_id: int, name: str, phone: str):
        self._user_id = user_id                    # protected (encapsulation)
        self._name = name                          # protected
        self.__phone = phone                       # private (encapsulation)

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def name(self) -> str:
        return self._name

    def get_phone_masked(self) -> str:
        # phone private ama maskeleyerek erişim sağlıyoruz
        if len(self.__phone) < 4:
            return "***"
        return f"***-***-{self.__phone[-4:]}"

    @abstractmethod
    def get_info(self) -> str:
        """Polymorphism: Student/Teacher bunu override edecek."""
        raise NotImplementedError


# -------------------------
# 2) INHERITANCE
# -------------------------
class Student(User):
    def __init__(self, user_id: int, name: str, phone: str, grade_level: str):
        super().__init__(user_id, name, phone)
        self._grade_level = grade_level
        self._appointments: List[int] = []  # appointment_id listesi (list)

    def add_appointment(self, appointment_id: int) -> None:
        self._appointments.append(appointment_id)

    def get_info(self) -> str:  # override -> polymorphism
        return f"Öğrenci #{self.user_id} | {self.name} | Seviye: {self._grade_level} | Tel: {self.get_phone_masked()}"

    @property
    def appointments(self) -> List[int]:
        return list(self._appointments)


class Teacher(User):
    def __init__(self, user_id: int, name: str, phone: str, branch: str):
        super().__init__(user_id, name, phone)
        self._branch = branch
        self._lessons: List[int] = []         # teacher'ın verdiği ders id'leri
        self.__rating_sum = 0                  # private
        self.__rating_count = 0                # private

    def add_lesson(self, lesson_id: int) -> None:
        self._lessons.append(lesson_id)

    def rate(self, score: int) -> None:
        if not (1 <= score <= 5):
            raise ValueError("Puan 1-5 arasında olmalı.")
        self.__rating_sum += score
        self.__rating_count += 1

    def avg_rating(self) -> float:
        if self.__rating_count == 0:
            return 0.0
        return self.__rating_sum / self.__rating_count

    def get_info(self) -> str:  # override -> polymorphism
        return f"Öğretmen #{self.user_id} | {self.name} | Branş: {self._branch} | Puan: {self.avg_rating():.1f} | Tel: {self.get_phone_masked()}"

    @property
    def lessons(self) -> List[int]:
        return list(self._lessons)


# -------------------------
# 3) ENTITY CLASSES
# -------------------------
@dataclass
class Lesson:
    lesson_id: int
    title: str
    duration_min: int
    hourly_price: float  # saatlik ücret

    def get_info(self) -> str:
        return f"Ders #{self.lesson_id} | {self.title} | Süre: {self.duration_min} dk | Saatlik: {self.hourly_price}₺"


class Payment:
    def __init__(self, payment_id: int, appointment_id: int, amount: float, method: str):
        self._payment_id = payment_id
        self._appointment_id = appointment_id
        self._amount = amount
        self.__method = method            # private
        self._paid_at = datetime.now()

    def get_info(self) -> str:
        return f"Ödeme #{self._payment_id} | Randevu #{self._appointment_id} | {self._amount:.2f}₺ | Yöntem: {self.__method} | {self._paid_at:%Y-%m-%d %H:%M}"


class Appointment:
    def __init__(
        self,
        appointment_id: int,
        student: Student,
        teacher: Teacher,
        lesson: Lesson,
        date_str: str,        # "YYYY-MM-DD"
        time_str: str         # "HH:MM"
    ):
        # COMPOSITION: Appointment içinde Student/Teacher/Lesson nesneleri
        self._appointment_id = appointment_id
        self._student = student
        self._teacher = teacher
        self._lesson = lesson
        self._date_str = date_str
        self._time_str = time_str
        self.__is_paid = False            # private
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
        # 60 dk üzerinden saatlik ücret -> toplam
        hours = self._lesson.duration_min / 60
        return self._lesson.hourly_price * hours

    def get_info(self) -> str:
        status = "ÖDENDİ" if self.__is_paid else "ÖDENMEDİ"
        return (
            f"Randevu #{self._appointment_id} | {self._date_str} {self._time_str} | {status}\n"
            f"  Öğrenci: {self._student.name} (#{self._student.user_id})\n"
            f"  Öğretmen: {self._teacher.name} (#{self._teacher.user_id})\n"
            f"  Ders: {self._lesson.title} (#{self._lesson.lesson_id}) | Tutar: {self.calculate_total():.2f}₺"
        )


# -------------------------
# 4) SYSTEM (COMPOSITION HUB)
# -------------------------
class TutoringSystem:
    def __init__(self):
        # dict veri yapıları (list/dict şartı)
        self._students: Dict[int, Student] = {}
        self._teachers: Dict[int, Teacher] = {}
        self._lessons: Dict[int, Lesson] = {}
        self._appointments: Dict[int, Appointment] = {}
        self._payments: Dict[int, Payment] = {}

        # auto increment id'ler
        self._next_student_id = 1
        self._next_teacher_id = 1
        self._next_lesson_id = 1
        self._next_appointment_id = 1
        self._next_payment_id = 1

    # ---------- helpers ----------
    @staticmethod
    def _validate_date(date_str: str) -> None:
        datetime.strptime(date_str, "%Y-%m-%d")  # ValueError atar

    @staticmethod
    def _validate_time(time_str: str) -> None:
        datetime.strptime(time_str, "%H:%M")     # ValueError atar

    # ---------- create entities ----------
    def add_student(self, name: str, phone: str, grade_level: str) -> Student:
        s = Student(self._next_student_id, name, phone, grade_level)
        self._students[s.user_id] = s
        self._next_student_id += 1
        return s

    def add_teacher(self, name: str, phone: str, branch: str) -> Teacher:
        t = Teacher(self._next_teacher_id, name, phone, branch)
        self._teachers[t.user_id] = t
        self._next_teacher_id += 1
        return t

    def add_lesson(self, teacher_id: int, title: str, duration_min: int, hourly_price: float) -> Lesson:
        if teacher_id not in self._teachers:
            raise KeyError("Öğretmen bulunamadı.")
        lesson = Lesson(self._next_lesson_id, title, duration_min, hourly_price)
        self._lessons[lesson.lesson_id] = lesson
        self._teachers[teacher_id].add_lesson(lesson.lesson_id)
        self._next_lesson_id += 1
        return lesson

    # ---------- appointment ----------
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

        appt = Appointment(
            appointment_id=self._next_appointment_id,
            student=self._students[student_id],
            teacher=teacher,
            lesson=self._lessons[lesson_id],
            date_str=date_str,
            time_str=time_str
        )

        self._appointments[appt.appointment_id] = appt
        self._students[student_id].add_appointment(appt.appointment_id)
        self._next_appointment_id += 1
        return appt

    # ---------- payment ----------
    def pay(self, appointment_id: int, method: str) -> Payment:
        if appointment_id not in self._appointments:
            raise KeyError("Randevu bulunamadı.")

        appt = self._appointments[appointment_id]
        if appt.is_paid:
            raise ValueError("Bu randevu zaten ödenmiş.")

        amount = appt.calculate_total()
        payment = Payment(self._next_payment_id, appointment_id, amount, method)
        self._payments[self._next_payment_id] = payment
        appt.mark_paid(self._next_payment_id)
        self._next_payment_id += 1
        return payment

    # ---------- rating ----------
    def rate_teacher(self, teacher_id: int, score: int) -> None:
        if teacher_id not in self._teachers:
            raise KeyError("Öğretmen bulunamadı.")
        self._teachers[teacher_id].rate(score)

    # ---------- list views ----------
    def list_students(self) -> List[str]:
        return [s.get_info() for s in self._students.values()]

    def list_teachers(self) -> List[str]:
        return [t.get_info() for t in self._teachers.values()]

    def list_lessons(self) -> List[str]:
        out = []
        for lesson in self._lessons.values():
            out.append(lesson.get_info())
        return out

    def list_appointments(self) -> List[str]:
        return [a.get_info() for a in self._appointments.values()]

    def list_payments(self) -> List[str]:
        return [p.get_info() for p in self._payments.values()]


# -------------------------
# 5) TERMINAL UI
# -------------------------
def print_menu() -> None:
    print("\n" + "=" * 60)
    print("ÖZEL DERS & ÖĞRETMEN EŞLEŞTİRME SİSTEMİ")
    print("=" * 60)
    print("1) Öğrenci ekle")
    print("2) Öğretmen ekle")
    print("3) Öğretmene ders ekle")
    print("4) Randevu oluştur")
    print("5) Randevu ödemesi yap")
    print("6) Öğretmeni puanla")
    print("7) Listele (Öğrenci/Öğretmen/Ders/Randevu/Ödeme)")
    print("0) Çıkış")


def print_list_menu() -> None:
    print("\nListele:")
    print("1) Öğrenciler")
    print("2) Öğretmenler")
    print("3) Dersler")
    print("4) Randevular")
    print("5) Ödemeler")


def safe_int(prompt: str) -> int:
    while True:
        try:
            return int(input(prompt).strip())
        except ValueError:
            print("Hatalı giriş. Lütfen sayı girin.")


def safe_float(prompt: str) -> float:
    while True:
        try:
            return float(input(prompt).strip().replace(",", "."))
        except ValueError:
            print("Hatalı giriş. Lütfen sayı girin (örn: 250 veya 250.5).")


def main():
    system = TutoringSystem()

    # İstersen hazır demo veri (raporda gösterim için güzel olur)
    # system.add_student("Buse Şevval", "05551234567", "Üniversite")
    # t = system.add_teacher("Ebru Hoca", "05559876543", "Matematik")
    # system.add_lesson(t.user_id, "Analiz - İntegral", 60, 400)

    while True:
        print_menu()
        choice = input("Seçiminiz: ").strip()

        try:
            if choice == "1":
                name = input("Öğrenci adı: ").strip()
                phone = input("Telefon: ").strip()
                grade = input("Seviye (örn: Lise/Üniversite): ").strip()
                s = system.add_student(name, phone, grade)
                print("✅ Eklendi:", s.get_info())

            elif choice == "2":
                name = input("Öğretmen adı: ").strip()
                phone = input("Telefon: ").strip()
                branch = input("Branş: ").strip()
                t = system.add_teacher(name, phone, branch)
                print("✅ Eklendi:", t.get_info())

            elif choice == "3":
                teacher_id = safe_int("Öğretmen ID: ")
                title = input("Ders adı: ").strip()
                duration = safe_int("Süre (dk): ")
                hourly = safe_float("Saatlik ücret (₺): ")
                lesson = system.add_lesson(teacher_id, title, duration, hourly)
                print("✅ Ders eklendi:", lesson.get_info())

            elif choice == "4":
                student_id = safe_int("Öğrenci ID: ")
                teacher_id = safe_int("Öğretmen ID: ")
                lesson_id = safe_int("Ders ID: ")
                date_str = input("Tarih (YYYY-MM-DD): ").strip()
                time_str = input("Saat (HH:MM): ").strip()
                appt = system.create_appointment(student_id, teacher_id, lesson_id, date_str, time_str)
                print("✅ Randevu oluşturuldu:\n", appt.get_info())

            elif choice == "5":
                appointment_id = safe_int("Randevu ID: ")
                method = input("Ödeme yöntemi (Kart/Havale/Nakit): ").strip()
                payment = system.pay(appointment_id, method)
                print("✅ Ödeme alındı:", payment.get_info())

            elif choice == "6":
                teacher_id = safe_int("Öğretmen ID: ")
                score = safe_int("Puan (1-5): ")
                system.rate_teacher(teacher_id, score)
                print("✅ Puan verildi.")

            elif choice == "7":
                print_list_menu()
                sub = input("Seçiminiz: ").strip()

                if sub == "1":
                    items = system.list_students()
                    print("\n--- ÖĞRENCİLER ---")
                    print("\n".join(items) if items else "(Boş)")
                elif sub == "2":
                    items = system.list_teachers()
                    print("\n--- ÖĞRETMENLER ---")
                    print("\n".join(items) if items else "(Boş)")
                elif sub == "3":
                    items = system.list_lessons()
                    print("\n--- DERSLER ---")
                    print("\n".join(items) if items else "(Boş)")
                elif sub == "4":
                    items = system.list_appointments()
                    print("\n--- RANDEVULAR ---")
                    print("\n\n".join(items) if items else "(Boş)")
                elif sub == "5":
                    items = system.list_payments()
                    print("\n--- ÖDEMELER ---")
                    print("\n".join(items) if items else "(Boş)")
                else:
                    print("Geçersiz seçim.")

            elif choice == "0":
                print("Çıkılıyor... 👋")
                break
            else:
                print("Geçersiz seçim.")

        except Exception as e:
            # try-except şartı: tüm beklenmeyen hataları yakala
            print(f"❌ Hata: {e}")


if __name__ == "__main__":
    main()
