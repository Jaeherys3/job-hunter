"""
Skrypt do automatycznego ustawienia Windows Task Scheduler.
Uruchom raz jako Administrator: python setup_scheduler.py
"""

import subprocess
import sys
import os

def setup_task():
    # Ścieżka do tego projektu
    project_dir = os.path.dirname(os.path.abspath(__file__))
    python_exe = sys.executable
    main_script = os.path.join(project_dir, "main.py")
    log_file = os.path.join(project_dir, "data", "scheduler.log")

    os.makedirs(os.path.join(project_dir, "data"), exist_ok=True)

    # Wrapper bat który loguje output
    bat_path = os.path.join(project_dir, "run_job_hunter.bat")
    with open(bat_path, "w") as f:
        f.write(f'@echo off\n')
        f.write(f'cd /d "{project_dir}"\n')
        f.write(f'"{python_exe}" "{main_script}" >> "{log_file}" 2>&1\n')

    # Komenda schtasks
    task_name = "JobHunterDaily"
    cmd = [
        "schtasks", "/create",
        "/tn", task_name,
        "/tr", bat_path,
        "/sc", "DAILY",
        "/st", "08:00",
        "/f",  # nadpisz jeśli istnieje
        "/rl", "HIGHEST",
    ]

    print(f"⚙️  Tworzę zadanie w Task Scheduler: '{task_name}'")
    print(f"   Python: {python_exe}")
    print(f"   Skrypt: {main_script}")
    print(f"   Czas:   codziennie o 08:00\n")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print("✅ Zadanie utworzone pomyślnie!")
        print(f"   Log będzie zapisywany do: {log_file}")
        print("\n💡 Możesz zmienić godzinę w Task Scheduler (wyszukaj 'Harmonogram zadań' w menu Start)")
    else:
        print(f"❌ Błąd: {result.stderr}")
        print("\n💡 Upewnij się, że uruchamiasz jako Administrator.")
        print("   Alternatywnie możesz ręcznie dodać zadanie w 'Harmonogramie zadań'.")

    print(f"\n📝 Plik .bat zapisany w: {bat_path}")

if __name__ == "__main__":
    setup_task()
